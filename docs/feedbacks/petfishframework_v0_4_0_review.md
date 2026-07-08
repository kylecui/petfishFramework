# petfishFramework v0.4.0 Review 与验证反馈

> 版本：`petfishframework==0.4.0`  
> 发布页：https://pypi.org/project/petfishframework/0.4.0/  
> 本次重点：验证 v0.4.0 的 production hardening 方向，包括 deterministic replay/resume、OpenTelemetry/SIEM、Vault adapter、deployment docs、Trusted Publishing、CI/Publish、Credential event hygiene、YAML Policy Engine、runtime 主链路。

---

## 1. 总体结论

v0.4.0 是一个明显的 production-hardening 版本。

如果说 v0.3.x 的核心是：

> YAML Policy Engine + CredentialBroker + Trusted Publishing。

那么 v0.4.0 的核心是：

> 继续补生产化外围能力：deterministic replay / resume、OpenTelemetry / SIEM observability、Vault adapter、Docker / deployment guide、threat model、retry / timeout 等。

本次验证结论：

> petfishFramework v0.4.0 已经从“企业 PoC 可展示 Alpha runtime”进一步推进到“生产化能力开始成体系的 Alpha runtime framework”。

但仍不建议称为 production-ready，因为仍有这些问题：

1. `CHANGELOG.md` 抓取结果仍几乎为空，release history 不透明；
2. `README.md` / `docs/api.md` raw 文件在抓取视图中显示为压缩单行，影响阅读体验与 diff 审查；
3. `SECURITY.md` 的 Supported Versions 仍写 `0.2.x` active development，未同步到 `0.4.x`；
4. `observability.__init__` 没有导出 `OTelSink` / `SIEMSink`，用户需要从子模块导入；
5. `SIEMSink` 当前主要 redacts credential token，不会自动 redact 任意 `api_key` / `secret` 字段，需要文档中明确；
6. MCP server mode 仍 planned；
7. 仍未达到 v1.0 所需的完整 deployment / monitoring / incident / compatibility / benchmark 体系。

---

## 2. PyPI 与发布状态

PyPI v0.4.0 页面显示：

| 项目 | 状态 |
|---|---|
| 版本 | `0.4.0` |
| 发布时间 | 2026-07-08 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| Tests | 300 |
| Provides-Extra | `openai`, `anthropic`, `mcp`, `otel`, `vault` |
| Trusted Publishing | Yes |
| Provenance / attestation | Yes |
| Wheel / sdist | 已发布 |
| Roadmap | `v0.4.x (current): Production hardening, deployment guides, Vault adapter, Docker, threat model ✅` |

PyPI 文件详情显示：

- `petfishframework-0.4.0.tar.gz` 使用 Trusted Publishing；
- `petfishframework-0.4.0-py3-none-any.whl` 使用 Trusted Publishing；
- 两者均有 provenance / attestation；
- provenance 指向 GitHub `publish.yml`、tag `refs/tags/v0.4.0`、commit `e30882b...`。

这是一个重要正向信号：供应链可信发布链路继续保持。

---

## 3. Playground 本地实测摘要

## 3.1 安装与版本

测试命令：

```bash
python3 -m venv /tmp/pf040
source /tmp/pf040/bin/activate
pip install petfishframework==0.4.0
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.4.0
```

---

## 3.2 核心功能实测结果

