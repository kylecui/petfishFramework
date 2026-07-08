# petfishFramework v0.5.1 Review 与验证反馈

> 版本：`petfishframework==0.5.1`  
> 发布页：https://pypi.org/project/petfishframework/0.5.1/  
> 本次重点：验证 v0.5.x 的 Tool/MCP governance 是否真正落地，复测 Quickstart、Trusted Publishing、MCP server、MCP allowlist/schema-pin/risk-map、schema validation、rate limiting、release hygiene、文档与分发一致性。

---

## 1. 总体结论

v0.5.1 是一个实质推进版本。它不是只改了 README，而是把 v0.5.x 路线中的 Tool/MCP governance 组件做进了包里。

本地安装 `petfishframework==0.5.1` 后，我验证到：

- Quickstart 继续正常；
- PyPI Trusted Publishing 继续正常；
- tests badge 已到 382；
- `MCPAllowlist` 可阻断未授权 MCP server command；
- `SchemaPin` 可 pin schema 并检测 drift；
- `MCPRiskMapper` 可按 capabilities 生成 risk level；
- `serve_as_mcp()` 已经是可运行的 minimal stdio JSON-RPC MCP server；
- `ToolSchemaValidator` 可做基础 JSON schema 检查；
- `RateLimiter` 可限制 tool 调用频率；
- `RuntimeEnvironment` 中已经有 schema validation / rate limiting / idempotency / retry / timeout wiring；
- `MCPClient` 支持 `pin_schemas()` / `verify_schemas()` / `health()` / `close()` / `reconnect()`；
- `MCPToolWrapper` 会把 MCP 工具统一包装成 framework `Tool`。

所以，v0.5.1 可以更明确地说：

> petfishFramework 已经进入 Tool/MCP governance Alpha 阶段，不再只是 runtime permission framework。

但我仍然不建议说 production-ready。当前主要问题是：

1. PyPI / README 的状态表仍写 `MCP server mode Planned`，但代码中已经有 minimal `serve_as_mcp()`；
2. API Reference raw 仍显示 `v0.4.0`，没有同步到 `v0.5.1`；
3. README / docs / CI YAML / Dockerfile 仍是超长行压缩格式；
4. PyPI README 让用户运行 `examples/05_enterprise_expense.py`，但 `pyproject.toml` 的 sdist exclude 里排除了 `examples/`，pip 安装后并没有这些示例；
5. `RuntimeEnvironment` 已有 schema validator / rate limiter / idempotency hook，但 `Agent` / `Session` 仍没有一等参数暴露这些治理组件；
6. `RiskClassificationPolicy` 的默认 `Resource` dataclass 没有 `risk_level` 字段，导致直接使用 `Resource(classification=...)` 不会触发 risk policy；
7. `MCP serverInfo.version` 当前返回 `0.5.0`，而包版本是 `0.5.1`；
8. schema validation 当前仍是轻量实现，不是完整 JSON Schema validator；
9. rate limiting 在 idempotency cache 之前执行，重复 idempotency key 的缓存命中也会先被 rate-limit 卡住，这一点需要确认设计意图。

我的判断：

> v0.5.1 对 Tool/MCP governance 的代码落地让我满意；对文档/分发一致性和上层 API 收口还不满意。

---

## 2. PyPI 与发布状态

PyPI v0.5.1 页面显示：

| 项目 | 状态 |
|---|---|
| 版本 | `0.5.1` |
| 发布时间 | 2026-07-08 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| Tests | 382 |
| Extras | `anthropic`, `mcp`, `openai`, `otel`, `vault` |
| Trusted Publishing | Yes |
| Provenance / attestation | Yes |
| Roadmap | `v0.5.x (current): Tool/MCP governance ... ✅` |
| MCP server mode | PyPI Current Limitations 仍写 Planned |

PyPI 文件详情显示：

