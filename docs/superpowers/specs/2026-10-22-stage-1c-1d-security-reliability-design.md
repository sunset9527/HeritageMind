# HeritageMind 阶段 1C+1D：Web 安全、认证、健康检查与依赖降级设计

设计日期：2026-10-22

基线提交：`7132d36 feat: complete stage 1b upload resource boundaries`

对应路线图：`agent非遗.md` 中“阶段 1（P0）：权限、安全与资源边界收口”的第 3、4 部分。

## 1. 背景与交付边界

阶段 1A 已完成管理员权限、资源归属和 published 可见性边界；阶段 1B 已完成上传校验、独立 Worker、有界解析和版本化索引。当前剩余风险集中在两个互相依赖的方面：Web/认证/密钥安全，以及健康检查/依赖降级。

本设计把原 1C 和 1D 作为一个交付包实施，不建立两套配置、异常协议或验收流程。完成后，阶段 1 才能整体标记为完成。

本次包含：

- 生产配置启动门禁与 CORS 白名单。
- 业务级限流和高成本操作并发控制。
- 密码策略、用户自带 API Key 的短期存储和 Base URL 安全校验。
- 请求标识、安全响应头、日志与错误脱敏。
- liveness、readiness、管理员依赖状态和 Worker 心跳。
- LLM、Embedding、Redis、MCP、Reranker、Whisper、Langfuse 的超时、有限重试、熔断和降级语义。
- 后端、前端、部署、故障注入与安全验收。

本次不包含：

- OAuth、短信、邮箱验证、刷新令牌和 HttpOnly Cookie 认证重构。
- Kubernetes、服务网格、独立 API Gateway、Celery 或 Prometheus 平台建设。
- 阶段 2 的知识资料扩充和阶段 7 的正式质量评测。
- 为追求“全依赖健康”而阻止只读页面或可降级能力启动。

## 2. 已确认的产品决策

- 生产环境默认关闭匿名问答；只有显式开启且配置服务器模型与匿名配额后才允许匿名调用。
- JWT 继续使用 Bearer Token，当前登录态存储机制不在本次改成 Cookie。
- 用户自带 API Key 默认只保存在运行内存或 `sessionStorage`，页面会话结束后自动消失；provider、模型名等非敏感偏好可继续保存在 `localStorage`。
- 限流以应用内统一组件为主，Redis 保存跨进程计数，Nginx 只承担连接层保护。
- MySQL 和活动检索能力属于 API 核心依赖；Reranker、Langfuse、MCP 等属于可选依赖。Redis 在生产后台任务链路中属于必需依赖，在问答缓存场景可以降级。
- 生产危险配置必须拒绝启动，不能只输出 warning。
- 所有降级必须在健康状态或可观察轨迹中显式呈现，不能把降级结果伪装成完整结果。

## 3. 总体架构

请求进入 FastAPI 后依次经过：

1. 请求体总量限制（沿用阶段 1B）。
2. 请求 ID 与可信代理客户端身份解析。
3. CORS 和安全响应头处理。
4. 认证与权限解析。
5. 业务类别限流及并发许可。
6. 路由与服务层处理。
7. 统一异常映射和脱敏日志。

外部依赖调用统一经过韧性组件。该组件负责超时、有限重试、并发上限、简单熔断和结果分类，并把状态更新到依赖健康注册表。健康接口只读取注册表和必要的轻量探测，不在每次请求中加载模型或执行昂贵推理。

后台 Worker 延续阶段 1B 的数据库状态机和 Redis 队列，增加 Worker 专属 readiness 与依赖状态，但不把 Worker 消费逻辑放回 API lifespan。

## 4. 配置与生产启动门禁

### 4.1 新配置

`config.py` 增加以下配置域：

