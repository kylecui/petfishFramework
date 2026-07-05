# petfishFramework 验证路线图（v0.2.1-validated）

> 基于 Council Thinking 审查结论：「停止扩展，开始验证。」
> 核心判断：架构正确，但存在**验证真空**——166 个测试全是 FakeModel，框架从未处理过一个真实 LLM 调用。
> 目标：从「纸面验证」推进到「真实验证」。

## 当前状态快照

| 指标 | 当前值 | 问题 |
|---|---|---|
| 测试数 | 166 | 全部使用 FakeModel（确定性）——0 个真实 LLM 测试 |
| LICENSE | ❌ 缺失 | 声称 MIT 但无法律文件——企业用户法务阻塞 |
| PyPI | ❌ 未发布 | 不能 `pip install`——无法被外部评估 |
| MCP 验证 | mock server | 从未连接真实 MCP server |
| Benchmark | ❌ 无 | 「可靠性即架构」无量化证据 |
| 真实用户 | 0 | 无外部反馈 |

## Council 核心风险

**虚假信心陷阱**：166 passing tests + 干净 ruff + 完整 API 文档 = 「框架已 ready」的错觉。实际上它从未在真实条件下运行过。第一个真实用户可能触发连锁失败。

---

## 验证路线图（5 个阶段，按优先级排序）

### Phase 0: 法务基础设施（立即，阻塞一切）

**目标**：解除所有法务阻塞，让框架可被企业评估。

| 动作 | 具体 | 验收标准 | 预估 |
|---|---|---|---|
| 创建 LICENSE | MIT 全文 | 文件存在，年份/持有者正确 | 5 min |
| 更新 pyproject.toml | `license = "MIT"` + classifier | `uv run python -m build` 无警告 | 2 min |
| 添加 LICENSE header | 主模块文件头（可选） | — | 10 min |

**决策门**：LICENSE 存在 → 进入 Phase 1。

---

### Phase 1: 真实集成验证（最高优先级，证明框架能跑）

**目标**：用真实 LLM API 证明框架端到端工作。这是 Council 指出的 #1 风险。

**为什么这是 #1**：当前所有差异化声明（可靠性、模型无关、工具调用）都建立在 FakeModel 上——一个确定性 mock。真实 API 有格式差异、token 计数偏差、超时行为、错误语义差异。这些只能通过真实调用发现。

#### 1A: OpenAI 集成测试

**测试文件**：`tests/integration/test_openai_integration.py`（新目录 `integration/`）

标记：`@pytest.mark.integration`——CI 默认跳过，需 `OPENAI_API_KEY` 环境变量 + `pytest -m integration` 显式触发。

| 测试 | 验证什么 | 预期结果 | 可能发现的 bug |
|---|---|---|---|
| `test_real_chat_completion` | Agent + OpenAIModel + 简单问题 → 返回非空答案 | answer 非空，usage.total_tokens > 0 | 消息格式转换错误 |
| `test_real_tool_calling` | Agent + OpenAIModel + Calculator → 工具被调用，结果正确 | trajectory 有 tool 步骤，答案包含计算结果 | tool_call ID 格式不匹配；arguments JSON 解析失败 |
| `test_real_conversation` | 两轮对话 + ConversationStore → 第二轮引用第一轮 | 第二轮答案引用了第一轮内容 | 消息拼接顺序错误；role 映射错误 |
| `test_real_streaming` | Agent.run_stream() → 多个 chunk | chunk 数 > 1，拼接 = 完整答案 | streaming 格式差异；chunk 解析错误 |
| `test_real_structured_output` | Agent.run_structured(PersonInfo) → 解析成功 | data.name 是字符串，parse_error is None | JSON 提取失败；dataclass 实例化失败 |
| `test_real_error_handling` | 无效 model name → 清晰错误 | 异常消息包含 model name | 错误类型映射不正确 |
| `test_real_retry` | RetryModelAdapter + OpenAI（人为触发限流） → 重试后成功 | retry_count > 0 或成功完成 | retry 逻辑与真实 API 错误不兼容 |

**关键执行步骤**：
1. 写测试（先用 FakeModel 确保测试逻辑正确）
2. 设置 `OPENAI_API_KEY` 环境变量
3. 逐个运行 `pytest -m integration -v`
4. **记录每个失败**：是什么 bug？是转换错误还是 API 行为差异？
5. 修复 bug，重跑
6. 全部通过 → Phase 1A 完成

