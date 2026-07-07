# petfishFramework v0.1.8 Review 与后续建议

> 版本：`petfishframework==0.1.8`  
> 发布页：https://pypi.org/project/petfishframework/0.1.8/  
> 复测重点：基于 v0.1.7 遗留建议，验证文档定位、nested mask、event mask、structured audit report、Tool metadata、`DEGRADE` fail-closed、生产可用性距离。  
> 备注：Trusted Publishing 已明确 deferred to v0.2.0，因此本文不把 Trusted Publishing 作为 v0.1.9 的阻断项，只作为 v0.2.0 生产化跟踪项。

---

## 1. 总体结论

v0.1.8 是一次从“权限语义闭环”向“审计与可用性闭环”推进的版本。

v0.1.7 的核心价值是：

> `DEGRADE` 无 fallback 时已经 fail-closed，6 种 DecisionEffect 的执行语义基本闭环。

v0.1.8 的核心价值则是：

> 项目开始补 production-readiness 外围能力：structured audit report、event mask、nested mask、文档定位与测试数量同步。

总体判断：

> petfishFramework v0.1.8 已经具备较完整的 Alpha-stage Agent runtime control skeleton，并开始进入“企业 PoC 可用性”收口阶段。

但仍不应称为 production-ready，原因包括：

1. YAML Policy Engine 尚未实现；
2. CredentialBroker 尚未实现；
3. deterministic rerun / resume 仍是 planned；
4. MCP server mode 仍是 planned；
5. structured audit report 仍是 MVP；
6. GitHub API Reference 仍存在旧表述；
7. 生产部署、OpenTelemetry、SIEM、供应链与安全披露流程尚未闭环。

---

## 2. PyPI 公开信息摘要

PyPI v0.1.8 页面显示：

| 项目 | 信息 |
|---|---|
| 包名 | `petfishframework` |
| 版本 | `0.1.8` |
| 发布时间 | 2026-07-07 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| License | MIT |
| Extras | `openai` / `anthropic` / `mcp` |
| 短描述 | `A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.` |
| Tests badge | 218 |
| Quickstart | Zero-cost FakeModel quickstart |
| MCP client stdio | Available |
| MCP server mode | Planned |
| Deterministic rerun / resume | Planned |

v0.1.8 的 PyPI 短描述已经从早期的 “general AI Agent framework” 收敛为更准确的 runtime 定位：

> A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.

这是一项小但重要的修正。它避免了项目被误解为普通 Agent 编排库，也更符合实际差异化。

---

## 3. Playground 复测摘要

## 3.1 测试环境

```bash
python3 -m venv /tmp/pf018
source /tmp/pf018/bin/activate
pip install petfishframework==0.1.8
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.1.8
```

---

## 3.2 核心测试结果

| 测试项 | v0.1.8 实测结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，显示 `0.1.8` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 通过，触发 `BudgetExceeded` | 稳定 |
| `DENY` | 通过，工具未执行 | 正确 |
| `REQUIRE_APPROVAL` | 通过，工具未执行 | 正确 |
| `PARTIAL_ALLOW` | 通过，执行前裁剪参数 | 正确 |
| `MASK` input mask | 通过，执行前脱敏 | 正确 |
| `MASK` output mask | 通过，返回结果脱敏 | 正确 |
| `MASK` event mask | 通过，事件日志中指定字段被 redact | 正确 |
| nested mask | 通过，`nested.ssn` 可脱敏 | v0.1.7 遗留问题已修 |
| `DEGRADE` with fallback | 通过，原工具不执行，fallback 执行 | 正确 |
| `DEGRADE` without fallback | 通过 fail-closed，原工具不执行 | 正确 |
| `session.replay()` | 通过 | 事件可用 |
| structured audit report | 可用，支持 Markdown / JSON | MVP 已出现 |
| `audit_report_from_session(session)` 默认包含 Result | 未通过 | 当前 Session 不保留 `_result` |
| Tool metadata | `BaseTool` 已支持 side-effect 等字段 | 稳定 |
| MCP client stdio | 函数实现存在，PyPI 标为 available | API Reference 仍旧文档冲突 |

---

## 4. v0.1.8 的关键进步

## 4.1 PyPI 定位修正

v0.1.7 中，PyPI 短描述仍带有旧的 “general AI Agent framework” 味道。

v0.1.8 已经修正为：

```text
A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.
```

这很重要。

