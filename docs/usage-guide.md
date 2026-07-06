# petfishFramework 使用指南 — 完整生命周期

> 从 `pip install` 到生产部署。每个示例都可运行（FakeModel 不需要 API key）。

---

## 1. 安装与配置

### 1.1 安装

```bash
# 基础安装（纯 Python，无外部依赖）
pip install petfishframework

# 带模型适配器
pip install petfishframework[openai]      # OpenAI / OpenAI 兼容 API
pip install petfishframework[anthropic]   # Anthropic Claude
pip install petfishframework[mcp]         # MCP 工具集成
pip install petfishframework[openai,anthropic,mcp]  # 全部
```

### 1.2 配置 API Key

```bash
# .env 文件
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1    # 或 SiliconFlow/其他兼容 API

# 可选：Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# 可选：benchmark 用的模型名
BENCHMARK_MODEL=gpt-4o-mini
```

框架自动加载 `.env`（通过 `python-dotenv`）。

### 1.3 验证安装

```python
from petfishframework import Agent, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.core.types import ModelResponse

# 用 FakeModel 验证（不需要 API key）
agent = Agent(
    model=FakeModel(responses=(ModelResponse(content="Hello!"),)),
    reasoning=ReAct(),
)
result = agent.run("Say hello")
print(result.answer)  # "Hello!"
```

---

## 2. 你的第一个 Agent

### 2.1 最简路径（3 行核心代码）

```python
from petfishframework import Agent, ReAct
from petfishframework.models.openai import OpenAIModel

agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),  # 或 SiliconFlow 兼容 API
    reasoning=ReAct(),
)

result = agent.run("What is the capital of France?")
print(result.answer)        # "Paris"
print(result.usage.total_tokens)  # token 消耗
```

### 2.2 发生了什么？

```
agent.run("...")
  → 创建 Session（事件溯源执行进程）
    → 创建 Environment（咽喉点：权限 + 预算 + 审计）
      → ReAct 策略执行（think → act → observe 循环）
        → model.query() 通过 Environment
        → 工具调用通过 Environment（如有）
      → 返回 Result（answer + trajectory + usage）
```

### 2.3 Result 对象

```python
result = agent.run("What is 2 + 3?")

result.answer              # str — 最终答案
result.trajectory.steps    # tuple[Step] — 每步推理记录
result.usage.total_tokens  # int — 总 token 消耗
result.session_id          # str — 唯一会话 ID
```

---

## 3. 工具系统

### 3.1 使用内置工具

```python
from petfishframework import Agent, ReAct
from petfishframework.models.openai import OpenAIModel
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.word_sorter import WordSorter

agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tools=(Calculator(), WordSorter()),
)

# 框架自动选择正确的工具
result = agent.run("What is 17 * 23?")
print(result.answer)  # "391"

result = agent.run("Sort alphabetically: cherry apple banana")
print(result.answer)  # "apple banana cherry"
```

### 3.2 创建自定义工具

```python
from petfishframework import BaseTool
from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

class WebSearch(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information"
    input_schema: dict = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    risk_level: RiskLevel = RiskLevel.MEDIUM  # 网络访问
    capabilities: tuple = ("network",)

    def execute(self, args: dict) -> ToolResult:
        query = args.get("query", "")
        # 你的搜索逻辑
        results = my_search_function(query)
        return ToolResult(value=results)

# 使用
agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tools=(WebSearch(), Calculator()),
)
```

### 3.3 自动工具选择（ToolRegistry）

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.registry import ToolRegistry, create_default_registry

# 方式 1：使用默认注册表（内置 Calculator + WordSorter + PathPlanner）
agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tool_registry=create_default_registry(),
)

# 方式 2：自定义注册表
registry = ToolRegistry()
registry.register(Calculator(), intents=("calculate", "multiply", "divide", "add"))
registry.register(WebSearch(), intents=("search", "find", "lookup", "google"))
registry.register(WordSorter(), intents=("sort", "alphabetize"))

agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tool_registry=registry,
)

# 框架根据任务意图自动选择工具
agent.run("What is 17 * 23?")        # → 自动加载 Calculator
agent.run("Search for latest AI news")  # → 自动加载 WebSearch
agent.run("Explain quantum physics")    # → 无匹配 → 纯 LLM 推理
```

---

## 4. 推理策略

### 4.1 三种策略对比

| 策略 | 适用场景 | 特点 |
|---|---|---|
| **ReAct** | 通用任务（默认） | think → act → observe 循环 |
| **LATS** | 复杂多步推理 | MCTS 搜索，候选生成 + 价值评估 |
| **LLM+P** | 有明确规划步骤的任务 | LLM 翻译 + 符号规划器求解 |

### 4.2 切换策略

```python
from petfishframework import Agent, ReAct, LATS, LLMPlusP

