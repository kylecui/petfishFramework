# QC Gate Decision — petfishFramework v0.1.0 Alpha

> Decision: **CONDITIONAL PASS** — 允许 Alpha 发布，附条件。
> Date: 2026-07-06
> Based on: qa/qa-review.md

## 决策

**CONDITIONAL PASS** — petfishFramework v0.1.0 满足 Alpha 内测发布条件。

## 发布条件

| # | 条件 | 状态 | 阻塞？ |
|---|---|---|---|
| C1 | 187 测试全通过 | ✅ | 否 |
| C2 | ruff lint clean | ✅ | 否 |
| C3 | LICENSE 存在 (MIT) | ✅ | 否 |
| C4 | 真实 API 验证通过 | ✅ (SiliconFlow OpenAI + Anthropic format) | 否 |
| C5 | 真实 MCP 验证通过 | ✅ (14 工具发现) | 否 |
| C6 | 无 P0 未修复 bug | ✅ (7 个全修复) | 否 |
| C7 | README + Quick Start | ✅ | 否 |
| C8 | .env 不泄露 | ✅ | 否 |

## 附带条件（Alpha 期间必须完成）

| # | 条件 | 期限 | 当前状态 |
|---|---|---|---|
| A1 | 找到第一个真实用户 | Alpha 后 2 周内 | 待执行 |
| A2 | CI/CD GitHub Actions | 发布前 | 待执行 |
| A3 | 多模型验证（GPT-4o 或 Claude） | Alpha 后 1 月内 | 待执行（需 API key） |

## 已接受的风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 单模型验证 | 模型无关性未充分证明 | adapter 通过 mock 测试 + SiliconFlow 双 format 验证 |
| benchmark 样本量小 | 结论为方向性 | 多次重复一致；扩大样本需更快 API |
| 无真实用户反馈 | 未知使用模式 | Alpha 内测目标就是获取反馈 |

## 版本号决策

**v0.1.0a1** (Alpha 1)：
- `a1` 后缀明确标识预发布状态
- PyPI 标记为 prerelease
- README 标注 "Alpha — API may change"

## 发布后行动计划

1. PyPI 发布 (`uv build && twine upload`)
2. 观察 Alpha 用户反馈
3. 根据 feedback 决定 v0.1.0 正式版或 v0.2.0
