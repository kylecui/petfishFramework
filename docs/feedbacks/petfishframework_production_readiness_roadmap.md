# petfishFramework 生产可用路线图与差距规划

> 版本背景：本文以 `petfishframework==0.1.5` 为当前基线。  
> 当前状态：Alpha；核心 runtime 可跑；Quickstart、Budget、Permission、Replay、Pass^k、MCP client 等关键能力已具备基础实现。  
> 目标：规划 petfishFramework 距离“生产可用级别”还需要完成的工作。

---

## 1. 结论先行

petfishFramework 目前已经具备一个 **Agent runtime framework** 的核心雏形，但距离生产可用仍有明显距离。

当前可以比较有底气地说：

> petfishFramework 是一个 Alpha 阶段的、面向可靠、可审计、预算可控、权限可控 AI Agent 的轻量级 Python runtime framework。

但还不能说：

> petfishFramework 已经是 production-ready 的企业级 Agent 安全框架。

生产可用的关键不是“是否能跑一个 Agent demo”，而是：

- 权限语义是否完整且不可绕过；
- 工具调用是否可治理；
- 事件审计是否可信；
- replay 是否能用于故障复现；
- 策略是否可配置、可测试、可版本化；
- 对多租户、密钥、数据、日志、异常、部署、CI/CD、供应链安全是否有系统设计；
- 是否有足够的 benchmark、回归测试和生产级文档；
- 是否能在真实企业 workflow 中承受失败、恶意输入、工具异常、成本爆炸和权限边界压力。

当前最重要的判断：

> 0.1.5 已经修复了 0.1.4 最严重的权限执行语义问题：`DENY`、`REQUIRE_APPROVAL`、`PARTIAL_ALLOW` 已经具备 pre-execution enforcement 基础。但 `DEGRADE` 仍未完成真实降级执行，`MASK` 仍主要是 post-execution result masking，策略引擎、审计报告、deterministic replay、credential broker、生产部署与安全加固还未闭环。

---

## 2. 什么叫“生产可用”

生产可用不是一个单点功能，而是一组工程和治理能力。

对 petfishFramework 这类 Agent runtime 来说，生产可用至少应包含以下 12 个维度。

| 维度 | 生产可用要求 |
|---|---|
| Runtime 正确性 | Agent / Session / Environment / Tool / Model / Retriever 的执行语义稳定、可测试、可扩展 |
| 权限控制 | 所有能力调用经过统一仲裁，策略不可绕过，DecisionEffect 语义完整 |
| 工具治理 | 工具注册、schema 校验、风险分级、幂等性、副作用标注、沙箱、限流、超时、回滚 |
| 密钥与凭据 | 凭据不暴露给模型，工具调用按最小权限获取临时凭据 |
| 预算与配额 | token、cost、step、tool-call、wall-clock、per-user、per-tenant 预算均可硬限制 |
| 审计与可观测性 | 所有关键事件结构化记录，支持 trace、metrics、logs、SIEM、OpenTelemetry |
| Replay 与恢复 | audit replay、deterministic rerun、checkpoint resume 分层清晰且可用 |
| 可靠性评测 | pass@k、扰动测试、工具调用准确率、权限违规率、预算违规率、回归测试 |
| RAG 与数据治理 | 检索来源、证据、引用、数据脱敏、数据保留、租户隔离、prompt injection 防护 |
| 部署与运维 | 配置、日志、健康检查、版本升级、灰度、回滚、容器化、部署指南 |
| 供应链安全 | CI/CD、SBOM、依赖扫描、签名发布、Trusted Publishing、漏洞响应 |
| 文档与生态 | API 稳定性、迁移指南、示例、限制说明、benchmark、企业 demo、贡献规范 |

如果以这个标准看，petfishFramework 当前大概处于：

> Alpha runtime 可用，企业 PoC 需要补强，生产可用仍需系统化建设。

---

## 3. 当前 v0.1.5 状态评估

## 3.1 已经具备的能力

| 能力 | 当前状态 | 评价 |
|---|---|---|
| Zero-cost quickstart | 已有 | 新用户能直接跑通 |
| Real LLM quickstart | 已有 | 支持 OpenAI adapter 和 shorthand |
| Agent / Session 抽象 | 已有 | 主线正确 |
| Environment chokepoint | 已有 | 核心架构资产 |
| ReAct | 可用 | 默认 reasoning strategy |
| LATS / LLM+P | 轻量可用 | 不宜宣传为完整 SOTA 实现 |
| Budget hard limits | 可用 | token / cost / step / tool-call 基础可用 |
| Permission SARC model | 已有 | 方向正确 |
| DENY | 已 enforce | 工具执行前阻断 |
| REQUIRE_APPROVAL | 已 enforce | 工具执行前阻断 |
| PARTIAL_ALLOW | 已 enforce | 执行前参数过滤 |
| MASK | 已 enforce | 主要是执行后结果脱敏 |
| DEGRADE | 已建模 | 工具切换未实现 |
| Replay | Audit replay 可用 | deterministic rerun / resume 未闭环 |
| Pass^k | 可用 | 可靠性评测方向正确 |
| MCP client stdio | 可用 | 可接外部 MCP server |
| MCP server mode | planned | 未完成 |
| Structured output | 可用 | JSON → dataclass |
| Conversation memory | 可用 | 基础跨 session memory |
| ToolRegistry | 可用 | 需要更强治理能力 |
| 测试数量 | 自述 187 tests | 需要 CI 可见性和覆盖率报告 |

---

## 3.2 当前主要缺口

最重要的缺口不是“功能数量不足”，而是生产语义与治理闭环不足。

优先级最高的缺口包括：

