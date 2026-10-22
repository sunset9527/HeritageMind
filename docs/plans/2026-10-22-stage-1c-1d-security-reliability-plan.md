# HeritageMind 阶段 1C+1D：安全与可靠性合并实施计划

> 设计依据：`docs/superpowers/specs/2026-10-22-stage-1c-1d-security-reliability-design.md`
>
> 交付方式：1C 与 1D 在同一开发周期、同一发布候选和同一最终验收中完成。下列工作包是代码依赖顺序，不是拆分发布。
>
> 开发原则：严格 TDD；每项先观察新增测试按预期失败，再写最小实现，最后重构并复跑受影响测试。不得放宽阶段 1A/1B 权限、上传、草稿隔离和索引原子性测试。

## 0. 基线、威胁清单与修改边界

**目标**

冻结实施起点，避免把既有问题误算为本阶段回归，并把安全风险映射到测试。

**操作**

- 确认起始提交、工作区状态和当前 Alembic head。
- 运行后端、前端、生产构建、编译、迁移与 Compose 基线。
- 建立威胁清单：通配 CORS、伪造代理 IP、暴力登录、匿名模型滥用、限流绕过、SSRF、默认密钥、错误泄露、日志/Trace 泄密、依赖卡死和错误健康状态。
- 记录本机不可用工具，不把未安装的 Ruff、未启动的容器或未加载的模型写成通过。

**基线命令**

```powershell
git status --short
git rev-parse HEAD
python -m pytest tests -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-baseline
Set-Location frontend
npm run test -- --run
npm run build
Set-Location ..
python -m compileall -q api.py config.py src migrations
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.production.yml config --quiet
```

**产物**

- `docs/stage-1c-1d-security-reliability-audit.md` 建立空的验收骨架，只在实际验证后填入结果。
- 更新 `progress.md`，记录真实基线。

## 1. 配置模型与生产启动门禁

**先写测试**

- 新建 `tests/test_stage1cd_settings.py`。
- 新建 `tests/test_stage1cd_startup_validation.py`。
- 覆盖环境枚举、CORS 列表解析、配额/超时正数约束、可信代理、匿名问答组合约束和 Base URL 规则。
- 覆盖生产默认 JWT、示例数据库密码、占位模型 Key、通配 CORS、无 HTTPS 却启用 HSTS、危险 Base URL 时拒绝启动。
- 覆盖 development/test 允许确定性宽松配置，但返回明确警告结果。

**实现**

- 扩展 `config.py`，新增环境、安全、配额、并发、超时、可信代理和依赖策略配置。
- 新建 `src/services/startup_validation.py`，返回结构化问题列表；生产 fatal 问题抛出专用异常。
- 在 API 和 Worker 启动最前面调用校验，不记录实际 Secret、完整数据库 URL 或 API Key。
- 新建 `src/services/url_policy.py`，统一验证用户自定义模型 Base URL：生产只允许 HTTPS、配置主机和正常公网端口；拒绝 userinfo、文件协议、本机、链路本地和私有网段。开发模式只有显式开关才能允许 localhost HTTP。

**验证**

```powershell
python -m pytest tests/test_stage1cd_settings.py tests/test_stage1cd_startup_validation.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-config
```

## 2. 请求上下文、可信客户端 IP、CORS 与安全响应头

**先写测试**

- 新建 `tests/test_stage1cd_request_context.py`。
- 新建 `tests/test_stage1cd_cors_headers.py`。
- 覆盖自动 request ID、合法外部 request ID、恶意超长/控制字符 ID 替换。
- 覆盖未配置可信代理时忽略 `X-Forwarded-For`，配置可信代理时只消费约定跳数。
- 覆盖合法/非法 Origin、预检、凭据和无 Origin 的服务间请求。
- 覆盖 CSP、nosniff、Referrer-Policy、frame/Permissions Policy，以及 HSTS 只在真实 HTTPS 生产环境出现。

**实现**

- 新建 `src/middleware/request_context.py`，使用 ContextVar 暴露 request ID 和客户端身份。
- 新建 `src/middleware/security_headers.py`。
- 将 `api.py` 的通配 CORS 替换为配置白名单。
- 明确中间件顺序：请求体限制在最外层计数；请求上下文尽早建立；统一错误层能取得 request ID；安全头作用于成功和错误响应。
- 对 Nginx 模板和前端 Nginx 配置使用与应用一致的最小安全头，不设置冲突的宽松值。