# ReAct（默认）
agent = Agent(model=model, reasoning=ReAct())

# LATS — 更强搜索能力
agent = Agent(model=model, reasoning=LATS(breadth=3, max_depth=5))

# LLM+P — 符号规划
agent = Agent(model=model, reasoning=LLMPlusP(planner_tool="path_planner"))
```

### 4.3 策略可互换

三种策略共享同一个冻结接口（V2 原型验证）。切换策略不需要改其他代码。

---

## 5. 检索增强（RAG）

### 5.1 基础向量检索

```python
from petfishframework.retrieval.memory_store import MemoryRetriever

retriever = MemoryRetriever()
retriever.add("Python is a high-level language.", {"topic": "python"})
retriever.add("Rust focuses on memory safety.", {"topic": "rust"})

agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    retriever=retriever,
)

result = agent.run("What is Python?")
# 框架自动检索相关文档，注入到模型上下文
```

### 5.2 CRAG（纠正式 RAG）

```python
from petfishframework.retrieval.crag import CRAGRetriever

# CRAG 评估检索质量，质量差时回退到 web 搜索
retriever = CRAGRetriever(
    base_retriever=MemoryRetriever(),  # 基础检索器
    web_search=my_web_search_func,      # 可选：web 搜索回退
)

agent = Agent(model=model, reasoning=ReAct(), retriever=retriever)
```

### 5.3 Adaptive-RAG（自适应检索路由）

```python
from petfishframework.retrieval.adaptive import AdaptiveRetriever

# 根据查询复杂度自动选择检索策略
retriever = AdaptiveRetriever(
    base_retriever=MemoryRetriever(),
    # 简单查询 → 不检索；中等 → 单步检索；复杂 → 多步检索
)

agent = Agent(model=model, reasoning=ReAct(), retriever=retriever)
```

---

## 6. 结构化输出

### 6.1 从自由文本到结构化数据

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PersonInfo:
    name: str
    age: int
    city: str

agent = Agent(model=OpenAIModel(model="gpt-4o-mini"), reasoning=ReAct())

result = agent.run_structured(
    "Tell me about Alice who is 30 and lives in Paris",
    PersonInfo,
)

if result.data:
    print(result.data.name)   # "Alice"
    print(result.data.age)    # 30
    print(result.data.city)   # "Paris"
else:
    print(f"Parse failed: {result.parse_error}")
```

### 6.2 多选题（MMLU 场景）

```python
@dataclass(frozen=True)
class MCQAnswer:
    answer: str  # "A", "B", "C", or "D"

result = agent.run_structured(
    "What is 2+2? A) 3  B) 4  C) 5  D) 6",
    MCQAnswer,
)
# result.data.answer == "B" — 零歧义，无需 regex
```

---

## 7. 对话记忆

### 7.1 多轮对话

```python
from petfishframework.core.conversation import InMemoryConversationStore

store = InMemoryConversationStore()
agent = Agent(model=OpenAIModel(model="gpt-4o-mini"), reasoning=ReAct())

# 第一轮
agent.run("My name is Alice.", conversation_id="chat1", conversation_store=store)

# 第二轮 — agent 记住了第一轮
result = agent.run("What's my name?", conversation_id="chat1", conversation_store=store)
print(result.answer)  # "Alice"
```

### 7.2 隔离的对话

```python
# 不同 conversation_id 互不干扰
agent.run("I like blue.", conversation_id="user1", conversation_store=store)
agent.run("I like red.", conversation_id="user2", conversation_store=store)

# user1 记住 blue，user2 记住 red
```

---

## 8. 流式输出

```python
agent = Agent(model=OpenAIModel(model="gpt-4o-mini"), reasoning=ReAct())

# 逐 chunk 输出
for chunk in agent.run_stream("Tell me a story about a robot."):
    print(chunk, end="", flush=True)
# 实时流式输出，不等完整响应
```

---

## 9. 异步操作

### 9.1 异步运行

```python
import asyncio

async def main():
    agent = Agent(model=OpenAIModel(model="gpt-4o-mini"), reasoning=ReAct())

    # 异步运行
    result = await agent.run_async("What is the capital of Japan?")
    print(result.answer)  # "Tokyo"

asyncio.run(main())
```

