"""API boundaries, provenance and secret handling without network access."""

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from scholar_compass.fixtures import demo_papers, demo_plan, demo_scholar_results
from scholar_compass.providers import (
    CrossrefProvider,
    JsonHttpClient,
    OpenAlexProvider,
    ProviderError,
    SerpAPIScholarProvider,
    attach_impact_factor,
    deduplicate,
    load_impact_factors,
)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        return copy.deepcopy(self.response)


class HttpClientTests(unittest.TestCase):
    def test_get_encodes_params_and_sets_timeout(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return io.BytesIO(b'{"ok":true}')

        self.assertEqual(JsonHttpClient(timeout=7, opener=opener).get("https://example.org/search", {"q": "RAG & evidence", "api_key": "a+b"}), {"ok": True})
        self.assertEqual(calls[0][1], 7)
        self.assertEqual(parse_qs(urlsplit(calls[0][0].full_url).query)["q"], ["RAG & evidence"])
        self.assertEqual(parse_qs(urlsplit(calls[0][0].full_url).query)["api_key"], ["a+b"])

    def test_transient_get_retries_once(self):
        attempts, delays = [], []

        def opener(request, timeout):
            attempts.append(request)
            if len(attempts) == 1:
                raise HTTPError(request.full_url, 429, "secret-123", {}, io.BytesIO(b"secret-123"))
            return io.BytesIO(b'{"results":[]}')

        self.assertEqual(JsonHttpClient(opener=opener, sleeper=delays.append).get("https://example.org"), {"results": []})
        self.assertEqual(len(attempts), 2)
        self.assertEqual(delays, [0.25])

    def test_auth_failure_does_not_retry_or_expose_secret(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 401, "secret-123", {}, io.BytesIO(b"secret-123"))

        with self.assertRaises(ProviderError) as caught:
            JsonHttpClient(opener=opener).get("https://example.org", {"api_key": "secret-123"})
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("secret-123", str(caught.exception))
        self.assertNotIn("example.org", str(caught.exception))
        self.assertEqual(len(calls), 1)

    def test_post_never_retries_after_network_failure(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise URLError("Bearer secret-123")

        with self.assertRaises(ProviderError) as caught:
            JsonHttpClient(retries=3, opener=opener).post("https://example.org", {"title": "测试"}, {"Authorization": "Bearer secret-123"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0].data), {"title": "测试"})
        self.assertEqual(calls[0].method, "POST")
        self.assertNotIn("secret-123", str(caught.exception))

    def test_json_and_size_boundaries(self):
        for data in (b"not JSON secret-123", b"[]", b"x" * (10 * 1024 * 1024 + 1)):
            with self.subTest(size=len(data)), self.assertRaises(ProviderError) as caught:
                JsonHttpClient(opener=lambda *args, **kwargs: io.BytesIO(data)).get("https://example.org")
            self.assertNotIn("secret-123", str(caught.exception))

    def test_rejects_invalid_or_unbounded_requests(self):
        for kwargs in ({"timeout": float("inf")}, {"timeout": True}, {"timeout": 0}, {"retries": 4}, {"retries": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                JsonHttpClient(**kwargs)
        for url in ("http://example.org", "file:///tmp/secret", "https://user:secret@example.org", "https://[bad"):
            with self.subTest(url=url), self.assertRaises(ProviderError):
                JsonHttpClient().get(url)


class AdapterTests(unittest.TestCase):
    def test_openalex_metadata_and_abstract(self):
        client = FakeClient({"results": [{
            "id": "https://openalex.org/W123", "title": "Evidence retrieval", "doi": "https://doi.org/10.1234/ABCD",
            "publication_year": 2024, "cited_by_count": 12, "is_retracted": True,
            "authorships": [{"author": {"display_name": "Jane Doe"}}, None, {"author": None}],
            "primary_location": {"landing_page_url": "javascript:alert(1)", "source": {"display_name": "Nature", "issn": ["00280836", "invalid"]}},
            "abstract_inverted_index": {"evidence": [1], "Retrieving": [0], "bad": [-1, True, 99999999]},
        }]})
        paper = OpenAlexProvider(client, api_key="secret").search("evidence", limit=2, year_from=2020, year_to=2024)[0]
        self.assertEqual(paper["abstract"], "Retrieving evidence")
        self.assertEqual(paper["doi"], "10.1234/abcd")
        self.assertEqual(paper["authors"], ["Jane Doe"])
        self.assertEqual(paper["issns"], ["0028-0836"])
        self.assertEqual(paper["url"], "https://doi.org/10.1234/abcd")
        self.assertTrue(paper["is_retracted"])
        self.assertIsNone(paper["metrics"])
        self.assertNotIn("secret", json.dumps(paper))
        self.assertEqual(client.calls[0][1]["filter"], "publication_year:2020-2024")
        self.assertEqual(client.calls[0][1]["api_key"], "secret")

    def test_openalex_missing_and_invalid_metadata_stays_missing(self):
        client = FakeClient({"results": [None, {"title": None}, {"title": "Paper", "publication_year": True, "cited_by_count": -1, "authorships": "invalid", "primary_location": None}]})
        papers = OpenAlexProvider(client).search("paper")
        self.assertEqual(len(papers), 1)
        self.assertIsNone(papers[0]["year"])
        self.assertIsNone(papers[0]["citation_count"])
        self.assertEqual(papers[0]["authors"], [])

    def test_crossref_preserves_count_source_and_strips_abstract_markup(self):
        client = FakeClient({"status": "ok", "message": {"items": [{
            "DOI": "10.1234/CROSSREF", "title": ["A paper"],
            "author": [{"given": "Jane", "family": "Doe"}, {"name": "Research Group"}],
            "published": {"date-parts": [[2023, 1, 1]]},
            "abstract": "<jats:p>Evidence &amp; <jats:bold>retrieval</jats:bold>.</jats:p>",
            "container-title": ["Nature"], "ISSN": ["1476-4687"], "is-referenced-by-count": 0,
        }, {"DOI": "garbage", "title": ["Drop me"]}]}})
        papers = CrossrefProvider(client).search("paper", year_from=2020, year_to=2025)
        self.assertEqual(len(papers), 1)
        paper = papers[0]
        self.assertEqual(paper["year"], 2023)
        self.assertEqual(paper["authors"], ["Jane Doe", "Research Group"])
        self.assertEqual(paper["citation_count"], 0)
        self.assertIn("Crossref", paper["citation_source"])
        self.assertNotIn("<", paper["abstract"])
        self.assertIn("Evidence &", paper["abstract"])
        self.assertEqual(paper["issns"], ["1476-4687"])
        self.assertEqual(client.calls[0][1]["filter"], "from-pub-date:2020-01-01,until-pub-date:2025-12-31")

    def test_provider_errors_are_sanitized(self):
        for provider in (OpenAlexProvider(FakeClient({"error": "secret-123"})), CrossrefProvider(FakeClient({"message": "secret-123"})), SerpAPIScholarProvider(FakeClient({"error": "secret-123"}), "key")):
            with self.subTest(provider=type(provider).__name__), self.assertRaises(ProviderError) as caught:
                provider.search("paper")
            self.assertNotIn("secret-123", str(caught.exception))

    def test_scholar_quotes_title_and_preserves_raw_evidence(self):
        raw = {"search_metadata": {"status": "Success"}, "organic_results": [{"title": "A paper", "link": "https://example.org/paper"}]}
        client = FakeClient(raw)
        self.assertEqual(SerpAPIScholarProvider(client, "key").search("A paper"), raw)
        self.assertEqual(client.calls[0][1]["q"], '"A paper"')
        self.assertEqual(client.calls[0][1]["engine"], "google_scholar")

    def test_scholar_success_empty_differs_from_incomplete_or_error(self):
        for raw in ({"search_metadata": {"status": "Success"}}, {"search_metadata": {"status": "Success"}, "error": "Google hasn't returned any results for this query."}, {"organic_results": []}):
            with self.subTest(raw=raw):
                self.assertEqual(SerpAPIScholarProvider(FakeClient(raw), "key").search("paper")["organic_results"], [])
        for raw in ({}, {"search_metadata": {"status": "Error"}}, {"search_metadata": {"status": "Success"}, "error": "Quota reached"}, {"organic_results": "invalid"}):
            with self.subTest(raw=raw), self.assertRaises(ProviderError):
                SerpAPIScholarProvider(FakeClient(raw), "key").search("paper")

    def test_missing_scholar_key_and_bad_queries_do_not_send_requests(self):
        client = FakeClient({})
        with self.assertRaises(ProviderError):
            SerpAPIScholarProvider(client, "").search("paper")
        for kwargs in ({"query": ""}, {"query": "x", "limit": 0}, {"query": "x", "year_from": 2024, "year_to": 2020}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ProviderError):
                OpenAlexProvider(client).search(**kwargs)
        self.assertFalse(client.calls)


class ImpactFactorTests(unittest.TestCase):
    def write_metrics(self, text, suffix=".csv"):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ("metrics" + suffix)
        path.write_text(text, encoding="utf-8")
        return path

    def test_exact_issn_match_newest_year_and_no_input_mutation(self):
        path = self.write_metrics("issn,impact_factor,year,source\n0028-0836,10,2023,User licensed JCR\n00280836,11,2024,User licensed JCR\n")
        metrics = load_impact_factors(path)
        paper = {"venue": "Nature", "issns": ["0028-0836"], "metrics": None}
        attached = attach_impact_factor(paper, metrics)
        self.assertEqual(attached["metrics"]["impact_factor"], 11)
        self.assertEqual(attached["metrics"]["year"], 2024)
        self.assertIsNone(paper["metrics"])
        attached["metrics"]["source"] = "mutated"
        self.assertEqual(metrics["0028-0836"]["source"], "User licensed JCR")
        self.assertIsNone(attach_impact_factor({"venue": "Nature", "issns": []}, metrics)["metrics"])

    def test_json_accepts_measured_zero(self):
        path = self.write_metrics('[{"issn":"0028-0836","impact_factor":0,"year":2024,"source":"Licensed file"}]', ".json")
        self.assertEqual(load_impact_factors(path)["0028-0836"]["impact_factor"], 0)

    def test_invalid_metrics_rejected(self):
        base = {"issn": "0028-0836", "impact_factor": 11, "year": 2024, "source": "JCR export"}
        for update in ({"issn": "0028-0837"}, {"impact_factor": -1}, {"impact_factor": "NaN"}, {"impact_factor": "inf"}, {"impact_factor": True}, {"year": 2024.5}, {"source": ""}):
            path = self.write_metrics(json.dumps([{**base, **update}]), ".json")
            with self.subTest(update=update), self.assertRaises(ProviderError):
                load_impact_factors(path)

    def test_same_year_conflicting_metrics_rejected(self):
        path = self.write_metrics("issn,impact_factor,year,source\n0028-0836,10,2024,JCR\n0028-0836,11,2024,JCR\n")
        with self.assertRaises(ProviderError):
            load_impact_factors(path)


class DeduplicationAndFixtureTests(unittest.TestCase):
    def paper(self, **overrides):
        return {"title": "A Useful Paper", "year": 2024, "authors": ["Jane Doe"], "doi": None, "source": "OpenAlex", "citation_count": 9, "citation_source": "OpenAlex", "citation_as_of": "2026-01-01", "issns": [], "abstract": "", **overrides}

    def test_doi_merge_preserves_count_attribution_and_enriches_metadata(self):
        original = [self.paper(doi="https://doi.org/10.1234/ABC"), self.paper(doi="10.1234/abc", source="Crossref", citation_count=99, citation_source="Crossref", abstract="Additional evidence", issns=["0028-0836"])]
        before = copy.deepcopy(original)
        merged = deduplicate(original)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["citation_count"], 9)
        self.assertEqual(merged[0]["citation_source"], "OpenAlex")
        self.assertEqual(merged[0]["sources"], ["OpenAlex", "Crossref"])
        self.assertEqual(merged[0]["abstract"], "Additional evidence")
        self.assertEqual(original, before)

    def test_title_fallback_requires_author_and_year_without_conflicting_dois(self):
        self.assertEqual(len(deduplicate([self.paper(), self.paper(title="A useful paper!")])), 1)
        self.assertEqual(len(deduplicate([self.paper(), self.paper(authors=[])])), 2)
        self.assertEqual(len(deduplicate([self.paper(), self.paper(year=None)])), 2)
        self.assertEqual(len(deduplicate([self.paper(doi="10.1234/a"), self.paper(doi="10.1234/b")])), 2)
        self.assertEqual(len(deduplicate([self.paper(doi="10.1234/a"), self.paper(doi="10.1234/b"), self.paper()])), 3)

    def test_missing_citations_are_filled_with_matching_source(self):
        merged = deduplicate([self.paper(citation_count=None), self.paper(source="Crossref", citation_source="Crossref", citation_count=4)])
        self.assertEqual(merged[0]["citation_count"], 4)
        self.assertEqual(merged[0]["citation_source"], "Crossref")

    def test_fixtures_are_independent_and_explicitly_synthetic(self):
        papers = demo_papers()
        self.assertGreaterEqual(len(papers), 8)
        self.assertTrue(all("Synthetic" in paper["citation_source"] for paper in papers))
        self.assertTrue(all(paper["metrics"] is None for paper in papers))
        self.assertTrue(all(paper["url"].startswith("https://arxiv.org/abs/") for paper in papers))
        self.assertEqual(demo_plan()["planner"], "demo")
        self.assertTrue(demo_scholar_results(papers[0])["fixture"])
        papers[0]["authors"].append("Mutation")
        self.assertNotIn("Mutation", demo_papers()[0]["authors"])


if __name__ == "__main__":
    unittest.main()
