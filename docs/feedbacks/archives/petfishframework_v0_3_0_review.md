# petfishFramework v0.3.0 Review 与反馈

> 版本：`petfishframework==0.3.0`  
> 发布页：https://pypi.org/project/petfishframework/0.3.0/  
> 本次重点：验证 v0.3.0 的 YAML Policy Engine、CredentialBroker、CI + Publish、Trusted Publishing、文档一致性，以及 runtime 主链路是否继续稳定。

---

## 1. 总体结论

v0.3.0 是一个实质性版本。

如果说 v0.2.x 解决的是：

> runtime control skeleton：DecisionEffect、mask、degrade、AuditReport、企业 PoC demo、CI / SECURITY.md。

那么 v0.3.0 解决的是：

> policy / credential 两个生产化前置能力的第一阶段落地。

本次核验结论：

> v0.3.0 的大方向成立：YAML Policy Engine、CredentialBroker、Trusted Publishing、CI + Publish 都已经进入公开发布物与代码路径；Quickstart、Budget、Permission、AuditReport、Pass^k 等核心路径继续可用。

但仍不能说 production-ready。当前最主要的残余问题不是 runtime 语义，而是：

1. 文档状态矩阵与版本号仍有同步尾巴；
2. CredentialBroker 已有 direct runtime hook，但还没有成为 Agent / Session 的一等用户 API；
3. Credential token 在 event data 中仍以对象形式存在，虽然 `repr` / `str` 不泄露 secret，但对不可信 in-process event sink 仍应进一步收紧；
4. YAML Policy Engine 是 Phase A1，条件能力较窄，尚不是完整企业策略引擎；
5. deterministic rerun / resume、MCP server mode、生产部署与 OpenTelemetry / SIEM 仍未完成。

推荐定位：

> petfishFramework v0.3.0 已经从“企业 PoC 可展示的 Alpha runtime”推进到“具备策略与凭据治理雏形的 Alpha-stage Agent runtime control framework”。

---

## 2. PyPI 与发布状态

PyPI v0.3.0 页面显示：

| 项目 | 状态 |
|---|---|
| 版本 | `0.3.0` |
| 发布时间 | 2026-07-08 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| Tests | 259 |
| Trusted Publishing | Yes |
| Source distribution | `petfishframework-0.3.0.tar.gz` |
| Wheel | `petfishframework-0.3.0-py3-none-any.whl` |
| Provenance / attestation | 已有 |
| YAML Policy Engine | Available |
| Credential Broker | Available |
| Deterministic rerun / resume | Planned |
| MCP server mode | Planned |

本次最重要的发布层变化是：

> Trusted Publishing 已经启用，PyPI 文件详情显示 `Uploaded using Trusted Publishing? Yes`，并且 PyPI 页面展示了 attestation / provenance 信息，指向 GitHub `publish.yml` 工作流与 `v0.3.0` tag。

这解决了前几轮一直跟踪的供应链可信度问题。

---

## 3. Playground 实测摘要

## 3.1 安装与版本

测试命令：

```bash
python3 -m venv /tmp/pf030
source /tmp/pf030/bin/activate
pip install petfishframework==0.3.0
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.3.0
```

---

## 3.2 核心功能实测

| 测试项 | 结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，`0.3.0` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 通过 | 继续可用 |
| DecisionEffect 主链路 | 继承 v0.2.x 行为 | 未发现回归 |
| `DEGRADE` fallback | 通过 | 原工具不执行，fallback 执行 |
| `DEGRADE` no fallback | 通过 | fail-closed |
| nested / event mask | 继承 v0.2.x 行为 | 未发现回归 |
| AuditReport 默认 Result | 通过 | Markdown 中有 Final Output / usage |
| Pass^k | 通过 | 继续可用 |
| YAML Policy from string | 通过 | 可加载规则并按 priority 匹配 |
| YAML condition: `subject.role_not_in` | 通过 | 可 DENY |
| YAML condition: `action.args.amount_gt` | 通过 | 可 REQUIRE_APPROVAL |
| YAML condition: `tool.external_egress` | 通过 | 可 DEGRADE 到 fallback |
| CredentialBroker | 通过 | 可注册 credential、签发 scoped token、TTL 过期、revoke |
| Credential token repr/str | 通过 | 不泄露原始 secret |
| RuntimeEnvironment credential injection | 通过，但需要显式传 `_credential_broker` | 仍需 API 化 |

