# petfishFramework — 核心架构设计（草案 v0.2）

> Phase 2 核心抽象设计。基于竞品分析（11 框架）+ 文献综述（SOTA 方法）+ Oracle 架构推理。
> **v0.2 吸收**：参考仓库 `agentShield-dev`（运行时访问控制）+ `contract-driven-harness-study`（契约驱动稳定性）的实战研究成果。详见 `docs/research/reference-repos-absorption.md`。
> **状态：待评审** — 核心决策确认后才进入详细 API 设计。
>
> **v0.2 变更摘要**：
> - 决策 3：Environment 新增**契约编译层**（TaskSpec/MemorySlice/EvidenceBundle/OutputContract）
> - 决策 4：可靠性扩展为**契约编译 + 准入门 + 修复循环 + 扰动套件**；权限从抽象能力模型具体化为 **SARC + DecisionEffect(6) + 两道门**
> - 开放问题 1（🔴 MCP 吸收 retriever/memory）**已解决**

## 0. 设计原则（来自调研，非主观偏好）

| 原则 | 证据来源 | 对架构的约束 |
|---|---|---|
| **可靠性 > 峰值准确率** | τ-bench Pass^k（GPT-4o Pass^1 61% vs Pass^8 <25%） | 可靠性必须结构性嵌入，非可选附加 |
| **scaffold 决定分数** | GAIA 同模型 bare vs HAL 差 30pp | 执行基底（Session）必须一等公民 |
| **简洁但有控制力** | 定位图 A 空白带（比 LangGraph 简单，比 OpenAI SDK 有控制力） | 简单路径 5 行起步；高级路径暴露图/搜索 |
| **MCP-first** | 11/11 框架支持 MCP，但无一以 MCP 为核心抽象 | MCP 作为规范工具契约，非内部 RPC |
| **长程规划是首要失败模式** | 所有调查一致 | 显式状态跟踪 + 目标重注意 + 失败重规划 |
| **成本失控是普遍痛点** | GAIA $73-$1686/run | 内置 token/cost 预算硬执行 |
| **工具调用链是新攻击面** | Trustworthy Agent 调查 | 权限/审计/沙箱为一等公民 |

---

## 1. 核心心智模型

> **Agent 是配方（声明）；Session 是执行（可回放、可观测的进程）；Runtime 是驱动引擎。**

```
Agent : Session :: program : OS process
```

- **Agent**（不可变配方）= Model + ReasoningStrategy + Capabilities（tools/retriever/memory）
- **Session**（单次运行的实例）= 事件溯源的执行流，天然可检查点/可回放/可审计/成本计量
- **Runtime** = 驱动 Session 循环、托管事件流的引擎（用户极少直接接触）

**为什么是 Agent+Session 而非 Graph 或纯 Runner：**
- 拒绝 Graph-first（= LangGraph 的选择，放弃「比 LangGraph 简单」的差异定位）
- 拒绝纯 minimal Runner（= OpenAI SDK，控制力不足，无法结构化嵌入可靠性）
- Graph 降级为**一种** ReasoningStrategy（`reasoning="graph"`），非核心
- Session 作为 Process 基底**隐藏** OS 复杂度（用户无需思考「进程身份」），但自动获得检查点/回放/审计

---

## 2. 五个核心架构决策

### 决策 1：Agent + Session 混合抽象（用户面 = 简单；基底 = Process）

```python
@dataclass(frozen=True)
class Agent:                      # 声明 — 不可变配方
    model: ModelRef
    reasoning: ReasoningStrategy = ReAct()
    tools: tuple[Tool, ...] = ()
    retriever: Retriever | None = None
    memory: MemorySpec = MemorySpec()

class Session:                    # 执行 — 单次运行，可变，事件溯源
    def run(self, task: Task, budget: Budget) -> Result: ...
    # 天然：checkpointable, replayable, auditable, cost-metered
```

**简单路径（90% 用例）**：
```python
agent = Agent(model="openai:gpt-4o", tools=[search, calculator])
result = agent.run("What's the population of France?")   # 自动创建 Session
```

**高级路径**：
```python
agent = Agent(model="...", reasoning=LATS(value_fn=my_scorer), tools=[...])
session = agent.session(task, budget=Budget(tokens=50_000))
result = session.run()
replay = session.replay()        # 确定性回放
```

