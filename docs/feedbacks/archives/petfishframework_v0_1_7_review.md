# petfishFramework v0.1.7 Review 与 Markdown 反馈

> 版本：`petfishframework==0.1.7`  
> 发布页：https://pypi.org/project/petfishframework/0.1.7/  
> 复测日期：2026-07-07  
> 复测重点：基于 v0.1.6 遗留问题，重点验证 `DEGRADE` fail-closed、event mask、Tool metadata、文档同步、生产可用性边界。

---

## 1. 总体结论

v0.1.7 是一次非常关键的语义修复版。

如果说 v0.1.6 的关键进步是：

> `MASK` 支持 input + output，`DEGRADE` 支持 fallback tool switching。

那么 v0.1.7 的关键进步是：

> `DEGRADE` 在没有 fallback tool 时已经 fail-closed，不再执行原始高风险工具。

这意味着 petfishFramework 的 6 种 `DecisionEffect` 已经从“定义齐全”进一步推进到“执行语义基本闭环”。

当前可以比较有底气地说：

> petfishFramework v0.1.7 已经具备 Alpha 阶段较完整的 permission-aware Agent runtime control skeleton。

但仍不建议说：

> petfishFramework 已经 production-ready。

原因是：策略引擎、CredentialBroker、结构化审计报告、deterministic rerun / resume、MCP server mode、工具治理、供应链安全、部署运维等生产级能力还未闭环。

---

## 2. 公开信息摘要

PyPI v0.1.7 页面显示：

| 项目 | 信息 |
|---|---|
| 包名 | `petfishframework` |
| 版本 | `0.1.7` |
| 发布时间 | 2026-07-07 |
| Python 要求 | `>=3.10` |
| License | MIT |
| Development Status | `3 - Alpha` |
| Extras | `openai` / `anthropic` / `mcp` |
| Tests badge | 213 |
| Quickstart | Zero-cost FakeModel quickstart |
| MCP client stdio | Available |
| MCP server mode | Planned |
| Deterministic rerun / resume | Planned |
| Trusted Publishing | No |

PyPI 当前项目描述为：

> A lightweight Python framework for reliable, auditable, budget-aware, and permission-aware AI agents.

该定位比早期 “general AI Agent framework” 更准确，但 PyPI 顶部摘要处仍出现 “a general AI Agent framework” 的旧描述，这仍建议同步修正。

---

## 3. Playground 复测摘要

## 3.1 测试环境

测试方式：

```bash
python3 -m venv /tmp/pf017
source /tmp/pf017/bin/activate
pip install petfishframework==0.1.7
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.1.7
```

---

## 3.2 核心测试结果

| 测试项 | v0.1.7 实测结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，显示 `0.1.7` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 通过，触发 `BudgetExceeded` | 稳定 |
| `DENY` | 通过，工具未执行 | 正确 |
| `REQUIRE_APPROVAL` | 通过，工具未执行 | 正确 |
| `PARTIAL_ALLOW` | 通过，执行前裁剪参数 | 正确 |
| `MASK` input mask | 通过，执行前移除敏感字段 | 正确 |
| `MASK` output mask | 通过，返回结果脱敏 | 正确 |
| `MASK` event mask | 通过，事件日志中指定字段被 redact | 重要进步 |
| nested mask | 未发现 dot-path 语义生效 | 仍需增强 |
| `DEGRADE` with fallback | 通过，原工具不执行，fallback 执行 | 正确 |
| `DEGRADE` without fallback | 通过 fail-closed，原工具不执行 | 修复 v0.1.6 最大风险 |
| `session.replay()` | 通过 | 事件可用 |
| `pass_at_k_with_perturbations` | 通过 | 稳定 |
| Tool metadata | `BaseTool` 已支持 `side_effect` / `idempotent` / `external_egress` / `requires_credentials` | 重要进步 |
| MCP client stdio | PyPI 标为 available；此前实测可用 | 保留为能力点 |
| GitHub API reference | 仍有旧表述称 MCP stdio stub | 文档同步仍需修 |

---

## 4. 关键进步一：`DEGRADE` 已经 fail-closed

## 4.1 v0.1.6 的问题

v0.1.6 中，`DEGRADE` 已经可以 fallback tool switching。

但有一个严重残余问题：

```text
DEGRADE without fallback
  -> original tool may execute
```

这不符合安全框架的 fail-closed 原则。

