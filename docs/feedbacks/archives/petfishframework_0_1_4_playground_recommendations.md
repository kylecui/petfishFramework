# petfishFramework 0.1.4 Playground 实测与发展建议

## 0. 文档目的

本文整理对 `petfishframework==0.1.4` 的 Playground 实测结果与后续发展建议。

重点回答四个问题：

1. `0.1.4` 相比 `0.1.2` 是否有实质进步；
2. 当前框架的先进性在哪里；
3. 当前最严重的问题是什么；
4. 下一阶段应该优先修什么、怎么修、如何对外表述。

本文判断基于：

- PyPI `petfishframework==0.1.4` 项目页；
- GitHub README / API 文档 / CHANGELOG；
- 隔离 Python 环境中的实际安装与运行测试；
- 对核心能力的最小验证，包括 ReAct、FakeModel、Budget、Permission、Replay、Pass^k、MCP stdio、ToolRegistry、Structured Output、Conversation Memory、Async / Streaming、LATS、LLM+P。

---

# 1. 总体结论

`0.1.4` 相比 `0.1.2` 有明显进步。

如果说 `0.1.2` 是：

> 架构方向先进，但工程收口不足的 Alpha framework。

那么 `0.1.4` 可以更准确地描述为：

> 核心 runtime 已经可跑、主要设计主线已经成型的 Alpha framework。

但它仍然不应被宣传为：

> production-ready 的企业级 Agent 安全框架。

原因是：当前已经跨过“能不能跑”的阶段，但进入了更重要的阶段：

> 运行时语义是否正确。

尤其是 PermissionEffect 的执行语义，目前存在 P0 级安全问题。

---

# 2. 一句话评判

建议使用以下表述：

> petfishFramework 0.1.4 已经具备一个轻量 Agent runtime 的基本可运行骨架；它的核心价值不是 Agent 能力多，而是把 Session、Environment、Budget、Permission、Replay、Pass^k 放进了执行路径。但它仍处于 Alpha 阶段，尤其需要修复非 ALLOW 权限效果的 pre-execution enforcement 语义。

更短版本：

> 0.1.4 已经从“架构想法不错的 Alpha”进化为“核心 runtime 可跑的 Alpha”，但还不是 production-ready 的企业 Agent 安全框架。

---

# 3. Playground 实测摘要

## 3.1 测试结果总览

| 能力 | 0.1.4 实测结果 | 判断 |
|---|---:|---|
| `pip install petfishframework==0.1.4` | 通过 | 包可正常安装 |
| `import petfishframework` / 版本号 | 通过，显示 `0.1.4` | 发布有效 |
| Zero-cost quickstart | 通过 | `0.1.2` 的 P0 问题已修 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心 Agent Session 可跑 |
| `model="openai:gpt-4o-mini"` shorthand | 具备 resolver 逻辑 | `0.1.2` 的字符串模型问题已修 |
| Budget hard limit | 通过 | 可触发 `BudgetExceeded` |
| Permission `DENY` | 通过 | Deny 会阻断工具执行 |
| Permission `MASK` | 部分可用，但存在语义风险 | 当前更像 post-processing |
| Permission `REQUIRE_APPROVAL` | 发现严重问题 | 工具先执行，再标记 denied |
| `session.replay()` | 通过 | event log 可用 |
| `pass_at_k_with_perturbations` | 通过 | 可靠性测试可跑 |
| Structured output 到 dataclass | 通过 | 可解析 JSON 到 dataclass |
| Conversation memory | 通过 | `ConversationStore` 可跨 session 记录 |
| Async run | 通过 | `run_async()` 可跑 |
| Streaming | 通过 | FakeModel 可 stream chunks |
| LATS scenario | 通过 | 简化搜索链路可跑 |
| LLM+P scenario | 通过 | symbolic planner 链路可跑 |
| MCP stdio client | 通过 | 可连接本地最小 MCP JSON-RPC server |
| ToolRegistry | 通过 | 自动工具选择可跑，但示例需更清晰 |

---

# 4. 0.1.4 的主要进步

## 4.1 Quickstart 已经修到可运行

`0.1.2` 最大的问题之一是 Quickstart 与真实 API 不一致，导致用户复制示例后直接失败。

`0.1.4` 已经将第一段 Quickstart 改为零成本版本，使用：

- `FakeModel.script_tool_then_answer()`
- `ReAct()`
- `Calculator()`

该路径可以直接跑通。

这是一项关键修复，因为新用户对框架的第一判断通常来自 Quickstart。如果第一段代码失败，后续所有架构先进性都会被抵消。

