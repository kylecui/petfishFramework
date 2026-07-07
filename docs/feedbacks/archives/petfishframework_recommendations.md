# petfishFramework 发展建议文档

## 1. 总体判断

petfishFramework 当前最值得强调的价值，不是“又一个 Agent 框架”，而是：

> 面向企业 Agent 可靠性与运行时安全控制的轻量级框架原型。

它的核心先进性在于将 Agent 从“会调用工具的 Prompt 程序”，提升为一个具备运行时边界、权限控制、预算约束、事件审计、回放能力与可靠性度量的受控执行系统。

但当前版本仍处于 Alpha 阶段。建议对外表述时避免直接宣称“全面领先 LangChain / CrewAI / LangGraph”，而应强调其独特方向：

- Agent runtime control
- Tool-call chokepoint
- Session-level auditability
- Budget-aware execution
- Permission-aware execution
- Reliability-oriented evaluation
- MCP-friendly tool abstraction

---

## 2. 建议的产品定位

### 2.1 不建议的定位

不建议将 petfishFramework 定位为：

> 通用 Agent 框架，全面替代现有 Agent 生态。

这个说法风险较高，因为当前项目仍缺少真实用户、真实 benchmark、完整文档和成熟生态。

### 2.2 建议的定位

建议定位为：

> petfishFramework is a lightweight Python framework for building reliable, auditable, budget-aware, and permission-aware AI agents.

中文可以表述为：

> petfishFramework 是一个面向可靠、可审计、预算可控、权限可控 AI Agent 的轻量级 Python 框架。

更偏企业安全方向的版本可以是：

> petfishFramework 是一个面向企业 Agent 运行时安全与可靠性治理的轻量级框架，围绕 Session、Environment、Tool Contract、Budget、Permission 与 Replay 建立可控执行边界。

---

## 3. 当前最值得保留和强化的先进性

## 3.1 Environment 作为统一咽喉点

当前设计中，工具调用、模型查询、检索与预算计量都通过 Environment 执行。这是项目最核心的架构资产。

建议在文档中明确强调：

- Agent 不直接调用工具
- ReasoningStrategy 不直接拥有外部能力
- 所有能力调用必须经过 Environment
- Environment 是权限、预算、审计、观测与策略执行的统一控制点

这比“在工具外面包一层 logger”更有价值。它意味着运行时控制是框架结构的一部分，而不是事后补丁。

---

## 3.2 Session 是可审计执行过程

Session 不应只被描述为“运行一次 Agent 的上下文”，而应被定义为：

> 一次具备身份、事件流、预算使用、对话状态和可回放语义的 Agent 执行过程。

建议强化以下概念：

- 每次运行都有 session_id
- 每一步执行都有事件记录
- 工具调用、模型调用、预算消耗、权限决策都应进入事件流
- Session replay 是后续调试、审计和合规能力的基础

---

## 3.3 Permission Model 不只是 allow / deny

项目中的 SARC 模型和 DecisionEffect 是一个值得强化的方向。

建议把权限控制从简单二元判断扩展为企业 Agent 场景下的动作治理模型：

- ALLOW：允许执行
- DENY：拒绝执行
- MASK：脱敏后执行
- PARTIAL_ALLOW：部分字段或部分动作允许
- REQUIRE_APPROVAL：需要人工审批
- DEGRADE：降级执行，例如改用只读工具、摘要工具或低风险路径

这比传统 RBAC 更适合 AI Agent，因为 Agent 动作往往不是简单 API 调用，而是包含意图、上下文、数据对象和外部副作用的复杂行为。

---

## 3.4 Budget 是运行时硬约束

Budget 不应只被描述为“成本统计”，而应定义为运行时硬约束。

建议明确区分：

- token budget
- cost budget
- step budget
- tool-call budget
- wall-clock budget
- risk budget

未来可以进一步支持：

- per-session budget
- per-agent budget
- per-user budget
- per-tool budget
- per-tenant budget

企业场景中，预算控制不仅是省钱，也是一种安全边界。无限循环、工具滥用、检索过载和模型调用风暴，本质上都是运行时失控问题。

---

## 3.5 Pass^k 是可靠性而不是准确率指标

Pass^k 能力应被重点包装为可靠性评估能力。

建议对外解释为：

> 单次成功不代表 Agent 可靠。企业 Agent 需要关注同类任务多次运行时的稳定性。

建议内置或示例化以下测试：

- 同一输入重复运行 k 次
- 输入顺序扰动
- 文本改写扰动
- 增加无关干扰信息
- 同义词替换
- 工具返回格式轻微变化
- 检索结果顺序变化

输出指标可以包括：

- pass@1
- pass@k
- consistency@k
- variance
- failure class distribution
- tool-call divergence
- budget variance

---

## 4. 当前主要短板

## 4.1 Quickstart 与实际实现需要对齐

