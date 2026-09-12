# HeritageMind

> 面向中国非物质文化遗产的 AI 知识平台：以可追溯检索、图谱和多 Agent 协作回答问题，并在知识不足时说明边界。

`FastAPI` · `Vue 3` · `LangGraph` · `BM25 + BGE-M3 + RRF` · `ChromaDB` · `MySQL` · `NetworkX`

## 为什么做

非遗知识需要被保存，也需要被可靠地解释。HeritageMind 不把未知内容包装成事实：回答需要证据，系统会提示知识库覆盖不足。

当前知识库收录 23 种非遗技艺，涵盖陶瓷、丝织、雕刻、印染、纸艺、金属与戏曲等门类。

## 核心能力

| 能力 | 当前实现 |
| --- | --- |
| 混合检索 | jieba + BM25、BGE-M3 向量检索、RRF 与 CrossEncoder 重排序 |
| 多专家协作 | 调度器按问题分派技艺、历史、传承三类专家并融合回答 |
| 知识边界 | 知识缺口检测：覆盖不足时提示，而非补造事实 |
| 多轮对话 | 登录用户的 MySQL 会话记忆，支持同一会话中的指代追问 |
| 本地图谱 | 65 节点、39 条关系，覆盖技艺、材料、工具、传承人、地域与朝代 |
| v1.6 执行轨迹 | Router 输出 `rag / graph / hybrid`；Graph Agent 只读本地图谱；响应携带路线、轨迹与引用，Vue 可展开查看 |
| v1.8 动态协作 | Router 选出的实际专家进行受上限约束的补充、质疑与回应；SSE 实时推送 DAG 节点、协作摘要与降级状态 |
| v1.8 质量闭环 | 登录回答保存版本化规则评分；用户可点赞/点踩并补充意见；管理员可查看评估/反馈、配置内置专家 |
| 多模态基础 | 图片/音频/文档上传、音频转写与检索、Redis 不可达时的内存降级 |

## 当前架构

```text
Vue 3 → FastAPI → LangGraph Workflow
                    ├─ Router / Planner / 会话上下文
                    ├─ Research：混合检索 + 动态注册专家协作
                    ├─ Graph Agent：只读 data/heritage_graph.json
                    └─ Answer：融合证据、引用、缺口提示与过程质量信号
                         │
              MySQL · ChromaDB · 本地图谱 · 本地媒体文件
```

会话记忆只辅助理解上下文和改写检索词，不能单独作为事实来源；图谱无命中时记录降级原因并回退检索链路。

## 快速开始（Windows PowerShell）

前置条件：Python 3.11+、Node.js 18+、可用的 OpenAI 兼容 LLM API Key；MySQL 用于登录、会话记忆和媒体记录。

```powershell
git clone https://github.com/sunset9527/HeritageMind.git
cd HeritageMind
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env：至少配置 DEEPSEEK_API_KEY；按需配置 DATABASE_URL
python -m alembic upgrade head

# 终端 1：API（默认 8001）
python api.py

# 终端 2：Vue（默认 5173）
cd frontend
npm install
npm run dev
```

- 前端：<http://127.0.0.1:5173>
- Swagger：<http://127.0.0.1:8001/docs>

首次使用可在前端“设置”页填写自己的 API Key；它存于浏览器本地存储并作为请求头传递。

## API 与运行说明

完整端点、请求模型与交互调试以 Swagger 为准：<http://127.0.0.1:8001/docs>。

- `POST /query`：非遗问答；可选 `session_id` 继续登录用户会话。
- `POST /feedback`：登录用户对自己的已保存回答点赞、点踩、补充意见或取消反馈。
- `GET /admin/evaluations`、`GET /admin/feedback`、`GET/PATCH /admin/agents`：管理员质量回看与内置 Agent 配置。
- `GET /graph/stats`、`GET /graph/visualize`：本地图谱统计与可视化。
- `POST /media/upload`、`GET /search/audio`：媒体上传和音频文本检索。

`/query` 新增 `metadata.route`、`metadata.workflow_trace` 和 `citations`：只呈现路线、节点状态、耗时与实际使用的本地证据，不返回提示词、会话原文、密钥或内部推理。

## 可复现验证

### 检索评测

自建评测有 100 条，其中 94 条具备知识库锚点的有效题目；在当前 23 篇语料、主题区分度较高的条件下，BM25、向量检索与 RRF 的 Hit@5 均为 **94/94（100%）**。

这证明的是小规模领域知识库的召回表现，不等同于通用检索准确率。脚本：`eval_retrieval_hm100.py`。

### 自动化测试

```powershell
# 系统临时目录不可写时，指定一个可写目录
python -m pytest tests/ --basetemp E:\temp\heritagemind-pytest
```

本次 v1.6 迭代真实结果为 **154 passed, 1 skipped**。新增测试覆盖结构化 Router、Graph Agent、工作流路线和响应契约，且不依赖外网、API Key、Redis、BGE 或 Whisper。

v1.8 已额外实际运行 `tests/test_v18_quality_feedback_admin.py`，结果为 **11 passed**；覆盖规则评分、反馈归属与更新、管理员权限、评价持久化、Agent 配置注入和全禁用安全回退。`npx vue-tsc --noEmit` 已通过。尚未把完整模型端到端质量测试或全量构建回归宣称为已完成。

## v1.8 数据库迁移说明

执行 `python -m alembic upgrade head` 创建 `answer_evaluations`、`user_feedback` 与 `agent_configurations`。Windows 本地如遇 `alembic.ini` 编码问题，当前配置已使用 ASCII 注释兼容系统 GBK。

对于历史本地库：若已有部分 v1.5 表但没有 `alembic_version`，不能直接从空版本升级，否则会重复创建旧表。项目的 `004` 迁移会兼容补齐缺失的 `chat_history.session_id`；应先检查现有表结构后再执行版本登记与升级。

## 工程导航

```text
src/agents/       调度器、三专家与 Graph Agent
src/workflow/     LangGraph 状态、节点与工作流图
src/retrieval/    BM25、向量检索、RRF、重排序与查询改写
src/graph/        NetworkX 图谱与 pyvis 可视化
src/services/     会话记忆、缓存、媒体与音频转写
frontend/         Vue 3、Pinia、问答与图谱页面
data/             技艺文档与 heritage_graph.json
tests/            离线确定性测试
docs/             设计规格与项目文档
```

## 路线图

已完成：用户与会话、混合检索、知识缺口检测、动态多专家协作、实时 DAG、图片/音频/文档能力、本地图谱、v1.6 结构化路由与执行轨迹、v1.8 质量反馈与 Agent 管理。

后续方向：图像/音频理解、Reflection Agent、外部知识源、Agent 协作深化与反馈评估。未完成方向不作为当前能力承诺。

## 贡献与反馈

欢迎提交 Issue 或 Pull Request。涉及知识库与评测时，请同时说明来源、适用范围和可复现方式；不要为了提高指标而修改评测数据。

## License

本仓库尚未声明开源许可证；复用前请先联系作者确认。
