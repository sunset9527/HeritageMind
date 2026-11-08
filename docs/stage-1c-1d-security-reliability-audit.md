# HeritageMind 阶段 1C+1D 安全与可靠性验收记录

更新日期：2026-11-02

## 当前结论

阶段 1C+1D 的代码、定向测试、后端/前端全量回归、前端生产构建、Compose 静态配置，以及 API 的真实 MySQL/Redis、LLM、Embedding、Reranker、MCP 故障注入均已完成。高成本并发许可也已完成代码复审和真实 Docker 并发压测。

阶段 1 仍**不标记为完成**：用户于 2026-11-02 要求暂停剩余工作；尚未执行 Worker Redis 心跳断连恢复和 Whisper 实际任务失败链路。两项均记录为“暂停、未验收”，不将其写成通过或失败。

## 已验证内容

| 项目 | 实际命令或验证 | 结果 |
|---|---|---|
| 后端全量回归 | `python -m pytest tests -q --basetemp .pytest-tmp-stage1-full` | `610 passed, 1 skipped, 6 warnings in 34.51s` |
| 阶段 1 定向回归 | 依赖健康、部署、韧性、MCP、错误协议、脱敏、工作流安全测试 | `36 passed, 6 warnings in 17.66s` |
| Redis 故障公开契约 | 真实 API route 的 3 种 Redis 失败模拟 + 429 envelope | `4 passed, 6 warnings in 9.18s` |
| 前端全量回归 | `npm run test -- --run` | `24` files、`49 passed`，8.33 秒 |
| 前端生产构建 | `npm run build` | 通过；存在既有 Rollup PURE 注释与大于 500 kB chunk 提示 |
| 迁移 | SQLite `001→...→008→007→008` | 通过（此前定向验证） |
| 编译 | `python -m compileall -q api.py config.py src migrations` | 通过（本轮相关模块已再次编译） |
| 开发 Compose | `docker compose -f docker-compose.yml config --quiet` | 通过 |
| 生产 Compose 必填 Secret | 缺失变量解析失败；注入临时占位值后 `config --quiet` | 两种行为均符合预期 |
| LLM 不可用 + SERVER_LLM 许可 | 隔离生产 API 使用临时无效模型 Key，并发发送 5 个不同 `/query` 请求（上限 4） | 4 个请求安全降级为 200；超额请求约 0.37 秒返回统一 `503 busy`；发现并修复同步工作流阻塞事件循环的问题 |
| Embedding 不可用 | 隔离 API 中本地 BGE-M3 路径缺失、无 API Key | 初始化抛出受控 `RuntimeError`；`MultiSourceRetriever` 仍返回 3 条关键词检索结果 |
| Reranker 不可用 | 隔离 API 中实际缺少 `sentence_transformers` | `_available=False`；候选按已有 `score` 稳定排序 |
| MCP 网络不可用 | 隔离 API 的 Web MCP 连接关闭的本机 HTTPS 端口 | 返回 `unavailable`，健康注册表记录 `unavailable/retry_exhausted`，不泄露网络异常正文 |
| 高成本并发许可复审 | 路由/Worker 许可映射、释放/取消路径复审 + 上述真实并发压测 | 通过；`/query` 改为 `asyncio.to_thread`，LLM 请求覆盖改为 `ContextVar`，避免阻塞与跨请求串用 |

## 警告说明

- `jieba/pkg_resources`：第三方弃用警告。
- LangGraph：`allowed_objects` 默认值将在未来变更的弃用警告。
- Pydantic：现有 class-based `Config` 将在 Pydantic v3 移除的弃用警告。

以上 warning 未导致测试失败，不在本次安全可靠性改动中修复。

## 本轮关键验收点

