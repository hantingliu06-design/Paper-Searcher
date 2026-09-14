"""Small, auditable scholarly API adapters using the Python standard library.

OpenAlex: https://docs.openalex.org/api-entities/works/search-works
Crossref: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
Scholar via SerpAPI: https://serpapi.com/google-scholar-api
"""

from __future__ import annotations

import copy
import csv
import io
import json
import math
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class ProviderError(Exception):
    """A safe, user-facing error: never includes request URLs or API secrets."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonHttpClient:
    """Bounded requests with injectable transport; POST is never retried.

    ``opener`` and ``sleeper`` are test seams. We intentionally discard error
    bodies and exception messages because providers can echo their API keys.
    """

    def __init__(self, timeout=12, retries=1, *, opener=None, sleeper=None):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("timeout must be a number between 0 and 60 seconds")
        if not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("timeout must be a number between 0 and 60 seconds")
        if type(retries) is not int or not 0 <= retries <= 3:
            raise ValueError("retries must be an integer between 0 and 3")
        self.timeout = timeout
        self.retries = retries
        self._opener = opener or urlopen
        self._sleep = sleeper or time.sleep

    def get(self, url, params=None, headers=None) -> dict:
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params, doseq=True)
        return self._request(url, None, headers, "GET")

    def post(self, url, payload, headers=None) -> dict:
        try:
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            raise ProviderError("Request payload is not valid JSON.") from None
        return self._request(url, body, headers, "POST")

    def _request(self, url, body, headers, method) -> dict:
        try:
            parts = urlsplit(url) if isinstance(url, str) else None
        except ValueError:
            parts = None
        if not parts or parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ProviderError("Provider requests require an HTTPS endpoint.")
        request_headers = {"Accept": "application/json", "User-Agent": "ScholarCompass/0.1"}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        attempts = 1 + (self.retries if method == "GET" else 0)
        for attempt in range(attempts):
            try:
                request = Request(url, data=body, headers=request_headers, method=method)
                with self._opener(request, timeout=self.timeout) as response:
                    raw = response.read(10 * 1024 * 1024 + 1)
                if len(raw) > 10 * 1024 * 1024:
                    raise ProviderError("Provider response exceeds the 10 MB size limit.")
                try:
                    parsed = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError):
                    raise ProviderError("Provider returned invalid JSON.") from None
                if not isinstance(parsed, dict):
                    raise ProviderError("Provider returned an unexpected JSON structure.")
                return parsed
            except HTTPError as error:
                status = error.code
                error.close()
                if status in {429, 500, 502, 503, 504} and attempt + 1 < attempts:
                    self._sleep(min(0.25 * 2**attempt, 2))
                    continue
                if status in {401, 403}:
                    raise ProviderError(f"Provider authentication or access failed (HTTP {status}). Check the configured API key and permissions.") from None
                if status == 429:
                    raise ProviderError("Provider rate limit reached (HTTP 429). Try again later or check your quota.") from None
                raise ProviderError(f"Provider request failed (HTTP {status}).") from None
            except (URLError, TimeoutError, ConnectionError, OSError):
                if attempt + 1 < attempts:
                    self._sleep(min(0.25 * 2**attempt, 2))
                    continue
                raise ProviderError("Provider could not be reached within the request limits. Check your connection and retry.") from None
            except ValueError:
                raise ProviderError("Provider request configuration is invalid.") from None


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _integer(value, minimum=0, maximum=10**12):
    return value if type(value) is int and minimum <= value <= maximum else None


def _url(value) -> str:
    value = _text(value)
    try:
        parts = urlsplit(value)
        return value if parts.scheme in {"http", "https"} and parts.netloc else ""
    except ValueError:
        return ""


def _doi(value):
    value = _text(value).lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    return value if len(value) <= 2048 and re.fullmatch(r"10\.\d{4,9}/\S+", value) else None


def _issn(value):
    value = _text(value).replace("-", "").upper()
    if not re.fullmatch(r"\d{7}[\dX]", value):
        return None
    digits = [int(n) for n in value[:7]] + [10 if value[-1] == "X" else int(value[-1])]
    if sum(digit * weight for digit, weight in zip(digits, range(8, 0, -1))) % 11:
        return None
    return value[:4] + "-" + value[4:]


def _search_args(query, limit, year_from, year_to):
    if not _text(query) or len(query) > 2000:
        raise ProviderError("A search query must contain 1 to 2000 characters.")
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ProviderError("Search result limit must be between 1 and 200.")
    if any(type(year) is not int for year in (year_from, year_to)) or not 1900 <= year_from <= year_to <= 2100:
        raise ProviderError("Search years must be ordered and between 1900 and 2100.")


def _abstract(inverted) -> str:
    if not isinstance(inverted, dict):
        return ""
    words = {}
    for word, positions in list(inverted.items())[:20000]:
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions[:20000]:
            if type(position) is int and 0 <= position < 20000:
                words[position] = word
    return " ".join(words[position] for position in sorted(words))


class OpenAlexProvider:
    endpoint = "https://api.openalex.org/works"

    def __init__(self, client=None, api_key=None):
        self.client = client or JsonHttpClient()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY", "")

    def search(self, query, limit=10, year_from=2015, year_to=2026) -> list[dict]:
        _search_args(query, limit, year_from, year_to)
        params = {"search": query.strip(), "per-page": limit, "filter": f"publication_year:{year_from}-{year_to}"}
        if self.api_key:
            params["api_key"] = self.api_key
        payload = self.client.get(self.endpoint, params=params)
        if "error" in payload or not isinstance(payload.get("results"), list):
            raise ProviderError("OpenAlex returned an error or an unexpected result structure.")
        retrieved = _now()
        papers = []
        for item in payload["results"][:limit]:
            if not isinstance(item, dict):
                continue
            title = _text(item.get("title")) or _text(item.get("display_name"))
            if not title:
                continue
            location = item.get("primary_location") or {}
            location = location if isinstance(location, dict) else {}
            venue = location.get("source") or {}
            venue = venue if isinstance(venue, dict) else {}
            authors = []
            for authorship in item.get("authorships", []) if isinstance(item.get("authorships"), list) else []:
                author = authorship.get("author") if isinstance(authorship, dict) else None
                if isinstance(author, dict) and _text(author.get("display_name")):
                    authors.append(author["display_name"].strip())
            doi = _doi(item.get("doi"))
            source_url = _url(item.get("id"))
            issns = venue.get("issn") if isinstance(venue.get("issn"), list) else []
            papers.append({
                "id": source_url or (f"doi:{doi}" if doi else f"openalex:{len(papers)}:{title}"),
                "title": title, "authors": authors,
                "year": _integer(item.get("publication_year"), 1000, 2100),
                "doi": doi,
                "url": _url(location.get("landing_page_url")) or (f"https://doi.org/{doi}" if doi else source_url),
                "abstract": _abstract(item.get("abstract_inverted_index")),
                "venue": _text(venue.get("display_name")),
                "issns": list(dict.fromkeys(normalized for value in issns if (normalized := _issn(value)))),
                "citation_count": _integer(item.get("cited_by_count")),
                "citation_source": "OpenAlex cited_by_count",
                "citation_as_of": retrieved[:10], "source": "OpenAlex",
                "source_url": source_url, "retrieved_at": retrieved,
                "is_retracted": item.get("is_retracted") is True, "metrics": None,
            })
        return papers


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _strip_tags(value):
    parser = _PlainText()
    parser.feed(_text(value))
    return " ".join(" ".join(parser.parts).split())


class CrossrefProvider:
    endpoint = "https://api.crossref.org/works"

    def __init__(self, client=None):
        self.client = client or JsonHttpClient()

    def search(self, query, limit=10, year_from=2015, year_to=2026) -> list[dict]:
        _search_args(query, limit, year_from, year_to)
        params = {"query.bibliographic": query.strip(), "rows": limit, "filter": f"from-pub-date:{year_from}-01-01,until-pub-date:{year_to}-12-31"}
        payload = self.client.get(self.endpoint, params=params)
        message = payload.get("message")
        if payload.get("status") != "ok" or not isinstance(message, dict) or not isinstance(message.get("items"), list):
            raise ProviderError("Crossref returned an error or an unexpected result structure.")
        papers = []
        retrieved = _now()
        for item in message["items"][:limit]:
            if not isinstance(item, dict):
                continue
            titles = item.get("title")
            title = _text(titles[0]) if isinstance(titles, list) and titles else ""
            doi = _doi(item.get("DOI"))
            if not title or not doi:
                continue
            authors = []
            for author in item.get("author", []) if isinstance(item.get("author"), list) else []:
                if isinstance(author, dict):
                    name = " ".join(filter(None, (_text(author.get("given")), _text(author.get("family"))))) or _text(author.get("name"))
                    if name:
                        authors.append(name)
            year = None
            for field in ("published", "published-print", "published-online", "issued"):
                date = item.get(field)
                dates = date.get("date-parts") if isinstance(date, dict) else None
                if isinstance(dates, list) and dates and isinstance(dates[0], list) and dates[0]:
                    year = _integer(dates[0][0], 1000, 2100)
                    if year is not None:
                        break
            venues = item.get("container-title")
            issns = item.get("ISSN") if isinstance(item.get("ISSN"), list) else []
            papers.append({
                "id": f"doi:{doi}", "title": title, "authors": authors, "year": year,
                "doi": doi, "url": _url(item.get("URL")) or f"https://doi.org/{doi}",
                "abstract": _strip_tags(item.get("abstract")),
                "venue": _text(venues[0]) if isinstance(venues, list) and venues else "",
                "issns": list(dict.fromkeys(normalized for value in issns if (normalized := _issn(value)))),
                "citation_count": _integer(item.get("is-referenced-by-count")),
                "citation_source": "Crossref is-referenced-by-count",
                "citation_as_of": retrieved[:10], "source": "Crossref",
                "source_url": f"https://api.crossref.org/works/{doi}", "retrieved_at": retrieved,
                "is_retracted": False, "metrics": None,
            })
        return papers


class SerpAPIScholarProvider:
    endpoint = "https://serpapi.com/search.json"

    def __init__(self, client=None, api_key=None):
        self.client = client or JsonHttpClient()
        self.api_key = api_key if api_key is not None else os.environ.get("SERPAPI_API_KEY", "")

    def search(self, title) -> dict:
        if not self.api_key:
            raise ProviderError("Google Scholar verification requires a SERPAPI_API_KEY.")
        if not _text(title) or len(title) > 2000:
            raise ProviderError("A Scholar title must contain 1 to 2000 characters.")
        payload = self.client.get(self.endpoint, params={"engine": "google_scholar", "q": '"' + title.strip().replace('"', "") + '"', "num": 5, "hl": "en", "api_key": self.api_key})
        metadata = payload.get("search_metadata")
        status = metadata.get("status") if isinstance(metadata, dict) else None
        # SerpAPI can describe a completed empty search in its `error` field.
        # Only its exact documented no-results message is accepted as empty;
        # quota, CAPTCHA and unexpected errors remain unavailable.
        if status == "Success" and payload.get("error") == "Google hasn't returned any results for this query.":
            return {**{key: value for key, value in payload.items() if key != "error"}, "organic_results": []}
        if "error" in payload or status in {"Error", "Failed", "Processing", "Queued"}:
            raise ProviderError("The Scholar search provider could not complete verification. Check its service status and your quota.")
        if "organic_results" in payload and not isinstance(payload["organic_results"], list):
            raise ProviderError("The Scholar search provider returned an unexpected result structure.")
        # A successful empty result is distinct from an unavailable provider.
        if "organic_results" not in payload and status != "Success":
            raise ProviderError("The Scholar search provider returned an incomplete response.")
        return payload if "organic_results" in payload else {**payload, "organic_results": []}


def load_impact_factors(path) -> dict[str, dict]:
    """Load licensed/user-supplied JIF rows; newest year wins for each ISSN.

    CSV columns or JSON list keys: issn, impact_factor, year, source.
    Same-year conflicting rows fail rather than choosing arbitrarily.
    """
    try:
        target = Path(path)
        raw = target.read_text(encoding="utf-8-sig")
        if target.suffix.lower() == ".csv":
            rows = list(csv.DictReader(io.StringIO(raw)))
        elif target.suffix.lower() == ".json":
            rows = json.loads(raw)
        else:
            raise ProviderError("Impact-factor data must be a CSV or JSON file.")
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ProviderError("Impact-factor data could not be read as a CSV or JSON file.") from None
    if not isinstance(rows, list):
        raise ProviderError("Impact-factor JSON must contain a list of metric records.")
    metrics = {}
    for index, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict):
                raise ValueError
            issn = _issn(row.get("issn"))
            raw_value, raw_year = row.get("impact_factor"), row.get("year")
            if isinstance(raw_value, bool) or isinstance(raw_year, bool):
                raise ValueError
            value = float(raw_value)
            year = int(raw_year)
            if isinstance(raw_year, float) and raw_year != year:
                raise ValueError
            source = _text(row.get("source"))
            if not issn or not math.isfinite(value) or value < 0 or not 1900 <= year <= 2100 or not source:
                raise ValueError
        except (ValueError, TypeError, OverflowError):
            raise ProviderError(f"Invalid impact-factor record at row {index}; require a valid ISSN, finite nonnegative JIF, year, and source.") from None
        metric = {"impact_factor": value, "year": year, "source": source, "issn": issn}
        previous = metrics.get(issn)
        if previous and previous["year"] == year and previous != metric:
            raise ProviderError(f"Conflicting impact-factor records for the same ISSN and year at row {index}.")
        if not previous or year > previous["year"]:
            metrics[issn] = metric
    return metrics


def attach_impact_factor(paper, metrics) -> dict:
    result = copy.deepcopy(paper)
    matches = [metrics[normalized] for value in paper.get("issns", []) if (normalized := _issn(value)) in metrics]
    result["metrics"] = copy.deepcopy(max(matches, key=lambda metric: metric["year"])) if matches else None
    return result


def _normalized(value) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", _text(value)).casefold()))


def _same_without_doi(left, right) -> bool:
    if not _normalized(left.get("title")) or _normalized(left.get("title")) != _normalized(right.get("title")):
        return False
    if left.get("year") is None or left.get("year") != right.get("year"):
        return False
    left_authors = {_normalized(name) for name in left.get("authors", []) if _normalized(name)}
    right_authors = {_normalized(name) for name in right.get("authors", []) if _normalized(name)}
    return bool(left_authors & right_authors)


def _merge(left, right):
    # Keep the original citation count and its attribution together. A different
    # index's larger count is not automatically a better measurement.
    for key, value in right.items():
        if key not in {"citation_count", "citation_source", "citation_as_of", "sources"} and left.get(key) in (None, "", []):
            left[key] = copy.deepcopy(value)
    if left.get("citation_count") is None and right.get("citation_count") is not None:
        for key in ("citation_count", "citation_source", "citation_as_of"):
            left[key] = right.get(key)
    if len(right.get("abstract", "")) > len(left.get("abstract", "")):
        left["abstract"] = right["abstract"]
    left["issns"] = list(dict.fromkeys(left.get("issns", []) + right.get("issns", [])))
    left["is_retracted"] = bool(left.get("is_retracted") or right.get("is_retracted"))
    left["sources"] = list(dict.fromkeys(left.get("sources", []) + right.get("sources", [])))


def deduplicate(papers) -> list[dict]:
    """Merge equal DOIs; without a DOI require title, year and an author.

    Different DOIs are never merged using a title. Ambiguous matches survive.
    Input ordering establishes citation-source preference; inputs are untouched.
    """
    result = []
    for original in papers:
        paper = copy.deepcopy(original)
        paper["doi"] = _doi(paper.get("doi"))
        paper["sources"] = list(dict.fromkeys(paper.get("sources", []) + ([paper["source"]] if paper.get("source") else [])))
        same_doi = [existing for existing in result if paper["doi"] and existing.get("doi") == paper["doi"]]
        if same_doi:
            _merge(same_doi[0], paper)
            continue
        candidates = [existing for existing in result if _same_without_doi(existing, paper)]
        if len(candidates) == 1 and not (paper["doi"] and candidates[0].get("doi")):
            _merge(candidates[0], paper)
        else:
            result.append(paper)
    return result
