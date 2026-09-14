"""Behavioral checks for transparent ranking, unavailable data and edge cases."""

import math
import unittest

from scholar_compass.scoring import rank_papers, score_paper


PLAN = {
    "concepts": [
        {"name": "Retrieval", "terms": ["retrieval", "检索"], "importance": 3},
        {"name": "Hallucination", "terms": ["hallucination", "幻觉"], "importance": 2},
    ]
}


def paper(**changes):
    return {"title": "Retrieval with hallucination detection", "abstract": "", "citation_count": 99,
            "metrics": None, **changes}


class ScoringTests(unittest.TestCase):
    def test_missing_jif_renormalizes_and_exposes_coverage(self):
        score = score_paper(paper(), PLAN)
        citation_score = 100 * math.log(100) / math.log(10001)
        self.assertAlmostEqual(score["total"], (100 * 60 + citation_score * 25) / 85, places=2)
        self.assertIsNone(score["impact_factor"])
        self.assertEqual(score["coverage"], 0.85)
        self.assertEqual(score["effective_weights"]["impact_factor"], 0)
        self.assertAlmostEqual(score["effective_weights"]["relevance"], 100 * 60 / 85, places=4)

    def test_observed_zero_is_available_and_lowers_total(self):
        score = score_paper(paper(citation_count=0, metrics={"impact_factor": 0}), PLAN)
        self.assertEqual(score["citations"], 0)
        self.assertEqual(score["impact_factor"], 0)
        self.assertEqual(score["coverage"], 1)
        self.assertEqual(score["total"], 60)

    def test_all_metrics_missing_preserves_relevance_and_reduced_coverage(self):
        score = score_paper(paper(citation_count=None), PLAN)
        self.assertEqual(score["total"], 100)
        self.assertEqual(score["coverage"], 0.6)
        self.assertEqual(score["effective_weights"]["relevance"], 100)

    def test_caps_keep_very_large_values_bounded(self):
        score = score_paper(paper(citation_count=10**15, metrics={"impact_factor": 300}), PLAN)
        self.assertEqual(score["total"], 100)
        self.assertEqual(score["citations"], 100)
        self.assertEqual(score["impact_factor"], 100)

    def test_chinese_substrings_and_unicode_normalization(self):
        score = score_paper(paper(title="一种针对检索增强系统的幻觉检测研究"), PLAN)
        self.assertEqual(score["relevance"], 100)
        score = score_paper(paper(title="ＲＥＴＲＩＥＶＡＬ and HALLUCINATION"), PLAN)
        self.assertEqual(score["relevance"], 100)

    def test_generic_research_vocabulary_cannot_dominate(self):
        plan = {"concepts": [{"name": "Using a new retrieval model", "terms": [], "importance": 5}]}
        score = score_paper(paper(title="A new study using a model and method for evaluation"), plan)
        self.assertEqual(score["relevance"], 0)
        self.assertEqual(score["matched_concepts"], [])

    def test_acronym_requires_whole_word(self):
        plan = {"concepts": [{"name": "RAG", "terms": ["RAG"], "importance": 5}]}
        self.assertEqual(score_paper(paper(title="Fragmentation in agriculture"), plan)["relevance"], 0)
        self.assertEqual(score_paper(paper(title="RAG-based evidence retrieval"), plan)["relevance"], 100)

    def test_synonyms_use_best_variant_and_partial_tokens_are_inspectable(self):
        plan = {"concepts": [{"name": "retrieval augmented generation", "terms": ["RAG"], "importance": 5}]}
        self.assertEqual(score_paper(paper(title="RAG"), plan)["relevance"], 100)
        self.assertEqual(score_paper(paper(title="retrieval generation"), plan)["relevance"], 66.67)

    def test_venue_and_authors_do_not_inflate_relevance(self):
        candidate = paper(title="Quantum transport", venue="Retrieval and hallucination", authors=["Retrieval"])
        self.assertEqual(score_paper(candidate, PLAN)["relevance"], 0)

    def test_score_is_independent_of_candidate_pool_and_ties_are_stable(self):
        first, second = paper(id="first"), paper(id="second")
        first_score = score_paper(first, PLAN)
        ranked = rank_papers([first, second, paper(id="other", title="Quantum transport")], PLAN)
        self.assertEqual([p["id"] for p in ranked[:2]], ["first", "second"])
        self.assertEqual(ranked[0]["score"], first_score)
        self.assertNotIn("score", first)

    def test_invalid_metrics_are_missing_not_poisoned_numbers(self):
        for value in (float("nan"), float("inf"), -1, True, "123"):
            with self.subTest(value=value):
                score = score_paper(paper(citation_count=value, metrics={"impact_factor": value}), PLAN)
                self.assertIsNone(score["citations"])
                self.assertIsNone(score["impact_factor"])
                self.assertTrue(math.isfinite(score["total"]))

    def test_no_available_positive_weight_has_explicit_zero_coverage(self):
        score = score_paper(paper(), PLAN, {"relevance": 0, "citations": 0, "impact_factor": 100})
        self.assertEqual(score["total"], 0)
        self.assertEqual(score["coverage"], 0)

    def test_invalid_weights_are_rejected(self):
        for weights in ({"relevance": -1}, {"citations": float("nan")}, {"relevance": True},
                        {"extra": 20}, {"relevance": 0, "citations": 0, "impact_factor": 0}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                score_paper(paper(), PLAN, weights)

    def test_empty_concepts_and_empty_candidates_are_defined(self):
        self.assertEqual(score_paper(paper(), {"concepts": []})["relevance"], 0)
        self.assertEqual(rank_papers([], PLAN), [])


if __name__ == "__main__":
    unittest.main()
