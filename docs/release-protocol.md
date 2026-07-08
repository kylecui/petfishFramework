# petfishFramework — 强制发布协议

> 这不是建议清单。这是**每次发布必须执行的门禁脚本**。
> 不执行完不能打 tag。不执行完不能 push。

## 自动化脚本：`scripts/pre_release.py`

**每次发布前运行**：`python scripts/pre_release.py 0.3.4`

脚本自动检查：

1. **版本号一致性**（6 处）：
   - pyproject.toml version
   - __init__.py __version__
   - api.md 标题版本号
   - README badge URL 数字
   - README badge 文本数字
   - CHANGELOG 最新条目版本号

2. **文档完整性**：
   - grep 新增模块名在 api.md 中是否存在
   - grep CHANGELOG 中是否有当前版本条目
   - README roadmap "current" 是否指向当前版本

3. **测试 + lint**：
   - pytest 全通过
   - ruff check 通过

4. **API 闭合检查**（人工确认）：
   - 新功能是否在 Agent 或 Session 上有用户面参数？
   - 新功能是否有 api.md 章节？
   - 新功能是否有 CHANGELOG 条目？

退出码 0 = 可以发布；非 0 = 必须修复。

## 发布 SOP（严格顺序）

```
1. python scripts/pre_release.py <version>
   ↓ (必须 exit 0)
2. uv run pytest tests/ -q
   ↓ (必须全通过)
3. uv run ruff check src/ tests/ examples/
   ↓ (必须 All checks passed)
4. git add -A && git commit -m "release: v<version>"
5. git push origin master
6. git tag v<version>     # 必须有 v 前缀！
7. git push origin v<version>
8. 等待 CI + Publish 双绿
9. 验证 https://pypi.org/project/petfishframework/<version>/
```

## 版本号同步检查表（每次必查）

| 位置 | 检查命令 | 预期 |
|---|---|---|
| pyproject.toml | `grep "^version" pyproject.toml` | `version = "X.Y.Z"` |
| __init__.py | `grep "__version__" src/petfishframework/__init__.py` | `__version__ = "X.Y.Z"` |
| api.md 标题 | `head -3 docs/api.md` | `vX.Y.Z` |
| README badge URL | `grep "badge/tests" README.md` | URL 含正确测试数 |
| README badge 文本 | `grep "Tests:" README.md` | 文本含正确测试数 |
| CHANGELOG | `head -10 CHANGELOG.md` | `## [X.Y.Z]` 在顶部 |

## 新功能检查表（每次加功能必查）

| 检查项 | 命令 | 预期 |
|---|---|---|
| Agent 参数 | 新功能是否在 `Agent.__init__` 有对应参数？ | 用户能一行配置 |
| Session 传递 | Agent 参数是否传到 Session → Environment？ | 全链路通 |
| api.md 章节 | `grep "<新类名>" docs/api.md` | 有匹配 |
| CHANGELOG 条目 | `grep "<版本号>" CHANGELOG.md` | 有条目 |
| TDD 测试 | `pytest tests/test_<新功能>.py` | 通过 |
| 安全边界 | 负面测试：无配置时是否安全降级？ | 不崩溃 |

## 绝不再犯的错误清单

| # | 错误 | 防止机制 |
|---|---|---|
| 1 | 忘记更新 api.md 版本号 | pre_release.py 自动检查 |
| 2 | Badge URL 和文本不一致 | pre_release.py 自动检查 |
| 3 | CHANGELOG 缺当前版本条目 | pre_release.py 自动检查 |
| 4 | 功能只在内部 hook，Agent 无入口 | 新功能检查表：Agent 参数 |
| 5 | 安全语义只在正常路径验证 | TDD 必须包含 known-bad（side-effect tracking） |
| 6 | tag 无 v 前缀 | 发布 SOP 第 6 步明确 v 前缀 |
| 7 | 新功能无 api.md 章节 | 新功能检查表 |
| 8 | 使用 twine/token | 已撤销；Trusted Publishing only |
