# petfishFramework v0.2.1 Review：主要问题是否已经解决

> 版本：`petfishframework==0.2.1`  
> 发布页：https://pypi.org/project/petfishframework/0.2.1/  
> 背景说明：`0.2.0` 被 api.md-only 发布占用，实际内容版本递增为 `0.2.1`。  
> 本次复测目标：核验 v0.1.9 之后遗留的 5 个主要 todo 是否完成，并判断 v0.2.1 是否已进入“企业 PoC 可用性收口”阶段。

---

## 1. 总体结论

结论可以直接说：

> v0.2.1 已经解决了大部分核心 runtime 问题，也解决了 v0.1.9 阶段最重要的 AuditReport、DecisionEffect、mask、DEGRADE、CI、SECURITY.md 等生产化前置问题。

但仍有少量文档一致性问题需要修：

1. `docs/api.md` 内容已经大幅同步，但标题仍写 `v0.1.9`，应更新为 `v0.2.1`；
2. PyPI / README 的 Enterprise PoC 段落仍写 `examples/05_enterprise_expense.py (coming in v0.2.0 release)`，这对 `v0.2.1` 来说已经过时；
3. `tests/test_enterprise_demo.py` 已存在并覆盖企业 expense 场景，但 `examples/05_enterprise_expense.py` 路径未能成功获取；
4. README tests badge 存在轻微不一致：显示文本为 `Tests: 234`，但 badge URL 仍像是 `tests-213`；
5. Trusted Publishing 仍未启用，但用户已明确说明 deferred to v0.2.0 / v0.2.x，因此本文不将其作为 v0.2.1 阻断项。

综合判断：

> v0.2.1 已经可以更明确地定位为“企业 PoC 可用的 Alpha-stage Agent runtime control framework”，但仍不是 production-ready。

---

## 2. PyPI 公开信息摘要

PyPI v0.2.1 页面显示：

| 项目 | 状态 |
|---|---|
| 包名 | `petfishframework` |
| 版本 | `0.2.1` |
| 发布时间 | 2026-07-07 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| License | MIT |
| Extras | `openai` / `anthropic` / `mcp` |
| 短描述 | `A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.` |
| Tests badge | 234 |
| Development test command | `uv run pytest # 234 tests` |
| MCP client stdio | Available |
| MCP server mode | Planned |
| Session replay | Audit replay available |
| Deterministic rerun / resume | Planned |
| Trusted Publishing | No |

PyPI 当前描述已经比较准确：它不再强调 general AI Agent framework，而是明确说 runtime framework。

这点非常重要，因为 petfishFramework 的核心差异化不是“通用 Agent 编排”，而是：

> Agent 运行时控制：权限、预算、审计、回放、mask、degrade、Pass^k。

---

## 3. Playground 复测摘要

## 3.1 测试环境

```bash
python3 -m venv /tmp/pf021
source /tmp/pf021/bin/activate
pip install petfishframework==0.2.1
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.2.1
```

---

## 3.2 核心实测结果

| 测试项 | v0.2.1 实测结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，显示 `0.2.1` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 通过，触发 `BudgetExceeded` | 稳定 |
| `DENY` | 通过，工具未执行 | 正确 |
| `REQUIRE_APPROVAL` | 通过，工具未执行 | 正确 |
| `PARTIAL_ALLOW` | 通过，执行前裁剪参数 | 正确 |
| `MASK` input mask | 通过，执行前脱敏 | 正确 |
| `MASK` output mask | 通过，返回结果脱敏 | 正确 |
| `MASK` event mask | 通过，事件日志脱敏 | 正确 |
| nested mask | 通过，`nested.ssn` 可脱敏 | 正确 |
| `DEGRADE` with fallback | 通过，原工具不执行，fallback 执行 | 正确 |
| `DEGRADE` without fallback | 通过 fail-closed，原工具不执行 | 正确 |
| `session.replay()` | 通过 | 事件可用 |
| `AuditReport` 默认带 Result | 通过 | v0.1.8 问题已解决 |
| AuditReport Markdown | 通过，含 Summary / Event Count / Permission Summary / Budget / Timeline / Masked Fields / Final Output | v2 明显增强 |
| `pass_at_k_with_perturbations` | 通过 | 稳定 |
| Tool metadata | `BaseTool` 含 side_effect / idempotent / external_egress / requires_credentials | 稳定 |
| SECURITY.md | 存在 | 供应链/安全响应开始收口 |
| CI workflow | `.github/workflows/ci.yml` 存在 | 已有 Python 3.10-3.12 + ruff + pytest |
| GitHub API Reference | 内容已大幅同步，但标题仍写 v0.1.9 | 部分解决 |
| Enterprise PoC example | test 已存在，example 文件路径未验证成功 | 部分解决 |