---

## 4.2 Agent / Session / Environment 主线更完整

当前主线已经比较清晰：

```text
Agent
  -> Session
    -> ReasoningStrategy
      -> RuntimeEnvironment
        -> model.query()
        -> tool.execute()
        -> retriever.retrieve()
      -> EventEmitter
      -> CostAccountant
```

这说明 petfishFramework 的核心不是“多实现几个 Agent 算法”，而是建立了一个运行时框架。

推荐继续强化以下概念：

- Agent 是 recipe；
- Session 是一次可审计执行过程；
- Environment 是所有外部能力调用的统一咽喉点；
- Tool / Model / Retriever 都应受 Environment 控制；
- Budget / Permission / Audit / Replay 是运行时结构，而不是外围插件。

---

## 4.3 Model shorthand 已经有实质改善

`0.1.2` 中，类似：

```python
Agent(model="openai:gpt-4o")
```

会直接失败，因为内部期待的是 `ModelAdapter` 对象。

`0.1.4` 已经有 resolver 逻辑。用户在安装对应 optional extra 并配置 API key 后，可以更自然地使用 provider shorthand。

建议继续完善：

- provider string parser；
- optional dependency 检查；
- API key 缺失提示；
- 不支持 provider 时的友好错误；
- `openai:`、`anthropic:` 的文档示例。

---

## 4.4 MCP stdio client 已经可跑

`0.1.4` 的 MCP stdio client 已经不仅是概念。通过最小 JSON-RPC server 测试，可以完成：

- 启动本地 MCP server；
- 初始化；
- `tools/list`；
- `tools/call`；
- 将 MCP tool 包装为框架 tool。

这对 petfishFramework 的定位非常重要。

建议对外表述为：

> MCP client support with real stdio transport and unified native/MCP tool contract.

不建议说：

> full MCP support.

除非 server mode、auth、long-running server lifecycle、错误恢复、tool schema 兼容性等都进一步补齐。

---

## 4.5 Pass^k、Structured Output、Memory、Async、Streaming 都有基本可运行能力

`0.1.4` 不是只修了 Quickstart，也补齐了多个面向实际使用的能力：

- `pass_at_k_with_perturbations()` 可以运行；
- `run_structured()` 可以把 JSON 解析到 dataclass；
- `ConversationStore` 可以跨 session 保存消息；
- `run_async()` 可以执行异步 run；
- `run_stream()` 可以返回 streaming chunks；
- ToolRegistry 可以按 intent 自动选择工具；
- LATS / LLM+P 至少具备可执行 skeleton。

这些能力说明框架已经从“概念展示”进入“最小可用 runtime 组合”。

---

# 5. 当前最严重问题：PermissionEffect 执行语义

## 5.1 问题描述

当前 `DENY` 是安全的：工具不会执行。

但 `REQUIRE_APPROVAL`、`PARTIAL_ALLOW`、`DEGRADE`、`MASK` 的执行语义存在严重风险。

实测发现：

> 对 `REQUIRE_APPROVAL`，工具已经执行了，之后才标记为 denied / approval required。

也就是说，审计事件显示工具被拒绝，但真实副作用已经发生。

例如：

```python
state["calls"] += 1
```

当 policy 返回：

```python
DecisionEffect.REQUIRE_APPROVAL
```

实测结果可能是：

```text
state["calls"] == 1
event == tool.denied
```

这意味着：

- 安全语义失效；
- 审计日志误导；
- 副作用工具已经执行；
- 企业场景下可能造成不可逆后果。

---

## 5.2 为什么这是 P0 问题

petfishFramework 当前的对外定位包含：

- permission-aware；
- budget-aware；
- auditable；
- runtime control；
- enterprise agent safety。

在这样的定位下，权限效果必须具备严格语义。

如果某个 decision 表示“不应执行”，但工具实际已经执行，那么这个框架就不能被安全团队信任。

这不是普通 bug，而是运行时访问控制框架的核心语义问题。

---

## 5.3 正确语义

建议将 PermissionEffect 分成两类：

## A. Pre-execution effects

这些 effect 必须在工具执行前完成处理：

| Effect | 正确语义 |
|---|---|
| `DENY` | 不执行工具 |
| `REQUIRE_APPROVAL` | 审批前不执行工具 |
| `PARTIAL_ALLOW` | 执行前裁剪参数 / 字段 / 动作范围 |
| `DEGRADE` | 执行前切换到低风险工具或低风险参数 |

## B. Post-execution effects

这些 effect 可以在工具执行后处理，但前提是工具是只读或副作用已被明确接受：

