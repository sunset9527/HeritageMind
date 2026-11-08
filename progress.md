# Progress Log: HeritageMind 阶段 1C+1D

## Session: 2026-10-22

### Requirements & Design

- **Status:** complete
- Actions taken:
  - 对照总路线图确认当前完成到阶段 1B。
  - 检查现有 CORS、健康检查、错误响应、API Key 存储和依赖降级代码。
  - 提出并由用户确认 1C+1D 合并设计。
  - 写入并提交正式设计文档，提交为 `4d0dc6d`。
- Files created/modified:
  - `docs/superpowers/specs/2026-10-22-stage-1c-1d-security-reliability-design.md`

### Implementation Planning

- **Status:** complete
- Actions taken:
  - 将设计转换为一份合并 TDD 实施计划。
  - 固化实现顺序、文件边界、迁移策略、故障注入和发布门禁。
  - 建立持久任务状态、发现和进度文件。
- Files created/modified:
  - `docs/plans/2026-10-22-stage-1c-1d-security-reliability-plan.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Implementation

- **Status:** in_progress
- Actions taken:
  - 用户于 2026-10-22 确认开始实施。
  - 完成工作包一：生产配置门禁与外部 Base URL 策略，提交 `50b96d2`、`81f2a19`。
  - 独立规格审查曾发现环境值契约和空模型 Key 用例遗漏；已修复并复审通过。
  - 质量审查在完成运行时依赖核对后因工具额度中断；其运行时接入提示已纳入紧随的中间件集成工作包。
  - 完成请求上下文、可信代理、CORS 与安全响应头：`42c4407`、`1817465`、`d26f501`、`af1fa67`。其中修复了 XFF 伪造链、跨域 413 响应头与 Docs/ReDoc CSP 兼容。
  - 完成并独立复审 Redis 业务限流：`120e0a8`、`790d9f6`、`79ea29f`、`dfc4fbc`、`cea1fbc`。生产 Redis 异常 fail-closed；注册/登录双桶；HMAC 当前/旧 Key 门禁与轮换窗口测试均已通过。
  - 高成本操作并发许可已实现：`a6fc6a17`；定向回归通过，独立规格审查仍在进行，故未把它记为已验收。
  - 尚未实施：密码与 API Key 生命周期、统一错误/日志/Trace 脱敏、依赖健康和 008 迁移、韧性组件、前端错误体验、部署文档及最终全量/真实故障注入。
- Files created/modified:
  - `task_plan.md`
  - `progress.md`

### Session: 2026-10-31（续）

### Password, BYOK and initial error redaction

- **Status:** partially complete
- Actions taken:
  - 新增密码策略：普通用户最少 10 位、管理员最少 12 位、最多 128 位；拒绝空白、内置弱密码及与用户名/邮箱过于相似的密码。
  - 保持旧用户登录兼容；新哈希使用 `bcrypt_sha256`，仍可验证已有 bcrypt 哈希。
  - BYOK 从 `localStorage` 迁至 `sessionStorage`；升级时删除旧 Key，退出与设置页清除操作均会移除当前会话 Key。
  - 为公开 500/SSE 错误替换直接异常透传，并让文档、索引、音频任务在持久化失败信息前删除常见密钥、数据库 URL 和绝对路径。
  - 当前 Windows + Python 3.13 环境中，Starlette `TestClient` 在 AnyIO 创建 Proactor event loop 时卡在 `socketpair`；通过既有 HTTP 测试复现，确认与认证路由无关。未将该环境问题写成 HTTP 回归通过。
- Verification:
  - 后端：`16 passed`（密码、管理员初始化、脱敏）；存在既有 `jieba/pkg_resources` 弃用警告。
  - 前端：`5 passed`（settings 与 API client）。
  - `python -m compileall -q api.py src` 与 `git diff --check` 通过。

### Dependency health and Worker heartbeat migration

- **Status:** partially complete
- Actions taken:
  - 新增内存依赖健康注册表，严格保存状态、稳定原因码、检查时间和连续失败次数，不保存异常正文。
  - 增加 `/health/live`、`/health/ready` 和管理员 `/health/dependencies`；兼容 `/health` 改为 readiness 语义。API 核心依赖为 MySQL 与已初始化检索器，必需依赖失败返回 503；可选依赖可在注册表中表示为 degraded/disabled。
  - Worker 心跳扩展总体状态、依赖 JSON 摘要和稳定错误码；新增 Alembic `008`。
  - Docker healthcheck 改为 `/health/live`；README 与部署文档明确区分编排 liveness 和发布 readiness。
- Verification:
  - 依赖健康、008 迁移、Worker 心跳、007 回归与部署契约共 `18 passed`（有既有 `jieba/pkg_resources` 弃用警告）。
  - SQLite 真实烟雾：`001→…→008→007→008` 成功。
  - `python -m compileall -q api.py src migrations`、开发 Compose 配置校验与 `git diff --check` 通过。

### Session: 2026-11-02（续）

### Error contract, MCP resilience and production readiness

- **Status:** targeted verification complete; final integration verification pending.
- Actions taken:
  - 新增异步韧性组件（总超时、仅对白名单瞬时错误重试一次、进程内熔断）并接入 Wikipedia、GitHub 与 Web MCP 调用；失败以稳定状态登记到依赖健康注册表。
  - 安装 HTTP 全局异常协议、SSE 统一错误事件及 request ID；前端兼容新 `error.message` 与旧 `detail`，登录/注册和流式问答会显示 request ID。
  - Agent、工作流与内容适配降级路径改用稳定错误码和用户安全提示；API 与 Worker 的日志 handler 增加密钥、数据库 URL 与路径过滤器。
  - 修复可选依赖 `unavailable` 被误报为 overall `healthy` 的 readiness 语义；生产 API readiness 以 1 秒 Redis PING 作为 required 依赖，开发/test 保持可观察降级。
  - 生产 Compose 固定 `APP_ENV=prod`，并对 `MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`JWT_SECRET_KEY`、`DEEPSEEK_API_KEY`、`RATE_LIMIT_HMAC_KEY` 使用必填插值；缺失值在解析编排前中止。