---

## 4. 五个主要 todo 的完成情况

## 4.1 Todo 1：修 GitHub API Reference

## 结论：基本解决，但仍有版本号小尾巴

v0.1.8 时，`docs/api.md` 最大问题是仍写 MCP stdio 是 stub，与 PyPI 和实际代码冲突。

v0.2.1 中，API Reference 已经明显更新：

- MCP stdio transport 已写为 available；
- `BaseTool` metadata 已写入文档；
- `Decision` fields 已包含 `event_mask_fields`、`fallback_tool`、`fallback_args`；
- DecisionEffect execution semantics 已写清楚；
- nested mask dot-path 与 list wildcard 已写清楚；
- AuditReport 已写入文档；
- SafeByDefaultPolicy 示例已写入文档；
- Tool event fields 已写入文档。

这说明旧的“API Reference 与 PyPI 冲突”问题主体已经解决。

但还有一个小问题：

```text
docs/api.md 第一行仍写：public API of petfishFramework v0.1.9
```

这应更新为：

```text
public API of petfishFramework v0.2.1
```

## 建议

v0.2.2 修：

- `docs/api.md` 标题版本号；
- 若文档由自动脚本生成，版本号从 package metadata 读取；
- API Reference 添加 “Last validated against: 0.2.1”。

---

## 4.2 Todo 2：修 AuditReport 默认不带 Result

## 结论：已解决

v0.1.8 的问题是：

```python
session = agent.session("calc")
result = session.run()
report = audit_report_from_session(session)

report.result is None
```

v0.2.1 实测：

```text
audit_result_none False
audit_md_has_final True
audit_md_has_391 True
audit_md_has_usage True
```

AuditReport Markdown 中已经包含：

- Summary；
- Total Tokens；
- Cost；
- Steps；
- Model Calls；
- Tool Events；
- Permission Decisions；
- Masked Calls；
- Event Count by Type；
- Permission Summary；
- Budget；
- Timeline；
- Masked Fields；
- Final Output。

这说明 v0.1.8 的 audit result attachment 问题已经解决。

## 当前评价

AuditReport 已经从 MVP 进入可用于 PoC 展示的状态。

仍可继续增强：

- policy version；
- subject / action / resource / context；
- raw args hash；
- raw result hash；
- trace hash；
- degraded calls summary；
- approval-required summary；
- blocked calls summary；
- tool metadata summary；
- errors section 的更强展示。

但这不是 v0.2.1 的阻断问题。

---

## 4.3 Todo 3：补 Tool metadata policy 示例

## 结论：已解决

v0.2.1 的 API Reference 中已经有 SafeByDefaultPolicy 示例，展示如何根据 tool metadata 做策略判断：

- `side_effect=True` → `REQUIRE_APPROVAL`
- `external_egress=True` → `DEGRADE`
- 无 fallback → fail-closed

`BaseTool` 的签名中也已经包含：

```python
side_effect: bool = False
idempotent: bool = True
external_egress: bool = False
requires_credentials: bool = False
```

这说明 Tool metadata 已经不只是字段，而是进入了 policy 示例。

## 当前评价

这是一个重要进步。因为企业 Agent 安全不可能只按 tool name 决策，必须根据工具风险属性决策。

下一步建议把这个示例再扩展成：

- `risk_level`
- `capabilities`
- `requires_credentials`
- `external_domains`
- `data_reads`
- `data_writes`
- `sandbox_required`
- `max_retries`
- `timeout_ms`

但 v0.2.1 已经完成了 v0.1.9 阶段要求的基础闭环。

---

## 4.4 Todo 4：企业 PoC demo

## 结论：部分解决

