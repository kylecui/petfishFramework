# petfishFramework — Project Agent Guide

## 项目目标

构建一个通用 AI Agent 框架，让用户能够轻松对接各种模型，并便捷地接入自己的 RAG、MCP 及其他文档或工具。

## 项目类型

code（框架开发）

## 当前阶段

前期调研 → 核心抽象 → 设计（同步测试用例）→ 开发 → QA/QC → Alpha 内测

## 工作原则

- 理解目标后再行动；大规模修改前先提方案。
- 不覆盖现有文件，除非明确确认；不删除文件，除非明确要求。
- 调研阶段：所有结论必须可追溯（evidence ledger + source）。
- 设计阶段：测试用例与设计同步产出（TDD）。
- 开发阶段：未经 QA 的代码不进入 alpha。
- 网络操作失败时至少重试两次再换方案（瞬时故障常见）。
- 不写入密钥、API key、token、密码、私钥或生产凭证。
- 不将已安装的 skill/command/agent 派生文件纳入版本控制（加入 `.gitignore`）。

## 目录地图

```text
src/        框架核心代码
tests/      测试（与设计同步，TDD）
docs/       架构文档、API 文档、开发文档
examples/   使用示例
configs/    配置模板
mcp/        MCP 集成模板
qa/         QA 检查清单
scripts/    工具脚本
outputs/    生成输出（与源码分离）
tasks/      任务与 backlog
.opencode/  AI agent 技能与配置
```

## 偏好工具

- uv — Python 项目管理
- pytest — 测试
- ruff — lint
- mypy — 类型检查（可选）
- drawio — 架构图
- MCP filesystem server — 受控项目访问

## 质量门禁

- README 清晰说明项目目标与用法。
- 存在 tasks / 路线图。
- 存在 QA 检查清单。
- 生成输出与源码分离。
- 开发项目有测试或测试计划。

## Development Gotchas

<!--
记录代码库中非代码自解释的约定、已知陷阱、关键设计约束。
规则：每条必须是"违反会导致 bug，且代码本身无法自解释"的约束；上限 10 条。
-->

## Architecture Decisions

<!-- 重大技术选型和设计决策的简要记录（一句话结论 + 指向 docs/ 下完整 ADR 的链接）。 -->

## Crystallization Triggers

经验沉淀在以下时机评估是否有新 gotcha 需记录：
- 完成架构审查并修复问题后
- 修复了"看起来不是 bug 但其实是"的问题后
- 新增模型适配器 / RAG 后端 / MCP 集成点后

---

<!-- 以下为已安装 skill pack 的路由规则（由 PEtFiSh 安装器注入，请勿手动修改） -->

<!-- BEGIN pack: opencode-skill-pack-testcases-usage-docs -->
# Test Cases & Usage Docs Skill Pack Rules

This pack provides two complementary skills: generating test cases from real project code, and generating usage documentation from real project capabilities.

## Skill Routing (强制)

### Rules

1. When the user asks to generate **test cases, test strategy, test matrix, or test plan** from a project, **MUST** route to `generate-test-cases`. Do NOT route to `generate-usage-docs`.
2. When the user asks to generate **README, Quick Start, API docs, CLI docs, FAQ, or troubleshooting guides** from a project, **MUST** route to `generate-usage-docs`. Do NOT route to `generate-test-cases`.
3. Both skills require a **project inventory step first**: run `uv run scripts/project_inventory.py .` before generating artifacts. Do not skip this step.
4. When the user asks for both tests and docs in the same request, run `generate-test-cases` and `generate-usage-docs` sequentially (inventory once, then both generation steps). Do not merge them into a single pass.
5. Both skills operate on **real project code and design docs** — do not generate generic/template artifacts without first reading the actual project.

### Conflict Resolution

- "Write tests for this project" = `generate-test-cases`.
- "Document this project" = `generate-usage-docs`.
- "Help me ship this project" (ambiguous) → ask whether the priority is test coverage or user-facing documentation, then route accordingly.
- If the user provides a design doc or spec as input, both skills can use it — but route based on the desired output type (tests vs docs).

## generate-test-cases Workflow

1. Run project inventory: `uv run scripts/project_inventory.py .`
2. Build traceability map: capabilities → test targets
3. Generate layered test artifacts:
   - Test strategy (scope, risk areas, coverage goals)
   - Test matrix (feature × scenario × priority)
   - Test cases (input, expected output, pass/fail criteria)
4. Output to `tests/` or designated output directory

## generate-usage-docs Workflow

