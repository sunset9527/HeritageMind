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

系统以 23 种国家级非遗技艺为知识库，涵盖陶瓷、丝织、雕刻、印染、纸艺、金属、戏曲 7 大门类。

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
| **非遗知识图谱** | 65 节点 39 边，全中文标签，交互式可视化 |
| **辩论引擎** | 专家意见不一时自动触发辩论，过程可追溯 |
| **传承人叙事** | 可选"老匠人"口吻的技艺讲述风格 |
| **用户系统** | 注册 / 登录 / JWT 鉴权，登录后问答记录自动存档、分页回看 |
| **LLM 可观测性** | Langfuse 全链路追踪，每次 Agent 调用可回放分析 |

### 五大技术深度

| 深度点 | 说明 |
|--------|------|
| **多专家 Agent 协作** | 各有知识边界，调度 Agent 按需分配，并行检索 |
| **知识缺口检测** | 识别知识库空白领域，能回答"不知道什么" |
| **多粒度知识服务** | 好奇者/学习者/研究者看到不同深度回答 |
| **非遗知识图谱** | 技艺→材料→工具→传承人→地域多维关联 |
| **传承人视角叙事** | Prompt 工程模拟师徒对话风格 |

[//]: # (## 演示)

[//]: # ()
[//]: # (> 以下为系统实际运行效果截图，点击查看完整交互流程。)

[//]: # ()
[//]: # (<table>)

[//]: # (<tr>)

[//]: # (<td align="center"><b>多 Agent 问答</b><br><img src="docs/gifs/query.gif" width="400"/><br><i>三专家 Agent 并行检索，气泡展示各专家观点</i></td>)

[//]: # (<td align="center"><b>知识图谱</b><br><img src="docs/gifs/graph.gif" width="400"/><br><i>46节点52边非遗知识图谱，6类颜色编码</i></td>)

[//]: # (</tr>)

[//]: # (<tr>)

[//]: # (<td align="center"><b>辩论引擎</b><br><img src="docs/gifs/debate.gif" width="400"/><br><i>专家意见分歧时自动辩论，过程可视化</i></td>)

[//]: # (<td align="center"><b>知识缺口</b><br><img src="docs/gifs/gap.gif" width="400"/><br><i>检测知识库覆盖盲区，诚实标注缺口</i></td>)

[//]: # (</tr>)

[//]: # (</table>)

[//]: # ()
[//]: # (> 💡 如需录制演示 GIF，推荐使用 [ScreenToGif]&#40;https://www.screentogif.com/&#41;（Windows 免费开源），录制后放入 `docs/gifs/` 目录。)

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| LLM | DeepSeek API | 对话生成、意图分析、缺口检测 |
| Agent 编排 | LangGraph | 多 Agent 并行调度与工作流 |
| 检索框架 | LangChain | 文档加载与检索链 |
| 向量数据库 | ChromaDB | 非遗知识向量存储与语义检索 |
| 关键词检索 | BM25 + jieba | 术语精确匹配 |
| 知识图谱 | NetworkX + pyvis | 图谱建模与交互式可视化 |
| 后端 | FastAPI | RESTful API，18 个端点 |
| 前端 | Vue 3 + TypeScript + Element Plus + Tailwind | SPA 应用，Streamlit 保留可回退 |
| 状态管理 | Pinia | auth / chat / graph / settings 四模块 |
| 路由 | Vue Router 4 | 首页 / 问答 / 图谱 / 设置 / 登录 / 注册 |
| 数据库 | SQLAlchemy 2.0 + Alembic | ORM 建模与版本化迁移 |
| 数据存储 | SQLite / PostgreSQL 16 | 开发用 SQLite，生产用 PostgreSQL |
| 认证 | python-jose + passlib[bcrypt] | JWT 签发校验与密码哈希 |
| 可观测性 | Langfuse | LLM 调用全链路追踪 |
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

# 4. 配置环境变量
cp .env.example .env
# 必填：DEEPSEEK_API_KEY=sk-xxx
# 可选：DATABASE_URL（默认 SQLite）/ JWT_SECRET_KEY / LANGFUSE_*（详见 .env.example）

# 5. 初始化数据库（可选）
# 开发环境启动 API 时会自动建表；生产环境建议用 Alembic 迁移
alembic upgrade head

# 6. 启动服务
# 终端1：启动 API
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动 Vue 3 前端（推荐）
cd frontend && npm install && npx vite --host 0.0.0.0

# 或启动 Streamlit 前端（保留）
streamlit run main.py
```

访问 http://localhost:5173 进入 Vue 3 界面（Streamlit：http://localhost:8501）。

## Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx

# 2. 一键启动（PostgreSQL 16 + API + Web 三个服务）
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

访问：
- Vue 3 界面：http://localhost:5173（`docker compose --profile vue up`）
- Streamlit 界面：http://localhost:8501（默认）
- API 文档：http://localhost:8000/docs
- PostgreSQL：localhost:5432（用户/库名均为 heritagemind）

## API 文档

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 |
| GET | `/health` | 健康检查 |
| POST | `/query` | 非遗知识问答（登录后自动存档历史） |
| POST | `/query/simple` | 简化版问答（表单提交） |
| POST | `/upload` | 上传非遗文档 |
| GET | `/graph/stats` | 知识图谱统计 |
| GET | `/graph/visualize` | 交互式图谱 HTML |
| GET | `/graph/subgraph/{craft_name}` | 技艺子图查询 |
| GET | `/gap-report` | 知识缺口报告 |
| POST | `/switch-profile` | 切换用户画像 |
| GET | `/crafts` | 支持的技艺列表 |
| GET | `/profiles` | 用户画像列表 |
| GET | `/documents/summary` | 文档库摘要 |
| POST | `/auth/register` | 用户注册（返回 JWT） |
| POST | `/auth/login` | 用户登录（OAuth2 密码流） |
| GET | `/auth/me` | 当前用户信息 🔒 |
| GET | `/chat/history` | 聊天历史列表（分页） 🔒 |
| GET | `/chat/history/{chat_id}` | 单条聊天详情 🔒 |

> 🔒 需在请求头携带 `Authorization: Bearer <access_token>`

### `/query` — 非遗知识问答

请求：
```json
{
  "question": "景泰蓝的制作流程是什么？",
  "user_profile": "learner",
  "include_narrative": false,
  "craft_filter": null
}
```

> 携带 `Authorization: Bearer <token>` 调用时，问答记录会自动存档到聊天历史。

响应：
```json
{
  "question": "景泰蓝的制作流程是什么？",
  "answer": "景泰蓝的制作主要包含以下步骤...",
  "user_profile": "learner",
  "source_agents": [{"id": "craft_expert"}, {"id": "history_expert"}],
  "has_gaps": false,
  "gap_report": "",
  "reading_time": 3,
  "metadata": {}
}
```

### `/gap-report` — 知识缺口报告

响应：
```json
{
  "coverage_level": "partial",
  "relevant_documents": 3,
  "coverage_score": 0.62,
  "gaps": [
    {
      "aspect": "工艺细节",
      "description": "锻打工艺的详细技术资料覆盖不足",
      "suggestion": "建议补充相关技术文档"
    }
  ],
  "can_answer": true,
  "suggestions": ["龙泉宝剑 锻打 工序"],
  "report": "本次回答基于 3 篇相关文档..."
}
```

### `/auth/*` 与 `/chat/*` — 认证与聊天历史

```bash
# 注册（返回 JWT access_token）
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret123"}'

# 登录（OAuth2 密码流，表单提交）
curl -X POST http://localhost:8000/auth/login \
  -d "username=alice&password=secret123"

# 携带 token 查询聊天历史
curl "http://localhost:8000/chat/history?limit=20&offset=0" \
  -H "Authorization: Bearer <access_token>"
```

- JWT 默认 60 分钟过期（`JWT_EXPIRE_MINUTES` 可配置），签名算法 HS256
- 密码使用 bcrypt 哈希存储，登录失败返回 401
- 聊天历史按 user_id 隔离，仅本人可见

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
├── api.py                        # FastAPI 后端 (18 端点)
├── main.py                       # Streamlit 首页 Dashboard
├── ui_components.py              # Streamlit 公共组件（CSS/会话/API 客户端）
├── pages/                        # Streamlit 多页面
│   ├── 1_Chat.py                 #   问答页（登录/注册 + 历史记录）
│   ├── 2_Graph.py                #   知识图谱页
│   └── 3_Settings.py             #   设置页
├── alembic.ini                   # Alembic 迁移配置
├── migrations/                   # 数据库迁移脚本
│   └── versions/
│       └── 001_init_users_chat.py  # users + chat_history 建表
├── Dockerfile                    # Docker 多阶段构建
├── docker-compose.yml            # Docker Compose（PostgreSQL + API + Streamlit + Vue + Nginx）
├── .dockerignore                 # Docker 构建排除
├── .env.example                  # 环境变量模板
├── frontend/                     # Vue 3 前端（v1.0.3+）
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile                # Node build → Nginx serve
│   ├── nginx.conf
│   └── src/
│       ├── main.ts, App.vue
│       ├── router/, stores/, api/, types/
│       ├── views/                # Dashboard/Chat/Graph/Settings/Login/Register
│       └── components/           # layout/chat/dashboard/graph/settings
├── src/
│   ├── database.py               # SQLAlchemy 引擎与会话管理
│   ├── deps.py                   # FastAPI 依赖注入（get_db / get_current_user）
│   ├── models/                   # ORM 模型
│   │   ├── user.py               #   用户表
│   │   └── chat.py               #   聊天历史表
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── user.py               #   注册/登录/Token
│   │   └── chat.py               #   聊天历史
│   ├── services/                 # 业务服务层
│   │   ├── auth.py               #   注册/登录/JWT 签发
│   │   └── chat.py               #   聊天历史存取
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
│       ├── llm.py                #   LLM 统一工厂（Langfuse 追踪注入）
│       └── prompts.py            #   Prompt 模板管理
├── data/
│   ├── crafts/                   # 23 种非遗技艺文档（55,000 字）
│   │   ├── 景泰蓝.txt ... 蜀锦.txt       # 6 种原始技艺
│   │   ├── 剪纸.txt ... 壮锦.txt         # 11 种新增技艺
│   │   └── 景德镇瓷器.txt ... 京剧.txt   # 6 种新增技艺
│   ├── heritage.db               # SQLite 数据库（开发环境）
│   ├── heritage_graph.json       # 预构建知识图谱
│   └── user_profiles.json        # 用户画像配置
└── tests/                        # 测试
    ├── test_dispatcher.py
    ├── test_gap_detector.py
    ├── test_granularity.py
    └── test_heritage_graph.py
```

## Release

### v1.11.0 (2026-07-25)

- ✨ 知识图谱全中文化：节点标签、悬浮提示、属性键值全部中文化
- 🐛 修复图谱筛选 500 错误
- 🐛 修复 pyvis `add_node`/`add_edge` 参数名兼容 + Jinja2 tojson Unicode 转义
- ✨ 图谱节点属性键值英转中（region→产地，period→时期 等）

### v1.10.0 (2026-07-22~23)

- ✨ 知识库从 6 种扩展到 23 种非遗技艺（55,000 字）
- ✨ Vue 3 前端全栈重写（Vite + TypeScript + Pinia + Element Plus + Tailwind）
- ✨ 百度真实图片轮播 + 马山正行楷毛笔字体
- 🐛 修复中文分词检索 bug（空格切分→jieba 分词）
- ⚡ 缺口检测快速路径（90%+ 场景跳过 LLM 调用）
- ⚡ 占位符 API Key 503 立即返回（不再超时卡住）
- 🐛 缺口报告优化（部分覆盖时仅显示一行提示）
- ✨ 文档加载器改为自动扫描目录

### v1.9.0 (2026-07-17)

- ✨ 用户系统：注册 / 登录 / JWT 认证（OAuth2 密码流 + bcrypt 密码哈希）
- ✨ 聊天历史持久化：登录用户问答自动存档，支持分页查询与详情回看
- ✨ 数据库层：SQLAlchemy 2.0 + Alembic 迁移，SQLite（开发）/ PostgreSQL（生产）双支持
- ✨ Langfuse LLM 可观测性：统一 LLM 工厂 `create_llm()`，Agent 调用全链路追踪
- ♻️ Streamlit 多页面重构：首页 Dashboard + Chat / Graph / Settings 三页面，公共组件抽离 ui_components.py
- 🐳 docker-compose 新增 PostgreSQL 16 服务（健康检查 + 启动依赖编排）

### v1.8.0 (2026-07-2)

- ✨ Docker Compose 一键部署支持
- 📝 技术博客：多 Agent 辩论机制设计实践
- 📖 README 重构：架构图 / API 文档 / 项目目录

### v1.7.0 (2026-06-20)

- ✨ Streamlit 60/40 双栏布局 + Agent 气泡
- 🐛 修复 pyvis 图谱在 Streamlit 中的渲染问题

### v1.6.0 (2026-06-08)

- ✨ 辩论引擎 DebateEngine（多轮辩论 + 收敛判定）
- 🐛 修复辩论无限循环问题（加入 CONVERGE 指令）

### v1.5.0 (2026-04-25)

- ✨ FastAPI 8 端点 + Lifespan 资源管理
- ✨ 传承人视角叙事生成

### v1.4.0 (2026-03-02)

- ✨ 非遗知识图谱（NetworkX + pyvis）
- ✨ LangGraph 多 Agent 并行工作流

### v1.3.0 (2025-08-18)

- ✨ 多粒度知识服务（3 级用户画像）
- ✨ 知识缺口检测 GapDetector

### v1.2.0 (2025-04-05)

- ✨ 查询改写 + CrossEncoder 重排序
- 🐛 修复"景泰蓝"术语匹配问题

### v1.1.0 (2025-03-24)

- ✨ 三专家 Agent + 调度器
- ✨ ChromaDB + BM25 + RRF 多源检索

### v1.0.0 (2025-03-10)

- 🎉 首次发布
- ✨ 6 种非遗技艺知识库
- ✨ 基础问答 + FastAPI + Streamlit


