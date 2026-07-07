# petfishFramework 开发计划

> 基于 v0.1.5 + 3 份用户反馈 + 生产可用路线图
> 原则：**TDD 先行，语义闭环优先，不堆 feature**

---

## 版本路线图（对齐反馈）

```
v0.1.6  语义补全（DEGRADE + MASK 分离 + 工具元数据 + 审计字段）
v0.2.0  企业 PoC（报销审批 demo + 审计报告 + CredentialBroker + 工具治理）
v0.3.0  策略引擎（YAML policy + 规则匹配 + 策略版本 + 策略测试）
v0.4.0  可观测性 / Replay（OTel + 确定性回放 + SIEM 导出 + trace diff）
v0.5.0  工具 / MCP 治理（schema 校验 + 沙箱 + MCP allowlist + 限流）
v0.6.0  生产候选（Dockerfile + K8s + 威胁模型 + SBOM + 签名发布）
v1.0.0  生产可用（API 冻结 + 向后兼容 + 外部验证）
```

---

## v0.1.6：语义补全版

> 目标：把 permission-aware runtime 的语义补齐，让安全叙事可信。

### 任务 1：DEGRADE 真实降级执行

**现状**：DEGRADE 只是记录事件，不改变执行路径。

**目标**：DEGRADE 不执行原始工具，执行 fallback 工具。

#### TDD 测试先行

```python
# tests/test_degrade.py

def test_degrade_does_not_execute_original_tool():
    """DEGRADE: 原始工具不执行。"""
    state = {"dangerous_calls": 0, "safe_calls": 0}
    # policy 返回 DEGRADE + fallback_tool
    # 验证: state["dangerous_calls"] == 0

def test_degrade_executes_fallback_tool():
    """DEGRADE: fallback 工具执行。"""
    # 验证: state["safe_calls"] == 1

def test_degrade_event_records_both_tools():
    """DEGRADE 事件包含 original_tool + fallback_tool。"""
    # 验证: event.data["original_tool"] == "send_email"
    # 验证: event.data["fallback_tool"] == "draft_email"
    # 验证: event.data["original_executed"] == False
    # 验证: event.data["fallback_executed"] == True
```

#### 实现

1. `Decision` 增加 `fallback_tool: str | None` 和 `fallback_args: dict | None`
2. `RuntimeEnvironment.call()`:
   ```python
   if effect == DEGRADE and decision.fallback_tool:
       fallback = self._find_tool(decision.fallback_tool)
       result = fallback.execute(decision.fallback_args or args)
       emit("tool.degraded", original_tool=ref.name, fallback_tool=..., ...)
       return result
   ```
3. 同步更新 `call_async()`

---

### 任务 2：MASK 输入/输出分离

**现状**：MASK 只做 post-execution result masking。

**目标**：区分 input mask（执行前）/ output mask（执行后）/ event mask（审计时）。

#### TDD 测试先行

```python
# tests/test_mask_semantics.py

def test_input_mask_strips_fields_before_execution():
    """Input mask: ssn 在工具执行前被移除。"""
    captured = {}
    # policy: Decision(MASK, input_mask_fields=["ssn"])
    # 验证: "ssn" not in captured args

def test_output_mask_applies_after_execution():
    """Output mask: 工具执行后 phone 被掩码。"""
    # policy: Decision(MASK, output_mask_fields=["phone"])
    # 验证: result 不含原始 phone 值

def test_event_mask_redacts_in_audit_log():
    """Event mask: 审计日志中 api_key 被替换为 [REDACTED]。"""
    # policy: Decision(MASK, event_mask_fields=["api_key"])
    # 验证: event.data 中 api_key == "[REDACTED]"
```

#### 实现

1. `Decision` 增加字段：`input_mask_fields`, `output_mask_fields`, `event_mask_fields`
2. `call()` 流程：
   ```python
   if effect == MASK:
       # Pre: input mask
       if decision.input_mask_fields:
           args = {k: v for k, v in args.items() if k not in decision.input_mask_fields}
       # Execute
       result = tool.execute(args)
       # Post: output mask
       if decision.output_mask_fields:
           result = self._mask_result_fields(result, decision.output_mask_fields)
   ```
3. 事件写入时应用 event_mask_fields

---

### 任务 3：工具副作用元数据

**现状**：Tool 只有 risk_level + capabilities。

**目标**：Tool 声明 side_effect、idempotent、reversible 等。

#### TDD 测试先行

```python
def test_tool_with_side_effect_metadata():
    """Tool 声明 side_effect=True。"""
    # 验证 tool.side_effect == True

def test_high_side_effect_tool_visible_only_with_policy():
    """有副作用的工具默认在高风险策略下不可见。"""
    # 验证 DenyByDefaultPolicy 拒绝 side_effect=True 的工具
```

#### 实现

