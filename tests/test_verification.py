"""Verification is a metadata decision, never a title-search-link assertion."""

import unittest

from scholar_compass.verification import verify_paper


PAPER = {
    "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    "authors": ["Patrick Lewis", "Ethan Perez"], "year": 2020,
    "doi": "10.5555/3495724.3496517",
}


class FakeScholar:
    def __init__(self, *results, response=None, error=None):
        self.response = {"organic_results": list(results)} if response is None else response
        self.error = error
        self.calls = []

    def search(self, title):
        self.calls.append(title)
        if self.error:
            raise self.error
        return self.response


def record(**changes):
    return {"title": PAPER["title"], "link": "https://papers.nips.cc/paper/2020/example",
            "publication_info": {"summary": "P Lewis, E Perez, A Piktus - Advances in Neural Information Processing Systems, 2020",
                                 "authors": [{"name": "P Lewis"}, {"name": "E Perez"}]}, **changes}


class VerificationTests(unittest.TestCase):
    def test_actual_serpapi_publication_shape_matches_author_and_year(self):
        provider = FakeScholar(record())
        result = verify_paper(PAPER, provider)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(provider.calls, [PAPER["title"]])
        self.assertIsNotNone(result["checked_at"])
        self.assertEqual(result["title_similarity"], 1)

    def test_summary_authors_work_without_author_array(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={"summary": "P Lewis, E Perez - NeurIPS, 2020"})))
        self.assertEqual(result["status"], "verified")

    def test_exact_title_without_corroboration_is_ambiguous(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={})))
        self.assertEqual(result["status"], "ambiguous")

    def test_doi_url_can_corroborate_without_authors_or_year(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={}, link="https://doi.org/10.5555/3495724.3496517")))
        self.assertEqual(result["status"], "verified")

    def test_wrong_doi_rejects_even_when_title_author_and_year_match(self):
        result = verify_paper(PAPER, FakeScholar(record(doi="10.1234/different-paper")))
        self.assertEqual(result["status"], "ambiguous")
        self.assertTrue(any("DOI conflicts" in item for item in result["evidence"]))

    def test_wrong_year_rejects_even_with_matching_doi(self):
        result = verify_paper(PAPER, FakeScholar(record(doi=PAPER["doi"], year=2021)))
        self.assertEqual(result["status"], "ambiguous")
        self.assertTrue(any("year conflicts" in item for item in result["evidence"]))

    def test_no_shared_author_is_ambiguous(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={"summary": "J Smith - NeurIPS, 2020", "authors": [{"name": "J Smith"}]})))
        self.assertEqual(result["status"], "ambiguous")

    def test_same_surname_with_different_given_name_is_not_corroboration(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={"summary": "Paul Lewis - NeurIPS, 2020", "authors": [{"name": "Paul Lewis"}]})))
        self.assertEqual(result["status"], "ambiguous")

    def test_surname_alone_is_not_corroboration(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={"summary": "Lewis - NeurIPS, 2020", "authors": [{"name": "Lewis"}]})))
        self.assertEqual(result["status"], "ambiguous")

    def test_hallucinated_title_rejected_even_if_year_author_doi_match(self):
        result = verify_paper({**PAPER, "title": "Unicorn Agents Discover the Universal Law of Perfect Hallucination-Free Knowledge"}, FakeScholar(record(doi=PAPER["doi"])))
        self.assertEqual(result["status"], "not_found")

    def test_similar_but_different_title_is_not_verified(self):
        result = verify_paper(PAPER, FakeScholar(record(title="Retrieval-Augmented Generation for Protein-Intensive Biological Tasks")))
        self.assertEqual(result["status"], "not_found")

    def test_publication_year_not_inferred_from_snippet(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={"authors": [{"name": "P Lewis"}]}, snippet="Building on a 2020 study.")))
        self.assertEqual(result["status"], "ambiguous")

    def test_unicode_title_and_chinese_authors(self):
        candidate = {"title": "检索增强生成：事实性评估", "authors": ["张三"], "year": 2024, "doi": None}
        result = verify_paper(candidate, FakeScholar({"title": "检索增强生成:事实性评估", "publication_info": {"authors": [{"name": "张三"}], "summary": "张三 - 计算机研究, 2024"}}))
        self.assertEqual(result["status"], "verified")

    def test_empty_results_mean_not_found_but_provider_failure_is_unavailable(self):
        self.assertEqual(verify_paper(PAPER, FakeScholar())["status"], "not_found")
        result = verify_paper(PAPER, FakeScholar(error=RuntimeError("secret-api-key")))
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("secret-api-key", str(result))

    def test_error_and_malformed_responses_are_unavailable(self):
        for response in ({"error": "secret-api-key"}, {}, {"organic_results": None}, {"organic_results": [None]}):
            with self.subTest(response=response):
                result = verify_paper(PAPER, FakeScholar(response=response))
                self.assertEqual(result["status"], "unavailable")
                self.assertNotIn("secret-api-key", str(result))

    def test_successful_empty_serpapi_response_can_omit_results(self):
        response = {"search_metadata": {"status": "Success"}, "search_information": {"organic_results_state": "Fully empty"}}
        self.assertEqual(verify_paper(PAPER, FakeScholar(response=response))["status"], "not_found")

    def test_no_provider_requires_manual_work(self):
        result = verify_paper(PAPER)
        self.assertEqual(result["status"], "manual_required")
        self.assertIsNone(result["checked_at"])
        self.assertIn("scholar.google.com/scholar?q=", result["scholar_url"])

    def test_demo_never_calls_live_provider_or_claims_verification(self):
        provider = FakeScholar(record())
        result = verify_paper(PAPER, provider, demo=True)
        self.assertEqual(result["status"], "demo")
        self.assertEqual(provider.calls, [])
        self.assertIsNone(result["checked_at"])

    def test_later_corrobated_record_can_resolve_earlier_title_only_record(self):
        result = verify_paper(PAPER, FakeScholar(record(publication_info={}), record()))
        self.assertEqual(result["status"], "verified")


if __name__ == "__main__":
    unittest.main()