- sdist `petfishframework-0.5.1.tar.gz` 使用 Trusted Publishing；
- wheel `petfishframework-0.5.1-py3-none-any.whl` 使用 Trusted Publishing；
- 二者都有 attestation / provenance；
- provenance 指向 GitHub `publish.yml`、tag `refs/tags/v0.5.1`、commit `66bf962...`。

这说明供应链发布可信度继续正常。

---

## 3. 本地 Playground 复测摘要

## 3.1 安装与版本

```bash
python3 -m venv /tmp/pf051
source /tmp/pf051/bin/activate
pip install petfishframework==0.5.1
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.5.1
```

---

## 3.2 Quickstart 复测

```python
from petfishframework import Agent, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator

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

result = agent.run("calc")
print(result.answer)
```

输出：

```text
391
```

判断：

> 核心 quickstart 主链路继续稳定。

---

## 4. Tool/MCP Governance 实测

## 4.1 MCPAllowlist

实测：

```python
from petfishframework.mcp.allowlist import MCPAllowlist

allowlist = MCPAllowlist({"srv1"}, strict=True)

allowlist.is_allowed("srv1")  # True
allowlist.is_allowed("srv2")  # False
```

结果：

```text
True / False
```

判断：

> MCP server command allowlist 基础可用。

注意：

- `connect_stdio(command, args, allowlist=...)` 已经支持 allowlist；
- allowlist 当前基于 command 字符串，不是 server identity / package digest / binary hash；
- 这适合 PoC，但还不是强 supply-chain allowlist。

建议后续扩展：

```text
server_id
command
package name
version
digest
allowed args pattern
allowed working directory
```

---

## 4.2 SchemaPin / schema drift

实测：

```python
from dataclasses import dataclass
from petfishframework.mcp.schema_pin import SchemaPin

@dataclass
class T:
    name: str
    input_schema: dict

tools = [T("a", {"type": "object", "properties": {"x": {"type": "number"}}})]

pin = SchemaPin()
pin.pin(tools)
pin.verify(tools)  # []

changed = [T("a", {"type": "object", "properties": {"x": {"type": "string"}}})]
pin.verify(changed)
```

结果：

```text
[]
["tool 'a' input schema drifted"]
MCPSchemaDrift raised by assert_no_drift(...)
```

判断：

> schema pin / drift detection 可用。

这对 MCP governance 很关键，因为 MCP server 的 tools/list schema 变化会影响 agent tool invocation 安全边界。

---

## 4.3 MCPRiskMapper

实测：

```python
from petfishframework.mcp.risk_mapper import MCPRiskMapper

mapper = MCPRiskMapper()

mapper.classify(("read",))
mapper.classify(("write_file",))
mapper.classify(("network",))
```

结果：

```text
("read",)       -> MEDIUM
("write_file",) -> MEDIUM
("network",)    -> HIGH
```

判断：

> capability → risk_level 的基本映射可用。

当前风险映射仍较粗：

- `network` → HIGH；
- `write_file` / `delete_file` 等在默认映射中仍是 MEDIUM；
- 这是否合适要结合企业策略再定。

建议将默认风险映射配置化，至少允许 YAML 或 constructor 显式定义。

---

## 4.4 MCPClient risk mapping

实测：

```python
from petfishframework.mcp.client import MCPClient, MCPToolSpec
from petfishframework.mcp.risk_mapper import MCPRiskMapper

client = MCPClient(
    {
        "net": MCPToolSpec(
            name="net",
            description="",
            input_schema={},
            call_fn=lambda args: "ok",
            capabilities=("network",),
        )
    },
    risk_mapper=MCPRiskMapper(),
)

tool = client.discover_tools()[0]
print(tool.risk_level)
```

输出：

```text
RiskLevel.HIGH
```

判断：

> MCPClient discovery 阶段可以把 capabilities 映射成 Tool risk_level。

这是 v0.5.x 的关键正向信号。

---

## 4.5 Minimal MCP server

v0.5.1 中已经有：

```python
from petfishframework.mcp.server import serve_as_mcp
```

我用 `StringIO` 模拟 stdio JSON-RPC，验证了：

- `initialize`
- `tools/list`
- `tools/call`

