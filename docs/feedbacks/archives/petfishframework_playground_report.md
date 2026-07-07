# petfishFramework Playground 实测报告

## 1. 测试目标

本次测试目标是确认 `petfishframework` 是否可以在隔离 Python 环境中实际安装、导入和运行，并验证其核心 Agent runtime 能力是否只是文档描述，还是已经具备基本可运行性。

重点验证以下问题：

1. 包是否可以正常安装；
2. 基础模块是否可以正常导入；
3. README / PyPI quickstart 是否可以直接运行；
4. `FakeModel + ReAct + Tool` 是否可以完成一次 Agent Session；
5. Budget 是否能作为运行时硬约束生效；
6. Permission gate 是否真的位于工具调用执行路径上；
7. Replay / event log 是否可用；
8. Pass^k 稳定性测试是否可以运行；
9. 当前 API 与文档是否存在不一致。

---

## 2. 总体结论

结论可以概括为：

> petfishFramework 的核心 runtime 思路已经可以实际跑通；它的问题不是架构不可用，而是 Alpha 阶段的 API、文档与对外承诺尚未完全对齐。

本次测试确认以下能力已经可用：

- `pip install petfishframework` 可以成功安装；
- `import petfishframework` 可以成功导入；
- `FakeModel + ReAct + Calculator` 可以完成一次工具调用 Agent Session；
- `Session` 可以记录 trajectory；
- `session.replay()` 可以返回事件流；
- `Budget` 可以触发硬中断；
- 自定义 Permission Policy 可以拒绝工具调用；
- `pass_at_k` 可以运行稳定性测试。

但也发现几个直接影响新用户体验的问题：

- PyPI / README quickstart 中的 `model="openai:gpt-4o"` 字符串写法当前不能直接运行；
- `Agent(..., budget=...)` 这种直觉写法不可用，预算应传给 `run()` 或 `session()`；
- `Result` 对象没有 `events` 字段，事件需要从 `session.replay()` 获取；
- `session.replay(ReplayMode.AUDIT)` 当前不可用，因为 `Session.replay()` 不接受参数；
- `OpenAIModel` 需要安装 optional extra，例如 `petfishframework[openai]`。

---

## 3. 测试环境

测试方式：

- 使用隔离 Python 虚拟环境；
- 安装 PyPI 包 `petfishframework==0.1.2`；
- 优先使用 `FakeModel` 避免外部 API key 干扰；
- 只验证 framework 自身 runtime 能力；
- 不依赖 OpenAI / Anthropic 的真实调用结果；
- 不测试 MCP server mode。

项目信息：

| 项目 | 结果 |
|---|---|
| 包名 | `petfishframework` |
| 版本 | `0.1.2` |
| 安装方式 | `pip install petfishframework` |
| Python 要求 | `>=3.10` |
| 当前阶段 | Alpha |
| 可选依赖 | `openai` / `anthropic` / `mcp` |

---

## 4. 安装与导入测试

### 4.1 安装

安装命令：

```bash
pip install petfishframework
```

结果：

```text
安装成功
```

### 4.2 导入

测试：

```python
import petfishframework
print(petfishframework.__version__)
```

结果：

```text
0.1.2
```

结论：

> 包本身可以正常安装和导入，基础发布流程是有效的。

---

## 5. 最小 Agent Session 测试

### 5.1 可运行代码

以下代码可以成功运行：

```python
from petfishframework import Agent, ReAct, Budget
from petfishframework.tools.calculator import Calculator
from petfishframework.models.fake import FakeModel

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

session = agent.session(
    "What is 17 * 23?",
    budget=Budget(max_tokens=1000, max_tool_calls=5, max_steps=5),
)

result = session.run()

print(result.answer)
print(result.usage)
print(result.trajectory.steps)
print(session.replay())
```

### 5.2 实际输出

核心输出：

```text
ANSWER: 391
```

Usage 输出类似：

```text
Usage(input_tokens=20, output_tokens=40, total_tokens=60, cost_usd=0.0, elapsed_s=0.0)
```

Trajectory 中出现两步：

```text
Step(
    thought='I will use the calculator tool.',
    tool_name='calculator',
    tool_args={'expression': '17 * 23'},
    observation='391'
)

Step(
    thought='391',
    tool_name=None,
    tool_args=None,
    observation=None
)
```

Replay 事件流包含：

```text
session.start
model.called
tool.called
model.called
session.end
```

### 5.3 判断

该测试说明以下执行链路真实有效：

```text
Agent
  -> Session
    -> ReasoningStrategy
      -> ModelAdapter
      -> Environment
        -> Tool
      -> EventEmitter
```