当前 README / PyPI 示例中如果使用类似 `model="openai:gpt-4o"` 的字符串写法，而源码中 Agent 实际需要 `ModelAdapter` 对象，就会导致新用户试用失败。

这是优先级最高的问题之一。

建议立即处理：

```python
from petfishframework import Agent, OpenAIModel, Calculator

agent = Agent(
    model=OpenAIModel(model="gpt-4o"),
    tools=[Calculator()],
)
```

或者实现字符串自动解析：

```python
agent = Agent(
    model="openai:gpt-4o",
    tools=["calculator"],
)
```

如果选择支持字符串写法，则需要补充：

- provider parser
- model adapter registry
- clear error message
- provider dependency check
- API key validation hint

---

## 4.2 默认 allow-all 策略不适合安全叙事

当前默认策略如果是 allow all，那么不应在对外材料中暗示“已经具备完整企业级访问控制”。

建议文档中明确分层：

| 层级 | 当前状态 | 建议表述 |
|---|---|---|
| 权限模型抽象 | 已有 | SARC model and DecisionEffect are defined |
| 工具调用门控 | 已有基础 | Tool execution can pass through policy evaluation |
| 默认策略 | allow-all | Safe for development, not production |
| 完整策略引擎 | 待完善 | Policy engine is on roadmap |
| 审批流 | 待完善 | Human approval can be modeled but needs implementation |
| 字段级脱敏 | 待完善 | Masking effect defined, enforcement needs implementation |

建议增加一个 `DenyByDefaultPolicy` 示例，让安全叙事更可信。

---

## 4.3 Replay 语义需要闭环

当前 replay 如果主要返回事件日志，而 RESUME / RERUN 仍是 TODO，那么不能将其包装成完整可回放执行系统。

建议拆成三个层次：

1. **Audit Replay**
   - 回看发生了什么
   - 当前最容易完成

2. **Deterministic Rerun**
   - 固定模型响应、工具响应、检索结果
   - 用于回归测试

3. **Resume Execution**
   - 从中断点继续执行
   - 用于长任务恢复

短期建议优先完成 Audit Replay 和 Deterministic Rerun。Resume 可以放到后续版本。

---

## 4.4 MCP 支持需要清楚区分 client 与 server

如果当前已经能连接 MCP server，但不能把自身作为 MCP server 暴露能力，文档需要明确：

- MCP client mode：可用
- MCP server mode：计划中
- Native tool and MCP tool share the same contract：这是重点

建议避免写成“full MCP support”，而写成：

> MCP client support with a unified native/MCP tool contract. MCP server mode is planned.

---

## 4.5 RAG 模块应避免过度宣称

CRAG 和 Adaptive-RAG 当前如果只是轻量 skeleton，就不应直接暗示完整复现论文能力。

建议表述为：

> petfishFramework provides CRAG-inspired and Adaptive-RAG-inspired retriever interfaces, with lightweight reference implementations.

这样既能说明方向先进，也不会让用户误以为已经具备完整生产级 CRAG / Adaptive-RAG 能力。

---

## 5. 优先级最高的改进路线

## 5.1 P0：让新用户 5 分钟跑通

目标：

> pip install 后，用户复制 README 示例即可成功运行。

任务清单：

- 修复 quickstart 示例
- 明确 API key 配置方式
- 提供 FakeModel 零成本示例
- 提供 OpenAI 示例
- 提供 Anthropic 示例
- 提供 MCP client 示例
- 提供自定义 Tool 示例
- 增加错误提示
- 增加最小测试

建议 README 第一屏只保留最稳定示例，避免展示尚未完全实现的高级能力。

---

## 5.2 P1：做一个完整企业 Agent 示例

建议提供一个端到端 example：

> 企业报销审批 Agent

该示例可以展示：

- 用户提交报销请求
- Agent 检索公司政策
- Agent 调用金额校验工具
- Agent 调用发票检查工具
- Agent 根据权限决定是否允许审批
- 超过额度需要人工审批
- 敏感字段脱敏
- 全流程写入事件日志
- 预算超限则中断
- 最终输出审计报告

这个示例能同时展示框架的核心卖点：

- Tool contract
- Environment chokepoint
- Permission decision
- Budget enforcement
- Audit event
- Replay
- RAG
- Human approval

---

## 5.3 P1：补一个真实 benchmark

建议不要一开始追求大规模 benchmark，而是做一个小而硬的 benchmark。

可以设计三类任务：

### A. Tool-use reliability

测试 Agent 是否正确调用工具、是否少调用、多调用、错调用。

### B. Permission enforcement

测试不同用户、不同资源、不同上下文下，Agent 是否被运行时策略正确限制。

### C. Budget robustness

测试循环、异常工具、长上下文、重复检索场景下，预算是否能硬中断。

输出指标：

- success rate
- pass@k
- permission violation rate
- budget violation rate
- tool-call accuracy
- replay completeness
- event coverage
- cost per successful task

---

## 5.4 P2：补策略引擎

