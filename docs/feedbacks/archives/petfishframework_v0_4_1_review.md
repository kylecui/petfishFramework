# petfishFramework v0.4.1 Review 与反馈

> 版本：`petfishframework==0.4.1`  
> 发布页：https://pypi.org/project/petfishframework/0.4.1/  
> 本次验证重点：基于 v0.4.0 遗留问题，核验 release hygiene、observability API、SIEM redaction、Docker entrypoint、SECURITY.md、CHANGELOG、Trusted Publishing 与核心 runtime 主链路。

---

## 1. 总体结论

v0.4.1 是一次典型的 review-fix patch，目标明确，修得比较到位。

v0.4.0 的主要问题是：

1. `CHANGELOG.md` 基本不可用；
2. `SECURITY.md` supported versions 仍停在 `0.2.x`；
3. `OTelSink` / `SIEMSink` 未从 `petfishframework.observability` 顶层导出；
4. `SIEMSink` 主要处理 credential token，不会自动脱敏常见 secret 字段；
5. Docker entrypoint 需要验证；
6. README / docs / Dockerfile / deployment docs raw 格式仍被压缩成少量超长行。

v0.4.1 对前五项已经基本修复：

- `CHANGELOG.md` 已补 v0.4.1 / v0.4.0 / v0.3.x / v0.2.x 主要历史；
- `SECURITY.md` 已更新为 `0.4.x` active、`0.3.x` security fixes only；
- `petfishframework.observability` 顶层已经导出 `OTelSink` 和 `SIEMSink`；
- `SIEMSink` 增加默认敏感 key 脱敏和 nested key redaction；
- `python -m petfishframework` 已可执行，Docker entrypoint 不再天然崩溃。

仍未完全解决的是：

> README / docs / Dockerfile / deployment.md 等 raw 文件仍然呈现为少量超长行，可读性与 review 体验仍差。

因此，v0.4.1 可以评价为：

> 一个有效的 production-hardening patch，修复了 v0.4.0 最重要的 release hygiene、observability export、SIEM redaction 和 Docker entrypoint 问题；但文档格式化仍应继续修。

---

## 2. PyPI 与发布状态

PyPI v0.4.1 页面显示：

| 项目 | 状态 |
|---|---|
| 版本 | `0.4.1` |
| 发布时间 | 2026-07-08 |
| Python 要求 | `>=3.10` |
| Development Status | `3 - Alpha` |
| Tests | 305 |
| Extras | `openai`, `anthropic`, `mcp`, `otel`, `vault` |
| Trusted Publishing | Yes |
| Provenance / attestation | Yes |
| Source distribution | `petfishframework-0.4.1.tar.gz` |
| Wheel | `petfishframework-0.4.1-py3-none-any.whl` |

PyPI 文件详情显示：

- sdist 使用 Trusted Publishing；
- wheel 使用 Trusted Publishing；
- 两者均有 attestation / provenance；
- provenance 指向 GitHub `publish.yml`；
- tag 为 `refs/tags/v0.4.1`；
- source repository 为公开仓库；
- token issuer 为 GitHub OIDC。

这说明 v0.4.1 的供应链发布可信度继续保持。

---

## 3. 本地 Playground 复测摘要

## 3.1 安装与版本

测试命令：

```bash
python -m venv /tmp/pf041
source /tmp/pf041/bin/activate
pip install petfishframework==0.4.1
```

版本确认：

```python
import petfishframework
print(petfishframework.__version__)
```

输出：

```text
0.4.1
```

---

## 3.2 Quickstart 复测

测试：

```python
from petfishframework import Agent, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator

model = FakeModel.script_tool_then_answer(
    "calculator",
    {"expression": "17 * 23"},
    "391",
)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)
```

结果：

```text
391
```

判断：

> 核心 quickstart 主链路继续稳定。

---

## 3.3 Observability 顶层导出复测

测试：

```python
from petfishframework.observability import OTelSink, SIEMSink

print(OTelSink, SIEMSink)
```

结果：

```text
obs exports ok
```

判断：

> v0.4.0 中 OTelSink / SIEMSink 需要从子模块导入的问题已修复。

---

## 3.4 SIEMSink redaction 复测

测试 event：

```python
from petfishframework.observability import SIEMSink
from petfishframework.core.events import Event

sink = SIEMSink()

event = Event(
    "tool.called",
    1.0,
    {
        "tool_name": "x",
        "api_key": "SECRET",
        "authorization": "Bearer X",
        "nested": {
            "password": "PW",
            "normal": "ok",
        },
    },
)

sink(event)
```

实际 JSONL 中：

```json
{
  "details": {
    "api_key": "[REDACTED]",
    "authorization": "[REDACTED]",
    "nested": {
      "password": "[REDACTED]",
      "normal": "ok"
    },
    "tool_name": "x"
  },
  "redacted_fields": [
    "api_key",
    "nested.password",
    "authorization"
  ]
}
```