- Verification:
  - 用户 PowerShell：错误、脱敏、工作流安全契约 `13 passed, 6 warnings in 34.37s`；警告为 `jieba/pkg_resources`、LangGraph 与已有 Pydantic v2 class Config 弃用。
  - 用户 PowerShell：韧性与 MCP 回归 `7 passed, 1 warning in 1.87s`。
  - 本机：依赖健康/路由策略 `9 passed, 1 warning`；生产部署契约 `7 passed, 1 warning`；前端错误解析/认证/API client `7 passed`，生产构建成功（既有 Rollup PURE 注释与 500 kB chunk 提示）。
  - 生产 Compose：缺失必填变量时按预期拒绝解析；注入临时占位变量后 `docker compose --env-file .env.example -f docker-compose.production.yml config --quiet` 通过。
  - 用户 PowerShell：后端全量 `610 passed, 1 skipped, 6 warnings in 34.51s`；前端全量 `24` files、`49 passed`，8.33 秒。
  - 新增 `docs/stage-1c-1d-security-reliability-audit.md`；阶段 1 仍因高成本并发许可独立复审和 Worker 的真实心跳断连验证而保持进行中。
  - Docker 构建权限问题已修复：`frontend/.dockerignore` 排除前端 `.pytest_cache`；根 `.dockerignore` 排除 pytest 临时目录及 API/Worker 不需要的前端生成物，部署契约覆盖并通过。
  - 在独立 `heritagemind-injection` 生产配置栈完成 API 的真实故障注入：Redis 停止时 liveness=200、readiness=503、`/crafts` 为无上游细节的 `rate_limit_unavailable` 503，恢复后均为 200；MySQL 停止时 liveness=200、readiness=503 且原因码为 `connection_failed`，恢复后为 200。
  - Worker 真实心跳验证未执行：其专用镜像首次构建需下载约 539 MB PyTorch 依赖，已停止本次构建，未将该项记为通过。

