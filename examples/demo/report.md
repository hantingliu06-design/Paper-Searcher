# Scholar Compass · Reading report

**Topic:** 面向知识密集型问答的检索增强生成可靠性研究

Mode: **demo** · Run: `1bb5999821e7` · Created: 2026-09-14T09:08:13+00:00

## Scope and limitations

- 离线示例使用固定 RAG 文献集和规则规划，不调用大模型或外部检索。
- 规则规划使用关键词和有限中英词典；复杂研究问题建议使用大模型规划，并人工复核检索词。
- 纳入／排除条件是阅读筛选建议；自动硬过滤仅执行年份和撤稿标记。
- 离线演示：固定 RAG 文献集、合成引用数和示例描述，仅用于复现流程；未进行实时检索或 Google Scholar 核验。
- 部分期刊影响因子缺失或不适用；缺失项不记为零，按可用指标重新分配权重，并显示覆盖率。

## What to read for

围绕“面向知识密集型问答的检索增强生成可靠性研究”，现有方法、实验证据和未解决问题是什么？

- **问题与综述** (must): 寻找对 retrieval augmented generation、knowledge intensive question answering、dense retrieval 的任务定义、发展脉络、研究空白和适用边界。 — 建立研究地图，确定你的问题已被解决到什么程度。
- **方法与基线** (must): 寻找与 retrieval augmented generation、knowledge intensive question answering、dense retrieval 直接相关的核心方法、强基线、架构和训练／推理流程。 — 确认可比较的方法，避免只与弱基线比较。
- **数据与实验** (must): 提取数据集来源、规模、划分、评价指标、对照实验和消融设置。 — 为复现与公平比较确定实验条件。
- **可靠性与失败案例** (must): 寻找统计不确定性、域外测试、负结果、数据泄漏检查与失败案例。 — 识别结论的边界，形成可检验的研究假设。
- **复现资源** (should): 检查代码、数据、参数、依赖版本、算力和许可证是否可获取。 — 评估实现成本和复现可行性。
- **近期改进** (should): 寻找后续工作解决了哪些局限，是否带来可重复的提升。 — 定位你可以贡献的改进点。

## Search plan

- retrieval augmented generation knowledge intensive question answering
- retrieval augmented generation knowledge intensive question answering evaluation
- retrieval augmented generation knowledge intensive question answering survey
- retrieval augmented generation knowledge intensive question answering dense retrieval

### Inclusion guidance

- 发表于 2015–2026 年。
- 与 retrieval augmented generation、knowledge intensive question answering、dense retrieval 至少一个核心概念相关。
- 优先有明确实验设置、可获取全文或复现资源的工作。

### Exclusion guidance

- 已标记为撤稿的记录。
- 仅提及关键词但研究目标无关的论文。
- 缺少可核查书目信息的记录需人工确认。

## Ranked reading list

### 1. Retrieval-Augmented Generation for Large Language Models: A Survey

Yunfan Gao, Yun Xiong, Xinyu Gao · 2023 · arXiv preprint

**Score 83.7/100** · relevance 87.5 · metric coverage 85%

Citations: 950 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2312.10997)

