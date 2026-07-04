# Competitor Matrix — AI Agent Frameworks

> Evidence date: 2026-07-03. All data from official docs, GitHub API, and release notes via parallel librarian research. Stars are approximate as of 2026-07-03.

## 评估对象（11 个框架）

| # | 框架 | 维护方 | Stars | License | 最新版本 | 状态 |
|---|---|---|---|---|---|---|
| 1 | LangChain | LangChain Inc. | ~140.8k | MIT | v1.3.0 | 活跃 |
| 2 | LangGraph | LangChain Inc. | ~36.4k | MIT | v1.2.7 | 活跃 |
| 3 | LlamaIndex | LlamaIndex Inc. | ~50.6k | MIT | v0.14.23 | 活跃 |
| 4 | Haystack | deepset | ~25.8k | Apache-2.0 | v2.30.2 | 活跃 |
| 5 | AutoGen | Microsoft | ~59.4k | MIT(code)/CC-BY-4.0(docs) | py-v0.7.5 | ⚠️ 维护模式 → MAF |
| 6 | CrewAI | crewAI Inc. | ~54.8k | MIT | v1.15.1 | 活跃 |
| 7 | Semantic Kernel | Microsoft | ~28.2k | MIT | py-1.43.1 | ⚠️ → MAF |
| 8 | Dify | LangGenius | ~147.5k | Modified Apache 2.0† | v1.15.0 | 活跃（平台） |
| 9 | Pydantic AI | Pydantic | ~18.2k | MIT | v2.4.0 | 活跃（年轻） |
| 10 | OpenAI Agents SDK | OpenAI | ~27.6k | MIT | v0.17.7 | 活跃（pre-1.0） |
| 11 | Google ADK | Google | ~20.4k | Apache-2.0 | v2.3.0 | 活跃（年轻） |

†Dify 修改版 Apache 2.0：多租户 SaaS 需商业许可；前端不可移除 logo/copyright。

---

## 功能矩阵

### A. 架构范式

| 框架 | 核心范式 | 编排粒度 | 确定性控制 |
|---|---|---|---|
| LangChain | Agent harness (`create_agent` + middleware) | 中（agent loop） | 中（middleware 可拦截） |
| LangGraph | 有状态图 (`StateGraph` / Functional API) | 低（显式节点/边） | 高（显式图 + checkpoint） |
| LlamaIndex | 事件驱动 Workflows + Indices | 中（@step 事件） | 中（事件驱动） |
| Haystack | Pipeline 多重有向图 | 低（显式组件接线） | 高（YAML 序列化 + 验证） |
| AutoGen | 分层事件驱动多 Agent 对话 | 中（Team 预设） | 低-中（GraphFlow 可选） |
| CrewAI | 角色制 Crew + Task Process + Flows | 中（sequential/hierarchical） | 中（Flows 增强确定性） |
| Semantic Kernel | Kernel + Plugin + function calling | 中（plugin 编排） | 中 |
| Dify | 可视化工作流画布 | 中（节点编排） | 高（确定性 workflow 节点） |
| Pydantic AI | 类型安全 Agent + pydantic-graph | 中（graph 节点） | 中-高（显式 graph） |
| OpenAI Agents SDK | 极简原语（Agent/Runner/handoff） | 高（抽象少） | 低（极简，少控制点） |
| Google ADK | Agent + Workflow 图 | 低（显式图节点） | 高（graph workflows） |

**证据**：各框架官方架构文档。关键差异 — LangGraph/Haystack/ADK 提供显式图控制（最高确定性）；OpenAI SDK 最简但控制力最弱；Dify 是唯一可视化优先的。

### B. 模型抽象（多供应商支持）