| 测试项 | v0.4.0 实测结果 | 判断 |
|---|---:|---|
| 安装 / import / version | 通过，显示 `0.4.0` | 正常 |
| Zero-cost quickstart | 通过，输出 `391` | 稳定 |
| `FakeModel + ReAct + Calculator` | 通过 | 核心链路稳定 |
| Budget hard limit | 继续可用 | 稳定 |
| AuditReport 默认带 Result | 通过 | 稳定 |
| CredentialBroker Agent API | 通过 | 稳定 |
| Credential token event redaction | 通过，event 中是 redacted dict，不是 `ScopedToken` 对象 | 正确 |
| YAML Policy Engine | 通过，高级 matcher 与 combinator 可用 | 进步明显 |
| RecordingEnvironment | 通过 | 可记录 model/tool calls |
| ReplayEnvironment | 通过 | 可用录制响应 replay |
| RerunEnvironment | 通过 | 可比较 live rerun divergence |
| RetryPolicy / with_retry | 通过 | 可重试 |
| TimeoutPolicy / with_timeout | 通过 | 可超时中断 |
| SIEMSink | 通过，可输出 JSONL | 可用但 redaction 范围有限 |
| OTelSink | 通过，无 opentelemetry 时 no-op + warning | 可用 |
| VaultCredentialSource | 模块存在，`vault` extra 声明 `hvac` | 需真实 Vault 才能集成测试 |
| Dockerfile | 存在 | 部署能力开始补齐 |
| docker-compose.yml | 存在 | 部署能力开始补齐 |
| Deployment Guide | 存在 | 有基础部署文档 |
| Threat Model | PyPI roadmap 声称已加入，但本次 raw 抓取遇到 429，未完整核验 | 需复核 |

---

## 4. v0.4.0 的关键进步

## 4.1 deterministic replay / rerun / resume 从 planned 推进到 available

PyPI v0.4.0 Current Limitations 中已将：

```text
Session replay / deterministic rerun / resume ✅ Available
```

标为 available。

代码层面已经存在：

- `RecordingEnvironment`
- `ReplayEnvironment`
- `RerunEnvironment`
- `ResumableEnvironment`
- `Session.checkpoint()`
- `Session.resume_from(...)`

本地实测：

```text
RecordingEnvironment:
  model_responses = 1
  tool_calls = 1

ReplayEnvironment:
  可返回录制的 model response 和 tool result

RerunEnvironment:
  matches=True
  divergences=[]
```

这说明 v0.4.0 不再只是 `session.replay()` 返回 event log，而是已经有更完整的 replay / rerun / resume 基础设施。

### 当前边界

`Session.replay()` 本身仍主要返回 event log；完整 deterministic replay / rerun / resume 需要使用 `RecordingEnvironment` / `ReplayEnvironment` / `RerunEnvironment` / `ResumableEnvironment` 这些较底层 API。

建议文档中明确：

> Event audit replay is exposed via `session.replay()`. Deterministic replay/rerun/resume is available through the `reliability.replay` environment wrappers.

---

## 4.2 OpenTelemetry / SIEM observability 已出现

v0.4.0 新增 extras：

```text
otel
vault
```

PyPI Current Limitations 中也写：

```text
OpenTelemetry + SIEM observability ✅ Available
```

代码层面存在：

- `petfishframework.observability.otel_sink.OTelSink`
- `petfishframework.observability.siem_sink.SIEMSink`
- `petfishframework.observability.sinks.ListSink`
- `petfishframework.observability.sinks.ConsoleSink`

本地实测：

- `SIEMSink(output_path=...)` 可写 JSONL；
- `OTelSink()` 在未安装 `opentelemetry` 时会 no-op，并给 warning；
- `ListSink` / `ConsoleSink` 使用 `__call__(event)` 作为 sink 接口。

### 当前边界

`petfishframework.observability.__init__` 当前只导出：

```python
ConsoleSink
ListSink
```

没有直接导出：

```python
OTelSink
SIEMSink
```

用户需要写：

```python
from petfishframework.observability.otel_sink import OTelSink
from petfishframework.observability.siem_sink import SIEMSink
```

建议后续在 `observability/__init__.py` 中导出 `OTelSink` / `SIEMSink`，或在文档中明确导入路径。

---

## 4.3 SIEMSink 可用，但 redaction 范围需要说清楚

本地测试：

```python
sink = SIEMSink(output_path="siem.jsonl")
sink(Event("tool.called", 123.0, {
    "tool_name": "x",
    "_credential_token": {"credential_ref": "abc", "redacted": True},
    "api_key": "SECRET",
}))
```