**验证**

```powershell
python -m pytest tests/test_stage1cd_request_context.py tests/test_stage1cd_cors_headers.py tests/test_stage1b_request_size_limit.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-headers
```

## 3. Redis 业务限流与进程内保守降级

**先写测试**

- 新建 `tests/test_stage1cd_rate_limit.py`。
- 扩展 `tests/redis_stub.py` 支持所需原子脚本语义，或为限流存储注入独立确定性桩。
- 覆盖用户/IP/账号摘要隔离、窗口首次请求、临界值、超限、TTL 和新窗口恢复。
- 覆盖注册、登录、匿名问答、登录问答、AI 搜索、上传、索引重建和普通只读类别。
- 覆盖 Redis 故障后本地额度不比正常额度更宽。
- 断言 `429` 包含稳定错误码、`Retry-After` 和 request ID。
- 断言 Redis key 不包含 JWT、API Key、邮箱全文、用户名全文或问题正文。

**实现**

- 新建 `src/services/rate_limit.py`：定义策略、身份和存储协议。
- Redis 使用 Lua 完成 INCR、首次 EXPIRE 和剩余 TTL 的单次原子操作。
- 新建有界进程内窗口存储，限制最大 key 数并定期淘汰过期记录。
- 新建 `src/deps_rate_limit.py` 或等价依赖工厂，使路由只声明业务类别。
- 为相关路由接入限制；管理员权限检查仍是第一安全边界，限流不能代替权限。
- 对代理身份解析失败采用更保守身份，不能信任客户端自报头。

**验证**

```powershell
python -m pytest tests/test_stage1cd_rate_limit.py tests/test_stage1a_route_authorization.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-rate
```

## 4. 高成本操作并发许可

**先写测试**

- 新建 `tests/test_stage1cd_concurrency.py`。
- 覆盖 LLM、Embedding、解析和维护任务使用不同许可池。
- 覆盖正常完成、异常、取消和超时后许可必定释放。
- 覆盖达到上限快速失败，不在内存中无限排队。
- 覆盖后台任务已有数据库状态时不因通知失败丢失任务。

**实现**

- 新建 `src/services/concurrency.py`，按能力名称管理有限 semaphore 和短获取超时。
- 路由层限制进入同步/异步昂贵操作的请求数量。
- Worker 保留串行或配置并发消费；维护任务继续使用同类任务数据库互斥。
- 并发拒绝映射为统一 `busy` 错误，携带建议重试时间。

**验证**

```powershell
python -m pytest tests/test_stage1cd_concurrency.py tests/test_stage1b_maintenance_jobs.py tests/test_stage1b_worker_lifecycle.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-concurrency
```

## 5. 密码策略、账号枚举防护与 API Key 生命周期

**先写测试**

- 新建 `tests/test_stage1cd_password_policy.py` 和 `tests/test_stage1cd_auth_http.py`。
- 新建 `frontend/src/stores/settings.security.spec.ts`。
- 扩展登录/注册和 API client/query 测试。
- 覆盖普通用户 10～128 位、管理员至少 12 位、全空白、弱密码、与用户名/邮箱高度相同。
- 覆盖不存在用户与错误密码返回相同公开信息。
- 覆盖旧用户仍可登录，新注册和管理员初始化使用新策略。
- 覆盖启动前删除旧 `localStorage.hm_user_api_key`、Key 只进入 sessionStorage、退出和清除按钮删除 Key。
- 覆盖 provider/model 等非敏感偏好仍可持久化。
- 覆盖所有请求头注入路径都不回写 Key。

**实现**

- 新建 `src/services/password_policy.py`，由注册、管理员初始化和以后改密统一调用。
- 修改 `src/services/auth.py`，统一登录失败文案并保留内部安全审计原因码。
- 修改 `src/bootstrap_admin.py` 使用管理员密码策略。
- 修改前端 settings Store、SettingsView、API client 和 SSE query 模块。
- 设置页增加短期存储说明与一键清除按钮；退出登录时清理 Key。
- 保持 JWT Bearer Token 机制不变，不混入 Cookie/刷新令牌改造。

**验证**

