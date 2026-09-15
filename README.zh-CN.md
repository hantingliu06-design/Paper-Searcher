# Scholar Compass · 论文导航 Agent

从论文题目与研究背景出发，形成“应该读什么 → 搜索与评分 → Google Scholar 核验”的完整流程。

[English](README.md) · [架构说明](docs/architecture.md) · [评分与验证规则](docs/methodology.md) · [示例报告](examples/demo/report.md)

## 一分钟体验

安装 Python 3.11 或更高版本，在项目目录运行：

```bash
python3 -m scholar_compass serve
```

打开 [http://localhost:8000](http://localhost:8000)，点击 **运行研究流程**。无需安装额外依赖、配置密钥、搭建数据库或构建前端。

离线模式使用 9 篇真实论文的题录，其中包含 1 篇方向无关的高引用对照论文。引用数是明确标记的教学模拟值，描述是项目编写的概述，没有伪造期刊影响因子，也不会显示“已通过真实 Scholar 验证”。

## 三项任务

1. **生成阅读画像**：根据题目、背景、关键词，建议论文应包含哪些方法、基线、数据集、实验指标、失败案例与复现资源；给出阅读理由和检索式。可在界面先生成计划、修改后再运行。
2. **搜索与透明评分**：接入 Crossref、OpenAlex，去重并按年份筛选；候选不足时最多扩展一轮。根据方向相关性、引用数、期刊影响因子评分，同时展示指标来源、有效权重和缺失情况。
3. **Google Scholar 核验**：通过 SerpAPI 查询 Scholar 记录，比较题目及 DOI，或作者与年份。只有足够证据才标记匹配成功；服务失败和无结果分别处理。

这是有预算限制、可观察的工作流 Agent。可选大模型负责结构化规划；程序控制检索工具、评分公式和验证规则，模型不生成论文列表或自行宣称论文真实存在。规则模式用于无密钥演示和基线比较。

## 真实使用

复制 `.env.example` 为 `.env`，按需要配置并重启服务。在界面切换到 **真实检索**：

| 配置 | 作用 |
| --- | --- |
| 无密钥 | 使用 Crossref 检索，需网络连接。 |
| `OPENALEX_API_KEY` | 扩展检索和摘要、引用元数据。 |
| `OPENAI_API_KEY`、`OPENAI_MODEL` | 启用结构化大模型规划；模型须支持 Structured Outputs。 |
| `SERPAPI_API_KEY` | 自动查询 Google Scholar。没有时提供逐篇人工核验链接。 |
| `IMPACT_FACTOR_FILE` | 指向有来源和年份的 JIF CSV/JSON 文件。 |

JIF 文件字段是 `issn,impact_factor,year,source`，空模板位于 [examples/impact_factors.template.csv](examples/impact_factors.template.csv)。按 ISSN 精确匹配，使用文件中最新年份并显示。项目不附带商业期刊指标数据；将自己的数据放在被 Git 忽略的 `private-data/` 下。

大模型模式会将题目、背景和关键词发送给 OpenAI；文献索引收到检索式；SerpAPI 收到待核验论文题目。密钥保存在服务端，不发给浏览器。导出报告会包含研究输入，请按自己的需要分享。

更换研究方向时，填写新题目、背景和英文关键词即可；复杂中文题目建议使用大模型规划。离线示例始终只检索固定 RAG 数据集，不代表它已联网搜索其他领域。

## 分数该怎么理解

默认权重：相关性 60%、引用数 25%、期刊影响因子 15%。相关性由题目与摘要中的概念词匹配计算；它是可解释的词汇基线，不是语义模型或全文判断。

引用数和 JIF 使用固定对数刻度。缺失 JIF 不当成 0，而是重新分配有效权重；例如只有前两项时，权重变为 70.59% / 29.41%，指标覆盖率为 85%。不同覆盖率的总分需谨慎比较。

影响因子衡量期刊，不代表单篇论文质量；会议论文通常没有 JIF。引用数保留来源与时间，暂未做学科／年份归一化。完整公式见 [方法说明](docs/methodology.md)。

核验成功表示找到了足够匹配的 Scholar 题录，不代表内容结论正确。`not_found` 只表示本次没有匹配，不能证明论文不存在；`unavailable` 表示调用失败；`manual_required` 表示需要人工核验；`demo` 只用于演示。

## 复现与导出

```bash
python3 -m scholar_compass demo --output runs/demo
python3 -m unittest discover -s tests -v
python3 -m evals.run
```

得到完整 JSON、可阅读 Markdown 和 BibTeX 三类文件。界面也支持导出报告。自定义输入见 [examples/topic.json](examples/topic.json)，真实运行前将 `mode` 改为 `live`：

```bash
python3 -m scholar_compass plan --input examples/topic.json --output runs/plan.json
python3 -m scholar_compass run --input examples/topic.json --output runs/research
```

`run` 默认重新生成计划。如果希望使用修改后的计划，将其放入输入 JSON 的 `plan` 字段；界面会自动传递修改后的计划。

## 项目设计

- **易读**：三阶段流程、职责清晰的模块、英文主文档和中文指南。
- **易复现**：零运行时依赖、无密钥演示、命令行输出、GitHub CI。
- **可解释**：评分来源、有效权重、执行轨迹和身份核验依据均可查看。
- **有工程取舍**：明确大模型与确定性规则的边界，处理缺失数据、失败状态、重复记录和验证冲突。
- **可验证**：包含离线回归检查，披露模拟数据和样本规模限制。

可以从 [使用示例](docs/demo-guide.md) 开始，了解计划生成、文献检索、评分和核验流程。源码和示例报告可在 GitHub 上直接阅读；交互后端需要 Python 运行环境，不能部署在纯静态 GitHub Pages 上。

使用真实数据前，建议了解评分公式、身份核验规则和检索预算，并根据自己的研究领域调整关键词与阅读要求。已完成和未验证的内容见 [验证记录](docs/validation.md)。