判断：

> v0.4.0 中 “SIEMSink 只处理 credential token，不处理普通 api_key / secret / password” 的问题已经修复。v0.4.1 已支持默认敏感 key 与 nested key redaction。

---

## 3.5 `python -m petfishframework` 复测

测试：

```bash
python -m petfishframework
```

结果：

```text
petfishFramework v0.4.1

This is a library, not a standalone CLI.
Quick start:
  python -c 'from petfishframework import Agent, ReAct; ...'

Or run an example:
  python examples/01_quickstart.py
```

退出码：

```text
0
```

判断：

> Dockerfile 中 `ENTRYPOINT ["python", "-m", "petfishframework"]` 不再天然崩溃。v0.4.1 已通过新增 `__main__.py` 修复这个问题。

---

## 4. v0.4.0 遗留问题逐项核验

| v0.4.0 遗留问题 | v0.4.1 状态 | 判断 |
|---|---:|---|
| `CHANGELOG.md` 基本为空 | 已补 v0.4.1 / v0.4.0 / v0.3.x / v0.2.x / v0.1.x | 已解决 |
| `SECURITY.md` Supported Versions 仍写 `0.2.x` | 已更新为 `0.4.x` active + `0.3.x` security fixes only | 已解决 |
| `OTelSink` / `SIEMSink` 未从 observability 顶层导出 | 已导出 | 已解决 |
| `SIEMSink` 不自动 redact 常见 secret 字段 | 已支持默认 key + nested key redaction | 已解决 |
| Docker entrypoint 可能崩溃 | 已新增 `__main__.py`，`python -m petfishframework` 退出码 0 | 已解决 |
| README / docs / Dockerfile raw 格式压缩为少量长行 | 仍存在 | 未解决 |
| Docker build/run smoke test | 未在本次核验中确认 | 仍建议加入 CI |

---

## 5. CHANGELOG 状态

v0.4.1 的 `CHANGELOG.md` 已经不再是空壳，包含：

- v0.4.1 Review Fix Patch；
- v0.4.0 Production Foundation；
- v0.3.2 YAML Policy DSL Expansion；
- v0.3.1 Credential Event Safety；
- v0.3.0 Policy Engine + Credential Broker；
- v0.2.0 Enterprise PoC Release；
- v0.1.6-v0.1.9 merged baseline；
- v0.1.0a1 Alpha。

这说明 release history 已经可读。

当前问题：

> `CHANGELOG.md` raw 文件仍是极少数超长行，内容有了，但格式不利于 review、diff 和 blame。

建议 v0.4.2 修：

- 恢复正常 Markdown 换行；
- 每个版本标题、子标题、bullet 独立成行；
- 保持 GitHub preview 与 raw review 都可读。

---

## 6. SECURITY.md 状态

v0.4.1 中 `SECURITY.md` 已更新为：

```text
0.4.x ✅ Active development
0.3.x ⚠️ Security fixes only
< 0.3 ❌ Not supported
```

并继续包含：

- 不要开 public issue；
- 邮件报告；
- 48 小时确认；
- 7 天内 fix timeline；
- runtime permission bypass、tool execution without authorization、audit log tampering、sensitive data leakage in events 等 in-scope；
- LLM model vulnerabilities、prompt injection、infrastructure security 等 out-of-scope。

判断：

> v0.4.0 中 supported versions 过期的问题已解决。

建议后续：

- 将 “prompt injection” 的 out-of-scope 表述更精确化：petfishFramework 不消除 prompt injection，但 runtime controls mitigate tool-side impact；
- 增加 PGP key 或 security contact verification；
- 增加 supported versions 自动同步机制。

---

## 7. Observability API 状态

v0.4.1 中：

```python
from petfishframework.observability import OTelSink, SIEMSink
```

已可用。

`observability/__init__.py` 当前导出：

```python
ConsoleSink
ListSink
OTelSink
SIEMSink
```

判断：

> v0.4.0 的 observability API discoverability 问题已解决。

下一步建议：

- 在 README / API Reference 中增加 `event_sinks=(otel_sink, siem_sink)` 的完整示例；
- 增加 `SIEMSink(redact_keys=...)` 示例；
- 增加 `OTelSink` 在未安装 opentelemetry 时 no-op 的说明。

---

## 8. SIEMSink 状态

v0.4.1 中 `SIEMSink` 默认 redaction keys 包括：

```python
api_key
secret
password
token
authorization
cookie
```

同时支持：

- nested dict key matching；
- `_credential_token` redaction；
- `ScopedToken` redaction；
- `redacted_fields` 输出；
- 自定义 `redact_keys`。

判断：

> v0.4.0 中 SIEMSink redaction 范围有限的问题已解决。

