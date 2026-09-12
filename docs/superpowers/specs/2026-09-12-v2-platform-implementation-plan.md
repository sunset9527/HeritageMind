# HeritageMind v2.0 实施计划：平台数据、可信扩展与部署模板

> 前置规格：[v2.0 平台化设计](2026-09-12-v2-platform-design.md)

## 实施纪律

- 每一项生产行为先写最小、离线、确定性测试并观察其因功能缺失而失败；之后才编写最小实现。
- 外部 HTTP 访问均经可注入客户端完成；测试不得访问 Wikipedia、GitHub、LLM 或真实数据库服务。
- 自动抽取的图谱内容一律进入候选区，只有管理员审核通过才进入正式图谱；来源不足不发布。
- 不编造传承人事实、图片授权、搜索结果、线上部署、性能指标或测试结果。
- 本期沿用 MySQL、Chroma、本地图谱和 Vue 3，保持已有 `/query` 与 `/query/stream` 契约兼容。

## 1. 平台数据、来源与审计底座

**文件**：新增 `src/models/platform.py`、`src/services/platform_content.py`、`src/schemas/platform.py`、`migrations/versions/005_add_v2_platform_content.py`、`tests/test_v20_platform_content.py`；更新 `src/models/__init__.py`、`api.py`。

1. 先测试技艺条目、传承人档案、来源证据、图谱候选与审计日志的必填字段、唯一约束和状态机。
2. 实现 SQLAlchemy 模型及 005 Alembic 迁移。档案与候选记录均保存来源；候选状态限定为 `pending/approved/rejected`。
3. 实现服务层：技艺列表/详情、公开档案读取、管理员 CRUD、来源校验、审计写入，以及候选创建、列表、审核。
4. 实现公开 `GET /encyclopedia`、`GET /encyclopedia/{slug}`、`GET /inheritors`、`GET /inheritors/{slug}`；实现对应管理员接口。所有管理写接口使用 `require_admin`。
5. 编写可重复的 6 位传承人种子脚本/数据文件。记录来源机构和 URL；无法确认的字段保留为空。种子应幂等并只在管理员明确运行时写库。

**验收**：越权请求被拒绝；公开响应不泄露内部审核信息；每个已发布传承人档案至少拥有一个来源证据；审计日志不包含密钥。

## 2. 图谱候选抽取、审核合并与增量扫描

**文件**：新增 `src/services/graph_curation.py`、`src/services/graph_extraction.py`、`tests/test_v20_graph_curation.py`；更新 `src/graph/heritage_graph.py`、`api.py`、平台 schema/服务。

1. 先测试纯候选归一化与去重：同一 `(source, relation, target)` 及相同证据来源只产生一个 pending 候选。
2. 实现规则优先的抽取接口，允许后续注入 LLM 抽取器；默认不依赖 LLM。抽取器返回实体、节点类型、关系、证据片段和来源，而不是直接操作图谱。
3. 先测试批准时才向 `HeritageKnowledgeGraph` 添加节点/边且保存来源属性；拒绝或待审状态绝不改变正式图谱。
4. 实现图谱合并服务、管理员审核接口、候选预览接口，以及对新/变更的已发布百科条目的增量扫描接口。
5. 将调度器入口设计为独立命令/HTTP 管理操作，生产文档给出通过 cron 或容器任务运行方式；开发 API 不在 lifespan 中隐式启动循环。

**验收**：候选、审核人、时间和来源可追溯；审核重试幂等；保存失败不留下半更新图谱。

## 3. MCP 工具层与受控外部适配器

**文件**：新增 `src/mcp_server.py`、`src/services/mcp_tools.py`、`tests/test_v20_mcp_tools.py`；更新 `requirements.txt`、`config.py`、`.env.example`、`README.md`。

1. 先为本地知识、Wikipedia、GitHub、百度百科和 Web 搜索工具写契约测试：成功响应、超时、非 2xx、响应超限、未配置均有稳定结构。
2. 实现 `McpToolResult` 与统一 `ExternalHttpClient`，含超时、最大响应字节数、允许主机和错误码；拒绝用户可控 URL 请求。
3. 实现本地知识工具复用现有检索服务；Wikipedia 使用公开 REST API；GitHub 使用公开 REST API。输出限制结果数与字段。
4. 实现百度百科、通用 Web 搜索适配器和配置项。默认返回 `not_configured`；不设置密钥、不抓取网页、不合成虚假结果。
5. 使用官方 MCP Python SDK 暴露可由 stdio 启动的标准 Server，且工具实现与 HTTP 业务逻辑共用；在 README 记录启动命令和开发限制。

