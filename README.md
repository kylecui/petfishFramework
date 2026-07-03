# petfishFramework

> 通用 AI Agent 框架 — 让用户轻松对接各种模型，便捷接入 RAG / MCP / 自定义工具与文档

## 概述

petfishFramework 是一个通用 AI Agent 框架，目标是降低构建 AI Agent 应用的门槛：

- **模型无关**：统一接口对接各类 LLM（OpenAI、Anthropic、本地模型等）
- **即插即用**：用户可轻松接入自己的 RAG、MCP 服务、文档和工具
- **可扩展**：清晰的模块边界，支持自定义能力扩展

## 当前阶段

🚧 **前期调研中** — 同类产品分析 + 学界方法研究 → 核心能力抽象 → 设计 → 开发 → QA → Alpha 内测

## 目录结构

| 目录 | 用途 |
|---|---|
| `src/` | 框架核心代码 |
| `tests/` | 测试（与设计同步，TDD） |
| `docs/` | 架构文档、API 文档、开发文档 |
| `examples/` | 使用示例 |
| `configs/` | 配置模板 |
| `mcp/` | MCP 集成模板 |
| `qa/` | QA 检查清单 |
| `scripts/` | 工具脚本 |
| `outputs/` | 生成输出（与源码分离） |
| `.opencode/` | AI agent 技能与配置 |

## 开发环境

待初始化（Python + uv）。

## 路线图

1. ✅ 项目骨架初始化（code profile）
2. 🔄 同类产品调研 + 学界方法研究
3. ⬜ 核心能力与模块抽象
4. ⬜ 详细设计 + 同步测试用例（TDD）
5. ⬜ 框架开发与测试
6. ⬜ QA / QC
7. ⬜ Alpha 内测

详见 `AGENTS.md` 和 `tasks/backlog.md`。