示例：

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"calculator","arguments":{"expression":"2+3"}}}
```

输出包含：

```json
{"protocolVersion": "2024-11-05", "serverInfo": {"name": "petfishframework", "version": "0.5.0"}}
{"tools": [{"name": "calculator", ...}]}
{"content": [{"type": "text", "text": "5"}], "isError": false}
```

判断：

> MCP server mode 已经有 minimal implementation，不应继续在 PyPI Current Limitations 中写成纯 Planned。

但还要加边界：

> 当前是 minimal stdio server，不是完整 MCP server platform。

建议状态表改为：

```text
MCP server mode: MVP available — initialize/tools.list/tools.call only; governance and lifecycle hardening still in progress.
```

另一个小问题：

> `serverInfo.version` 返回 `0.5.0`，包版本是 `0.5.1`。建议从 `petfishframework.__version__` 动态读取。

---

## 4.6 ToolSchemaValidator

实测：

```python
from petfishframework.tools.schema_validator import ToolSchemaValidator

validator = ToolSchemaValidator()

schema = {
    "type": "object",
    "properties": {
        "amount": {"type": "number"},
        "name": {"type": "string"},
    },
    "required": ["amount"],
}

validator.validate(schema, {"amount": 1, "name": "a"})      # []
validator.validate(schema, {"amount": "x", "extra": 1})     # ["amount must be type number, got str"]
```

判断：

> 基础 schema validation 可用。

当前边界：

- 不是完整 JSON Schema 实现；
- 不处理所有 format / enum / oneOf / anyOf / nested schema；
- 对 additionalProperties 等约束支持有限。

建议文档中明确为：

```text
lightweight schema validator, not full jsonschema.
```

或直接依赖 `jsonschema` / `fastjsonschema` 作为 optional extra。

---

## 4.7 RateLimiter

实测：

```python
from petfishframework.tools.rate_limiter import RateLimiter, RateLimitPolicy

limiter = RateLimiter()
policy = RateLimitPolicy(max_calls=2, window_s=10)

limiter.check("t", policy)  # True
limiter.check("t", policy)  # True
limiter.check("t", policy)  # False
limiter.remaining("t", policy)  # 0
```

判断：

> tool-level sliding-window rate limiter 可用。

---

## 4.8 RuntimeEnvironment governance wiring

`RuntimeEnvironment` 已经包含：

```python
timeout_policy
rate_limiter
idempotency_store
schema_validator
```

执行顺序大致是：

```text
permission decision
-> PARTIAL_ALLOW arg filtering
-> schema validation
-> rate limiting
-> input mask
-> idempotency check
-> credential injection
-> retry
-> timeout
-> execution
-> output mask
-> event log
```

这说明 v0.5.1 已经把治理组件嵌入 runtime path。

但我发现一个设计细节：

> rate limiting 在 idempotency cache 之前执行。

实测中：

1. 第一次带 `_idempotency_key="k1"` 的 tool call 成功；
2. 第二次同 key，本应可 cache hit；
3. 但因为 rate limit 已满，第二次在到达 idempotency cache 之前被 `rate_limited` 阻断。

这未必是 bug，但要明确设计语义：

- 如果 rate limit 计的是“请求次数”，当前顺序合理；
- 如果 rate limit 计的是“真实外部副作用调用次数”，idempotency cache 应该在 rate limit 前。

建议在文档中明确，或者调整为：

```text
idempotency cache check -> rate limiting -> execution
```

这样重复请求不会消耗 rate quota。

---

## 5. 当前仍不满意的问题

## 5.1 PyPI / README 状态表与代码不一致

PyPI 当前 `Current Limitations` 仍写：

```text
MCP server mode Planned
```

但 v0.5.1 包里已经有可运行的 `serve_as_mcp()`，我也实际验证了 initialize / tools/list / tools/call。

建议改为：

```text
MCP server mode ✅ MVP Available
```

并补一句：

```text
Minimal stdio JSON-RPC server only; full lifecycle/governance hardening still ongoing.
```

---

## 5.2 API Reference 版本仍旧

我抓到的 `docs/api.md` raw 第一行仍是：

```text
public API of petfishFramework v0.4.0
```

这与 v0.5.1 不一致。

建议：

```text
public API of petfishFramework v0.5.1
```

或更稳妥：

```text
public API of petfishFramework v0.5.x
Last validated against: 0.5.1
```

---

## 5.3 README / docs / CI YAML 仍是超长行压缩格式

raw README 仍只有 11 行；CI YAML 只有 2 行；CHANGELOG 只有 3 行；deployment guide 只有 9 行。

这说明 v0.4.2 我提出的格式化问题仍没有彻底解决。

影响：

- review 难；
- diff 难；
- blame 难；
- 外部贡献难；
- markdownlint / prettier 难；
- 专业可信度受影响。

建议 v0.5.2 做一次 pure formatting patch。

---

## 5.4 PyPI 示例命令与包分发不一致

PyPI README 中写：

```text
Run: python examples/05_enterprise_expense.py
```

但 provenance commit 的 `pyproject.toml` 中：

```toml
[tool.hatch.build.targets.sdist]
exclude = [
  ".opencode/",
  ".petfish/",
  "outputs/",
  "examples/",
  "scripts/",
]
```

这意味着 PyPI sdist / wheel 不包含 examples。用户通过：

```bash
pip install petfishframework
python examples/05_enterprise_expense.py
```

会失败，除非他是在 GitHub 仓库 checkout 中运行。

我本地在非仓库目录验证：

```bash
python examples/05_enterprise_expense.py
```

结果：

```text
python: can't open file '/tmp/examples/05_enterprise_expense.py': [Errno 2] No such file or directory
```

建议二选一：

方案 A：README 写清楚：

```text
From a repository checkout:
  python examples/05_enterprise_expense.py
