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

1. **Release 版本号 grep checklist** — 每次发布前必须 grep 旧版本号。`SECURITY.md` 的 Supported Versions 表是版本敏感文件，但 `pre_release.py` 不检查它。发布前手动执行 `grep -rn "0\.[0-9]\+\.x" SECURITY.md` 确认当前版本。遗漏会导致外部安全审计认为项目维护停滞。
2. **新模块必须同步 `__init__.py` 导出** — 新增 `src/petfishframework/<module>/<sub>.py` 时，必须同时在 `<module>/__init__.py` 的 `__all__` 和 import 中添加导出。否则用户无法从包顶层导入，只能走子模块路径，违反 Python 包惯例。OTelSink/SIEMSink 在 v0.4.0 发布时遗漏了此步骤。
3. **Docker ENTRYPOINT 必须有对应的 `__main__.py`** — Dockerfile 中 `ENTRYPOINT ["python", "-m", "petfishframework"]` 要求 `src/petfishframework/__main__.py` 存在且 `main()` 返回 int 退出码。没有 `__main__.py` 时容器启动直接 crash，且 CI 不构建 Docker 所以不会发现。

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

<!-- BEGIN pack: project-initializer-skill -->
# Project Initializer Skill Pack Rules

This pack provides workspace scaffolding and initialization capabilities for AI-agent projects.

## Skill Routing (强制)

### Rules

1. When the user asks to initialize, scaffold, bootstrap, or set up a new AI-agent workspace, **MUST** route to `project-initializer`.
2. When the user asks to generate `AGENTS.md`, `README`, `.opencode/` templates, `docs/`, `tasks/`, `qa/`, or `mcp` config files, **MUST** route to `project-initializer`.
3. When the user selects or asks about a profile (minimal / course / code / ops / security / research / writing / skills-package / comprehensive), **MUST** route to `project-initializer`.
4. When the user asks to configure a `uv` dev environment for a new project, **MUST** route to `project-initializer`.
5. **Safe no-overwrite rule**: `project-initializer` must check for existing files before writing. For any file that already exists, it must ask for explicit confirmation before overwriting. Never silently overwrite.

### Conflict Resolution

- If the user asks to "update" or "modify" an existing `AGENTS.md` rather than initialize from scratch, do NOT route to `project-initializer` — handle as a direct edit task.
- If the user asks to initialize AND install packs, route initialization to `project-initializer` first, then route pack installation to `petfish-companion`.

## Profiles

| Profile | Included Templates |
|---|---|
| minimal | AGENTS.md, README |
| course | + docs/, course structure, QA/QC templates |
| code | + tasks/, .opencode/agents/, dev env |
| ops | + deploy config, runbook templates |
| security | + security policy, threat model stubs |
| research | + research/, evidence/, sources/ stubs |
| writing | + docs/, style guide stub |
| skills-package | + packs/, skill scaffold, lint config |
| comprehensive | all of the above |

## Behavioral Rules

- Always confirm the target directory and profile before writing any files.
- List all files that will be created before creating them (dry-run summary).
- For risky operations (overwrite existing files, delete, restructure), require explicit user confirmation.
- After scaffolding, output a post-init summary: files created, next steps, recommended pack installs.
- Do not create `README.md` files unless the profile explicitly includes them or the user requests them.

## Output Format

Post-init output must include:

1. **Files Created** — list of paths written
2. **Skipped / Conflicts** — files that already existed and were not overwritten
3. **Next Steps** — recommended commands (e.g., `/petfish install <pack>`, `uv sync`)
4. **Profile Summary** — what the selected profile provides
<!-- END pack: project-initializer-skill -->

<!-- BEGIN pack: doc-reader-skill -->
# Doc Reader Skill Pack Rules

This pack provides unified document-to-Markdown conversion for reading, review, and extraction.

## Skill Routing (强制)

### Rules

1. When the user wants to **read, extract text from, or convert** a non-Markdown document (PDF, DOCX, XLSX, HTML, EPUB) to Markdown, **MUST** route to `doc-reader`.
2. When the user needs **structured text content** from a document (tables, paragraphs, lists), **MUST** use `doc-reader` to convert first, then read the Markdown output.
3. For **PPTX files**: use `ppt-reader` for structural inventory (slide order, media, comments, layout), use `doc-reader` for full text extraction including tables and charts. Use both for complete PPTX understanding.
4. When the user provides a document and asks to **review, summarize, or extract key points**, use `doc-reader` for conversion, then apply `reference-document-review` for analysis. Do NOT treat conversion as analysis.

### Conflict Resolution