这证明 petfishFramework 不是纯概念项目，至少基本 Agent runtime 是可以实际执行的。

---

## 6. Budget 测试

### 6.1 测试目的

验证预算是否只是统计字段，还是可以作为运行时硬约束生效。

### 6.2 测试方式

将 token budget 设置得非常低：

```python
from petfishframework import Budget

result = agent.run(
    "What is 17 * 23?",
    budget=Budget(max_tokens=30, max_tool_calls=5, max_steps=5),
)
```

### 6.3 结果

运行触发异常：

```text
BudgetExceeded
```

### 6.4 判断

Budget 不是简单记录字段，而是可以触发运行时中断。

这是一个重要设计点。企业 Agent 中，预算控制不仅是成本管理，也是一种安全控制：

- 防止循环调用；
- 防止工具滥用；
- 防止检索风暴；
- 防止模型调用失控；
- 防止成本异常扩大；
- 防止恶意或异常任务拖垮系统。

建议后续将 Budget 明确包装为：

> Runtime hard limit, not just usage accounting.

---

## 7. Permission Gate 测试

### 7.1 测试目的

验证工具调用是否真的经过权限策略，而不是工具被 Agent 直接调用。

### 7.2 测试代码

定义一个拒绝所有动作的策略：

```python
from petfishframework.permissions import Decision, DecisionEffect

class DenyAllPolicy:
    def evaluate(self, subject, action, resource, context):
        return Decision(
            DecisionEffect.DENY,
            reason="test deny",
        )
```

将该策略传给 Session 或 Environment 后运行工具调用任务。

### 7.3 结果

工具调用没有被实际执行，Agent 收到的 observation 类似：

```text
denied: test deny
```

### 7.4 判断

这说明 Permission gate 确实位于工具调用执行路径上。

也就是说，petfishFramework 当前已经具备最关键的安全架构基础：

> Agent 不直接调用工具，工具调用必须经过 Environment gate。

这与企业 AI Agent 的运行时访问控制需求高度一致。

但当前实现仍偏基础，后续还需要补齐：

- Deny 后是否直接终止；
- Deny 是否进入结构化审计报告；
- Deny 是否触发 human approval；
- `MASK` 是否真正执行字段脱敏；
- `PARTIAL_ALLOW` 是否能限制字段或参数；
- `DEGRADE` 是否能切换到低风险工具；
- Subject / Resource / Context 如何从业务系统注入；
- 默认策略是否应从 allow-all 改为 deny-by-default 示例。

---

## 8. Replay / Event Log 测试

### 8.1 可用能力

当前 `session.replay()` 可以返回事件流。

示例事件包括：

```text
session.start
model.called
tool.called
model.called
session.end
```

这对于调试和审计很有价值。

### 8.2 当前限制

以下写法当前不可用：

```python
from petfishframework.reliability import ReplayMode

session.replay(ReplayMode.AUDIT)
```

错误原因：

```text
TypeError: Session.replay() takes 1 positional argument but 2 were given
```

这说明当前 `Session.replay()` 更像是固定的 audit event dump，而不是完整的 replay mode API。

### 8.3 建议分层

建议将 Replay 能力分为三个层级：

#### Level 1：Audit Replay

目标：

- 回看发生了什么；
- 展示模型调用；
- 展示工具调用；
- 展示权限决策；
- 展示预算消耗；
- 展示最终输出。

当前项目已经具备基础。

#### Level 2：Deterministic Rerun

目标：

- 固定模型响应；
- 固定工具响应；
- 固定检索结果；
- 用于 regression test；
- 用于失败复现。

建议作为近期优先方向。

#### Level 3：Resume Execution

目标：

- 从中断点恢复；
- 继续长任务；
- 支持 durable execution。

可以放到后续阶段。

---

## 9. Pass^k 测试

### 9.1 测试目标

验证框架是否支持同一任务多次运行，以检测 Agent 稳定性。

### 9.2 测试意义

单次成功不能证明 Agent 可靠。企业 Agent 更关心的是：

- 同类任务多次运行是否稳定；
- 输入轻微扰动后是否仍然成功；
- 工具调用路径是否一致；
- 失败模式是否可归类；
- 成本是否稳定；
- 是否偶发越权或超预算。

### 9.3 判断

`pass_at_k` 能够运行，说明 petfishFramework 已经把可靠性评估纳入框架设计，而不是完全依赖外部 benchmark。

建议后续扩展指标：