### 决策 2：MCP 作为规范工具契约（非内部 RPC）

**拒绝 MCP 作为内部通信协议**（Agent↔Memory 走 JSON-RPC 会引入序列化开销 + 泄漏风险 + 不匹配推理流需求）。

**「MCP-first」的具体含义（竞品未充分交付的）**：
1. **唯一工具契约** — 框架只有一个 `Tool` 接口，它就是 MCP 形状（name/description/input_schema + MCP 的 resource/prompt/sampling 语义）。原生 Python 工具被包装为 MCP 语义；外部 MCP server 原生消费。无「原生工具 vs MCP 工具」二元性。
2. **MCP 高级特性一等公民** — `resources/`（含订阅）、`sampling`（server 发起 LLM 调用，受权限门控）、`elicitation`、`prompts/` 模板、`roots` 工具集作用域。
3. **MCP 感知编排** — 运行时动态工具发现、按 agent 的 `roots` 限定工具集、按方法权限门控。
4. **泄漏隔离** — `mcp/` 适配模块是**唯一**知道 MCP 线协议的模块。Core 说规范 `Tool` 契约；适配器翻译。MCP 演进时只有 `mcp/` 变。

**MCP 在层蛋糕中的位置**：能力边界接缝（core 与 periphery 之间）。内部 = 类型化 Python 对象；接缝 = MCP 语义。

### 决策 3：ReasoningStrategy 是唯一可插拔轴；工具/RAG/记忆是 Environment 原语

**核心洞察**：策略在「如何搜索」上异构，但在「消费什么」上同构——任务 + 能力面 + 预算 → 轨迹。标准化 I/O，不标准化算法。

```python
class ReasoningStrategy(Protocol):
    name: str
    def run(self, ctx: RunContext) -> Result: ...

@dataclass
class RunContext:
    task: Task
    env: Environment          # 能力面 — 唯一咽喉点
    budget: Budget            # 在此执行，非附加
    memory: MemoryView        # 工作/情景/长期
    events: EventEmitter      # 可观测 + 审计 + 检查点（同一流）

class Environment(Protocol):   # 策略只能通过此访问能力
    def tools(self) -> list[Tool]: ...
    def call(self, ref: ToolRef, args: dict) -> ToolResult: ...     # 权限/成本门控
    def retrieve(self, query: str) -> list[Snippet]: ...
    def query_model(self, req: ModelRequest) -> ModelResponse: ...  # 价值函数/评估器用
```

**关键决策**：
- 工具和 RAG 是 **Environment 原语**，非策略内部。这是可互换性的前提：LATS 和 ReAct 看到相同环境。权限/成本门控集中在唯一咽喉点。
- `query_model` 暴露给策略（LATS 需价值函数，ToT 需评估器）；ReAct 不用它。
- **Reflexion 是包装器/装饰器**，非对等策略：`reasoning=Reflexion(ReAct(), memory=episodic)`。
- **记忆三层**：工作记忆（per-step，策略管理）/ 情景记忆（per-task，Session 持久化，Reflexion 用）/ 长期记忆（跨 Session，MemoryView，类 retriever 能力）。
- 简单路径：默认 `reasoning=ReAct()`；Environment 从 Agent 能力自动构建；用户写 `Agent(model=..., tools=[...])` 即可。

**契约编译层（v0.2 吸收 — 来自 contract-driven-harness-study）**：

Environment 在调用策略 `run()` **之前**，将意图编译为显式控制对象（契约）。模型在边界内运作，不是唯一控制源：

```python
@dataclass
class CompiledContext:          # Environment 编译，传给 RunContext
    task_spec: TaskSpec         # 编译后的任务规范（边界 + 成功条件 + 禁用动作）
    memory_slice: MemorySlice   # 有界记忆切片（主题过滤 + TTL + 冲突解决）
    evidence_bundle: EvidenceBundle  # 证据束（来源 + 引用链 + 信任层级）
    output_contract: OutputContract  # 输出契约（必需节 + 格式 + 验证规则）
```

