# Literature Review — LLM Agent SOTA 与 Research-to-Engineering Gap

> 基于 `literature-matrix.md` 的证据。核心问题（RQ6）：**学术 SOTA 与生产框架之间的差距在哪？petfishFramework 应采用哪些竞品缺失的方法？**

## 1. 研究脉络（Research Threads）

### Thread 1：从 ReAct → 刻意搜索推理

**演进**：ReAct（2022，think-act-observe 循环）→ CoT-SC（多采样投票）→ **ToT**（树搜索+评估器）→ **GoT**（图泛化+聚合）→ **LATS**（MCTS 统一推理+行动+规划+反思）→ **RAP**（世界模型+规划）。

**证据**：ToT 在 24-game 上 **74% vs CoT 4%**（18×）；LATS 在 HotPotQA 上 **0.61 vs ReAct 0.32**；RAP 在 Blocksworld 上 LLaMA-33B 超越 GPT-4 CoT。

**断裂点**：生产框架（LangChain/LlamaIndex/CrewAI/AutoGen）**全部停留在 ReAct**。ToT/GoT/LATS 仅有教程或可选包，无一作为核心原语。这是最显著的 research-to-engineering gap。

### Thread 2：从向量 RAG → 自适应/反思式 RAG

**演进**：朴素向量检索 → HyDE/查询变换（已进生产）→ **GraphRAG**（知识图谱+社区摘要）→ **Self-RAG**（反思 token 控制检索）→ **CRAG**（检索评估器+web 回退）→ **Adaptive-RAG**（复杂度路由）→ **Speculative RAG**（起草-验证）。

**证据**：CRAG 在 PubHealth **+36.6pp**；Adaptive-RAG 多跳 EM +8-9pp 且步数大减；GraphRAG 全面性 72-83% 胜率。

**断裂点**：生产框架（LlamaIndex/Haystack/Dify）已吸收 HyDE/融合检索（🟢），但 **Self-RAG/CRAG/Adaptive-RAG/Speculative RAG 全部缺席**（🔴）。RAG 与长上下文的自动路由也无框架实现。

### Thread 3：从 function-calling → 工具发现与组合

**演进**：ToolFormer（自监督学习工具）→ Gorilla（检索感知训练 1600+ API）→ Chameleon/HuggingGPT（LLM 规划器组合异构工具）→ ToolLLM/AnyTool（16k API 动态发现）→ PAL/PoT（代码作为推理基底）。

**证据**：Gorilla AST **59-84% vs GPT-4 18-39%**；Chameleon ScienceQA **86.54%**；AnyTool 在 16k API 上 **58.2% vs 14%**；PAL GSM8K **+15pp**。

**断裂点**：生产框架仅做**手动注册的 function-calling**。动态 API 发现、自动工具组合、代码作为默认推理基底——全部缺席（🔴）。

### Thread 4：从准确率 → 可靠性（新前沿）

**演进**：单次准确率 → **Pass^k**（k 次一致性）→ 策略合规（τ-bench）→ 成本调整准确率。

**证据**：GPT-4o 在 τ-bench retail **Pass^1 ~61% 但 Pass^8 <25%**；GAIA 同一模型 bare vs scaffolded 差 **~30pp**；所有 8 个主要基准可被 reward-hack 至 ~100%（Berkeley 2026-04）。

**关键洞察**：**可靠性是架构属性，不是模型属性**。同一模型在不同 scaffold 下分数差 30+pp。这直接印证「框架设计是核心机会」。

### Thread 5：Agent-as-OS（基础设施愿景）

**演进**：ad-hoc 编排 → AIOS（LLM 作为 OS，agent 作为进程）→ AgentRM（资源管理器）→ Agent libOS（检查点/谱系）→ Autellix（agent 程序作为一等公民，4-15× 吞吐）。

**意义**：学术共识正在形成——**生产级 agent 可靠性需要 OS 级服务**（调度、内存管理、访问控制、检查点）。这一脉络验证了 petfishFramework 作为「框架」而非「库」的存在价值。

---

## 2. 方法对比（横向比较）