1. `BaseTool` 增加字段：`side_effect: bool = False`, `idempotent: bool = True`, `reversible: bool = False`
2. Calculator/WordSorter: `side_effect=False, idempotent=True`
3. AgentAsTool: `side_effect=True, idempotent=False`
4. 新增工具强制声明

---

### 任务 4：审计事件字段补齐

**现状**：事件有 `executed: true/false`，但缺 `duration_ms`, `error`, `actor` 等。

#### TDD 测试先行

```python
def test_tool_event_has_duration():
    """tool.called 事件包含 duration_ms。"""

def test_failed_tool_has_error_field():
    """tool.failed 事件包含 error 信息。"""
```

#### 实现

1. `Event` 增加 `duration_ms: float | None`, `error: str | None`
2. `RuntimeEnvironment` 在工具执行前后记录时间
3. 异常捕获 → emit `tool.failed`

---

### 任务 5：CI 可见性 + 文档同步

- GitHub Actions badge in README
- Coverage report (pytest-cov)
- PyPI / README / API Reference 一致性检查
- CHANGELOG 更新

---

## v0.2.0：企业 PoC Demo 版

> 目标：端到端企业场景，让用户看到框架组合价值。

### 任务 1：结构化审计报告

#### TDD 测试先行

```python
def test_markdown_audit_report_contains_session_info():
    """审计报告包含 session_id, model, tokens, cost。"""

def test_audit_report_contains_tool_call_table():
    """审计报告包含工具调用表格。"""

def test_audit_report_contains_permission_decisions():
    """审计报告包含权限决策列表。"""
```

#### 实现

- `AuditReport.from_events(events) -> AuditReport`
- `AuditReport.to_markdown() -> str`
- `AuditReport.to_json() -> dict`
- 内容：Summary + Timeline + Tool Calls + Permission Decisions + Budget + Output

### 任务 2：CredentialBroker MVP

#### TDD 测试先行

```python
def test_credential_broker_issues_scoped_token():
    """Broker 发放 scoped 临时 token。"""

def test_credential_not_in_event_log():
    """事件日志中不记录 secret。"""

def test_credential_expires():
    """token 有 TTL，过期失效。"""
```

### 任务 3：企业报销审批 Agent

- 完整 demo：RAG + Tool + Permission + Budget + Audit + Structured Output
- 展示全部 5 种 DecisionEffect
- 使用 FakeModel 可运行

### 任务 4：工具风险分级 + 可见性门

- `CapabilityProjection` 实现：高风险工具默认不可见
- Tool risk classification: LOW / MEDIUM / HIGH / CRITICAL

---

## v0.3.0：策略引擎版

> 目标：从代码策略进入配置化策略。

### Phase 1: YAML Policy

```yaml
rules:
  - name: high-value-approval
    when:
      action.type: call
      action.tool_name: approve_payment
      context.amount_gt: 1000
    effect: REQUIRE_APPROVAL
    reason: "amount exceeds threshold"
```

#### TDD 测试先行

```python
def test_yaml_policy_deny_rule():
    """YAML deny 规则正确阻断。"""

def test_yaml_policy_priority_ordering():
    """高优先级规则先匹配。"""

def test_yaml_policy_deny_overrides():
    """deny-overrides 组合策略。"""
```

### Phase 2: 策略测试 + 审计

```yaml
tests:
  - name: analyst-cannot-approve-large-payment
    input: {subject.role: analyst, action.tool_name: approve_payment, context.amount: 5000}
    expect: {effect: DENY}
```

---

## v0.4.0：可观测性 / Replay 版

### 确定性回放（Level 2）

#### TDD 测试先行

```python
def test_deterministic_rerun_reproduces_trajectory():
    """录制 → 回放 → 轨迹一致。"""

def test_rerun_detects_divergence():
    """回放偏离时检测到并报告。"""
```

### OpenTelemetry 集成

- `OTelSink(EventEmitter)` — 事件 → OTel spans
- Session → trace, tool call → span, model call → span

---

## 执行原则

1. **每个任务 TDD 先行**：先写测试（含 known-bad），再实现
2. **不堆 feature**：v0.1.6 只做语义补全，不加新策略/适配器
3. **文档同步**：每个版本 PyPI / README / API Reference / CHANGELOG 一致
4. **测试门禁**：每个 PR 必须通过全部测试 + ruff
5. **版本节奏**：v0.1.6 快速迭代（1-2 天），v0.2.0 中等（1 周），后续按反馈调整

---

## 当前优先级（v0.1.6 立即执行）

| # | 任务 | TDD 测试数 | 复杂度 | 阻塞 |
|---|---|---|---|---|
| 1 | DEGRADE 降级执行 | 3 | 中 | 无 |
| 2 | MASK 输入/输出分离 | 3 | 中 | 无 |
| 3 | 工具副作用元数据 | 2 | 低 | 无 |
| 4 | 审计事件字段补齐 | 2 | 低 | 无 |
| 5 | CI badge + coverage | 0 | 低 | 无 |

**v0.1.6 总计 ~10 个新测试 + 5 个实现任务。**
