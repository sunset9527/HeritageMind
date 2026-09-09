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
| Embedding | 智谱 API (embedding-2) / BAAI BGE | 文档向量化，API优先+本地降级 |
| Agent 编排 | LangGraph | 多 Agent 调度与工作流 |
| 重排序 | BAAI/bge-reranker-base | CrossEncoder 逐对精排 |
| 检索框架 | LangChain | 文档加载与检索链 |
| 向量数据库 | ChromaDB | 非遗知识向量存储与语义检索 |
| 关键词检索 | BM25 + jieba | 术语精确匹配 |
| 知识图谱 | NetworkX + pyvis | 65 节点全中文可视化 |
| 后端 | FastAPI | RESTful API，30+ 端点 |
| 前端 | Vue 3 + TypeScript + Element Plus + Tailwind | SPA 应用 |
| 状态管理 | Pinia | auth / chat / graph / settings 四模块 |
| 路由 | Vue Router 4 | 首页 / 问答 / 图谱 / 媒体 / 设置 / 登录 / 注册 |
| 数据库 | MySQL 8.4 + SQLAlchemy 2.0 + Alembic | 5 张表，utf8mb4 |
| 多媒体 | 本地文件系统 | 图片/音频上传与存储 |
| 音频转写 | faster-whisper (本地 CTranslate2 small) | 语音转文字（PyAV 解码，无需系统 ffmpeg） |
| 音频检索 | ChromaDB（独立 audio collection） | 转写文本分块向量检索，`GET /search/audio` 按文字搜音频 |
| 缓存/队列 | Redis 8 + redis-py | 热门问答缓存（Redis 优先，进程内 LRU 兜底）+ 音频转写任务队列 |
| 认证 | python-jose + passlib[bcrypt] | JWT 签发校验与密码哈希 |
| 可观测性 | Langfuse | LLM 调用全链路追踪 |
| 配置 | Pydantic Settings | 集中配置管理 |
| CI/CD | GitHub Actions | ruff lint + pytest |
| 测试 | pytest | 检索模块 7 用例 |

## 文档解析（PDF/扫描件 OCR）

非遗资料多为扫描件/图片 PDF，`src/services/document_parser.py` 的 PDF 解析已升级为双通道：

- **文本层**：pymupdf(fitz) 提取，数字原生 PDF 直接出字
- **扫描页 OCR 兜底**：页文本字符数 < 20 → 渲染位图 → RapidOCR 中文识别（新模块 `src/services/pdf_parser.py`）

`parse_document(bytes, filename, mime)` 对上传的 PDF（含扫描件）统一返回纯文本，供知识库入库，接口签名不变。

```bash
python -m pytest tests/test_pdf_parser.py -v
```

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
| GET | `/prompts` | Prompt 模板列表 |
| POST | `/prompts` | 创建 Prompt 模板 |
| GET | `/prompts/{id}` | 获取 Prompt 模板 |
| PUT | `/prompts/{id}` | 更新 Prompt 模板（版本号+1） |
| DELETE | `/prompts/{id}` | 删除 Prompt 模板 |
| GET | `/config` | 服务器默认 LLM 配置 |
| POST | `/media/upload` | 上传图片/音频 |
| GET | `/media/list` | 媒体列表（可按技艺/类型筛选） |
| DELETE | `/media/{id}` | 删除媒体文件 |
| POST | `/favorites` | 添加收藏 🔒 |
| GET | `/favorites` | 收藏列表 🔒 |
| DELETE | `/favorites/{id}` | 删除收藏 🔒 |
| GET | `/search/image` | 文搜图 |
| POST | `/search/similar` | 以图搜图 |
| POST | `/search/index-images` | 重建图片向量索引 |
| GET | `/search/audio` | 文搜音频（按文字命中已转写音频，`?q=&top_k=&craft_name=`） |
| POST | `/search/audio/index` | 重建音频转写向量索引 |
| GET | `/media/{id}/transcript` | 查询音频转写状态（UPLOADED→TRANSCRIBING→INDEXED/FAILED，轮询用） |
| POST | `/media/{id}/transcribe` | 手动触发/重试音频转写 |
| GET | `/knowledge/categories` | 知识库分类 |
| POST | `/documents/upload` | 上传文档（PDF/Word/MD 自动解析） |

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
├── .github/workflows/ci.yml      # GitHub Actions CI（ruff + pytest）
├── migrations/                   # 数据库迁移脚本
│   └── versions/
│       ├── 001_init_users_chat.py  # users + chat_history 建表
│       └── 002_add_prompts.py      # prompts 表
├── tests/                        # 测试
│   └── test_retrieval.py          #   检索模块测试
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
│   │   ├── chat.py               #   聊天历史表
│   │   └── prompt.py             #   Prompt 模板表
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── user.py               #   注册/登录/Token
│   │   ├── chat.py               #   聊天历史
│   │   └── prompt.py             #   Prompt CRUD
│   ├── services/                 # 业务服务层
│   │   ├── auth.py               #   注册/登录/JWT 签发
│   │   ├── chat.py               #   聊天历史存取
│   │   └── prompt.py             #   Prompt 管理 + 热加载
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
│   │   └── reranker.py           #   CrossEncoder 重排序（逐对精排 + 规则降级）
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