- 运行环境：`APP_ENV`，取值限定为 `development/test/production`。
- CORS：允许来源列表、是否允许凭据。
- 功能开关：是否开放匿名问答。
- 配额：注册、登录、匿名问答、登录问答、AI 搜索、上传、索引重建的窗口和次数。
- 并发：LLM、Embedding、上传解析和后台维护任务的最大并发数。
- 网络边界：LLM、Embedding、Redis、MCP 的连接/读取/总超时和有限重试次数。
- 外部模型地址：允许的 API Base URL 主机列表及是否允许开发环境 HTTP localhost。
- 安全头：CSP、HSTS 和真实 HTTPS 标记。
- 依赖策略：每个依赖在 API/Worker 中属于 required 还是 optional。

列表类环境变量使用明确、可测试的解析规则；空项被过滤，非法 URL、非法窗口和非正数配额在 Settings 初始化阶段失败。

### 4.2 生产门禁

应用和 Worker 启动时调用同一个 `startup_validation` 服务。生产环境出现以下任一情况时拒绝启动：

- JWT Secret 为空、仍为示例值或长度不足。
- 数据库 URL 包含已知默认密码或缺少生产所需凭据。
- 开启服务器问答但模型 Key 为空或为占位值。
- CORS 包含 `*`，或携带凭据时来源列表为空。
- 开启匿名问答但服务器模型或匿名配额未配置。
- HSTS 开启但部署未声明真实 HTTPS。
- 外部模型 Base URL 使用非法协议、userinfo、未允许主机或明显的本机/内网地址；开发环境显式允许的 localhost 除外。

测试环境允许注入确定性配置。开发环境对危险值给出明确警告但不冒充生产安全。

## 5. CORS、请求身份和安全响应头

- `CORSMiddleware` 从通配来源改为配置白名单。
- 只有配置来源通过预检；不反射任意 `Origin`。
- 新增请求上下文中间件，为请求生成不可预测但不含业务信息的 `request_id`，并返回 `X-Request-ID`。
- 只有配置了可信代理层时才读取 `X-Forwarded-For`；否则使用直连地址，防止伪造 IP 绕过限流。
- 新增统一安全响应头：CSP、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、frame 限制和 Permissions Policy。
- HSTS 只在真实 HTTPS 生产环境启用。
- Nginx 保留必要安全头；应用层作为 API 直接暴露时的第二道保障。两层取值保持一致，避免相互覆盖成更宽松策略。

## 6. 限流与并发控制

### 6.1 限流身份

- 登录用户使用 `user_id`。
- 匿名请求使用可信代理规则解析后的客户端 IP。
- 登录和注册同时约束 IP 与规范化账号标识。
- 管理操作使用管理员 ID 与任务类别。

原始 API Key、JWT、邮箱全文和密码永远不能成为 Redis key 或日志字段。账号标识需要不可逆摘要。

### 6.2 默认配额

| 类别 | 默认配额 |
|---|---:|
| 注册 | 每 IP 每小时 5 次 |
| 登录 | 每 IP 每分钟 10 次；账号失败次数单独累计 |
| 匿名问答 | 生产默认关闭；开启后每 IP 每分钟 3 次 |
| 登录问答 | 每用户每分钟 10 次 |
| AI 搜索/MCP | 每用户每分钟 10 次 |
| 图片、音频、文档上传 | 每用户每分钟 5 次 |
| 三类索引重建 | 每管理员每小时 3 次，并保留同类任务互斥 |
| 普通只读接口 | 配置较宽的突发额度 |

配额必须全部可配置，但不能用 0 或负数表达“无限”；关闭限制必须使用显式开发配置，生产环境禁止关闭关键写接口限制。

### 6.3 存储与降级

Redis 使用固定窗口加原子计数和 TTL，实现跨进程配额。返回统一 `429`，同时包含 `Retry-After`、稳定错误码和 `request_id`。

Redis 不可用时采用进程内保守限流：额度不能比正常配置更宽，状态标记为 degraded。多实例下该方案不能提供全局精确计数，因此生产 readiness 会把后台任务 Redis 不可用视为不可就绪，而不是长期依赖本地降级。