| Effect | 正确语义 |
|---|---|
| `MASK` | 对返回结果进行脱敏 |
| `ALLOW` | 正常执行 |

但即使是 `MASK`，也要区分：

- 只读工具；
- 有副作用工具；
- 外发数据工具；
- 写操作工具。

对于带副作用或外发风险的工具，`MASK` 可能不能只做 post-processing，而需要 pre-execution 参数脱敏。

---

# 6. 建议的 PermissionEffect 修复方案

## 6.1 推荐执行流程

建议将 `RuntimeEnvironment.call()` 的核心流程调整为：

```python
decision = policy.evaluate(subject, action, resource, context)

if decision.effect == DENY:
    return block_without_execution(decision)

if decision.effect == REQUIRE_APPROVAL:
    return approval_required_without_execution(decision)

if decision.effect == PARTIAL_ALLOW:
    args = apply_partial_allow(args, decision)

if decision.effect == DEGRADE:
    tool, args = resolve_degraded_execution(tool, args, decision)

result = tool.execute(args)

if decision.effect == MASK:
    result = apply_mask(result, decision)

record_tool_event(
    tool=tool,
    decision=decision,
    executed=True,
    args=args,
    result=result,
)

check_budget()
return result
```

关键原则：

> 除 `ALLOW`、处理后的 `PARTIAL_ALLOW`、处理后的 `DEGRADE` 外，不应默认执行原始工具。

---

## 6.2 推荐事件类型

当前事件如果只是 `tool.called` / `tool.denied`，不足以表达真实执行语义。

建议增加事件类型：

- `tool.allowed`
- `tool.called`
- `tool.blocked`
- `tool.approval_required`
- `tool.partial_allowed`
- `tool.degraded`
- `tool.masked`
- `tool.failed`
- `tool.budget_exceeded`

每个事件建议包含：

```yaml
event_type: tool.approval_required
tool_name: approve_payment
decision_effect: REQUIRE_APPROVAL
decision_reason: amount exceeds approval threshold
executed: false
side_effect: none
subject: user:alice
resource: expense:123
action: approve
timestamp: ...
```

其中最重要的字段是：

```yaml
executed: true | false
```

这可以避免“审计日志显示 denied，但实际已经执行”的问题。

---

## 6.3 推荐测试用例

必须增加副作用工具测试。

### Test 1：DENY 不执行工具

```python
def test_deny_does_not_execute_tool():
    state = {"calls": 0}

    class SideEffectTool(Tool):
        def execute(self, args):
            state["calls"] += 1
            return "done"

    policy = DenyPolicy()

    agent.run("call side effect tool", policy=policy)

    assert state["calls"] == 0
```

### Test 2：REQUIRE_APPROVAL 不执行工具

```python
def test_require_approval_does_not_execute_tool():
    state = {"calls": 0}

    policy = RequireApprovalPolicy()

    agent.run("call side effect tool", policy=policy)

    assert state["calls"] == 0
```

### Test 3：PARTIAL_ALLOW 使用裁剪后的参数执行

```python
def test_partial_allow_rewrites_args_before_execution():
    captured_args = {}

    class CaptureTool(Tool):
        def execute(self, args):
            captured_args.update(args)
            return "done"

    policy = PartialAllowPolicy(allowed_fields=["name"])

    agent.run("call tool with name and ssn", policy=policy)

    assert "name" in captured_args
    assert "ssn" not in captured_args
```

### Test 4：DEGRADE 不执行原始高风险工具

```python
def test_degrade_uses_safe_tool_not_original_tool():
    state = {
        "dangerous_calls": 0,
        "safe_calls": 0,
    }

    policy = DegradePolicy(target_tool="readonly_lookup")

    agent.run("call dangerous tool", policy=policy)

    assert state["dangerous_calls"] == 0
    assert state["safe_calls"] == 1
```

### Test 5：MASK 不影响工具执行但影响返回结果

```python
def test_mask_applies_to_result():
    policy = MaskPolicy(mask_fields=["ssn"])

    result = agent.run("lookup user record", policy=policy)

    assert "ssn" not in result.answer
```

---

# 7. 先进性判断

## 7.1 已经成立的先进性

petfishFramework 的先进性主要体现在运行时架构，而不是单个算法是否 SOTA。

当前已经可以成立的先进性包括：

### 1. Agent / Session 分离

Agent 是静态配方，Session 是一次运行实例。

这有利于：

- 多 session 管理；
- 事件审计；
- replay；
- memory；
- per-run budget；
- per-run policy；
- 多租户隔离。