1. `DEGRADE` 还没有真正降级执行；
2. `MASK` 需要区分输入脱敏与输出脱敏；
3. 缺少策略引擎：目前主要是 Python policy；
4. 缺少策略版本、策略测试、策略审计；
5. 缺少 CredentialBroker；
6. 缺少结构化审计报告；
7. Replay 仍主要是 audit event log；
8. deterministic rerun 与 checkpoint resume 未闭环；
9. 工具风险治理还不够：副作用、幂等性、回滚、沙箱、超时、限流需要系统化；
10. MCP client 可用，但 MCP server mode、server lifecycle、错误恢复、认证授权还不完整；
11. 缺少 OpenTelemetry / SIEM / log integration；
12. 缺少企业级 benchmark；
13. 缺少 CI/CD、coverage、SBOM、签名发布、Trusted Publishing；
14. 文档仍存在 PyPI 与 GitHub API reference 不一致的风险；
15. 还没有真实企业 workflow demo；
16. 缺少部署、运维、升级、回滚和安全加固指南。

---

## 4. 生产可用目标分层

建议不要把“生产可用”作为一个模糊目标，而是分成四个阶段。

## 4.1 Stage A：可信 Alpha

目标：

> 核心语义可信，开发者可以用来做实验和小型 PoC。

准入条件：

- Quickstart 稳定；
- 核心 API 测试覆盖；
- DENY / REQUIRE_APPROVAL / PARTIAL_ALLOW / MASK 语义明确；
- DEGRADE 状态明确；
- Audit replay 可用；
- Budget 可硬中断；
- 文档不夸大能力；
- 所有限制明确写出。

当前 v0.1.5 基本处于 Stage A，但仍需修文档同步和 DEGRADE 状态说明。

---

## 4.2 Stage B：企业 PoC 可用

目标：

> 可以在受控环境中支撑真实企业 PoC，但不承诺大规模生产稳定性。

准入条件：

- 完整企业 demo；
- 结构化审计报告；
- 策略引擎 MVP；
- CredentialBroker MVP；
- 工具风险分级；
- 工具调用超时 / retry / circuit breaker；
- per-session / per-user budget；
- 可导出 JSON trace；
- pass@k + permission benchmark；
- CI/CD 可见；
- 安全限制清楚。

建议版本目标：`v0.2.x`。

---

## 4.3 Stage C：生产候选版

目标：

> 可以给早期客户试点上线，具备基本运维、安全、审计和回滚能力。

准入条件：

- deterministic replay；
- checkpoint resume；
- policy versioning；
- policy test harness；
- tenant isolation；
- durable storage adapter；
- OpenTelemetry；
- SIEM export；
- dependency vulnerability scan；
- SBOM；
- signed release；
- deployment guide；
- upgrade / migration guide；
- failure mode guide；
- benchmark 报告；
- 真实端到端案例。

建议版本目标：`v0.4.x` 到 `v0.6.x`。

---

## 4.4 Stage D：生产可用 / v1.0

目标：

> API 稳定、语义稳定、文档完整、测试充分、可运维、可审计、可被企业安全团队接受。

准入条件：

- v1 API freeze；
- backward compatibility policy；
- semantic versioning；
- security policy；
- vulnerability disclosure process；
- production hardening checklist；
- threat model；
- compliance mapping；
- reference deployment；
- load / chaos / adversarial testing；
- production incident playbook；
- multi-tenant isolation；
- credential isolation；
- policy and audit integrity；
- external review 或真实客户 PoC 反馈。

建议版本目标：`v1.0`。

---

# 5. 核心技术路线

---

## 5.1 Runtime Kernel 稳定化

## 当前问题

petfishFramework 当前已经有 Agent、Session、Environment 的主线，但生产级 runtime 需要更严格的执行模型。

目前需要继续稳定：

- Session lifecycle；
- event ordering；
- tool call lifecycle；
- model call lifecycle；
- error propagation；
- budget accounting；
- cancellation；
- timeout；
- async / sync 一致性；
- streaming 与 event log 的一致性；
- nested agent / AgentAsTool 的事件归属。

---

## 目标设计

建议定义标准 run lifecycle：

```text
session.created
session.started
model.requested
model.completed
tool.requested
permission.evaluated
tool.blocked | tool.called | tool.failed | tool.completed
budget.checked
result.generated
session.completed | session.failed | session.cancelled
```

每个事件都应包含：

```yaml
event_id: uuid
session_id: uuid
parent_event_id: uuid | null
timestamp: iso8601
type: string
actor: agent | model | tool | retriever | policy
subject: optional
action: optional
resource: optional
decision: optional
executed: true | false | null
duration_ms: number
error: optional
metadata: object
```

---

## 生产准入标准

- event order deterministic；
- nested tool / AgentAsTool trace 可追踪；
- async 与 sync 路径事件一致；
- streaming partial output 可记录；
- error event 与 exception 一一对应；
- session failure 后可生成完整 failure report；
- 所有 runtime path 有测试覆盖。

---

## 5.2 Permission / Policy 体系

## 当前状态

已有 SARC 模型和 6 种 DecisionEffect：

- ALLOW；
- DENY；
- MASK；
- PARTIAL_ALLOW；
- REQUIRE_APPROVAL；
- DEGRADE。

v0.1.5 中：

- DENY：pre-execution block；
- REQUIRE_APPROVAL：pre-execution block；
- PARTIAL_ALLOW：pre-execution arg filtering；
- MASK：post-execution result masking；
- DEGRADE：modeled，未实现真实 tool switching。

---

## 必须补齐的能力

## 5.2.1 完整 DEGRADE

`DEGRADE` 不能只是记录事件，而应真正改变执行路径。