| 能力维度 | 最佳学术方法（证据最强） | 生产实现？ | petfishFramework 差异化潜力 |
|---|---|---|---|
| **复杂推理/规划** | LATS（跨域最强）+ ToT（单域最大增益） | 🔴 缺席 | 高 — 作为可插拔推理策略 |
| **确定性规划** | LLM+P（符号规划器，最优保证） | 🔴 缺席 | 中 — 专域（有 PDDL 时） |
| **RAG 质量** | CRAG（+36.6pp）+ Adaptive-RAG（路由） | 🔴 缺席 | 高 — 模块化 RAG 后端接口 |
| **全局语义** | GraphRAG（KG+社区摘要） | 🟡 partner 包 | 中 — 非默认 |
| **工具可靠性** | Reflexion（反思记忆）+ τ-bench Pass^k | 🔴 缺席 | 高 — 内置可靠性度量 |
| **代码推理** | PAL/PoT（代码作为推理基底） | 🟡 REPL 工具 | 高 — 默认推理基底 |
| **大规模 API** | AnyTool/Gorilla（动态发现） | 🔴 缺席 | 中 — 长期方向 |
| **评估** | Pass^k（一致性） | 🔴 缺席 | 高 — 框架原生评估 |

---

## 3. 研究空白（Research Gaps）— ≥3 类（质量门禁）

### Gap 1：推理策略可插拔性空白（架构层）
**证据**：ToT/GoT/LATS/RAP 有强基准证据，但无生产框架将其作为可切换的推理原语。用户只能在「手写 ReAct」或「手写 ToT 图」间选择，无 `reasoning=strategy` 级抽象。
**gap 性质**：工程空白（方法已验证，缺工程封装）。
**petfishFramework 机会**：提供 `reasoning ∈ {react, tot, lats, llm+p}` 可插拔策略层。

### Gap 2：RAG 自适应路由空白（检索层）
**证据**：Adaptive-RAG（复杂度分类器）、CRAG（检索评估器）、SELF-ROUTE（RAG/LC 路由）均有实证增益，但无生产框架内置查询→策略路由。LlamaIndex/Haystack 需用户手动编排。
**gap 性质**：工程空白 + 需轻量分类器。
**petfishFramework 机会**：内置 RAG 路由器（no-retrieval / single-step / multi-step / web-fallback）。

### Gap 3：可靠性度量空白（评估层）
**证据**：τ-bench 提出 Pass^k，但无生产框架原生支持。所有框架优化单次成功，不测一致性。Berkeley 证明所有基准可被 reward-hack。
**gap 性质**：评估范式空白（非算法空白）。
**petfishFramework 机会**：Pass^k 作为一等评估指标 + 成本/准确率 Pareto 前沿。

### Gap 4：Agent-OS 服务空白（基础设施层）
**证据**：AIOS/AgentRM/Agent-libOS 提出 OS 级服务（调度/内存/检查点/访问控制），但仅 5-6 篇论文，无生产框架实现。长时运行 agent 的状态持久化、检查点、恢复——全部缺失。
**gap 性质**：架构空白（新兴方向）。
**petfishFramework 机会**：框架内建 agent 进程模型（身份/谱系/检查点/能力控制）。

### Gap 5：工具动态发现空白（工具层）
**证据**：Gorilla/AnyTool 验证 16k API 动态发现可行，但生产框架要求手动注册每个工具。MCP 普及使工具发现的技术障碍降低，但无框架做「自动摄取 MCP/OpenAPI → 检索排序 → 验证」。
**gap 性质**：工程空白（技术就绪，缺集成）。
**petfishFramework 机会**：MCP-first 架构天然支持工具动态发现。

---

## 4. Research-to-Engineering Gap 总览（RQ6 核心）

以下方法有**强基准证据**且**完全缺席于生产框架**（🔴）。按 petfishFramework 采用优先级排序：

