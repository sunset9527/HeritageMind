# HeritageMind — 非遗多智能体知识问答系统

基于多 Agent 协作 + 知识缺口检测 + 交互式图谱的非遗知识保存与传承平台。

## 项目介绍

非物质文化遗产是"正在消失的活知识"——传承人老龄化、技艺失传、知识碎片化。HeritageMind 尝试用多智能体技术做两件事：**结构化地保存非遗知识**，以及**让不同需求的人都能获得合适深度的回答**。

与通用问答系统的关键区别：

| 对比维度 | 通用问答 | HeritageMind |
|----------|---------|-------------|
| 知识边界 | 假装全知，不知道也硬答 | 主动检测知识缺口，诚实告知覆盖程度 |
| 回答深度 | 一刀切 | 好奇者/学习者/研究者三种粒度 |
| 知识整合 | 单一来源 | 三个领域专家Agent多视角融合 |
| 分歧处理 | 无 | 辩论引擎，可视化分歧→达成共识 |
| 叙事风格 | 标准学术口吻 | 可选传承人视角（老匠人口吻） |
| 知识图谱 | 无 | 技艺→材料→工具→传承人→地域多维关联 |

系统以 6 种国家级非遗技艺（景泰蓝、苏绣、龙泉青瓷、宜兴紫砂、芜湖铁画、蜀锦）为示例知识库。

## 系统架构

```
用户提问
    │
    ▼
┌──────────────────────┐
│  调度 Agent           │
│  (意图分析 + 专家分配) │
└──────────┬───────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌──────┐ ┌──────┐ ┌──────┐
│ 技艺  │ │ 历史  │ │ 传承  │
│ 专家  │ │ 专家  │ │ 专家  │
│ Agent │ │ Agent │ │ Agent │
├──────┤ ├──────┤ ├──────┤
│ 工艺  │ │ 起源  │ │ 传承人│
│ 材料  │ │ 演变  │ │ 濒危  │
│ 工具  │ │ 文化  │ │ 保护  │
└──┬───┘ └──┬───┘ └──┬───┘
   │        │        │
   └────────┼────────┘
            ▼
   ┌────────────────┐
   │  意见不一致？    │
   │  → 辩论引擎     │
   │  (多轮辩论收敛)  │
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │  知识融合       │
   │  (多视角整合)    │
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │  知识缺口检测    │
   │  (覆盖程度评估)  │
   ├────────────────┤
   │ 充足 → 生成回答  │
   │ 不足 → 标注缺口  │
   └───────┬────────┘
           ▼
   ┌────────────────┐
   │  多粒度输出     │
   │  (根据用户画像)  │
   ├────────────────┤
   │ 好奇者: 300-500字│
   │ 学习者: 800-1500 │
   │ 研究者: 2000+    │
   └────────────────┘
```

## 功能介绍

### 核心功能

| 功能 | 说明 |
|------|------|
| **多 Agent 问答** | 三领域专家并行检索，调度 Agent 融合多视角结果 |
| **知识缺口检测** | 主动识别知识库覆盖盲区，告知用户"哪里信息不足" |
| **多粒度输出** | 同一问题根据用户画像输出不同深度（300~5000字） |
| **非遗知识图谱** | 46 节点 52 边，6 类节点颜色编码，交互式可视化 |
| **辩论引擎** | 专家意见不一时自动触发辩论，过程可追溯 |
| **传承人叙事** | 可选"老匠人"口吻的技艺讲述风格 |

### 五大技术深度

| 深度点 | 说明 |
|--------|------|
| **多专家 Agent 协作** | 各有知识边界，调度 Agent 按需分配，并行检索 |
| **知识缺口检测** | 识别知识库空白领域，能回答"不知道什么" |
| **多粒度知识服务** | 好奇者/学习者/研究者看到不同深度回答 |
| **非遗知识图谱** | 技艺→材料→工具→传承人→地域多维关联 |
| **传承人视角叙事** | Prompt 工程模拟师徒对话风格 |

## 演示

> 以下为系统实际运行效果截图，点击查看完整交互流程。

<table>
<tr>
<td align="center"><b>多 Agent 问答</b><br><img src="docs/gifs/query.gif" width="400"/><br><i>三专家 Agent 并行检索，气泡展示各专家观点</i></td>
<td align="center"><b>知识图谱</b><br><img src="docs/gifs/graph.gif" width="400"/><br><i>46节点52边非遗知识图谱，6类颜色编码</i></td>
</tr>
<tr>
<td align="center"><b>辩论引擎</b><br><img src="docs/gifs/debate.gif" width="400"/><br><i>专家意见分歧时自动辩论，过程可视化</i></td>
<td align="center"><b>知识缺口</b><br><img src="docs/gifs/gap.gif" width="400"/><br><i>检测知识库覆盖盲区，诚实标注缺口</i></td>
</tr>
</table>