> 以下为合并后的大版本。细碎小版本记录见 git history。

### v2.5 — MySQL 会话记忆与 Vue 多轮对话（2026-08-12）

> 保持既有 **MySQL + Vue 3** 技术栈：不迁移 PostgreSQL，也不引入 Streamlit。由于当前工作流会在单个 HTTP 请求内完整执行，本版本持久化的是跨轮对话语义，而非体积较大的逐节点 LangGraph checkpoint。

- 🧠 **跨轮会话记忆**：新增 `chat_sessions`，并为 `chat_history` 关联 `session_id`；登录用户首次 `/query` 自动建会话，后续携带 `session_id` 即会加载最近 4 轮、最多 2,400 字的上下文。上下文同时进入路由分析、检索改写与最终回答生成，支持“介绍昆曲”后继续追问“它有哪些代表剧目？”
- 🔐 **会话隔离与缓存安全**：所有会话读取均同时校验 `session_id + user_id`，越权按不存在处理；带会话的问答不走热门问答缓存，避免不同上下文因相同问题命中错误答案；记忆读写失败则降级为空上下文，不中断本轮回答。
- 🎯 **用户偏好学习**：新增 `user_preferences`，只从项目内 23 种标准技艺与用户显式选择的学习深度学习偏好；保留最多 5 个技艺，不从 LLM 生成文本中写入偏好。本轮显式画像和技艺筛选始终优先于历史偏好。
- 🧭 **会话 API**：新增 `GET /chat/sessions`、`POST /chat/sessions`、`GET /chat/sessions/{session_id}/messages`；`/query` 与 `/query/stream` 均支持可选 `session_id`，响应 metadata 返回本轮会话 ID。
- 🎨 **Vue 交互**：Pinia 维护 `activeSessionId`；聊天侧栏支持“继续上次对话”、加载历史轮次和“新对话”，首轮请求自动回填服务端创建的会话 ID。
- 🗄️ **数据库迁移**：新增 Alembic `003_add_v15_session_memory.py`，创建 `chat_sessions`、`user_preferences` 并向 `chat_history` 增加 `session_id`。已有 MySQL 环境升级前执行 `python -m alembic upgrade head`。
- ✅ **验证**：新增会话归属、上下文截断/顺序、偏好白名单、工作流 thread 配置、带指代的检索改写等离线测试；全量 `python -m pytest tests/ --basetemp <可写临时目录>` **145 通过、1 跳过**。


### v2.4 核心 Agent 主线 — Router 工具化 · 检索改写接线 · Planner 大纲（2026-08-09）

> 本条目对应开发路线图 `agent非遗.md` 的 **v1.4「核心 Agent 主线」**里程碑，实现时叠加于当时最新产品版本（v2.3）之上；与下文产品历史版本中的 `v1.4 (2026-03-02) 非遗知识图谱` 属于不同编号体系，请勿混淆。