注意点：

- 当前 redaction 是 key-based，不是 value-pattern based；
- 它不会自动识别所有 secret 格式，例如 `sk-...`、JWT、AWS key，除非字段名命中；
- 如果用户把 secret 放在 `data` / `value` / `payload` 这类普通 key 下，仍可能泄露。

建议 v0.4.2 / v0.5：

- 增加可选 value regex redaction；
- 增加 allowlist mode；
- 增加 max field length / payload size limit；
- 增加 SIEMSink 文档警告：key-based redaction is not a DLP engine。

---

## 9. Docker / Deployment 状态

v0.4.1 已新增：

```python
src/petfishframework/__main__.py
```

本地实测：

```bash
python -m petfishframework
```

退出码为 0，并输出版本与使用提示。

这意味着 Dockerfile 的：

```dockerfile
ENTRYPOINT ["python", "-m", "petfishframework"]
```

不再天然失败。

但我没有完成实际：

```bash
docker build
docker run
```

因此：

> Docker entrypoint 的 Python 层问题已修；完整 container build/run 仍建议进入 CI 做 smoke test。

建议：

```bash
docker build -t petfishframework .
docker run --rm petfishframework
docker run --rm -v $(pwd)/examples:/app/examples petfishframework python examples/05_enterprise_expense.py
```

---

## 10. 文档格式仍是主要残留问题

v0.4.1 当前最大残余问题不是 runtime，不是 supply chain，也不是 observability，而是：

> raw Markdown 文件大量压缩为少量超长行。

受影响文件包括：

- README.md；
- CHANGELOG.md；
- SECURITY.md；
- Dockerfile；
- docs/deployment.md；
- 可能还有 docs/api.md 等。

这会造成：

- diff 不可读；
- review 不可读；
- git blame 不可用；
- 外部 contributor 难以维护；
- Markdown lint 难做；
- release review 难做。

建议 v0.4.2 做一次纯格式化版本：

```text
docs-format-only:
  README.md
  CHANGELOG.md
  SECURITY.md
  Dockerfile
  docker-compose.yml
  docs/*.md
```

并加入 CI：

```bash
markdownlint README.md docs/*.md
ruff format?  # Python only
prettier --check "**/*.md" "**/*.yml" "Dockerfile"
```

---

## 11. 当前成熟度判断

## 11.1 可以说什么

可以说：

> petfishFramework v0.4.1 is an Alpha-stage runtime control framework with production-hardening scaffolding, including deterministic replay/rerun/resume, OTel/SIEM observability, Vault adapter, Docker deployment docs, CI, Trusted Publishing, and improved release/security hygiene.

可以说：

> v0.4.1 fixes the v0.4.0 observability export, SIEM redaction, Docker entrypoint, CHANGELOG, and SECURITY.md versioning issues.

可以说：

> v0.4.1 is suitable for controlled enterprise PoC and production-readiness evaluation.

---

## 11.2 不应说什么

仍不建议说：

- production-ready；
- v1 API stable；
- complete deployment hardening；
- complete SIEM / DLP solution；
- complete MCP server support；
- fully benchmark-proven against mainstream frameworks；
- complete incident response / ops lifecycle；
- enterprise compliance ready without additional controls。

---

## 11.3 推荐定位

中文：

> petfishFramework v0.4.1 是一个 Alpha 阶段的 Agent 运行时控制框架，已经具备较完整的运行时权限、策略、凭据、审计、回放、观测、Vault、Docker 与可信发布基础，并修复了 v0.4.0 的主要 release hygiene 与 observability 问题。它适合受控企业 PoC 与生产化前评估，但仍需继续完善文档格式、Docker smoke、SIEM redaction 边界说明和 v1 API 稳定性。

英文：

> petfishFramework v0.4.1 is an Alpha-stage runtime control framework for reliable, auditable, budget-aware, and permission-aware AI agents, with production-hardening scaffolding and improved release/security hygiene.

---

## 12. 五顾问评判

## 12.1 反对者

v0.4.1 仍不是 production-ready。

主要问题：

1. Markdown / Dockerfile raw 格式仍压缩为超长行；
2. Docker build/run 尚未在本次核验中确认；
3. SIEMSink 是 key-based redaction，不是完整 DLP；
4. MCP server mode 仍 planned；
5. v1 API 稳定性、migration policy、compatibility policy 尚未形成；
6. OpenTelemetry / SIEM 还缺真实后端集成 demo。

但反对者也应承认：

> v0.4.1 确实修掉了 v0.4.0 的几个明显工程短板。

---

## 12.2 本质思考者

v0.4.1 的本质不是新增大功能，而是：

> 对生产化可信度的小闭环修复。

它修的是开发者信任链：

- release history；
- security policy；
- observability API；
- SIEM redaction；
- Docker entrypoint。

