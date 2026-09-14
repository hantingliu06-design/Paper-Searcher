# Evaluation

`python3 -m evals.run` runs a small offline regression check. It verifies four invariants: a relevant RAG paper outranks a high-citation computer-vision control, the control is not first, missing JIF remains visible through coverage, and scores remain within 0–100.

This is a unit-level sanity check, not a benchmark. The fixture has nine papers, hand-written educational descriptions and synthetic citation counts. It does not measure recall, Scholar precision, semantic relevance or scientific quality. A serious extension should add a domain-specific, manually labeled set with a frozen metadata snapshot and report precision@k, recall@k and verification error types.