因为 `DEGRADE` 的语义本质是：

> 原路径风险过高，不能按原路径执行，应切换到低风险路径。

如果没有低风险路径，正确做法应该是阻断，而不是继续执行原高风险工具。

---

## 4.2 v0.1.7 的实测结果

v0.1.7 中，当 policy 返回：

```python
Decision(
    effect=DecisionEffect.DEGRADE,
    reason="no fallback",
)
```

实测结果：

```text
state == {}
event == tool.degrade_failed
executed == False
fallback_tool == None
```

这说明：

- 原始工具没有执行；
- fallback 工具也没有执行；
- 事件明确标记为 `tool.degrade_failed`；
- `executed=False`；
- 运行时选择了 fail-closed。

这是 v0.1.7 最重要的修复。

---

## 4.3 正确语义已经基本成立

现在 `DEGRADE` 的语义可以整理为：

```text
DEGRADE + fallback_tool exists
  -> do not execute original tool
  -> execute fallback tool
  -> emit tool.degraded
  -> original_executed = false
  -> fallback_executed = true

DEGRADE + fallback_tool missing
  -> do not execute original tool
  -> emit tool.degrade_failed
  -> executed = false
```

这已经符合 runtime access control 的安全直觉。

---

## 5. 关键进步二：`event_mask_fields` 已经出现

v0.1.7 的 `Decision` 已经包含：

```python
event_mask_fields: tuple[str, ...] | None
```

复测中，当 policy 返回：

```python
Decision(
    effect=DecisionEffect.MASK,
    reason="event mask",
    event_mask_fields=("ssn",),
)
```

事件日志中：

```text
args.ssn == "[REDACTED]"
```

这说明 v0.1.7 开始解决一个非常重要的问题：

> 审计日志不能成为新的敏感数据泄漏源。

---

## 5.1 当前 mask 能力状态

当前可以认为 v0.1.7 具备三类 mask 的基础：

| 类型 | 状态 | 说明 |
|---|---|---|
| input mask | 可用 | 工具执行前移除指定字段 |
| output mask | 可用 | 工具返回后脱敏指定字段 |
| event mask | 基础可用 | 写事件前 redact 指定字段 |

这是从“功能性脱敏”走向“审计安全”的关键一步。

---

## 5.2 仍需增强：nested mask

复测发现，类似：

```python
input_mask_fields=("nested.ssn",)
output_mask_fields=("nested.ssn",)
```

未观察到 dot-path nested mask 生效。

例如输入：

```json
{
  "name": "alice",
  "nested": {
    "ssn": "456"
  }
}
```

使用 `nested.ssn` mask 后，工具仍可能收到：

```json
{
  "nested": {
    "ssn": "456"
  }
}
```

建议下一阶段支持：

```text
user.ssn
user.cards[*].number
invoice.vendor.tax_id
```

并支持多种 mask mode：

| mode | 语义 |
|---|---|
| drop | 删除字段 |
| redact | 替换为 `[MASKED]` |
| hash | 替换为 hash |
| preserve_format | 保留格式，例如 `****-****-****-1234` |

---

## 6. 关键进步三：Tool metadata 已经进入 BaseTool

复测中，`BaseTool` 构造签名已经包含：

```python
side_effect: bool = False
idempotent: bool = True
external_egress: bool = False
requires_credentials: bool = False
```

这是一项很重要的生产化基础能力。

因为真正的企业 Agent runtime 不能只知道 tool name，还要知道：

- 这个工具有没有副作用；
- 是否幂等；
- 是否会访问外部网络；
- 是否需要凭据；
- 是否可能写入业务系统；
- 是否可以重试；
- 是否需要审批；
- 是否应该进入沙箱。

---

## 6.1 建议继续扩展 Tool metadata

建议下一阶段继续加入：

```python
risk_level: RiskLevel
capabilities: tuple[str, ...]
side_effect: bool
idempotent: bool
external_egress: bool
requires_credentials: bool
reversible: bool
timeout_ms: int
max_retries: int
rate_limit: str
data_reads: tuple[str, ...]
data_writes: tuple[str, ...]
external_domains: tuple[str, ...]
sandbox_required: bool
```

这会让 policy 更容易表达：

