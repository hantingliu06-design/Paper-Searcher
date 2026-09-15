# 90-second walkthrough

1. Run `python3 -m scholar_compass serve` and open `http://localhost:8000`.
2. Read the sample topic in the left panel. Keep **离线演示** selected and click **生成阅读计划**.
3. Review the concepts, reading requirements and queries. Edit the queries to match your research scope before starting retrieval.
4. Click **运行研究流程**. The trace changes from planning to search, ranking and verification. The banner says that the results are fixtures.
5. Sort by score or filter by Scholar status. Expand a paper to inspect its score explanation, matched concepts, citation source and manual-check link.
6. Export Markdown or JSON to read and process the results outside the browser. A complete sample report is available at `examples/demo/report.md`.
7. For a live run, copy `.env.example`, set only the services you need, and choose **真实检索**. A `manual_required` result needs a manual Scholar check; `unavailable` means the verification service could not complete the request.