---

### 2. Environment 作为统一咽喉点

Environment 控制：

- tool call；
- model query；
- retrieval；
- budget；
- permission；
- event emission；
- usage accounting。

这比“Agent 自己到处调用工具，然后外挂 logger”更适合企业场景。

---

### 3. Budget 是硬约束

Budget 能够触发运行时异常，而不是只做统计。

这对企业 Agent 很重要，因为预算失控往往等同于运行时失控。

---

### 4. Permission gate 进入执行路径

`DENY` 已经能阻断工具执行，说明权限门控不是单纯文档概念。

虽然其他 effect 需要修复，但工具调用必须经过 Environment 这一点已经成立。

---

### 5. Event-sourced Session

`session.replay()` 可以拿到事件流。

这为以下能力提供基础：

- 调试；
- 审计；
- 失败归因；
- regression test；
- run comparison；
- 安全复盘。

---

### 6. Pass^k 可靠性测试

内置 Pass^k 思路是正确的。

企业 Agent 不能只看单次成功，而要看多次运行稳定性、扰动稳定性、工具调用路径稳定性。

---

### 7. MCP stdio client

MCP client 能够实际连接 stdio server，说明它具备接入外部工具生态的基础。

更重要的是，它尝试把 native tool 和 MCP tool 统一到同一 Tool Contract 下。

---

## 7.2 暂时不能过度宣传的部分

以下能力目前不能宣传得过满：

| 能力 | 当前建议表述 | 不建议表述 |
|---|---|---|
| 企业权限控制 | permission model foundation | production-grade access control |
| 6 种 DecisionEffect | effects are modeled; some enforcement needs hardening | all effects are fully enforced |
| MCP | MCP client stdio support | full MCP support |
| Replay | audit event replay | full deterministic replay / resume |
| LATS | lightweight LATS-inspired strategy | complete SOTA LATS |
| LLM+P | LLM+P-inspired planning path | full symbolic planning framework |
| CRAG / Adaptive-RAG | inspired retriever interfaces | full CRAG / Adaptive-RAG reproduction |
| Benchmark | initial test suite | proven superior to LangChain / CrewAI / LangGraph |
| Production | Alpha runtime framework | production-ready enterprise platform |

---

# 8. 五个视角的评判

## 8.1 反对者：不要因为 0.1.4 能跑了就过度乐观

0.1.4 确实有进步，但现在暴露出更重要的问题：

> 权限 effect 的执行语义不安全。

如果主打 permission-aware，却出现 `REQUIRE_APPROVAL` 后工具已经执行的问题，安全团队会直接质疑框架可信度。

此外还有几个风险：

- 文档局部不一致；
- GitHub API Reference 与 PyPI 描述可能不同步；
- 187 tests 的可见性不足；
- 生产部署、策略引擎、审批流、credential broker 尚未闭环；
- replay 还不是完整 deterministic replay / resume。

结论：

> 0.1.4 可以展示，但不能吹成生产级安全框架。

---

## 8.2 本质思考者：核心价值是 runtime，不是 agent algorithm

petfishFramework 不应该和 LangChain / CrewAI / AutoGen 正面比“谁的工具多、谁的链式编排复杂”。

它真正的价值是：

```text
所有能力调用必须经过 runtime；
runtime 负责权限、预算、审计、回放和可靠性观测。
```

因此，未来研发优先级应该围绕：

- Environment chokepoint；
- policy enforcement；
- budget accounting；
- event semantics；
- replay fidelity；
- reliability measurement。

而不是继续堆更多 reasoning strategy。

---

## 8.3 机会挖掘者：0.1.4 已经可以形成对外叙事

现在可以讲：

> petfishFramework 是一个围绕 Agent Session 的受控执行 runtime。所有模型、工具、检索能力都通过 Environment chokepoint；每次执行都有预算限制、权限决策、事件审计、trajectory 和 replay；同时支持 Pass^k 可靠性测试与 MCP 工具接入。

这条叙事和以下方向高度一致：

- 企业 AI 从 PoC 到生产；
- Agent 运行时安全；
- 工具调用治理；
- 最小权限；
- 完全仲裁；
- 责任分离；
- contract-driven harness；
- runtime access control；
- AI-native infrastructure security。

---

## 8.4 局外人：用户首先会看到文档和示例

外部开发者不会先理解你的架构，他们会先做三件事：

1. `pip install`;
2. 复制 Quickstart;
3. 看第一个复杂示例能不能跑。

所以短期最重要的是：

