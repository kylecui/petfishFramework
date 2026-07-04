# Positioning Map — AI Agent Frameworks

> 基于 `competitor-matrix.md` 的证据。定位轴选择理由附后。

## 定位图 A：抽象层级 × 控制力

```
高控制力（显式图/状态）
        ↑
        │   Haystack          LangGraph
        │                              Google ADK
        │   Semantic Kernel
        │
        │            LlamaIndex        AutoGen(Core)
        │
        │   Pydantic AI     CrewAI
        │
        │            LangChain
        │                     OpenAI Agents SDK
        │   Dify (可视化)
        │
低抽象 ←───────────────────────────────────→ 高抽象（少代码/低门槛）
        │
        │                           简单但少控制
        ↓
低控制力（隐式/黑盒）
```

**轴解释**：
- **X 轴（抽象层级）**：左 = 库/SDK（用户写更多代码）；右 = 平台/高抽象（少代码/可视化）。证据：Dify 是可视化平台（最右）；OpenAI SDK 极简原语（偏右）；Haystack/LangGraph 显式接线（偏左）。
- **Y 轴（控制力）**：上 = 显式图/状态/确定性控制强；下 = 隐式编排/黑盒。证据：LangGraph/Haystack/ADK 提供显式图 + checkpoint（上）；OpenAI SDK 极简少控制点（下）。

**petfishFramework 目标位置**：**右上象限中部** — 高控制力（显式编排）+ 中-高抽象（比 LangGraph 简单，比 OpenAI SDK 有控制力）。即「简洁但有控制力」的空白带。

---

## 定位图 B：模型无关性 × 生态开放度

```
高生态开放度（中立/可插拔）
        ↑
        │   LangChain         LlamaIndex
        │                              Pydantic AI
        │   CrewAI
        │                              Haystack
        │
        │   ─────────────────────────────────
        │   Semantic Kernel          Google ADK
        │                              OpenAI Agents SDK
        │   Dify（许可受限）
        │   AutoGen（维护模式）
        │
低模型 ←───────────────────────────────────→ 高模型无关
无关性                              无关性
        │
        ↓
低开放度（厂商引力/锁定）
```

**轴解释**：
- **X 轴（模型无关性）**：右 = 真正多供应商无锁定；左 = 厂商引力。证据：Pydantic AI 最无关（右）；OpenAI SDK/Google ADK 有厂商引力（左）；Dify 许可受限拉低开放度。
- **Y 轴（生态开放度）**：上 = 中立许可 + 解耦观测 + 可插拔；下 = 厂商平台绑定。证据：LangChain/LlamaIndex MIT + 大生态（上）；Dify 修改版许可 + 自有平台（下）。

**petfishFramework 目标位置**：**右上方** — 高模型无关 + 高生态开放（MIT + 厂商中立观测 + 可插拔 RAG/工具）。

---

## 定位图 C：形态 × 目标用户

```
平台/产品（可视化/托管）
        ↑
        │                    Dify
        │
        │                    CrewAI (AMP)
        │
        │   ─────────────────────────────────
        │   LangChain (+LangSmith)
        │   LlamaIndex (+LlamaCloud)
        │
        │   Haystack         AutoGen
        │   Semantic Kernel  Google ADK
        │   Pydantic AI      OpenAI SDK
        │
库/SDK（嵌入式代码）           LangGraph
        │
        ↓
库/SDK（嵌入式代码）
```

**轴解释**：
- **Y 轴（形态）**：上 = 平台/产品（含托管/可视化）；下 = 嵌入式库/SDK。证据：Dify 是完整平台（最上）；OpenAI SDK/Pydantic AI/LangGraph 是纯库（下）。
- Dify 与 CrewAI(AMP) 偏平台；其余偏库。

**petfishFramework 目标位置**：**底部库/SDK 区** — 轻量嵌入式框架，可选可视化层（不强制平台形态）。

---

## 定位结论

petfishFramework 的差异化定位是三条轴的交集：

1. **高控制力 + 中高抽象**（图 A 右上中部）— 比 LangGraph 简单，比 OpenAI SDK 有控制力
2. **高模型无关 + 高生态开放**（图 B 右上）— 真正中立，MIT，解耦观测
3. **库/SDK 形态**（图 C 底部）— 轻量嵌入，不强制平台

这个定位带的直接竞争者极少 — 最接近的是 Pydantic AI（但 Python-only + 无内置 RAG）和 Haystack（但 Python-only + 模型抽象弱）。