### 6.4 并发边界

LLM、Embedding、上传解析和维护任务分别使用独立并发许可，不共享一个全局锁。达到上限时快速返回 `429` 或 `503`，并提供建议重试时间；已经进入数据库队列的后台任务继续按状态机处理。

## 7. 密码、认证与用户自带模型配置

### 7.1 密码策略

- 普通用户最少 10 位，管理员最少 12 位，最多 128 位。
- 拒绝全空白、与用户名/邮箱高度相同及内置小型弱密码集合中的密码。
- 不强制无意义的“大小写+数字+符号”组合。
- 已有密码不会批量失效；注册、初始化管理员和以后改密时执行新规则。
- 登录失败统一返回“用户名或密码错误”，不暴露账号是否存在。
- 管理员初始化和密钥轮换操作写入部署文档；密码和密钥本身不写入审计日志。

### 7.2 API Key 与 Base URL

- 前端设置 Store 初始化时从 `sessionStorage` 读取 API Key，不再从 `localStorage` 迁移旧值到新持久位置。
- 首次升级时删除历史 `hm_user_api_key`；设置页提示用户重新输入。
- 页面提供“一键清除密钥”，退出登录时一并清除。
- API Key 不进入 URL、Pinia 持久化、错误对象、日志或 Langfuse metadata。
- 后端只在单次请求上下文中使用 Key，确保正常、异常和 SSE 中断都执行清理。
- 用户提供的 Base URL 必须经过统一 URL 校验和允许主机策略；生产环境默认不允许任意自定义主机。

JWT Token 继续保存在现有位置，本次通过 CSP、输出编码和现有 DOMPurify 降低 XSS 风险；迁移到 HttpOnly Cookie 留给独立认证版本处理。

## 8. 统一错误、日志和 Trace 脱敏

### 8.1 公开错误协议

所有 HTTP 和 SSE 错误统一为：

```json
{
  "error": {
    "code": "dependency_unavailable",
    "message": "当前模型服务暂不可用",
    "request_id": "01..."
  }
}
```

错误码至少覆盖：参数错误、未认证、无权限、资源不存在、状态冲突、限流、并发繁忙、依赖超时、依赖不可用、配置错误和内部错误。

### 8.2 异常映射

- 路由不再向公开响应直接返回 `str(e)`。
- Agent 和 Workflow 内部错误可以进入受控事件记录，但公开回答只显示稳定、可行动提示。
- SSE 的 error event 与普通 HTTP 使用同一错误码和 request ID。
- 管理员任务详情保留 `error_code` 和截断后的脱敏摘要，不保存原始堆栈。
- 数据库错误、绝对路径、第三方响应正文和内部类名不得出现在公开响应。

### 8.3 脱敏范围

日志过滤器统一处理 `Authorization`、Cookie、API Key、JWT、数据库 URL、查询参数敏感字段和常见 Key 格式。Langfuse callback 只接收允许字段，不记录请求头和完整用户密钥。服务器内部堆栈保留在受控日志中，但同样先进行密钥与连接串脱敏。

## 9. 健康检查与依赖状态

### 9.1 接口

- `/health/live`：只确认进程和事件循环存活，不访问外部服务。
- `/health/ready`：检查实例是否能承接其核心职责；成功返回 200，核心依赖失败返回 503。
- `/health/dependencies`：管理员接口，返回脱敏后的详细依赖状态。
- `/health`：保留兼容入口，返回精简 readiness，不再固定 healthy。

所有响应包含状态、版本、检查时间和 request ID；不包含数据库地址、模型绝对路径、密钥或第三方原始异常。

### 9.2 依赖分类

| 依赖 | API | Worker |
|---|---|---|
| MySQL | required | required |
| 活动知识语料/检索器 | required | 索引任务 required |
| Redis | 生产任务链路 required；缓存可降级 | required |
| LLM | 开启服务器问答时 required | optional |
| Embedding | 语义问答按配置判定 | 索引任务 required |
| Reranker | optional | optional |
| Whisper | optional | 音频任务按开关判定 required |
| Langfuse | optional | optional |
| MCP/Web Tool | optional | optional |