- Quickstart 永远可运行；
- 示例要少而稳；
- 文档不要超前于实现；
- 明确哪些能力是 Alpha；
- 明确哪些 effect 已 enforce，哪些只是 model；
- 提供 GitHub Actions badge；
- 提供真实测试可见性。

---

## 8.5 执行者：下一版不要继续堆 feature

0.1.5 不建议继续新增大量能力。

建议只做三件事：

1. 修 PermissionEffect 执行语义；
2. 修事件审计语义；
3. 同步 PyPI / GitHub / API Reference 文档。

这三件事比新增另一个 Agent strategy 更重要。

---

# 9. 版本路线建议

## 9.1 v0.1.5：语义修复版

目标：

> 修复安全语义，确保 permission-aware 叙事可信。

优先任务：

- 修 `REQUIRE_APPROVAL` pre-execution blocking；
- 修 `PARTIAL_ALLOW` pre-execution arg rewriting；
- 修 `DEGRADE` pre-execution tool/path switching；
- 明确 `MASK` 的 pre/post 适用边界；
- 增加 `executed: true/false` 事件字段；
- 增加 side-effect tool 测试；
- 同步 PyPI / GitHub / API Reference；
- 明确 Alpha caveats。

---

## 9.2 v0.1.6：审计报告版

目标：

> 让用户能直观看到一次 Agent Session 发生了什么。

建议增加：

- Markdown trace report；
- JSON trace export；
- session summary；
- tool call timeline；
- permission decision list；
- budget usage timeline；
- final answer；
- errors；
- replay hints。

示例输出：

```markdown
# Session Trace Report

- Session ID: ...
- Agent: ...
- Model: ...
- Start Time: ...
- End Time: ...
- Total Tokens: ...
- Total Cost: ...

## Tool Calls

| Step | Tool | Decision | Executed | Result |
|---|---|---|---|---|

## Permission Decisions

| Step | Effect | Reason | Executed |
|---|---|---|---|

## Budget

| Metric | Used | Limit |
|---|---:|---:|
```

---

## 9.3 v0.2.x：企业 Demo 版

目标：

> 做一个完整端到端企业 Agent 示例，展示框架真正价值。

推荐示例：

> 企业报销审批 Agent

能力覆盖：

- 用户提交报销请求；
- Agent 检索公司政策；
- 调用金额校验工具；
- 调用发票检查工具；
- 超过额度触发审批；
- 敏感字段脱敏；
- 根据角色执行不同权限；
- 全流程事件审计；
- budget 超限中断；
- 最终生成审计报告。

这个 demo 能完整展示：

- Tool Contract；
- RuntimeEnvironment；
- Permission；
- Budget；
- RAG；
- Replay；
- Human approval；
- Structured output；
- Audit report。

---

## 9.4 v0.3.x：最小 Benchmark 版

目标：

> 用小而硬的 benchmark 证明框架差异化。

建议 benchmark 不要一开始追求大而全，而是围绕 runtime control。

### Benchmark A：Tool-use reliability

测试：

- 工具是否调用正确；
- 是否少调用；
- 是否多调用；
- 是否错调用；
- 工具参数是否正确；
- 失败后是否可审计。

指标：

- tool-call accuracy；
- tool-call precision；
- tool-call recall；
- wrong-tool rate；
- missing-tool rate。

---

### Benchmark B：Permission enforcement

测试：

- 不同用户；
- 不同角色；
- 不同资源；
- 不同上下文；
- 不同 DecisionEffect；
- 副作用工具。

指标：

- permission violation rate；
- blocked execution correctness；
- approval-required correctness；
- partial-allow correctness；
- degrade correctness；
- mask correctness。

---

### Benchmark C：Budget robustness

测试：

- 循环工具调用；
- 长上下文；
- 多次检索；
- 模型多轮反复；
- 工具异常重试。

指标：

- budget violation rate；
- cost per successful task；
- token variance；
- tool-call variance；
- step variance。

---

### Benchmark D：Replay completeness

测试：

- 是否记录模型调用；
- 是否记录工具调用；
- 是否记录权限决策；
- 是否记录预算；
- 是否记录错误；
- 是否能复盘失败原因。

指标：

- event coverage；
- trace completeness；
- replay usefulness；
- failure classification coverage。

---

## 9.5 v0.4.x：Policy Engine 版

目标：

> 从 Python policy 进化到可配置策略系统。

建议分阶段实现。

### Phase 1：Python Policy

```python
class FinancePolicy(Policy):
    def evaluate(self, subject, action, resource, context):
        if action == "approve_payment" and context["amount"] > 1000:
            return Decision(REQUIRE_APPROVAL)
        return Decision(ALLOW)
```