- `pass@1`
- `pass@k`
- `consistency@k`
- `tool_call_accuracy`
- `tool_call_divergence`
- `budget_variance`
- `permission_violation_rate`
- `failure_class_distribution`

---

## 10. README / PyPI Quickstart 问题

### 10.1 当前文档写法

PyPI / README 示例类似：

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator

agent = Agent(
    model="openai:gpt-4o",
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)
```

### 10.2 实际问题

当前运行会报错：

```text
AttributeError: 'str' object has no attribute 'query'
```

### 10.3 原因判断

当前 `Agent.model` 实际需要的是 `ModelAdapter` 对象，而不是字符串。

也就是说，文档中展示了 model string shortcut，但实现中尚未看到对应的 resolver。

### 10.4 修复方案 A：修改文档

将 quickstart 改为真实可运行版本：

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.models.openai import OpenAIModel

agent = Agent(
    model=OpenAIModel(model="gpt-4o"),
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)
```

### 10.5 修复方案 B：实现字符串解析

保留当前写法：

```python
agent = Agent(
    model="openai:gpt-4o",
    reasoning=ReAct(),
    tools=(Calculator(),),
)
```

则需要实现：

- provider parser；
- model adapter registry；
- optional dependency check；
- API key hint；
- 清晰错误提示；
- 单元测试。

示意逻辑：

```python
def resolve_model(model):
    if isinstance(model, ModelAdapter):
        return model

    if isinstance(model, str):
        provider, name = model.split(":", 1)
        if provider == "openai":
            return OpenAIModel(model=name)
        if provider == "anthropic":
            return AnthropicModel(model=name)

    raise TypeError(
        "model must be a ModelAdapter or provider string like 'openai:gpt-4o'"
    )
```

### 10.6 建议

短期建议先采用方案 A，确保 quickstart 100% 可运行。

中期再实现方案 B，提高易用性。

---

## 11. Budget API 体验问题

### 11.1 直觉写法

很多用户可能会自然写成：

```python
agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(Calculator(),),
    budget=Budget(max_tokens=1000),
)
```

### 11.2 当前结果

该写法会失败：

```text
TypeError: Agent.__init__() got an unexpected keyword argument 'budget'
```

### 11.3 设计解释

从架构上看，当前设计是合理的：

- Agent 是配方；
- Session 是一次执行；
- Budget 是执行期约束；
- 因此 Budget 放在 `run()` 或 `session()` 更合理。

### 11.4 建议文档表述

建议在文档中明确写：

```python
# Agent defines the recipe.
agent = Agent(...)

# Budget belongs to a run/session.
result = agent.run(
    "task",
    budget=Budget(max_tokens=1000, max_tool_calls=5),
)
```

并解释：

> Budget is execution-scoped, not agent-scoped.

---

## 12. Result 与 Events 的关系

### 12.1 可能的误用

用户可能会期待：

```python
result.events
```

### 12.2 当前问题

`Result` 没有 `events` 字段。

### 12.3 当前正确方式

使用：

```python
session = agent.session("task")
result = session.run()
events = session.replay()
```

### 12.4 建议

可以考虑在文档中明确：

- `Result`：最终答案、usage、trajectory；
- `Session`：事件、回放、执行上下文。

也可以考虑在未来增加便利字段：

```python
result.events
```

但如果坚持严格分层，也可以不加，只要文档说清楚。

---

## 13. OpenAI / Anthropic Optional Dependencies

### 13.1 当前情况

base install 后，如果直接使用 OpenAI adapter，可能会失败，因为需要 optional dependency。

### 13.2 建议文档写法

```bash
pip install "petfishframework[openai]"
```

或：

```bash
pip install "petfishframework[anthropic]"
```

或完整安装：

```bash
pip install "petfishframework[openai,anthropic,mcp]"
```

### 13.3 建议错误提示

当用户没有安装 optional dependency 时，建议抛出更友好的错误：

```text
OpenAIModel requires the optional dependency 'openai'.
Install it with:

    pip install "petfishframework[openai]"
```

---

## 14. 建议的 README Quickstart 重写

### 14.1 零成本 Quickstart

建议 README 第一段使用 FakeModel，保证没有 API key 也能跑通：

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.models.fake import FakeModel

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
print(result.answer)
```

预期输出：

```text
391
```

### 14.2 OpenAI Quickstart

放在第二段：

```bash
pip install "petfishframework[openai]"
```

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.models.openai import OpenAIModel

agent = Agent(
    model=OpenAIModel(model="gpt-4o"),
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)
```

### 14.3 Budget 示例