```

方案 B：把 examples 纳入 sdist，或提供 console script：

```bash
python -m petfishframework.examples.enterprise_expense
```

---

## 5.5 `Agent` / `Session` 还没有暴露 governance 参数

虽然 `RuntimeEnvironment` 已有：

```python
rate_limiter
schema_validator
idempotency_store
timeout_policy
```

但 `Agent(...)` 仍没有这些一等参数。

当前 `Agent` 签名是：

```python
Agent(
    model,
    reasoning,
    tools,
    retriever=None,
    permission_policy=...,
    tool_registry=None,
    credential_broker=None,
)
```

建议 v0.5.2 / v0.6 增加：

```python
Agent(
    ...,
    schema_validator=ToolSchemaValidator(),
    rate_limiter=RateLimiter(),
    idempotency_store=IdempotencyStore(),
    timeout_policy=TimeoutPolicy(...),
)
```

或提供统一对象：

```python
ToolGovernance(
    schema_validator=...,
    rate_limiter=...,
    idempotency_store=...,
)
```

否则这些治理能力虽然在 runtime path，但用户需要直接构造 `RuntimeEnvironment`，不够一等 API。

---

## 5.6 `RiskClassificationPolicy` 与 Resource 类型不完全匹配

`RiskClassificationPolicy.evaluate()` 读取：

```python
getattr(resource, "risk_level", None)
```

但 `permissions.model.Resource` 当前字段是：

```python
type
classification
tags
```

没有 `risk_level`。

因此直接使用默认 `Resource(classification="restricted")` 时：

```text
resource has no RiskLevel; defaulting to ALLOW
```

这可能造成用户误解。

建议：

1. 给 `Resource` 增加 `risk_level: RiskLevel | None`；
2. 或让 `RiskClassificationPolicy` 根据 `classification` 映射 risk；
3. 或明确该 policy 只能用于带动态 `risk_level` 的 Resource-like object。

---

## 6. v0.5.1 当前成熟度判断

## 6.1 可以说什么

可以说：

> petfishFramework v0.5.1 is an Alpha-stage runtime control framework with Tool/MCP governance primitives: MCP allowlist, schema pinning, risk mapping, lightweight schema validation, rate limiting, idempotency hooks, retry/timeout wiring, minimal MCP server, CI, and Trusted Publishing.

可以说：

> v0.5.1 is suitable for controlled enterprise PoC, Tool/MCP governance experiments, and production-readiness evaluation.

可以说：

> v0.5.1 has a minimal MCP server implementation, but not a full MCP server platform.

---

## 6.2 不应说什么

仍不建议说：

- production-ready；
- v1 API stable；
- complete MCP governance platform；
- complete JSON Schema enforcement；
- complete MCP server lifecycle management；
- complete rate-limit / idempotency semantics；
- complete deployment hardening；
- complete SIEM / DLP solution；
- enterprise compliance ready without additional controls。

---

## 6.3 推荐定位

中文：

> petfishFramework v0.5.1 是一个 Alpha 阶段的 Agent 运行时控制框架，已经在 v0.4.x 的生产化基础上继续补齐 Tool/MCP governance 能力，包括 MCP allowlist、schema pin/drift、risk mapping、schema validation、rate limiting、minimal MCP server、retry/timeout/idempotency wiring 与可信发布链路。它适合受控企业 PoC 与 Tool/MCP governance 验证，但仍需补齐文档状态、分发一致性、一等治理 API 与完整生产语义。

英文：

> petfishFramework v0.5.1 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, now with Tool/MCP governance primitives and a minimal MCP server implementation.

---

## 7. 五顾问评判

## 7.1 反对者

v0.5.1 仍不是 production-ready。

主要问题：

1. PyPI 状态表说 MCP server planned，但代码已有 minimal implementation；
2. API Reference 仍是 v0.4.0；
3. README / docs raw 格式仍是压缩超长行；
4. examples 不随 PyPI 包安装，但 README 直接让用户运行 examples；
5. Tool governance hooks 没有进入 Agent 一等 API；
6. RiskClassificationPolicy 与 Resource 类型不匹配；
7. schema validator 不是完整 JSON Schema；
8. rate limiting 与 idempotency 顺序需要明确。

---

## 7.2 本质思考者

v0.5.1 的本质变化是：

> petfishFramework 开始把“工具可信边界”从普通 native tool 扩展到 MCP server / external tool ecosystem。

这非常关键。

企业 Agent 最大风险之一不是模型回答错，而是：

```text
Agent 调错工具
Agent 调了漂移 schema 的工具
Agent 调了未经授权的 MCP server
Agent 调了高风险 capability
Agent 对外部工具调用没有 rate limit / retry / timeout / idempotency
```

v0.5.1 正在直接处理这些问题。

---

## 7.3 机会挖掘者

v0.5.1 已经可以讲一条更完整的 MCP governance 叙事：

```text
MCP Server Discovery
  -> Allowlist blocks unknown servers
  -> SchemaPin detects tool contract drift
  -> MCPRiskMapper classifies risk by capabilities
  -> MCPToolWrapper normalizes external tools into Tool
  -> RuntimeEnvironment validates schema and rate-limits
  -> PermissionPolicy controls action
  -> AuditReport / SIEM records result
  -> Trusted Publishing verifies package provenance