```python
if resource.tool.side_effect and subject.role != "approver":
    return Decision(effect=DecisionEffect.REQUIRE_APPROVAL)

if resource.tool.external_egress and "network.egress" not in subject.capabilities:
    return Decision(effect=DecisionEffect.DENY)

if resource.tool.requires_credentials:
    return Decision(effect=DecisionEffect.DEGRADE, fallback_tool="dry_run")
```

---

## 7. DecisionEffect 当前成熟度

到 v0.1.7，6 种 effect 的执行语义可总结如下：

| DecisionEffect | 当前状态 | 评价 |
|---|---|---|
| `ALLOW` | 正常执行 | 可用 |
| `DENY` | pre-execution block | 可用 |
| `REQUIRE_APPROVAL` | pre-execution block | 可用 |
| `PARTIAL_ALLOW` | pre-execution arg filtering | 可用 |
| `MASK` | input/output/event mask 基础可用 | 基本可用，需 nested mask |
| `DEGRADE` | fallback switching + no fallback fail-closed | 基本可用 |

这意味着 v0.1.7 已经完成了从“权限模型定义”到“权限执行骨架”的关键跃迁。

---

## 8. 与 v0.1.6 的对比

| 维度 | v0.1.6 | v0.1.7 |
|---|---|---|
| Quickstart | 可跑 | 可跑 |
| Budget | 可用 | 可用 |
| DENY | 正确 | 正确 |
| REQUIRE_APPROVAL | 正确 | 正确 |
| PARTIAL_ALLOW | 正确 | 正确 |
| MASK input/output | 可用 | 可用 |
| event mask | 未明确 | 基础可用 |
| nested mask | 未完成 | 仍未完成 |
| DEGRADE with fallback | 可用 | 可用 |
| DEGRADE without fallback | 原工具可能执行 | fail-closed，原工具不执行 |
| Tool metadata | 初步 | `BaseTool` 明确包含关键字段 |
| 文档 | PyPI 较好，GitHub API ref 冲突 | 冲突仍在 |
| 生产可用性 | 不建议 | 仍不建议，但已更接近企业 PoC |
| 企业 PoC 可用性 | 接近 | 更接近 |

---

## 9. 当前仍然存在的问题

## 9.1 文档同步仍是最大可信度问题

PyPI v0.1.7 页面写得比较完整：

- MCP client stdio available；
- Tests 213；
- Permission effects enforced；
- API reference 989-line definitive reference；
- Current Limitations 状态表较清楚。

但 GitHub `docs/api.md` 仍存在旧表述，例如：

```text
Real stdio transport is stubbed by connect_stdio, which raises NotImplementedError.
```

这与 PyPI v0.1.7 的 MCP client stdio available 互相冲突。

此外，GitHub API reference 开头仍写 v0.1.0。这会让认真读文档的用户困惑：

> 到底 PyPI 页面可信，还是 GitHub API Reference 可信？

建议 v0.1.8 前必须同步：

- README；
- PyPI long_description；
- docs/api.md；
- docs/usage.md；
- CHANGELOG；
- benchmark docs；
- examples；
- tests count；
- current limitations；
- MCP 状态；
- Replay 状态；
- DecisionEffect 状态。

---

## 9.2 PyPI 短描述仍有旧定位

PyPI v0.1.7 顶部仍显示：

```text
petfishFramework — a general AI Agent framework
```

但项目描述正文已经是：

```text
A lightweight Python framework for reliable, auditable, budget-aware, and permission-aware AI agents.
```

建议统一为后者。

因为“general AI Agent framework” 会削弱差异化。

更建议的短描述：

```text
A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.
```

---

## 9.3 Trusted Publishing 仍未启用

PyPI 文件元数据仍显示：

```text
Uploaded using Trusted Publishing? No
Uploaded via: twine
```

对普通库可以接受，但对于一个主打安全、审计、运行时控制的框架，建议尽快启用：

- PyPI Trusted Publishing；
- release provenance；
- signed release；
- SBOM；
- dependency scanning；
- SECURITY.md；
- vulnerability disclosure policy。

---

## 9.4 Replay 仍需区分“可审计”与“可复现”

PyPI v0.1.7 Current Limitations 明确写：

```text
Session replay: Audit replay available
Deterministic rerun / resume: Planned
```

这是准确的。

但 Core Concepts 中仍有：

```text
Replay AUDIT, RESUME, RERUN
```

建议避免让用户误解为 deterministic replay / resume 已完整可用。

推荐表述：

