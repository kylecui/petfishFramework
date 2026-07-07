# petfishFramework v0.1.6 Playground 复测与后续建议

> 当前版本：`petfishframework==0.1.6`  
> 发布页面：https://pypi.org/project/petfishframework/0.1.6/  
> 本文目的：整理 v0.1.6 相比 v0.1.5 的关键变化、当前先进性、残余风险，以及下一阶段建议。

---

## 1. 总体判断

v0.1.6 是一次有实质意义的版本推进。

如果说 v0.1.5 的关键价值是修复了 `DENY`、`REQUIRE_APPROVAL`、`PARTIAL_ALLOW` 的 pre-execution enforcement，那么 v0.1.6 的关键价值是：

> `MASK` 和 `DEGRADE` 的运行时语义开始闭环。

具体来说：

- `MASK` 已经从单纯 output mask，推进到 input mask + output mask；
- `DEGRADE` 已经从“只记录 degraded 事件”，推进到“可执行 fallback tool switching”；
- 核心 quickstart、budget、permission、replay、Pass^k 等能力继续保持可用；
- PyPI 文档已经明确列出 v0.1.6 的能力状态与当前限制。

但 v0.1.6 仍然不是生产可用版本。

当前最重要的风险是：

> 当 `DEGRADE` 没有提供 fallback tool 时，当前行为仍可能退回执行原始工具。对一个安全语义框架来说，这不符合 fail-closed 原则。

因此，v0.1.6 可以被定位为：

> Alpha-stage permission-aware Agent runtime，已经具备较完整的 DecisionEffect 执行骨架。

但不应定位为：

> Production-ready enterprise Agent security framework。

---

## 2. 公开信息摘要

根据 PyPI v0.1.6 项目页，当前公开信息包括：

| 项目 | 信息 |
|---|---|
| 包名 | `petfishframework` |
| 当前版本 | `0.1.6` |
| 发布时间 | 2026-07-07 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| License | MIT |
| Extras | `openai` / `anthropic` / `mcp` |
| 项目定位 | reliable, auditable, budget-aware, permission-aware AI agents |
| Quickstart | Zero-cost FakeModel quickstart |
| MCP client | stdio transport available |
| Replay | Audit replay available |
| Deterministic rerun / resume | Planned |
| MCP server mode | Planned |

PyPI v0.1.6 Current Limitations 中已经明确列出：

- `DENY`：pre-execution block；
- `REQUIRE_APPROVAL`：pre-execution block；
- `PARTIAL_ALLOW`：pre-execution arg filtering；
- `MASK`：input mask before + output mask after；
- `DEGRADE`：fallback tool switching；
- Deterministic rerun / resume：planned；
- MCP server mode：planned；
- LATS / LLM+P：lightweight implementations；
- CRAG / Adaptive-RAG：lightweight reference implementations。

这说明 v0.1.6 的文档表述比早期版本更接近真实能力边界。

---

## 3. Playground 复测摘要

## 3.1 测试结果总览

| 测试项 | v0.1.6 结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，显示 `0.1.6` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 通过，触发 `BudgetExceeded` | 稳定 |
| `DENY` | 通过，工具未执行 | 正确 |
| `REQUIRE_APPROVAL` | 通过，工具未执行 | 正确 |
| `PARTIAL_ALLOW` | 通过，执行前裁剪参数 | 正确 |
| `MASK` input mask | 通过，执行前移除敏感字段 | 明显进步 |
| `MASK` output mask | 通过，返回结果被脱敏 | 明显进步 |
| `DEGRADE` with fallback | 通过，原工具不执行，fallback 执行 | 关键进步 |
| `DEGRADE` without fallback | 存在风险，可能仍执行原工具 | 需要修复 |
| `session.replay()` | 通过 | 事件可用 |
| `pass_at_k_with_perturbations` | 通过 | 稳定 |
| MCP client stdio | 前序测试可跑，PyPI 也标为 available | 可继续保留为能力点 |

---

## 4. v0.1.6 的关键改进

## 4.1 `DEGRADE` 从记录语义推进到执行语义

v0.1.5 中，`DEGRADE` 仍主要是 modeled / recorded：即可以记录 degraded，但并没有真正改变执行路径。