### 9.2 并发运行

```python
async def concurrent():
    agent = Agent(model=model, reasoning=ReAct())

    # 同时运行多个任务
    results = await asyncio.gather(
        agent.run_async("What is 2+2?"),
        agent.run_async("What is 3+3?"),
        agent.run_async("What is 4+4?"),
    )
    # results[0].answer == "4", results[1].answer == "6", ...

asyncio.run(concurrent())
```

---

## 10. 多 Agent 委托

### 10.1 Supervisor → Worker 模式

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.agent_tool import AgentAsTool

# 创建一个专门做数学的 worker agent
math_agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tools=(Calculator(),),
)

# 把 worker 包装为工具，supervisor 可以调用它
supervisor = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tools=(
        AgentAsTool(agent=math_agent, name="math_worker",
                    description="Delegate a math problem to a math specialist"),
    ),
)

# supervisor 自动委托给 worker
result = supervisor.run("Calculate the area of a circle with radius 5")
# supervisor → 调用 math_worker → math_agent 用 Calculator 计算 → 返回结果
```

### 10.2 多专家委托

```python
research_agent = Agent(model=model, reasoning=ReAct(), tools=(WebSearch(),))
writing_agent = Agent(model=model, reasoning=ReAct())

supervisor = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(
        AgentAsTool(agent=research_agent, name="researcher"),
        AgentAsTool(agent=writing_agent, name="writer"),
        AgentAsTool(agent=math_agent, name="mathematician"),
    ),
)

result = supervisor.run("Research AI trends, summarize in 200 words, and calculate growth rate")
```

---

## 11. MCP 工具集成

### 11.1 连接真实 MCP Server

```python
from petfishframework.mcp import connect_stdio

# 连接 filesystem MCP server
client = connect_stdio(
    "npx",
    ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
)

# 发现可用工具
tools = client.discover_tools()
print([t.name for t in tools])
# ['read_file', 'write_file', 'list_directory', 'create_directory', ...]

# 在 Agent 中使用 MCP 工具
agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),
    reasoning=ReAct(),
    tools=tuple(tools),
)

result = agent.run("List all files in /tmp")
```

### 11.2 自定义 MCP 工具

```python
from petfishframework.mcp.wrapper import MCPToolWrapper
from petfishframework.mcp.client import MCPToolSpec

# 手动注册 MCP 格式的工具
custom_tool = MCPToolWrapper(
    name="custom_api",
    description="Call my custom API",
    input_schema={"type": "object", "properties": {"endpoint": {"type": "string"}}},
    call_fn=lambda args: {"result": f"Called {args['endpoint']}"},
)

agent = Agent(model=model, reasoning=ReAct(), tools=(custom_tool,))
```

---

## 12. 可靠性

### 12.1 预算控制

```python
from petfishframework import Budget

# 限制 token、步数、工具调用次数
budget = Budget(
    max_tokens=10000,       # 最大 token
    max_cost_usd=0.50,      # 最大成本
    max_steps=10,           # 最大推理步数
    max_tool_calls=5,       # 最大工具调用次数
)

result = agent.run("Complex task...", budget=budget)
# 超出任何限制 → BudgetExceeded 异常
```

### 12.2 重试与容错

```python
from petfishframework.reliability.retry import RetryPolicy, retry_model_adapter

# 包装模型适配器，自动重试瞬时故障
raw_model = OpenAIModel(model="gpt-4o-mini")
safe_model = retry_model_adapter(raw_model, RetryPolicy(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
))

agent = Agent(model=safe_model, reasoning=ReAct())
# API 限流 → 自动重试，指数退避 + 随机抖动
```

### 12.3 超时

```python
from petfishframework.reliability.timeout import TimeoutPolicy, with_timeout

# 包装慢操作
policy = TimeoutPolicy(
    model_call_timeout_s=30.0,
    tool_call_timeout_s=10.0,
)
# 超时 → OperationTimedOut 异常
```

### 12.4 Pass^k 一致性度量

```python
from petfishframework.reliability import pass_at_k, pass_at_k_with_perturbations, exact_match
from petfishframework.core.types import Task

task = Task(prompt="What is 17 * 23? Use the calculator.")

# 基本 Pass^k — 同一任务跑 k 次，测一致性
result = pass_at_k(
    session_factory=lambda t: agent.session(t),
    task=task,
    k=8,
    agreement=exact_match,
)
print(f"Pass@8: {result.pass_count}/8")