```

这个叙事比普通 Agent framework 更有差异化。

---

## 7.4 局外人

外部用户看到 PyPI 会觉得项目更成熟：

- 382 tests；
- Trusted Publishing；
- Tool/MCP governance roadmap；
- MCP client；
- YAML Policy；
- CredentialBroker；
- OTel/SIEM；
- Vault；
- Docker。

但他会被几个小坑卡住：

- Current Limitations 说 MCP server planned；
- examples 命令在 pip 安装环境下跑不通；
- docs/api.md 版本仍旧；
- raw markdown 仍压缩。

这些不是核心架构失败，但会影响第一印象和使用体验。

---

## 7.5 执行者

v0.5.2 建议只做 5 件事：

1. 修 PyPI/README MCP server status；
2. 修 API Reference 到 v0.5.1；
3. 修 examples 分发/运行说明；
4. 把 schema/rate/idempotency/timeout governance 暴露到 Agent/Session 或 ToolGovernance；
5. 做一次真正的 markdown/yaml/docker formatting patch。

---

## 8. v0.5.2 建议清单

## P0：文档状态同步

- [ ] Current Limitations: `MCP server mode Planned` → `MVP Available`;
- [ ] 标注 minimal MCP server 边界；
- [ ] docs/api.md 版本改为 v0.5.1 / v0.5.x；
- [ ] README roadmap 保持 v0.5.x current；
- [ ] Development tests count 保持 382。

## P0：examples 分发一致性

二选一：

- [ ] README 写 `From repository checkout: python examples/...`；
- [ ] 或把 examples 纳入 sdist；
- [ ] 或提供 `python -m petfishframework.examples.enterprise_expense`；
- [ ] 或提供 `petfish-example enterprise-expense` console script。

## P1：ToolGovernance 一等 API

建议：

```python
from petfishframework.tools import ToolGovernance

