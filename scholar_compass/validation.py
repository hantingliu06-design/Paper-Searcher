"""Validate every untrusted boundary, including structured LLM output."""

from __future__ import annotations

import math
from datetime import date


class ValidationError(ValueError):
    """A user-correctable request error."""


def _text(value: object, name: str, limit: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValidationError(f"{name} 必须是非空文本。")
    if len(value) > limit:
        raise ValidationError(f"{name} 最多 {limit} 个字符。")
    return value.strip()


def _integer(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValidationError(f"{name} 必须是 {low}–{high} 之间的整数。")
    return value


def _strings(value: object, name: str, *, maximum: int = 8, limit: int = 500) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValidationError(f"{name} 需要 1–{maximum} 项。")
    return list(dict.fromkeys(_text(item, name, limit) for item in value))


def validate_input(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("输入必须是 JSON 对象。")
    year = date.today().year
    result = {
        "title": _text(data.get("title"), "论文题目", 500),
        "background": _text(data.get("background"), "研究背景", 8000),
        "keywords": _text(data.get("keywords", ""), "检索关键词", 1000, empty=True),
        "mode": data.get("mode", "demo"),
        "planner": data.get("planner", "rules"),
        "max_results": _integer(data.get("max_results", 8), "论文数量", 1, 20),
        "year_from": _integer(data.get("year_from", 2015), "起始年份", 1900, year),
        "year_to": _integer(data.get("year_to", year), "结束年份", 1900, year),
    }
    if result["mode"] not in ("demo", "live"):
        raise ValidationError("mode 必须是 demo 或 live。")
    if result["planner"] not in ("rules", "openai"):
        raise ValidationError("planner 必须是 rules 或 openai。")
    if result["year_from"] > result["year_to"]:
        raise ValidationError("起始年份不能晚于结束年份。")
    weights = data.get("weights", {"relevance": 60, "citations": 25, "impact_factor": 15})
    if not isinstance(weights, dict) or set(weights) != {"relevance", "citations", "impact_factor"}:
        raise ValidationError("评分权重需要 relevance、citations、impact_factor 三项。")
    for value in weights.values():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValidationError("权重必须是 0–100 之间的有限数值。")
    if weights["relevance"] <= 0:
        raise ValidationError("方向相关性权重必须大于 0。")
    result["weights"] = dict(weights)
    return result


def validate_plan(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("阅读计划必须是 JSON 对象。")
    concepts = data.get("concepts")
    requirements = data.get("reading_requirements")
    if not isinstance(concepts, list) or not 1 <= len(concepts) <= 10:
        raise ValidationError("计划需要 1–10 个研究概念。")
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 10:
        raise ValidationError("计划需要 1–10 个阅读要求。")
    clean_concepts, clean_requirements = [], []
    for concept in concepts:
        if not isinstance(concept, dict):
            raise ValidationError("研究概念格式错误。")
        clean_concepts.append({
            "name": _text(concept.get("name"), "概念名称", 120),
            "terms": _strings(concept.get("terms"), "概念检索词", maximum=10, limit=120),
            "importance": _integer(concept.get("importance"), "概念重要性", 1, 5),
        })
    for item in requirements:
        if not isinstance(item, dict) or item.get("priority") not in ("must", "should"):
            raise ValidationError("阅读要求的 priority 必须是 must 或 should。")
        clean_requirements.append({
            "category": _text(item.get("category"), "阅读类别", 120),
            "priority": item["priority"],
            "what_to_extract": _text(item.get("what_to_extract"), "提取信息", 1500),
            "why": _text(item.get("why"), "阅读理由", 1000),
        })
    planner = data.get("planner", "rules")
    if planner not in ("rules", "openai", "demo"):
        raise ValidationError("未知的计划生成方式。")
    warnings = data.get("warnings", [])
    if not isinstance(warnings, list) or len(warnings) > 10:
        raise ValidationError("计划 warnings 格式错误。")
    return {
        "research_question": _text(data.get("research_question"), "研究问题", 2000),
        "concepts": clean_concepts,
        "reading_requirements": clean_requirements,
        "queries": _strings(data.get("queries"), "检索式", maximum=6, limit=300),
        "inclusion_criteria": _strings(data.get("inclusion_criteria"), "纳入标准"),
        "exclusion_criteria": _strings(data.get("exclusion_criteria"), "排除标准"),
        "planner": planner,
        "warnings": [_text(w, "提示", 1000) for w in warnings],
    }
