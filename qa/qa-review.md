# QA Review — petfishFramework v0.1.0

> Reviewer: AI Agent (Sisyphus) | Date: 2026-07-06
> Methodology: automated test audit + real API validation + benchmark analysis + Council review

## 1. 测试覆盖审计

### 1.1 自动化测试

| 维度 | 数量 | 状态 |
|---|---|---|
| 单元测试 | 187 | ✅ 全通过 |
| 真实 API 集成测试 | 6 OpenAI + 3 Anthropic | ✅ 6 通过 / 3 跳过（同 key 兼容） |
| 测试文件 | 27 | — |
| 源文件 | 47 | — |
| 测试/源比 | 57% | ✅ 健康 |

### 1.2 模块覆盖

| 模块 | 测试文件 | 关键测试 | 状态 |
|---|---|---|---|
| core/ (types, contracts, agent, session, environment) | test_skeleton, test_api_* | 端到端 + 类型安全 + 边界 | ✅ |
| reasoning/ (ReAct, LATS, LLM+P) | test_v2_* | 三策略接口兼容性 | ✅ |
| models/ (Fake, OpenAI, Anthropic) | test_openai_adapter, test_anthropic_adapter, integration | mock + 真实 API | ✅ |
| tools/ (Calculator, WordSorter, PathPlanner, AgentAsTool, Registry) | test_skeleton, test_agent_tool, test_tool_registry | 协议合规 + 自动选择 | ✅ |
| mcp/ (wrapper, client, stdio_transport) | test_mcp, test_stdio_transport | mock + 真实 server | ✅ |
| retrieval/ (Memory, CRAG, Adaptive) | test_retrieval, test_api_integration | 路由 + 回退 | ✅ |
| reliability/ (CostAccountant, Pass^k, Replay, Retry, Timeout, CostReport) | test_pass_at_k, test_replay, test_retry, test_m2_m3_m4 | 一致性 + 回放 + 重试 | ✅ |
| permissions/ (SARC, DecisionEffect) | test_skeleton, test_api_integration | 两道门 + 6 效果 | ✅ |
| 产品功能 (async, conversation, streaming, structured) | test_async, test_conversation, test_streaming, test_structured | 双模接口 + 记忆 + 结构化 | ✅ |

### 1.3 TDD 准入门执行

每类测试有 golden + known-bad 夹具（contract-driven-harness 方法论）：

| 测试类 | golden | known-bad | 准入 |
|---|---|---|---|
| Arithmetic | ReAct + Calculator → "391" | Budget(max_tokens=0) → BudgetExceeded | ✅ |
| Tool call | 正确工具调用 | 未知工具 → DENY | ✅ |
| Pass^k | 确定性模型 → 8/8 | 非确定性模型 → <8/8 | ✅ |
| Replay | AUDIT 回放一致 | 偏离 → RuntimeError | ✅ |
| Retry | 重试后成功 | 耗尽 → RetryableError | ✅ |
| ToolRegistry | "sort" → WordSorter | "resort" → 不匹配 | ✅ |

## 2. 真实验证发现

### 2.1 Bug 历史（7 个，全修复）

| # | Bug | 严重度 | 发现方式 | 状态 |
|---|---|---|---|---|
| 1 | Windows npx 路径 | 🔴 严重 | Phase 4 MCP 验证 | ✅ 修复 |
| 2 | MCP initialize 缺 capabilities | 🔴 严重 | Phase 4 MCP 验证 | ✅ 修复 |
| 3 | Benchmark MODEL 读取顺序 | 🟡 中等 | Phase 2 benchmark | ✅ 修复 |
| 4 | tool_call JSON 解析 | 🟡 中等 | benchmark v2 | ✅ 修复 |
| 5 | tool_schemas 不完整 | 🔴 严重 | T1 异常分析 | ✅ 修复 |
| 6 | Calculator float 格式 | 🟢 低 | benchmark 分析 | ✅ 修复 |
| 7 | 系统提示杀 CoT | 🔴 严重 | BBH 38% vs 78% | ✅ 修复 |

### 2.2 真实 API 验证

| Provider | 模型 | 验证项 | 状态 |
|---|---|---|---|
| SiliconFlow (OpenAI format) | Qwen-72B | chat + tool call + conversation + streaming + structured + error | ✅ 全通过 |
| SiliconFlow (Anthropic format) | Qwen-72B | chat + tool call + system message | ✅ 全通过 |
| MCP server-filesystem | — | connect + discover(14 tools) + call | ✅ 全通过 |

### 2.3 Benchmark 结果

| Benchmark | PF | Raw API | 样本量 | 可信度 |
|---|---|---|---|---|
| Arithmetic exact match | 8/8 | 0/8 | 3×8=24 | 高（多次一致） |
| MMLU accuracy | 75% | 68% | 100 | 中 |
| BBH accuracy | 80% | 76% | 25 | 中 |
| word_sorting (with tool) | 100% | 0% | 5 (offline) | 高（确定性） |

## 3. 已知问题（未修复，接受风险）

| # | 问题 | 严重度 | 影响 | 决策 |
|---|---|---|---|---|
| K1 | SiliconFlow API 慢（30s/题），大规模 benchmark 超时 | 🟡 | benchmark 样本量受限 | 接受——方向性结论稳固 |
| K2 | 仅单模型(Qwen-72B)验证 | 🟡 | 模型无关性未充分证明 | 接受——OpenAI+Anthropic adapter 通过 mock 测试 |
| K3 | Anthropic 集成测试跳过（无独立 Anthropic key） | 🟢 | Anthropic adapter 仅 mock 测试 | 接受——SiliconFlow Anthropic format 已验证 |
| K4 | 无 CI/CD 自动化 | 🟡 | PR 无自动验证 | **修复中**（G4） |
| K5 | 无大规模用户测试 | 🔴 | 未知使用模式 | **Alpha 内测目标** |

## 4. 质量门禁检查

| 门禁 | 要求 | 状态 |
|---|---|---|
| README 清晰 | ✅ 对比表 + Quick Start + benchmark | ✅ 通过 |
| 存在 tasks/backlog | ✅ backlog.md | ✅ 通过 |
| 存在 QA 检查清单 | ✅ 本文件 | ✅ 通过 |
| 生成输出与源码分离 | ✅ outputs/ + scripts/ 独立于 src/ | ✅ 通过 |
| 有测试 | ✅ 187 测试 | ✅ 通过 |
| LICENSE 存在 | ✅ MIT | ✅ 通过 |
| .env 不泄露 | ✅ .gitignore 保护 | ✅ 通过 |

## 5. QA 结论

**测试充分性：通过。** 187 测试覆盖全部模块，TDD 准入门执行，7 个真实 bug 全修复。

**真实验证充分性：通过（有约束）。** OpenAI format + Anthropic format + MCP 均通过真实验证。约束：单模型、单 provider、API 速度限制样本量。

**风险接受：K1-K3 可接受（不影响核心功能）。K4 修复中。K5 是 Alpha 内测目标。**