输出 JSONL 中：

- `_credential_token` 会被标记为 redacted；
- `redacted_fields` 包含 `_credential_token`；
- 但普通字段 `api_key: SECRET` 没有自动 redact。

这意味着：

> SIEMSink 当前主要处理 credential token redaction，不是通用 secret/PII redaction engine。

这不是 bug，但必须写清楚。否则用户可能误以为所有 `api_key` / `secret` 字段都会自动脱敏。

建议 v0.4.1 增加：

```python
SIEMSink(redact_keys=("api_key", "secret", "password", "token"))
```

或复用 `event_mask_fields` 策略结果。

---

## 4.4 Vault adapter 已加入

v0.4.0 metadata 中 `Provides-Extra` 已包含：

```text
vault
```

并且依赖中有：

```text
hvac>=1.0; extra == 'vault'
```

代码层面存在：

```python
from petfishframework.credentials.vault_adapter import VaultCredentialSource
```

`CredentialBroker` 也已有：

```python
register_credential_from_vault(name, vault_source, path)
```

这说明 Vault integration 已经进入代码层。

当前仍需真实 Vault server 才能做完整集成验证。本次只验证了模块、API 和 optional dependency 声明。

---

## 4.5 YAML Policy Engine 继续增强

v0.3.0 时 YAML matcher 还比较窄。v0.4.0 中，条件系统已经明显增强。

代码中可见支持：

- `action.tool_name`
- `subject.role_in`
- `subject.role_not_in`
- `action.args.amount_gt`
- `action.args.amount_lt`
- `action.args.amount_eq`
- `action.args.amount_gte`
- `action.args.amount_lte`
- `subject.role_count_gte`
- `subject.clearance_eq`
- `subject.tenant_id_eq`
- `resource.classification_eq`
- `resource.tags_contains`
- `tool.risk_level_eq`
- `tool.capabilities_contains`
- `tool.requires_credentials`
- `tool.side_effect`
- `tool.external_egress`
- `context.session_risk_gt`
- `context.prompt_risk_gt`
- generic `action.args.<field>_eq`
- combinators: `any`, `all`, `not`

本地实测：

```yaml
all:
  - subject.tenant_id_eq: acme
  - resource.classification_eq: secret
  - not:
      subject.clearance_eq: secret
```

可以正确返回 `DENY`。

也测试了：

```yaml
any:
  - tool.risk_level_eq: high
  - tool.requires_credentials: true
```

可以正确返回 `REQUIRE_APPROVAL`。

这说明 YAML Policy Engine 已经从 A1 进入更可用的 A2/A3 状态。

---

## 4.6 Docker / deployment guide 已出现

GitHub raw 文件中可见：

- `Dockerfile`
- `docker-compose.yml`
- `docs/deployment.md`

Deployment Guide 覆盖：

- Docker build / run；
- Docker Compose；
- 环境变量；
- volume mounts；
- credential and secret handling；
- Vault integration；
- security notes；
- health check；
- link to threat model / API reference。

这是生产化方向的重要补齐。

### 当前边界

当前 Dockerfile / docker-compose 在 raw 抓取中显示为单行，虽然内容存在，但可读性差。

此外，Dockerfile 使用：

```dockerfile
ENTRYPOINT ["python", "-m", "petfishframework"]
```

需要确认 package 是否有可用 `__main__.py` 或 CLI entry，否则容器启动可能失败。本次没有实际 docker build / run，因此这里应作为待验证项。

---

## 5. 发布与 CI 状态

v0.4.0 的 PyPI 文件详情显示：

- sdist 与 wheel 都使用 Trusted Publishing；
- provenance 指向 GitHub `publish.yml`；
- tag 是 `refs/tags/v0.4.0`；
- source repository 是 public；
- token issuer 是 GitHub OIDC；
- runner environment 是 github-hosted。

CI workflow 继续保持：

