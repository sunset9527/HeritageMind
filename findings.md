# Findings & Decisions: HeritageMind 阶段 1C+1D

## Requirements

- 将路线图阶段 1 的 Web/认证/密钥安全与健康检查/依赖降级一次完成。
- 不拆成两套设计、计划或发布。
- 生产环境默认关闭匿名问答。
- 完成后必须有自动化回归、真实依赖故障注入和可追溯验收记录。

## Research Findings

- 当前 `api.py` 使用 `allow_origins=["*"]`。
- 初始 `/health` 固定返回成功，不能反映数据库、Redis、检索器或模型状态；现已分为 live/ready/dependencies，生产 ready 使用短 Redis PING。
- 初始 HTTP/SSE 与工作流存在异常原文泄露风险；现已统一公开 envelope、SSE error event、前端兼容解析和日志脱敏。
- 用户自带 API Key 初始保存在 `localStorage.hm_user_api_key`；现已迁移到 `sessionStorage`。
- 开发 Compose 保留本地示例值；生产 Compose 现对 MySQL、JWT、服务器模型 Key 使用必填插值门禁。
- Redis 已用于缓存和后台任务，可复用为跨进程限流存储。
- 阶段 1B 已有请求体限制、独立 Worker、硬超时、任务状态机和 WorkerHeartbeat，可在其上扩展而不重做。
- 当前基线提交为 `7132d36`；后端基线 `480 passed, 1 skipped`，前端基线 `40 passed`。

## Technical Decisions

| Decision | Rationale |
|---|---|
| 固定窗口 Redis Lua 限流 | 原子、实现范围可控、足以满足当前单体部署 |
| 本地保守限流降级 | Redis 故障时不无限放行，同时明确多实例精度限制 |
| 进程内轻量熔断器 | 当前 API 单 worker；无需引入分布式熔断基础设施 |
| `/health/live` 无外部 I/O | 容器编排只需判断进程是否存活，不能因依赖抖动重启 API |
| `/health/ready` 区分 required/optional | 核心失败返回 503，可选失败返回 200+degraded |
| API Key 使用 sessionStorage | 满足关闭页面清除和刷新会话可用之间的平衡 |
| Base URL 使用 HTTPS/主机白名单 | 防止用户自定义模型地址成为 SSRF 通道 |
| 008 Alembic 迁移扩展心跳 | 持久化 Worker 总体状态和脱敏依赖摘要 |
| 生产 Redis 为 API readiness 必需项 | 后台任务、跨进程限流依赖共享 Redis；开发环境仅报告 degraded |

## Implementation Findings

- `Settings` 的生产环境契约已固定为 `dev/test/prod`（默认 `dev`），不能接受旧的长名称，以免生产门禁被错误环境名绕过。
- Base URL 校验是纯本地 URL/IP 解析，不做 DNS 或网络请求；生产仅允许 HTTPS、公共端口、白名单主机，开发本机 HTTP 须显式开启。
- 当前门禁已接入 API 与上传 Worker；请求上下文会绑定可信代理链尾，白名单 CORS 与安全头已覆盖 413 和错误响应。
- Redis 业务限流在生产环境不能安全访问共享 Redis 时必须 fail-closed，不能使用每进程内存额度伪装成分布式防护；登录/注册同时按账号和可信客户端 IP 限制。
- 限流 key 使用当前及旧 HMAC Key 生成，生产启动逐项拒绝空、默认或过短轮换 Key；轮换测试必须实际验证同一 Lua 调用的多 key 语义。
- 高成本操作并发许可已实现并正在独立规格审查；在其审查和后续全量验证完成前，阶段 1 仍为进行中。
- Starlette `TestClient` 在当前 Windows/Python 3.13 环境创建 AnyIO 的 Proactor event loop 时，会在 Windows `socketpair` 回退实现中阻塞；既有 HTTP 测试也可复现。不能把本机该类 HTTP 测试的超时归因于认证路由，Docker/Linux 集成验收仍是必要门槛。
- 用户 PowerShell 可正常运行 asyncio 定时器与 ASGI 定向测试；Codex 自动化终端对部分带定时器的 asyncio 测试会卡住，因此这些运行时验证由用户终端执行并保留真实输出。

## Issues Encountered

| Issue | Resolution |
|---|---|
| `writing-plans` 技能不可用 | 使用项目现有 `docs/plans` 格式生成完整 TDD 实施计划，并明确记录该替代方案 |
| 计划初稿引用了不存在的 `tests/test_auth.py` | 改为实施时新建 `tests/test_stage1cd_auth_http.py`，避免伪造现有测试入口 |
| 非提权 Git 状态检查间歇性报告“must be run in a work tree” | 确认 `.git/config`、`core.bare=false` 和工作目录存在；最终使用受控 Git 权限检查和提交 |

## Resources

- `docs/superpowers/specs/2026-10-22-stage-1c-1d-security-reliability-design.md`
- `docs/plans/2026-10-22-stage-1c-1d-security-reliability-plan.md`
- `docs/stage-1b-upload-resource-boundaries-audit.md`
- `E:/个人发展/002职业/项目2：agent非遗/agent非遗.md`

## Visual/Browser Findings

- 本任务没有依赖图片、页面截图或浏览器视觉判断。
