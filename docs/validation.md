# Validation record

Validated locally on 2026-09-14 with the bundled Python 3.12.14 runtime:

* 62 offline unit tests pass across provider adapters, planner validation, scoring and Scholar matching.
* The offline demo creates JSON, Markdown and BibTeX output for eight displayed papers.
* The labeled evaluation passes four regression checks.
* A live Crossref smoke request was attempted but the restricted environment could not reach the provider. Live adapters are therefore validated with injected response fixtures, not with a current network claim.

Known limits: lexical relevance is intentionally simple; citation counts are not normalized by field or age; JIF requires a user-supplied licensed snapshot; Scholar verification depends on SerpAPI availability; demo descriptions and citation counts are educational fixtures. Browser screenshots are a presentation artifact, not a correctness test.