| 框架 | 锁定风险 | 供应商覆盖 | 接口统一度 |
|---|---|---|---|
| LangChain | 低 | 1000+ 集成（`init_chat_model`） | 高（`BaseChatModel`） |
| LangGraph | 低（继承 LangChain） | 同 LangChain | 高 |
| LlamaIndex | 低 | 300+ 包（`LLM` base） | 高 |
| Haystack | 中 | 40+ Generator 组件 | 中（per-provider class） |
| AutoGen | 低-中 | OpenAI/Azure/Anthropic/Ollama + SK adapter | 高（`ChatCompletionClient`） |
| CrewAI | 低 | OpenAI/Anthropic/Gemini/Bedrock/Cortex + LiteLLM | 高（`LLM` class） |
| Semantic Kernel | 低 | OpenAI/Azure/Gemini/Mistral/HF/Bedrock/Ollama/ONNX | 高（`IChatCompletionService`） |
| Dify | 低 | 插件市场（OpenAI/Anthropic/Gemini/Ollama 等） | 高（插件统一接口） |
| Pydantic AI | 最低 | OpenAI/Anthropic/Gemini/xAI/Bedrock/Groq/Ollama/OpenRouter + 兼容 | 高（`Model` base） |
| OpenAI Agents SDK | ⚠️ **中-高** | OpenAI 优先；非 OpenAI 需适配器；高级功能仅 Responses API | 中 |
| Google ADK | 中 | Gemini 优先；LiteLLM 连接器启用后 100+ | 中（默认仅 Gemini 注册） |

**证据**：各官方 models 文档。**关键发现**：OpenAI Agents SDK 与 Google ADK 存在厂商引力（最佳功能绑定自有平台）；Pydantic AI 模型无关性最强。

### C. RAG 集成深度

| 框架 | 内置 RAG | 向量库支持 | 定制难度 |
|---|---|---|---|
| LangChain | ✅ 成熟（loaders/splitters/embeddings/vectorstores/retrievers） | 20+ 主流 | 低（subclass `VectorStore`） |
| LangGraph | ⚠️ 间接（用 LangChain 组件做节点） | 同 LangChain | 中 |
| LlamaIndex | ✅ 最深（5 种 Index + postprocessors + ingestion pipeline） | 300+ 包 | 低 |
| Haystack | ✅ 强（DocumentStore protocol + retrievers + rankers） | 7 类 ~20+ | 低（实现 protocol） |
| AutoGen | ❌ 无内置 RAG Agent（Memory protocol，BYO 索引） | ChromaDB/Redis/Mem0 | 高 |
| CrewAI | ✅ Knowledge 系统（PDF/CSV/web + ChromaDB/Qdrant） | ChromaDB/Qdrant | 中 |
| Semantic Kernel | ⚠️ 库级（Vector Store connectors + Text Search） | Qdrant 等 connectors | 中 |
| Dify | ✅ 可视化 Knowledge 管道（chunking/index/retrieval/rerank） | Qdrant/Milvus/Weaviate/Chroma/pgvector/ES | 低（UI 配置） |
| Pydantic AI | ❌ BYO（`Embedder` 接口 + 自写工具） | 用户自选 | 高 |
| OpenAI Agents SDK | ⚠️ 托管（`FileSearchTool` → OpenAI Vector Stores） | OpenAI 托管 | 低（但锁定 OpenAI） |
| Google ADK | ⚠️ GCP 优先（Vertex AI Search / Vector Search 2.0） | GCP + BYO | 中 |

**证据**：各 RAG/Knowledge 文档。**关键发现**：LlamaIndex/Haystack 在 RAG 深度上领先；Dify 提供唯一可视化 RAG；AutoGen/Pydantic AI/OpenAI SDK 的 RAG 是薄弱点或厂商锁定。

### D. MCP 支持 ⭐（关键维度）

