# Literature Matrix — LLM Agent SOTA (2023–2026)

> 结构化文献矩阵。生产状态：🟢 已实现 / 🟡 部分实现 / 🔴 学术独有（= research-to-engineering gap）。
> 证据日期 2026-07-03。arXiv ID 已核对。

## 矩阵 A — Agent 架构与编排

| 方法 | 论文 | arXiv / 会议 | 数据集/基准 | 关键指标 | 发现 | 局限 | 生产状态 |
|---|---|---|---|---|---|---|---|
| **LATS** | Language Agent Tree Search | [2310.04406](https://arxiv.org/abs/2310.04406) ICML 2024 | HotPotQA, HumanEval, WebShop | HotPotQA EM 0.61 vs ReAct 0.32；HumanEval 94.4% | MCTS 统一推理+行动+规划+反思，跨域大幅超越 ReAct | 高成本（n=5 展开, k=30-50 轨迹）；需可回溯环境 | 🟡 LangGraph 教程 + LlamaIndex agent 包（非核心原语） |
| **Reflexion** | Verbal Reinforcement Learning | [2303.11366](https://arxiv.org/abs/2303.11366) NeurIPS 2023 | AlfWorld, HumanEval, HotPotQA | AlfWorld 97%；HumanEval 91% vs GPT-4 80% | 语言反思替代权重更新；多次试验累积记忆 | 需多次重试；反思易泛化导致局部最优；需可靠评估器 | 🟡 LangGraph reflection prebuilt + LlamaIndex introspective（非一等公民） |
| **Multi-Agent Debate** | Improving Factuality via Debate / Encouraging Divergent Thinking | [2305.14325](https://arxiv.org/abs/2305.14325) / [2305.19118](https://arxiv.org/abs/2305.19118) | GSM8K, MMLU, Arithmetic, MT | GSM8K +8pp；MMLU +7.2pp；GPT-3.5+MAD 超 GPT-4 | 多智能体辩论提升事实性与推理 | 成本×agents×rounds；收敛不保证；judge 偏同源模型 | 🔴 无框架内置 DebateAgent |
| **Voyager** | Open-Ended Embodied Agent | [2305.16291](https://arxiv.org/abs/2305.16291) TMLR 2024 | Minecraft | 物品×3.3；距离×2.3；科技树×15.3 | 自动课程+技能库+迭代代码生成 | 绑定模拟器；需可执行代码动作空间 | 🔴 仅研究代码 |
| **Generative Agents** | Interactive Simulacra | [2304.03442](https://arxiv.org/abs/2304.03442) UIST 2023 | Smallville 模拟 | 人类评估最可信 | 记忆流+反思+规划架构 | 无数值基准；可扩展性未解 | 🔴 仅研究代码 |
| **ADAS / Meta Agent Search** | Automated Design of Agentic Systems | [2408.08435](https://arxiv.org/abs/2408.08435) ICLR 2025 | DROP, MGSM, MMLU, GPQA | DROP +10.3pp；MGSM +14.4pp；迁移 GSM8K +25.9pp | 元智能体自动编写新 agent 代码并归档最优 | $300-500/run；需沙箱；仅单步任务 | 🔴 仅研究代码 |
| **RAP** | Reasoning via Planning | [2305.14992](https://arxiv.org/abs/2305.14992) EMNLP 2023 | Blocksworld, GSM8K, PrOntoQA | Blocksworld 4-step 0.88 vs CoT ~0；LLaMA-33B+RAP 超 GPT-4 CoT | LLM 同时做世界模型+推理 agent，MCTS 搜索 | 需 log-prob（封闭 API 受阻）；需手设状态/奖励 | 🔴 仅研究库（llm-reasoners） |
| **Tree Search (Koh)** | Tree Search for LM Agents | [2407.01476](https://arxiv.org/abs/2407.01476) 2024 | VisualWebArena, WebArena | VWA +39.7%；WebArena +28% | A* 式搜索在真实 web 环境，多模态价值函数 | 极贵；需价值模型+可回溯模拟器 | 🔴 仅研究代码 |
| **PAR** | From Words to Actions | [2405.19883](https://arxiv.org/abs/2405.19883) ICML 2024 | 理论 | 证明 ε-greedy 给出次线性 regret | Planner-Actor-Reporter 层级 RL 形式化 | 理论性，无任务基准 | 🔴（理论框架，用于设计文档） |

## 矩阵 B — RAG 前沿

| 方法 | 论文 | arXiv / 会议 | 数据集/基准 | 关键指标 | 发现 | 局限 | 生产状态 |
|---|---|---|---|---|---|---|---|
| **GraphRAG** | From Local to Global | [2404.16130](https://arxiv.org/abs/2404.16130) 2024 | 1M-token 语料 | 全面性 72-83% 胜率；多样性 62-82%；根级摘要 -97% token | KG+社区摘要解决全局语义问题 | 索引成本极高（多次 LLM 调用） | 🟡 Microsoft 开源工具；LlamaIndex/LangChain 有 partner 包（非默认） |
| **Self-RAG** | Self-Reflection RAG | [2310.11511](https://arxiv.org/abs/2310.11511) ICLR 2024 | PopQA, TriviaQA, PubHealth, ARC | 13B 超 ChatGPT/Llama2；引用精度大幅提升 | 反思 token 控制检索时机+ grounded 评分 | 需微调模型+反思 token 词表 | 🔴 LlamaIndex SelfRAGPack（非原论文 checkpoint） |
| **CRAG** | Corrective RAG | [2401.15884](https://arxiv.org/abs/2401.15884) 2024 | PopQA, Biography, PubHealth, ARC | PubHealth +36.6pp；PopQA +7pp | T5 检索评估器+web 搜索回退 | 需微调评估器；web 搜索延迟 | 🔴 仅 LangGraph 教程（简化版） |
| **Adaptive-RAG** | Learning to Adapt Retrieval | [2403.14403](https://arxiv.org/abs/2403.14403) NAACL 2024 | MuSiQue, HotpotQA, 2Wiki | 多跳 EM +8-9pp；步数/时间大幅减少 | 查询复杂度分类器路由{无检索/单步/多步} | 需训练分类器；分布偏移风险 | 🔴 仅研究代码 |
| **IRCoT** | Interleaving Retrieval with CoT | [2212.10509](https://arxiv.org/abs/2212.10509) ACL 2023 | HotpotQA, MuSiQue, IIRC | 召回 +21pp；F1 +15pp | 推理↔检索交替，每句推理触发下一检索 | 高延迟（迭代 LLM+检索） | 🔴 无框架内置 |
| **Speculative RAG** | Drafting RAG | [2407.08223](https://arxiv.org/abs/2407.08223) ICLR 2025 | TriviaQA, MuSiQue, PopQA | 精度 +12.97pp；延迟 -11.9~50.8% | 小模型起草+大模型验证 | 需蒸馏 drafter+并行推理 | 🔴 仅研究代码 |
| **HyDE** | Hypothetical Document Embeddings | [2212.10496](https://arxiv.org/abs/2212.10496) ACL 2023 | BEIR | "Best Practices in RAG" 最有效检索 | 生成假设答案再嵌入检索 | 额外 LLM 调用 | 🟢 LlamaIndex/Haystack 内置 |
| **RAG-Fusion** | Multi-query + RRF | [2402.03367](https://arxiv.org/abs/2402.03367) 2024 | — | 混合搜索+rerank 后增益被中和 | 多查询重写+倒数排名融合 | 成本随查询数线性增长 | 🟢 LlamaIndex/Haystack/LangChain 内置融合检索器 |
| **RAG vs Long-Context** | SELF-ROUTE | [2407.16833](https://arxiv.org/abs/2407.16833) 2024 | 多语料 | LC 在密集语料优；RAG 在碎片化优且便宜 23× | "RAG 已死"不成立；混合路由是共识 | — | 🔴 无框架自动 RAG/LC 路由 |

## 矩阵 C — 规划与推理

| 方法 | 论文 | arXiv / 会议 | 数据集/基准 | 关键指标 | 发现 | 局限 | 生产状态 |
|---|---|---|---|---|---|---|---|
| **ToT** | Tree of Thoughts | [2305.10601](https://arxiv.org/abs/2305.10601) NeurIPS 2023 | 24-game, Crosswords, Creative Writing | 24-game 74% vs CoT 4%（18×）；Crosswords 60% vs 0% | 树搜索+LLM 评估器，刻意推理 | 高成本（b=5 → ~100 节点） | 🔴 无框架内置（LangGraph 仅教程） |
| **GoT** | Graph of Thoughts | [2308.09687](https://arxiv.org/abs/2308.09687) AAAI 2024 | Sorting, Set Intersection | 排序误差 -62% vs ToT；成本 -31% | 图泛化 ToT，支持聚合/反馈 | 中高成本 | 🔴 仅学术代码 |
| **LLM+P** | LLM + Classical Planner | [2304.11477](https://arxiv.org/abs/2304.11477) 2023 | Blocksworld, Grippers, Storage | Blocksworld 90% vs 15-20%；Grippers 95% vs 35% | LLM 翻译 PDDL + 经典规划器求最优解 | 需手写 domain PDDL | 🔴 无框架内置 |
| **Plan-and-Solve** | Zero-shot Planning | [2305.04091](https://arxiv.org/abs/2305.04091) ACL 2023 | GSM8K, SVAMP, AQuA | GSM8K +2.9pp；+SC 73.7% vs 70.7% | 先规划再执行，单次调用 | 增益小 | 🟡 可作为 prompt 模板 |
| **Self-Consistency** | Majority Voting | [2203.11171](https://arxiv.org/abs/2203.11171) ICLR 2023 | GSM8K, SVAMP, AQuA | GSM8K +17.9pp | 多采样+多数投票 | k 次采样成本 | 🟡 易手动实现 |
| **PRM** | Step-level Verification | [2305.20050](https://arxiv.org/abs/2305.20050) ICLR 2024 | MATH | best-of-500 达 78.2% | 步级奖励模型验证推理 | 需 PRM800K 标注+训练 | 🔴 无框架内置 |
| **STaR / ReST** | Self-Training Reasoners | [2203.14465](https://arxiv.org/abs/2203.14465) / [2308.08998](https://arxiv.org/abs/2308.08998) | CommonsenseQA, MATH, APPS | CQA 72.5% vs 36.6%；MATH 超人类数据微调 | 生成-过滤-微调迭代自改进 | 需微调基础设施 | 🔴 需训练，非推理时方法 |

## 矩阵 D — 工具使用

| 方法 | 论文 | arXiv / 会议 | 数据集/基准 | 关键指标 | 发现 | 局限 | 生产状态 |
|---|---|---|---|---|---|---|---|
| **ToolFormer** | Self-Supervised Tool Learning | [2302.04761](https://arxiv.org/abs/2302.04761) NeurIPS 2023 | LAMA, ASDiv, SVAMP | GPT-J 6.7B 超 GPT-3 175B | 自监督学习工具调用时机 | 需微调；已被 function-calling 超越 | 🔴 需训练 |
| **Gorilla** | Massive API LLM | [2305.15334](https://arxiv.org/abs/2305.15334) NeurIPS 2024 | APIBench (1600 APIs) | AST 59-84% vs GPT-4 18-39%；幻觉 5-11% vs 37-79% | 检索感知训练（RAT）适配文档变更 | 需 SFT on API 语料 | 🔴 仅研究项目 |
| **Chameleon** | Compositional Reasoning | [2304.09842](https://arxiv.org/abs/2304.09842) NeurIPS 2023 | ScienceQA, TabMWP | ScienceQA 86.54%（+11.37pp）；TabMWP 98.78% | LLM 规划器自动组合异构工具为程序 | 中高成本 | 🔴 无框架内置 |
| **HuggingGPT** | LLM as Controller | [2303.17580](https://arxiv.org/abs/2303.17580) NeurIPS 2023 | HF Hub 任务 | 规划 F1 67-71%；端到端成功 63% | 任务规划→模型选择→执行→响应 DAG | 延迟高；依赖 Hub 描述质量 | 🔴 无框架内置 |
| **ToolLLM / AnyTool** | Large-scale API Discovery | [2307.16789](https://arxiv.org/abs/2307.16789) / [2402.04253](https://arxiv.org/abs/2402.04253) ICML 2024 | ToolBench (16k APIs) | AnyTool 58.2% vs ToolLLM 22.9%；AnyToolBench 73.8% vs 14% | 层级检索+求解器+反思，处理数千 API | 准确率仍低；需大规模 API 索引 | 🔴 无框架内置动态发现 |
| **PAL / PoT** | Code-as-Reasoning | [2211.10435](https://arxiv.org/abs/2211.10435) ICML 2023 / [2211.12588](https://arxiv.org/abs/2211.12588) TMLR 2023 | GSM8K, GSM-HARD, FinQA | PAL GSM8K 72% +15pp；GSM-HARD +40pp；PoT +8-12pp | 生成代码作为推理轨迹，解释器执行 | 需代码执行环境 | 🟡 LangChain PythonREPL / OpenAI Code Interpreter（非默认推理基底） |
| **Web Agents** | Mind2Web/WebArena/SeeAct/VWA | [2306.06070](https://arxiv.org/abs/2306.06070) / [2307.13854](https://arxiv.org/abs/2307.13854) / [2401.01614](https://arxiv.org/abs/2401.01614) / [2401.13649](https://arxiv.org/abs/2401.13649) | WebArena 74.3% vs human 78%；VWA 36% vs 89% | 真实浏览器自动化；多模态 grounding | 仍远低于人类（尤其视觉） | 🔴 无框架内置浏览器 grounding harness |

## 矩阵 E — 基准 SOTA（2026-07 快照）

| 基准 | arXiv | 2023 基线 | 2026 SOTA | 人类 | 剩余差距 |
|---|---|---|---|---|---|
| SWE-bench Verified | [2310.12931](https://arxiv.org/abs/2310.12931) | 1.96% | **95.5%**（Claude Mythos 5） | ~90% | ~饱和 |
| GAIA（scaffolded） | [2311.12983](https://arxiv.org/abs/2311.12983) | 15% | **74.6%**（Sonnet 4.5+HAL） | ~92% | ~17pp |
| GAIA（bare model） | — | — | **52.3%**（Mythos 5） | ~92% | ~40pp |
| WebArena | [2307.13854](https://arxiv.org/abs/2307.13854) | 14.4% | **74.3%**（WebTactix） | ~78% | ~4pp |
| τ-bench | [2406.12045](https://arxiv.org/abs/2406.12045) | ~46% | **89.2%**（Mythos 5） | — | Pass^k 仍低 |
| AgentBench | [2308.03688](https://arxiv.org/abs/2308.03688) | ~40% | **~73%**（Opus 4.7） | — | — |
| MLE-bench（奖牌率） | [2410.07095](https://arxiv.org/abs/2410.07095) | 16.9% | **~64%** | — | — |

> **关键洞察**：GAIA bare vs scaffolded 差 **~30pp** — scaffold（框架）对分数的影响与模型相当。这直接印证「框架设计是核心机会」。