### Phase 2：YAML Policy

```yaml
rules:
  - name: large-payment-approval
    when:
      action: approve_payment
      resource.type: expense
      context.amount_gt: 1000
    effect: REQUIRE_APPROVAL
```

### Phase 3：Policy Composition

支持：

- deny-overrides；
- allow-overrides；
- tenant policy；
- user policy；
- tool policy；
- resource policy；
- policy version；
- policy audit。

---

## 9.6 v0.5.x：试点版

目标：

> 能支撑真实企业 PoC。

建议补齐：

- deployment guide；
- production caveats；
- security hardening checklist；
- credential handling；
- approval workflow；
- logging integration；
- SIEM export；
- OpenTelemetry；
- policy versioning；
- failure recovery；
- deterministic replay；
- MCP lifecycle hardening。

---

# 10. 建议的文档重构

## 10.1 README 建议结构

```markdown
# petfishFramework

Reliable, auditable, budget-aware, and permission-aware AI agents.

## Why petfishFramework?

Most agent frameworks focus on making agents capable.
petfishFramework focuses on making agents controllable.

## Core Concepts

- Agent: declarative recipe
- Session: auditable execution
- Environment: runtime chokepoint
- Tool Contract: native and MCP-compatible tools
- Budget: hard execution limits
- Permission: runtime action control
- Replay: audit and regression foundation
- Pass^k: reliability under repeated runs

## Quickstart: No API Key Required

## OpenAI Example

## Tool Example

## Budget Example

## Permission Example

## Replay Example

## MCP Client Example

## Reliability Evaluation

## Status and Limitations

Alpha. API may change.

## Roadmap
```

---

## 10.2 必须明确的限制

README 中建议增加：

```markdown
## Current Limitations

petfishFramework is currently Alpha.

- MCP client stdio is supported; MCP server mode is not yet production-ready.
- DENY enforcement is implemented.
- Other DecisionEffects are modeled but require hardened pre-execution enforcement.
- Replay currently focuses on audit event replay, not full deterministic rerun or resume.
- CRAG / Adaptive-RAG implementations are lightweight references.
- LATS / LLM+P are lightweight strategy implementations.
- APIs may change before v1.0.
```

---

## 10.3 建议补充状态矩阵

```markdown
| Capability | Status |
|---|---|
| Zero-cost quickstart | Available |
| ReAct | Available |
| Budget hard limits | Available |
| DENY permission gate | Available |
| MASK | Basic / needs hardening |
| REQUIRE_APPROVAL | Modeled / needs pre-execution enforcement |
| PARTIAL_ALLOW | Modeled / needs pre-execution rewriting |
| DEGRADE | Modeled / needs pre-execution routing |
| Session replay | Audit replay available |
| Deterministic rerun | Planned |
| Resume | Planned |
| MCP client stdio | Available |
| MCP server mode | Planned |
| Pass^k | Available |
| ToolRegistry | Available |
| Structured output | Available |
| Conversation memory | Available |
```

---

# 11. 对外定位建议

## 11.1 英文一句话

> petfishFramework is a lightweight Python runtime for building reliable, auditable, budget-aware, and permission-aware AI agents.

## 11.2 中文一句话

> petfishFramework 是一个面向可靠、可审计、预算可控、权限可控 AI Agent 的轻量级 Python 运行时框架。

## 11.3 企业安全版本

> petfishFramework provides a runtime control layer for enterprise AI agents, enforcing tool-call boundaries, budget limits, permission decisions, audit events, and reliability evaluation.

## 11.4 开发者版本

> Build Python agents with structured sessions, unified tools, MCP integration, runtime budgets, permission gates, replayable traces, and Pass^k reliability testing.

## 11.5 研究 / 论文版本

> petfishFramework explores a runtime-centered architecture for AI agents, where capabilities are mediated through an auditable environment that enforces budgets, permissions, and reliability-oriented execution traces.

---

# 12. 建议避免的表述

以下表述目前不建议使用：

- “生产级企业 Agent 安全框架”
- “完整访问控制系统”
- “完整 MCP 支持”
- “完整 CRAG / Adaptive-RAG 实现”
- “完整 LATS / LLM+P SOTA 实现”
- “全面替代 LangChain / CrewAI / AutoGen / LangGraph”
- “业界领先 Agent benchmark”
- “默认安全”
- “所有 DecisionEffects 已完整执行”
- “deterministic replay / resume 已闭环”

推荐改成：