petfishFramework 的差异化不是：

```text
又一个通用 Agent 框架
```

而是：

```text
Agent runtime control framework
```

也就是：

- tool call 受控；
- model call 受控；
- retriever call 受控；
- budget hard limit；
- permission gate；
- event audit；
- replay；
- Pass^k reliability。

这个定位修正是对外叙事的必要收口。

---

## 4.2 nested mask 已经可用

v0.1.7 中我建议补 nested mask。

v0.1.8 实测发现，类似：

```python
input_mask_fields=("ssn", "nested.ssn")
output_mask_fields=("secret", "nested.ssn")
event_mask_fields=("name", "nested.ssn")
```

已经可以生效。

测试输入：

```python
{
    "name": "alice",
    "ssn": "123",
    "nested": {"ssn": "456"},
    "extra": "E",
}
```

工具实际收到：

```python
{
    "name": "alice",
    "ssn": "[MASKED]",
    "nested": {"ssn": "[MASKED]"},
    "extra": "E",
}
```

事件日志中，因为 `event_mask_fields=("name", "nested.ssn")`，记录变为：

```python
{
    "name": "[MASKED]",
    "ssn": "[MASKED]",
    "nested": {"ssn": "[MASKED]"},
    "extra": "E",
}
```

这说明 v0.1.8 已经完成了 v0.1.7 中最重要的 mask 增强之一。

---

## 4.3 event mask 已经实际可用

v0.1.7 中 `Decision` 已经包含 `event_mask_fields`，v0.1.8 实测确认该能力可用。

这很关键，因为审计日志本身也是敏感数据泄露面。

没有 event mask 时，框架可能出现：

```text
模型没看到 secret
工具返回也被 mask
但 audit log 里记录了原始 secret
```

v0.1.8 已经开始阻断这个风险。

当前可以认为 petfishFramework 已经有三类 mask 基础：

| 类型 | 发生时机 | 当前状态 |
|---|---|---|
| input mask | 工具执行前 | 可用 |
| output mask | 工具执行后 | 可用 |
| event mask | 写事件前 | 可用 |

---

## 4.4 structured audit report 已经出现

v0.1.8 中已经存在：

```python
from petfishframework.reliability.audit_report import (
    AuditReport,
    audit_report_from_session,
)
```

并支持：

```python
report.to_markdown()
report.to_json()
```

实测输出包括：

- Session ID；
- Model Calls；
- Tool Events；
- Permission Decisions；
- Timeline；
- Tool Calls；
- Permission Decisions；
- Final Output，如果 Report 中有 Result。

这是 v0.1.8 的一个关键进步。

因为生产可用的 Agent runtime 不仅要“记录事件”，还要能让人读懂：

- 哪个工具被调用；
- 哪个工具被阻断；
- 哪个动作被降级；
- 原工具是否执行；
- fallback 是否执行；
- 是否发生 mask；
- 权限决策是什么；
- 最终输出是什么。

---

## 4.5 `DEGRADE` fail-closed 继续保持正确

v0.1.8 中，`DEGRADE` 语义继续保持 v0.1.7 的正确行为。

### 有 fallback

```python
Decision(
    effect=DecisionEffect.DEGRADE,
    fallback_tool="safe",
    fallback_args={"name": "bob"},
)
```

实测结果：

```text
original tool calls: 0
fallback tool calls: 1
event: tool.degraded
original_executed: False
fallback_executed: True
```

### 无 fallback

```python
Decision(effect=DecisionEffect.DEGRADE)
```

实测结果：

```text
original tool calls: 0
event: tool.degrade_failed
executed: False
```

这说明 v0.1.6 的主要安全语义风险已经稳定修复。

---

## 5. 当前发现的问题

## 5.1 `audit_report_from_session(session)` 默认拿不到 Result

v0.1.8 已经提供 structured audit report，这是进步。

但实测发现：

```python
session = agent.session("calc")
result = session.run()

report = audit_report_from_session(session)
print(report.result)
```

输出：

```text
None
```

原因是：

```python
audit_report_from_session(session)
```

内部似乎读取：

```python
getattr(session, "_result", None)
```

但 `Session.run()` 当前没有把最后一次 `Result` 保存到 `session._result`。

因此，默认生成的 audit report 没有：

- Total Tokens；
- Cost；
- Steps；
- Final Output。

这会影响审计报告的完整性。

### 建议修复

方案 A：让 `Session.run()` 保存最后结果