---

## 4. YAML Policy Engine 核验

## 4.1 已经可用的能力

v0.3.0 的 `YamlPolicy` 已经可以：

- `YamlPolicy.from_file(path)`
- `YamlPolicy.from_string(yaml_text)`
- 按 `priority` 降序匹配规则；
- first match wins；
- 规则命中后返回 `Decision`；
- 将 policy `version` / `name` 写入 `Decision`；
- 支持 `fallback_tool` / `fallback_args`；
- 支持 `input_mask_fields` / `output_mask_fields` / `event_mask_fields`；
- 支持 `allowed_fields`；
- 通过 `register_tools(tools)` 读取 tool metadata。

实测 YAML 示例：

```yaml
version: "1.0"
name: "expense"
rules:
  - name: deny-non-finance
    priority: 100
    when:
      action.tool_name: approve_payment
      subject.role_not_in: [finance, admin]
    effect: DENY
    reason: "only finance/admin can approve"

  - name: require-large
    priority: 90
    when:
      action.tool_name: approve_payment
      action.args.amount_gt: 1000
    effect: REQUIRE_APPROVAL
    reason: "large payment"

  - name: external-egress-degrade
    priority: 80
    when:
      tool.external_egress: true
    effect: DEGRADE
    reason: "external egress"
    fallback_tool: dry_run
    fallback_args:
      ok: true

  - name: default-allow
    priority: 0
    when: {}
    effect: ALLOW
    reason: "ok"
```

实测结果：

| 输入 | 决策 |
|---|---|
| 非 finance 调 `approve_payment` | `DENY` |
| finance 调 `approve_payment` 且 amount > 1000 | `REQUIRE_APPROVAL` |
| tool metadata `external_egress=True` | `DEGRADE` 到 fallback |
| 无规则命中 | `ALLOW` |

---

## 4.2 当前 matcher 范围

源码中的条件 matcher 目前支持：

| 条件键 | 含义 |
|---|---|
| `action.tool_name` | exact match |
| `subject.role_in` | subject roles 中任一角色在列表内 |
| `subject.role_not_in` | subject roles 中没有任何角色在列表内 |
| `action.args.amount_gt` | `action.args["amount"] > value` |
| `action.args.amount_lt` | `action.args["amount"] < value` |
| `tool.side_effect` | 匹配 tool metadata |
| `tool.external_egress` | 匹配 tool metadata |

未知 condition key 是 fail-closed：返回 `False`，不会误匹配。

这个设计是安全方向正确的，但说明它仍是 Phase A1，而不是完整策略 DSL。

---

## 4.3 YAML Policy Engine 的当前边界

当前还不是完整企业策略引擎，原因包括：

- 条件键是固定白名单，不是通用 JSONPath；
- 暂无 AND / OR / NOT 组合语法；
- 暂无 resource classification / tenant / project / clearance matcher；
- 暂无 policy inheritance / composition；
- 暂无 deny-overrides / allow-overrides 模式；
- 暂无 policy test harness；
- 暂无 policy migration / version diff；
- 暂无策略加载时的 schema validation 报告；
- `register_tools()` 当前只记录 `side_effect` 和 `external_egress`，尚未覆盖 `requires_credentials`、`risk_level`、`capabilities` 等更多 metadata。

建议将其定位为：

> YAML Policy Engine Phase A1：可用于企业 PoC 和简单规则治理，但还不是完整生产级策略系统。

