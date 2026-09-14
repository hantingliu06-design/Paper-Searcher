"""Deterministic, inspectable lexical relevance and bibliography ranking.

Scores are bounded to 0..100. Citations use log1p(count)/log1p(10000),
and Journal Impact Factor (JIF) uses log1p(JIF)/log1p(50). These are fixed
scales, so adding candidates cannot change an existing paper's score.
Missing metrics are excluded and remaining weights are renormalized.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping

DEFAULT_WEIGHTS = {"relevance": 60.0, "citations": 25.0, "impact_factor": 15.0}
CITATION_CAP = 10_000
IMPACT_FACTOR_CAP = 50

# Generic research vocabulary must not make unrelated papers look relevant.
# Domain words (e.g. retrieval, language, clinical) deliberately remain.
STOPWORDS = frozenset(
    "a an the and or of on in to for from with without by at as is are was were "
    "be been being this that these those it its our their we you your into via "
    "using use used based study studies research paper papers approach approaches "
    "method methods model models framework system systems analysis evaluation "
    "evaluating evaluate new novel proposed propose towards toward how what "
    "effect effects application applications performance improvement improved "
    "的 了 和 与 及 或 在 对 为 中 基于 研究 论文 方法 模型 系统 分析 评估 应用".split()
)


def _normalize(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).casefold()


def _tokens(text: object) -> list[str]:
    return re.findall(r"[^\W_]+", _normalize(text), flags=re.UNICODE)


def _has_cjk(token: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in token)


def _number(value: object) -> float | None:
    # bool is an int in Python but is not a bibliometric observation.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
    except (OverflowError, ValueError):
        return None
    return numeric if math.isfinite(numeric) and numeric >= 0 else None


def _validated_weights(weights: Mapping | None) -> dict[str, float]:
    supplied = {} if weights is None else weights
    if not isinstance(supplied, Mapping):
        raise ValueError("weights must be an object containing numeric weights")
    if set(supplied) - set(DEFAULT_WEIGHTS):
        raise ValueError("Unknown score weight")
    result = dict(DEFAULT_WEIGHTS)
    for name, value in supplied.items():
        number = _number(value)
        if number is None:
            raise ValueError("Weights must be finite, nonnegative numbers")
        result[name] = number
    if sum(result.values()) <= 0 or not math.isfinite(sum(result.values())):
        raise ValueError("At least one weight must be positive")
    return result


def _relevance(paper: Mapping, plan: Mapping) -> tuple[float, list, list, list]:
    # Author and venue names are not evidence of topical relevance.
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
    document_tokens = set(_tokens(text))
    document_normalized = _normalize(text)
    weighted_match = 0.0
    possible = 0.0
    matched: list[str] = []
    missing: list[str] = []
    details: list[str] = []
    for concept in plan.get("concepts", []):
        if not isinstance(concept, Mapping):
            continue
        name = str(concept.get("name", "")).strip()
        terms = concept.get("terms", [])
        if not isinstance(terms, list):
            terms = []
        variants = [name, *[term for term in terms if isinstance(term, str)]]
        scores = []
        for term in variants:
            informative = set(_tokens(term)) - STOPWORDS
            if not informative:
                continue
            # CJK has no obligatory word spaces. Exact substring matches
            # support user-provided Chinese phrases without guessed segmentation.
            hits = sum(
                token in document_normalized if _has_cjk(token)
                else token in document_tokens
                for token in informative
            )
            scores.append(hits / len(informative))
        if not scores:
            continue
        importance = _number(concept.get("importance", 1))
        importance = max(1.0, min(5.0, importance if importance is not None else 1.0))
        fraction = max(scores)
        weighted_match += importance * fraction
        possible += importance
        (matched if fraction > 0 else missing).append(name)
        if fraction > 0:
            details.append(f"{name}: {fraction:.0%} lexical term coverage")
    score = 100 * weighted_match / possible if possible else 0.0
    return score, matched, missing, details


def score_paper(paper: Mapping, plan: Mapping, weights: Mapping | None = None) -> dict:
    """Return score components, completeness, effective weights and evidence.

    A concept contributes its best synonym's informative-token coverage, weighted
    by importance (1..5). This measures word overlap, not semantic understanding.
    ``coverage`` is the share of requested weight supported by available data;
    ``effective_weights`` are percentages after missing-data renormalization.
    Observed zero counts and zero JIF are available data, not missing data.
    """
    requested = _validated_weights(weights)
    relevance, matched, missing, concept_details = _relevance(paper, plan)
    count = _number(paper.get("citation_count"))
    metrics = paper.get("metrics")
    impact = _number(metrics.get("impact_factor")) if isinstance(metrics, Mapping) else None
    citations = 100 * math.log1p(min(count, CITATION_CAP)) / math.log1p(CITATION_CAP) if count is not None else None
    impact_score = 100 * math.log1p(min(impact, IMPACT_FACTOR_CAP)) / math.log1p(IMPACT_FACTOR_CAP) if impact is not None else None
    components = {"relevance": relevance, "citations": citations, "impact_factor": impact_score}
    available_weight = sum(requested[key] for key, value in components.items() if value is not None)
    effective = {
        key: 100 * requested[key] / available_weight
        if value is not None and available_weight > 0 else 0.0
        for key, value in components.items()
    }
    total = sum((value or 0.0) * effective[key] / 100 for key, value in components.items())
    explanation = [
        "Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match.",
        *concept_details,
        "Citation score = 100 × ln(1 + min(count, 10000)) / ln(10001)."
        if count is not None else "Citation count is missing; its weight is excluded.",
        "JIF score = 100 × ln(1 + min(JIF, 50)) / ln(51). JIF is a journal-level metric."
        if impact is not None else "Journal Impact Factor is missing; its weight is excluded, not treated as zero.",
    ]
    if not paper.get("abstract"):
        explanation.append("Abstract is unavailable; relevance uses title only.")
    if available_weight == 0:
        explanation.append("No available component has positive requested weight; total is 0 and coverage is 0.")
    return {
        "total": round(total, 2),
        "relevance": round(relevance, 2),
        "citations": round(citations, 2) if citations is not None else None,
        "impact_factor": round(impact_score, 2) if impact_score is not None else None,
        "coverage": round(available_weight / sum(requested.values()), 4),
        "effective_weights": {key: round(value, 4) for key, value in effective.items()},
        "matched_concepts": matched,
        "missing_concepts": missing,
        "explanation": explanation,
    }


def rank_papers(papers: list[dict], plan: Mapping, weights: Mapping | None = None) -> list[dict]:
    """Return copies with scores, descending; preserve input order on ties."""
    _validated_weights(weights)
    scored = [{**paper, "score": score_paper(paper, plan, weights)} for paper in papers]
    return sorted(scored, key=lambda paper: paper["score"]["total"], reverse=True)
