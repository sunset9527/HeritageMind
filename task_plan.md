# Task Plan: HeritageMind 阶段 1C+1D 合并实施

## Goal

一次完成 Web/认证/密钥安全、真实健康检查和依赖降级，使路线图阶段 1 达到可验证的完成标准。

## Current Phase

Phase 3: Implementation — concurrency permits under independent specification review

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

- [ ] 严格按 TDD 实现配置门禁、安全中间件、限流、认证、脱敏、健康检查和韧性组件
- [ ] 更新前端 API Key 生命周期与错误解析
- [ ] 更新 Worker 心跳、迁移和部署配置
- **Status:** in_progress

已验证子包：配置/启动门禁、请求安全中间件、Redis 业务限流及其生产 fail-closed 与 HMAC 轮换加固。高成本操作并发许可已实现并提交，正等待独立规格复审；阶段 3 其余范围尚未实施。

### Phase 4: Testing & Verification

- [ ] 运行定向测试与后端、前端全量回归
- [ ] 运行迁移、编译、静态扫描和 Compose 校验
- [ ] 完成真实 MySQL/Redis 故障注入并记录结果
- **Status:** pending

### Phase 5: Delivery

- [ ] 更新 README、Swagger、部署说明、路线图和安全验收记录
- [ ] 确认工作区干净并提交最终实现
- **Status:** pending

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