```python
self._result = result
return result
```

方案 B：允许显式传入 result

```python
audit_report_from_session(session, result=result)
```

方案 C：两者都支持

```python
def audit_report_from_session(session, result=None):
    return AuditReport(
        session_id=session.session_id,
        events=session.replay(),
        result=result or getattr(session, "_result", None),
    )
```

建议采用方案 C。

---

## 5.2 structured audit report 仍是 MVP

当前 report 已经可用，但还比较基础。

建议继续补：

- budget section；
- model call section；
- result usage；
- masked fields summary；
- degraded calls summary；
- approval-required summary；
- blocked calls summary；
- event count by type；
- error section；
- trace integrity hash；
- policy version；
- tool metadata；
- subject/action/resource/context；
- raw args hash；
- raw result hash。

尤其是：

```text
executed
original_executed
fallback_executed
input_masked
output_masked
event_masked
```

这些字段应进入表格，方便安全团队阅读。

---

## 5.3 GitHub API Reference 仍存在严重旧文档问题

PyPI v0.1.8 页面已经说：

```text
MCP client stdio ✅ Available
```

但 GitHub `docs/api.md` 中仍出现：

```text
Real stdio transport is stubbed by connect_stdio, which raises NotImplementedError.
Both real transport directions are stubs in the current release.
```

这与 PyPI v0.1.8 和实际源码实现冲突。

另外，`docs/api.md` 开头仍写：

```text
public API of petfishFramework v0.1.0
```

这与 v0.1.8 也不一致。

这是当前最伤信任的问题之一。

v0.1.8 已经把 PyPI 页面做得比较好，但如果用户点进 API Reference，仍会遇到旧信息。

建议 v0.1.9 必须修：

- `docs/api.md` 版本号；
- MCP stdio 状态；
- Tool metadata signature；
- Decision fields；
- event_mask_fields；
- nested mask；
- audit_report；
- Current Limitations；
- Replay 状态。

---

## 5.4 Replay 文档仍需谨慎

PyPI Current Limitations 中写：

```text
Session replay ✅ Audit replay available
Deterministic rerun / resume Planned
```

这是准确的。

但 Core Concepts 表格中写：

```text
Replay AUDIT (event log), RESUME (checkpoint), RERUN (fresh)
```

这容易让人误会 RESUME / RERUN 已经可用。

建议改为：

```text
Replay: AUDIT event log available; deterministic RERUN and checkpoint RESUME planned.
```

或者在表格中明确：

| Replay Mode | Status |
|---|---|
| AUDIT | Available |
| RERUN | Planned |
| RESUME | Planned |

---

## 5.5 Tool metadata 已有基础，但尚未进入 policy 示例

`BaseTool` 已经支持：

```python
side_effect
idempotent
external_egress
requires_credentials
```

这是好事。

但文档和示例中仍应展示如何用 metadata 写策略。

否则 metadata 只是字段，没有成为治理能力。

建议提供一个 SafeByDefaultPolicy 示例：