**预估**：2-4 小时（含 bug 修复时间）。

**预算**：~$1-3（GPT-4o-mini 即可验证逻辑；GPT-4o 用于完整验证）。

**风险**：可能发现 3-5 个真实 bug。这是好事——在用户发现之前找到它们。

#### 1B: Anthropic 集成测试（并行）

**测试文件**：`tests/integration/test_anthropic_integration.py`

| 测试 | 验证什么 |
|---|---|
| `test_real_anthropic_chat` | Agent + AnthropicModel → 返回非空答案 |
| `test_real_anthropic_tool_call` | Agent + AnthropicModel + Calculator → 工具调用 |
| `test_real_anthropic_system_message` | 系统消息正确分离（Anthropic 特有） |

**预估**：1-2 小时。预算 ~$1。

#### 1C: 修复发现的 bug

Phase 1A/1B 可能发现的问题（预判）：
- OpenAI tool_call ID 格式（`call_xxxx`）与我们的 ToolCall.id 不匹配
- Token 计数：OpenAI 返回 `prompt_tokens`/`completion_tokens`，字段名映射
- Anthropic content blocks 格式：text + tool_use 混合
- Anthropic max_tokens 必填：默认值可能不够
- 错误类型映射：`openai.RateLimitError` vs 我们的处理

**修复原则**：修真实 bug，不改测试逻辑（如果测试逻辑正确但实现错误，改实现）。

**决策门**：全部集成测试通过 → 进入 Phase 2。

---

### Phase 2: Pass^k Benchmark（旗舰卖点验证）

**目标**：用真实模型 + 真实任务证明「可靠性即架构」不是空话。这是 Council 指出的**最大杠杆**。

**为什么这是最大杠杆**：
- 如果 Pass@8 在 petfishFramework 下显著高于裸 API 调用 → 这是**可量化、可发表、用户可感知**的差异化
- 如果 Pass@8 = 8/8 → 证明 scaffold 稳定
- 如果 Pass@8 < 8/8 → 发现了真实问题（更有价值）

#### 2A: 设计 benchmark

**任务选择原则**：
- 简单到成本可控（< $5/batch）
- 复杂到能体现 scaffold 差异（不是单次问答）
- 可判定（有明确的正确/错误标准）

**候选任务**：
1. **多步计算**：「(15 + 27) * 3 - 10 = ?」（需要工具调用，ReAct 多步）
2. **知识检索**：「Python 的 GIL 是什么？」（需要 RAG，CRAG 路由）
3. **结构化输出**：「返回 JSON {"product": "x", "price": n}」（需要结构化解析）

**模型**：GPT-4o-mini（低成本，temperature=0.7 用于引入非确定性）

**对照组**：
- A: petfishFramework（ReAct + Calculator + Budget + 事件溯源）
- B: 裸 API 调用（直接 OpenAI chat.completions，无框架）

#### 2B: 执行 benchmark

```python
# 对每个任务 × 每个对照组 × k=8 次
# 记录：答案、一致性、token 消耗、耗时

# petfishFramework 组
agent = Agent(model=OpenAIModel("gpt-4o-mini"), reasoning=ReAct(), tools=(Calculator(),))
pf_result = pass_at_k(lambda task: agent.session(task), Task("..."), k=8)

# 裸 API 组
raw_result = pass_at_k_raw(task, k=8)  # 直接调 OpenAI API

# 对比
print(f"petfishFramework Pass@8: {pf_result.pass_count}/8")
print(f"Raw API Pass@8:           {raw_result.pass_count}/8")
```

#### 2C: 文档化结果

创建 `docs/benchmark-results.md`：
- 任务描述
- 模型/参数
- 两组 Pass@8 对比
- token 消耗对比
- 结论：scaffold 是否提高了可靠性？

**预估**：1-2 小时。预算 ~$5-10。

**决策门**：
- 如果 petfishFramework Pass@8 ≥ 裸 API → 旗舰卖点得到验证 → 进入 Phase 3
- 如果 petfishFramework Pass@8 < 裸 API → 发现问题，分析原因，修复后重跑

---

### Phase 3: 发布与对外可见（让世界评估）

**目标**：让外部开发者能在 5 分钟内评估 petfishFramework。

#### 3A: PyPI 发布