典型场景：

```text
send_email        -> draft_email
delete_file       -> preview_delete
approve_payment   -> request_approval
write_database    -> dry_run_sql
external_api_post -> readonly_lookup
```

建议 Decision 支持：

```python
Decision(
    effect=DecisionEffect.DEGRADE,
    reason="write action requires safe fallback",
    fallback_tool="draft_email",
    fallback_args={"recipient": "...", "body": "..."},
)
```

执行语义：

```text
policy returns DEGRADE
  -> do not execute original tool
  -> resolve fallback tool
  -> validate fallback args
  -> execute fallback tool
  -> emit tool.degraded with original_tool + fallback_tool
```

事件应明确：

```yaml
type: tool.degraded
original_tool: send_email
fallback_tool: draft_email
original_executed: false
fallback_executed: true
decision_reason: write action requires approval
```

---

## 5.2.2 输入脱敏与输出脱敏分离

当前 `MASK` 更像输出脱敏。生产场景中必须区分：

| 类型 | 发生时机 | 示例 |
|---|---|---|
| input mask | 工具执行前 | 发给外部 API 前移除身份证号 |
| output mask | 工具执行后 | 返回用户记录后隐藏手机号 |
| context mask | 发给模型前 | RAG 片段中脱敏客户信息 |
| event mask | 写审计日志前 | trace 中不记录 access token |

建议 Decision 增加：

```python
Decision(
    effect=DecisionEffect.MASK,
    input_mask_fields=["ssn", "credit_card"],
    output_mask_fields=["phone"],
    event_mask_fields=["api_key"],
)
```

---

## 5.2.3 Policy Engine MVP

仅靠 Python policy 不够。生产级需要配置化策略。

建议阶段：

### Phase 1：Python Policy 稳定

适合开发者扩展。

```python
class FinancePolicy(PermissionPolicy):
    def evaluate(self, subject, action, resource, context):
        ...
```

### Phase 2：YAML Policy

适合企业安全团队维护。

```yaml
rules:
  - name: high-value-payment-approval
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
- first-match；
- priority；
- tenant-level policy；
- user-level policy；
- tool-level policy；
- environment-level policy；
- policy inheritance；
- policy versioning。

### Phase 4：Policy Test Harness

策略必须可测试。

```yaml
tests:
  - name: analyst-cannot-delete-file
    input:
      subject.role: analyst
      action: delete_file
      resource.type: file
    expect:
      effect: DENY
```

---

## 5.2.4 Policy Audit

每个权限决策必须能解释：

- 哪条规则命中；
- 为什么命中；
- 是否执行；
- 是否降级；
- 是否被审批；
- 审批人是谁；
- 策略版本是什么。

建议事件字段：

```yaml
policy_id: finance-policy
policy_version: 2026-07-07.1
rule_id: high-value-payment-approval
effect: REQUIRE_APPROVAL
reason: amount exceeds 1000
executed: false
```

---

## 5.3 Tool Governance

## 当前问题

当前 Tool 已有基本 contract，但生产级工具治理需要更细。

Agent 工具不是普通函数。它可能：

- 读数据；
- 写数据；
- 删除数据；
- 发邮件；
- 调支付；
- 调公网 API；
- 触发工作流；
- 改变业务系统状态。

因此，工具治理必须成为 framework 的一级能力。

---

## 5.3.1 工具元数据

每个 Tool 建议强制声明：

```yaml
name: send_email
description: Send an email
risk_level: HIGH
capabilities:
  - network.egress
  - email.send
side_effect: true
idempotent: false
requires_approval: true
reads:
  - user.email
writes:
  - mailbox.outbound
external_domains:
  - smtp.example.com
timeout_ms: 5000
max_retries: 0
```

建议 Tool metadata 包括：

| 字段 | 用途 |
|---|---|
| risk_level | 风险分级 |
| capabilities | 权限匹配 |
| side_effect | 是否有副作用 |
| idempotent | 是否幂等 |
| reversible | 是否可回滚 |
| data_access | 读取哪些数据 |
| data_write | 写入哪些系统 |
| external_egress | 是否外发 |
| required_credentials | 需要哪些凭据 |
| timeout | 最大执行时间 |
| retry_policy | 重试策略 |
| rate_limit | 限流 |
| sandbox_required | 是否需要沙箱 |
| audit_level | 审计级别 |

---

## 5.3.2 工具执行生命周期

建议标准化：

```text
tool.requested
tool.schema_validated
permission.evaluated
credential.requested
credential.issued
tool.executing
tool.completed | tool.failed | tool.timeout | tool.blocked
tool.result_validated
tool.result_masked
tool.audit_recorded
```

---

## 5.3.3 工具 schema 验证

生产级必须严格验证输入参数。

要求：

- JSON Schema validation；
- required fields；
- type check；
- enum check；
- max length；
- regex；
- disallow unknown fields；
- default value handling；
- partial allow 后再次 validate；
- fallback tool args validate。

---

## 5.3.4 副作用与幂等性

必须区分：

| 类型 | 示例 | 治理方式 |
|---|---|---|
| pure function | calculator | 可自由重试 |
| read-only | lookup_user | 可重试但需权限 |
| write operation | update_ticket | 需幂等键 |
| irreversible action | delete_file | 需审批 / dry-run |
| external side effect | send_email | 需审批 / 审计 |
| financial action | transfer_money | 高风险策略 |

建议 ToolResult 增加：

```python
ToolResult(
    value=...,
    side_effect_performed=True,
    idempotency_key="...",
    rollback_hint="...",
)
```

---

## 5.3.5 工具沙箱

对高风险工具建议支持 sandbox execution。

包括：

- 文件系统沙箱；
- 网络 egress allowlist；
- subprocess 限制；
- CPU / memory 限制；
- timeout；
- read-only mount；
- temporary workspace；
- output size limit。

---

## 5.3.6 MCP 工具治理

MCP 是关键能力，但生产环境中外部 MCP server 是风险源。

需要补齐：

- MCP server allowlist；
- tool discovery 审批；
- tool schema pinning；
- tool version pinning；
- server identity；
- transport security；
- timeout；
- reconnect；
- health check；
- capability filtering；
- risk metadata mapping；
- external tool audit；
- prompt injection 防护；
- data egress control。

建议不要默认把所有 discovered MCP tools 暴露给 Agent，而是：

```text
discover tools
  -> classify risk
  -> apply capability projection
  -> expose allowed subset to agent