required 失败使对应进程 unavailable；optional 失败使整体 degraded，但不阻止无关能力。功能关闭时状态为 disabled，不得误报 unavailable。

### 9.3 状态注册表

依赖状态使用 `healthy/degraded/unavailable/disabled/unknown`，记录最后成功时间、最后失败时间、稳定原因码和连续失败次数。健康接口读取注册表并做短 TTL 轻量探测，禁止在健康请求中加载 BGE、Reranker、Whisper 或执行完整问答。

Docker API Healthcheck 改用 `/health/live`，部署启动验收使用 `/health/ready`。Worker 继续写 `WorkerHeartbeat`，并附加自身总体状态；管理员文档列表保留 `online/stale/offline` 兼容字段。

## 10. 超时、有限重试、熔断和降级

建立共享韧性组件，调用方提供依赖名、超时、允许重试的异常类型、最大重试次数、并发组和降级策略。

统一规则：

- 只有幂等读取和确认属于瞬时错误的操作允许重试。
- 认证失败、参数错误、文件损坏、资源超限和业务冲突不得重试。
- 重试使用指数退避和小幅抖动，最大次数有限。
- 连续失败达到阈值后短时打开熔断器；半开只允许少量探测。
- 所有熔断和降级更新依赖状态，不把异常静默吞掉。

建议默认策略：

- LLM：请求级总超时，最多 1 次瞬时错误重试，持续失败短时熔断。
- Embedding API：批次有界，最多 1 次瞬时错误重试；本地模型加载失败按配置决定 API 降级或不可用。
- Redis：1 秒左右连接超时和短命令超时，请求链路不长时间重试。
- MCP/Web Tool：约 5 秒总超时，失败后标记工具不可用，不影响无工具回答。
- Reranker：加载或推理失败降级到原排序。
- Langfuse：始终可选，发送失败不阻断回答。
- Whisper、PDF/OCR、索引：沿用阶段 1B spawn 子进程硬超时和数据库可重试状态，不套用网络调用重试。

任何降级都要在内部执行轨迹和管理员依赖状态中记录原因。公开回答只在降级会实质影响答案能力时给出简洁提示。

## 11. 数据流与典型失败行为

### 11.1 登录问答

请求 ID → JWT 解析 → 用户级限流 → LLM 并发许可 → 检索与依赖韧性包装 → 统一响应。Redis 缓存故障时使用受限内存缓存；Reranker 故障时保留原排序；LLM 不可用时返回稳定 `dependency_unavailable`，不泄露供应商正文。

### 11.2 匿名问答

生产开关关闭时直接返回 403。开启时必须同时满足服务器模型可用、IP 配额和并发许可，不接受匿名 BYOK 绕过配额。

### 11.3 上传和索引

管理员权限 → 用户级限流 → 阶段 1B 文件校验 → 数据库状态 → Redis 通知。Redis 失败保留 pending 状态并显示 degraded；Worker readiness 变为 unavailable。重建任务继续使用同类互斥和版本化切换。

### 11.4 健康检查

liveness 永远不等待外部依赖；readiness 使用短超时轻量探测和状态缓存。可选依赖失败返回 200 + degraded；核心依赖失败返回 503 + unavailable。

## 12. 测试设计

实施继续遵循 TDD。至少增加：