```python
from petfishframework import Budget

result = agent.run(
    "What is 17 * 23?",
    budget=Budget(
        max_tokens=1000,
        max_tool_calls=5,
        max_steps=5,
    ),
)
```

### 14.4 Replay 示例

```python
session = agent.session("What is 17 * 23?")
result = session.run()

for event in session.replay():
    print(event)
```

---

## 15. 建议补充的最小测试集

建议增加以下单元测试，保证 PyPI 发布前不会再次出现 quickstart 失效：

### 15.1 Import Test

```python
def test_import_package():
    import petfishframework
    assert petfishframework.__version__
```

### 15.2 FakeModel ReAct Test

```python
def test_fake_model_react_calculator():
    model = FakeModel.script_tool_then_answer(
        "calculator",
        {"expression": "17 * 23"},
        "391",
    )

    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    result = agent.run("What is 17 * 23?")
    assert result.answer == "391"
```

### 15.3 Budget Test

```python
def test_budget_exceeded():
    model = FakeModel.script_tool_then_answer(
        "calculator",
        {"expression": "17 * 23"},
        "391",
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

### 15.4 Permission Deny Test

```python
def test_permission_deny_blocks_tool_call():
    class DenyAllPolicy:
        def evaluate(self, subject, action, resource, context):
            return Decision(DecisionEffect.DENY, reason="test deny")

    # Assert tool execution is denied and event is recorded.
```

### 15.5 Replay Test

```python
def test_session_replay_contains_tool_call():
    session = agent.session("What is 17 * 23?")
    result = session.run()

    events = session.replay()
    assert any(event.name == "tool.called" for event in events)
```

---

## 16. 修复优先级

### P0：必须立即修

- README / PyPI quickstart 必须可运行；
- 文档必须明确 `model` 参数当前需要 `ModelAdapter`；
- 文档必须明确 Budget 传给 `run()` 或 `session()`；
- 文档必须明确 events 通过 `session.replay()` 获取；
- OpenAI / Anthropic optional dependency 安装方式必须写清楚。

### P1：增强可信度

- 增加 FakeModel 零成本 quickstart；
- 增加 OpenAI / Anthropic 示例；
- 增加 Budget 示例；
- 增加 Permission 示例；
- 增加 Replay 示例；
- 增加 Pass^k 示例；
- 增加 GitHub Actions 测试 quickstart。

### P2：增强企业安全叙事

- 增加 `DenyByDefaultPolicy`；
- 增加 `RequireApprovalPolicy` 示例；
- 实现 `MASK` enforcement；
- 实现 `PARTIAL_ALLOW` enforcement；
- 实现 `DEGRADE` enforcement；
- 增加结构化 audit report；
- 增加 policy decision event。

---

## 17. 对框架成熟度的判断

当前 petfishFramework 可以被描述为：

> 一个已经具备核心 runtime 能力的 Alpha framework。

不应描述为：

> 一个成熟的生产级企业 Agent 安全平台。

原因是：

- quickstart 尚未完全对齐实现；
- 权限策略仍偏基础；
- replay 还不是完整 RERUN / RESUME；
- MCP server mode 未验证；
- CRAG / Adaptive-RAG 更像轻量 skeleton；
- benchmark 尚未补齐；
- 生产部署指南尚不完整。

更稳妥的表达是：

> petfishFramework has a promising runtime architecture for controlled agent execution, but needs API cleanup, documentation alignment, realistic examples, and validation benchmarks before being positioned as production-ready.

中文表达：

> petfishFramework 已经具备受控 Agent 执行的核心架构雏形，但在成为生产级框架之前，还需要完成 API 收口、文档对齐、真实示例、策略闭环和 benchmark 验证。

---

## 18. 最重要的结论

本次 playground 实测说明：

1. **核心执行链路可用**  
   `Agent -> Session -> ReasoningStrategy -> Environment -> Tool -> Event Log` 可以实际跑通。

2. **运行时控制是真的**  
   Budget 和 Permission gate 不只是文档概念，已经能影响执行结果。

3. **当前最大问题是 P0 工程收口**  
   Quickstart、API 文档、optional dependency、Replay API 需要尽快对齐。

4. **项目方向值得继续推进**  
   它的价值不在于“比 LangChain 多几个工具”，而在于以 Environment 为咽喉点，将权限、预算、审计、回放和可靠性测试纳入 Agent runtime。

最终判断：

> petfishFramework 当前已经越过“纯概念项目”的阶段，但还没有到“成熟生产框架”的阶段。它最应该优先补的是可运行文档、端到端示例和最小 benchmark。完成这些之后，它的企业 Agent runtime 定位会更有说服力。