| 优先级 | 方法 | 证据强度 | 工程难度 | 对 petfishFramework 的价值 |
|---|---|---|---|---|
| 🥇 | **LATS/ToT 可插拔推理** | 极强（18× 增益） | 中 | 旗舰差异化：`reasoning=lats` 一行切换 |
| 🥇 | **Pass^k 可靠性度量** | 强（τ-bench） | 低-中 | 框架原生评估，竞品全部缺失 |
| 🥈 | **CRAG/Adaptive-RAG 路由** | 强（+36.6pp） | 中 | 模块化 RAG 后端 + 自动路由 |
| 🥈 | **Reflexion 反思记忆** | 强（HumanEval 91%） | 中 | 跨试验记忆提升可靠性 |
| 🥈 | **PAL/PoT 代码推理基底** | 强（+15pp） | 低 | 默认推理基底（已有 REPL 基础） |
| 🥉 | **LLM+P 符号规划** | 强（90% vs 15%） | 中 | 专域差异化（确定性保证） |
| 🥉 | **Agent-OS 服务** | 中（理论+早期实证） | 高 | 长期方向（检查点/调度/访问控制） |
| 🥉 | **API 动态发现** | 中（58.2% 仍低） | 高 | MCP-first 架构的长期价值 |

**🟢 已进生产（非差异化）**：HyDE、RAG-Fusion、混合检索、ReAct、function-calling、基本反思模式。

---

## 5. 战略综合：学术界告诉 petfishFramework 什么

### 与竞品分析的交叉验证

竞品分析（`competitor-matrix.md`）发现：MCP 已成标配（非差异化）；真正差距在**简洁性、多语言、中立许可、可靠性**。文献综述**独立验证**了这一点：

- **可靠性是第一开放问题**（所有调查 + 基准一致认同）→ 验证 petfishFramework 应以可靠性为核心
- **可靠性是架构属性，不是模型属性**（scaffold 差 30pp）→ 验证「框架」有独立价值
- **Pass^k / 成本调整准确率是新度量**（竞品全无）→ 差异化机会
- **推理/RAG/工具的学术方法远超生产实现**（大量 🔴）→ 方法集成机会

### petfishFramework 应采用的学术方法（竞品缺失）

**Tier 1（旗舰差异化，强证据 + 缺席 + 可工程化）**：
1. **可插拔推理策略层**（LATS/ToT/LLM+P）— `reasoning=strategy` 抽象
2. **Pass^k 可靠性度量** — 框架原生评估
3. **自适应 RAG 路由**（CRAG/Adaptive/SELF-ROUTE）— 查询→策略自动路由

**Tier 2（高价值，中等难度）**：
4. **Reflexion 反思记忆** — 跨试验错误记忆
5. **PAL/PoT 代码推理基底** — 代码作为默认推理路径
6. **模块化 RAG 后端接口** — 统一接口接任意 RAG（含 GraphRAG）

**Tier 3（长期方向）**：
7. **Agent-OS 服务**（检查点/调度/访问控制）
8. **MCP-first 工具动态发现**

### 设计原则（来自学术开放问题）

文献一致指出以下设计原则，petfishFramework 应内化：

| 原则 | 来源 | 对设计的含义 |
|---|---|---|
| **可靠性 > 峰值准确率** | τ-bench, Berkeley reward-hack | 默认测 Pass^k，不只测单次 |
| **scaffold 决定分数** | GAIA bare vs HAL | 框架质量 = 产品质量 |
| **长程规划是首要失败模式** | 所有调查 | 需显式状态跟踪 + 目标重注意 + 失败重规划 |
| **成本失控是普遍痛点** | GAIA $73-$1686/run | 内置 token/cost 预算护栏 |
| **工具调用链是新攻击面** | Trustworthy Agent 调查 | 工具权限/审计/沙箱为一等公民 |

---

## 6. 结论

学术界在**推理搜索、自适应 RAG、工具发现、可靠性度量**四个方向上显著领先于生产框架。这些方法有强基准证据但工程集成空白——正是 petfishFramework 的差异化空间。

最关键的战略洞察是：**可靠性（而非能力）是新前沿**，且**可靠性是架构属性**。这意味着一个设计良好的框架本身就能创造价值（scaffold 差 30pp），而不只是「包装模型的胶水」。这为 petfishFramework 作为独立框架的存在提供了学术正当性。

**下一步**：将 Tier 1 方法（LATS/ToT 推理策略、Pass^k 度量、自适应 RAG 路由）纳入核心抽象设计（Phase 2），并通过原型验证其工程可行性（V1）。
