# 参考仓库吸收笔记 — 稳定性与安全性（运行时访问控制）

> 基于 4 个参考仓库的并行分析。提取可复用的设计模式，映射到 petfishFramework 架构决策。
> 特别是用户强调的**稳定性**与**安全性（运行时访问控制）**研究成果。

## 仓库价值评级

| 仓库 | 核心价值 | 对架构的影响 |
|---|---|---|
| **agentShield-dev** | 运行时访问控制执行面（实战验证） | 🔴 直接具体化 `permissions/` + Environment 咽喉点 + 审计 |
| **contract-driven-harness-study** | 契约驱动稳定性方法论（实证） | 🔴 直接具体化 `reliability/` + Environment 编译层 + Pass^k |
| **ai_harness_courseware** | 8 层概念架构 + 工具契约 | 🟡 验证模块边界 + Tool Contract schema |
| **AI_All_Courses (az)** | MCP 配置文化 + Harness 治理层 | 🟡 MCP 集成模式 + 治理确定性层 |

---

## 1. 稳定性研究成果（来自 contract-driven-harness-study）

### 核心方法论：契约驱动 = 将可靠性义务外化到显式契约

**关键洞察**：模型是契约系统内的**一个组件**，不是唯一控制源。运行前，harness 将意图**编译**为显式控制对象，模型在边界内运作。

### 六类契约（petfishFramework 应采纳）

| 契约 | 指定什么 | petfishFramework 映射 |
|---|---|---|
| **TaskContract** | 任务类型、允许自主度、成功/失败条件、禁用动作 | `Task` 对象 + `OutputContract` |
| **CapabilityContract** | 技能/工具能做什么、输入输出、权限、依赖 | `Tool` 定义 + 能力声明 |
| **WorkflowContract** | 状态、转换、停止条件、人工检查点 | `ReasoningStrategy` 的图/状态机 |
| **MemoryContract** | 可写/可召回、TTL、主题过滤、冲突解决 | `MemoryView` + `MemorySlice` |
| **OutputContract** | 最终产物结构、必需节、引用策略、格式 | `OutputContract` schema + `ValidatorGate` |
| **VerificationContract** | 如何衡量成功、哪些指标必须通过 | `reliability/` 的评估器 + Pass^k |

### 控制对象（Environment 应编译）

每次运行前，Environment 编译：
- **TaskSpec** — 编译后的任务规范（意图路由 → 边界任务）
- **MemorySlice** — 有界记忆切片（主题过滤 + TTL + 冲突解决）
- **EvidenceBundle** — 证据束（来源标注 + 引用链 + 信任层级）
- **OutputContract** — 输出契约（必需节 + 格式 + 验证规则）
- **TraceLog** — 轨迹日志（每步 + 工具调用 + 事件）

### 稳定性机制（实证验证）

| 机制 | 实证结果 | petfishFramework 应用 |
|---|---|---|
| **机制原子**（单机制测试单元） | 弱模型在 G9 全 harness 下 task_success +0.576 | 每个推理策略/工具有原子级 fixture |
| **Golden/known-bad 夹具** | 本地门必须拒绝 known-bad 才能上线 | 策略/工具的准入门 |
| **冻结-扰动回归** | Stage B v5.4 **40/40** 跨 5 种扰动 | Pass^k = 冻结 TaskSpec 的 k 次重复 + 扰动套件 |
| **修复循环协议** | Stage 7e v1→v4 逐步修复至 4/4 | 失败 → 隔离义务 → 契约更新 → known-bad → 重跑 |
| **已知状态溯源** | state_id + fact + evidence_ids 防压缩 | MemorySlice 的强制字段 |

### 对架构决策 4（可靠性）的丰富

原设计的 Pass^k 现在有了**具体实现路径**：
```
pass_at_k(session_factory, task, k=8, perturbations=[canonical, order_shuffled, alias, paraphrase, distractor])
→ 冻结 TaskSpec + 契约
→ k 次运行（分离 provider 偏差 vs 契约失败）
→ 全部通过 = 准入；否则触发修复循环
```

**弱模型赋能**心态：默认在预算模型 + 全 harness 下跑关键宏；仅契约无法满足时升级到强模型。这是成本控制的实证方法。

---

## 2. 安全性（运行时访问控制）研究成果（来自 agentShield-dev）

### 核心原则

> **不约束模型思想。约束模型行为。**（Do not constrain model thoughts. Constrain model behavior.）

AgentShield 是一个**不可绕过的引用监视器**——每个敏感路径（输入/检索/工具发现/工具调用/工具结果/输出/原始动作）必须流经它。

### SARC 访问控制模型（petfishFramework 应采纳）

**Subject-Action-Resource-Context** 混合 ABAC + RBAC + 风险上下文：

- **Subject**：UserContext（user_id, roles, clearance, projects, tenant_id）
- **Action**：read / call / send / write / delete / export / execute
- **Resource**：classification / project / tags / resource_type
- **Context**：prompt_risk / session_risk / 时间窗