编译流程：`意图路由 → TaskSpec 编译 → MemorySlice 切片 → EvidenceBundle 召回 → OutputContract 绑定 → 交付策略`。检索和记忆是**契约对象的来源**（`evidence_bundle` 来自 `retrieve()`，`memory_slice` 来自 `memory`），而非模型调用的工具——这直接回答了开放问题 1。

### 决策 4：可靠性结构性嵌入（一条事件流 = 审计 + 检查点 + 成本账 + 回放源）

竞品的可观测性是「附加的」，因为它们没有单一咽喉点。我们有（Environment + EventEmitter）。**Session 设计为事件溯源**，可靠性自然涌现：

1. **Session = 追加只读事件日志**（Event Sourcing）。每步（模型调用、工具调用、检索、权限决策）都是 EventEmitter 上的事件。**一条流，多消费者** — 这就是结构性技巧。快照 = 某点物化状态。
2. **检查点与回放** — 记录每步输入/输出 + seed。回放 = 按序重注入记录的模型/工具输出（视模型为外部非确定源；重执行确定性工具）。失败重启 = 加载快照续跑。直接回应 GAIA scaffold confound：scaffold 质量现在可测、可复现。
3. **Pass^k 评估器**在 `reliability/` 模块，是 Session 之上的**元算子**：`pass_at_k(session_factory, task, k=8, agreement=...)`。**v0.2 吸收**：Pass^k 非简单 k 次运行，而是**冻结 TaskSpec + 契约后的 k 次重复 + 扰动套件**（canonical/order-shuffled/alias/paraphrase/distractor），分离 provider 偏差 vs 契约失败。实证基准：contract-driven-harness Stage B v5.4 达 40/40 跨 5 种扰动。
4. **成本硬执行** — Budget 进入 RunContext；Environment 内的 CostAccountant 在每次 query_model/call/retrieve 累计 tokens/$/time，超限抛 BudgetExceeded（硬）或信号策略（软）。
5. **权限 = SARC 模型 + 6 种 DecisionEffect + 两道门**（v0.2 吸收 — 来自 agentShield-dev，实战验证）：
   - **SARC**（Subject-Action-Resource-Context）：UserContext（roles/clearance/projects/tenant）× Action（read/call/write/execute）× Resource（classification/tags）× Context（risk/session）
   - **DecisionEffect**（替代二元 allow/deny）：`ALLOW | DENY | MASK | PARTIAL_ALLOW | REQUIRE_APPROVAL | DEGRADE`
   - **两道门**：① 可见性门（CapabilityProjection — 模型不应看到无法使用的工具描述）；② 调用门（authorize → executor → sanitize，字段级 ACL：每个参数检查 classification + required_permission）
   - **CapabilityGrant 审计产物**：metadata-only（chunk IDs / 字段名 / 实体类型），**非内容**；GrantStore 生命周期 ISSUED→USED→EXPIRED/REVOKED 支持回放
   - **CredentialBroker**：agent 永不持有真实凭证；签发 scoped HMAC 短期令牌
   - MCP sampling/elicitation（server 发起）走同一调用门 — **这是 agentShield 的差距，petfishFramework 的差异化**
6. **准入门 + 修复循环**（v0.2 吸收 — 来自 contract-driven-harness）：新策略/工具必须有 golden + **known-bad** 夹具；本地门拒绝 known-bad 才能上线。运行失败触发修复循环：`失败 → 隔离缺失义务 → 契约更新 → 加 known-bad → 本地门 → 定向重跑`。
7. **审计失败 = 安全信号**（v0.2 吸收 — agentShield P0-9）：高风险请求（risk_level HIGH/CRITICAL）的审计写入失败 → 返回**降级拒绝**，非原答案。系统永不在「回答用户」和「记录事件」间选择。
8. **断路器 + 降级模式**（v0.2 吸收）：per-provider CircuitBreaker（身份/LLM/向量库）；依赖探针驱动降级模式（full/degraded/sandbox/fail_closed）。

**为什么是结构性的**：EventEmitter 是 Q3 可观测契约**必需的**；检查点是 Q1 Process 基底**必需的**；咽喉点是 Q3 Environment **必需的**。可靠性不是可跳过的模块——它是已做选择的自然涌现。