v0.1.6 中，`DEGRADE` 已经支持 fallback tool switching。

理想语义如下：

```text
policy returns DEGRADE
  -> do not execute original high-risk tool
  -> resolve fallback tool
  -> validate fallback args
  -> execute fallback tool
  -> emit tool.degraded event
```

典型例子：

```text
dangerous_delete_file  -> preview_delete_file
send_email             -> draft_email
approve_payment        -> request_approval
write_database         -> dry_run_sql
external_post_api      -> readonly_lookup
```

这对 petfishFramework 非常重要。因为 `DEGRADE` 是企业 Agent 安全中非常常见的控制方式：

> 不一定完全拒绝任务，而是把高风险动作降级为低风险动作。

例如：

- 不直接发邮件，改为生成草稿；
- 不直接删除文件，改为展示删除计划；
- 不直接付款，改为提交审批；
- 不直接写数据库，改为 dry-run；
- 不直接调用公网写接口，改为只读查询。

v0.1.6 开始具备这类运行时控制能力。

---

## 4.2 `MASK` 从 output-only 推进到 input + output

v0.1.5 的 `MASK` 更像输出结果脱敏。

v0.1.6 已经支持：

- `input_mask_fields`
- `output_mask_fields`

这意味着框架开始区分：

| 类型 | 发生时机 | 价值 |
|---|---|---|
| input mask | 工具执行前 | 防止敏感字段发给外部工具 |
| output mask | 工具执行后 | 防止敏感结果返回给模型或用户 |

这是一个关键变化。

对企业安全来说，只做 output mask 往往不够。因为敏感数据可能已经被发送给外部工具、外部 API 或 MCP server。

更安全的语义应该是：

```text
raw args
  -> input mask
  -> policy-approved args
  -> tool execution
  -> raw result
  -> output mask
  -> result exposed to model/user
```

v0.1.6 已经朝这个方向推进。

---

## 4.3 DecisionEffect 执行骨架更完整

到 v0.1.6，DecisionEffect 的执行状态可以总结为：

| DecisionEffect | 当前语义 | 状态 |
|---|---|---|
| `ALLOW` | 正常执行 | 可用 |
| `DENY` | 执行前阻断 | 可用 |
| `REQUIRE_APPROVAL` | 审批前不执行 | 可用 |
| `PARTIAL_ALLOW` | 执行前裁剪参数 | 可用 |
| `MASK` | 输入脱敏 + 输出脱敏 | 基本可用 |
| `DEGRADE` | fallback tool switching | 基本可用，但需 fail-closed 修复 |

这已经比 v0.1.4 / v0.1.5 更接近真正的 runtime access control model。

---

## 5. 当前最重要的残余风险

## 5.1 `DEGRADE` 缺少 fallback 时不应执行原工具

当前最需要修复的问题：

> 如果 policy 返回 `DEGRADE`，但没有提供 fallback tool，框架不应继续执行原始工具。

否则会出现安全语义反转：

```text
policy: 这个工具太危险，需要降级
runtime: 没有 fallback，所以继续执行原危险工具
```

这不符合安全框架应有的 fail-closed 原则。

## 5.1.1 建议语义

应改为：

```text
DEGRADE + fallback_tool exists
  -> execute fallback tool
  -> original_executed = false
  -> fallback_executed = true
  -> event = tool.degraded

DEGRADE + fallback_tool missing
  -> block
  -> original_executed = false
  -> fallback_executed = false
  -> event = tool.degrade_failed
```

## 5.1.2 推荐事件

```yaml
type: tool.degrade_failed
decision_effect: DEGRADE
reason: fallback tool not provided
original_tool: danger
original_executed: false
fallback_tool: null
fallback_executed: false
executed: false
```

## 5.1.3 推荐异常或返回

可以选择两种方式：

### 方案 A：抛异常

```python
raise DegradeFailed("DEGRADE requires fallback_tool in fail-closed mode")
```

### 方案 B：返回 observation

```text
degrade_failed: fallback tool not provided
```

对于安全框架，建议默认采用 fail-closed，至少提供配置项：