### DecisionEffect（6 种效果，非二元 allow/deny）

```python
class DecisionEffect(Enum):
    ALLOW
    DENY
    MASK              # 返回掩码值 [MASKED:classification]
    PARTIAL_ALLOW     # 仅允许部分参数
    REQUIRE_APPROVAL  # 需人工审批
    DEGRADE           # 降级响应
```

这比二元 allow/deny **强大得多**——支持字段级掩码、部分允许、人工在环、降级。petfishFramework 的 `permissions/` 应直接采纳。

### 两道门工具模型（Environment 咽喉点的具体化）

```
Gate 1 — 可见性（CapabilityProjection）
  Registry ∩ Approved ∩ RiskPolicy ∩ PermissionCheck → 可见工具列表
  无 UserContext → 空列表（fail-closed）

Gate 2 — 调用（ToolCallMonitor.authorize）
  1. 工具已注册？否 → DENY
  2. 工具已启用？否 → DENY
  3. 策略引擎评估；异常 → DENY
  4. 关键风险工具需 approval_required？否 → DENY
  5. 高 prompt_risk → DENY
  6. 字段级 ACL：每个参数检查 classification + required_permission
  7. 决策：ALLOW / PARTIAL_ALLOW / DENY / REQUIRE_APPROVAL
```

**执行**：authorize → executor（http/mcp/sandbox）→ `mask_return_value()` → 结果

### CapabilityGrant 作为审计产物（非内容）

```
RAG_CONTEXT grant → chunk IDs + deny reasons（非 chunk 内容）
TOOL_INVOCATION grant → 允许/拒绝的字段名（非参数值）
OUTPUT_RELEASE grant → 实体类型 + 阻断段（非响应文本）
```

Grant 生命周期：ISSUED → USED → EXPIRED / REVOKED。`GrantStore` 支持回放/可解释性。

### 审计失败 = 安全信号（P0-9）

高风险请求（risk_level HIGH/CRITICAL）的审计写入失败 → 返回**降级拒绝**，而非原答案。系统永远不在「回答用户」和「记录事件」间选择。

### 对架构决策 4（权限）的具体化

原设计的「能力模型 + 按调用策略」现在有了**实战验证的实现**：

| 架构概念 | agentShield 对应 | 采纳 |
|---|---|---|
| Environment 咽喉点 | `SecureChatPipeline` + `ToolCallMonitor` | ✅ 单一不可绕过路径 |
| 决策效果 | `DecisionEffect`（6 种） | ✅ 替代二元 allow/deny |
| 工具可见性门 | `CapabilityProjection` | ✅ 模型不应看到无法使用的工具描述 |
| 工具调用门 | `ToolCallMonitor.authorize` | ✅ 字段级 ACL |
| 审计产物 | `CapabilityGrant` + `GrantStore` | ✅ metadata-only，无内容泄漏 |
| 审计失败处理 | P0-9 高风险降级 | ✅ |
| 凭证隔离 | `CredentialBroker`（scoped HMAC） | ✅ agent 永不持有真实凭证 |
| 降级模式 | full/degraded/sandbox/fail_closed | ✅ 依赖探针驱动 |
| 断路器 | per-provider `CircuitBreaker` | ✅ 身份/LLM/向量库 |

---

## 3. MCP 集成模式（来自 AI_All_Courses + agentShield）

### MCP 作为配置一等公民（非代码）

`opencode.json` 将 MCP server 声明为项目配置——与技能权限、插件并列。这是 petfishFramework 的 MCP-first 落地方式：MCP server 是**插件/扩展面**，通过配置声明，非硬编码。

### 纯 stdlib MCP server 骨架（可行）

`skill-registry` 和 `usage-cost` server 用纯 Python stdlib 实现 stdio MCP（Content-Length/JSONL 自动检测，JSON-RPC 2.0）。**无需 MCP SDK 依赖**。这对 petfishFramework 的内部 MCP 桥接（技能注册、成本跟踪、上下文状态）是可行模式。

### MCP 安全差距 = 差异化机会

AgentShield **仅处理** `tools/list` + `tools/call`。**MCP sampling/elicitation（server 发起的 LLM 调用）完全未被门控**。这是 petfishFramework 的差异化机会：原生门控 MCP sampling/elicitation/roots。

### 条件化 MCP 调用（性能优化）

`fish-trail.md` 展示：系统提示注入的上下文块已提供信息时，**抑制**例行 MCP 调用；仅在用户主动操作或「冷」检索时调用。这降低 token/延迟开销。

---

## 4. 概念架构验证（来自 ai_harness_courseware）

### Agent = Model + Harness

8 层参考架构**验证**了 petfishFramework 的模块边界：
- L1 Task → L2 Entry → L3 Inference → L4 Context/Evidence → L5 Capability/Contract → L6 Control Plane → L7 Action → L8 Governance