| 框架 | MCP 客户端 | MCP 服务端 | 传输协议 | 成熟度 |
|---|---|---|---|---|
| LangChain | ✅ `langchain-mcp-adapters` | ❌ | stdio/SSE/HTTP | 高 |
| LangGraph | ✅ 同上 | ✅ `/mcp` endpoint (langgraph-api≥0.2.3) | stdio/SSE/HTTP | 高 |
| LlamaIndex | ✅ `llama-index-tools-mcp` | ✅ serve workflows + LlamaCloud | stdio/SSE/HTTP | 高 |
| Haystack | ✅ `MCPTool`/`MCPToolset` | ✅ Hayhooks | stdio/SSE/HTTP | 高 |
| AutoGen | ✅ `McpWorkbench` | ❌ | stdio/SSE/HTTP | ⚠️ 中（维护模式，bug 不修） |
| CrewAI | ✅ `mcps=[]` DSL + `MCPServerAdapter` | ❌ | stdio/SSE/HTTP | 高 |
| Semantic Kernel | ✅ `MCPStdioPlugin`/`MCPSsePlugin` (Python) | ✅ Kernel as MCP server | stdio/SSE/HTTP | 中（.NET/Java 待补） |
| Dify | ✅ 原生双向 | ✅ publish app as MCP server | HTTP | 高 |
| Pydantic AI | ✅ `MCP` capability + `MCPToolset` | ✅ act as MCP server | stdio/SSE/HTTP | 高 |
| OpenAI Agents SDK | ✅ `HostedMCPTool` + stdio/SSE/HTTP | ❌ | stdio/SSE/HTTP/hosted | 高 |
| Google ADK | ✅ `McpToolset` | ✅ expose ADK tools as MCP | stdio/SSE/HTTP | 高 |

**证据**：各 MCP 文档。**关键发现**：**MCP 已成为标配** — 11/11 框架均支持 MCP 客户端。6/11 同时支持服务端。**MCP 不再是差异化因素**；但「MCP-first 架构」（以 MCP 为核心抽象而非适配器）仍是空白。

### E. 工具 / Function Calling

| 框架 | 工具定义方式 | 托管工具 | 工具生态 |
|---|---|---|---|
| LangChain | `@tool` / `BaseTool` / Pydantic | ❌ | 1000+ 集成 |
| LlamaIndex | `FunctionTool` / `QueryEngineTool` / `ToolSpec` | ❌ | LlamaHub 300+ |
| Haystack | `@tool` / `Tool` dataclass / `ComponentTool` | ❌ | core-integrations |
| AutoGen | `FunctionTool` / `BaseTool` | `PythonCodeExecutionTool`/`HttpTool` | community extensions |
| CrewAI | `@tool` / `BaseTool` | ❌ | crewai-tools 75+ |
| Semantic Kernel | `KernelFunction` / OpenAPI / prompt template | ❌ | connectors |
| Dify | 工具节点 + 插件市场 | ✅ 内置 + 插件 | Marketplace 插件 |
| Pydantic AI | `@agent.tool` / `@agent.tool_plain` | ❌ | toolsets |
| OpenAI Agents SDK | `@function_tool` | ✅ WebSearch/FileSearch/CodeInterpreter/ImageGen | hosted tools |
| Google ADK | `tools=[fn]` auto-wrap / `BaseTool` / OpenAPI | ✅ Vertex AI Search / Google Search | GCP tools |

**证据**：各 tools 文档。大多数用装饰器/函数；OpenAI SDK 与 Dify 提供托管工具（便利但锁定）。

### F. 扩展机制

| 框架 | 机制 | 难度 |
|---|---|---|
| LangChain | middleware + base classes + 集成包 | 低 |
| LangGraph | custom nodes/edges/checkpointers/subgraphs | 中 |
| LlamaIndex | subclass base classes + LlamaHub | 低 |
| Haystack | `@component` + DocumentStore protocol | 低 |
| AutoGen | subclass `BaseChatAgent`/`RoutedAgent` + Core API | 高（冗长） |
| CrewAI | `BaseTool`/`@tool` + Skills + `BaseKnowledgeSource` | 低 |
| Semantic Kernel | connectors + plugins + DI + filters | 中 |
| Dify | Plugin SDK + Marketplace（6 类插件） | 低（沙箱化） |
| Pydantic AI | custom Model/Toolset/Capabilities/hooks + graph nodes | 中 |
| OpenAI Agents SDK | ModelProvider + function tools + guardrails + sessions | 低 |
| Google ADK | `BaseTool`/`FunctionTool` + callbacks + skills + A2A | 中 |

### G. 语言与运行时

