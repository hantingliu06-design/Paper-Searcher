# Methodology

## Relevance

For each plan concept, tokenize its name and synonyms. Remove generic research words, then measure the best informative-token coverage in the paper title and abstract. Concept coverage is weighted by importance 1–5. The relevance component is:

`100 × Σ(importance × best_variant_coverage) / Σ importance`

This is lexical evidence. It does not infer meaning, inspect full text, or treat author and venue names as topical evidence.

## Citations and JIF

`citation_score = 100 × ln(1 + min(citations, 10000)) / ln(10001)`

`jif_score = 100 × ln(1 + min(JIF, 50)) / ln(51)`

Requested defaults are 60 / 25 / 15. Missing components are excluded and remaining weights renormalized. Coverage is available requested weight divided by total requested weight. A measured zero remains available. Fixed caps keep scores stable as the candidate pool changes.

JIF is a journal-level metric with a source and year. It is never inferred from a venue string or replaced with CiteScore. The loader rejects invalid ISSNs, negative/non-finite values and conflicting same-year records.

## Verification

The verifier creates an exact-title Scholar query. A candidate needs normalized title similarity ≥0.90 plus either the expected DOI or matching author and year. Conflicting DOI or year metadata vetoes verification. Exact title alone is `ambiguous`; no results is `not_found`; provider errors are `unavailable`; missing provider is `manual_required`; offline fixtures are `demo`.

`verified` means a matching bibliographic record was found. It does not establish the paper's scientific correctness, quality, peer-review status or current retraction state.

## Reproducibility

Every paper retains source URL, retrieval timestamp, citation source/date and verification timestamp. Reports include the generated plan, warnings and per-stage trace. Offline fixtures are pinned to 2026-01-01 and never call a live service. Live runs are necessarily time-dependent; save the exported JSON for a citation-time snapshot.