### Session: 2026-11-02（真实模型/检索/MCP故障注入与暂停）

- **Status:** API 侧完成；Worker/Whisper 验收暂停。
- Actions taken:
  - 在隔离生产 Compose 项目 `heritagemind-injection` 重建 API 后，以 5 个真实并发 `/query` 请求验证 `SERVER_LLM=4`：4 个请求继续完成，超额第 5 个请求在约 0.37 秒返回统一 `503 busy`。
  - 该真实压测暴露 `/query` 直接调用同步 `workflow.query()` 会阻塞事件循环、使许可无法产生背压；新增回归测试后改为 `asyncio.to_thread`。同时将请求级 LLM override 从进程全局字典迁移为 `ContextVar`，并以双线程隔离测试验证不会串用 API Key。
  - 在同一真实容器中验证：本地 BGE-M3 缺失时 `MultiSourceRetriever` 降级为关键词检索；Reranker 依赖缺失时按既有 score 排序；MCP Web 对关闭 HTTPS 端口返回 `unavailable` 并写入 `retry_exhausted` 健康原因码。
  - Worker 镜像构建需要下载 PyTorch 等额外依赖；用户随后要求暂停剩余项，已停止仅用于验证的后台构建，未删除卷、容器或项目数据。
- Remaining paused verification:
  - Worker Redis 断连/恢复后的持久化心跳状态。
  - Whisper 模型目录或推理不可用时，真实音频任务的失败落库、脱敏信息和 worker 存活性。

## Test Results

| Test | Input | Expected | Actual | Status |
|---|---|---|---|---|
| 设计自检 | 占位符、冲突、范围和歧义扫描 | 无 TBD/TODO 和关键矛盾 | 通过 | ✓ |
| 配置门禁与 URL 策略 | 新增 36 项目标测试 | 配置/生产拒绝规则与 Base URL 策略通过 | 36 passed | ✓ |
| Settings 相关回归 | 既有 15 项 | 既有设置行为不回归 | 15 passed | ✓ |
| 请求安全中间件 | 请求 ID、可信代理、CORS、安全头与 1B 体积限制 | 运行时安全边界有效 | 65 passed | ✓ |
| Redis 限流加固 | 限流、启动门禁、请求上下文、鉴权/上传/检索相关回归 | 生产 fail-closed、双桶/HMAC 轮换与路由覆盖有效 | 109 passed | ✓ |
| 高成本并发许可 | 并发、1B 维护任务/Worker 生命周期与限流回归 | 许可接线与释放路径通过；独立复审待完成 | 42 passed | in review |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|---|---|---:|---|
| 2026-10-22 | `writing-plans` 技能未提供 | 1 | 使用项目既有计划格式和 planning-with-files 替代，不开始实现 |
| 2026-10-22 | 计划引用了不存在的 `tests/test_auth.py` | 1 | 改为明确新建 `tests/test_stage1cd_auth_http.py` |
| 2026-10-22 | 非提权 `git status` 间歇性误报非工作树 | 1 | 验证仓库配置正常，最终 Git 操作用受控提权完成 |
| 2026-10-22 | 复合 `rg` 正则被 PowerShell 引号截断 | 1 | 改用不含嵌套转义的简单占位符扫描 |
| 2026-10-31 | pytest 系统临时目录创建失败 | 2 | 使用已授权工作区内唯一 `--basetemp` 重跑，相关回归 15 passed |
| 2026-10-31 | 独立质量审查代理额度中断 | 1 | 保留运行时接入提示给下一工作包；本包由通过的规格复审和主代理只读核查继续把关 |

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | 配置门禁、请求安全中间件和限流加固已验收；高成本并发许可已实现并处于独立规格复审 |
| Where am I going? | 一次完成阶段 1C+1D，并通过安全、故障注入和全量回归门禁 |
| What's the goal? | 让 HeritageMind 路线图阶段 1 可真实标记为完成 |
| What have I learned? | 见 `findings.md` |
| What have I done? | 已完成 1C/1D 的配置、请求安全与限流子包；提交、测试与待办见本文件 |
