"""Deterministic examples: real bibliographic identities, synthetic citations.

Titles, publication years and arXiv identifiers refer to existing papers.
Abstracts below are short educational descriptions, not quoted abstracts.
No fixture is evidence of a live Google Scholar check or a journal JIF.
"""

from __future__ import annotations

import copy

SNAPSHOT_DATE = "2026-01-01"

DEMO_INPUT = {
    "title": "面向知识密集型问答的检索增强生成可靠性研究",
    "background": "研究如何通过检索增强生成（RAG）改善大语言模型在知识密集型问答中的事实准确性，重点比较稠密检索、检索与生成联合训练、自适应检索以及引用证据评估。希望找到基础方法、强基线、数据集和可复现实验。",
    "keywords": "retrieval augmented generation, knowledge intensive question answering, dense retrieval, factuality",
    "mode": "demo", "planner": "rules", "max_results": 8,
    "year_from": 2015, "year_to": 2026,
    "weights": {"relevance": 60, "citations": 25, "impact_factor": 15},
}


def demo_plan() -> dict:
    return {
        "research_question": DEMO_INPUT["title"],
        "concepts": [
            {"name": "检索增强生成", "terms": ["retrieval augmented generation", "retrieval-augmented", "RAG"], "importance": 5},
            {"name": "知识密集型问答", "terms": ["knowledge intensive", "knowledge-intensive", "question answering", "open-domain"], "importance": 5},
            {"name": "检索方法", "terms": ["dense retrieval", "dense passage", "retriever", "retrieval"], "importance": 4},
            {"name": "事实性与证据", "terms": ["factuality", "factual", "faithfulness", "citation", "evidence"], "importance": 4},
        ],
        "reading_requirements": [
            {"category": "基础方法", "priority": "must", "what_to_extract": "检索器、生成器与联合训练目标；与参数化知识的对照。", "why": "建立 RAG 方法的技术起点和统一术语。"},
            {"category": "强基线与消融", "priority": "must", "what_to_extract": "稀疏与稠密检索、固定与自适应检索，以及 top-k、重排序和上下文长度的消融。", "why": "区分检索质量与生成能力的贡献。"},
            {"category": "数据与评估", "priority": "must", "what_to_extract": "问答数据集、准确率、事实一致性、引用支持度和失败案例。", "why": "将论文主张变成可复现、可比较的实验。"},
            {"category": "复现资源", "priority": "should", "what_to_extract": "代码、模型、语料版本、训练成本与推理延迟。", "why": "评估在有限资源下复现和扩展的可行性。"},
        ],
        "queries": [
            "retrieval augmented generation knowledge intensive question answering",
            "dense passage retrieval open domain question answering",
            "retrieval augmented generation factuality citation evaluation",
        ],
        "inclusion_criteria": ["直接研究检索增强生成、开放域问答或其评估", "包含方法、基线、数据或可验证实验信息"],
        "exclusion_criteria": ["只出现相同关键词但任务和方法无关", "缺乏足够题录信息，无法进行身份核验"],
        "planner": "demo",
        "warnings": ["离线示例使用真实论文题录和人为设置的教学引用数；尚未进行实时 Google Scholar 核验。"],
    }