# 冻结-扰动 Pass^k — 加扰动变体（顺序打乱、同义词替换等）
full_result = pass_at_k_with_perturbations(
    session_factory=lambda t: agent.session(t),
    task=task,
    k=8,
)
print(full_result.summary())
# Pass@8 — PASS (100%)
#   canonical:        8/8
#   order_shuffled:   8/8
#   alias:            8/8
#   paraphrase:       8/8
#   distractor:       8/8
```

---

## 13. 回放与审计

### 13.1 事件溯源

```python
from petfishframework.observability.sinks import ListSink

sink = ListSink()
agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

# 运行前订阅事件流
session = agent.session("What is 2+3?")
session.events.subscribe(sink)

result = session.run()

# 检查审计日志
for event in sink.events:
    print(f"{event.type}: {event.data}")
# session.start: {}
# model.called: {usage: {input_tokens: 50, output_tokens: 20}}
# tool.called: {tool_name: "calculator", args: {expression: "2+3"}, result: 5}
# session.end: {}
```

### 13.2 确定性回放

```python
from petfishframework.reliability.replay import RecordingEnvironment, ReplayEnvironment, ReplayMode

# 第一次运行：录制
recording = RecordingEnvironment(real_env)
ctx = RunContext(task=task, env=recording, ...)
result = strategy.run(ctx)
# recording.model_responses 和 recording.tool_calls 已保存

# AUDIT 回放：确定性重放（相同轨迹）
replay_env = ReplayEnvironment(
    model_responses=recording.model_responses,
    tool_results=recording.tool_calls,
)
ctx2 = RunContext(task=task, env=replay_env, ...)
replayed = strategy.run(ctx2)
# replayed.answer == result.answer — 完全一致
```

---

## 14. 权限控制

### 14.1 SARC 访问控制

```python
from petfishframework.permissions.model import (
    DecisionEffect, Subject, Action, Resource, AccessContext,
    Decision, PermissionPolicy
)

class StrictPolicy:
    """自定义策略：拒绝所有网络工具。"""
    def evaluate(self, subject, action, resource, context):
        if "network" in resource.tags:
            return Decision(
                effect=DecisionEffect.DENY,
                reason="network access blocked"
            )
        if "shell" in resource.tags:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason="shell commands need approval"
            )
        return Decision(effect=DecisionEffect.ALLOW)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(WebSearch(), Calculator()),
    permission_policy=StrictPolicy(),
)
# WebSearch 被 DENY，Calculator 被 ALLOW
```

### 14.2 六种决策效果

```python
DecisionEffect.ALLOW             # 完全允许
DecisionEffect.DENY              # 拒绝
DecisionEffect.MASK              # 返回掩码值 [MASKED]
DecisionEffect.PARTIAL_ALLOW     # 仅允许部分参数
DecisionEffect.REQUIRE_APPROVAL  # 需人工审批
DecisionEffect.DEGRADE           # 降级响应
```

---

## 15. 观测性与成本

### 15.1 事件监控

```python
from petfishframework.observability.sinks import ConsoleSink, ListSink

# 控制台输出（调试用）
session = agent.session("task")
session.events.subscribe(ConsoleSink())
result = session.run()
# [session.start] {}
# [model.called] {model: gpt-4o-mini, tokens: 120}
# [tool.called] {tool: calculator, result: 391}
# [session.end] {}
```

### 15.2 成本报告

```python
from petfishframework.reliability.cost_report import CostReport

result = agent.run("Complex task with multiple tool calls...")

report = CostReport.from_result(result)
print(report.format_text())
# Tokens: 1500 in / 800 out | Cost: $0.0045 | Time: 3.2s | 3 tool calls
```

---

## 16. 配置系统

```python
from petfishframework.config import FrameworkConfig

# 从环境变量加载
config = FrameworkConfig.from_env()

# 从字典加载（YAML/JSON 配置文件）
config = FrameworkConfig.from_dict({
    "default_model": "gpt-4o-mini",
    "default_temperature": 0.0,
    "default_budget": {"max_tokens": 10000},
    "openai_api_key": "sk-...",
    "timeout_s": 30.0,
})