```python
class SafeByDefaultPolicy:
    def evaluate(self, subject, action, resource, context):
        tool = context.get("tool_metadata")

        if tool.side_effect:
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

## 5.6 Trusted Publishing：按计划 deferred to v0.2.0

PyPI 文件元数据显示 v0.1.8 仍是：

```text
Uploaded using Trusted Publishing? No
Uploaded via: twine/6.2.0
```

用户已明确说明 Trusted Publishing deferred to v0.2.0。

因此本文不把它列为 v0.1.9 阻断项。

但建议在 roadmap 中保留：

```text
v0.2.0: Trusted Publishing, SBOM, SECURITY.md, release provenance
```

这对安全框架很重要，但可以作为 v0.2.0 生产化任务处理。

---

## 6. 与 v0.1.7 的对比

| 维度 | v0.1.7 | v0.1.8 |
|---|---|---|
| Quickstart | 可跑 | 可跑 |
| Budget | 可用 | 可用 |
| DENY | 正确 | 正确 |
| REQUIRE_APPROVAL | 正确 | 正确 |
| PARTIAL_ALLOW | 正确 | 正确 |
| MASK input/output | 可用 | 可用 |
| event mask | 基础可用 | 可用 |
| nested mask | 未确认生效 | 已确认生效 |
| DEGRADE with fallback | 可用 | 可用 |
| DEGRADE without fallback | fail-closed | fail-closed |
| Tool metadata | 已有关键字段 | 稳定 |
| structured audit report | 未重点确认 | 已有 MVP |
| audit report result attachment | 未确认 | 默认缺失 Result |
| PyPI 定位 | 基本正确 | 短描述已修正 |
| GitHub API Reference | 旧信息冲突 | 仍冲突 |
| Trusted Publishing | No | No，deferred to v0.2.0 |
| 企业 PoC 可用性 | 更接近 | 更进一步 |

---

## 7. 当前成熟度判断

## 7.1 可以说什么

可以说：

> petfishFramework v0.1.8 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents.

可以说：

> v0.1.8 has enforced runtime semantics for ALLOW, DENY, REQUIRE_APPROVAL, PARTIAL_ALLOW, MASK, and DEGRADE.

可以说：

> v0.1.8 supports input/output/event masking, nested field masking, DEGRADE fallback switching with fail-closed behavior, and structured audit report export.

可以说：

> It is suitable for experimentation and controlled enterprise PoC design.

---

## 7.2 不应说什么

不建议说：

- production-ready；
- enterprise-grade access control platform；
- complete policy engine；
- complete credential governance；
- complete MCP support；
- deterministic replay completed；
- checkpoint resume completed；
- fully hardened security framework；
- benchmark-proven superior to mainstream Agent frameworks；
- safe by default in all production environments。

---

## 7.3 当前最合适定位

中文：

> petfishFramework 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备较完整的权限效果执行骨架，并开始补齐审计报告、事件脱敏、嵌套脱敏等企业 PoC 所需能力。

英文：

> petfishFramework is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, now with enforced permission effects, nested/event masking, DEGRADE fail-closed behavior, and structured audit report export.

---

## 8. 五顾问评判

## 8.1 反对者

v0.1.8 仍不能称为生产可用。

主要理由：

1. API Reference 仍存在旧文档冲突；
2. structured audit report 不能默认带上 Result；
3. Policy Engine 尚未实现；
4. CredentialBroker 尚未实现；
5. deterministic rerun / resume 仍未实现；
6. MCP server mode 仍未实现；
7. Tool metadata 尚未与官方 policy 示例闭环；
8. 生产部署、OpenTelemetry、SIEM、供应链流程仍未完成。

结论：

> v0.1.8 是优秀的 Alpha 收口版本，但不是生产版本。

---

## 8.2 本质思考者

v0.1.8 的本质变化是：

> runtime control 不再只停留在“权限是否执行”，而开始扩展到“执行之后如何被审计、事件中如何不泄露数据”。

这非常关键。

企业 AI Agent 的生产问题不是单纯回答准确率，而是：

- 能不能控制动作；
- 能不能限制工具；
- 能不能防止敏感数据外泄；
- 能不能解释为什么执行或阻断；
- 能不能复盘每一步；
- 能不能让安全团队读懂审计结果。

v0.1.8 已经开始补这些能力。

---

## 8.3 机会挖掘者

v0.1.8 已经很适合作为企业 PoC 的技术底座雏形。

可以围绕以下 demo 展示：

> Enterprise Expense Approval Agent

展示点：

- amount threshold → REQUIRE_APPROVAL；
- sensitive PII → input/output/event mask；
- external egress → DEGRADE fallback；
- missing fallback → fail-closed；
- budget hard limit；
- replay；
- audit report Markdown / JSON。

这个 demo 会比继续展示 calculator 更能证明 petfishFramework 的差异化。

---

## 8.4 局外人

外部开发者现在会觉得 PyPI 页面已经比较专业。

但如果他点击 GitHub API Reference，会看到旧信息：

- v0.1.0；
- MCP stdio stub；
- BaseTool signature 不完整；
- 没有 event_mask_fields；
- 没有 audit report。

这会破坏信任。

所以 v0.1.9 最应该修的是文档一致性，而不是继续加功能。

---

## 8.5 执行者

v0.1.9 建议只做五件事：

1. 修 GitHub API Reference；
2. 修 `audit_report_from_session()` 默认不带 Result；
3. 补 Tool metadata policy 示例；
4. 做企业 PoC demo；
5. 加最小 CI / docs snippet test。

Trusted Publishing 按计划放到 v0.2.0，不作为 v0.1.9 阻断项。

---

## 9. v0.1.9 建议路线

## 9.1 P0：文档同步

必须修：

- `docs/api.md` 版本号；
- MCP stdio 状态；
- Decision fields；
- `event_mask_fields`；
- nested mask；
- `BaseTool` metadata；
- `AuditReport`；
- Current Limitations；
- Replay Mode status；
- Tests count；
- examples。

建议把文档生成纳入测试：

```text
README quickstart -> pytest
PyPI examples -> pytest
docs snippets -> pytest
```

---

## 9.2 P0：修 audit report result attachment

当前：

```python
report = audit_report_from_session(session)
report.result is None
```

建议：

```python
result = session.run()
report = audit_report_from_session(session)
report.result == result
```

或：

```python
report = audit_report_from_session(session, result=result)
```

验收标准：

- Markdown report 包含 Total Tokens；
- Markdown report 包含 Cost；
- Markdown report 包含 Steps；
- Markdown report 包含 Final Output；
- JSON report 包含 result；
- 如果没有 result，明确显示 Result unavailable。

---

## 9.3 P1：Tool metadata policy demo

示例目标：

> 证明 BaseTool metadata 不只是字段，而是可以驱动 runtime policy。

建议官方示例：

```python
class SafeByDefaultPolicy:
    def evaluate(self, subject, action, resource, context):
        tool = context.get("tool_metadata")

        if tool.side_effect:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason="side-effect tool requires approval",
            )

        if tool.external_egress:
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason="external egress degraded",
                fallback_tool="dry_run",
            )

        return Decision(effect=DecisionEffect.ALLOW)