> 💡 如需录制演示 GIF，推荐使用 [ScreenToGif](https://www.screentogif.com/)（Windows 免费开源），录制后放入 `docs/gifs/` 目录。

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| LLM | DeepSeek API | 对话生成、意图分析、缺口检测 |
| Agent 编排 | LangGraph | 多 Agent 并行调度与工作流 |
| 检索框架 | LangChain | 文档加载与检索链 |
| 向量数据库 | ChromaDB | 非遗知识向量存储与语义检索 |
| 关键词检索 | BM25 + jieba | 术语精确匹配 |
| 知识图谱 | NetworkX + pyvis | 图谱建模与交互式可视化 |
| 后端 | FastAPI | RESTful API，8 个端点 |
| 前端 | Streamlit | 60/40 双栏布局，Agent 气泡 |
| 配置 | Pydantic Settings | 集中配置管理 |
| 测试 | pytest | 核心模块测试 |

## 快速开始

### 前置条件

- Python 3.11+
- DeepSeek API Key

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/sunset9527/HeritageMind.git
cd HeritageMind

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx

# 5. 启动服务
# 终端1：启动 API
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动前端
streamlit run main.py
```

访问 http://localhost:8501 进入 Web 界面。

## Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx

# 2. 一键启动
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

访问：
- Web 界面：http://localhost:8501
- API 文档：http://localhost:8000/docs

## API 文档

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 |
| GET | `/health` | 健康检查 |
| POST | `/query` | 非遗知识问答 |
| POST | `/upload` | 上传非遗文档 |
| GET | `/graph/stats` | 知识图谱统计 |
| POST | `/graph/query` | 图谱查询 |
| GET | `/gap-report` | 知识缺口报告 |
| POST | `/switch-profile` | 切换用户画像 |
| GET | `/crafts` | 支持的技艺列表 |
| GET | `/profiles` | 用户画像列表 |

### `/query` — 非遗知识问答

请求：
```json
{
  "question": "景泰蓝的制作流程是什么？",
  "user_profile": "learner",
  "enable_narrative": false,
  "enable_debate": true
}
```

响应：
```json
{
  "query_id": "uuid",
  "answer": "景泰蓝的制作主要包含以下步骤...",
  "agents_used": ["craft_expert", "history_expert"],
  "debate_log": [...],
  "gap_report": {
    "coverage": "good",
    "missing_areas": []
  },
  "knowledge_graph_nodes": 46
}
```

### `/gap-report` — 知识缺口报告

响应：
```json
{
  "gaps": [
    {
      "entity": "龙泉宝剑锻打工艺",
      "current_coverage": "shallow",
      "suggestion": "建议补充锻打工艺的详细技术资料"
    }
  ],
  "overall_coverage": "72%"
}
```

### 用户画像

| 画像 | 说明 | 输出长度 | temperature |
|------|------|---------|-------------|
| curious | 对非遗有初步兴趣 | 300-500 字 | 0.8 |
| learner | 想要系统学习 | 800-1500 字 | 0.4 |
| researcher | 需要深度资料 | 2000+ 字 | 0.1 |

## 项目目录

```
HeritageMind/
├── README.md                     # 项目文档
├── requirements.txt              # Python 依赖
├── config.py                     # Pydantic Settings 配置
├── api.py                        # FastAPI 后端 (8 端点)
├── main.py                       # Streamlit 前端 (60/40 双栏)
├── Dockerfile                    # Docker 多阶段构建
├── docker-compose.yml            # Docker Compose 一键部署
├── .dockerignore                 # Docker 构建排除
├── .env.example                  # 环境变量模板
├── src/
│   ├── agents/                   # Agent 模块
│   │   ├── dispatcher.py         #   调度 Agent（意图分析+专家分配）
│   │   ├── craft_expert.py       #   技艺知识 Agent
│   │   ├── history_expert.py     #   历史文化 Agent
│   │   ├── heritage_expert.py    #   传承现状 Agent
│   │   └── debate_engine.py      #   辩论引擎
│   ├── knowledge/                # 知识模块
│   │   ├── gap_detector.py       #   知识缺口检测
│   │   ├── granularity.py        #   多粒度控制
│   │   └── narrative.py          #   传承人视角叙事
│   ├── graph/                    # 知识图谱
│   │   ├── heritage_graph.py     #   NetworkX 图谱定义
│   │   ├── builder.py            #   图谱构建
│   │   └── visualizer.py         #   pyvis 交互式可视化
│   ├── retrieval/                # 检索模块
│   │   ├── document_loader.py    #   文档加载
│   │   ├── retriever.py          #   多源检索
│   │   ├── vector_retriever.py   #   ChromaDB 向量检索
│   │   ├── bm25_retriever.py     #   BM25 关键词检索
│   │   ├── embeddings.py         #   Embedding 模型配置
│   │   ├── fusion.py             #   结果融合
│   │   ├── query_rewriter.py     #   查询改写
│   │   └── reranker.py           #   CrossEncoder 重排序
│   ├── workflow/                 # LangGraph 工作流
│   │   ├── graph.py              #   主工作流定义
│   │   ├── nodes.py              #   工作流节点
│   │   └── state.py              #   状态定义
│   └── utils/
│       └── prompts.py            #   Prompt 模板管理
├── data/
│   ├── crafts/                   # 6 种非遗技艺文档
│   │   ├── 景泰蓝.txt
│   │   ├── 苏绣.txt
│   │   ├── 龙泉青瓷.txt
│   │   ├── 宜兴紫砂.txt
│   │   ├── 芜湖铁画.txt
│   │   └── 蜀锦.txt
│   ├── heritage_graph.json       # 预构建知识图谱
│   └── user_profiles.json        # 用户画像配置
├── docs/
│   └── blog-heritage-mind.md     # 技术分享文章
└── tests/                        # 测试
    ├── test_dispatcher.py
    ├── test_gap_detector.py
    ├── test_granularity.py
    └── test_heritage_graph.py
```

## Roadmap

### 已完成

- [x] **v1.0** — 三专家 Agent 架构（技艺/历史/传承）+ 调度器
- [x] **v1.1** — 多源检索管线（ChromaDB + BM25 + RRF 融合）
- [x] **v1.2** — 知识缺口检测 GapDetector
- [x] **v1.3** — 多粒度知识服务（好奇者/学习者/研究者）
- [x] **v1.4** — 非遗知识图谱（46 节点 52 边，pyvis 可视化）
- [x] **v1.5** — 传承人视角叙事生成
- [x] **v1.6** — 辩论引擎 DebateEngine（多轮辩论收敛）
- [x] **v1.7** — Streamlit 60/40 双栏 + FastAPI 8 端点
- [x] **v1.8** — Docker Compose 一键部署

### 进行中

- [ ] **v1.9** — 流式输出（SSE）；非遗技艺扩展到 20+ 种

### 规划中

| 版本 | 季度 | 内容 |
|------|------|------|
| **v2.0** | 2026 Q3 | 知识图谱自动化构建（实体关系抽取）；图文混合检索 |
| **v2.1** | 2026 Q4 | 传承人访谈录音转写与知识抽取；多语言支持（中/英/日） |
| **v2.2** | 2027 Q1 | 社区协作编辑；辩论引擎升级（3+ Agent 多方辩论） |
| **v3.0** | 2027 Q2 | 非遗知识图谱开放 API；VR/AR 集成；博物馆数据对接 |

## Release

### v1.8.0 (2026-06-29)

- ✨ Docker Compose 一键部署支持
- 📝 技术博客：多 Agent 辩论机制设计实践
- 📖 README 重构：架构图 / API 文档 / 项目目录

### v1.7.0 (2026-06-20)

- ✨ Streamlit 60/40 双栏布局 + Agent 气泡
- 🐛 修复 pyvis 图谱在 Streamlit 中的渲染问题

### v1.6.0 (2026-06-08)

- ✨ 辩论引擎 DebateEngine（多轮辩论 + 收敛判定）
- 🐛 修复辩论无限循环问题（加入 CONVERGE 指令）

### v1.5.0 (2026-05-25)

- ✨ FastAPI 8 端点 + Lifespan 资源管理
- ✨ 传承人视角叙事生成

### v1.4.0 (2026-05-02)

- ✨ 非遗知识图谱（NetworkX + pyvis）
- ✨ LangGraph 多 Agent 并行工作流

### v1.3.0 (2026-04-18)

- ✨ 多粒度知识服务（3 级用户画像）
- ✨ 知识缺口检测 GapDetector

### v1.2.0 (2026-04-05)

- ✨ 查询改写 + CrossEncoder 重排序
- 🐛 修复"景泰蓝"术语匹配问题

### v1.1.0 (2026-03-24)

- ✨ 三专家 Agent + 调度器
- ✨ ChromaDB + BM25 + RRF 多源检索

### v1.0.0 (2026-03-10)

- 🎉 首次发布
- ✨ 6 种非遗技艺知识库
- ✨ 基础问答 + FastAPI + Streamlit

## License

MIT License
