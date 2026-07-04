# Competitor Analysis — AI Agent Frameworks

> 研究范围、方法论与证据追踪。结论性文档见同目录下的 `competitor-matrix.md`、`positioning-map.md`、`swot-analysis.md`、`market-brief.md`。

## 研究目标

为 petfishFramework（通用 AI Agent 框架）的立项提供竞争格局证据，回答：
1. 同类 AI Agent 框架如何构建？架构模式、模型对接、RAG/工具/MCP 集成方式。
2. 现有方案的优缺点与未满足需求在哪里？
3. petfishFramework 可以从哪些方向差异化？

## petfishFramework 定位（评估基准）

| 维度 | 目标 |
|---|---|
| 模型层 | 模型无关，统一接口对接各类 LLM |
| RAG 层 | 用户便捷接入自己的 RAG 后端 |
| 工具/MCP 层 | 原生 MCP 支持 + 自定义工具即插即用 |
| 扩展性 | 清晰模块边界，低门槛扩展 |

## 竞争范围

### 直接竞品（通用 Agent 框架）
| 框架 | Cluster | 纳入理由 |
|---|---|---|
| LangChain / LangGraph | A | 编排生态主导者 |
| LlamaIndex | B | RAG 数据框架代表 |
| Haystack | B | 生产级 RAG 管线 |
| AutoGen | C | 多 Agent 对话（Microsoft） |
| CrewAI | C | 角色制多 Agent |
| Semantic Kernel | D | 企业集成（Microsoft） |
| Dify | D | 低代码 LLMOps 平台 |

### 新兴/潜在进入者
| 框架 | Cluster | 纳入理由 |
|---|---|---|
| Pydantic AI | E | 类型安全，新进 |
| OpenAI Agents SDK | E | 厂商官方（原 Swarm） |
| Google ADK | E | 厂商官方 |

### 替代方案（不计入矩阵，但讨论竞争压力）
- 通用工作流自动化（n8n + AI 节点、Zapier AI）
- 可视化无代码（Flowise、Langflow）
- 直接调 API + 手写 prompt（"无框架"方案）

## 评估维度（统一应用于所有框架）

1. 架构范式（chain/graph/pipeline/multi-agent/role-based）
2. 模型抽象（多供应商？接口统一度？锁定风险？）
3. RAG 集成（内置？向量库？定制难度？）
4. 工具/Function calling 机制
5. **MCP 支持**（原生？适配器？路线图？）⭐ 关键维度
6. 扩展机制（插件/自定义组件）
7. 语言与运行时
8. 采用信号（GitHub stars、活跃度、生产用户）
9. 许可证
10. 核心优势（证据支撑）
11. 核心劣势（证据支撑）
12. 2025-2026 动态

## 方法论

- **证据要求**：每个关键论断须可追溯至官方文档/GitHub/博客，附 URL 与访问时间。
- **时效性**：优先 2025-2026 数据；这些框架迭代极快，训练知识可能过时。
- **研究方式**：5 个并行 librarian agent 分别深挖 framework cluster（web search + GitHub + Context7）。
- **质量门禁**：≥3 竞品；矩阵每项有证据；定位图 ≥2 轴；差异化机会可执行；市场规模显式假设。

## 研究任务映射

| Task ID | Cluster | 状态 |
|---|---|---|
| bg_465abddf | LangChain + LangGraph | 进行中 |
| bg_0c4a67a5 | LlamaIndex + Haystack | 进行中 |
| bg_f32bc376 | AutoGen + CrewAI | 进行中 |
| bg_08585fd7 | Semantic Kernel + Dify | 进行中 |
| bg_72f133fe | Pydantic AI + OpenAI SDK + Google ADK | 进行中 |

## 已生成交付物

- [x] [`competitor-matrix.md`](competitor-matrix.md) — 功能矩阵（11 框架 × 8 维度，附证据）
- [x] [`positioning-map.md`](positioning-map.md) — 3 张定位图（抽象×控制力 / 模型无关×开放度 / 形态×用户）
- [x] [`swot-analysis.md`](swot-analysis.md) — petfishFramework 视角 SWOT + 战略含义
- [x] [`market-brief.md`](market-brief.md) — TAM/SAM/SOM + 5 个差异化机会 + 验证优先级

## 高不确定区（需后续验证）

| # | 不确定项 | 原因 | 验证方法 |
|---|---|---|---|
| U1 | 市场规模数字（TAM/SAM） | 预测来源差异大（$30B-$200B+） | 查 Gartner/IDC 付费报告 |
| U2 | MCP-first 架构可行性 | 设计假设，未原型验证 | Phase 2 原型实验（V1） |
| U3 | AutoGen/SK 用户迁移意愿 | 推测性，无一手数据 | 社区调研（V2） |
| U4 | 「简洁+控制力」需求强度 | 定位假设 | 用户访谈（V3） |
| U5 | Stars/采用数据时效 | 2026-07-03 快照，持续变化 | 定期刷新 |

## 证据来源

所有数据由 5 个并行 librarian agent 于 2026-07-03 通过官方文档、GitHub API、release notes 获取。详细引用见各交付物内联链接。