### 决策 5：瘦核心 + 内指依赖（Ports & Adapters）

`core/` 是**纯契约 + 驱动循环 + 事件流**，无任何具体策略/适配器。用户可只 vendor `core/` + 一个模型适配器 + ReAct + 一个工具，即得可用 agent。所有差异化（LATS、CRAG、Adaptive-RAG、MCP-高级、Pass^k）都是插入式 periphery。

---

## 3. 模块结构（层蛋糕）

依赖方向：**严格内指 → core**。除 `mcp/`→`tools/` 的一个特许横向（因 MCP 即工具契约边界），periphery 不互相依赖，只通过 core 契约。

| 模块 | 职责 | 依赖 | 被依赖 |
|---|---|---|---|
| `core/` | **瘦核心**：Agent, Session, Runtime, RunContext + 契约（ReasoningStrategy, Environment, Tool, Retriever, MemoryView, Budget, EventEmitter, Task/Result/Trajectory）+ 驱动循环 | *无具体*（仅 stdlib） | 一切 |
| `reasoning/` | ReAct, LATS, ToT, LLM+P, Reflexion 包装器, graph(FSM) 策略 | core | 用户代码 |
| `models/` | 模型适配器（OpenAI, Anthropic, local）实现 query_model | core | 用户代码 |
| `tools/` | 原生工具包装器、注册表、sampling/resource 辅助 | core | mcp/ |
| `mcp/` | **唯一知道 MCP 线协议的模块**。规范 Tool ↔ MCP 翻译、动态发现、roots/作用域 | core, tools/ | 用户代码 |
| `retrieval/` | RAG 后端：向量+rerank+HyDE 基线、**CRAG**、**Adaptive-RAG**（调研空白）— 作 Environment.retrieve 实现，产出 EvidenceBundle | core | 用户代码 |
| `memory/` | 工作/情景/长期记忆存储、MemoryView 实现 | core | 用户代码 |
| `reliability/` | pass_at_k（冻结+扰动）、CostAccountant、检查点/回放引擎、预算执行、**准入门（golden/known-bad）+ 修复循环** | core | observability/, 用户代码 |
| `permissions/` | **SARC 模型 + DecisionEffect(6) + 两道门（CapabilityProjection/ToolCallMonitor）+ CapabilityGrant/GrantStore + CredentialBroker + 断路器** | core | （经 core 门控横切） |
| `observability/` | EventEmitter sink：OTel、console、LangSmith 兼容导出 | core | 用户代码 |

---

## 4. 调研方法 → 框架模块映射

| 调研发现（方法/缺口） | 映射模块 | 优先级 |
|---|---|---|
| LATS/ToT/GoT（推理搜索，18× 增益） | `reasoning/` | 🥇 Tier 1 |
| CRAG/Adaptive-RAG（RAG 自适应，+36.6pp） | `retrieval/` | 🥇 Tier 1 |
| Pass^k（可靠性度量） | `reliability/` | 🥇 Tier 1 |
| Reflexion（反思记忆） | `reasoning/`(wrapper) + `memory/` | 🥈 Tier 2 |
| PAL/PoT（代码推理基底） | `reasoning/`(code strategy) | 🥈 Tier 2 |
| LLM+P（符号规划） | `reasoning/` | 🥉 Tier 3 |
| MCP-高级（sampling/roots/elicitation） | `mcp/` | 🥈 Tier 2 |
| Agent-OS 服务（检查点/调度/访问控制） | `core/`(Session) + `reliability/` + `permissions/` | 🥉 Tier 3 |
| GraphRAG | `retrieval/`（后端） | 🥉 Tier 3 |

---

## 5. 待解决的开放问题（需原型验证）

### ✅ 已解决：MCP 语义能否干净吸收 retriever 和 memory？

**答案：不能，也不应该。Retriever 和 memory 是契约对象（EvidenceBundle/MemorySlice）的来源，非 MCP 工具。**

**证据**（两个独立来源）：
1. contract-driven-harness-study：retriever 是 `EvidenceBundle` 来源，memory 是 `MemorySlice` 来源——Environment 编译的契约对象，非模型调用的工具
2. agentShield-dev：检索通过 `RetrieverEngine` + `RetrievalConstraint`（max_classification/allowed_projects/top_k）在 pipeline 内门控，不暴露为工具