- 配置和启动门禁测试：生产默认密钥、通配 CORS、危险 Base URL、匿名问答缺配置。
- CORS 和安全头测试：合法预检、非法来源、凭据、CSP、HSTS 条件和 request ID。
- 限流测试：不同类别、用户/IP 隔离、双键登录限制、`Retry-After`、Redis 原子计数和本地降级。
- 并发测试：许可释放、取消请求、异常路径、达到上限快速失败。
- 认证测试：普通密码、管理员密码、弱密码、账号枚举防护。
- 前端密钥测试：不再写 localStorage、刷新会话行为、一键清除、退出清除和请求头注入。
- 错误脱敏测试：HTTP、SSE、日志、任务详情和 Langfuse metadata 均不出现测试密钥、绝对路径和连接串。
- 健康检查测试：liveness 零外部 I/O，required/optional/disabled 各状态，503 语义和短 TTL。
- 韧性测试：超时、只重试瞬时错误、熔断开/半开/恢复、并发许可回收和降级轨迹。
- 部署契约测试：Docker healthcheck、环境变量、Nginx 安全头和生产示例无默认密钥。
- 故障注入：MySQL、Redis、LLM、Embedding、MCP、Reranker、Whisper 分别不可用时的预期状态。

阶段 1A/1B 测试必须全部保留，不能通过放宽权限、上传或草稿可见性预期换取通过。

## 13. 主要代码边界

计划新增：

- `src/middleware/request_context.py`
- `src/middleware/security_headers.py`
- `src/middleware/rate_limit.py`
- `src/services/startup_validation.py`
- `src/services/dependency_health.py`
- `src/services/resilience.py`
- `src/services/error_sanitizer.py`
- `src/schemas/health.py`

计划重点修改：

- `config.py`、`api.py`
- `src/services/auth.py`、`src/deps.py`
- `src/utils/llm.py`
- `src/retrieval/embeddings.py`、`src/retrieval/reranker.py`
- `src/services/cache.py`、`src/services/queue.py`、`src/services/mcp_tools.py`
- `src/workers/upload_worker.py`
- `frontend/src/stores/settings.ts`
- `frontend/src/api/client.ts`、`frontend/src/api/query.ts`
- `frontend/src/views/SettingsView.vue`
- Docker、Compose、Nginx、`.env.example`、README 和部署文档

`api.py` 只负责装配中间件、依赖和路由；配置校验、限流、健康判断、脱敏和韧性逻辑必须放入独立模块，避免继续扩大单文件职责。

## 14. 迁移与兼容策略

- `/health` 保留，但语义从固定 healthy 改为精简 readiness；新增接口提供明确分层。
- 前端升级时主动删除旧 `localStorage.hm_user_api_key`，不读取并搬运明文密钥。
- 现有用户密码保持可登录，新策略只作用于注册、初始化管理员和以后改密。
- 现有错误响应的 HTTP 状态码尽量保持；响应体统一后同步更新前端解析和 OpenAPI。
- 限流默认值写入 `.env.example`，开发环境保留合理宽松配置，生产示例不提供危险兜底值。
- 如健康状态需要持久化 Worker 依赖摘要，应通过新的 Alembic 迁移增加字段；禁止依赖 `create_all()` 偷改生产表。

## 15. 验收门槛

只有同时满足以下条件，才可把路线图阶段 1 标记为完成：

- 阶段 1A、1B 全量回归无退化。
- 新增 1C+1D 自动化测试全部通过。
- 生产危险配置会拒绝启动。
- 不存在通配凭据 CORS、匿名管理写入或任意外部 Base URL。
- 高成本入口具有权限、限流、并发、超时和有限重试边界。
- 用户 API Key 不进入 localStorage、日志、Trace、URL 或公开错误。
- readiness 能真实区分核心失败与可选降级。
- 所有降级可观察且不冒充完整能力。
- HTTP、SSE 和任务错误不泄露底层异常、密钥、连接串和绝对路径。
- 后端全量测试、前端全量测试、生产构建、编译、迁移和两套 Compose 配置通过。
- 在真实 MySQL/Redis 容器上完成断连与恢复验收，并保存结果。
- README、Swagger、部署文档、`.env.example` 和路线图状态一致。

Ruff、Docker 或真实模型在执行环境不可用时必须记录为“未验证”，不能写成通过；任何指标和测试数量只记录实际命令输出。