```python
RuntimeEnvironment(
    degrade_without_fallback="block"  # block | allow_original
)
```

默认必须是：

```python
block
```

---

## 5.2 `MASK` 还需要 event mask 与 nested mask

v0.1.6 已经有 input mask 和 output mask，这是实质进步。

下一步建议补：

- `event_mask_fields`
- nested dict mask
- list item mask
- hash mask
- preserve-format mask
- selective mask by subject role
- mask policy audit

## 5.2.1 为什么需要 event mask

即使 input / output 已经 mask，审计日志仍可能泄露：

- 原始 args；
- 原始 result；
- API key；
- OAuth token；
- 身份证号；
- 电话；
- 邮箱；
- 银行卡号；
- prompt 原文；
- RAG snippet 原文。

因此需要：

```python
Decision(
    effect=DecisionEffect.MASK,
    input_mask_fields=("ssn",),
    output_mask_fields=("secret",),
    event_mask_fields=("api_key", "raw_prompt"),
)
```

## 5.2.2 nested mask 示例

企业数据往往不是平铺结构：

```json
{
  "user": {
    "name": "Alice",
    "ssn": "123-45-6789",
    "cards": [
      {"number": "4111111111111111"}
    ]
  }
}
```

应支持：

```text
user.ssn
user.cards[*].number
```

---

## 5.3 Tool metadata 仍需系统化

`DEGRADE` 和 `MASK` 的语义越丰富，越需要 Tool 自己声明风险属性。

建议每个 Tool 至少声明：

```yaml
name: send_email
risk_level: high
side_effect: true
idempotent: false
external_egress: true
requires_credentials: true
capabilities:
  - email.send
  - network.egress
```

否则 policy 很难可靠判断：

- 是否允许执行；
- 是否需要审批；
- 是否需要降级；
- 是否需要 input mask；
- 是否需要 output mask；
- 是否需要 event mask；
- 是否允许 retry；
- 是否需要 idempotency key。

---

## 5.4 文档仍需要同步

PyPI v0.1.6 文档已经明显进步，但 GitHub API Reference 仍可能存在旧表述问题，例如 MCP stdio 是否 stub、API reference 版本号是否仍停留在早期版本。

建议 v0.1.7 前完成：

- PyPI 项目页同步；
- GitHub README 同步；
- docs/api.md 同步；
- docs/usage.md 同步；
- CHANGELOG 同步；
- 测试数量同步；
- status matrix 同步；
- 所有示例自动测试。

文档同步不是形式问题，而是可信度问题。

如果一个项目主打 reliability / auditability，但自己的公开文档互相冲突，会削弱技术信任。

---

## 5.5 测试与供应链可信度仍需补强

PyPI v0.1.6 页面显示 Tests badge 为 210，但 Development 段落仍出现 `187 tests` 的旧数字。

此外，PyPI 文件元数据显示：

```text
Uploaded using Trusted Publishing? No
Uploaded via: twine
```

对普通库这不是严重问题，但对一个主打安全、审计、运行时控制的框架，后续应该补：

- GitHub Actions badge；
- coverage badge；
- Ruff / mypy badge；
- SBOM；
- signed release；
- PyPI Trusted Publishing；
- provenance；
- SECURITY.md；
- vulnerability disclosure process。

---

## 6. 与 v0.1.5 的对比

| 维度 | v0.1.5 | v0.1.6 |
|---|---|---|
| Quickstart | 可跑 | 可跑 |
| Budget | 可用 | 可用 |
| DENY | pre-execution block | pre-execution block |
| REQUIRE_APPROVAL | pre-execution block | pre-execution block |
| PARTIAL_ALLOW | pre-execution arg filtering | pre-execution arg filtering |
| MASK | 主要 output mask | input mask + output mask |
| DEGRADE | modeled / 记录 | fallback tool switching |
| DEGRADE 无 fallback | 风险较小，因为尚未宣称完整 | 成为明确语义风险 |
| Replay | audit replay | audit replay |
| MCP client | 可用 | 可用 |
| 文档 | PyPI 较好，局部冲突 | PyPI 更好，仍需同步 GitHub docs |
| 企业 PoC 可用性 | 接近 | 更接近 |
| 生产可用性 | 不建议 | 仍不建议 |

