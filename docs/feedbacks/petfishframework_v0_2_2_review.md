# petfishFramework v0.2.2 Review：5 个 Todo 修复核验

> 版本：`petfishframework==0.2.2`  
> 发布页：https://pypi.org/project/petfishframework/0.2.2/  
> 本次核验目标：检查 v0.2.1 后遗留的 5 个主要问题是否已解决。  
> 备注：本次主要基于 PyPI 页面与 GitHub 公开文件核验；我的本地 pip index 暂时未能解析到 `0.2.2`，因此没有完成完整本地 playground 安装实测。

---

## 1. 总体结论

v0.2.2 基本完成了 v0.2.1 后提出的 5 个 todo。

可以认为：

> petfishFramework v0.2.2 已经完成“企业 PoC 可展示 Alpha runtime”的关键文档与示例收口。

具体来说：

- PyPI 页面已显示 `0.2.2`，短描述是 runtime framework 定位；
- PyPI 页面显示 Tests 为 234，Development 段落也同步为 `uv run pytest # 234 tests`；
- PyPI 页面 Enterprise PoC 段落已经删除 “coming in v0.2.0”；
- GitHub README 页面显示 Tests: 234；
- GitHub examples 目录中已经存在 `05_enterprise_expense.py`；
- GitHub 中 `examples/05_enterprise_expense.py` 页面显示 278 lines / 233 loc；
- `docs/enterprise-expense-demo.md` 已存在，并描述 5 个场景、6 种 DecisionEffect 以及 AuditReport 输出；
- PyPI 当前限制仍明确标记为 Alpha，deterministic rerun / resume 与 MCP server mode 仍 planned，这个边界是合理的。

但仍有一个需要复核的小尾巴：

> 我抓取到的 raw `docs/api.md` 第一行仍显示 `v0.1.9`。这可能是缓存、raw 视图、分支同步或发布顺序问题；但如果外部用户也看到这个版本号，会继续造成文档一致性问题。

因此，我的最终判断是：

> 5 个 todo 中，4 个已经明确解决；`api.md` 标题修复在我的抓取结果中仍有不确定性，建议再确认 raw 文件头是否已经真正变成 v0.2.2。

---

## 2. 5 个 Todo 逐项核验

| Todo | 预期修复 | 核验结果 | 判断 |
|---|---|---:|---|
| `api.md` 标题 v0.1.9 | 改为 v0.2.2 | 我抓取到的 raw `docs/api.md` 第一行仍显示 v0.1.9 | ⚠️ 需复核 |
| README “coming in v0.2.0” | 删除，改为直接链接 | GitHub README 页面未找到 “coming in”，PyPI 页面也已直接给出运行命令 | ✅ 解决 |
| README badge URL tests-213 | 改为 tests-234 | GitHub README 页面显示 Tests: 234，PyPI 页面也显示 Tests: 234 | ✅ 解决 |
| `examples/05_enterprise_expense.py` 不存在 | 创建可运行示例 | examples 目录列出 `05_enterprise_expense.py`，文件页面显示 278 lines / 233 loc | ✅ 解决 |
| 缺 demo 文档 | 新增 `docs/enterprise-expense-demo.md` | 文档存在，包含场景、策略、输出说明 | ✅ 解决 |

---

## 3. PyPI v0.2.2 状态

PyPI v0.2.2 页面显示：

| 项目 | 状态 |
|---|---|
| 版本 | `0.2.2` |
| 发布时间 | 2026-07-07 |
| 短描述 | `A lightweight runtime framework for reliable, auditable, budget-aware, and permission-aware AI agents.` |
| Python 要求 | `>=3.10` |
| Development Status | Alpha |
| Tests | 234 |
| Enterprise PoC | 已直接链接 `examples/05_enterprise_expense.py` 和 `tests/test_enterprise_demo.py` |
| 当前限制 | deterministic rerun / resume planned；MCP server mode planned |
| Trusted Publishing | No，但此前已说明 deferred |

PyPI 页面中 Enterprise PoC 段落已经写为：

```text
See examples/05_enterprise_expense.py and tests/test_enterprise_demo.py
for a complete enterprise expense approval scenario demonstrating all 6 DecisionEffects.

Run: python examples/05_enterprise_expense.py
```

这说明 PyPI 层面已经完成了你列出的 README / demo 文案收口。

---

## 4. GitHub README 状态

GitHub README 页面显示：

- Tests badge 文案为 `Tests: 234`；
- 没有找到 `coming in`；
- Enterprise PoC 段落已经直接写 `examples/05_enterprise_expense.py`；
- 运行命令已给出：

```bash
python examples/05_enterprise_expense.py
```

这说明 README 页面层面已经解决了 v0.2.1 的主要文档尾巴。

注意：我在一次 raw README 抓取中看到过旧的 `tests-213` 与 `coming in` 内容，但 GitHub 页面视图和 PyPI 页面均已更新。更可能是 raw 抓取缓存或工具视图不一致。建议后续 release checklist 仍加入 raw 文件 grep，避免这种不确定性。

---

## 5. Enterprise Example 状态

GitHub examples 目录已经列出：

```text
05_enterprise_expense.py
```

并且文件页面显示：

```text
278 lines / 233 loc / 9.86 KB
```