- “Alpha runtime framework”
- “runtime-control-oriented”
- “permission model foundation”
- “MCP client support”
- “audit replay”
- “Pass^k reliability testing”
- “lightweight strategy implementations”
- “production hardening on roadmap”

---

# 13. 0.1.5 P0 修复清单

## 13.1 PermissionEffect 执行顺序

- [ ] `DENY`：执行前阻断；
- [ ] `REQUIRE_APPROVAL`：执行前阻断；
- [ ] `PARTIAL_ALLOW`：执行前改写参数；
- [ ] `DEGRADE`：执行前替换工具或降低权限；
- [ ] `MASK`：明确 pre-mask 与 post-mask；
- [ ] 所有 non-ALLOW effect 必须有测试覆盖。

---

## 13.2 事件审计语义

- [ ] 增加 `executed` 字段；
- [ ] 区分 blocked / called / masked / degraded；
- [ ] 记录 decision effect；
- [ ] 记录 decision reason；
- [ ] 记录 subject / resource / action / context 摘要；
- [ ] 避免 event 与真实执行状态不一致。

---

## 13.3 文档同步

- [ ] PyPI 与 GitHub README 同步；
- [ ] API Reference 同步；
- [ ] CHANGELOG 同步；
- [ ] MCP 状态同步；
- [ ] Replay 状态同步；
- [ ] DecisionEffect enforcement 状态同步；
- [ ] 增加 Alpha limitations。

---

## 13.4 测试可见性

- [ ] GitHub Actions；
- [ ] CI badge；
- [ ] Quickstart test；
- [ ] MCP stdio test；
- [ ] Permission side-effect test；
- [ ] Budget test；
- [ ] Replay event test；
- [ ] Pass^k smoke test。

---

# 14. 建议的最小测试套件

## 14.1 Quickstart test

```python
def test_zero_cost_quickstart():
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )

    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    result = agent.run("What is 17 * 23?")
    assert result.answer == "391"
```

---

## 14.2 Budget test

```python
def test_budget_exceeded():
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )

    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    with pytest.raises(BudgetExceeded):
        agent.run(
            "What is 17 * 23?",
            budget=Budget(max_tokens=1),
        )
```

---

## 14.3 Deny side-effect test

```python
def test_deny_does_not_execute_side_effect_tool():
    state = {"calls": 0}

    class SideEffectTool(Tool):
        name = "side_effect"

        def execute(self, args):
            state["calls"] += 1
            return "done"

    policy = DenyPolicy()

    agent.run("call side_effect", policy=policy)

    assert state["calls"] == 0
```

---

## 14.4 Require approval side-effect test

```python
def test_require_approval_does_not_execute_side_effect_tool():
    state = {"calls": 0}

    policy = RequireApprovalPolicy()

    agent.run("call side_effect", policy=policy)

    assert state["calls"] == 0
```

---

## 14.5 Partial allow argument rewrite test

```python
def test_partial_allow_rewrites_args_before_execution():
    captured_args = {}

    class CaptureTool(Tool):
        name = "capture"

        def execute(self, args):
            captured_args.update(args)
            return "done"

    policy = PartialAllowPolicy(allowed_fields=["name"])

    agent.run("call capture with name and ssn", policy=policy)

    assert "name" in captured_args
    assert "ssn" not in captured_args
```

---

## 14.6 Degrade test

```python
def test_degrade_uses_safe_tool():
    state = {
        "dangerous_calls": 0,
        "safe_calls": 0,
    }

    policy = DegradePolicy(target_tool="safe_lookup")

    agent.run("call dangerous_action", policy=policy)

    assert state["dangerous_calls"] == 0
    assert state["safe_calls"] == 1
```

---

## 14.7 Replay consistency test

```python
def test_replay_events_match_execution_state():
    session = agent.session("call tool")
    result = session.run()

    events = session.replay()

    for event in events:
        if event.type in ["tool.blocked", "tool.approval_required"]:
            assert event.executed is False

        if event.type == "tool.called":
            assert event.executed is True
```

---

# 15. 建议的企业 Demo：报销审批 Agent

## 15.1 为什么选择这个 Demo

报销审批是一个很适合展示 petfishFramework 的企业 Agent 场景，因为它天然包含：

- 用户身份；
- 金额阈值；
- 发票附件；
- 政策检索；
- 敏感数据；
- 审批权限；
- 外部系统调用；
- 预算限制；
- 审计要求。

---

## 15.2 Demo 流程

