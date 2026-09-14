"""Portable, provenance-preserving report exports."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


def _md(value) -> str:
    return re.sub(r"([\\`*{}\[\]()#+.!|_<>])", r"\\\1", str(value or "").replace("\n", " "))


def _url(value) -> str:
    value = str(value or "")
    try:
        if urlsplit(value).scheme not in ("https", "http"):
            return ""
    except ValueError:
        return ""
    return value.replace(" ", "%20").replace(")", "%29").replace("(", "%28").replace("\n", "").replace("\r", "")


def to_markdown(report: dict) -> str:
    lines = ["# Scholar Compass · Reading report", "", f"**Topic:** {_md(report['input']['title'])}", "",
             f"Mode: **{report['mode']}** · Run: `{report['run_id']}` · Created: {report['created_at']}", "",
             "## Scope and limitations", ""]
    lines.extend(f"- {_md(w)}" for w in report["warnings"])
    lines.extend(["", "## What to read for", "", _md(report["plan"]["research_question"]), ""])
    for item in report["plan"]["reading_requirements"]:
        lines.append(f"- **{_md(item['category'])}** ({item['priority']}): {_md(item['what_to_extract'])} — {_md(item['why'])}")
    lines.extend(["", "## Search plan", ""])
    lines.extend(f"- {_md(query)}" for query in report["plan"]["queries"])
    for label, key in (("Inclusion guidance", "inclusion_criteria"), ("Exclusion guidance", "exclusion_criteria")):
        lines.extend(["", f"### {label}", ""])
        lines.extend(f"- {_md(item)}" for item in report["plan"][key])
    lines.extend(["", "## Ranked reading list", ""])
    for index, paper in enumerate(report["papers"], 1):
        score, verification = paper["score"], paper["verification"]
        metric = paper.get("metrics")
        lines.extend([f"### {index}. {_md(paper['title'])}", "",
                      f"{_md(', '.join(paper['authors']))} · {paper.get('year') or 'year unknown'} · {_md(paper.get('venue'))}", "",
                      f"**Score {score['total']:.1f}/100** · relevance {score['relevance']:.1f} · metric coverage {score['coverage']:.0%}", "",
                      f"Citations: {paper.get('citation_count') if paper.get('citation_count') is not None else 'N/A'} · source: {_md(paper.get('citation_source'))} · as of: {_md(paper.get('citation_as_of'))}", "",
                      f"Journal impact factor: {_md(str(metric['impact_factor']) + ' (' + str(metric['year']) + ', ' + metric['source'] + ')') if metric else 'N/A; not imputed'}", "",
                      f"Scholar status: **{verification['status']}** · checked: {_md(verification.get('checked_at') or 'not checked')}", ""])
        for label, url in (("Source record", paper.get("source_url")), ("Paper", paper.get("url")), ("Google Scholar", verification["scholar_url"]), ("Matched Scholar result", verification.get("matched_url"))):
            if _url(url):
                lines.extend([f"[{label}]({_url(url)})", ""])
        lines.extend(f"- {_md(explanation)}" for explanation in score["explanation"])
        lines.extend(f"- Evidence: {_md(evidence)}" for evidence in verification["evidence"])
        if paper.get("abstract"):
            lines.extend(["", _md(paper["abstract"])])
        lines.append("")
    lines.extend(["## Execution trace", ""])
    lines.extend(f"- {event['stage']} / {event['status']}: {_md(event['detail'])} ({event['duration_ms']} ms)" for event in report["trace"])
    return "\n".join(lines) + "\n"


def _tex(value) -> str:
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "$": r"\$"}
    return "".join(replacements.get(c, c) for c in str(value).replace("\n", " "))


def to_bibtex(report: dict) -> str:
    entries = ["% Scholar Compass export. Check metadata and verification status before citing."]
    for paper in report["papers"]:
        key = "sc" + hashlib.sha256(paper["id"].encode()).hexdigest()[:10]
        fields = {"title": paper["title"], "author": " and ".join(paper["authors"]), "year": paper.get("year"),
                  "howpublished": paper.get("venue"), "doi": paper.get("doi"), "url": _url(paper.get("url")),
                  "note": f"Scholar verification: {paper['verification']['status']}; mode: {report['mode']}"}
        entries.append("@misc{" + key + ",\n" + ",\n".join(f"  {k} = {{{_tex(v)}}}" for k, v in fields.items() if v) + "\n}")
    return "\n\n".join(entries) + "\n"