- Python 3.10 / 3.11 / 3.12 matrix；
- `uv sync --all-extras`；
- `ruff check src/ tests/`；
- `pytest tests/`；
- integration tests 在没有 API key 时跳过。

Publish workflow 继续保持：

- tag `v*` 触发；
- build job 先测试和 lint；
- `uv build`；
- publish job 使用 OIDC / Trusted Publishing；
- 不使用 API token / password。

发布可信度继续保持良好。

---

## 6. 当前发现的问题

## 6.1 CHANGELOG.md 基本不可用

本次抓取到的 `CHANGELOG.md` 只有：

```text
# Changelog All notable changes to petfishFramework will be documented in this file.
```

这意味着外部用户无法从 CHANGELOG 看到：

- v0.3.1；
- v0.3.2；
- v0.3.3；
- v0.4.0；
- 新增了什么；
- 修了什么；
- breaking changes；
- migration notes。

对一个快速迭代的框架来说，这是当前最影响可信度的问题之一。

建议 v0.4.1 必须补 CHANGELOG，至少包括：

- v0.3.0: YAML Policy + CredentialBroker；
- v0.3.2: credential event redaction + Agent credential_broker API；
- v0.4.0: deterministic replay/resume, OTel/SIEM, Vault adapter, Docker/deployment/threat model, retry/timeout；
- known limitations；
- migration notes。

---

## 6.2 SECURITY.md 版本仍旧

`SECURITY.md` 的 Supported Versions 仍写：

```text
0.2.x ✅ Active development
< 0.2 ❌ Not supported
```

但当前已经是 v0.4.0。

建议改为：

```text
0.4.x ✅ Active development
0.3.x ⚠️ Security fixes only
< 0.3 ❌ Not supported
```

或者：

```text
Latest minor ✅ Active development
Previous minor ⚠️ Security fixes only
Older ❌ Not supported
```

---

## 6.3 README / API / deployment docs raw 格式压缩为单行

本次 web 抓取中：

- README.md 总行数显示 11；
- docs/api.md 总行数显示 83；
- Dockerfile / docker-compose 显示为单行；
- docs/deployment.md 内容也呈现大量单行压缩。

如果仓库中实际文件也是这种压缩格式，会造成：

- diff 难读；
- review 难做；
- blame 难看；
- markdown 可维护性差；
- 外部贡献者体验差。

建议恢复正常换行格式。

---

## 6.4 OTelSink / SIEMSink 未从 observability 包顶层导出

当前：

```python
from petfishframework.observability import OTelSink
```

失败。

必须写：

```python
from petfishframework.observability.otel_sink import OTelSink
from petfishframework.observability.siem_sink import SIEMSink
```

建议 v0.4.1 在 `observability/__init__.py` 中导出：

```python
from .otel_sink import OTelSink
from .siem_sink import SIEMSink
```

并更新 `__all__`。

---

## 6.5 SIEM redaction 范围有限

当前 `SIEMSink` 会处理：

- `_credential_token`
- `ScopedToken`

但不会自动处理任意：

- `api_key`
- `password`
- `secret`
- `token`
- `authorization`
- `cookie`

建议下一版增加：

```python
SIEMSink(redact_keys=("api_key", "secret", "password", "token", "authorization"))
```

并支持 nested key matching。

---

## 6.6 Docker entrypoint 需要实际验证

Dockerfile 使用：

```dockerfile
ENTRYPOINT ["python", "-m", "petfishframework"]
```

需要确认包中有可执行 `petfishframework.__main__`。

本地 wheel 文件中未看到明显 `__main__.py`，因此这个 Docker entrypoint 可能需要验证。

建议 v0.4.1 CI 加：

```bash
docker build -t petfishframework .
docker run --rm petfishframework
```

或者将 Dockerfile 改为运行 example：

```dockerfile
CMD ["python", "examples/05_enterprise_expense.py"]
```

---

## 7. 当前成熟度判断

## 7.1 可以说什么

可以说：