```text
Replay: AUDIT event replay is available.
Deterministic RERUN and checkpoint RESUME are planned / experimental.
```

---

## 9.5 MCP client 与 MCP server 的边界仍需写清楚

PyPI v0.1.7 写：

```text
MCP client stdio: Available
MCP server mode: Planned
```

这是清楚的。

但 API Reference 仍称 stdio transport stub，必须修。

建议明确：

```text
MCP client stdio transport: available.
MCP server mode: planned.
MCP governance, server allowlist, schema pinning, authentication, lifecycle hardening: future work.
```

---

## 9.6 Policy Engine / CredentialBroker 尚未闭环

v0.1.7 已经把 effect 执行语义做得不错，但生产级还需要：

- YAML policy；
- policy composition；
- policy versioning；
- policy test harness；
- policy audit；
- CredentialBroker；
- scoped temporary credentials；
- vault integration；
- credential event masking；
- policy migration guide。

目前仍主要是开发者自定义 Python policy。

---

## 10. 五顾问评判

## 10.1 反对者

v0.1.7 不能说 production-ready。

理由：

1. 文档互相冲突仍然存在；
2. PyPI short description 仍是 general AI Agent framework；
3. nested mask 尚未完成；
4. CredentialBroker 尚未实现；
5. YAML policy engine 尚未实现；
6. deterministic replay / resume 尚未完成；
7. MCP server mode 尚未完成；
8. Trusted Publishing / SBOM / SECURITY.md 等供应链安全能力未闭环。

结论：

> v0.1.7 证明了 runtime access control 骨架越来越可信，但仍不是生产级安全框架。

---

## 10.2 本质思考者

v0.1.7 的本质价值是：

> 6 种 DecisionEffect 的执行语义已经基本形成闭环。

这比新增功能更重要。

Agent 安全的关键不是提示词，而是 runtime：

```text
模型可以提出动作
但是否执行、如何执行、是否降级、是否脱敏、是否审批
必须由 RuntimeEnvironment 仲裁
```

v0.1.7 已经把这个原则体现得更完整。

---

## 10.3 机会挖掘者

现在可以更有底气地对外讲：

> petfishFramework is an Alpha-stage runtime control framework for AI agents.

差异化已经很清楚：

- 不是普通 Agent 编排；
- 不是只做 prompt；
- 不是只做工具封装；
- 而是在 Agent 执行路径上统一做 permission、budget、audit、mask、degrade、Pass^k。

这与企业 AI 从 PoC 到生产的核心需求高度一致。

---

## 10.4 局外人

外部开发者会看到：

- Quickstart 能跑；
- PyPI 页面比较完整；
- tests badge 是 213；
- permission effects 状态表清楚；
- Current Limitations 比较诚实。

但如果他继续点 API Reference，就会看到 MCP stub 的旧说法。

这会让用户产生疑问：

> 这个项目到底哪个文档是真的？

所以 v0.1.8 最应该做的不是继续堆 feature，而是修文档一致性。

---

## 10.5 执行者

v0.1.8 建议只做六件事：

1. 同步 PyPI / README / API Reference / CHANGELOG；
2. 修 short description；
3. 增加 nested mask；
4. 增加 structured audit report；
5. 启用 CI badge、coverage badge、Trusted Publishing；
6. 写一个企业 PoC demo。

这些比新增另一个 reasoning strategy 更重要。

---

## 11. v0.1.8 建议路线

## 11.1 P0：文档同步

必须修：

- `docs/api.md` 版本号；
- MCP stdio 状态；
- Replay 状态；
- DecisionEffect 状态；
- Tests count；
- Current Limitations；
- PyPI short description；
- README 与 PyPI 一致性。

建议加入自动检查：

```text
docs code snippets -> pytest
README quickstart -> pytest
PyPI long_description generated from README
tests count generated automatically
```

---

## 11.2 P1：nested mask

建议支持：

```text
user.ssn
user.cards[*].number
invoice.vendor.tax_id
```

并支持：

```python
Decision(
    effect=DecisionEffect.MASK,
    input_mask_fields=("user.ssn",),
    output_mask_fields=("invoice.card.number",),
    event_mask_fields=("raw_prompt", "tool_args.api_key"),
)
```

---

## 11.3 P1：structured audit report

基于 `session.replay()` 生成：

- JSON trace；
- Markdown report；
- HTML report 可后续再做。

最小 Markdown report：