- 🧭 Router 原生 function-calling：路由分析改走 `route_question` 工具（裸 dict schema 固定工具名、枚举内嵌引导），三分支降级 —— 原生 tool_calls → content 口述 JSON（兼容 ```json 剥壳）→ 关键词回退；`DISPATCHER_SYSTEM_PROMPT` 现真正以 SystemMessage 进 LLM，不再要求"提示词输出 JSON + 手解析"
- 🔀 检索 Query 改写接线（规则模式）：`select_best_query` 选出最佳候选写入 `state.search_query`；dispatch 层级聚合检索、缺口检测与三专家 `process(question, context, search_query=...)` 统一消费改写后 query。改写只作用于检索，专家识别技艺名 / 生成仍用原始 question。开关：`query_rewriting_enabled`（接线总闸）/ `query_rewriting_use_llm`（LLM 候选，默认关，完整 LLM 改写版留待 v1.6）
- 🗂️ Planner 大纲式分解：复杂问题（complex 或 ≥2 专家）在分派前经 `create_plan` 产出 3-6 个必须覆盖子方面 + 组织大纲，注入融合提示词与生成粒度适配（`context`），约束回答结构而不触发额外检索；`planner_enabled` 可一键关回旧路径，plan 失败自动跳过（None，最安全降级）
- 🧯 修复请求级 override 泄漏：`/query` 与 `/query/stream` 对 `set_request_override` 包裹 try/finally，异常 / 客户端中断 / 正常 [DONE] 均收尾 `clear_request_override()`，杜绝一次带 `X-API-Key/Base/Model` 的请求污染后续无头请求
- ✅ 验证：全量 `python -m pytest tests/` 84 通过（新增 router 工具调用 / 改写接线 / Planner 接线 3 组共 39 例）；检索 eval 基线无回归 —— HM-100 三路 Hit@5 96/96（100%），craft-boost 含技艺名全集 Hit@1 62/62（100%）

### v2.3 — 检索效果实测(2026-08-02)

- 📊 自建 94 条领域评测集（40 直问 + 54 推理难题，难题不含技艺名称），Hit@5 三路均 100%（BM25 / 向量 BGE-M3 / RRF 混合）
- 🔍 评测脚本 `eval_retrieval_hm100.py` 可复现；6 条覆盖缺口 query 验证 gap_detector 价值

### v2.2 — 多模态平台（2026-07-26~28）

- ✨ 图片/音频上传：POST /media/upload，本地存储 + MySQL
- ✨ 前端 MediaView：上传表单 + 画廊 + 筛选 + 删除
- ✨ 文搜图/以图搜图：BGE 向量匹配 + CLIP 降级
- ✨ 文档解析：PDF/Word/Markdown 自动解析（pdfplumber + python-docx）
- ✨ 收藏功能：favorites 表 + CRUD API（需登录）
- ✨ 知识库分类：23 种技艺分 10 大类
- ✨ Swagger 文档：/docs + /redoc，9 个 Tag
- ✨ 审核状态：media_documents.status（draft→reviewed→published）
- ✨ Embedding 重建：POST /knowledge/rebuild-embeddings
- ✨ 音频转写：Whisper base（openai-whisper）
- ✨ Chunk 配置：chunk_size / chunk_overlap 可配置
- ✨ Settings 保存按钮 + ElMessage 反馈
- ✨ Embedding 升级：智谱 API (embedding-2) 优先 + 本地 BGE 降级

### v2.1 — 前端现代化 + 知识平台（2026-07-22~26）

- ✨ Vue 3 全栈：Vite + TypeScript + Pinia + Element Plus + Tailwind
- ✨ Dashboard：马山正行楷毛笔标题 + 23 张本地图片轮播（左名右竖排）+ 模糊背景
- ✨ AI 问答：ChatView + Agent 彩色标签 + 辩论面板 + 流式进度
- ✨ 知识图谱：65 节点全中文可视化（pyvis tojson Unicode 修复 + 筛选修复）
- ✨ 设置页：提供商切换 + 模型输入 + API Key 管理
- 🔴 Logo：🏺→朱砂红「遇岸」隶书印章 SVG
- ✨ 知识库 6→23 种：17 篇新文档，55,000 字，10 大类
- 🐛 jieba 分词：修复中文检索 0 篇 bug
- ⚡ 缺口检测：快速路径 + 占位 Key 503 快速返回
- ✨ Prompt 管理：prompts 表 + CRUD + 版本控制
- ✨ CrossEncoder 重排序：BAAI/bge-reranker-base
- ✨ Query Rewrite：规则 + LLM 双模式
- ✨ CI/CD：GitHub Actions（ruff + pytest）

### v2.0 — 产品地基 + 质量兜底（2026-07-17~25）

- ✨ 用户系统：JWT 注册/登录（OAuth2 + bcrypt），users 表
- ✨ 聊天历史：chat_history 表，分页查询
- 🗄️ 数据库：SQLAlchemy 2.0 + Alembic + MySQL 8.4 + utf8mb4
- ✨ Langfuse：LLM 全链路追踪
- ✨ Docker Compose：PostgreSQL + API + Streamlit 三服务
- ✨ 基础 Agent：三专家 + 调度器 + 辩论引擎
- ✨ 知识图谱：NetworkX + pyvis
- ✨ 多粒度知识服务 + 知识缺口检测
- ✨ 检索管线：ChromaDB + BM25 + RRF
- ✨ 6 种非遗技艺知识库（初始版本）

### v1.8 (2026-07-02)

- ✨ Docker Compose 一键部署支持
- 📖 README 重构：架构图 / API 文档 / 项目目录

### v1.7 (2026-06-20)

- ✨ Streamlit 60/40 双栏布局 + Agent 气泡
- 🐛 修复 pyvis 图谱在 Streamlit 中的渲染问题

### v1.6 (2026-06-08)

- ✨ 辩论引擎 DebateEngine（多轮辩论 + 收敛判定）

### v1.5 (2026-04-25)

- ✨ FastAPI 8 端点 + Lifespan 资源管理
- ✨ 传承人视角叙事生成

### v1.4 (2026-03-02)

- ✨ 非遗知识图谱（NetworkX + pyvis）+ LangGraph 多 Agent 工作流

### v1.3 (2025-08-18)

- ✨ 多粒度知识服务（3 级用户画像）+ 知识缺口检测

### v1.2 (2025-04-05)

- ✨ 查询改写 + CrossEncoder 重排序

### v1.1 (2025-03-24)

- ✨ 三专家 Agent + 调度器 + ChromaDB + BM25 + RRF 多源检索

### v1.0 (2025-03-10)

- 🎉 首次发布：6 种非遗技艺知识库 + 基础问答 + FastAPI + Streamlit