> petfishFramework v0.4.0 is an Alpha-stage runtime control framework with YAML policies, credential brokering, deterministic replay/rerun/resume infrastructure, OpenTelemetry/SIEM sinks, Vault adapter, Docker/deployment docs, CI, and Trusted Publishing.

可以说：

> v0.4.0 is suitable for controlled enterprise PoC, security architecture evaluation, and early production-hardening experiments.

可以说：

> v0.4.0 significantly improves production-readiness scaffolding, but remains Alpha.

---

## 7.2 不应说什么

仍不建议说：

- production-ready；
- fully enterprise-grade；
- complete observability platform；
- complete SIEM redaction；
- complete Vault-based secret lifecycle；
- complete MCP server support；
- deployment-hardened for production；
- benchmark-proven superior to mainstream frameworks；
- v1 API stable。

---

## 7.3 推荐定位

中文：

> petfishFramework v0.4.0 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备完整的核心权限语义、YAML 策略、凭据代理、审计报告、deterministic replay/rerun/resume 基础、OpenTelemetry/SIEM 观测接口、Vault adapter、Docker/deployment 文档与可信发布链路，适合受控企业 PoC 和生产化前架构验证，但仍需继续完善文档格式、CHANGELOG、SIEM 脱敏、部署验证和 v1 API 稳定性。

英文：

> petfishFramework v0.4.0 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, now with production-hardening scaffolding including deterministic replay/rerun/resume, OTel/SIEM sinks, Vault adapter, Docker deployment docs, CI, and Trusted Publishing.

---

## 8. 五顾问评判

## 8.1 反对者

v0.4.0 仍不是生产级。

主要问题：

1. CHANGELOG 几乎为空；
2. SECURITY.md supported versions 过期；
3. 文档 raw 格式压缩，不利于维护；
4. SIEMSink 不会自动 redact 常见 secret 字段；
5. OTel/SIEM 没有从 observability 顶层导出；
6. Docker entrypoint 需要实际验证；
7. MCP server mode 仍 planned；
8. 仍缺 deployment/observability 的真实端到端验证。

结论：

> v0.4.0 生产化 scaffolding 已经出现，但 production-ready 还差一层 hardening 与验证。

---

## 8.2 本质思考者

v0.4.0 的本质变化是：

> petfishFramework 开始从“安全 runtime 框架”走向“可部署、可观测、可复盘、可接企业基础设施”的方向。

此前的核心是工具调用仲裁，现在开始覆盖：

- replay；
- observability；
- Vault；
- deployment；
- threat model；
- retry/timeout；
- publish provenance。

这是从 framework prototype 向 enterprise infrastructure 的必要过渡。

---

## 8.3 机会挖掘者

v0.4.0 已经可以支持更完整的企业安全叙事：

```text
Agent 执行
  -> YAML policy 决策
  -> CredentialBroker 发 scoped token
  -> RuntimeEnvironment 仲裁
  -> DecisionEffect 控制动作
  -> AuditReport 生成审计
  -> Replay/Rerun 支持复盘
  -> SIEM/OTel 接入监控
  -> Vault adapter 接入凭据系统
  -> Docker/deployment guide 支持 PoC 部署
  -> Trusted Publishing 保证发布可信
```

这已经非常接近“AI Agent runtime control infrastructure”的叙事。

---

## 8.4 局外人

外部用户会看到 PyPI 页面很强：

- 300 tests；
- Trusted Publishing；
- OTel / SIEM；
- Vault；
- deterministic replay/resume；
- Docker/deployment；
- Alpha 边界写得清楚。

但他点进 GitHub raw 文件后，会遇到：

- CHANGELOG 空；
- SECURITY 版本旧；
- 文档单行压缩；
- Dockerfile 可读性差；
- observability 入口不直观。

这些不是核心架构问题，但会影响专业可信度。

---

## 8.5 执行者

v0.4.1 不建议继续加大功能。

建议只做 6 件事：