# The counterexample demonstrates that a large citation count cannot establish
# topical relevance. These hand-written descriptions are not publisher abstracts.
_PAPERS = [
    ("2005.11401", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus"], 2020, "NeurIPS", 3200,
     "Educational description: retrieval augmented generation (RAG) combines a dense retriever with a sequence-to-sequence generator for knowledge intensive question answering. It studies parametric and non-parametric memory, open-domain question answering and factual generation."),
    ("2004.04906", "Dense Passage Retrieval for Open-Domain Question Answering", ["Vladimir Karpukhin", "Barlas Oğuz", "Sewon Min"], 2020, "EMNLP", 2200,
     "Educational description: dense passage retrieval uses a dual-encoder retriever for open-domain question answering. It provides a retrieval baseline and evaluates passage retrieval and downstream question answering with publicly released code."),
    ("2002.08909", "REALM: Retrieval-Augmented Language Model Pre-Training", ["Kelvin Guu", "Kenton Lee", "Zora Tung"], 2020, "ICML", 1800,
     "Educational description: retrieval-augmented language model pre-training jointly learns a knowledge retriever and language representations for open-domain question answering. It studies retrieval from a large text corpus and knowledge-intensive reasoning."),
    ("2007.01282", "Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering", ["Gautier Izacard", "Edouard Grave"], 2021, "EACL", 1600,
     "Educational description: Fusion-in-Decoder combines retrieved passages in a generative question answering model. It evaluates open-domain question answering and the effect of retrieving multiple evidence passages."),
    ("2310.11511", "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection", ["Akari Asai", "Zeqiu Wu", "Yizhong Wang"], 2024, "ICLR", 1200,
     "Educational description: Self-RAG adds adaptive retrieval and self-reflection to retrieval augmented generation. It evaluates question answering, factuality and citation accuracy, using critique tokens to assess retrieved evidence and generated answers."),
    ("2305.14251", "Enabling Large Language Models to Generate Text with Citations", ["Tianyu Gao", "Howard Yen", "Jiatong Yu", "Danqi Chen"], 2023, "EMNLP", 650,
     "Educational description: ALCE evaluates retrieval augmented generation with citations. It measures fluency, correctness and citation quality on knowledge-intensive question answering and examines whether evidence supports factual claims."),
    ("2307.03172", "Lost in the Middle: How Language Models Use Long Contexts", ["Nelson F. Liu", "Kevin Lin", "John Hewitt"], 2024, "TACL", 1400,
     "Educational description: long-context language models show position sensitivity when relevant information occurs in the middle of input. Multi-document question answering and key-value retrieval experiments expose challenges for retrieval augmented generation."),
    ("2312.10997", "Retrieval-Augmented Generation for Large Language Models: A Survey", ["Yunfan Gao", "Yun Xiong", "Xinyu Gao"], 2023, "arXiv preprint", 950,
     "Educational description: a survey of retrieval augmented generation (RAG), including retriever design, indexing, augmentation and generation. It summarizes evaluation, factuality, datasets and research challenges for knowledge intensive question answering."),
    ("1512.03385", "Deep Residual Learning for Image Recognition", ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"], 2016, "CVPR", 9500,
     "Educational description: residual networks make very deep convolutional neural networks easier to optimize for image classification and object detection. This computer vision paper is an intentionally off-topic comparison."),
]


def demo_papers() -> list[dict]:
    papers = []
    for arxiv, title, authors, year, venue, citations, abstract in _PAPERS:
        papers.append({
            "id": f"arxiv:{arxiv}", "title": title, "authors": copy.deepcopy(authors),
            "year": year, "doi": None, "url": f"https://arxiv.org/abs/{arxiv}",
            "abstract": abstract, "venue": venue, "issns": [],
            "citation_count": citations,
            "citation_source": "Synthetic teaching fixture — not a measured citation count",
            "citation_as_of": SNAPSHOT_DATE, "source": "Offline educational fixture (real paper identity)",
            "source_url": f"https://arxiv.org/abs/{arxiv}",
            "retrieved_at": SNAPSHOT_DATE + "T00:00:00+00:00",
            "is_retracted": False, "metrics": None,
        })
    return papers


def demo_scholar_results(paper) -> dict:
    """Schema fixture only. Call verification with demo=True, never as live proof."""
    return {
        "fixture": True,
        "search_metadata": {"status": "Success", "note": "Synthetic fixture; no Google Scholar request occurred."},
        "organic_results": [{
            "title": paper["title"], "link": paper["url"],
            "publication_info": {
                "summary": f"{', '.join(paper['authors'])} - {paper['year']} - {paper['venue']}",
                "authors": [{"name": name} for name in paper["authors"]],
            },
        }],
    }
