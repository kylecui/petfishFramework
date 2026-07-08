# 骨架完整性清单（Walking Skeleton Completeness Map）

> 确保 v0.2 架构的每一个承诺在骨架中有对应体现。状态：✅ 实现 / 🔶 stub（接口就位） / 📋 TODO（设计就位，后续实现）。
> Last updated: v0.4.5

## 决策 1：Agent + Session 双层抽象

| 承诺 | 骨架产物 | 状态 |
|---|---|---|
| Agent = 不可变配方（model + reasoning + tools + retriever + memory） | `core/agent.py: Agent` (frozen dataclass) | ✅ |
| Agent.run() 自动创建 Session | `core/agent.py: Agent.run()` | ✅ |
| Agent.session() 显式创建 | `core/agent.py: Agent.session()` | ✅ |
| Session = 事件溯源执行进程 | `core/session.py: Session` | ✅ |
| Session.run(task, budget) -> Result | `core/session.py: Session.run()` | ✅ |
| Session.replay() | `core/session.py: Session.replay()` + `reliability/replay.py` | ✅（AUDIT + RESUME + RERUN 全部实现） |
| 简单路径 5 行 | 测试验证 | ✅ |

## 决策 2：MCP 作为规范工具契约

| 承诺 | 骨架产物 | 状态 |
|---|---|---|
| 唯一 Tool 接口 = MCP 形状 | `core/contracts.py: Tool` (name/description/input_schema/risk_level/capabilities) | ✅ |
| 原生工具包装为 MCP 语义 | `tools/base.py` 包装器 | ✅ |
| MCP client（外部工具发现与调用） | `mcp/client.py: connect_stdio, MCPClient` | ✅ |
| MCP 高级特性（sampling/roots/elicitation） | `mcp/` 模块 | 📋（v0.5+） |
| MCP server mode | `mcp/server.py: serve_as_mcp` | 📋（NotImplementedError stub; v0.5） |
| 泄漏隔离 | 设计文档已记录 | 📋 |

## 决策 3：ReasoningStrategy 可插拔 + Environment 咽喉点

| 承诺 | 骨架产物 | 状态 |
|---|---|---|
| ReasoningStrategy Protocol | `core/contracts.py: ReasoningStrategy` | ✅ |
| run(ctx: RunContext) -> Result | 接口定义 | ✅ |
| Environment Protocol（call/retrieve/query_model/tools） | `core/contracts.py: Environment` | ✅ |
| 咽喉点：所有调用经 Environment | `environment.py: RuntimeEnvironment` 实现 | ✅ |
| 契约编译层（TaskSpec/MemorySlice/EvidenceBundle/OutputContract） | `core/compiled.py` | 🔶（类型就位；编译逻辑 = 最小实现） |
| query_model 暴露给策略 | 接口含 query_model | ✅ |
| Reflexion 是包装器 | `reasoning/reflexion.py` | 📋（接口设计就位；骨架仅 ReAct） |
| 记忆三层 | `core/contracts.py: MemoryView` + `ConversationStore` | 🔶（工作记忆 = 策略内；会话记忆 = ✅；情景/长期 = 📋） |
| 可插拔策略 | ReAct + LATS + LLM+P 实现 + 注册机制 | ✅ |

## 决策 4：可靠性结构性嵌入

| 承诺 | 骨架产物 | 状态 |
|---|---|---|
| Session = 事件溯源（追加只读日志） | `core/events.py: EventEmitter` + `core/session.py` | ✅ |
| 一条流多消费者 | EventEmitter sink 注册（ListSink/ConsoleSink/OTelSink/SIEMSink） | ✅ |
| 检查点与回放 | `Session.checkpoint()` / `reliability/replay.py` | ✅（AUDIT + RESUME + RERUN + 偏离检测） |
| Pass^k 评估器 | `reliability/pass_at_k.py` | ✅（含扰动套件：canonical/order_shuffled/paraphrase/distractor/alias） |
| 成本硬执行 | `reliability/cost.py: CostAccountant` + BudgetExceeded | ✅ |
| SARC + DecisionEffect(6) | `permissions/model.py` | ✅（全部 6 效果在 RuntimeEnvironment 中 enforced） |
| 两道门（可见性 + 调用） | `permissions/gates.py` | 🔶（调用门 ✅ enforced；可见性门 = 📋 v0.5） |
| CapabilityGrant 审计产物 | `permissions/grants.py` | 📋（类型定义；骨架不发射 grant） |
| CredentialBroker | `credentials/broker.py: CredentialBroker` + `ScopedToken` | ✅（含 Vault adapter） |
| 准入门（golden/known-bad） | 测试套件采用此模式 | ✅（测试侧） |
| 修复循环 | — | 📋（运行时机制；骨架不含） |
| 审计失败 = 安全信号 | `core/session.py` 审计写失败处理 | 📋（骨架记录审计；降级逻辑后续） |
| 断路器 + 降级模式 | DEGRADE effect（fallback switching + fail-closed）= ✅；CircuitBreaker = 📋 | 🔶 |
| Retry + Timeout | `reliability/retry.py` + `reliability/timeout.py` | ✅ |
| OTel + SIEM 观测 | `observability/otel_sink.py` + `observability/siem_sink.py` | ✅ |

