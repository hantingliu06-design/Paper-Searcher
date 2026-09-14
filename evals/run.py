from __future__ import annotations

import json
from pathlib import Path

from scholar_compass.fixtures import DEMO_INPUT, demo_papers
from scholar_compass.planner import create_plan
from scholar_compass.scoring import rank_papers
from scholar_compass.validation import validate_input


def main() -> int:
    request = validate_input(DEMO_INPUT)
    plan = create_plan(request)
    ranked = rank_papers(demo_papers(), plan, request["weights"])
    # The fixture contains a deliberately off-topic high-citation control paper.
    top = ranked[0]
    control = next(p for p in ranked if "Image Recognition" in p["title"])
    checks = {
        "relevant_top_has_higher_relevance": top["score"]["relevance"] > control["score"]["relevance"],
        "off_topic_control_not_top": ranked[0]["title"] != control["title"],
        "missing_jif_is_visible": all(p["score"]["coverage"] < 1 for p in ranked),
        "scores_bounded": all(0 <= p["score"]["total"] <= 100 for p in ranked),
    }
    result = {"name": "offline_rag_control", "checks": checks, "passed": sum(checks.values()), "total": len(checks),
              "limitation": "Nine-paper fixture; citation counts are synthetic teaching values and lexical relevance is not a general benchmark."}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
