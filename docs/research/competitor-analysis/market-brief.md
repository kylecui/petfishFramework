# Market Brief — AI Agent Framework 市场

> 基于 `competitor-matrix.md` 证据。市场规模为**估算**，显式标注假设与口径。
> ⚠️ 市场数据不确定性较高（见末尾「高不确定区」）。建议后续用独立来源验证。

## 1. 市场规模估算（TAM / SAM / SOM）

### 口径定义
- **TAM（总可达市场）**：全球 AI Agent / Agentic AI 软件市场（含平台、框架、应用）
- **SAM（可服务市场）**：开发者工具/框架层（排除终端应用与垂直方案）
- **SOM（可获取市场）**：petfishFramework 在 1-2 年内现实可获取的份额

### 估算

| 层级 | 估算（年） | 核心假设 | 置信度 |
|---|---|---|---|
| TAM | ~$50B-80B（2027）| Agentic AI 市场预测（Gartner/MarketsAndMarkets 区间），含所有软件 | 低（预测差异大） |
| SAM | ~$3B-6B（2027）| 开发者框架/SDK 层约占 TAM 6-8%；排除终端应用/SaaS 平台 | 低-中 |
| SOM | ~$0.5M-2M（首年）| 假设获取 SAM 中 0.01-0.03%；参考新兴框架早期（Pydantic AI 1 年 ~18k stars 但商业化低） | 低 |

> **显式假设**：
> 1. Agentic AI 市场在 2025-2027 高速增长（CAGR > 40%），但具体数字来源差异大（$30B-$200B+）
> 2. 框架/SDK 层是市场的一小部分（大部分价值在终端应用与云服务）
> 3. 开源框架的直接商业化困难（竞品多为开源 + 付费平台模式）
> 4. SOM 取决于变现模式（开源免费 vs 平台/企业版）

### 变现模式参考（竞品证据）

| 模式 | 采用者 | 启示 |
|---|---|---|
| 开源 + 托管平台 | LangChain(LangSmith)、LlamaIndex(LlamaCloud)、Dify(Enterprise) | 主流；框架免费，平台收费 |
| 开源 + 企业版 | CrewAI(AMP/Enterprise)、deepset(Cloud) | 企业功能收费 |
| 纯开源 + 周边 | Pydantic AI(Logfire/Gateway) | 框架免费，观测/网关收费 |
| 厂商免费 SDK | OpenAI SDK、Google ADK、Semantic Kernel | 厂商靠云/API 收费，框架获客工具 |

**对 petfishFramework 的含义**：框架层直接变现困难。现实路径是「开源框架获客 + 可选平台/企业版」。

---

## 2. 差异化机会（可执行策略选项）

基于矩阵 + 定位 + SWOT，按优先级排序：

### 🥇 优先级 1：MCP-first 架构 + 生态复用（S1+O2+W1 缓解）

**洞察**：11/11 框架支持 MCP，但无一以 MCP 为**核心抽象**。所有框架把 MCP 作为附加适配器。

**策略**：把框架的核心抽象建立在 MCP 之上 — Agent = MCP 客户端 + 编排逻辑；工具/RAG/数据源 = MCP 服务器。这样新框架**无需自建工具生态**（W1），而是通过 MCP 复用 LangChain(1000+)、LlamaIndex(300+)、CrewAI(75+) 等所有现有生态的工具。

**可执行验证**：
- [ ] 原型：用 MCP 连接 LangChain 工具 + LlamaIndex retriever + 自定义工具，验证「生态复用」可行性
- [ ] 对比：MCP-first vs 适配器附加的架构复杂度差异

### 🥈 优先级 2：吸收 AutoGen/SK 流离用户（O1+T1）

**洞察**：AutoGen（维护模式）+ Semantic Kernel（→MAF）用户面临强制迁移。MAF 1.0 GA（2026-04）但迁移有摩擦。

**策略**：提供 AutoGen/SK → petfishFramework 迁移指南；在 MAF 迁移窗口期（2026-2027）定位为「轻量中立替代方案」。

**可执行验证**：
- [ ] 调研 AutoGen/SK 社区（GitHub issues/Discord）迁移痛点
- [ ] 评估 MAF 的迁移摩擦点（哪些用户会不满 MAF）

### 🥉 优先级 3：简洁但有控制力的中间定位（S4+定位图A）

**洞察**：LangGraph/ADK 强大但陡峭；OpenAI SDK 简单但控制力弱。中间地带（高控制 + 中高抽象）竞争者少。

**策略**：默认 API 简单（5 行起步），高级 API 暴露显式图/状态/checkpoint。参考 Pydantic AI 的「渐进式复杂度」设计。

**可执行验证**：
- [ ] 设计：定义「简单路径」与「高级路径」API 草案
- [ ] 用户测试：让目标用户对比 LangGraph vs petfishFramework 的 hello-world 复杂度

### 优先级 4：中立观测 + 成本控制（O4+O5+S3）

**洞察**：用户不满厂商绑定观测（LangSmith/AMP）；多 Agent token 失控是普遍痛点。

**策略**：采用 OpenTelemetry 标准（厂商中立）；内置 token/cost 预算护栏。

**可执行验证**：
- [ ] 调研用户对 LangSmith 定价/绑定的不满程度
- [ ] 原型：token budget 中断机制

### 优先级 5：中国本土化（O7）

**洞察**：多数框架英文优先；Dify 在中国强采用证明本土化价值。

**策略**：中英双论文档；MCP 镜像/网络优化；本土模型适配（通义/文心/智谱）。

**可执行验证**：
- [ ] 调研中国开发者对现有框架的本地化痛点
- [ ] 评估本土模型 MCP 兼容性

---

## 3. 不做清单（明确放弃的方向）

基于竞品格局，以下方向**不建议**进入（红海或与定位冲突）：

| 方向 | 原因 |
|---|---|
| 可视化工作流平台 | Dify（147k stars）已主导；正面对抗资源不足 |
| 最大工具生态 | LangChain（1000+）壁垒过高；用 MCP 复用更聪明 |
| 厂商绑定 SDK | OpenAI/Google 有分发优势；中立性是我们的卖点 |
| 纯多 Agent 对话 | AutoGen/MAF 已覆盖；确定性不足是已知弱点 |

---

## 4. 下一步验证优先级

| # | 验证项 | 方法 | 优先级 |
|---|---|---|---|
| V1 | MCP-first 架构可行性 | 原型 + 对比实验 | 最高 |
| V2 | AutoGen/SK 用户迁移意愿 | 社区调研 | 高 |
| V3 | 「简洁+控制力」定位需求 | 用户访谈 | 高 |
| V4 | 市场规模数据 | 独立报告验证（Gartner/IDC） | 中 |
| V5 | 多语言维护成本 | JS/TS 原型评估 | 中 |
| V6 | 中国本土化需求 | 开发者调研 | 中 |