这说明 v0.2.1 时“企业 demo 仍偏 test、public example 未完全收口”的问题已经解决。

当前状态可以说：

> Enterprise Expense Approval demo 已经从 test asset 变成 public runnable example。

---

## 6. Enterprise Demo 文档状态

`docs/enterprise-expense-demo.md` 已存在，并覆盖：

- Demo 目标：展示 petfishFramework 是 runtime control framework，不是 calculator framework；
- 运行方式：

```bash
python examples/05_enterprise_expense.py
```

- 5 个场景：
  1. ALLOW + PARTIAL_ALLOW；
  2. MASK；
  3. REQUIRE_APPROVAL；
  4. DENY；
  5. DEGRADE with fallback；
- AuditReport 输出；
- Policy Design 表格；
- 文件说明：`examples/05_enterprise_expense.py` 与 `tests/test_enterprise_demo.py`。

这已经满足一个 PoC demo 文档的基本要求。

---

## 7. 仍需确认：api.md 标题

你列出的第一个修复项是：

```text
api.md 标题 v0.1.9 → v0.2.2
```

但我抓到的 raw `docs/api.md` 第一行仍然是：

```text
public API of petfishFramework v0.1.9
```

由于 PyPI 和 GitHub 页面其它部分都已经同步到 v0.2.2 状态，这里可能有几种解释：

1. raw 文件缓存；
2. branch / release tag 与 master 不一致；
3. api.md 标题没有真正更新；
4. 文档生成过程生成到了 PyPI，但没有同步到 GitHub raw；
5. 工具抓取到了旧内容。

建议你直接在仓库里执行：

```bash
grep -n "v0.1.9\|v0.2.2" docs/api.md
```

如果仍看到 v0.1.9，建议立即改掉。

如果本地已经是 v0.2.2，则建议：

```bash
git status
git log -1 -- docs/api.md
git push
```

并确认 GitHub raw 页面刷新。

---

## 8. 当前成熟度判断

v0.2.2 后，petfishFramework 可以更明确地定位为：

> 企业 PoC 可展示的 Alpha-stage Agent runtime control framework。

当前已经具备：

- runtime framework 定位；
- Quickstart；
- 234 tests；
- 6 种 DecisionEffect 核心执行语义；
- Budget hard limit；
- Audit replay；
- structured AuditReport；
- input/output/event/nested mask；
- DEGRADE fallback + fail-closed；
- Tool metadata；
- CI / SECURITY.md 基础；
- Enterprise Expense Approval public example；
- Enterprise demo 文档。

仍不应称为 production-ready，因为：

- YAML Policy Engine 尚未实现；
- CredentialBroker 尚未实现；
- deterministic rerun / resume 仍 planned；
- MCP server mode 仍 planned；
- Trusted Publishing / SBOM / release provenance deferred；
- OpenTelemetry / SIEM / deployment hardening 尚未闭环。

---

## 9. 下一步建议

## 9.1 v0.2.3：最后的文档一致性补丁

建议只做一件事：

- 确认 `docs/api.md` raw 文件头已经是 v0.2.2 / v0.2.3；
- release checklist 中加入：

```bash
grep -R "v0.1" README.md docs/ pyproject.toml
grep -R "coming in" README.md docs/ examples/
grep -R "tests-213" README.md docs/
```

目标：

> 彻底消灭文档旧版本残留。

---

## 9.2 v0.3.0：Policy Engine + CredentialBroker

v0.2.x 的 runtime 与 demo 已经基本收口，v0.3.0 建议进入：

1. YAML Policy Engine；
2. policy versioning；
3. policy test harness；
4. CredentialBroker MVP；
5. scoped temporary credentials；
6. secret/event redaction；
7. policy audit metadata；
8. policy examples for enterprise demo。

---

## 9.3 v0.4.0：Production Hardening

后续生产化建议继续推进：

- deterministic rerun；
- checkpoint resume；
- OpenTelemetry；
- SIEM export；
- MCP server mode；
- MCP governance；
- Trusted Publishing；
- SBOM；
- signed release；
- deployment guide；
- threat model。

---

## 10. 最终判断

v0.2.2 的回答是：

> 主要问题已经基本解决。

更精确地说：

- README 过期文案：解决；
- tests badge：解决；
- enterprise example：解决；
- enterprise demo docs：解决；
- PyPI 文档：解决；
- API Reference 主体：大概率已解决，但 raw 文件标题仍需你再确认。

现在 petfishFramework 的短期工作重点可以从“修文档尾巴”切换到：

> v0.3 的 Policy Engine 与 CredentialBroker 设计。

我建议在进入 v0.3 前，只再做一个极小的 v0.2.3 文档一致性补丁，确保 `api.md` raw 版本号与所有 release 文案完全同步。

---

## 11. 参考链接

- PyPI v0.2.2: https://pypi.org/project/petfishframework/0.2.2/
- GitHub API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- GitHub README: https://github.com/kylecui/petfishFramework/blob/master/README.md
- Examples directory: https://github.com/kylecui/petfishFramework/tree/master/examples
- Enterprise example: https://github.com/kylecui/petfishFramework/blob/master/examples/05_enterprise_expense.py
- Enterprise demo docs: https://github.com/kylecui/petfishFramework/blob/master/docs/enterprise-expense-demo.md