```

---

## 5.4 CredentialBroker

## 当前问题

生产级 Agent 最大风险之一是凭据泄露。

模型不应该看到：

- API key；
- OAuth token；
- database password；
- cloud credential；
- user session cookie；
- signing key。

工具也不应该长期持有高权限密钥。

---

## 目标设计

引入 CredentialBroker：

```text
Agent requests tool call
  -> Environment evaluates policy
  -> CredentialBroker issues scoped temporary credential
  -> Tool executes with credential
  -> Credential revoked / expires
  -> Audit records credential reference, not secret
```

---

## CredentialBroker 应支持

- short-lived credentials；
- per-tool credentials；
- per-session credentials；
- per-user delegation；
- scoped token；
- no secret in prompt；
- no secret in event log；
- rotation；
- revocation；
- vault integration；
- cloud IAM integration；
- audit reference。

---

## 事件示例

```yaml
type: credential.issued
credential_ref: cred_abc123
scope:
  - github.issue.read
ttl_seconds: 300
secret_logged: false
```

---

## 生产准入标准

- 模型永远看不到 secret；
- event log 永远不记录 secret；
- tool 只能拿到最小权限凭据；
- 凭据过期后不可复用；
- 高风险凭据使用必须审计；
- 支持 Vault / AWS Secrets Manager / GCP Secret Manager / Azure Key Vault 适配。

---

## 5.5 Audit / Observability

## 当前状态

`session.replay()` 可以返回 event log，这是好基础。

但生产级需要结构化审计报告和观测系统集成。

---

## 5.5.1 Structured Trace

每次 session 应可导出：

- JSON trace；
- Markdown report；
- HTML report；
- OpenTelemetry trace；
- SIEM event。

---

## 5.5.2 审计报告内容

建议生成：

```markdown
# Agent Session Audit Report

## Summary

- Session ID
- Agent Name
- User / Subject
- Model
- Start Time
- End Time
- Status
- Total Tokens
- Total Cost
- Tool Calls
- Permission Decisions
- Budget Violations
- Errors

## Timeline

| Time | Event | Decision | Executed | Detail |
|---|---|---|---|---|

## Tool Calls

| Step | Tool | Risk | Args Hash | Decision | Executed | Duration | Result |
|---|---|---|---|---|---|---|---|

## Permission Decisions

| Step | Subject | Action | Resource | Effect | Rule | Reason | Executed |
|---|---|---|---|---|---|---|---|

## Budget

| Metric | Used | Limit | Status |
|---|---:|---:|---|

## Final Output

...
```

---

## 5.5.3 日志脱敏

审计日志不能成为新的泄露源。

必须支持：

- secret masking；
- PII masking；
- field-level log policy；
- event-level redaction；
- raw args hash；
- raw result hash；
- secure debug mode；
- retention policy。

---

## 5.5.4 OpenTelemetry / SIEM

生产级建议支持：

- OpenTelemetry traces；
- Prometheus metrics；
- JSON logs；
- syslog；
- webhook export；
- Splunk / Elastic / Datadog / Sentinel integration；
- custom event sink。

---

## 5.5.5 关键指标

建议暴露 metrics：

| 指标 | 含义 |
|---|---|
| session_total | 总 session 数 |
| session_success_rate | 成功率 |
| session_failure_rate | 失败率 |
| tool_call_total | 工具调用次数 |
| tool_denied_total | 被拒绝工具调用 |
| approval_required_total | 需要审批次数 |
| budget_exceeded_total | 预算超限次数 |
| permission_violation_total | 权限违规尝试 |
| token_used_total | token 使用量 |
| cost_usd_total | 成本 |
| model_latency_ms | 模型延迟 |
| tool_latency_ms | 工具延迟 |
| replay_available_total | 可 replay session 数 |

---

## 5.6 Replay / Deterministic Rerun / Resume

## 当前状态

当前 audit replay 可用，但 deterministic rerun 和 resume 仍未闭环。

---

## 建议分层

## Level 1：Audit Replay

目标：

> 看清楚发生了什么。

当前已有基础。

需要完善：

- 事件完整性；
- 事件排序；
- JSON export；
- Markdown report；
- 错误归因；
- 权限决策归因。

---

## Level 2：Deterministic Rerun

目标：

> 固定模型响应、工具响应、检索结果，复现一次 run。

需要记录：

- model request；
- model response；
- tool args；
- tool result；
- retriever query；
- retriever snippets；
- policy decision；
- budget state；
- random seed；
- framework version；
- policy version；
- tool version。

执行方式：

```text
record mode:
  live model/tool/retriever
  record all responses

rerun mode:
  no live external call
  replay recorded responses
  compare final output and trace