**结论**：MCP = 工具契约边界（仅 tools/resources）；retriever/memory = 一等 Environment 方法。**Environment 接口（决策 3）确认正确，已冻结。** 原计划的原型 V1 不再需要。

### ✅ 已解决：ReasoningStrategy.run(ctx)->Result 能否无特例容纳 LLM+P？

**答案：能。规划器作工具（`env.call("planner", ...)`），接口零变更。**

**验证**（V2 原型，16 测试全通过）：
1. **LATS**：搜索循环在 `run()` 内部，通过 `env.query_model()`（策略+价值函数）和 `env.call()`（动作执行）完成。接口零变更。已实现 `reasoning/lats.py`。
2. **LLM+P**：翻译用 `env.query_model()`，规划器作工具用 `env.call("path_planner", ...)`。规划器走咽喉点（审计/预算/权限门控）。已实现 `reasoning/llm_plus_p.py` + `tools/path_planner.py`。
3. **接口兼容性测试**（`test_v2_interface_compatibility.py`）：ReAct、LATS、LLM+P 三策略共用同一冻结 `RunContext`，全部返回 Result，全部经 EventEmitter 发射事件。

### ✅ 已解决：确定性回放的模型非确定性处理

**答案：三种 ReplayMode 显式区分，RecordingEnvironment + ReplayEnvironment 实现，无需修改 core/。**

**验证**（Q3 原型，5 测试全通过）：
1. **AUDIT**（确定性回放）：`RecordingEnvironment` 在首次运行时捕获所有 ModelResponse + ToolResult；`ReplayEnvironment` 重注入这些记录。验证：重放轨迹与原始完全一致。偏离检测：若重放调用数超出记录 → `RuntimeError`。
2. **RERUN**（新鲜运行）：创建全新 Session 重跑。验证：非确定性模型产生不同结果（非确定性正是 Pass^k 度量对象）。
3. **RESUME**（检查点恢复）：`ResumableEnvironment` 在检查点前用记录响应，之后切换到 live env。验证：确定性前缀 + 新鲜后缀，用于失败恢复。

**关键设计决策**：所有回放逻辑在 `reliability/replay.py`（依赖 core/，不反向）。core/ 的 Session 和 Environment **零修改**——RecordingEnvironment 作为 Environment 协议的包装器，符合 Ports & Adapters。

**三个开放问题全部解决。**

---

## 6. 与竞品的定位对照

| 维度 | LangGraph | OpenAI SDK | petfishFramework |
|---|---|---|---|
| 核心抽象 | StateGraph（显式图） | Agent + Runner | **Agent + Session（Process 基底）** |
| 简单路径 | 冗长（需定义节点/边） | 极简 | 极简（5 行） |
| 控制力 | 高（图） | 低 | 高（策略 + 图可选） |
| 推理策略 | 仅 ReAct + 手写图 | 仅 ReAct | **可插拔 react/tot/lats/llm+p** |
| 可靠性 | 手动加 LangSmith | 无 | **结构性（契约编译 + 事件流 + Pass^k 冻结扰动）** |
| 权限/安全 | 无原生 | 无原生 | **SARC + DecisionEffect(6) + 两道门 + Grant 审计** |
| MCP | 适配器附加 | 适配器附加 | **规范工具契约 + sampling/elicitation 门控** |
| 工具模型 | 原生 + MCP 二元 | 原生 + MCP 二元 | **单一 MCP 形状契约** |
| 成本控制 | 日志 | 无 | **硬执行 Budget + 弱模型赋能** |

---

## 7. 下一步

1. **确认核心决策**（本文档 v0.2）— 用户评审 5 决策 + 契约编译层 + SARC 权限模型。
2. ~~原型 V1：MCP 吸收 retriever/memory~~ — **已解决**（开放问题 1 ✅），无需原型。
3. **原型 V2**：ReasoningStrategy 接口对 LATS + LLM+P 的容纳性（开放问题 2 🟡）。
4. 确认后 → 详细 API 设计（`docs/api.md`）+ 同步测试用例（TDD，`tests/`），以 golden/known-bad 夹具为准入基线。
