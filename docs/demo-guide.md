# 90-second walkthrough

1. Run `python3 -m scholar_compass serve` and open `http://localhost:8000`.
2. Read the sample topic in the left panel. Keep **离线演示** selected and click **生成阅读计划**.
3. Review the concepts, reading requirements and queries. Edit a query to show that the plan is an explicit hand-off between stages.
4. Click **运行研究流程**. The trace changes from planning to search, ranking and verification. The banner says that the results are fixtures.
5. Sort by score or filter by Scholar status. Expand a paper to show its score explanation, matched concepts, citation source and manual-check link.
6. Export Markdown or JSON. Open `examples/demo/report.md` beside the UI to show that the same report is reviewable outside the browser.
7. For a live run, copy `.env.example`, set only the services you need, choose **真实检索**, and explain that `manual_required` and `unavailable` are honest states rather than failed assertions.