## 决策 5：瘦核心 + 内指依赖

| 承诺 | 骨架产物 | 状态 |
|---|---|---|
| core/ 纯契约 + 驱动循环 | `core/` 仅依赖 stdlib | ✅ |
| periphery 依赖 core | 所有模块 import core | ✅ |
| 用户可 vendor 最小子集 | 包结构支持 | ✅ |

## 模块存在性（每个架构模块在骨架中有对应）

| 模块 | 骨架 | 状态 |
|---|---|---|
| `core/` | 类型 + 协议 + Agent + Session + events + compiled | ✅ |
| `reasoning/` | ReAct, LATS, LLM+P | ✅（+ Reflexion/ToT/GoT = 📋） |
| `models/` | FakeModel, OpenAIModel, AnthropicModel | ✅ |
| `tools/` | Calculator, WordSorter, AgentAsTool, BaseTool | ✅ |
| `mcp/` | connect_stdio, MCPClient, MCPToolWrapper | ✅（server mode = 📋） |
| `retrieval/` | MemoryRetriever, CRAGRetriever, AdaptiveRetriever | 🔶（lightweight reference implementations） |
| `memory/` | ConversationStore, InMemoryConversationStore | 🔶（会话级 ✅；长期记忆 = 📋） |
| `reliability/` | CostAccountant, Pass^k, Replay, Retry, Timeout, AuditReport | ✅（+ CircuitBreaker = 📋） |
| `permissions/` | DecisionEffect + SARC + DefaultAllow + DenyByDefault + enforcement | ✅（+ CapabilityGrant/visibility gate = 📋） |
| `credentials/` | CredentialBroker + ScopedToken + VaultCredentialSource | ✅ |
| `observability/` | ListSink + ConsoleSink + OTelSink + SIEMSink | ✅ |
| `policies/` | YamlPolicy + PolicyRule + validator + 20 matchers | ✅ |

## 开放问题状态

| 问题 | 骨架处理 |
|---|---|
| ✅ Q1 MCP 吸收 retriever/memory | 已解决；retriever/memory = Environment 方法（非 MCP 工具） |
| ✅ Q2 LLM+P 容纳 | ✅ 已验证：规划器作工具 `env.call()`，接口零变更 |
| ✅ Q3 回放确定性 | ✅ Session 支持 AUDIT 回放 + RESUME 恢复 + RERUN 偏离检测（RecordingEnvironment / ReplayEnvironment / ResumableEnvironment / RerunEnvironment） |

## 测试（TDD — golden/known-bad 准入门）

| 测试 | 类型 | 验证 |
|---|---|---|
| ReAct + FakeModel + calculator 正确回答 | golden | 竖切端到端 |
| Budget 超限 → BudgetExceeded | known-bad | 成本硬执行 |
| 未知工具 → DecisionEffect.DENY | known-bad | 调用门存在 |
| 所有步骤有审计事件 | golden | 事件溯源 |
| Session.replay() 重现轨迹 | golden | AUDIT 回放 |
| RerunEnvironment 偏离检测 | known-bad | RERUN 确定性 |
| SIEMSink redaction（credential + secret keys） | known-bad | 凭据安全 |
| YAML Policy 20 matchers + combinators | golden | 策略引擎 |
| CredentialBroker scoped token injection + revocation | golden | 凭据治理 |
| 305 tests total | — | full suite |