建议实现最小可用策略引擎，而不是一开始追求复杂 DSL。

第一阶段可以支持 Python policy：

```python
class FinancePolicy(Policy):
    def evaluate(self, subject, action, resource, context):
        if action == "approve_payment" and context["amount"] > 1000:
            return Decision(REQUIRE_APPROVAL)
        return Decision(ALLOW)
```

第二阶段再支持 YAML policy：

```yaml
rules:
  - name: large-payment-approval
    when:
      action: approve_payment
      resource.type: expense
      context.amount_gt: 1000
    effect: REQUIRE_APPROVAL
```

第三阶段再考虑：

- policy composition
- tenant policy
- policy versioning
- policy audit
- deny-overrides
- allow-overrides
- risk scoring
- approval workflow

---

## 5.5 P2：补可视化审计输出

建议提供一种简单的 HTML / Markdown trace report。

内容包括：

- session_id
- agent name
- model
- start / end time
- total token / cost
- tool calls
- permission decisions
- budget checkpoints
- final output
- errors
- replay hint

这样项目会更容易被企业用户理解，也更容易用于 demo。

---

## 6. 建议的 README 结构

建议 README 改成以下结构：

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

## Quickstart

Use FakeModel first.

## OpenAI Example

## Tool Example

## Permission Example

## Budget Example

## Replay Example

## MCP Client Example

## Reliability Evaluation

## Roadmap

## Status

Alpha. API may change.
```

---

## 7. 建议的对外表述

## 7.1 一句话版本

> petfishFramework is a lightweight Python framework for reliable, auditable, budget-aware, and permission-aware AI agents.

## 7.2 中文一句话版本

> petfishFramework 是一个面向可靠、可审计、预算可控、权限可控 AI Agent 的轻量级 Python 框架。

## 7.3 企业安全版本

> petfishFramework provides a runtime control layer for enterprise AI agents, enforcing tool-call boundaries, permission checks, budget limits, audit events, and reliability evaluation.

## 7.4 开发者版本

> Build Python agents with structured sessions, unified tools, MCP integration, runtime budgets, permission gates, replayable traces, and Pass^k reliability testing.

---

## 8. 建议避免的表述

建议避免以下表述：

- “完全替代 LangChain”
- “生产级企业安全 Agent 框架”
- “完整 MCP 支持”
- “完整 CRAG / Adaptive-RAG 实现”
- “业界领先 Agent benchmark”
- “默认安全”
- “已验证优于主流 Agent 框架”

这些说法目前证据不足，容易被技术读者质疑。

更稳妥的说法是：

- “architecture-first”
- “runtime-control-oriented”
- “alpha framework”
- “MCP client support”
- “CRAG-inspired retriever”
- “Adaptive-RAG-inspired retriever”
- “permission model foundation”
- “replay and reliability roadmap”

---

## 9. 建议的近期版本路线

## v0.1.x：可跑通

目标：

- 修复 quickstart
- FakeModel 示例稳定
- OpenAI 示例稳定
- Anthropic 示例稳定
- Calculator / WordSorter / PathPlanner 示例稳定
- 基础单元测试通过

## v0.2.x：可展示

目标：

- 企业审批 Agent 示例
- Budget 示例
- Permission 示例
- Replay report 示例
- MCP client 示例
- Pass^k 示例

## v0.3.x：可验证

目标：

- 小型 benchmark
- pass@k 指标
- permission violation test
- budget violation test
- event coverage test
- 与简单 baseline 对比

## v0.4.x：可扩展

目标：

- Policy engine
- YAML policy
- Human approval hook
- CredentialBroker
- Deterministic rerun
- richer MCP integration

## v0.5.x：可试点

目标：

- 真实企业 workflow demo
- trace report
- policy audit
- deployment guide
- production caveats
- security hardening checklist

---

## 10. 最重要的三条建议

第一，先把 **quickstart 跑通**。  
如果用户复制第一段示例失败，后面的架构先进性都会被抵消。

第二，尽快做一个 **企业 Agent 端到端示例**。  
petfishFramework 的价值不是单点 API，而是 Session + Environment + Tool + Permission + Budget + Audit 的组合效果。

第三，补一个 **小型但可信的 benchmark**。  
不需要一开始很大，但必须证明它在可靠性、安全门控、预算控制、审计覆盖方面确实优于裸 Agent 或简单 ReAct baseline。

---

## 11. 最终结论

petfishFramework 的方向是对的：它抓住了企业 Agent 从 PoC 走向生产时真正缺失的运行时控制问题。

它现在最需要的不是增加更多概念，而是把已有概念闭环：

- 示例闭环
- 权限闭环
- 预算闭环
- 审计闭环
- replay 闭环
- benchmark 闭环

只要这几个闭环完成，petfishFramework 就可以从“架构很有想法的 Alpha 项目”，成长为一个真正有差异化的企业 Agent runtime framework。
