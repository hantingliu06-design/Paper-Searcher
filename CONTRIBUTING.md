# Contributing

Run `python -m unittest discover -s tests -v` and `python -m evals.run` before a pull request. Tests and the example run must work without API keys or external network access.

Keep changes small. For a new provider, implement `search(query, limit, year_from, year_to)` and return the normalized paper fields documented in [architecture](docs/architecture.md). Add response-fixture tests for missing metadata, rate limits and malformed responses. Never commit real credentials, private research prompts, or licensed JIF data.

For a scoring change, explain the ranking impact and rerun the labeled evaluation. Do not tune against a single example and describe it as a general benchmark. For matching changes, add both positive and adversarial Scholar examples; reducing false verification matters more than inflating the verified count.

The UI uses no build system. Keep it keyboard-accessible, readable at small widths, and explicit about offline versus live results. Check changes in a browser as well as running `node --check scholar_compass/static/app.js`.

The web server is intended for local use. Proposals for public hosting must include authentication, per-user job isolation, durable storage policy and service quotas.