- 用户 API Key 仅使用 `sessionStorage`；退出和清除操作会移除它。
- HTTP 错误使用 `{ "error": { "code", "message", "request_id" } }`；SSE 使用相同 code/message/request_id 语义。
- 密钥、数据库 URL、绝对路径和上游异常原文不会进入公开错误、工作流降级结果或已安装 handler 的日志输出。
- `/health/live` 不做外部 I/O；`/health/ready` 检查 MySQL、检索器和 Redis。Redis 在 `prod` 为必需依赖，在 `dev/test` 显式呈现为可观察降级。
- Worker 心跳包含仅含状态与原因码的依赖摘要；008 迁移已经过升级/回退烟雾验证。
- MCP/Web 调用有 5 秒总超时、一次瞬时错误重试、熔断和健康状态更新。
- 生产 Compose 要求显式提供 `MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`JWT_SECRET_KEY`、`DEEPSEEK_API_KEY` 与 `RATE_LIMIT_HMAC_KEY`。

## 发布前未验证项

以下内容尚未在与发布配置一致的环境执行；已按用户要求暂停：

1. 启动 Worker 后停止 Redis：确认持久化心跳写入 `unavailable/connection_failed`，恢复后重新写入 healthy。
2. 构造真实音频任务并使 Whisper 模型目录或推理不可用：确认 Worker 标记任务失败、记录脱敏原因且保持存活。

在恢复并确认上述两项前，路线图的阶段 1 状态为“暂停（待真实 Worker/Whisper 验收）”。

## 2026-11-02 容器故障注入尝试

- 已确认 Docker Desktop 可访问，但当前运行的容器均属于 LexRAG；未对它们做任何暂停或改动。
- 当前仓库的 HeritageMind Compose 栈起初没有运行容器。前台构建输出随后确认根因：前端独立构建上下文包含 `frontend/.pytest_cache`，Docker 无权读取该目录，因而取消并行 API/Worker 构建。
- 已新增 `frontend/.dockerignore` 排除 `.pytest_cache/`、`node_modules/`、`dist/` 等生成物；相应部署契约测试通过。用户决定延后故障注入，因此未再次启动完整 Compose 栈。
- 已停止由本次验证启动的卡住 Compose 进程，并再次确认 HeritageMind 容器列表为空。没有删除卷、镜像、容器或数据。
- 随后用户要求继续真实故障注入。为与发布行为一致，发现并修复生产 Compose 未固定 `APP_ENV=prod`、未要求 `RATE_LIMIT_HMAC_KEY` 的缺口；新增契约测试覆盖这两项。
- 使用独立项目名 `heritagemind-injection` 启动 MySQL、Redis、API，临时测试密钥仅存在于启动进程环境，未写入 `.env`。基线 `/health/ready` 为 200，MySQL、检索器与 Redis 均为 healthy。
- 停止该隔离 Redis 后：`/health/live` 为 200；`/health/ready` 为 503，Redis 状态为 `unavailable/connection_failed`；公共 `/crafts` 为 503，错误包为 `rate_limit_unavailable`，无上游 Redis 细节。重新启动 Redis 后，readiness 与 `/crafts` 均恢复 200。
- 停止该隔离 MySQL 后：`/health/live` 为 200；`/health/ready` 为 503，MySQL 状态为 `unavailable/connection_failed`。重新启动 MySQL 并等待 `mysqladmin ping` 成功后，liveness 和 readiness 均恢复 200。
- 后续隔离 API 镜像完成重建后，实际并发压测确认上限 4 时第 5 个请求返回 `503 busy`；4 个已获许可请求在无效临时模型 Key 下走安全回答降级。为此新增 `asyncio.to_thread` 执行同步工作流，并用 `ContextVar` 隔离线程间的请求级 LLM 覆盖。
- 在同一隔离 API 容器中确认：本地 Embedding 缺失时关键词检索仍返回结果；Reranker 依赖缺失时按已有分数排序；MCP 到关闭 HTTPS 端口时返回 `unavailable/retry_exhausted`。
- Worker 专用镜像第二次后台构建仍在下载 PyTorch 时，用户要求暂停剩余工作；已停止该构建。未启动 Worker，未将 Worker 心跳或 Whisper 失败链路记为已验证。