petfishFramework 的层蛋糕映射：
| 课程ware 层 | petfishFramework 模块 |
|---|---|
| L1-L2 Task/Entry | `core/`（Task, Session） |
| L3 Inference | `models/` |
| L4 Context/Evidence | `retrieval/` + `memory/` + 契约对象 |
| L5 Capability/Contract | `tools/` + `mcp/` + Tool Contract |
| L6 Control Plane | `core/`（Environment + ReasoningStrategy） |
| L7 Action | `tools/` executors（http/mcp/sandbox） |
| L8 Governance | `permissions/` + `reliability/` + `observability/` |

### 描述面/执行面防火墙

课程ware 的「描述面 vs 执行面防火墙」**= agentShield 的两道门**。两个独立来源验证同一设计：模型看到的工具描述（L5）与工具实际执行（L7）之间必须有确定性门控。

### Tool Contract schema（7 元素）

```
tool_name, version, description, risk_level, requires_approval,
input/output schema, constraints, side_effects, error_semantics
```

这是 petfishFramework `Tool` 定义的具象化。

---

## 5. 对架构开放问题的影响

### 🔴 开放问题 1（最高杠杆）：MCP 语义能否干净吸收 retriever 和 memory？

**现在可以回答**（两个独立来源的证据）：

**答案：不能，也不应该。Retriever 和 memory 应作为契约对象（MemorySlice/EvidenceBundle），非 MCP 工具。**

证据：
1. **contract-driven-harness**：retriever 是 `EvidenceBundle` 的来源，memory 是 `MemorySlice` 的来源——两者是 Environment **编译**的契约对象，非模型调用的工具。模型收到的是编译后的切片，不是原始检索接口。
2. **agentShield**：检索通过 `RetrieverEngine` + `RetrievalConstraint`（max_classification, allowed_projects, top_k）在 pipeline 内门控，**不暴露为工具**。ACL 预过滤 + 检索后审查。
3. **概念上**：MCP 的 resource/tool/prompt 三分法不自然适配「向量检索器」（它是批量召回 + 排序，非单次调用）或「情景记忆」（它是跨试验的状态持久化，非无状态查询）。

**结论**：
- **MCP = 工具契约边界**（仅用于 tools/resources proper）
- **Retriever = 一等 Environment 方法**（`env.retrieve(query) -> list[Snippet]`），后端可插拔（向量/CRAG/Adaptive/GraphRAG），产出 `EvidenceBundle`
- **Memory = 一等 Environment 方法**（`env.memory` -> `MemoryView`），后端可插拔（工作/情景/长期），编译为 `MemorySlice`

**这冻结了 Environment 接口**（原架构决策 3 的接口保持不变，确认正确）。

### 开放问题 2：ReasoningStrategy 能否无特例容纳 LLM+P？

**部分回答**：contract-driven-harness 的 `WorkflowContract`（状态/转换/停止条件）表明，LLM+P 的 PDDL 规划器可作为**确定性 workflow 策略**（state-machine 类），与 bounded agent loop（ReAct/LATS）是两类。Environment 的 `query_model` 足以支持 LLM+P 的 PDDL 翻译步骤。需原型确认。

### 权限模型从「待设计」变为「有实战参考」

原架构决策 4 的权限部分较抽象。现在有 agentShield 的完整实现作参考：
- SARC + DecisionEffect（6 种）
- 两道门（可见性 + 调用）
- 字段级分类
- CapabilityGrant 审计产物
- CredentialBroker 凭证隔离
- 断路器 + 降级模式

### 可靠性从「事件流」扩展为「契约编译 + 事件流 + 准入门」

原设计：事件流 = 审计 + 检查点 + 成本 + 回放。
**新增**：
- Environment 编译契约（TaskSpec/MemorySlice/EvidenceBundle/OutputContract）**在模型运行前**
- Golden/known-bad 夹具作为策略/工具的**准入门**
- Pass^k = 冻结 TaskSpec 的 k 次重复 + 扰动套件（非简单 k 次运行）
- 修复循环协议（失败 → 契约更新 → 重跑）

---

## 6. 综合架构丰富（待更新到 docs/architecture.md）

| 架构决策 | 原设计 | 吸收后丰富 |
|---|---|---|
| 决策 1 Agent+Session | 不变 | Session 现在编译契约对象 |
| 决策 2 MCP 契约 | 不变 | + sampling/elicitation 门控（差异化）+ 条件化调用 |
| 决策 3 Environment | 接口确认正确 | + 契约编译层（TaskSpec/MemorySlice/EvidenceBundle/OutputContract） |
| 决策 4 可靠性 | 事件流 | + 契约编译 + 准入门（golden/known-bad）+ 修复循环 + 扰动套件 |
| 决策 4 权限 | 抽象能力模型 | + SARC + DecisionEffect(6) + 两道门 + 字段级 + Grant 审计 + CredentialBroker + 断路器 |
| 决策 5 瘦核心 | 不变 | permissions/reliability 现在有具象参考实现 |