```

用途：

- 回归测试；
- bug 复现；
- 版本升级验证；
- policy change impact analysis。

---

## Level 3：Resume

目标：

> 长任务失败后从 checkpoint 继续。

需要：

- checkpoint format；
- serializable session state；
- durable storage；
- idempotency；
- duplicate tool call prevention；
- pending approval state；
- timeout recovery；
- async task recovery。

---

## 5.7 Budget / Quota / Cost Governance

## 当前状态

已经支持 token、cost、step、tool-call 的 hard limit。

---

## 生产级扩展

需要从 session-level 扩展到组织级治理：

| 层级 | 示例 |
|---|---|
| per-run | 单次任务最多 5000 tokens |
| per-agent | 某 Agent 每天最多 $10 |
| per-user | 用户每天最多 100 次 tool call |
| per-tenant | 租户每月最多 $1000 |
| per-tool | 高风险工具每天最多 20 次 |
| per-model | 昂贵模型每小时最多 50 次 |
| per-workflow | 审批流程最多 10 步 |
| burst limit | 1 分钟内最多 5 次 |
| soft limit | 超过 80% 发 warning |
| hard limit | 超过 100% 中断 |

---

## 预算事件

```yaml
type: budget.warning
metric: cost_usd
used: 8.0
limit: 10.0
threshold: 0.8
```

```yaml
type: budget.exceeded
metric: tool_calls
used: 11
limit: 10
action: session_terminated
```

---

## 5.8 Reliability Evaluation / Benchmark

## 当前状态

Pass^k 是正确方向，但生产级需要覆盖更多维度。

---

## 5.8.1 Benchmark 分层

建议建立四类 benchmark。

### A. Tool-use Reliability

目标：Agent 是否正确使用工具。

指标：

- correct tool rate；
- wrong tool rate；
- missing tool rate；
- unnecessary tool rate；
- argument accuracy；
- schema violation rate；
- tool-call sequence accuracy。

---

### B. Permission Enforcement

目标：策略是否真的限制动作。

测试：

- DENY；
- REQUIRE_APPROVAL；
- PARTIAL_ALLOW；
- MASK；
- DEGRADE；
- multi-policy composition；
- nested AgentAsTool；
- MCP tools；
- malicious tool request；
- prompt injection forcing tool call。

指标：

- permission violation rate；
- blocked execution correctness；
- approval-required correctness；
- partial-allow correctness；
- mask correctness；
- degrade correctness；
- audit correctness。

---

### C. Budget Robustness

目标：是否能阻止成本与循环失控。

测试：

- infinite reasoning loop；
- tool retry storm；
- retrieval storm；
- long context；
- streaming overrun；
- nested agent runaway。

指标：

- budget enforcement latency；
- cost overrun percentage；
- step overrun rate；
- tool-call overrun rate；
- termination correctness。

---

### D. Replay / Audit Completeness

目标：失败后是否能复盘。

指标：

- event coverage；
- model call coverage；
- tool call coverage；
- permission decision coverage；
- budget checkpoint coverage；
- error coverage；
- deterministic rerun success rate；
- trace diff quality。

---

## 5.8.2 Pass^k 扩展

当前 Pass^k 可以继续扩展：

- pass@k；
- consistency@k；
- tool_path_consistency@k；
- cost_variance@k；
- latency_variance@k；
- permission_stability@k；
- perturbation robustness；
- adversarial perturbation robustness。

---

## 5.8.3 CI 中的可靠性测试

建议把轻量 benchmark 加入 CI：

```text
unit tests
  -> runtime tests
  -> permission tests
  -> replay tests
  -> smoke benchmark
  -> package build
```

每个 PR 至少跑：

- quickstart；
- budget；
- DENY；
- REQUIRE_APPROVAL；
- PARTIAL_ALLOW；
- MASK；
- DEGRADE modeled；
- replay event correctness；
- FakeModel Pass^k；
- MCP mock server；
- structured output。

---

## 5.9 RAG / Data Governance

## 当前状态

MemoryRetriever、CRAG-inspired、Adaptive-RAG-inspired 能力已有基础，但仍是 lightweight reference。

---

## 生产级需要

## 5.9.1 Evidence Governance

RAG 结果应具备：

- source id；
- document id；
- snippet id；
- timestamp；
- version；
- retrieval score；
- tenant id；
- access decision；
- sensitivity label；
- citation metadata。

---

## 5.9.2 RAG 权限控制

检索不能绕过权限。

流程应是：

```text
retrieve candidates
  -> filter by subject/resource policy
  -> mask sensitive fields
  -> pass allowed snippets to model
  -> record evidence in trace
```

注意：

> 不能先把所有检索结果发给模型，再让模型“不要使用无权限内容”。

---

## 5.9.3 Prompt Injection 防护

RAG 文档可能包含恶意指令。

需要支持：

- document instruction stripping；
- source trust level；
- instruction/data separation；
- retrieval context labeling；
- tool-call isolation；
- quote-only evidence mode；
- model prompt hardening；
- suspicious snippet events。

---

## 5.9.4 数据保留与租户隔离

需要支持：

- per-tenant vector store；
- memory isolation；
- conversation retention policy；
- deletion request；
- PII handling；
- data residency；
- audit log retention；
- encryption at rest；
- encryption in transit。

---

## 5.10 Model Provider Governance

## 当前状态

支持 OpenAI、Anthropic、FakeModel。

生产级需要更完整的 model runtime 管理。

---

## 需要补齐

- provider abstraction stability；
- OpenAI-compatible endpoint 配置；
- timeout；
- retry；
- circuit breaker；
- fallback model；
- model allowlist；
- model risk level；
- cost model；
- token estimation；
- rate limit；
- response validation；
- tool-call format normalization；
- streaming error handling；
- provider outage handling。

---

## 模型 fallback 策略

示例：

```yaml
models:
  primary:
    provider: openai
    name: gpt-4o-mini
  fallback:
    provider: anthropic
    name: claude-...
  emergency:
    provider: fake
    name: deterministic
