"""Bounded plan → discover → rank → verify agent, with an observable search loop."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from .config import Settings
from .exports import to_bibtex, to_markdown
from .fixtures import demo_papers
from .planner import create_plan
from .providers import (
    CrossrefProvider, OpenAlexProvider, ProviderError, SerpAPIScholarProvider,
    attach_impact_factor, deduplicate, load_impact_factors,
)
from .scoring import rank_papers
from .validation import validate_input, validate_plan
from .verification import verify_paper


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ResearchAgent:
    """Dependencies are injectable so tests never need an API key or network."""

    def __init__(self, settings: Settings | None = None, *, search_providers=None, scholar_provider=None):
        self.settings = settings or Settings.from_env()
        self.search_providers = search_providers
        self.scholar_provider = scholar_provider

    def plan(self, data: dict) -> dict:
        return create_plan(validate_input(data), self.settings)

    def run(self, data: dict) -> dict:
        request = validate_input(data)
        warnings, trace = [], []

        def record(stage, status, detail, started):
            trace.append({"stage": stage, "status": status, "detail": detail, "duration_ms": round((perf_counter() - started) * 1000)})

        started = perf_counter()
        plan = validate_plan(data["plan"]) if "plan" in data else create_plan(request, self.settings)
        warnings.extend(plan["warnings"])
        record("plan", "complete", f"{'使用已复核计划' if 'plan' in data else '生成阅读计划'}；{len(plan['concepts'])} 个概念，{len(plan['queries'])} 条检索式。", started)

        started = perf_counter()
        if request["mode"] == "demo":
            papers = demo_papers()
            warnings.append("离线演示：固定 RAG 文献集、合成引用数和示例描述，仅用于复现流程；未进行实时检索或 Google Scholar 核验。")
            record("search", "demo", "载入固定示例文献集；编辑查询不会触发真实搜索。", started)
        else:
            papers = self._discover(request, plan, warnings, trace)
        original_count = len(papers)
        # Unknown publication years are excluded when enforcing a date range.
        papers = [p for p in papers if isinstance(p.get("year"), int)
                  and request["year_from"] <= p["year"] <= request["year_to"]
                  and not p.get("is_retracted", False)]
        removed = original_count - len(papers)
        if removed:
            warnings.append(f"按年份范围、未知年份或撤稿标记排除了 {removed} 条记录。")
        papers = deduplicate(papers)
        candidate_count = len(papers)
        started = perf_counter()
        if request["mode"] == "live" and self.settings.impact_factor_file:
            metrics = load_impact_factors(self.settings.impact_factor_file)
            papers = [attach_impact_factor(p, metrics) for p in papers]
        if any(p.get("metrics") is None for p in papers):
            warnings.append("部分期刊影响因子缺失或不适用；缺失项不记为零，按可用指标重新分配权重，并显示覆盖率。")
        papers = rank_papers(papers, plan, request["weights"])[:request["max_results"]]
        record("rank", "complete", f"{candidate_count} 篇候选按概念相关性、引用数和可用期刊影响因子排序，保留 {len(papers)} 篇。", started)

        started = perf_counter()
        scholar = self.scholar_provider
        if request["mode"] == "live" and scholar is None and self.settings.serpapi_key:
            scholar = SerpAPIScholarProvider(api_key=self.settings.serpapi_key)
        if request["mode"] == "live" and scholar is None:
            warnings.append("未配置 SERPAPI_API_KEY：Google Scholar 自动核验未执行，请通过每篇论文的学术搜索链接人工确认。")
        # Preserve ranking order while limiting paid Scholar requests to displayed papers.
        with ThreadPoolExecutor(max_workers=2) as executor:
            verifications = list(executor.map(
                lambda p: verify_paper(p, provider=scholar, demo=request["mode"] == "demo"), papers,
            ))
        for paper, verification in zip(papers, verifications):
            paper["verification"] = verification
        verified = sum(v["status"] == "verified" for v in verifications)
        unavailable = sum(v["status"] == "unavailable" for v in verifications)
        if unavailable:
            warnings.append(f"{unavailable} 篇论文的 Scholar 服务调用不可用，不能据此判定论文不存在。")
        record("verify", "demo" if request["mode"] == "demo" else ("partial" if verified < len(papers) else "complete"),
               f"核验 {len(papers)} 条记录；真实 Scholar 匹配 {verified} 条。", started)
        if not papers:
            warnings.append("没有可展示的候选论文；请检查检索式、年份范围和服务配置。")
        report = {
            "run_id": uuid4().hex[:12], "mode": request["mode"], "created_at": _now(),
            "input": copy.deepcopy(request), "plan": plan, "papers": papers,
            "warnings": list(dict.fromkeys(warnings)), "trace": trace,
            "summary": {"found": len(papers), "candidates": candidate_count, "verified": verified,
                        "manual": sum(v["status"] != "verified" for v in verifications)},
        }
        report["markdown"] = to_markdown(report)
        report["bibtex"] = to_bibtex(report)
        return report

    def _discover(self, request, plan, warnings, trace) -> list[dict]:
        providers = self.search_providers
        if providers is None:
            providers = [CrossrefProvider()]
            if self.settings.openalex_api_key:
                providers.insert(0, OpenAlexProvider(api_key=self.settings.openalex_api_key))
            else:
                warnings.append("未配置 OPENALEX_API_KEY；当前使用 Crossref。其摘要与引用覆盖可能较少，计数来源会单独标注。")
        queries = plan["queries"][:4]
        papers, failures, attempts = [], 0, 0
        # First two queries, then at most two more if recall is below the target or weak.
        for round_index in range(2):
            batch = queries[round_index * 2:round_index * 2 + 2]
            if not batch:
                break
            started = perf_counter()
            before = len(papers)
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for query in batch:
                    for provider in providers:
                        future = executor.submit(provider.search, query, limit=min(40, request["max_results"] * 2),
                                                 year_from=request["year_from"], year_to=request["year_to"])
                        futures[future] = (type(provider).__name__, query)
                        attempts += 1
                # Consume deterministically: completion timing must not change metadata precedence.
                outcomes = {}
                for future in as_completed(futures):
                    try:
                        outcomes[future] = future.result()
                    except ProviderError as exc:
                        outcomes[future] = exc
                for future, (provider_name, query) in futures.items():
                    outcome = outcomes[future]
                    if isinstance(outcome, Exception):
                        failures += 1
                        warnings.append(f"{provider_name} 检索失败：{outcome}")
                    else:
                        papers.extend(outcome)
            papers = deduplicate(papers)
            eligible = [p for p in papers if isinstance(p.get("year"), int)
                        and request["year_from"] <= p["year"] <= request["year_to"]
                        and not p.get("is_retracted", False)]
            ranked = rank_papers(eligible, plan, request["weights"])
            relevant_count = sum(p["score"]["relevance"] >= 40 for p in ranked)
            satisfied = relevant_count >= request["max_results"]
            trace.append({"stage": "search", "status": "complete" if satisfied else "partial",
                          "detail": f"第 {round_index + 1} 轮：{'；'.join(batch)}。累计 {len(papers)} 条去重记录，新增 {len(papers) - before} 条；相关性≥40 的 {relevant_count} 条。" + ("达到目标，停止扩展。" if satisfied else "召回不足，按预算扩展或结束。"),
                          "duration_ms": round((perf_counter() - started) * 1000)})
            if satisfied:
                break
        if attempts and attempts == failures:
            warnings.append("所有真实检索调用均失败；没有用离线示例替代真实结果。")
        if len(plan["queries"]) > 4:
            warnings.append("本次最多执行计划中的前 4 条检索式（两轮预算）。调整检索式顺序可改变检索范围。")
        return papers