v0.2.1 的 CHANGELOG 显示已经加入：

- Enterprise Expense Approval Agent demo；
- 6 个 TDD tests covering ALL 6 DecisionEffects；
- `PolicyChecker`
- `ApprovePayment(side_effect=True)`
- `DryRunPayment`
- `ExpensePolicy`
- AuditReport v2 enhancement。

`tests/test_enterprise_demo.py` 确实存在，内容覆盖：

- ALLOW；
- PARTIAL_ALLOW；
- MASK；
- REQUIRE_APPROVAL；
- DENY；
- AuditReport；
- 企业 expense policy 场景；
- tool metadata + amount thresholds；
- `ApprovePaymentTool(side_effect=True)`；
- `DryRunPaymentTool`。

这说明企业 PoC demo 的测试层已经存在。

但 PyPI / README 中仍写：

```text
See examples/05_enterprise_expense.py (coming in v0.2.0 release)
and tests/test_enterprise_demo.py
```

对 v0.2.1 来说，这句话已经过时。并且我尝试打开：

```text
examples/05_enterprise_expense.py
```

未成功获取该文件。

## 判断

企业 PoC 已经有 TDD 测试基础，但还没有完全完成“面向用户的 example 资产”。

## 建议

v0.2.2 或 v0.2.3 修：

1. 如果 example 文件已经存在，修正路径；
2. 如果 example 文件还没有发布，新增 `examples/05_enterprise_expense.py`；
3. README / PyPI 从 “coming in v0.2.0” 改为：

```text
See examples/05_enterprise_expense.py and tests/test_enterprise_demo.py
for a complete enterprise expense approval scenario.
```

4. 给这个 demo 增加一段运行说明：

```bash
python examples/05_enterprise_expense.py
```

5. demo 输出应包含：

- final decision；
- tool events；
- AuditReport Markdown；
- all 6 DecisionEffects summary。

---

## 4.5 Todo 5：CI / docs snippet / supply chain

## 结论：CI 与 SECURITY.md 已解决；Trusted Publishing 按计划 deferred

v0.2.1 中：

- `.github/workflows/ci.yml` 存在；
- CI 覆盖 Python 3.10 / 3.11 / 3.12；
- CI 执行 `uv sync --all-extras`；
- CI 执行 `uv run ruff check src/ tests/`；
- CI 执行 `uv run pytest tests/ -q --tb=short`；
- `SECURITY.md` 已存在；
- SECURITY.md 中给出漏洞报告邮箱、响应时间、支持版本和范围。

这说明 CI 与安全披露流程已经开始收口。

Trusted Publishing 仍是 No，但用户已说明 deferred to v0.2.0 / v0.2.x，因此本文不将其列为 v0.2.1 阻断项。

## 建议

v0.2.x 继续补：

- Trusted Publishing；
- SBOM；
- release provenance；
- signed artifact；
- coverage badge；
- docs snippet test；
- example test；
- security scan；
- dependency scan。

---

## 5. Runtime 核心语义状态

v0.2.1 中，6 种 DecisionEffect 的核心执行语义已经比较可信：

| Effect | v0.2.1 状态 | 判断 |
|---|---|---|
| `ALLOW` | 原工具执行 | 正常 |
| `DENY` | pre-execution block | 正确 |
| `REQUIRE_APPROVAL` | pre-execution block | 正确 |
| `PARTIAL_ALLOW` | 先裁剪参数，再执行 | 正确 |
| `MASK` | input / output / event mask，支持 nested path | 正确 |
| `DEGRADE` with fallback | 原工具不执行，fallback 执行 | 正确 |
| `DEGRADE` without fallback | fail-closed，原工具不执行 | 正确 |

这是 petfishFramework 从“有权限模型”走向“有运行时控制语义”的核心成果。

---

## 6. 当前最重要的残留问题

## 6.1 文档版本号与发布内容同步

当前主要是小尾巴，但需要修。

问题：

- `docs/api.md` 标题仍写 v0.1.9；
- PyPI / README Enterprise PoC 文案仍写 coming in v0.2.0；
- README tests badge 文本与图片 URL 可能不一致；
- API Reference 标称 989-line definitive reference，但 raw 文档目前是压缩为少量长行，这影响阅读体验。