```markdown
# Session Audit Report

## Summary

- Session ID:
- Agent:
- Model:
- Status:
- Total Tokens:
- Tool Calls:
- Permission Decisions:

## Timeline

| Step | Event | Tool | Effect | Executed | Reason |
|---|---|---|---|---|---|

## Tool Calls

| Tool | Original Executed | Fallback Tool | Fallback Executed | Masked |
|---|---:|---|---:|---:|

## Budget

| Metric | Used | Limit |
|---|---:|---:|
```

---

## 11.4 P1：Tool metadata policy 示例

既然 `BaseTool` 已支持：

- `side_effect`
- `idempotent`
- `external_egress`
- `requires_credentials`

建议增加官方示例：

```python
class SafeByDefaultPolicy:
    def evaluate(self, subject, action, resource, context):
        tool = context.tool_metadata

        if tool.side_effect and "approver" not in subject.roles:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason="side-effect tool requires approval",
            )

        if tool.external_egress:
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason="external egress degraded to dry-run",
                fallback_tool="dry_run",
            )

        return Decision(effect=DecisionEffect.ALLOW)
```

---

## 11.5 P2：企业 PoC demo

建议选择：

> Enterprise Expense Approval Agent

覆盖：

- RAG policy retrieval；
- invoice validation tool；
- amount threshold policy；
- REQUIRE_APPROVAL；
- PARTIAL_ALLOW；
- MASK；
- DEGRADE；
- Budget；
- Replay；
- structured audit report；
- optional MCP tool。

这个 demo 会比更多算法 demo 更能体现 petfishFramework 的差异化。

---

## 11.6 P2：供应链可信度

建议补：

- GitHub Actions；
- coverage；
- Ruff；
- mypy；
- SBOM；
- Trusted Publishing；
- SECURITY.md；
- vulnerability disclosure；
- release checklist；
- signed artifact。

---

## 12. 生产可用性判断

## 12.1 当前可以说什么

可以说：

> petfishFramework v0.1.7 is an Alpha-stage runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.

可以说：

> v0.1.7 has enforced runtime semantics for ALLOW, DENY, REQUIRE_APPROVAL, PARTIAL_ALLOW, MASK, and DEGRADE, including fail-closed behavior when DEGRADE has no fallback.

可以说：

> It is suitable for experimentation and controlled enterprise PoC design.

---

## 12.2 当前不应说什么

不建议说：

- production-ready；
- enterprise-grade access control platform；
- complete policy engine；
- complete credential governance；
- complete MCP support；
- deterministic replay completed；
- fully hardened security framework；
- benchmark-proven superior to mainstream agent frameworks；
- safe by default in all production environments。

---

## 12.3 当前最合适定位

中文建议：

> petfishFramework 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备较完整的权限效果执行骨架，重点解决工具调用、权限语义、预算硬限制、审计回放和可靠性评测问题。

英文建议：

> petfishFramework is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents.

---

## 13. 最终结论

v0.1.7 是一次关键版本。

它最重要的成果不是新增了很多功能，而是修复了 v0.1.6 中 `DEGRADE` 无 fallback 时可能执行原工具的安全语义风险。

到 v0.1.7 为止：

- `DENY`：不执行；
- `REQUIRE_APPROVAL`：不执行；
- `PARTIAL_ALLOW`：先裁剪再执行；
- `MASK`：input / output / event mask 基础可用；
- `DEGRADE`：有 fallback 则执行 fallback，无 fallback 则 fail-closed；
- `Budget`：可硬中断；
- `Replay`：audit replay 可用；
- `Pass^k`：可靠性评测可用；
- `Tool metadata`：已经进入 BaseTool。

这说明 petfishFramework 已经不再只是“有安全概念的 Agent 框架”，而是正在形成一个真正的 runtime control skeleton。

下一步最重要的不是继续增加功能，而是：

1. 修文档一致性；
2. 做 nested mask；
3. 做 structured audit report；
4. 做企业 PoC demo；
5. 做 policy engine 和 CredentialBroker；
6. 做供应链安全与 CI/CD。

只要这些继续推进，petfishFramework 可以比较自然地从 Alpha runtime 进入企业 PoC 可用阶段。

---

## 14. 参考链接

- PyPI v0.1.7: https://pypi.org/project/petfishframework/0.1.7/
- GitHub Repository: https://github.com/kylecui/petfishFramework
- API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