- "Read this PDF and summarize": route `doc-reader` (convert) → agent reads output → summarize. Conversion and analysis are separate steps.
- "Extract the tables from this DOCX": route `doc-reader` with `--json` for metadata, then read the Markdown output.
- "Read this PPTX": route `ppt-reader` first for structure, then `doc-reader` for full text if structural inventory is insufficient.
- "Convert this document to Markdown": route `doc-reader` only. No analysis needed.
- When `reference-document-review` is also installed: `doc-reader` handles conversion, `reference-document-review` handles analysis and extraction into course inputs. Do not merge these responsibilities.

## doc-reader Workflow

1. Identify input file and format (PDF, DOCX, XLSX, HTML, EPUB, etc.)
2. Run conversion:
   ```bash
   uv run scripts/doc_to_markdown.py input.pdf --output output.md
   ```
3. Read the converted Markdown output
4. Optionally extract structured metadata:
   ```bash
   uv run scripts/doc_to_markdown.py input.pdf --output output.md --json metadata.json
   ```

## Behavioral Rules

- Always convert before reading. Do NOT attempt to interpret binary file contents directly.
- Preserve the conversion output as a file when the user needs to review or cite it later. Use `--output` flag.
- For scanned PDFs, warn the user that markitdown does NOT perform OCR by default; text extraction will be minimal.
- For PPTX, always recommend `ppt-reader` for structural analysis first if structure matters (slide order, media inventory, layout issues).
- Do NOT attempt LLM-based image description through this skill. The agent can view images natively.

## Output Format

**doc-reader** outputs:
1. Markdown file — converted text content from the source document
2. (Optional) JSON metadata — `{source_file, source_ext, text_length, title_guess}`
<!-- END pack: doc-reader-skill -->

<!-- BEGIN pack: opencode-ppt-skills -->
# PPT Skills Pack Rules

This pack provides PPTX reading and writing capabilities for course slides, proposals, reports, and technical decks.

## Skill Routing (强制)

### Rules

1. When the user wants to **read, inspect, summarize, audit, or compare** a PPT/PPTX file, **MUST** route to `ppt-reader`. Do NOT route to `ppt-writer`.
2. When the user wants to **create, rewrite, restructure, update, or export** a PPT/PPTX deck, **MUST** route to `ppt-writer`. Do NOT route to `ppt-reader`.
3. When the user provides a Markdown outline, document, meeting notes, or old PPT and asks to generate a new deck, **MUST** route to `ppt-writer`.
4. When the user asks for a "rewrite brief" or "per-slide action plan" as input for a future writing task, **MUST** route to `ppt-reader` (produces the brief), then `ppt-writer` (executes it).
5. When the user asks for visual QA of a generated deck, **MUST** use `ppt-writer`'s `qa_deck.py` step — do NOT treat this as a `ppt-reader` task.

### Conflict Resolution

- "Read and then rewrite" requests: route `ppt-reader` first to produce inventory + rewrite brief, then `ppt-writer` to execute. Do not merge into a single step.
- "Summarize the slides" = `ppt-reader`. "Update the slides" = `ppt-writer`.
- When ambiguous, ask: is the primary output a **report about** the deck (`ppt-reader`) or **a new deck** (`ppt-writer`)?

## ppt-reader Workflow

1. Extract slide inventory → `pptx_inventory.json` (titles, layout, notes, comments, media, links)
2. Produce Markdown summary of structure and content
3. Flag: missing placeholders, sensitive info, broken links, layout inconsistencies
4. Optionally produce a rewrite brief / per-slide action plan for `ppt-writer`

## ppt-writer Workflow

1. Receive input: Markdown / doc / outline / old PPTX / rewrite brief
2. Build narrative structure and page plan
3. Run `build_deck.py` to generate PPTX
4. Run `qa_deck.py` to verify output
5. Fix issues found in QA
6. Re-verify until QA passes
7. Deliver final PPTX

## Behavioral Rules

- Never skip the `qa_deck.py` step after `build_deck.py`. Generate → QA → fix → re-verify is mandatory.
- `ppt-reader` output (inventory JSON + Markdown summary) must be saved before passing to `ppt-writer`.
- Template and style unification must be applied consistently across all slides in a deck.
- Do not mix reading and writing in a single tool invocation.
- LibreOffice and Poppler are optional dependencies for visual QA; if unavailable, note the limitation and proceed with structural QA only.

## Output Format

**ppt-reader** outputs:
1. `pptx_inventory.json` — structured slide inventory
2. Markdown summary — human-readable structure and content overview
3. (Optional) Rewrite brief — per-slide action plan

**ppt-writer** outputs:
1. Generated `.pptx` file
2. QA report — issues found and fixed
3. Delivery summary — slide count, template used, known limitations
<!-- END pack: opencode-ppt-skills -->
