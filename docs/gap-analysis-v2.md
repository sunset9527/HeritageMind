# V1 → V2 差距分析

> 对比时间：2026-06-20 | 目标：求职展示级多智能体非遗问答系统

---

## ✅ V1 已具备（保持不变）

| 模块 | 评价 |
|------|------|
| 三智能体 + Dispatcher | 架构清晰，Agent 职责划分合理 |
| 6 种技艺知识库 | 数据质量好，覆盖完整 |
| 知识图谱（36 节点 41 边） | NetworkX 实现完善，查询方法齐全 |
| 粒度适配（3 种画像） | 好奇者/学习者/研究者分级合理 |
| 叙事模式（匠人口吻） | 独特卖点，保留增强 |
| 知识缺口检测 | 差异化功能，保留 |
| LangGraph 工作流 | 框架使用正确 |
| 42 个测试用例 | 覆盖核心逻辑 |

---

## 🔴 P0：检索从"玩具级"升级到"生产级"

### 问题

当前 `retriever.py` 只用 Python `in` 操作符做关键词匹配：

```python
# 当前实现（V1）
for doc in self.documents:
    for keyword in keywords:
        if keyword in doc.content:  # 字符串包含检查
            scored_docs.append((doc_id, 1.0))
```

ChromaDB 在 `requirements.txt` 里但代码中从未 import。

### 需要新增

| 组件 | 文件 | 工作量 |
|------|------|--------|
| Embedding 管理 | `src/retrieval/embeddings.py` | 1 天 |
| BM25 检索器 | `src/retrieval/bm25_retriever.py` | 1 天 |
| ChromaDB 向量检索 | `src/retrieval/vector_retriever.py` | 1 天 |
| RRF 融合 | `src/retrieval/fusion.py` | 0.5 天 |
| BGE-Reranker | `src/retrieval/reranker.py` | 0.5 天 |
| Query Rewriting | `src/retrieval/query_rewriter.py` | 1 天 |
| **小计** | | **5 天** |

---

## 🔴 P0：新增加辩论引擎

### 问题

V1 的 Agent 之间没有直接对话——Dispatcher 收集各自回答后融合，是"并行发言→汇总"模式，不是真正的"辩论/协作"。

### 需要新增

| 组件 | 文件 | 工作量 |
|------|------|--------|
| 辩论数据结构 | `src/agents/debate_engine.py` | 0.5 天 |
| 辩论触发判断（3 种模式） | 同上 | 1 天 |
| 辩论轮次管理（Round 1→2→3→4） | 同上 | 1.5 天 |
| Agent 间上下文传递 | 同上 | 1 天 |
| 辩论结果结构化输出 | 同上 | 0.5 天 |
| 融合辩论结果 | 修改 `src/agents/dispatcher.py` | 1 天 |
| **小计** | | **5.5 天** |

### 关键修改

```python
# V1: 并行收集
for agent in agents:
    responses.append(agent.answer(question))
fused = dispatcher.fuse(responses)

# V2: 辩论链
debate = DebateEngine(agents=[craft, history, heritage])
debate.add_round(role="主答", agent=craft, prompt=question)
debate.add_round(role="补充", agent=heritage, context=debate.history)
debate.add_round(role="历史视角", agent=history, context=debate.history)
debate.add_round(role="回应", agent=craft, context=debate.history)
result = debate.synthesize()
```

---

## 🟠 P1：知识图谱可视化

### 问题

V1 图谱查询只返回 JSON 文本，没有可视化渲染。

### 需要修改/新增

| 组件 | 文件 | 工作量 |
|------|------|--------|
| pyvis 图谱渲染 | 新增 `src/graph/visualizer.py` | 1 天 |
| 节点样式配置 | 同上 | 0.5 天 |
| Streamlit 嵌入 | 修改 `main.py` | 0.5 天 |
| 节点点击交互 | 修改 `main.py` | 1 天 |
| **小计** | | **3 天** |

---

## 🟠 P1：UI 全面升级

### 问题

V1 UI 是基础 Streamlit 布局（侧边栏 + 对话 + 几个 st.metric），没有展示多智能体协作的优势。

### 需要修改

| 改动 | 说明 | 工作量 |
|------|------|--------|
| 60/40 双栏布局 | 左：对话区，右：增强面板 | 1 天 |
| Agent 发言气泡 | 不同 Agent 不同颜色/头像 | 1 天 |
| 辩论时间线组件 | 右侧面板可视化辩论过程 | 1.5 天 |
| 图谱探索 Tab | 右侧面板切换至图谱视图 | 1 天 |
| 自定义 CSS | 暖棕/古铜非遗主题 | 1 天 |
| **小计** | | **5.5 天** |

---

## 🔵 P2：数据 & 配置

| 改动 | 说明 | 工作量 |
|------|------|--------|
| 补充 `.env.example` | 当前缺失 | 0.5 天 |
| 确认 DeepSeek Embedding | 或切换到本地 BGE 模型 | 0.5 天 |
| 补充技艺数据 | 可选：增加到 10 种技艺 | 2 天 |
| 图谱数据增强 | 添加更多传承人、工具节点 | 1 天 |

---

## 📊 总工时估算

| 优先级 | 模块 | 预估工时 |
|--------|------|---------|
| 🔴 P0 | 检索升级 | 5 天 |
| 🔴 P0 | 辩论引擎 | 5.5 天 |
| 🟠 P1 | 图谱可视化 | 3 天 |
| 🟠 P1 | UI 升级 | 5.5 天 |
| 🔵 P2 | 数据 & 配置 | 4 天 |
| **合计** | | **23 天（约 5 周）** |

---

## 🆚 V1 vs V2 对比总览

| 维度 | V1（现有） | V2（目标） |
|------|-----------|-----------|
| 智能体协作 | 并行发言 → 汇总 | 多轮辩论 → 补充质疑回应 |
| 检索 | 关键词 `in` 匹配 | BM25 + 向量 + 图谱 + RRF + Reranker |
| 图谱 | JSON API 查询 | 交互式可视化探索 |
| UI | 基础 Streamlit | 60/40 双栏 + 辩论时间线 + 气泡 |
| 检索精度 | ~30% | ~85%+ |
| 演示冲击力 | 中等 | 强 |
| Agent 对话感 | 无 | 强（"像三个专家在讨论"） |