1. Run project inventory: `uv run scripts/project_inventory.py .`
2. Identify target audience (end user / developer / operator)
3. Identify project capabilities (CLI, API, config, integrations)
4. Build doc set:
   - README (overview, install, quick start)
   - API / CLI reference
   - FAQ and troubleshooting
5. Output to `docs/` or designated output directory

## Behavioral Rules

- Always run project inventory before generating any artifact. Do not generate from assumptions.
- Test cases must be traceable to specific project capabilities identified in the inventory.
- Usage docs must reflect actual project behavior, not generic boilerplate.
- If the project inventory reveals missing or ambiguous capabilities, flag them before generating — do not silently fill gaps with invented behavior.
- Generated test cases must include: input, expected output, and pass/fail criteria. Vague test descriptions are not acceptable.
- Generated docs must include: at least one working example per capability documented.

## Output Format

**generate-test-cases** outputs:
1. Test strategy document — scope, risk areas, coverage goals
2. Test matrix — feature × scenario × priority table
3. Test case files — structured cases with input/output/criteria

**generate-usage-docs** outputs:
1. README — overview, install, quick start
2. Reference docs — API / CLI / config
3. FAQ / Troubleshooting — common issues and resolutions
<!-- END pack: opencode-skill-pack-testcases-usage-docs -->

<!-- BEGIN pack: trustskills-governance-pack -->
# Trust Skills Governance Pack Rules

This pack provides skill trust scanning, governance level assignment, and manifest generation/verification for PEtFiSh skill packs.

## Skill Routing (强制)

### Rules

1. When the user asks to **scan skills for trust, safety, or governance issues**, **MUST** route to `skill-trust-governance`.
2. When the user asks to **generate or verify a trust manifest** for a skill or pack, **MUST** route to `skill-trust-governance`.
3. When the user asks to **assign or review governance levels** (allow / allow_with_ask / sandbox_required / manual_review_required / deny) for skills, **MUST** route to `skill-trust-governance`.
4. When the user asks to **redline** a skill (flag it as requiring manual review or denial), **MUST** route to `skill-trust-governance`.
5. The entrypoint for all trust operations is: `uv run .opencode/skills/skill-trust-governance/scripts/trust_scan.py`. Do not invoke `trustskills` CLI directly without going through this entrypoint.

### Conflict Resolution

- Trust governance vs security audit: `skill-trust-governance` handles **governance classification and manifest management** (what level of trust to grant a skill). `skill-security-auditor` handles **vulnerability and risk scanning** (what security risks a skill poses). They are complementary — run security audit first, then use findings to inform governance level assignment.
- When the user asks to "check if a skill is safe to install", route to `skill-security-auditor` for risk findings, then `skill-trust-governance` for governance decision.
- When the user asks to "publish a skill", the governance manifest must be generated by `skill-trust-governance` before the `quality-gate` publish flow.

## Governance Levels

| Level | Meaning | Agent Behavior |
|---|---|---|
| `allow` | Trusted, no restrictions | Execute without prompting |
| `allow_with_ask` | Trusted but requires confirmation for sensitive actions | Prompt user before sensitive operations |
| `sandbox_required` | Must run in isolated environment | Do not execute outside sandbox |
| `manual_review_required` | Flagged for human review before use | Block execution, notify user |
| `deny` | Rejected, must not be used | Refuse to load or execute |

## trust_scan.py Modes

- **scan**: Analyze a skill directory and produce a trust report
- **manifest**: Generate a signed trust manifest for a skill
- **verify**: Verify an existing trust manifest against current skill content
- **redline**: Flag a skill at `manual_review_required` or `deny` level

## Behavioral Rules

- Never assign `allow` governance level without completing a full scan. Partial scans must result in `manual_review_required` at minimum.
- Trust manifests must be regenerated whenever skill content changes. Stale manifests are treated as `manual_review_required`.
- `deny`-level skills must not be loaded, executed, or referenced in routing rules.
- When a scan finds issues, report them with the specific governance level recommendation and the reason. Do not silently downgrade to `allow`.
- Governance decisions must be logged with: skill path, scan timestamp, findings summary, assigned level, and agent ID.

## Output Format

**scan** output:
1. Trust report — findings per skill file, risk signals detected
2. Recommended governance level with justification

**manifest** output:
1. Signed trust manifest file (saved alongside skill)
2. Manifest summary — skill path, level, timestamp, hash

**verify** output:
1. Verification result: PASS / FAIL / STALE
2. If FAIL or STALE: diff of what changed and recommended action

**redline** output:
1. Updated governance level in manifest
2. Redline reason and required remediation steps before level can be upgraded
<!-- END pack: trustskills-governance-pack -->