---

## 7. 五顾问评判

## 7.1 反对者

v0.1.6 还不能称为生产可用。

主要原因：

1. `DEGRADE` 没有 fallback 时仍可能执行原工具，不符合 fail-closed；
2. `MASK` 还缺 event mask、nested mask、mask mode；
3. 工具元数据治理不完整；
4. 文档仍需同步；
5. 测试数量与 CI 可见性不足；
6. 供应链安全还没达到安全项目应有标准。

结论：

> v0.1.6 能证明方向，但不能证明生产成熟度。

---

## 7.2 本质思考者

v0.1.6 的本质进步不是多了一个 feature，而是：

> DecisionEffect 的执行语义更接近真实运行时访问控制。

这非常重要。

Agent 安全的关键不是提示词里告诉模型“不要做坏事”，而是让所有能力调用都经过 runtime，并由 runtime 决定：

- 是否执行；
- 是否阻断；
- 是否审批；
- 是否裁剪；
- 是否脱敏；
- 是否降级；
- 是否审计；
- 是否超预算。

v0.1.6 已经朝这个方向迈出关键一步。

---

## 7.3 机会挖掘者

现在可以更有底气地讲：

> petfishFramework 已经具备 Alpha 阶段的 runtime access control skeleton，覆盖 block、approval、partial allow、mask、degrade fallback、budget、audit replay 和 Pass^k。

它的差异化已经比较清晰：

```text
不是普通 Agent 编排库
而是面向企业 Agent 的运行时控制框架
```

这可以与以下叙事连接：

- 企业 AI 从 PoC 到生产；
- Agent 工具调用治理；
- 运行时访问控制；
- 最小权限；
- 完全仲裁；
- 可审计执行；
- contract-driven harness；
- AI-native infrastructure security。

---

## 7.4 局外人

外部开发者最关心三件事：

1. Quickstart 能不能跑；
2. 文档是不是可信；
3. 宣称的安全能力是不是语义正确。

v0.1.6 在第 1 点已经比较好，在第 3 点明显进步，但第 2 点仍需要收口。

尤其是 PyPI、README、API Reference、CHANGELOG 之间必须一致。

---

## 7.5 执行者

v0.1.7 不建议继续堆新 feature。

建议只做五件事：

1. `DEGRADE` 无 fallback 时 fail-closed；
2. 增加 `event_mask_fields` 与 nested mask；
3. 增加 Tool metadata；
4. 同步文档；
5. 增加 CI / coverage / Trusted Publishing。

这些比新增另一个 reasoning strategy 更重要。

---

## 8. v0.1.7 建议路线

## 8.1 P0：修 `DEGRADE` fail-closed

### 当前风险

```text
DEGRADE without fallback
  -> original tool may execute
```

### 建议修复

```text
DEGRADE without fallback
  -> block
  -> original_executed = false
  -> event = tool.degrade_failed
```

### 验收测试

```python
def test_degrade_without_fallback_does_not_execute_original_tool():
    state = {"danger_calls": 0}

    policy = DegradeWithoutFallbackPolicy()

    result = agent.run("call danger tool", permission_policy=policy)

    assert state["danger_calls"] == 0
    assert any(e.type == "tool.degrade_failed" for e in session.replay())
```

---

## 8.2 P1：补 `event_mask_fields`

### 目标

避免审计日志成为敏感数据泄漏源。

### 建议 API

```python
Decision(
    effect=DecisionEffect.MASK,
    input_mask_fields=("ssn",),
    output_mask_fields=("secret",),
    event_mask_fields=("api_key", "raw_prompt"),
)
```

### 验收标准

- 工具执行前 input mask 生效；
- 工具执行后 output mask 生效；
- 写 event 前 event mask 生效；
- raw args / raw result 不泄露敏感字段；
- 可选保留 hash 供审计追踪。

---

## 8.3 P1：支持 nested mask

### 建议字段语法

```text
user.ssn
user.cards[*].number
invoice.vendor.tax_id
```

### mask mode

建议支持：

| mode | 示例 |
|---|---|
| drop | 删除字段 |
| redact | `[MASKED]` |
| hash | `sha256:...` |
| preserve_format | `****-****-****-1234` |

