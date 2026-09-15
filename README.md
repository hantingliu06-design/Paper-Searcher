<div align="center">

# Scholar Compass

**Know what to read. Understand why it ranks. Inspect the evidence.**

A literature research agent that turns a research question into a reading plan,
searches scholarly indexes, and checks candidate records against Google Scholar.

[中文指南](README.zh-CN.md) · [Architecture](docs/architecture.md) · [Scoring & verification](docs/methodology.md) · [Sample report](examples/demo/report.md)

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Runtime dependencies 0](https://img.shields.io/badge/runtime_dependencies-0-20634B)
![License MIT](https://img.shields.io/badge/license-MIT-20634B)

</div>

## Try it in one minute

From the repository directory, with **Python 3.11+** installed:

```bash
python3 -m scholar_compass serve
```

Open **[localhost:8000](http://localhost:8000)** and choose **运行研究流程**. No installation, API key, database, frontend build, or external asset request is required. The interface is in Chinese; code and architecture documentation are in English.

Prefer a reproducible command-line artifact?

```bash
python3 -m scholar_compass demo --output runs/demo
python3 -m unittest discover -s tests -v
python3 -m evals.run
```

The demo creates `report.json`, `report.md`, and `references.bib`. The [checked-in sample](examples/demo/report.md) provides a complete report you can read without running the application.

**Demo data is explicitly synthetic where it should be:** nine real paper identities, hand-written educational descriptions, illustrative citation counts, no fabricated impact factors, and no claim that a live Scholar check occurred. Demo mode always stays offline, even if credentials exist.

## What the agent does

| Stage | Behavior | Reviewable output |
| --- | --- | --- |
| **1 · Plan** | Converts the title, background and keywords into research concepts, reading requirements and queries. Optional LLM planning uses a validated JSON schema. | What to extract, why it matters, search terms, inclusion/exclusion guidance. |
| **2 · Discover & rank** | Searches Crossref and optionally OpenAlex; inspects recall and expands the search once if needed. Deduplicates, filters years/retraction flags, then ranks. | Component scores, metric coverage, matched concepts, provenance and execution trace. |
| **3 · Verify** | Searches Google Scholar through SerpAPI and conservatively compares title plus DOI or author/year evidence. | Matched record, matching evidence, timestamp and an explicit verification state. |

You can review and edit queries and reading requirements before retrieval, change ranking weights, inspect the evidence, filter results and export the report. The entire workflow is also available through the CLI and local JSON API.

This is a **bounded workflow agent**: a structured planner proposes the search, tools return metadata, and an observation-driven loop expands retrieval within a fixed budget. It does not let the model invent bibliographies or control arbitrary tools. The rules planner is an explicit baseline, not an LLM.

## Use real services

```bash
cp .env.example .env
```

Edit the local `.env`, restart the server, and select **真实检索**. Start with Crossref alone or add services independently:

| Configuration | Enables | Without it |
| --- | --- | --- |
| None | Crossref bibliographic search and available Crossref citation counts | Live search still requires Internet access. |
| `OPENALEX_API_KEY` | OpenAlex discovery, abstracts and citation metadata | Uses Crossref alone. |
| `OPENAI_API_KEY` + `OPENAI_MODEL` | LLM reading-plan generation via Responses + Structured Outputs | Uses the transparent rules planner; select it in the UI. |
| `SERPAPI_API_KEY` | Automated Google Scholar checks | Returns `manual_required` and a Scholar search link. |
| `IMPACT_FACTOR_FILE` | Journal Impact Factors from your own sourced CSV/JSON | JIF is missing, excluded from the weighted mean. |

Choose a model available to your account that supports Structured Outputs. LLM planning sends the title, background and keywords to OpenAI; search sends queries to the selected indexes; verification sends candidate titles to SerpAPI. Credentials stay on the server. The application has no database or analytics; explicit report exports can contain your research context.

JIF input columns are `issn,impact_factor,year,source`; an empty [CSV template](examples/impact_factors.template.csv) is included. Match is by exact ISSN, with the newest supplied metric year displayed. Keep licensed data in `private-data/`, which is ignored by Git. JIF is a journal-level indicator and is **not** inferred from a conference name, substituted with CiteScore, or treated as paper quality.

For a different subject, edit [examples/topic.json](examples/topic.json), set `mode` to `live`, and run:

```bash
python3 -m scholar_compass plan --input examples/topic.json --output runs/plan.json
python3 -m scholar_compass run --input examples/topic.json --output runs/research
```

`run` creates its own plan unless the input JSON contains a reviewed `plan` object. The UI passes the edited plan automatically. Live service failures are reported explicitly; they never trigger a silent substitution with demo results.

## Explainable ranking

Defaults: **60% topic relevance · 25% citations · 15% journal impact factor**.

Relevance is weighted concept-token coverage in the returned title and abstract, using each concept's best synonym. Citation and JIF components use fixed logarithmic scales. Missing metrics are omitted and remaining weights renormalized; metric coverage is shown beside the score. Observed zero is retained.

For example, when JIF is absent, the effective weights are 70.59% relevance and 29.41% citations, with 85% metric coverage. This avoids inventing a value while making incomplete comparisons visible. Citation counts retain their index and retrieval date; counts across indexes, fields and publication ages are not directly comparable.

See [the exact formulas and limitations](docs/methodology.md). This baseline is lexical, not an embedding model, full-text review, or scientific-quality estimate. The included evaluation is a small regression fixture, not evidence of general retrieval quality.

## Verification means a matched record

| State | Meaning |
| --- | --- |
| `verified` | Title similarity ≥ 0.90 plus corroborating DOI, or author **and** year; no conflicting DOI/year. |
| `ambiguous` | Similar title with insufficient or conflicting metadata. |
| `not_found` | A completed search returned no qualifying match; it does not prove nonexistence. |
| `unavailable` | Service error, timeout, malformed response or access issue. |
| `manual_required` | No Scholar service configured. |
| `demo` | Offline illustration; no live verification. |

Google Scholar has no supported public search API for this workflow. The adapter uses SerpAPI; it does not scrape Scholar pages or handle CAPTCHA. A matching record supports bibliographic identity, not correctness, peer-review status, or absence of retraction. Strict checks may leave legitimate preprint/conference year differences ambiguous.

## Project map

```text
scholar_compass/
  planner.py          # Rules baseline + optional structured LLM plan
  workflow.py         # Bounded search loop and observable stage trace
  providers.py        # Crossref / OpenAlex / Scholar / JIF adapters
  scoring.py          # Pure, deterministic scoring functions
  verification.py     # Conservative record matching and evidence
  validation.py       # User and model-output boundary validation
  exports.py          # Markdown / BibTeX reports
  server.py           # Local JSON API and static UI
  static/             # No-build, accessible browser interface
tests/                # Offline unit + integration tests
evals/                # Labeled example evaluation with disclosed limits
examples/             # Reproducible request and committed output
docs/                 # Architecture, methodology, demo walkthrough
.github/workflows/    # Python matrix + package + UI syntax checks
```

The standard-library runtime keeps the first run small and auditable. Optional packaging uses setuptools. A production service would replace the demo HTTP server with a production application server, authenticated job queue, per-user quotas and persistent storage; see [architecture tradeoffs](docs/architecture.md).

## Optional packaging and Docker

```bash
python3 -m pip install .
scholar-compass serve
```

```bash
docker build -t scholar-compass .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env scholar-compass
```

The Docker image runs as a non-root user. Docker requires downloading the Python base image; the plain Python demo does not. Bind this demo to localhost. GitHub Pages cannot run its Python backend; GitHub hosts the source, screenshot and sample report.

## Explore and validate

Start with the [90-second walkthrough](docs/demo-guide.md), read the [architecture decisions](docs/architecture.md), then run the offline tests and [evaluation](evals/README.md). These cover missing JIF, high-citation off-topic papers, ambiguous titles, conflicting metadata and provider failures.

Current validation and remaining gaps are recorded in [docs/validation.md](docs/validation.md). Planned extensions include embedding-based relevance with a labeled benchmark, field/year-normalized citation metrics, saved user reviews, broader domain fixtures and full-text evidence extraction.

[Contributions](CONTRIBUTING.md) are welcome. Source code and original educational descriptions are MIT-licensed; third-party paper metadata and journal metrics retain their respective terms.