```powershell
python -m pytest tests/test_stage1cd_password_policy.py tests/test_stage1cd_auth_http.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-auth
Set-Location frontend
npm run test -- --run src/stores/settings.security.spec.ts src/api/client.spec.ts
Set-Location ..
```

## 6. 统一错误协议、日志过滤与 Trace 脱敏

**先写测试**

- 新建 `tests/test_stage1cd_error_contract.py`。
- 新建 `tests/test_stage1cd_redaction.py`。
- 覆盖 HTTP、验证错误、未认证、无权限、限流、状态冲突、依赖超时和未知异常。
- 覆盖 SSE error event 与 HTTP 使用相同 code/request_id。
- 使用带测试 Secret、数据库连接串、Windows/Linux 绝对路径和第三方响应正文的异常，断言公开响应、日志、任务错误和 Trace metadata 均不包含原文。
- 覆盖管理员仍能看到可行动的稳定错误码和脱敏摘要。

**实现**

- 新建 `src/schemas/errors.py` 和 `src/services/error_sanitizer.py`。
- 新建全局异常处理器，保留 FastAPI/Pydantic 正确状态码并统一 envelope。
- 扫描和替换 `api.py` 中公开 `detail=str(e)` 及 SSE `msg=str(e)`。
- 调整 Agent/Workflow 的公开错误信息，不把底层异常放入最终答案；内部状态只保留原因码和脱敏摘要。
- 为 Python logging 增加递归字段过滤器；Langfuse 只允许明确字段白名单。
- 对数据库任务的 `error_message` 执行截断与脱敏，再持久化。

**验证**

```powershell
python -m pytest tests/test_stage1cd_error_contract.py tests/test_stage1cd_redaction.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-errors
rg -n "detail=str\(e\)|msg.*str\(e\)|error.*str\(e\)" api.py src
```

`rg` 命中必须逐条分类；内部日志允许经过统一过滤器记录异常，公开响应不得直接透传。

## 7. 依赖健康注册表和真实健康接口

**先写测试**

- 新建 `tests/test_stage1cd_dependency_health.py`。
- 新建 `tests/test_stage1cd_health_routes.py`。
- 覆盖 `healthy/degraded/unavailable/disabled/unknown` 状态迁移和时间字段。
- 断言 liveness 不访问数据库、Redis、模型或文件系统。
- 覆盖 required 失败时 readiness 返回 503；optional 失败时返回 200+degraded；关闭功能显示 disabled。
- 覆盖健康响应不包含连接串、模型路径、密钥和异常正文。
- 覆盖短 TTL 防止健康端点形成依赖压力。

**实现**

- 新建 `src/services/dependency_health.py` 和 `src/schemas/health.py`。
- 实现 `/health/live`、`/health/ready`、管理员 `/health/dependencies`，并把 `/health` 改为精简 readiness 兼容入口。
- MySQL 使用轻量 `SELECT 1`；Redis 使用带短超时 `PING`；检索器检查初始化和活动索引/语料状态。
- LLM/Embedding/Reranker/Whisper/Langfuse/MCP 主要读取注册表，不在健康请求里加载重模型。
- 修改 Dockerfile 和 Compose：API 容器 healthcheck 使用 `/health/live`；部署脚本单独等待 `/health/ready`。

**验证**

```powershell
python -m pytest tests/test_stage1cd_dependency_health.py tests/test_stage1cd_health_routes.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-health
```

## 8. Worker 心跳状态与 008 迁移

**先写测试**

- 新建 `tests/test_stage1cd_worker_health_migration.py`。
- 扩展 `tests/test_stage1b_worker_lifecycle.py` 和迁移测试。
- 覆盖空库、007 已有库和 legacy create_all 数据库升级 008。
- 覆盖旧心跳数据保留、依赖摘要合法 JSON、公开接口不暴露敏感 detail。
- 覆盖 downgrade 008→007 不误删旧心跳行。

**实现**

- 新建 `migrations/versions/008_worker_dependency_health.py`。
- `WorkerHeartbeat` 增加 `status`、`dependencies_json`、`last_error_code`；摘要只保存依赖名、状态和稳定原因码。
- Worker 启动和周期心跳更新总体状态；Redis/MySQL required 失败为 unavailable，可选能力失败为 degraded。
- 管理员依赖接口读取 Worker 最新心跳；现有文档列表的 `online/stale/offline` 保持兼容。

