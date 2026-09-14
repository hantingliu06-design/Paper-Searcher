"""Conservative Google Scholar record matching, with explicit failure states.

Only returned Scholar metadata can produce ``verified``. A search URL or an
exact title without corroborating metadata never establishes verification.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import quote, unquote

TITLE_THRESHOLD = 0.90


def _normal(text: object) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).casefold()
    text = re.sub(r"^\s*\[(?:pdf|html|book|citation)\]\s*", "", text)
    return " ".join(re.findall(r"[^\W_]+", text, flags=re.UNICODE))


def _similarity(left: object, right: object) -> float:
    left_text, right_text = _normal(left), _normal(right)
    if not left_text or not right_text:
        return 0.0
    if left_text == right_text:
        return 1.0
    sequence = SequenceMatcher(None, left_text, right_text, autojunk=False).ratio()
    left_words, right_words = Counter(left_text.split()), Counter(right_text.split())
    dice = 2 * sum((left_words & right_words).values()) / (sum(left_words.values()) + sum(right_words.values()))
    return min(sequence, dice)


def _doi(value: object) -> str | None:
    text = unquote(str(value or "")).strip().casefold()
    match = re.search(r"10\.\d{4,9}/[^\s<>\"?#]+", text)
    if not match:
        return None
    result = match.group(0).rstrip(".,;:")
    while result.endswith(")") and result.count(")") > result.count("("):
        result = result[:-1]
    return result.rstrip("]}")


def _record_dois(record: Mapping) -> set[str]:
    publication = record.get("publication_info")
    publication = publication if isinstance(publication, Mapping) else {}
    values = [record.get("doi"), record.get("link"), publication.get("doi")]
    resources = record.get("resources", [])
    for resource in resources if isinstance(resources, list) else []:
        if isinstance(resource, Mapping):
            values.extend([resource.get("doi"), resource.get("link")])
    return {doi for value in values if (doi := _doi(value))}


def _year(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    text = str(value or "")
    return int(text) if re.fullmatch(r"(?:18|19|20|21)\d{2}", text) else None


def _record_year(record: Mapping) -> tuple[int | None, bool]:
    publication = record.get("publication_info")
    publication = publication if isinstance(publication, Mapping) else {}
    years = {_year(record.get("year")), _year(publication.get("year"))} - {None}
    summary = str(publication.get("summary", ""))
    # Only the publication portion contains a meaningful publication year;
    # snippets may refer to unrelated years or papers.
    if " - " in summary:
        summary = " - ".join(summary.split(" - ")[1:])
    years.update(int(year) for year in re.findall(r"\b((?:18|19|20|21)\d{2})\b", summary))
    if len(years) == 1:
        return years.pop(), False
    return None, len(years) > 1


def _record_authors(record: Mapping) -> list[str]:
    publication = record.get("publication_info")
    publication = publication if isinstance(publication, Mapping) else {}
    authors = publication.get("authors", record.get("authors", [])) or []
    if isinstance(authors, str):
        authors = [authors]
    if not isinstance(authors, list):
        authors = []
    names = []
    for author in authors:
        if isinstance(author, str):
            names.append(author)
        elif isinstance(author, Mapping) and author.get("name"):
            names.append(str(author["name"]))
    summary = str(publication.get("summary", ""))
    if " - " in summary:
        author_segment = summary.split(" - ", 1)[0]
        names.extend(re.split(r",|\s+and\s+|\s*&\s*", author_segment))
    return names


def _author_key(author: str) -> tuple[str, str] | None:
    author = re.sub(r"\bet\s+al\.?", "", author, flags=re.I).replace("…", "")
    # Recognize the common surname, given-name rendering.
    if author.count(",") == 1:
        last, first = author.split(",")
        author = first + " " + last
    tokens = _normal(author).split()
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0], ""
    return tokens[-1], tokens[0]


def _author_overlap(paper: Mapping, record: Mapping) -> bool:
    expected = {_author_key(str(name)) for name in paper.get("authors", []) or []} - {None}
    actual = {_author_key(name) for name in _record_authors(record)} - {None}
    for surname, initial in expected:
        for other_surname, other_initial in actual:
            if surname != other_surname:
                continue
            if initial and other_initial and (
                initial == other_initial or
                (min(len(initial), len(other_initial)) == 1 and initial[0] == other_initial[0])
            ):
                return True
            # A full unspaced Chinese name is stronger than a surname-only
            # Latin match. Latin surname-only metadata is not corroboration.
            if not initial and not other_initial and any("\u3400" <= ch <= "\u9fff" for ch in surname) and len(surname) >= 2:
                return True
    return False


def verify_paper(paper: Mapping, provider=None, demo: bool = False) -> dict:
    """Verify one paper against Scholar through a provider's ``search(title)``.

    A normalized title similarity >= .90 requires either the same DOI, or a
    matching author and publication year. Conflicting DOI/year metadata vetoes
    verification even when other evidence matches. ``verified`` means existence
    of a matching record, not that the paper's claims are correct.
    """
    title = str(paper.get("title", ""))
    result = {
        "status": "manual_required",
        "method": "google_scholar_manual",
        "scholar_url": "https://scholar.google.com/scholar?q=" + quote('"' + title + '"'),
        "matched_title": None,
        "matched_url": None,
        "title_similarity": None,
        "evidence": [],
        "checked_at": None,
    }
    if demo:
        result.update(status="demo", method="offline_fixture", evidence=["Offline demonstration; no live Google Scholar verification was performed."])
        return result
    if provider is None:
        result["evidence"] = ["Google Scholar provider is not configured. Open the Scholar search link to check manually."]
        return result
    result.update(method="google_scholar_serpapi", checked_at=datetime.now(timezone.utc).isoformat())
    try:
        response = provider.search(title)
    except Exception:
        # Provider exceptions can embed API keys or complete request URLs.
        result.update(status="unavailable", evidence=["Google Scholar lookup failed; no verification conclusion can be drawn."])
        return result
    if isinstance(response, Mapping) and not response.get("error") and "organic_results" not in response:
        metadata = response.get("search_metadata")
        information = response.get("search_information")
        success = isinstance(metadata, Mapping) and metadata.get("status") == "Success"
        explicitly_empty = isinstance(information, Mapping) and information.get("organic_results_state") == "Fully empty"
        # SerpAPI may omit organic_results for a completed empty search. A bare
        # missing field remains an incomplete response, never a negative match.
        if success or explicitly_empty:
            response = {**response, "organic_results": []}
    if not isinstance(response, Mapping) or response.get("error") or not isinstance(response.get("organic_results"), list):
        result.update(status="unavailable", evidence=["Google Scholar returned an error or an incomplete response; no verification conclusion can be drawn."])
        return result
    records = [record for record in response["organic_results"] if isinstance(record, Mapping) and isinstance(record.get("title"), str)]
    if response["organic_results"] and not records:
        result.update(status="unavailable", evidence=["Google Scholar result records could not be interpreted."])
        return result
    if not records:
        result.update(status="not_found", evidence=["The completed Google Scholar search returned no records. This is not proof that the paper does not exist."])
        return result
    candidates = sorted(records, key=lambda record: _similarity(title, record.get("title")), reverse=True)
    expected_doi = _doi(paper.get("doi"))
    expected_year = _year(paper.get("year"))
    ambiguous = None
    for record in candidates:
        similarity = _similarity(title, record.get("title"))
        if similarity < TITLE_THRESHOLD:
            continue
        dois = _record_dois(record)
        found_year, year_conflict = _record_year(record)
        doi_match = bool(expected_doi and expected_doi in dois)
        doi_conflict = bool(expected_doi and dois and dois != {expected_doi})
        year_match = expected_year is not None and found_year == expected_year
        year_conflict = year_conflict or (expected_year is not None and found_year is not None and found_year != expected_year)
        author_match = _author_overlap(paper, record)
        evidence = [f"Normalized title similarity: {similarity:.3f} (required ≥ {TITLE_THRESHOLD:.2f})."]
        if doi_match:
            evidence.append("DOI matches the returned Scholar metadata.")
        if doi_conflict:
            evidence.append("DOI conflicts with the candidate paper; verification is rejected.")
        if year_match:
            evidence.append(f"Publication year matches: {expected_year}.")
        if year_conflict:
            evidence.append("Publication year conflicts or is internally inconsistent; verification is rejected.")
        if author_match:
            evidence.append("At least one author matches by surname and first initial, or by full Chinese name.")
        verified = not doi_conflict and not year_conflict and (doi_match or (year_match and author_match))
        if not verified and not doi_conflict and not year_conflict:
            evidence.append("Title alone is insufficient: a matching DOI, or matching author plus year, is required.")
        matched = {
            **result,
            "status": "verified" if verified else "ambiguous",
            "matched_title": record["title"],
            "matched_url": record.get("link") if isinstance(record.get("link"), str) else None,
            "title_similarity": round(similarity, 4),
            "evidence": evidence,
        }
        if verified:
            matched["evidence"].append("A matching Google Scholar record was found; this does not assess research quality or claim correctness.")
            return matched
        if ambiguous is None:
            ambiguous = matched
    if ambiguous is not None:
        return ambiguous
    result.update(status="not_found", evidence=["The completed search returned records, but none met the title similarity threshold. This is not proof of nonexistence."])
    return result