---

## 5. CredentialBroker 核验

## 5.1 已经可用的能力

v0.3.0 新增了：

```python
from petfishframework.credentials import CredentialBroker, ScopedToken
```

已实测能力：

- `register_credential(name, secret)`
- `issue_token(name, tool_name, ttl_s=None)`
- `validate_token(token_id)`
- `revoke_token(token_id)`
- `cleanup_expired()`
- `ScopedToken.is_valid()`
- `ScopedToken.get_secret()`
- `ScopedToken.__repr__()` / `__str__()` 隐藏 secret

实测结果：

```text
repr has secret? False
str has secret? False
valid before expiry: True
valid after expiry: False
expired token get_secret() raises ValueError
```

这说明 CredentialBroker 的最小闭环已经成立。

---

## 5.2 RuntimeEnvironment credential injection

`RuntimeEnvironment` 中已经有 `_credential_broker` 字段和 `_maybe_inject_credential()` hook。

实测：

- tool 声明 `requires_credentials=True`；
- broker 注册 credential；
- RuntimeEnvironment 配置 `_credential_broker=broker`；
- tool 执行前 args 中会注入 `_credential_token`；
- token 对象的 `repr` / `str` 不暴露 secret；
- tool 内部可通过 `token.get_secret()` 取出真实 secret。

这说明 v0.3.0 已经不是“只有 CredentialBroker 类”，而是有 runtime integration hook。

---

## 5.3 当前 CredentialBroker 的关键问题

## 问题一：还没有 Agent / Session 一等 API

当前 `Agent` 构造函数没有 `credential_broker` 参数，`Session` 创建路径也不会自动传 broker。

也就是说，普通用户不能自然写：

```python
agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=tools,
    credential_broker=broker,
)
```

而需要直接构造 `RuntimeEnvironment` 或修改内部路径。

这意味着：

> CredentialBroker 已经进入 runtime hook，但还没有完成用户层 API 闭环。

建议 v0.3.1 增加：

```python
@dataclass(frozen=True)
class Agent:
    ...
    credential_broker: CredentialBroker | None = None
```

并在 `Session._prepare_run()` 中传给 `RuntimeEnvironment`。

---

## 问题二：event data 中仍含 ScopedToken 对象

实测中，`tool.called` event 的 `args` 中出现：

```python
"_credential_token": ScopedToken(..., _secret='[REDACTED]')
```

`repr` 是安全的，不会显示 secret。

但对象本身仍是 `ScopedToken`，不可信的 in-process sink 如果拿到 event object，理论上可以调用：

```python
event.data["args"]["_credential_token"].get_secret()
```

这对“日志文本”不是泄漏，但对“不可信事件消费者”仍是风险。

建议 v0.3.1 修：

- tool 执行时 args 中可以有 `ScopedToken`；
- 但 event emission 前必须把 token 对象替换为：

```python
{
  "credential_ref": token.token_id,
  "tool_name": token.tool_name,
  "redacted": True,
}
```

更严格的做法：

```python
event_args["_credential_token"] = "[CREDENTIAL_REF:abc123]"
```

原则：

> secret-bearing object 不应进入 event log，即使它的 repr 是 redacted。

---

## 问题三：Credential name 绑定方式需要文档化

当前 `_maybe_inject_credential()` 使用：

```python
broker.issue_token(tool.name, tool_name=tool.name)
```

这意味着 credential name 默认等于 tool name。

这很简单，但企业场景里经常需要：

```text
tool = github_create_issue
credential = github_app_installation_token
```

建议后续扩展：

```python
BaseTool(
    name="github_create_issue",
    requires_credentials=True,
    credential_name="github_app",
)
```

或者：

```yaml
credentials:
  github_create_issue: github_app
```

---

## 6. Trusted Publishing / Publish 核验

v0.3.0 在发布可信度上有明显进步。