```

---

## 9.4 P1：Enterprise PoC demo

建议 demo：

> Enterprise Expense Approval Agent

必须覆盖：

- RAG policy retrieval；
- invoice validation tool；
- amount check；
- DENY；
- REQUIRE_APPROVAL；
- PARTIAL_ALLOW；
- MASK；
- DEGRADE；
- Budget；
- AuditReport；
- structured output；
- optional MCP tool。

这个 demo 是 v0.2.0 前最重要的资产。

---

## 9.5 P1：AuditReport 增强

建议增加字段：

- budget summary；
- event count by type；
- permission count by effect；
- degraded calls；
- blocked calls；
- masked fields；
- original/fallback execution；
- model calls；
- tool metadata；
- policy reason；
- trace hash。

---

## 9.6 P2：CI / quality

v0.1.9 可先做最小 CI：

- install package；
- quickstart；
- permission effects；
- nested mask；
- event mask；
- degrade fail-closed；
- audit report；
- ruff；
- pytest。

Trusted Publishing 保持 v0.2.0。

---

## 10. v0.2.0 建议聚焦

由于 Trusted Publishing 已 deferred to v0.2.0，建议 v0.2.0 聚焦“企业 PoC + 供应链可信度”：

1. Enterprise Expense Approval Agent；
2. YAML Policy Engine MVP；
3. CredentialBroker MVP；
4. structured audit report 完整版；
5. CI/CD；
6. Trusted Publishing；
7. SBOM；
8. SECURITY.md；
9. release provenance；
10. production limitations document。

---

## 11. 最终结论

v0.1.8 是一个很好的 Alpha 收口版本。

它最重要的进展包括：

- PyPI 定位已经修正为 runtime framework；
- 218 tests；
- nested mask 可用；
- event mask 可用；
- input/output mask 继续稳定；
- DEGRADE with fallback 正确；
- DEGRADE without fallback fail-closed；
- Tool metadata 继续稳定；
- structured audit report 已有 Markdown / JSON MVP；
- Quickstart / Budget / Replay / Pass^k 继续稳定。

当前最重要的问题是：

> GitHub API Reference 仍与实际能力冲突，structured audit report 默认缺 Result。

因此，v0.1.9 最应该做的是文档与审计报告收口，而不是继续堆新功能。

推荐下一步主线：

```text
v0.1.9:
  文档同步 + AuditReport 修复 + Tool metadata policy demo + 企业 PoC demo 草案

v0.2.0:
  企业 PoC + YAML Policy MVP + CredentialBroker MVP + Trusted Publishing + 供应链可信度
```

只要按这个方向继续推进，petfishFramework 就可以从“Alpha-stage runtime control skeleton”进入“企业 PoC 可用框架”的阶段。

---

## 12. 参考链接

- PyPI v0.1.8: https://pypi.org/project/petfishframework/0.1.8/
- GitHub Repository: https://github.com/kylecui/petfishFramework
- API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
