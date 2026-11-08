# Task Plan: HeritageMind 阶段 1C+1D 合并实施

## Goal

一次完成 Web/认证/密钥安全、真实健康检查和依赖降级，使路线图阶段 1 达到可验证的完成标准。

## Current Phase

Phase 4/5: Verification and delivery — API-side真实验收完成；Worker/Whisper 验收按用户要求暂停

## Phases

### Phase 1: Requirements & Discovery

- [x] 对照 `agent非遗.md` 确认阶段 1 剩余范围
- [x] 检查当前 CORS、健康检查、密钥存储、错误响应和依赖超时实现
- [x] 记录基线提交与验证结果
- **Status:** complete

### Phase 2: Design & Planning

- [x] 确认 1C+1D 使用单一交付包
- [x] 完成并提交合并设计文档
- [x] 完成总实施计划
- **Status:** complete

### Phase 3: Implementation

- [x] 严格按 TDD 实现配置门禁、安全中间件、限流、认证、脱敏、健康检查和韧性组件；API 侧最终集成验收完成
- [x] 更新前端 API Key 生命周期
- [x] 更新 Worker 心跳、迁移和部署配置
- **Status:** complete（Worker/Whisper 真实运行验收属于 Phase 4）

已验证子包：配置/启动门禁、请求安全中间件、Redis 业务限流及其生产 fail-closed 与 HMAC 轮换加固；密码/API Key 生命周期、统一错误与日志脱敏、依赖健康、008 迁移、MCP 韧性和部署门禁。高成本操作并发许可已完成路由/Worker 映射复审与真实 Docker 压测；同步工作流已转入线程执行，请求级 LLM 覆盖已改为 `ContextVar` 隔离。

本轮新增：新注册/管理员初始化密码策略、旧密码登录兼容、BYOK 的 sessionStorage 生命周期已实现并通过定向测试；HTTP/SSE 统一错误 envelope、前端兼容解析、日志过滤、依赖健康检查、008 迁移与 MCP/Web 韧性组件也已完成定向测试。

后续新增：依赖健康注册表、`/health/live`、`/health/ready`、管理员 `/health/dependencies`、Worker 依赖摘要和 `008` 迁移已实现并完成定向与真实 SQLite 升级/回退验证。生产 Compose 对 MySQL、JWT 和服务器模型 Key 已强制必填；API readiness 在生产会以短 Redis PING 作为核心依赖。仍未完成：全量回归、真实 MySQL/Redis 断连恢复故障注入、最终验收记录与路线图状态更新。

### Phase 4: Testing & Verification

- [x] 运行定向测试与后端、前端全量回归
- [x] 运行迁移、编译、静态扫描和 Compose 校验
- [x] 完成生产 API 的真实 MySQL/Redis 故障注入与恢复记录
- [x] 完成 LLM、Embedding、Reranker、MCP 的真实 API/容器故障注入与降级记录
- [x] 完成高成本并发许可的真实压测与复审结论
- [ ] 完成 Worker 真实 Redis 故障心跳验证（**已暂停**）
- [ ] 完成 Whisper 模型/推理不可用的真实音频任务失败验证（**已暂停**）
- **Status:** paused（用户于 2026-11-02 要求暂停剩余 Worker/Whisper 验收）

### Phase 5: Delivery

- [x] 更新 README、部署说明和安全验收记录
- [x] 更新验收记录、路线图状态与暂停项
- [ ] 确认工作区干净并提交最终实现
- **Status:** paused（等待用户恢复剩余验收或决定以当前边界交付）

## Key Questions

1. 匿名问答生产默认是否开放？已决定：关闭，只有显式配置模型与配额后开放。
2. Redis 故障是否允许无限放行？已决定：不允许，使用更保守的进程内限流，并让生产任务链路 readiness 失败。
3. 是否在本阶段迁移 JWT 到 Cookie？已决定：不迁移，保持 Bearer Token，避免扩大范围。

## Decisions Made

| Decision | Rationale |
|---|---|
| 1C+1D 单一交付 | 安全配置、错误协议、健康状态和降级逻辑互相依赖，拆开会形成临时不一致状态 |
| 应用内 Redis 限流 | 能同时识别用户、IP 和业务类别，复用现有 Redis，不引入 API Gateway |
| 生产危险配置拒绝启动 | 安全门禁不能依赖人工阅读 warning |
| 可选依赖失败进入 degraded | 避免 Langfuse、Reranker 等非核心能力拖垮整站 |
| 新增 008 迁移扩展 WorkerHeartbeat | Worker 依赖状态需要持久、可观测且不能依赖 create_all 偷改表 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 当前会话没有 `writing-plans` 技能 | 1 | 使用已确认设计、项目既有计划格式和 `planning-with-files` 生成合并实施计划 |
| 沙箱内非提权 `git status` 间歇性误报非工作树 | 1 | 文件系统读写正常；记录环境问题，最终 Git 检查和提交使用受控提权 |
| PowerShell 中复合 `rg` 正则引号解析失败 | 1 | 不重复原命令；拆成不含嵌套转义的简单模式检查 |

## Notes

- 开始实现前重新阅读正式设计、实施计划和 `findings.md`。
- 所有功能先写失败测试，再写最小实现。
- 不得为了测试通过而放宽阶段 1A/1B 的权限、上传和草稿隔离预期。
- 所有测试数量和故障注入结论只记录真实命令输出。