governance = ToolGovernance(
    schema_validator=ToolSchemaValidator(),
    rate_limiter=RateLimiter(),
    idempotency_store=IdempotencyStore(),
    timeout_policy=TimeoutPolicy(tool_call_timeout_s=5),
)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=tools,
    tool_governance=governance,
)
```

## P1：Risk policy 修复

- [ ] 给 `Resource` 增加 `risk_level`；
- [ ] 或让 `RiskClassificationPolicy` 根据 `classification` 映射；
- [ ] 或在文档中明确输入类型要求；
- [ ] 增加测试覆盖 LOW/MEDIUM/HIGH/CRITICAL。

## P1：idempotency / rate-limit 顺序

明确语义：

- 如果 rate limit 计请求，则当前顺序 OK；
- 如果 rate limit 计外部执行，则 idempotency cache 应在 rate-limit 前。

建议增加注释和测试。

## P2：格式化

- [ ] README.md 正常换行；
- [ ] CHANGELOG.md 正常换行；
- [ ] SECURITY.md 正常换行；
- [ ] `.github/workflows/*.yml` 正常换行；
- [ ] Dockerfile 正常多行；
- [ ] docs/*.md 正常换行；
- [ ] CI 加 prettier / markdownlint / yaml check。

---

## 9. 最终判断

v0.5.1 的回答是：

> 是的，v0.5.1 的 Tool/MCP governance 方向让我认可，核心能力已经不是空壳。

我满意的点：

- 382 tests；
- Trusted Publishing 继续正常；
- Quickstart 继续稳定；
- MCP allowlist 可用；
- schema pin / drift detection 可用；
- risk mapper 可用；
- MCPClient risk mapping 可用；
- minimal MCP server 可运行；
- schema validation 可用；
- rate limiter 可用；
- RuntimeEnvironment 已有 schema/rate/idempotency/retry/timeout wiring。

我不满意的点：

- PyPI 仍写 MCP server mode planned；
- API Reference 版本仍旧；
- examples 不随 pip 分发但 README 直接要求运行；
- docs/raw 仍压缩；
- governance hooks 尚未成为 Agent 一等 API；
- RiskClassificationPolicy 与 Resource 类型不匹配；
- idempotency / rate-limit 顺序需要明确。

建议下一步：

```text
v0.5.2:
  文档状态同步 + examples 分发修正 + ToolGovernance 一等 API + risk policy 修复 + formatting patch

v0.6.0:
  MCP server lifecycle/governance hardening + policy test harness + deployment reference

v1.0:
  API freeze + compatibility policy + external validation + production guide
```

---

## 10. 参考链接

- PyPI v0.5.1: https://pypi.org/project/petfishframework/0.5.1/
- PyPI provenance commit: https://github.com/kylecui/petfishFramework/tree/66bf962c7ea8961f545bf595509c280b0ea994a2
- README: https://github.com/kylecui/petfishFramework/blob/master/README.md
- API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
- CI workflow: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/ci.yml