PyPI 文件详情显示：

- Source distribution 和 wheel 都是 Trusted Publishing；
- PyPI 页面展示了 attestation bundle；
- provenance 指向 GitHub `publish.yml`；
- trigger 是 `push`；
- source repository 是公开仓库；
- workflow 使用 OIDC token，而不是 API token。

GitHub `publish.yml` 也显示：

- tag `v*` 触发；
- build job 先跑 tests 和 ruff；
- build package；
- publish job 使用 `id-token: write`；
- 使用 `pypa/gh-action-pypi-publish@release/v1`；
- 无 password / token。

这解决了前几轮 deferred 的 Trusted Publishing 问题。

---

## 7. CI 核验

GitHub Actions 页面列出了 v0.3.0 的：

- `Publish to PyPI #5`
- `CI #24`

并显示 commit `e88c395`，对应 `release: v0.3.0 — YAML Policy Engine + CredentialBroker + Enterprise ...`。

CI workflow 文件显示：

- Python matrix：3.10 / 3.11 / 3.12；
- `uv sync --all-extras`；
- `uv run ruff check src/ tests/`；
- `uv run pytest tests/ -q --tb=short`；
- integration tests 在无 API key 时跳过。

PyPI 的 Trusted Publishing provenance 进一步证明 publish workflow 成功执行并发布了 0.3.0。

---

## 8. 文档与状态矩阵问题

v0.3.0 的文档同步比早期好，但仍存在几个明显尾巴。

## 8.1 API Reference 版本号不一致

GitHub HTML 视图中 `docs/api.md` 写：

```text
public API of petfishFramework v0.2.5
```

而 raw 抓取中仍出现过：

```text
public API of petfishFramework v0.1.9
```

无论哪个是缓存或渲染问题，对 v0.3.0 都不准确。

建议修成：

```text
public API of petfishFramework v0.3.0
```

更好做法：

```text
public API of petfishFramework v0.3.x
Last validated against: 0.3.0
```

---

## 8.2 Roadmap 中 “v0.2.x current” 已过期

PyPI / README 中仍有：

```text
v0.2.x (current): Core runtime, permission semantics, enterprise PoC, Trusted Publishing ✅
v0.3.x: Policy engine (YAML), credential broker ✅
```

对 v0.3.0 来说，`current` 应该改成 v0.3.x。

建议：

```text
v0.2.x: Core runtime, permission semantics, enterprise PoC, Trusted Publishing ✅
v0.3.x (current): YAML Policy Engine, CredentialBroker ✅
v0.4.x: Production hardening, deployment guides
```

---

## 8.3 API Reference 缺少 CredentialBroker 独立章节

`docs/api.md` 已经有 YAML Policy Engine 章节，但没有检索到 `CredentialBroker` 的独立 API 章节。

这与 PyPI Current Limitations 中的：

```text
Credential Broker ✅ Available
```

不完全匹配。

建议新增章节：

```markdown
## 16. Credential Broker

from petfishframework.credentials import CredentialBroker, ScopedToken

...
```

并说明：

- broker API；
- token lifecycle；
- repr / str redaction；
- RuntimeEnvironment integration；
- Agent / Session API 状态；
- event log safety caveat；
- 推荐 credential name mapping。

---

## 8.4 README / PyPI 没有展示 YAML / Credential 用法

PyPI / README 只在状态矩阵中列出：

```text
YAML Policy Engine ✅ Available
Credential Broker ✅ Available
```

但正文没有最小例子。

建议增加两个短示例：

```python
policy = YamlPolicy.from_file("examples/policies/enterprise-expense.yaml")
policy.register_tools(tools)
agent = Agent(..., permission_policy=policy)
```

```python
broker = CredentialBroker()
broker.register_credential("github_tool", os.environ["GITHUB_TOKEN"])
```

否则用户很难从 README 直接理解 v0.3.0 的新增价值。

---

