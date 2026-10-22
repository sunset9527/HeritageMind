# Findings & Decisions: HeritageMind 阶段 1C+1D

## Requirements

- 将路线图阶段 1 的 Web/认证/密钥安全与健康检查/依赖降级一次完成。
- 不拆成两套设计、计划或发布。
- 生产环境默认关闭匿名问答。
- 完成后必须有自动化回归、真实依赖故障注入和可追溯验收记录。

## Research Findings

- 当前 `api.py` 使用 `allow_origins=["*"]`。
- 当前 `/health` 固定返回成功，不能反映数据库、Redis、检索器或模型状态。
- 多个 HTTP/SSE 分支直接返回 `str(e)`，存在内部错误和路径泄露风险。
- 用户自带 API Key 当前保存在 `localStorage.hm_user_api_key`。
- 当前开发 Compose 含示例 JWT Secret，生产 Compose 依赖外部变量但缺少应用启动门禁。
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