**验证**

```powershell
python -m pytest tests/test_stage1cd_worker_health_migration.py tests/test_stage1b_worker_lifecycle.py tests/test_stage1b_upload_migration.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-worker-health
$env:DATABASE_URL='sqlite:///E:/codex/2026-10-15/a/stage1cd-migration-smoke.db'
python -m alembic upgrade head
python -m alembic downgrade 007
python -m alembic upgrade head
Remove-Item -LiteralPath 'E:\codex\2026-10-15\a\stage1cd-migration-smoke.db' -Force
Remove-Item Env:DATABASE_URL
```

## 9. 共享韧性组件与依赖适配

**先写测试**

- 新建 `tests/test_stage1cd_resilience.py`。
- 扩展 LLM、Embedding、Redis、MCP、Reranker 和 Langfuse 相关测试。
- 覆盖硬超时、只重试允许的瞬时错误、退避、最大次数和取消传播。
- 覆盖熔断 closed→open→half-open→closed，以及 open 状态快速失败。
- 覆盖每次调用更新依赖注册表且不记录敏感参数。
- 覆盖可选依赖降级、必需依赖错误和功能 disabled 三种不同语义。

**实现**

- 新建 `src/services/resilience.py`，提供异步/同步调用包装、超时、有限重试、进程内熔断和依赖状态更新。
- LLM：总超时、最多 1 次瞬时错误重试、短时熔断、请求级并发许可。
- Embedding API：有界批次、总超时和最多 1 次重试；本地模型失败按配置降级 API 或 unavailable。
- Redis：复用短连接/命令超时，不在请求内长重试。
- MCP/Web：约 5 秒总超时，失败标记工具 unavailable，主回答可继续。
- Reranker：失败继续现有排序并标记 degraded。
- Langfuse：失败不阻断业务，但更新 optional 状态。
- Whisper、PDF/OCR、索引继续使用阶段 1B 子进程硬超时，不重复包裹网络重试。

**验证**

```powershell
python -m pytest tests/test_stage1cd_resilience.py tests/test_redis_backend_and_queue.py tests/test_reranker_wiring.py tests/test_stage1b_embedding_api.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-resilience
```

## 10. 路由接线、OpenAPI 与前端错误体验

**先写测试**

- 新建 `tests/test_stage1cd_route_policies.py`，静态断言高成本端点均声明正确限流和并发策略。
- 扩展 API 契约测试，覆盖匿名问答关闭、管理员写端点、健康接口鉴权和统一错误 envelope。
- 新建前端错误解析测试，覆盖 `error.message`、旧 `detail` 兼容和 request ID 展示。
- 扩展 SettingsView 测试，覆盖密钥风险提示和清除按钮可访问性。

**实现**

- 将限流、并发、Base URL 校验和错误协议接入所有目标端点，避免遗漏旧 `/query/simple` 或兼容路由。
- 匿名问答关闭时返回稳定 403；开启时不允许用匿名 BYOK 绕过配额。
- 更新 OpenAPI 描述：认证、限流、429、错误 envelope、健康接口与依赖状态。
- 前端统一显示用户可行动信息；开发模式可以在控制台显示 request ID，但不能打印密钥或底层响应。
- 设置页和登录/注册页面对密码与 Key 规则提供即时但不泄露账号存在性的提示。

**验证**

```powershell
python -m pytest tests/test_stage1cd_route_policies.py tests/test_stage1a_route_authorization.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-routes
Set-Location frontend
npm run test -- --run
npm run build
Set-Location ..
```

## 11. 部署、安全配置和运维文档

**先写测试**

- 扩展 `tests/test_stage1b_deployment_contract.py` 或新建 `tests/test_stage1cd_deployment_contract.py`。
- 断言生产 Compose 不提供默认 JWT/数据库密码；启动必需变量使用 `${VAR:?message}`。
- 断言 API healthcheck 使用 liveness，部署说明等待 readiness。
- 断言 Nginx 和应用的 CORS/安全头职责一致。
- 断言 `.env.example` 包含安全配置说明但不包含可误用的生产 Secret。

**实现**