## 9. 当前成熟度判断

## 9.1 可以说什么

现在可以说：

> petfishFramework v0.3.0 is an Alpha-stage runtime control framework with enforced permission effects, structured audit reports, a YAML Policy Engine, CredentialBroker, CI, and Trusted Publishing.

可以说：

> v0.3.0 is suitable for controlled enterprise PoC demonstrations where policies can be expressed in YAML and tools can receive scoped credential tokens through the runtime.

可以说：

> Trusted Publishing and provenance are now enabled for PyPI artifacts.

---

## 9.2 不应说什么

仍不建议说：

- production-ready；
- full enterprise policy engine；
- complete credential governance；
- secret-proof event system；
- full MCP server support；
- deterministic replay completed；
- resume completed；
- deployment-hardened；
- SIEM / OTel ready；
- benchmark-proven superior to mainstream frameworks。

---

## 9.3 推荐定位

中文：

> petfishFramework v0.3.0 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备完整的核心权限效果执行语义、企业 PoC demo、结构化审计报告、YAML 策略引擎、CredentialBroker 雏形、CI 与 Trusted Publishing，适合受控企业 PoC 与架构验证，但仍需继续完善策略 DSL、凭据治理、事件安全与生产部署能力。

英文：

> petfishFramework v0.3.0 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, now with YAML policy rules, scoped credential tokens, CI, and Trusted Publishing.

---

## 10. 五顾问评判

## 10.1 反对者

v0.3.0 的问题已经不是“能不能跑”，而是“是否可以承受生产安全审查”。

主要反对点：

1. YAML Policy Engine 条件能力仍窄；
2. CredentialBroker 没有 Agent / Session 一等 API；
3. event log 中仍可能保存 `ScopedToken` 对象；
4. API Reference 版本号仍不一致；
5. CredentialBroker 缺少文档章节；
6. deterministic replay / resume 仍 planned；
7. MCP server mode 仍 planned；
8. 没有 deployment guide / OpenTelemetry / SIEM。

结论：

> v0.3.0 很适合 PoC，但还不能叫生产级。

---

## 10.2 本质思考者

v0.3.0 的本质突破是：

> runtime control 开始从“硬编码 Python policy”进入“可配置 policy + 凭据隔离”阶段。

这正是从 framework prototype 到 enterprise runtime 的关键过渡。

此前的核心问题是：

- 能不能 block；
- 能不能 mask；
- 能不能 degrade；
- 能不能 audit。

现在开始进入：

- 策略能不能配置；
- 凭据能不能不暴露给模型；
- 发布链路是否可信。

这是正确方向。

---

## 10.3 机会挖掘者

v0.3.0 已经足以讲一个更完整的企业叙事：

```text
企业报销审批 Agent
  -> YAML policy 定义角色 / 金额 / 工具风险
  -> RuntimeEnvironment 统一仲裁工具调用
  -> CredentialBroker 给需要凭据的工具发 scoped token
  -> DecisionEffect 控制 allow / deny / approval / mask / degrade
  -> AuditReport 输出可读审计
  -> Trusted Publishing 保证包发布可信
```

这比 v0.2.x 的 demo 更接近企业安全团队关心的问题。

---

## 10.4 局外人

外部用户看到 PyPI 会觉得项目明显专业化：

- 259 tests；
- Trusted Publishing；
- provenance；
- YAML Policy Engine；
- Credential Broker；
- Enterprise PoC；
- Current Limitations 清楚写 planned 项。

但如果用户点 API Reference，会看到 v0.2.5 / v0.1.9 的版本号问题；如果想学 CredentialBroker，也找不到 API Reference 章节。

这会造成“功能已经有，但文档入口不足”的问题。

---

## 10.5 执行者

v0.3.1 不建议继续大规模加功能。

优先做 5 件事：