```text
User submits reimbursement request
  -> Agent parses request
  -> Retriever loads expense policy
  -> Tool checks invoice
  -> Tool checks amount
  -> Permission policy evaluates user/action/resource/context
  -> If allowed: submit approval
  -> If over threshold: require approval
  -> If sensitive fields: mask
  -> Event log records every step
  -> Budget enforces run limits
  -> Structured output returns final decision
  -> Trace report generated
```

---

## 15.3 Demo 中可展示的框架能力

| 能力 | Demo 展示方式 |
|---|---|
| Agent | 报销审批 Agent |
| Session | 一次报销请求 |
| Environment | 所有工具调用经过统一咽喉点 |
| Tool | 发票校验、金额校验、审批提交 |
| Retriever | 公司报销政策检索 |
| Budget | 限制 token / tool call / step |
| Permission | 金额、角色、部门、上下文决策 |
| MASK | 脱敏身份证号 / 银行账号 |
| REQUIRE_APPROVAL | 超额度审批 |
| Replay | 复盘整次决策 |
| Structured Output | 输出标准审批结果 |
| Audit Report | 生成审计报告 |

---

# 16. 与用户现有叙事的关系

petfishFramework 的最佳叙事不是“一个新的 Agent 框架”，而是与以下主线融合：

## 16.1 企业 AI 从 PoC 到生产

PoC 阶段关注：

- 能不能回答；
- 能不能调工具；
- 能不能跑 demo。

生产阶段关注：

- 能不能控制；
- 能不能审计；
- 能不能限权；
- 能不能限成本；
- 能不能复盘；
- 能不能稳定运行；
- 出错后能不能定位。

petfishFramework 正好应定位在后者。

---

## 16.2 最小权限、责任分离、完全仲裁

petfishFramework 可以映射到三个访问控制原则：

| 原则 | petfishFramework 映射 |
|---|---|
| 最小权限 | Permission policy / Tool visibility / DecisionEffect |
| 责任分离 | Agent recipe 与 RuntimeEnvironment 分离 |
| 完全仲裁 | 所有 tool/model/retriever 调用经过 Environment |

其中最重要的是：

> Environment 是完全仲裁点。

---

## 16.3 Contract-driven harness

petfishFramework 与 contract-driven harness 的关系：

| Harness 概念 | petfishFramework 对应 |
|---|---|
| Task spec | Agent / Session input |
| Output contract | Structured output |
| Evidence bundle | Retriever / context |
| Validation gate | Budget / Permission / Tool result validation |
| Trace requirement | Event log / Replay |
| Bounded execution | Budget / max steps / max tool calls |

它可以被描述为：

> contract-driven harness 思想在 Agent runtime 中的一种轻量工程实现。

---

## 16.4 AgentShield / AI 运行时安全

petfishFramework 可作为 AgentShield 思路的开发者框架化表达：

- AgentShield 更像安全产品 / 安全控制平面；
- petfishFramework 更像开发者 runtime / agent execution harness；
- 两者可以共享：policy、audit、budget、tool mediation、runtime control。

---

# 17. 最终建议

## 17.1 研发建议

下一版不要继续堆新 feature。

优先级应该是：

1. 修 PermissionEffect pre-execution enforcement；
2. 修事件审计语义；
3. 同步文档；
4. 增加副作用工具测试；
5. 做一个企业端到端 demo；
6. 再做最小 benchmark。

---

## 17.2 宣传建议

可以说：

> petfishFramework is an Alpha-stage runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.

不要说：

> petfishFramework is a production-ready enterprise AI security framework.

---

## 17.3 技术路线建议

坚持 runtime-centered 路线，不要退化成普通 Agent 工具箱。

核心差异化应持续围绕：

- Environment chokepoint；
- permission enforcement；
- budget hard limit；
- audit event；
- replay；
- Pass^k；
- MCP tool contract；
- structured session。

---

## 17.4 最终判断

`0.1.4` 是一次实质性进步。

它说明 petfishFramework 已经不是纯概念项目，而是具备真实运行链路的 Agent runtime Alpha。

但是，当前最关键问题也已经暴露：

> permission-aware 框架必须先保证 permission effect 的执行语义正确。

因此，下一阶段的判断标准不是“新增多少能力”，而是：

- `REQUIRE_APPROVAL` 是否真的不执行；
- `PARTIAL_ALLOW` 是否真的先裁剪；
- `DEGRADE` 是否真的先降级；
- `MASK` 是否明确区分 pre/post；
- 审计事件是否真实反映执行状态；
- 文档是否准确说明当前边界。

只要这几个点修好，petfishFramework 就可以从“可跑的 Alpha runtime”进一步走向“可信的 Agent runtime framework”。