```

策略：

```text
primary timeout
  -> retry once
  -> fallback model
  -> if structured output invalid, repair once
  -> if still invalid, fail closed
```

---

## 5.11 Multi-Agent / AgentAsTool

## 当前状态

AgentAsTool 已有基础。

生产级多 Agent 需要解决：

- 子 Agent 权限继承；
- 子 Agent 预算继承；
- 子 Agent 事件归属；
- delegation depth limit；
- cyclic delegation 防护；
- supervisor / specialist boundary；
- sensitive context propagation；
- result contract；
- failure bubbling；
- policy override rules。

---

## 建议

AgentAsTool 必须有：

```yaml
parent_session_id
child_session_id
delegation_reason
delegation_depth
inherited_budget
inherited_policy
allowed_context_fields
```

并设置：

- max delegation depth；
- max child sessions；
- child budget fraction；
- no secret propagation；
- child trace linkage。

---

## 5.12 Deployment / Operations

## 当前缺口

生产可用必须有部署和运维指南。

---

## 建议补齐

### 配置系统

支持：

- env；
- YAML；
- dict；
- secret reference；
- profile；
- tenant config；
- policy config；
- model config；
- tool config。

### 健康检查

```text
/healthz
/readyz
/metrics
```

### 容器化

提供：

- Dockerfile；
- docker-compose；
- Kubernetes example；
- Helm chart optional；
- resource limits；
- non-root user；
- read-only filesystem；
- tmp workspace。

### 运维文档

包括：

- installation；
- upgrade；
- rollback；
- migration；
- logging；
- monitoring；
- backup；
- retention；
- troubleshooting；
- performance tuning；
- incident response。

---

## 5.13 Security Hardening

## 5.13.1 Threat Model

必须写 threat model。

至少覆盖：

- malicious user prompt；
- prompt injection；
- tool injection；
- RAG injection；
- MCP server compromise；
- credential leakage；
- cross-tenant data leakage；
- unauthorized tool use；
- budget exhaustion；
- replay log leakage；
- supply chain attack；
- dependency compromise；
- model provider outage；
- model output manipulation；
- audit tampering。

---

## 5.13.2 Secure Defaults

生产级必须 fail closed。

建议默认：

- high-risk tools hidden；
- DENY unknown tool；
- DENY unknown capability；
- no external egress unless allowed；
- no write action unless policy allows；
- no secrets in prompt；
- no raw args in logs unless safe；
- budget required for production mode；
- timeout required for all tools；
- structured output validation required where configured。

---

## 5.13.3 Supply Chain Security

需要：

- GitHub Actions；
- dependency scan；
- static analysis；
- ruff / mypy；
- unit / integration tests；
- coverage report；
- SBOM；
- signed artifacts；
- PyPI Trusted Publishing；
- release provenance；
- vulnerability disclosure policy；
- SECURITY.md；
- dependency pinning strategy；
- changelog；
- release notes；
- CVE response process。

当前 PyPI 文件元数据中显示 0.1.5 uploaded using twine，Trusted Publishing 为 No。生产级建议改用 Trusted Publishing 和签名/来源证明。

---

## 5.14 Documentation / Developer Experience

## 当前状态

文档已经比 0.1.2/0.1.4 明显好，但仍需保证一致性。

---

## 必须修复

- PyPI 与 GitHub README 同步；
- API Reference 同步；
- MCP 状态一致；
- Replay 状态一致；
- DecisionEffect enforcement 状态一致；
- Roadmap 版本号一致；
- 示例全部加入测试；
- 文档中所有代码片段可自动执行；
- 当前限制写清楚；
- 不夸大生产能力。

---

## 推荐文档结构

```markdown
# petfishFramework

## Why petfishFramework?

## Production Status

## Core Concepts

## Quickstart

## Real LLM

## Tools

## Budget

## Permission

## Audit / Replay

## MCP

## RAG

## Structured Output

## Multi-Agent

## Reliability Evaluation

## Enterprise Demo

## Deployment

## Security Model

## API Reference

## Roadmap