建议：

- 文档版本号自动生成；
- README / PyPI long_description 从同一源生成；
- release checklist 中加入 `grep "coming in"`；
- release checklist 中加入 `grep "v0.1"`；
- tests badge 自动生成；
- API Reference 保持正常换行格式。

---

## 6.2 企业 PoC demo 需要从 test 变成 public example

当前 `tests/test_enterprise_demo.py` 已经很有价值，但对用户来说，测试不是 demo。

建议新增：

```text
examples/05_enterprise_expense.py
docs/enterprise-expense-demo.md
```

其中 demo 文档应包含：

- 场景说明；
- 工具定义；
- Policy 规则；
- 6 种 DecisionEffect 展示；
- AuditReport 输出；
- 如何运行；
- 预期输出。

---

## 6.3 Policy Engine / CredentialBroker 仍是下一阶段核心

v0.2.1 解决的是 runtime execution semantics 与 PoC 可见性。

但要走向生产可用，下一阶段仍需要：

- YAML Policy Engine；
- policy versioning；
- policy test harness；
- CredentialBroker；
- scoped temporary credentials；
- secret redaction；
- vault integration；
- OpenTelemetry；
- SIEM export；
- deterministic replay / resume。

这些不应混入 v0.2.1 的“已完成”判断中。

---

## 7. 当前成熟度判断

## 7.1 可以说什么

可以说：

> petfishFramework v0.2.1 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents.

可以说：

> v0.2.1 has enforced runtime semantics for all 6 DecisionEffects and an AuditReport v2 suitable for enterprise PoC demonstrations.

可以说：

> v0.2.1 includes CI, SECURITY.md, and enterprise expense TDD coverage.

可以说：

> v0.2.1 is ready for controlled enterprise PoC design and demonstration.

---

## 7.2 不应说什么

仍不建议说：

- production-ready；
- complete enterprise security platform；
- complete policy engine；
- complete credential governance；
- full MCP server support；
- deterministic replay completed；
- resume completed；
- benchmark-proven superior to LangChain / CrewAI / LangGraph；
- safe by default in all production environments。

---

## 7.3 推荐定位

中文：

> petfishFramework v0.2.1 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备较完整的权限效果执行语义、审计报告能力、企业 expense PoC 测试基础和 CI / SECURITY.md 等工程可信度基础，适合进入受控企业 PoC 展示阶段。

英文：

> petfishFramework v0.2.1 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, now suitable for controlled enterprise PoC demonstrations.

---

## 8. 五顾问评判

## 8.1 反对者

v0.2.1 仍不是 production-ready。

原因：

1. API Reference 标题仍是 v0.1.9；
2. Enterprise PoC public example 文件未完全验证；
3. README / PyPI 文案仍有 “coming in v0.2.0”；
4. Policy Engine 尚未实现；
5. CredentialBroker 尚未实现；
6. deterministic replay / resume 仍 planned；
7. MCP server mode 仍 planned；
8. Trusted Publishing / SBOM / provenance 仍未完成。

但反对者也承认：

> 这次剩下的问题主要是文档与生产化外围，不再是 runtime 核心语义。

---

## 8.2 本质思考者

v0.2.1 的本质变化是：

> petfishFramework 的 runtime control 语义已经基本站住了。

它已经具备：

- 完全仲裁点：Environment；
- 权限效果：6 DecisionEffects；
- 预算硬限制：Budget；
- 审计：Event log + AuditReport；
- 脱敏：input/output/event/nested mask；
- 降级：DEGRADE fallback + fail-closed；
- 可靠性：Pass^k；
- 工具治理基础：BaseTool metadata；
- 工程可信度基础：CI + SECURITY.md。

因此，下一阶段不应继续在 0.2.x 里疯狂加 feature，而应把企业 PoC demo 和文档体验打磨好。

---

## 8.3 机会挖掘者

v0.2.1 已经适合做一场正式 demo：

> 企业报销审批 Agent：从 PoC 到受控执行。

可以展示：

- 小额报销：ALLOW；
- policy check：PARTIAL_ALLOW；
- PII：MASK；
- 高风险支付：REQUIRE_APPROVAL；
- 非 finance 用户：DENY；
- 超大金额：DEGRADE 到 dry-run；
- 缺 fallback：fail-closed；
- 最终生成 AuditReport。