**验收**：工具对任一外部失败安全降级；不记录 Authorization/API Key；无网络测试全部通过。

## 4. AI 搜索聚合 API

**文件**：新增 `src/services/ai_search.py`、`src/schemas/search.py`、`tests/test_v20_ai_search.py`；更新 `api.py`、`src/retrieval/*` 的最小调用点。

1. 先测试聚合器能合并 RAG、图谱、媒体与工具结果，且按稳定规则去重引用；未配置外部工具不影响本地答案。
2. 实现无需改写现有工作流的 `AiSearchService`：复用可注入的本地检索、图谱查询和媒体搜索，将外部工具作为可选补充。
3. 实现 `POST /search/ai`，返回 `answer`、`citations`、`graph`、`media`、`sources` 与不含提示词/密钥/推理的 execution 摘要。
4. 只有在有效 LLM 配置下才生成回答；否则仍返回已检索的证据和清晰 `answer_status`，不把检索片段伪装成模型答案。

**验收**：请求、响应、降级与引用均受 API 测试保护，原聊天接口不被修改为不兼容格式。

## 5. Vue 平台页与管理扩展

**文件**：新增 `frontend/src/views/SearchView.vue`、`EncyclopediaView.vue`、`CraftDetailView.vue`、`InheritorListView.vue`、`InheritorDetailView.vue`、`ProfileView.vue`；新增对应 `frontend/src/api/*` 与组件；更新 `router/index.ts`、`AppHeader.vue`、`AdminView.vue`、`types/index.ts`、Dashboard 组件和样式。

1. 先为纯 TypeScript 数据归约函数写最小断言：AI 搜索的来源状态、空状态、引用去重和档案来源展示。
2. 实现 API 客户端和类型；所有网络错误显示明确状态，不用静态假数据替代。
3. 实现 AI 搜索结果页、百科目录/详情和传承人目录/详情；档案和百科提供 title、description、canonical 元数据。
4. 通过构建期脚本将已发布技艺路由预渲染为静态文件；以测试的静态清单驱动构建，不在浏览器模拟 SSR。
5. 实现个人中心，聚合现有 sessions、收藏、偏好和设置入口；服务端仍负责归属校验。
6. 扩展 Dashboard 使用真实 API 数据；扩展后台管理候选审核、传承人、百科、媒体、Prompt/模型只读或安全编辑、用户与审计入口。
7. 路由守卫仅优化体验；管理员 API 权限始终由后端验证。

**验收**：`npx vue-tsc --noEmit` 和 `npm run build` 通过；空、未登录、未配置与无权限状态可理解。

## 6. 容器、Nginx 与真实域名交接文档

**文件**：新增 `docker-compose.production.yml`、`deploy/nginx/heritagemind.conf.template`、`deploy/nginx/https.conf.template`、`deploy/README.md`；更新 `docker-compose.yml`、`frontend/nginx.conf`、`.env.example`、README。

1. 先检查 Nginx 配置语法和 Compose 渲染；配置不在当前机器绑定 443 或签发证书。
2. 拆分本地开发和生产 Compose：生产仅暴露 Nginx，API/MySQL/Redis 位于内部网络，持久卷明确声明。
3. 配置安全响应头、gzip、SPA 回退、`/api/` 反向代理、SSE 禁缓冲、上传大小限制和健康检查。
4. 使用 `${DOMAIN}`、`${CERTBOT_EMAIL}`、`${CERT_PATH}` 等占位符；文档分步骤说明购买服务器/域名后设置 DNS、替换变量、使用 Certbot 签发与续期、启动和回滚。

**验收**：本地模板经配置校验；文档不声称 HTTPS 已启用或证书已签发。

## 7. 回归、数据核验与交付记录

1. 每个阶段在实现后运行对应单测，再运行全量 `python -m pytest tests/ --basetemp <可写目录>`。
2. 执行 `npx vue-tsc --noEmit` 与 `npm run build`；如有既有警告，记录为警告而非测试成功。
3. 在用户提供有效 MySQL、LLM、可联网环境后，单独进行并记录可选手动 E2E：百科/档案发布、候选审核、AI 搜索与 MCP 真实调用。无此环境时不虚报。
4. 更新 README 的当前能力、运行方式、MCP/部署边界和验证结果；最终用 `git diff --check`、`git status --short` 审查仅含本期文件。