---

## 8.4 P1：Tool metadata

建议 Tool 至少支持：

```python
class SendEmailTool(Tool):
    name = "send_email"
    risk_level = "high"
    side_effect = True
    idempotent = False
    external_egress = True
    capabilities = ("email.send", "network.egress")
```

Policy 可以据此判断：

```python
if resource.tool.side_effect and subject.role != "approver":
    return Decision(effect=DecisionEffect.REQUIRE_APPROVAL)
```

---

## 8.5 P1：事件语义增强

每个 tool event 建议包含：

```yaml
tool_name: danger
decision_effect: DEGRADE
decision_reason: fallback required
executed: false
original_tool: danger
original_executed: false
fallback_tool: safe_lookup
fallback_executed: true
input_masked: true
output_masked: true
event_masked: true
```

---

## 8.6 P2：文档与可信度

需要同步：

- PyPI；
- README；
- API Reference；
- Usage Guide；
- CHANGELOG；
- Examples；
- tests count；
- Current Limitations；
- status matrix。

建议增加：

- GitHub Actions badge；
- coverage badge；
- Ruff / mypy badge；
- PyPI Trusted Publishing；
- SECURITY.md；
- SBOM。

---

## 9. 生产可用性判断

## 9.1 当前可以说什么

可以说：

> petfishFramework v0.1.6 is an Alpha-stage runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.

可以说：

> It now supports enforced permission effects including DENY, REQUIRE_APPROVAL, PARTIAL_ALLOW, MASK, and DEGRADE fallback switching.

可以说：

> It is suitable for experimentation and controlled enterprise PoC design.

---

## 9.2 当前不应说什么

不建议说：

- production-ready；
- enterprise-grade access control；
- complete policy engine；
- full MCP support；
- complete deterministic replay；
- fully hardened security framework；
- proven benchmark superiority；
- safe by default in production。

---

## 9.3 当前最合适定位

建议定位为：

> 一个正在快速收敛的 Alpha-stage Agent runtime control framework。

中文：

> petfishFramework 是一个正在快速收敛的 Alpha 阶段 Agent 运行时控制框架，重点解决工具调用、权限语义、预算硬限制、审计回放与可靠性评测问题。

---

## 10. 下一阶段优先级

## 10.1 立即做

1. `DEGRADE` 无 fallback 时 fail-closed；
2. 文档同步；
3. 测试数量同步；
4. CI badge；
5. Trusted Publishing。

## 10.2 短期做

1. event mask；
2. nested mask；
3. Tool metadata；
4. structured audit report；
5. policy examples；
6. enterprise PoC demo。

## 10.3 中期做

1. YAML policy engine；
2. CredentialBroker；
3. deterministic rerun；
4. OpenTelemetry；
5. MCP governance；
6. tool sandbox；
7. benchmark。

## 10.4 长期做

1. production deployment guide；
2. multi-tenant isolation；
3. SIEM integration；
4. supply chain hardening；
5. security review；
6. v1 API freeze。

---

## 11. 最终结论

v0.1.6 是一次实质推进。

它最重要的变化是：

> `MASK` 与 `DEGRADE` 开始具备真正的运行时控制语义。

这意味着 petfishFramework 已经不只是“定义了权限效果”，而是在逐步把这些效果变成真实执行路径。

当前最值得肯定的是：

- Quickstart 稳定；
- Budget 可硬中断；
- DENY / REQUIRE_APPROVAL / PARTIAL_ALLOW 语义正确；
- MASK 支持 input + output；
- DEGRADE 支持 fallback tool switching；
- Replay / Pass^k / MCP client 继续可用；
- 公开文档开始更准确描述能力边界。

当前最需要修的是：

> `DEGRADE` 无 fallback 时必须 fail-closed。

只要这个问题修掉，再补 event mask、Tool metadata、审计报告和文档同步，petfishFramework 就可以更正式地进入“企业 PoC 可用”的阶段。

---

## 12. 参考链接

- PyPI v0.1.6: https://pypi.org/project/petfishframework/0.1.6/
- GitHub Repository: https://github.com/kylecui/petfishFramework
- API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