## Current Limitations
```

---

# 6. 分版本路线图

---

## v0.1.6：语义补全版

目标：

> 把当前 permission-aware runtime 的语义补齐。

任务：

- [ ] 实现真实 `DEGRADE` tool switching；
- [ ] 区分 input mask / output mask / event mask；
- [ ] 增加 tool side-effect metadata；
- [ ] 增加 `executed`、`original_executed`、`fallback_executed` 事件字段；
- [ ] 增加副作用工具测试；
- [ ] 同步 PyPI / README / API Reference；
- [ ] 增加 CI badge；
- [ ] 增加 coverage badge。

验收标准：

- `REQUIRE_APPROVAL` 不执行工具；
- `PARTIAL_ALLOW` 只用过滤后参数执行；
- `DEGRADE` 不执行原始工具，执行 fallback；
- `MASK` 明确 pre/post；
- 所有权限事件真实反映执行状态。

---

## v0.2.0：企业 PoC Demo 版

目标：

> 做出一个端到端企业场景，让用户看到框架价值。

任务：

- [ ] 企业报销审批 Agent；
- [ ] policy examples；
- [ ] structured audit report；
- [ ] JSON trace export；
- [ ] Markdown trace export；
- [ ] CredentialBroker MVP；
- [ ] Tool risk metadata；
- [ ] Policy test harness MVP；
- [ ] MCP tool governance example；
- [ ] deployment mini guide。

验收标准：

- demo 可以完整运行；
- 展示 DENY / REQUIRE_APPROVAL / PARTIAL_ALLOW / MASK / DEGRADE；
- 展示审计报告；
- 展示 budget hard stop；
- 展示 RAG evidence；
- 展示 MCP tool 受控暴露；
- 展示 structured output。

---

## v0.3.0：Policy Engine 版

目标：

> 从代码策略进入配置化策略。

任务：

- [ ] YAML policy；
- [ ] rule matching；
- [ ] deny-overrides；
- [ ] priority；
- [ ] policy version；
- [ ] policy tests；
- [ ] policy audit；
- [ ] tenant policy；
- [ ] tool policy；
- [ ] resource policy；
- [ ] policy migration guide。

验收标准：

- 安全团队不写 Python 也能配置策略；
- 每个 policy change 可测试；
- 每次 decision 可解释；
- 策略版本进入 trace。

---

## v0.4.0：Observability / Replay 版

目标：

> 让框架可审计、可复盘、可接入企业日志系统。

任务：

- [ ] OpenTelemetry traces；
- [ ] Prometheus metrics；
- [ ] JSON logs；
- [ ] SIEM export；
- [ ] deterministic rerun；
- [ ] trace diff；
- [ ] failure report；
- [ ] replay storage adapter；
- [ ] event redaction；
- [ ] retention policy。

验收标准：

- 任意失败 session 可导出报告；
- 任意 session 可进入 OTel trace；
- deterministic rerun 可复现固定 run；
- trace 中无 secret；
- metrics 可接入 dashboard。

---

## v0.5.0：Tool / MCP Governance 版

目标：

> 把工具和 MCP 作为企业能力资产治理。

任务：

- [ ] tool metadata required；
- [ ] tool schema strict validation；
- [ ] tool risk classification；
- [ ] tool rate limit；
- [ ] tool timeout；
- [ ] tool retry policy；
- [ ] idempotency key；
- [ ] sandbox execution；
- [ ] MCP server allowlist；
- [ ] MCP tool schema pinning；
- [ ] MCP tool risk mapping；
- [ ] MCP server health check；
- [ ] MCP server lifecycle management。

验收标准：

- 高风险工具默认不可见；
- MCP 工具不自动全量暴露；
- 所有工具有 risk metadata；
- 工具执行超时可控；
- 工具调用可限流；
- 副作用工具可审计。

---

## v0.6.0：Production Candidate

目标：

> 可用于早期生产试点。

任务：

- [ ] deployment guide；
- [ ] Dockerfile；
- [ ] Kubernetes example；
- [ ] security hardening checklist；
- [ ] threat model；
- [ ] SBOM；
- [ ] signed release；
- [ ] PyPI Trusted Publishing；
- [ ] vulnerability disclosure process；
- [ ] CI/CD pipeline；
- [ ] load test；
- [ ] chaos test；
- [ ] adversarial test；
- [ ] upgrade / rollback guide。

验收标准：

- 有完整 release pipeline；
- 有安全披露流程；
- 有部署文档；
- 有生产限制说明；
- 有 benchmark 报告；
- 有 reference architecture。

---

## v1.0.0：Production Ready

目标：

> API 稳定、语义稳定、可审计、可运维、可被企业安全团队接受。

准入条件：

- [ ] API freeze；
- [ ] semantic versioning；
- [ ] backward compatibility policy；
- [ ] migration guide；
- [ ] production deployment guide；
- [ ] enterprise demo；
- [ ] policy engine stable；
- [ ] credential broker stable；
- [ ] tool governance stable；
- [ ] deterministic replay stable；
- [ ] audit report stable；
- [ ] OpenTelemetry stable；
- [ ] security hardening complete；
- [ ] test coverage threshold；
- [ ] benchmark baseline；
- [ ] external feedback / real PoC validation。

---

# 7. 生产可用验收清单

以下清单可以作为 v1.0 前的 gate。

---

## 7.1 Runtime Gate

- [ ] Session lifecycle 稳定；
- [ ] Event ordering 稳定；
- [ ] Sync / async 行为一致；
- [ ] Streaming 与 event log 一致；
- [ ] Nested Agent trace 可追踪；
- [ ] 所有 exception 有结构化 event；
- [ ] Budget 超限可中断；
- [ ] Timeout 可中断；
- [ ] Cancellation 可中断。

---

## 7.2 Permission Gate

- [ ] DENY 不执行；
- [ ] REQUIRE_APPROVAL 不执行；
- [ ] PARTIAL_ALLOW 先裁剪；
- [ ] DEGRADE 执行 fallback；
- [ ] MASK 区分 input/output/event；
- [ ] Capability projection 生效；
- [ ] Tool visibility gate 生效；
- [ ] Invocation gate 生效；
- [ ] Policy version 进入 trace；
- [ ] Rule reason 可解释；
- [ ] 策略有测试。

---

## 7.3 Tool Gate

- [ ] Tool schema strict validation；
- [ ] Unknown args 拒绝；
- [ ] Risk metadata 必填；
- [ ] Side effect metadata 必填；
- [ ] High-risk tool 默认隐藏；
- [ ] Write tool 需要策略允许；
- [ ] External egress 需要策略允许；
- [ ] Tool timeout；
- [ ] Tool rate limit；
- [ ] Tool retry policy；
- [ ] Idempotency key；
- [ ] Sandbox option。

---

## 7.4 Credential Gate

- [ ] 模型不可见 secret；
- [ ] event log 不记录 secret；
- [ ] tool 获得 scoped credential；
- [ ] credential 有 TTL；
- [ ] credential 可撤销；
- [ ] Vault / Secret Manager integration；
- [ ] credential use audited。

---

## 7.5 Audit Gate

- [ ] JSON trace；
- [ ] Markdown audit report；
- [ ] OTel trace；
- [ ] SIEM export；
- [ ] event redaction；
- [ ] retention policy；
- [ ] trace integrity；
- [ ] executed 字段可信；
- [ ] failure report；
- [ ] trace diff。

---

## 7.6 Reliability Gate

- [ ] pass@k；
- [ ] perturbation suite；
- [ ] tool-use benchmark；
- [ ] permission benchmark；
- [ ] budget benchmark；
- [ ] replay benchmark；
- [ ] adversarial prompt test；
- [ ] RAG injection test；
- [ ] MCP malicious tool test；
- [ ] regression suite in CI。

---

## 7.7 Deployment Gate

- [ ] Dockerfile；
- [ ] Kubernetes example；
- [ ] config guide；
- [ ] secret guide；
- [ ] logging guide；
- [ ] monitoring guide；
- [ ] upgrade guide；
- [ ] rollback guide；
- [ ] backup / retention guide；
- [ ] incident response guide。

---

## 7.8 Supply Chain Gate

- [ ] GitHub Actions；
- [ ] dependency scan；
- [ ] static analysis；
- [ ] type checking；
- [ ] coverage report；
- [ ] SBOM；
- [ ] signed release；
- [ ] Trusted Publishing；
- [ ] SECURITY.md；
- [ ] vulnerability disclosure；
- [ ] release provenance。

---

# 8. 推荐的企业端到端 Demo

## 8.1 Demo 名称

> Enterprise Expense Approval Agent

中文：

> 企业报销审批 Agent

---

## 8.2 为什么选这个场景

这个场景天然覆盖：

- 用户身份；
- 角色权限；
- 金额阈值；
- 发票校验；
- 政策检索；
- 敏感字段；
- 审批流；
- 外部系统；
- 审计；
- 成本预算；
- 工具副作用。

---

## 8.3 Demo 流程

```text
User submits reimbursement request
  -> Agent parses request
  -> Retriever loads expense policy
  -> Invoice tool validates receipt
  -> Amount tool checks threshold
  -> Permission policy evaluates subject/action/resource/context
  -> If low amount: allow submit
  -> If high amount: require approval
  -> If sensitive fields: mask
  -> If risky write: degrade to draft
  -> Budget tracks cost/steps/tools
  -> Audit report generated
  -> Structured output returned