- 更新 Dockerfile、开发/生产 Compose、两份 Nginx 配置和 `.env.example`。
- 生产 Compose 对 JWT、MySQL 密码使用必填变量，不再默默替换为空字符串。
- README 和 `deploy/README.md` 增加：生产启动门禁、CORS、可信代理、匿名问答、限流、健康接口、故障处理、密钥轮换和回滚。
- 文档明确 liveness 不能代替 readiness，optional degraded 不能冒充 full healthy。

**验证**

```powershell
python -m pytest tests/test_stage1cd_deployment_contract.py -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-deploy
docker compose -f docker-compose.yml config --quiet
$env:MYSQL_PASSWORD='test-only-password'
$env:MYSQL_ROOT_PASSWORD='test-only-root-password'
$env:JWT_SECRET_KEY='test-only-long-jwt-secret-not-for-production'
docker compose -f docker-compose.production.yml config --quiet
Remove-Item Env:MYSQL_PASSWORD
Remove-Item Env:MYSQL_ROOT_PASSWORD
Remove-Item Env:JWT_SECRET_KEY
```

## 12. 全量回归、真实故障注入与路线图收口

**自动化回归**

```powershell
python -m pytest tests -q --basetemp E:\codex\2026-10-15\a\.pytest-stage1cd-final
Set-Location frontend
npm run test -- --run
npm run build
Set-Location ..
python -m compileall -q api.py config.py src migrations
python -m ruff check src api.py config.py tests
git diff --check
docker compose -f docker-compose.yml config --quiet
```

Ruff 未安装时记录“不可用”，不能写成通过；CI 中的 Ruff 必须实际通过后才能完成发布门禁。

**静态安全扫描**

```powershell
rg -n "allow_origins=\[\"\*\"\]|detail=str\(e\)|msg.*str\(e\)|hm_user_api_key.*localStorage|change-me-in-production|sk-your" api.py config.py src frontend/src docker-compose.yml docker-compose.production.yml
```

每个命中逐条分类。测试样本、开发提示和明确拒绝逻辑可以存在；生产默认值、公开异常透传和前端长期 Key 存储不得存在。

**真实故障注入**

在本地 Docker MySQL/Redis 环境逐项执行并记录：

- 正常启动：liveness 200、readiness 200、依赖状态符合配置。
- 停 Redis：liveness 仍为 200；readiness 按生产任务策略返回 503；限流进入保守降级；上传任务保持可恢复状态。
- 恢复 Redis：在状态 TTL 后 readiness 恢复，pending 任务被 Worker sweep 补偿。
- 停 MySQL：liveness 200、readiness 503，写接口返回统一依赖错误而非原始 SQL 异常。
- 模拟 LLM 超时：达到有限次数后熔断，后续请求快速失败；冷却后半开恢复。
- 禁用 Reranker/Langfuse/MCP：readiness 为 200+degraded，基本问答仍可运行且轨迹注明降级。
- Whisper 缺失：API 保持可就绪；Worker 音频能力按配置显示 unavailable，任务进入可重试失败状态。

**安全验收**

- 非白名单 Origin 不能跨域读取凭据响应。
- 伪造 `X-Forwarded-For` 不能绕过限流。
- 不存在用户和错误密码响应一致。
- 生产默认 Secret、危险 Base URL 和通配 CORS 均拒绝启动。
- 匿名用户不能调用管理写接口或绕过匿名问答开关。
- HTTP/SSE/日志/Trace 不出现测试 Secret、数据库 URL、绝对路径和第三方原始正文。

**最终文档**

- 完成 `docs/stage-1c-1d-security-reliability-audit.md`，写入真实命令、结果、耗时、警告和未验证项。
- 更新 README、Swagger、部署文档和 `agent非遗.md` 的阶段状态；只有全部门禁通过才将阶段 1 标记为完成。
- 更新 `task_plan.md`、`findings.md` 和 `progress.md`。

## 提交建议

计划在同一开发周期内形成以下可审查提交，最终一起交付，不分 1C/1D 发布：

1. `feat: add production security configuration gates`
2. `feat: add request security and distributed rate limits`
3. `feat: harden authentication secrets and error handling`
4. `feat: add dependency health and resilience controls`
5. `feat: align frontend deployment and operations security`
6. `docs: record stage 1 security reliability verification`

每次提交前运行对应定向测试；最终提交前必须通过全量回归和真实故障注入。不得为了保持提交数量而混入无关重构。