| 动作 | 具体 |
|---|---|
| 完善 pyproject.toml | authors, classifiers, readme, urls (GitHub, docs) |
| 构建 | `uv build` → wheel + sdist |
| 检查 | `twine check dist/*` |
| 发布 | `twine upload dist/*`（需 PyPI 账号 + API token） |
| 验证 | `pip install petfishframework` → import → Agent 可用 |

#### 3B: README 重写

**结构**（回答「为什么切换？」）：

```markdown
# petfishFramework

> The AI agent framework where reliability is architecture, not an afterthought.

## 为什么用 petfishFramework？

| 维度 | LangChain | CrewAI | petfishFramework |
|---|---|---|---|
| 可靠性度量 | 手动加 LangSmith | 无 | **Pass^k 原生支持** |
| 推理策略 | 仅 ReAct | 仅 ReAct | **ReAct + LATS + LLM+P** |
| MCP | 适配器附加 | 适配器附加 | **规范工具契约** |
| 成本控制 | 日志 | 无 | **硬执行 Budget** |

## Quick Start（3 行）

pip install petfishframework
...
（从 Phase 2 的 benchmark 数据填充）

## Benchmark

Pass@8 on GPT-4o-mini: petfishFramework 8/8 vs Raw API X/8
（从 Phase 2 结果填充）
```

#### 3C: 文档站点（可选）

- mkdocs-material + API reference（已有 docs/api.md）
- 部署到 GitHub Pages

**预估**：3-4 小时。

**决策门**：PyPI 可安装 + README 有 benchmark 数据 → 进入 Phase 4。

---

### Phase 4: 真实 MCP 验证

**目标**：用真实 MCP server 证明 MCP-first 不是空话。

| 动作 | 具体 |
|---|---|
| 安装 MCP server | `npx @modelcontextprotocol/server-filesystem /tmp` |
| 连接 | `connect_stdio("npx", ["@modelcontextprotocol/server-filesystem", "/tmp"])` |
| 发现工具 | `client.discover_tools()` → 验证 list_files / read_file 等 |
| 调用工具 | 通过 Agent 调用 MCP 工具 → 验证结果 |
| 文档化 | 记录兼容性、发现的问题 |

**预估**：1-2 小时。

**风险**：真实 MCP server 的 JSON-RPC 实现细节可能与我们不同（初始化参数、capabilities 格式、错误处理）。

---

### Phase 5: 首个真实用户（外部验证）

**目标**：让一个不参与设计的人用框架构建一个真实项目。

| 动作 | 具体 |
|---|---|
| 定义目标用户 | 有 LangChain 经验、想评估替代方案的 Python 开发者 |
| 创建入门指南 | `docs/getting-started.md`——从安装到第一个 agent |
| 找 1 个测试用户 | 朋友/同事/社区 |
| 收集反馈 | 什么卡住了？什么惊喜？什么缺失？ |
| 迭代 | 根据反馈修复/改进 |

**预估**：1-2 周（外部依赖，不可控）。

---

## 总结：验证路线图时间线

| Phase | 目标 | 预估 | 阻塞 |
|---|---|---|---|
| **0. LICENSE** | 法务解阻 | 15 min | 无 |
| **1. 真实集成** | 证明能跑 | 3-5 小时 | Phase 0 |
| **2. Pass^k** | 证明更好 | 1-2 小时 | Phase 1 |
| **3. PyPI + README** | 让世界评估 | 3-4 小时 | Phase 2 |
| **4. 真实 MCP** | 证明 MCP-first | 1-2 小时 | Phase 1 |
| **5. 首个用户** | 外部验证 | 1-2 周 | Phase 3 |

**关键路径**：Phase 0 → 1 → 2 → 3（约 1-2 天内部工作）。

**Council 的核心建议**：每个 Phase 都产生**可验证的证据**，而非更多功能。下一个版本号是 v0.2.1-validated，不是 v0.3-features。

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| Phase 1 发现严重 bug（框架根本不能跑） | 高 | 这是好事——在用户前发现。预留 bug 修复时间 |
| Pass@8 无差异（scaffold 不影响可靠性） | 高 | 如果真无差异，重新评估定位；可能需要更强的 scaffold（LATS vs ReAct） |
| MCP 协议不兼容 | 中 | 记录差异，修复传输层 |
| 首个用户反馈负面 | 中 | 负面反馈 = 真实信号，优于无反馈 |
| AutoGen→MAF 迁移窗口关闭 | 中 | 速度优先——Phase 0-3 在 1 周内完成 |