[Paper](https://arxiv.org/abs/2312.10997)

[Google Scholar](https://scholar.google.com/scholar?q=%22Retrieval-Augmented%20Generation%20for%20Large%20Language%20Models%3A%20A%20Survey%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 100% lexical term coverage
- knowledge intensive question answering: 100% lexical term coverage
- dense retrieval: 50% lexical term coverage
- factuality: 100% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: a survey of retrieval augmented generation \(RAG\), including retriever design, indexing, augmentation and generation\. It summarizes evaluation, factuality, datasets and research challenges for knowledge intensive question answering\.

### 2. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

Patrick Lewis, Ethan Perez, Aleksandra Piktus · 2020 · NeurIPS

**Score 78.7/100** · relevance 75.0 · metric coverage 85%

Citations: 3200 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2005.11401)

[Paper](https://arxiv.org/abs/2005.11401)

[Google Scholar](https://scholar.google.com/scholar?q=%22Retrieval-Augmented%20Generation%20for%20Knowledge-Intensive%20NLP%20Tasks%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 100% lexical term coverage
- knowledge intensive question answering: 100% lexical term coverage
- dense retrieval: 100% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: retrieval augmented generation \(RAG\) combines a dense retriever with a sequence-to-sequence generator for knowledge intensive question answering\. It studies parametric and non-parametric memory, open-domain question answering and factual generation\.

### 3. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

Akari Asai, Zeqiu Wu, Yizhong Wang · 2024 · ICLR

**Score 75.6/100** · relevance 75.0 · metric coverage 85%

Citations: 1200 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2310.11511)

[Paper](https://arxiv.org/abs/2310.11511)

[Google Scholar](https://scholar.google.com/scholar?q=%22Self-RAG%3A%20Learning%20to%20Retrieve%2C%20Generate%2C%20and%20Critique%20through%20Self-Reflection%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 100% lexical term coverage
- knowledge intensive question answering: 50% lexical term coverage
- dense retrieval: 50% lexical term coverage
- factuality: 100% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: Self-RAG adds adaptive retrieval and self-reflection to retrieval augmented generation\. It evaluates question answering, factuality and citation accuracy, using critique tokens to assess retrieved evidence and generated answers\.

### 4. Enabling Large Language Models to Generate Text with Citations

Tianyu Gao, Howard Yen, Jiatong Yu, Danqi Chen · 2023 · EMNLP

**Score 64.8/100** · relevance 62.5 · metric coverage 85%

Citations: 650 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2305.14251)

[Paper](https://arxiv.org/abs/2305.14251)

[Google Scholar](https://scholar.google.com/scholar?q=%22Enabling%20Large%20Language%20Models%20to%20Generate%20Text%20with%20Citations%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 100% lexical term coverage
- knowledge intensive question answering: 100% lexical term coverage
- dense retrieval: 50% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: ALCE evaluates retrieval augmented generation with citations\. It measures fluency, correctness and citation quality on knowledge-intensive question answering and examines whether evidence supports factual claims\.

### 5. REALM: Retrieval-Augmented Language Model Pre-Training

Kelvin Guu, Kenton Lee, Zora Tung · 2020 · ICML

**Score 62.2/100** · relevance 54.2 · metric coverage 85%

Citations: 1800 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2002.08909)

[Paper](https://arxiv.org/abs/2002.08909)

[Google Scholar](https://scholar.google.com/scholar?q=%22REALM%3A%20Retrieval-Augmented%20Language%20Model%20Pre-Training%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 67% lexical term coverage
- knowledge intensive question answering: 100% lexical term coverage
- dense retrieval: 50% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: retrieval-augmented language model pre-training jointly learns a knowledge retriever and language representations for open-domain question answering\. It studies retrieval from a large text corpus and knowledge-intensive reasoning\.

### 6. Lost in the Middle: How Language Models Use Long Contexts

Nelson F\. Liu, Kevin Lin, John Hewitt · 2024 · TACL

**Score 58.4/100** · relevance 50.0 · metric coverage 85%

Citations: 1400 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2307.03172)

[Paper](https://arxiv.org/abs/2307.03172)

[Google Scholar](https://scholar.google.com/scholar?q=%22Lost%20in%20the%20Middle%3A%20How%20Language%20Models%20Use%20Long%20Contexts%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 100% lexical term coverage
- knowledge intensive question answering: 50% lexical term coverage
- dense retrieval: 50% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: long-context language models show position sensitivity when relevant information occurs in the middle of input\. Multi-document question answering and key-value retrieval experiments expose challenges for retrieval augmented generation\.

### 7. Dense Passage Retrieval for Open-Domain Question Answering

Vladimir Karpukhin, Barlas Oğuz, Sewon Min · 2020 · EMNLP

**Score 56.9/100** · relevance 45.8 · metric coverage 85%

Citations: 2200 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2004.04906)

[Paper](https://arxiv.org/abs/2004.04906)

[Google Scholar](https://scholar.google.com/scholar?q=%22Dense%20Passage%20Retrieval%20for%20Open-Domain%20Question%20Answering%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 33% lexical term coverage
- knowledge intensive question answering: 50% lexical term coverage
- dense retrieval: 100% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: dense passage retrieval uses a dual-encoder retriever for open-domain question answering\. It provides a retrieval baseline and evaluates passage retrieval and downstream question answering with publicly released code\.

### 8. Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering

Gautier Izacard, Edouard Grave · 2021 · EACL

**Score 47.1/100** · relevance 33.3 · metric coverage 85%

Citations: 1600 · source: Synthetic teaching fixture — not a measured citation count · as of: 2026-01-01

Journal impact factor: N/A; not imputed

Scholar status: **demo** · checked: not checked

[Source record](https://arxiv.org/abs/2007.01282)

[Paper](https://arxiv.org/abs/2007.01282)

[Google Scholar](https://scholar.google.com/scholar?q=%22Leveraging%20Passage%20Retrieval%20with%20Generative%20Models%20for%20Open%20Domain%20Question%20Answering%22)

- Relevance is importance-weighted lexical coverage in title and abstract; synonyms use their best match\.
- retrieval augmented generation: 33% lexical term coverage
- knowledge intensive question answering: 50% lexical term coverage
- dense retrieval: 50% lexical term coverage
- Citation score = 100 × ln\(1 \+ min\(count, 10000\)\) / ln\(10001\)\.
- Journal Impact Factor is missing; its weight is excluded, not treated as zero\.
- Evidence: Offline demonstration; no live Google Scholar verification was performed\.

Educational description: Fusion-in-Decoder combines retrieved passages in a generative question answering model\. It evaluates open-domain question answering and the effect of retrieving multiple evidence passages\.

## Execution trace

- plan / complete: 生成阅读计划；4 个概念，4 条检索式。 (0 ms)
- search / demo: 载入固定示例文献集；编辑查询不会触发真实搜索。 (0 ms)
- rank / complete: 9 篇候选按概念相关性、引用数和可用期刊影响因子排序，保留 8 篇。 (1 ms)
- verify / demo: 核验 8 条记录；真实 Scholar 匹配 0 条。 (0 ms)
