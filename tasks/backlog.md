# Backlog

## 当前阶段：前期调研

> 工作流：调研 → 核心抽象 → 设计（同步测试用例）→ 开发 → QA/QC → Alpha 内测

## To Do

### Phase 1 — 调研（当前）
- [ ] **同类 AI Agent 框架竞品调研**：LangChain / LlamaIndex / AutoGen / CrewAI / Semantic Kernel / Dify 等 — 分析架构模式、模型对接方式、RAG/工具扩展机制、优缺点
- [ ] **学界先进方法文献综述**：agent 架构、RAG 技术、tool-use / function-calling、planning 与 reasoning — 识别优于现有工程产品的学术方法
- [ ] **调研综合结论**：竞品对比矩阵 + 学界方法差距分析 → 输出可追溯的 evidence ledger

### Phase 2 — 核心抽象
- [ ] **抽象 petfishFramework 核心能力与模块边界**：基于调研结论定义框架的核心抽象（模型层、RAG 层、工具/MCP 层、编排层等）

### Phase 3 — 设计 + 测试
- [ ] **详细设计文档**：各模块接口与交互（`docs/architecture.md`, `docs/api.md`）
- [ ] **同步测试用例**：设计阶段即产出测试用例（TDD，`tests/`）

### Phase 4 — 开发
- [ ] 框架开发（`src/`）

### Phase 5 — QA
- [ ] QA / QC（`qa/`）

### Phase 6 — 发布
- [ ] Alpha 内测