1. 修 API Reference 版本号和 Roadmap current 状态；
2. 给 CredentialBroker 增加 API Reference 章节；
3. Agent / Session 增加 `credential_broker` 参数；
4. event log 中 credential token 改为 credential ref，不保留 token object；
5. README / PyPI 增加 YAML Policy + CredentialBroker 最小示例。

---

## 11. v0.3.1 建议清单

## P0：Credential event safety

当前：

```python
event.data["args"]["_credential_token"] = ScopedToken(...)
```

建议改成：

```python
event.data["args"]["_credential_token"] = {
    "credential_ref": token.token_id,
    "tool_name": token.tool_name,
    "redacted": True,
}
```

原则：

> event log 不应保存 secret-bearing object。

---

## P0：Agent / Session credential_broker API

建议：

```python
agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=tools,
    credential_broker=broker,
)
```

或：

```python
session = agent.session(task, credential_broker=broker)
```

当前 direct `RuntimeEnvironment` hook 适合测试，但不够用户友好。

---

## P1：CredentialBroker docs

新增：

```markdown
## Credential Broker

- register_credential
- issue_token
- validate_token
- revoke_token
- cleanup_expired
- ScopedToken repr/str redaction
- RuntimeEnvironment integration
- event log safety
- credential name mapping
```

---

## P1：YAML Policy docs 示例

新增 README 短示例：

```python
from petfishframework import YamlPolicy

policy = YamlPolicy.from_file("examples/policies/enterprise-expense.yaml")
policy.register_tools(tools)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=tools,
    permission_policy=policy,
)
```

并列出当前支持的 matcher。

---

## P1：Roadmap / version sync

修：

- `docs/api.md` version；
- PyPI / README `v0.2.x (current)`；
- API Reference “989-line definitive reference” 与实际行数；
- README / PyPI 当前能力状态。

---

## P2：YAML Policy Engine 下一步

建议 v0.3.x 后续增强：

- `resource.classification`
- `resource.tags`
- `subject.clearance`
- `subject.tenant_id`
- `context.prompt_risk`
- `action.args.<path>_gt/lt/eq`
- `tool.requires_credentials`
- `tool.risk_level`
- `tool.capabilities_contains`
- `any` / `all` / `not`
- policy schema validation
- policy test harness
- policy diff

---

## P2：CredentialBroker 下一步

建议后续增强：

- `credential_name` metadata；
- scoped capabilities；
- one-time token；
- token use count；
- token event reference only；
- vault adapter；
- per-tenant credential namespace；
- credential audit events；
- revocation on session end；
- tool credential allowlist。

---

## 12. 最终判断

v0.3.0 的回答是：

> 方向正确，而且核心新增能力已经真正落地。

具体来说：

- YAML Policy Engine 已经可加载规则并生成 Decision；
- CredentialBroker 已经能签发 scoped token；
- RuntimeEnvironment 已经能给 `requires_credentials=True` 的 tool 注入 token；
- token 的 repr / str 不泄露 secret；
- Trusted Publishing 已启用；
- PyPI provenance 已出现；
- CI + Publish 工作流都已进入公开 Actions 列表；
- runtime 主链路没有明显回归。

但 v0.3.0 仍是 Alpha：

- YAML Policy Engine 是 Phase A1；
- CredentialBroker 需要一等 Agent / Session API；
- event log 不应保存 token object；
- API Reference / Roadmap 仍有版本同步尾巴；
- deterministic replay / resume、MCP server、生产部署仍未完成。

我的建议是：

> v0.3.1 做小而关键的“credential hygiene + docs sync”版本；v0.3.x 后续再扩 YAML DSL 和 credential governance；v0.4.0 再进入 deployment / observability / production hardening。

---

## 13. 参考链接

- PyPI v0.3.0: https://pypi.org/project/petfishframework/0.3.0/
- GitHub Actions: https://github.com/kylecui/petfishFramework/actions
- GitHub API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
- publish.yml: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/publish.yml
- ci.yml: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/ci.yml