| 框架 | Python | JS/TS | C#/.NET | Go | Java | 其他 |
|---|---|---|---|---|---|---|
| LangChain | ✅ 主 | ✅ | ❌ | ❌ | ❌ | ❌ |
| LangGraph | ✅ 主 | ✅（滞后） | ❌ | ❌ | ❌ | ❌ |
| LlamaIndex | ✅ 主 | ✅ | ❌ | ❌ | ❌ | ❌ |
| Haystack | ✅ 仅 | ❌ | ❌ | ❌ | ❌ | ❌ |
| AutoGen | ✅ 主 | ❌ | .NET（维护） | ❌ | ❌ | distributed runtime |
| CrewAI | ✅ 仅 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Semantic Kernel | ✅ | ❌ | ✅ 主 | ❌ | ✅ | ❌ |
| Dify | ✅ 后端 | ✅ 前端 | ❌ | ❌ | ❌ | 平台（Docker/K8s） |
| Pydantic AI | ✅ 仅 | ❌ | ❌ | ❌ | ❌ | ❌ |
| OpenAI Agents SDK | ✅ 主 | ✅ | ❌ | ❌ | ❌ | ❌ |
| Google ADK | ✅ | ✅ | ❌ | ✅ | ✅ | Kotlin |

**关键发现**：仅 **Google ADK**（5 语言）和 **Semantic Kernel**（3 语言）是真正多语言。多数框架 Python-only。**多语言是差异化机会**。

### H. 采用信号汇总

| 框架 | Stars | 活跃度 | 生产用户 | 商业化 |
|---|---|---|---|---|
| LangChain | ~140.8k | 高 | 广泛 | LangSmith/LangGraph Platform |
| LangGraph | ~36.4k | 高 | Klarna/Uber/JPM/Replit | LangSmith Deployment |
| LlamaIndex | ~50.6k | 高 | Boeing/NTT/Experian | LlamaCloud/LlamaAgents |
| Haystack | ~25.8k | 中-高 | Apple/Meta/NVIDIA/Airbus | deepset Cloud |
| AutoGen | ~59.4k | ⚠️ 低（维护） | 研究/原型 | → MAF |
| CrewAI | ~54.8k | 高 | Fortune 500（声称 63%） | AMP/Enterprise/Factory |
| Semantic Kernel | ~28.2k | ⚠️ 中-低（→MAF） | Microsoft Store/KPMG/Fujitsu | → MAF |
| Dify | ~147.5k | 极高 | Kakaku/CyberAgent/Fortune 500 | Enterprise/$30M 融资 |
| Pydantic AI | ~18.2k | 高 | 成长中 | Logfire/Gateway |
| OpenAI Agents SDK | ~27.6k | 高 | 广泛（OpenAI 生态） | OpenAI 平台 |
| Google ADK | ~20.4k | 高 | 成长中 | GCP/Vertex AI |

---

## 未满足需求汇总（跨框架差距）

基于矩阵分析，以下需求**未被现有框架充分满足**：

| # | 未满足需求 | 证据 |
|---|---|---|
| 1 | **简洁但有控制力** — LangGraph/ADK 强大但复杂；OpenAI SDK 简单但控制力弱。中间地带空白 | 架构范式对比 |
| 2 | **真正多语言** — 仅 2/11 框架多语言；Python-only 限制全栈团队 | 语言矩阵 |
| 3 | **MCP-first 架构** — 所有框架把 MCP 作为适配器附加，而非核心抽象 | MCP 矩阵 |
| 4 | **中立许可 + 无 SaaS 限制** — Dify 有限制；多数框架绑观测平台 | 许可证 + 商业化 |
| 5 | **透明成本/确定性控制** — CrewAI/AutoGen 多 Agent 易 token 失控 | 弱点分析 |
| 6 | **解耦观测性** — LangChain→LangSmith、CrewAI→AMP、Dify→自有平台；无厂商中立标准 | 商业化列 |
| 7 | **RAG 即插即用且不锁定** — LlamaIndex 深但重；OpenAI SDK 锁定 Vector Store | RAG 矩阵 |