这比 calculator demo 有说服力得多。

---

## 8.4 局外人

外部开发者现在会觉得项目靠谱很多：

- PyPI 清楚；
- Quickstart 能跑；
- API Reference 大幅同步；
- CI 有了；
- SECURITY.md 有了；
- tests 234；
- 企业 demo test 有了。

但他也会被两个小点卡住：

1. “coming in v0.2.0” 这种过期文案；
2. examples 文件路径不可用。

这类问题不难修，但会影响第一印象。

---

## 8.5 执行者

v0.2.2 建议只做四件事：

1. 修文档版本号与过期文案；
2. 补 `examples/05_enterprise_expense.py` 或修正链接；
3. 把 enterprise demo 从 test 变成 public runnable example；
4. 加 docs snippet / example test，防止文档再次漂移。

Trusted Publishing 继续留到 v0.2.x 生产化包，不作为 v0.2.2 阻断项。

---

## 9. v0.2.2 建议清单

## P0：文档一致性

- [ ] `docs/api.md` 标题从 v0.1.9 改为 v0.2.1 / v0.2.2；
- [ ] PyPI / README 删除 `coming in v0.2.0`；
- [ ] README tests badge 与实际 234 tests 一致；
- [ ] API Reference 正常换行，避免 raw markdown 变成超长行；
- [ ] PyPI long_description 与 README 同源生成；
- [ ] release checklist 加 `grep "coming in"`；
- [ ] release checklist 加 `grep "v0.1"`。

## P1：Enterprise example

- [ ] 新增或修正 `examples/05_enterprise_expense.py`；
- [ ] 新增 `docs/enterprise-expense-demo.md`；
- [ ] example 可通过 `python examples/05_enterprise_expense.py` 运行；
- [ ] 输出 AuditReport Markdown；
- [ ] 展示全部 6 DecisionEffects；
- [ ] example 加入 CI。

## P1：AuditReport 展示增强

- [ ] 增加 degraded calls summary；
- [ ] 增加 approval-required summary；
- [ ] 增加 blocked calls summary；
- [ ] 增加 tool metadata summary；
- [ ] 增加 policy reason summary；
- [ ] 增加 trace hash。

## P2：v0.3 前置设计

- [ ] YAML Policy Engine 设计文档；
- [ ] CredentialBroker 设计文档；
- [ ] OpenTelemetry 设计文档；
- [ ] deterministic replay / resume 设计文档；
- [ ] MCP governance 设计文档。

---

## 10. 最终判断

v0.2.1 的回答是：

> 是的，主要问题已经基本解决。

具体来说：

- runtime 执行语义已经解决；
- AuditReport 默认带 Result 已解决；
- nested/event mask 已解决；
- DEGRADE fail-closed 已解决；
- Tool metadata policy 示例已解决；
- CI 已解决；
- SECURITY.md 已解决；
- PyPI 定位已解决；
- 测试数量在 PyPI 上已统一为 234；
- API Reference 主体已同步，不再有 MCP stub 冲突。

剩余问题主要是：

- API Reference 标题版本号仍旧；
- Enterprise demo 仍偏 test，public example 未完全收口；
- README / PyPI 存在过期 “coming in v0.2.0” 文案；
- Trusted Publishing 按计划 deferred，不作为当前阻断；
- Policy Engine / CredentialBroker / deterministic replay / MCP server mode 仍是后续阶段。

所以我对 v0.2.1 的评价是：

> petfishFramework 已经从“Alpha runtime skeleton”推进到“企业 PoC 可展示的 Alpha runtime framework”。接下来最应该做的不是继续堆 runtime 语义，而是把企业 demo、文档一致性和 v0.3 的 policy/credential 路线补齐。

---

## 11. 参考链接

- PyPI v0.2.1: https://pypi.org/project/petfishframework/0.2.1/
- GitHub API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- GitHub CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
- GitHub README: https://github.com/kylecui/petfishFramework/blob/master/README.md
- SECURITY.md: https://github.com/kylecui/petfishFramework/blob/master/SECURITY.md
- CI workflow: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/ci.yml