```

---

## 8.4 展示点

| 展示点 | 对应框架能力 |
|---|---|
| 报销请求 | Session |
| 公司政策 | Retriever |
| 发票检查 | Tool |
| 金额阈值 | Policy |
| 超额审批 | REQUIRE_APPROVAL |
| 字段脱敏 | MASK |
| 只生成草稿 | DEGRADE |
| 工具预算 | Budget |
| 审计报告 | Replay / Audit |
| 标准结果 | Structured output |
| 外部系统 | MCP / Tool |

---

# 9. 风险与反模式

---

## 9.1 不要继续堆 feature 掩盖核心语义

下一阶段不应优先增加：

- 更多 reasoning strategies；
- 更多 demo tools；
- 更多 provider adapters；
- 更复杂 RAG 名词；
- 更多 multi-agent 花活。

优先级应是：

- permission semantics；
- tool governance；
- audit report；
- policy engine；
- credential broker；
- replay fidelity；
- deployment hardening。

---

## 9.2 不要过早宣称生产级安全

当前可以说：

> Alpha-stage runtime framework with production-oriented design.

不能说：

> Production-ready enterprise agent security platform.

---

## 9.3 不要让文档超前实现

如果某能力只是 modeled，应写 modeled。

如果只是 planned，应写 planned。

如果是 lightweight reference implementation，应写 lightweight。

生产可用项目最怕“文档承诺强于代码语义”。

---

# 10. 最终路线建议

## 短期：v0.1.6

聚焦语义闭环：

1. DEGRADE 真正降级；
2. input/output/event mask 分离；
3. tool side-effect metadata；
4. event audit 字段补齐；
5. 文档同步；
6. CI 可见。

---

## 中期：v0.2.x - v0.4.x

聚焦企业 PoC：

1. 企业审批 demo；
2. structured audit report；
3. YAML policy MVP；
4. CredentialBroker MVP；
5. Tool governance；
6. deterministic rerun；
7. OTel / SIEM；
8. benchmark。

---

## 长期：v0.5.x - v1.0

聚焦生产化：

1. deployment；
2. security hardening；
3. supply chain；
4. multi-tenant；
5. durable storage；
6. policy versioning；
7. production guide；
8. external validation；
9. API freeze；
10. v1.0。

---

# 11. 最终判断

petfishFramework 的方向是对的，而且 0.1.5 已经比 0.1.4 更接近“可信 runtime”。

它最值得保留的核心是：

> Environment 作为完全仲裁点，统一控制 model / tool / retriever 调用，并在该点实施 permission、budget、audit、replay 和 reliability evaluation。

它距离生产可用的核心差距不是“还缺几个 Agent 功能”，而是：

> 还缺一整套围绕运行时安全、工具治理、策略治理、凭据治理、审计治理、可靠性治理和部署治理的工程闭环。

如果按本文路线推进，petfishFramework 可以形成非常清晰的差异化：

> 不是又一个 Agent 编排库，而是一个面向企业 Agent 运行时控制的轻量级 runtime framework。

这条路线值得继续推进。

---

# 12. 参考来源

- PyPI petfishframework 0.1.5: https://pypi.org/project/petfishframework/0.1.5/
- GitHub repository: https://github.com/kylecui/petfishFramework
- GitHub CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
- GitHub API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