print(config.default_model)       # "gpt-4o-mini"
print(config.openai_api_key)      # "sk-..."
```

---

## 17. 生产模式：综合示例

### 17.1 带完整可靠性保障的 Agent

```python
from petfishframework import Agent, Budget, ReAct
from petfishframework.models.openai import OpenAIModel
from petfishframework.reliability.retry import RetryPolicy, retry_model_adapter
from petfishframework.tools.registry import create_default_registry
from petfishframework.observability.sinks import ListSink

# 1. 模型（带重试）
model = retry_model_adapter(
    OpenAIModel(model="gpt-4o-mini"),
    RetryPolicy(max_retries=3, initial_delay=1.0, backoff_factor=2.0),
)

# 2. Agent（带自动工具选择 + 预算）
agent = Agent(
    model=model,
    reasoning=ReAct(),
    tool_registry=create_default_registry(),
)

# 3. 运行（带预算 + 审计）
sink = ListSink()
session = agent.session(
    "Research the population of France, calculate density given area 551695 km²",
    budget=Budget(max_tokens=5000, max_tool_calls=5),
)
session.events.subscribe(sink)

result = session.run()

# 4. 检查结果
print(f"Answer: {result.answer}")
print(f"Tokens: {result.usage.total_tokens}")
print(f"Steps:  {len(result.trajectory.steps)}")

# 5. 审计
for event in sink.events:
    if event.type == "tool.called":
        print(f"  Tool: {event.data.get('tool_name')}")

# 6. 成本
from petfishframework.reliability.cost_report import CostReport
report = CostReport.from_events(sink.events)
print(report.format_text())
```

### 17.2 多 Agent 系统

```python
# 专家 agents
researcher = Agent(
    model=model, reasoning=ReAct(),
    tool_registry=create_default_registry(),
    retriever=CRAGRetriever(base_retriever=MemoryRetriever()),
)

analyst = Agent(
    model=model, reasoning=ReAct(),
    tools=(Calculator(),),
)

# Supervisor 委托给专家
from petfishframework.tools.agent_tool import AgentAsTool

supervisor = Agent(
    model=model, reasoning=ReAct(),
    tools=(
        AgentAsTool(agent=researcher, name="researcher",
                    description="Research a topic"),
        AgentAsTool(agent=analyst, name="analyst",
                    description="Analyze data and calculate"),
    ),
)

result = supervisor.run(
    "Research France's population and area, then calculate population density"
)
```

### 17.3 对话机器人

```python
from petfishframework.core.conversation import InMemoryConversationStore

store = InMemoryConversationStore()
agent = Agent(
    model=model, reasoning=ReAct(),
    tool_registry=create_default_registry(),
)

# 模拟多轮对话
def chat(user_input: str, session_id: str = "user1"):
    result = agent.run(
        user_input,
        conversation_id=session_id,
        conversation_store=store,
        budget=Budget(max_tokens=2000),
    )
    return result.answer

# 多轮对话
print(chat("Hi, I'm Alice and I'm learning Python."))
print(chat("What's a good first project?"))
print(chat("What language did I say I'm learning?"))  # → "Python"（记住第一轮）
```

---

## 18. 完整生命周期总结

```
安装 → 配置 → 创建 Agent → 添加工具/检索/策略 → 运行 → 审计/回放 → 生产
  │        │        │           │                  │        │          │
  │        │        │           │                  │        │          └─ 多 Agent + 对话记忆
  │        │        │           │                  │        └─ 事件溯源 + 成本报告
  │        │        │           │                  └─ 预算 + 重试 + 超时
  │        │        │           └─ ToolRegistry 自动选择 + CRAG/Adaptive-RAG
  │        │        └─ Agent(model, reasoning, tools, retriever, tool_registry, policy)
  │        └─ .env + FrameworkConfig
  └─ pip install petfishframework[openai,anthropic,mcp]
```

**框架三个自动路由轴**：

| 轴 | 自动决策 | 用户无需操心 |
|---|---|---|
| ToolRouter | 任务意图 → 工具选择 | 不需要手动配工具 |
| Adaptive-RAG | 查询复杂度 → 检索策略 | 不需要手动选检索方式 |
| ReasoningStrategy | 任务类型 → 推理方式 | 不需要手动选 ReAct/LATS/LLM+P |

**可靠性基础设施（结构性嵌入）**：

| 机制 | 作用 |
|---|---|
| Budget | 硬执行 token/cost/steps 上限 |
| Retry | 瞬时故障自动重试 |
| Timeout | 操作超时保护 |
| Pass^k | 一致性度量 |
| Replay | 确定性回放 |
| SARC | 权限控制 |
| EventEmitter | 全链路审计 |