1. 补完整 CHANGELOG；
2. 修 SECURITY.md supported versions；
3. 格式化 README / docs / Dockerfile / docker-compose；
4. 导出 OTelSink / SIEMSink；
5. 增强 SIEMSink secret redaction；
6. CI 加 Docker build/run smoke test。

---

## 9. v0.4.1 建议清单

## P0：Release Hygiene

- [ ] 补 CHANGELOG；
- [ ] 更新 SECURITY.md supported versions；
- [ ] README / docs 恢复正常换行；
- [ ] Dockerfile / docker-compose 恢复正常格式；
- [ ] 确认 PyPI long_description 与 README 同源生成；
- [ ] release checklist 加 grep 过期版本号。

## P0：Observability API

- [ ] `observability.__init__` 导出 `OTelSink`；
- [ ] `observability.__init__` 导出 `SIEMSink`；
- [ ] README 增加 OTel / SIEM 最小示例；
- [ ] API Reference 增加 observability sink 用法。

## P1：SIEM redaction

- [ ] `SIEMSink(redact_keys=...)`；
- [ ] 默认 redact `api_key`, `secret`, `password`, `token`, `authorization`, `cookie`；
- [ ] 支持 nested key；
- [ ] 输出 `redacted_fields`；
- [ ] 增加测试。

## P1：Docker smoke

- [ ] CI build Docker image；
- [ ] CI run container；
- [ ] 确认 `python -m petfishframework` 可执行；
- [ ] 或调整 Docker entrypoint；
- [ ] docs/deployment.md 与实际 Docker 行为一致。

## P2：Replay docs

- [ ] 明确 `session.replay()` 是 event log；
- [ ] 明确 deterministic replay/rerun/resume 使用 environment wrappers；
- [ ] 增加最小 replay/rerun/resume 示例；
- [ ] 增加 divergence 输出示例。

## P2：Vault docs

- [ ] 增加 Vault local dev 示例；
- [ ] 增加 `register_credential_from_vault` 用法；
- [ ] 增加 Vault failure mode；
- [ ] 增加 cache / rotation / revocation caveats。

---

## 10. 最终判断

v0.4.0 的回答是：

> 是的，生产化路线明显推进，而且不是空声明。Trusted Publishing、300 tests、deterministic replay/rerun/resume infrastructure、OTel/SIEM、Vault adapter、Docker/deployment docs 都已经进入公开发布物或代码路径。

但还要保持边界：

> v0.4.0 是 production-hardening Alpha，不是 production-ready。

当前最值得肯定的是：

- runtime 主链路稳定；
- DecisionEffect 语义持续正确；
- Credential event redaction 仍正确；
- YAML Policy Engine 明显增强；
- replay/rerun/resume 进入代码层；
- OTel/SIEM 进入代码层；
- Vault adapter 进入代码层；
- Trusted Publishing 和 provenance 保持；
- Docker / deployment guide 已出现。

当前最值得修的是：

- CHANGELOG；
- SECURITY.md 版本；
- 文档格式；
- observability exports；
- SIEM redaction；
- Docker entrypoint smoke test。

建议下一步：

```text
v0.4.1:
  release hygiene + observability API cleanup + SIEM redaction + Docker smoke

v0.5.0:
  MCP server mode / MCP governance / production deployment reference

v1.0:
  API freeze + compatibility policy + production guide + external validation
```

---

## 11. 参考链接

- PyPI v0.4.0: https://pypi.org/project/petfishframework/0.4.0/
- GitHub Repository: https://github.com/kylecui/petfishFramework
- README: https://github.com/kylecui/petfishFramework/blob/master/README.md
- API Reference: https://github.com/kylecui/petfishFramework/blob/master/docs/api.md
- Deployment Guide: https://github.com/kylecui/petfishFramework/blob/master/docs/deployment.md
- CI workflow: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/ci.yml
- Publish workflow: https://github.com/kylecui/petfishFramework/blob/master/.github/workflows/publish.yml
- SECURITY.md: https://github.com/kylecui/petfishFramework/blob/master/SECURITY.md
