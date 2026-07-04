# Search Strategy — LLM Agent SOTA 文献综述

> 系统化检索策略。可复核：数据库、检索式、时间窗口均记录在案。

## 研究问题（RQ）

连接竞品分析发现的工程差距，本综述追问：**学术界是否有比生产框架更先进的方法？**

| RQ | 问题 | 连接的竞品差距 |
|---|---|---|
| RQ1 | 哪些 agent 架构范式（超越 ReAct/graph）在学术上有基准证据？ | 生产框架均用 ReAct 循环/FSM 图 |
| RQ2 | 哪些 RAG 技术（超越向量检索）有实证增益？ | LlamaIndex/Haystack 仅做向量+rerank |
| RQ3 | 哪些规划/推理方法（超越 CoT/ReAct）在基准上显著更优？ | 生产框架无 ToT/GoT/搜索式推理 |
| RQ4 | 哪些工具使用能力（超越 function-calling）已验证但未进生产？ | 生产框架仅做基础 function-calling |
| RQ5 | 学术界识别的最难开放问题是什么？petfishFramework 应针对哪些？ | — |
| RQ6 | **核心**：学术 SOTA 与生产框架之间的 research-to-engineering gap 在哪？ | 综合 |

## 检索策略

### 数据库
| 来源 | 覆盖 | 用途 |
|---|---|---|
| arXiv (cs.CL, cs.AI, cs.MA) | 预印本，最新 | 主要来源（2023-2026 前沿多在 arXiv） |
| Google Scholar | 引用追踪 | 验证引用数、找高被引综述 |
| Semantic Scholar | 语义检索 | 补充关键词检索 |
| Papers With Code | 基准排行榜 | 验证 SOTA 数字 |

> 注：本研究由 librarian agent 通过 web search 执行（arXiv + Scholar），非直接数据库 API。

### 时间窗口
**2023-01 至 2026-07**（ChatGPT 后的 agent 研究爆发期）。少数奠基性工作（如 ReAct 2022、ToolFormer 2023）作为基线纳入。

### 关键词种子

| 主题 | 关键词 |
|---|---|
| 架构 | "LLM agent architecture", "language agent tree search", "LATS", "Reflexion", "multi-agent debate", "self-improving agent", "ADAS", "actor model agent" |
| RAG | "GraphRAG", "Self-RAG", "corrective RAG", "CRAG", "adaptive RAG", "multi-hop retrieval", "speculative RAG", "RAG vs long context" |
| 规划 | "Tree of Thoughts", "ToT", "Graph of Thoughts", "GoT", "LLM+P", "Reasoning via Planning", "RAP", "process reward model", "step verification", "self-consistency", "STaR" |
| 工具 | "tool learning", "ToolFormer", "Gorilla", "tool composition", "API discovery", "web agent", "Mind2Web", "WebArena", "tau-bench", "program of thoughts" |
| 综述/基准 | "LLM agent survey", "agent benchmark", "SWE-bench", "GAIA", "AgentBench", "agent open problems", "agent evaluation" |

### 检索式示例
```
("LLM agent" OR "language agent") AND ("architecture" OR "framework") AND ("benchmark" OR "evaluation")
arXiv: 2023-2026, cs.CL/cs.AI
("retrieval augmented" OR "RAG") AND ("graph" OR "self-reflective" OR "corrective" OR "adaptive")
("tree of thoughts" OR "graph of thoughts" OR "planning" OR "search") AND ("reasoning" OR "agent")
```

### 迭代记录
- 第 1 轮：5 个并行 agent 各负责一个主题簇，广搜 + 定向验证 arXiv ID
- 第 2 轮（如需）：引用追踪（滚雪球）补充遗漏的高被引工作

## 并行研究任务映射

| Task ID | 主题簇 | 对应 RQ | 状态 |
|---|---|---|---|
| bg_4fdb0e0f | Agent 架构（LATS/Reflexion/多智能体/自设计） | RQ1 | 进行中 |
| bg_ffb20fc6 | RAG 前沿（GraphRAG/Self-RAG/CRAG/Adaptive） | RQ2 | 进行中 |
| bg_0894aa9b | 规划与推理（ToT/GoT/LLM+P/PRM/自改进） | RQ3 | 进行中 |
| bg_cf4679e9 | 工具使用（ToolFormer/Gorilla/Web Agents/τ-bench） | RQ4 | 进行中 |
| bg_18250335 | 综述与基准（surveys/SWE-bench/GAIA/开放问题） | RQ5 | 进行中 |

## 方法论约束
- **证据优先**：每篇纳入文献须有实证基准结果（排除纯立场性/观点论文）
- **可验证**：arXiv ID 须核对
- **生产对照**：每个方法须标注「是否已在生产框架实现」——这是 RQ6 的核心