这些都不是“炫功能”，但都属于生产化框架必须补的工程卫生。

---

## 12.3 机会挖掘者

现在 petfishFramework 的企业叙事更完整：

```text
Runtime control
  -> YAML policy
  -> CredentialBroker
  -> AuditReport
  -> Replay/Rerun/Resume
  -> OTel/SIEM
  -> Vault
  -> Docker
  -> Trusted Publishing
  -> Security Policy
```

这已经不是普通 Agent 框架的叙事，而是 AI Agent runtime infrastructure 的叙事。

---

## 12.4 局外人

外部用户现在看到 PyPI 会觉得：

- 305 tests；
- Trusted Publishing；
- OTel/SIEM；
- Vault；
- Docker；
- SECURITY.md；
- CHANGELOG；
- Alpha 边界清晰。

但点进 raw 文件时仍会看到压缩成一行的 README / CHANGELOG / Dockerfile，这会让项目显得“生成感”重，也影响专业度。

---

## 12.5 执行者

v0.4.2 不建议加大功能。

建议只做四件事：

1. 全量格式化 Markdown / Dockerfile / YAML；
2. CI 加 markdownlint / prettier check；
3. CI 加 Docker build/run smoke；
4. SIEMSink 文档说明 key-based redaction 边界。

---

## 13. v0.4.2 建议清单

## P0：文档格式化

- [ ] README.md 正常换行；
- [ ] CHANGELOG.md 正常换行；
- [ ] SECURITY.md 正常换行；
- [ ] Dockerfile 正常多行；
- [ ] docker-compose.yml 正常多行；
- [ ] docs/deployment.md 正常换行；
- [ ] docs/api.md 正常换行；
- [ ] docs/threat-model.md 正常换行。

## P0：格式检查 CI

- [ ] markdownlint；
- [ ] prettier check for `.md`, `.yml`, `Dockerfile`；
- [ ] release check: no compressed one-line markdown；
- [ ] release check: grep old versions；
- [ ] release check: grep stale “coming in”。

## P1：Docker smoke CI

- [ ] `docker build -t petfishframework .`；
- [ ] `docker run --rm petfishframework`；
- [ ] `docker run --rm -v $(pwd)/examples:/app/examples petfishframework python examples/05_enterprise_expense.py`；
- [ ] docker-compose smoke optional。

## P1：SIEM redaction docs

- [ ] 明确默认 key-based redaction；
- [ ] 明确不是 full DLP；
- [ ] 增加 `redact_keys` 示例；
- [ ] 增加 nested redaction 示例；
- [ ] 增加 secret-in-value caveat。

## P2：Observability demo

- [ ] 增加 `examples/06_observability.py`；
- [ ] 展示 ListSink / ConsoleSink / SIEMSink / OTelSink；
- [ ] 输出 JSONL；
- [ ] 展示 redacted_fields；
- [ ] 可选 OpenTelemetry collector docker compose。

---

## 14. 最终判断

v0.4.1 的回答是：

> 是的，v0.4.0 的主要 review-fix 项基本已经解决。

具体包括：

- CHANGELOG 已补；
- SECURITY.md supported versions 已更新；
- OTelSink / SIEMSink 顶层导出已修；
- SIEMSink 默认敏感 key 与 nested redaction 已修；
- Docker entrypoint 的 Python 层崩溃风险已修；
- Trusted Publishing 继续保持；
- PyPI tests 数已更新到 305；
- Quickstart 与核心 runtime 继续稳定。

剩下主要是：

> 文档与配置文件 raw 格式仍需工程化整理；Docker build/run 需要进入 CI；SIEM redaction 需要明确边界说明。

推荐下一步：

```text
v0.4.2:
  docs/config formatting + markdownlint/prettier + Docker smoke + SIEM docs

v0.5.0:
  MCP server mode / MCP governance / observability demo / deployment reference

v1.0:
  API freeze + compatibility policy + production guide + external validation
```

---

## 15. 参考链接

- PyPI v0.4.1: https://pypi.org/project/petfishframework/0.4.1/
- README: https://github.com/kylecui/petfishFramework/blob/master/README.md
- CHANGELOG: https://github.com/kylecui/petfishFramework/blob/master/CHANGELOG.md
- SECURITY.md: https://github.com/kylecui/petfishFramework/blob/master/SECURITY.md
- Observability exports: https://github.com/kylecui/petfishFramework/blob/master/src/petfishframework/observability/__init__.py
- SIEMSink: https://github.com/kylecui/petfishFramework/blob/master/src/petfishframework/observability/siem_sink.py
- Dockerfile: https://github.com/kylecui/petfishFramework/blob/master/Dockerfile
- Deployment Guide: https://github.com/kylecui/petfishFramework/blob/master/docs/deployment.md
