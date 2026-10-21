# HeritageMind 阶段 1B：上传、文件与资源边界设计

- 日期：2026-10-20
- 状态：已确认，待实施
- 对应路线图：`agent非遗.md` 阶段 1「上传、文件与资源消耗安全」
- 前置提交：阶段 1A 授权边界已完成并审计

## 1. 背景与问题

当前上传链路存在四类边界缺口：

1. `/documents/upload` 使用 `await file.read()` 无界读取，并把 `craft_name + "_upload.txt"` 直接写入生效语料目录；这同时带来路径穿越、覆盖、资源耗尽和未审核内容污染 RAG 的风险。
2. `/media/upload` 只信任声明的 `content_type`，同步全量读取后落盘；数据库提交失败会留下孤儿文件。
3. `/search/similar` 对公开上传图片无大小和真实格式约束，并直接全量读入内存。
4. 音频虽通过 Redis 排队，但消费者由 API lifespan 启动；PDF/OCR、音频转写和索引重建缺少统一的页数、时长、文本量及硬超时边界。

阶段 1B 必须一次覆盖入口校验、路径安全、分块落盘、草稿隔离、独立 worker、资源限额、失败恢复及部署配置，且不能把 `craft_name` 当成 `craft_id`。

## 2. 目标与非目标

### 2.1 目标

- 三类上传入口共享一套可测试的安全校验和有限读取机制。
- 存储路径只由服务端内部 ID/UUID 决定，用户字段不参与路径拼接。
- 文件扩展名、声明 MIME 和真实文件签名必须一致。
- FastAPI 在 multipart 解析前限制整个请求体，业务处理再执行按类型的更小上限。
- 文档、OCR、转写和索引任务在独立 worker 中执行，Web 进程只做有限校验、持久化和入队。
- 数据库是任务状态真相；Redis 消息丢失或重复都不会丢任务或重复处理。
- 所有上传默认草稿；文档解析成功也不会自动进入公开检索和生成。
- 文件、数据库、队列和索引之间发生部分失败时，可清理、恢复或安全重试。
- 保持现有前端和仅提交 `craft_name` 的旧客户端渐进兼容。

### 2.2 非目标

- 本阶段不实现文档审核、发布到正式 RAG 的完整内容治理流程；该接线属于后续内容治理阶段。
- 不引入对象存储、Celery、RQ、病毒扫描服务或新的外部基础设施。
- 不声称上传文件绝对安全；本阶段提供格式、资源、路径和进程隔离边界，不替代专用恶意文件检测。
- 不伪造性能或安全指标；验收只记录实际执行结果。

## 3. 方案选择

采用“统一持久化任务管线”：

- API 分块接收、校验、落盘、建草稿记录并入队。
- Redis 只传递带版本的任务通知。
- 数据库保存状态、尝试次数、错误和产物元数据。
- 独立 worker 扫描补偿并调用受隔离的处理子进程。

未采用以下方案：

- 仅在 API 内增加大小检查：不能满足耗时任务与 Web 进程隔离要求。
- 对象存储 + Celery/RQ + 扫毒服务：对当前单机/单 worker 项目过重，并扩大部署面。

## 4. 总体架构与数据流

```text
客户端
  -> API 鉴权/授权
  -> CraftCatalog 规范化 craft_id/craft_name
  -> UploadGuard
       - 参数和原文件名检查
       - 扩展名/MIME/签名一致性
       - 分块读取、大小计数、SHA-256
       - UUID .part 临时文件
  -> 数据库草稿/任务记录
  -> 原子改名
  -> Redis 通知（失败可由 DB sweep 补偿）
  -> 独立 worker 原子抢占
  -> 隔离处理子进程（解析/OCR/转写/Embedding）
  -> 原子发布产物或记录失败
```

### 4.1 媒体上传

- `/media/upload` 接受 `craft_id` 优先、`craft_name` 兼容的表单。
- 两者同时存在时必须映射到同一目录项。
- 图片校验成功后以 UUID 存储，数据库状态为 `draft`。
- 音频在文件校验成功后创建 `MediaDocument` 与 `AudioTranscript`，提交后通知 worker。
- Redis 不可用时保留 `UPLOADED` 状态，由 worker 启动/周期 sweep 补入队。

### 4.2 文档上传

- `/documents/upload` 不再解析正文，也不再写入 `crafts_doc_path`。
- 原文件以 UUID 存入文档隔离区，创建 `DocumentUpload` 草稿和 `pending` 处理状态。
- 接口返回 `202 Accepted` 和文档任务标识。
- worker 把解析结果写入 UUID 临时产物，完整成功后原子改名并置为 `ready`。
- `ready` 只表示解析完成，审核状态仍为 `draft`，不会进入公开展示、搜索或生成。

### 4.3 以图搜图

- `/search/similar` 仅接收受支持图片。
- 使用同一图片校验器和有限读取器，最大 10 MiB。
- 校验后的字节只在当前请求内使用，不持久化。
- `top_k` 限制为 1～20。

## 5. 技艺目录与输入规范化

新增共享 `CraftCatalog`，替代 `/crafts` 与 `_get_craft_list()` 的重复目录：

- 优先读取活动图书投影；不存在时使用旧版 23 项目录。
- `craft_id` 必须命中目录，不允许客户端自造。
- 只传 `craft_name` 时，必须能唯一反查 `craft_id`。
- 同时提交但不匹配时返回客户端错误。
- 服务内部始终同时保留规范 `craft_id` 和规范 `craft_name`，不混用二者。

原始文件名只作为数据库显示字段：

- 拒绝 `/`、`\\`、盘符、绝对路径、控制字符和超长名称。
- 不通过 `Path(filename).name` 静默修复恶意路径；非法输入直接失败。
- 磁盘文件名只使用服务端 UUID 和校验后的固定扩展名。

`media_type` 使用枚举，只允许 `image` 或 `audio`。所有最终路径在写入前 `resolve()`，并验证仍位于配置的存储根目录内。

## 6. 格式与默认资源限额

所有数值进入 `Settings`，支持环境变量覆盖；测试固定验证默认边界。

| 类型 | 允许格式 | 字节上限 | 处理上限 |
|---|---|---:|---|
| 图片/以图搜图 | JPEG、PNG、WebP | 10 MiB | 可解码；宽高及总像素受限 |
| 音频 | MP3、WAV、M4A、FLAC、OGG | 50 MiB | 最长 30 分钟 |
| PDF | PDF | 25 MiB | 最多 100 页、最多 25 个 OCR 页 |
| Word | DOCX | 15 MiB | ZIP 成员数、解压总量、压缩比受限 |
| Markdown/TXT | UTF-8 文本 | 2 MiB | 最多提取 500,000 字符 |

额外规则：

- 扩展名、声明 MIME、文件签名三者必须相容。
- 拒绝 SVG、HTML、旧版 `.doc`、宏文档、伪装 ZIP 和含 NUL 的文本。
- 图片使用解码器验证，拒绝解压炸弹和异常尺寸。
- DOCX 必须包含合法的 Office Open XML 必要成员，且不能突破解压边界。
- 文档任务默认硬超时 180 秒；音频任务默认硬超时 20 分钟。
- Nginx 请求总上限设为 `52m`，应用继续按类型执行更严格的上限。

## 7. 数据模型

### 7.1 MediaDocument

新增：

- `craft_id`：新记录由服务保证非空；旧记录允许暂时为空。
- `content_sha256`：新记录保存实际内容摘要；旧记录可为空。
- `uploaded_by_user_id`：记录管理员操作者；旧记录可为空。

现有 `status=draft/reviewed/published` 继续只表示审核状态。音频处理状态仍由 `AudioTranscript` 表示。

### 7.2 DocumentUpload

新增独立表，至少包含：

- 身份：`id`、`craft_id`、`craft_name`
- 操作者：`uploaded_by_user_id`
- 文件：`storage_name`、`original_name`、`extension`、`mime_type`、`size_bytes`、`content_sha256`
- 产物：`parsed_storage_name`、`char_count`、`page_count`、`ocr_page_count`
- 状态：`review_status`、`processing_status`
- 运维：`attempts`、`error_code`、`error_message`、`started_at`、`finished_at`、`created_at`、`updated_at`

审核状态初始为 `draft`。处理状态为：

```text
pending -> processing -> ready
                      -> failed
```

### 7.3 MaintenanceJob

索引维护任务至少包含：

- `kind`：知识 Embedding 重建或图片索引维护
- `status`：`pending/processing/ready/failed`
- `attempts`、`error_code`、`error_message`
- 输入规模、输出版本、开始/完成时间

### 7.4 WorkerHeartbeat

新增单行/按 worker 实例更新的心跳表，至少包含 `worker_id`、`started_at`、`last_seen_at` 和版本信息。管理接口以数据库心跳判断消费者是否在线，不把 Redis 是否可达误当成 worker 是否健康。

### 7.5 迁移兼容

新增 `007_stage1b_upload_boundaries.py`。旧项目的媒体/音频表曾由 `create_all()` 创建而未完整进入 Alembic 历史，因此迁移必须兼容：

- 新数据库：创建缺失的媒体、音频、文档上传和维护任务表。
- 已有数据库：保留数据，只补充缺失列、索引和约束。
- 只对可唯一映射的旧 `craft_name` 回填 `craft_id`；无法可靠映射的保持空值供审计。
- 迁移测试覆盖 SQLite，并生成/检查 MySQL 兼容结构；不依赖修改生产数据凑结果。
- 迁移记录哪些旧表由 007 新建，降级时不误删原本由 `create_all()` 管理的既有表；新增业务表和新增列按可逆边界处理。

## 8. 任务队列、幂等与恢复

统一 Redis 消息格式：

```json
{"version": 1, "kind": "document_parse", "entity_id": 42}
```

支持的 `kind` 至少包括文档解析、音频转写、知识索引重建、图片索引维护和音频索引重建。

- 消息只携带任务类型与实体 ID，不携带正文、路径或密钥。
- worker 使用条件更新原子抢占，重复消息不会重复执行。
- 数据库是状态真相；worker 启动及运行期间扫描 `pending` 和陈旧 `processing` 记录。
- 处理任务最大尝试次数默认 3 次。
- `failed` 且未达到上限的文档可由管理员显式重试。
- 正在 `processing` 的文档拒绝删除并返回 `409`。
- 删除可删除状态的草稿时，同时清理原文件、解析产物和数据库记录。

## 9. 解析与硬超时隔离

FastAPI 增加最外层 ASGI 请求体计数器，在 Starlette 解析 multipart、生成 `UploadFile` 之前执行 52 MiB 总上限；即使请求使用 chunked transfer、没有可信 `Content-Length`，也会在越界时停止继续接收。业务上传服务随后按文件类型执行更严格的 2/10/15/25/50 MiB 上限。

API 不执行 OCR、Whisper、Embedding 或全库索引。独立 worker 由调度器和受隔离处理子进程组成：

- 调度器持有数据库状态、心跳、重试和最终状态迁移。
- 子进程执行高开销解析；模型在处理进程内懒加载。
- 调度器按任务类型等待固定截止时间，超时后终止并重建处理进程。
- 不使用 `asyncio.wait_for(asyncio.to_thread(...))` 充当硬超时，因为线程会继续运行。

处理器二级限制：

- PDF 打开后先检查页数；逐页检查累计字符、OCR 页数、渲染像素和截止时间。
- DOCX、Markdown、TXT 在累计文本达到上限时失败，不静默截断为看似完整的正文。
- 依赖缺失或解析失败必须返回结构化失败，不把“某依赖未安装”写成正文。
- 音频先用 PyAV 检查真实时长和可解码性，再调用 Whisper；转写结果文本同样受总量限制。
- 音频全文成功后再建向量索引；索引失败保留全文，重试时不重复转写。
- 子进程只写临时产物，父调度器确认成功后执行原子改名和数据库提交。

## 10. 索引维护

`/knowledge/rebuild-embeddings` 改为创建维护任务并返回 `202`：

- 默认最多处理 1,000 篇、总计 5,000,000 字符、最长 10 分钟。
- worker 在版本化临时目录中构建完整索引。
- 全部成功后通过 `os.replace()` 原子替换小型活动版本清单；不依赖 Windows 不支持的目录原子替换语义。
- API 在请求边界检测版本变化并安全换载。
- 失败或超时保留上一个完整索引，不暴露半成品。

`/search/index-images` 同样改为维护任务，避免接口未来执行真实图片索引时重新阻塞 Web 进程。

`/search/audio/index` 当前会在请求内遍历全部已转写音频并重放向量，同样改为维护任务；重建先写新的版本化 collection，成功后切换活动 collection，失败继续使用旧 collection。

## 11. API 契约

### 11.1 调整

- `POST /media/upload`
  - 新增可选 `craft_id`，保留 `craft_name`。
  - 返回规范技艺字段、SHA-256、审核状态和音频处理状态。
- `POST /documents/upload`
  - 接受渐进式技艺参数。
  - 返回 `202`、`document_id`、`processing_status=pending`、大小和摘要。
- `POST /knowledge/rebuild-embeddings`
  - 返回 `202` 和维护任务 ID。
- `POST /search/index-images`
  - 返回 `202` 和维护任务 ID。
- `POST /search/audio/index`
  - 返回 `202` 和维护任务 ID。

### 11.2 新增管理员接口

- `GET /admin/documents`
- `GET /admin/documents/{id}`
- `POST /admin/documents/{id}/retry`
- `DELETE /admin/documents/{id}`

现有音频状态及重试接口保持兼容，只替换底层消费者。

### 11.3 错误语义

- `400/422`：参数或映射无效
- `401`：未认证
- `403`：非管理员访问写接口
- `413`：请求字节超限；异步处理发现页数/时长等超限时记录等价的结构化失败码
- `415`：格式不支持或扩展名/MIME/签名不一致
- `409`：当前任务状态不允许重试或删除

## 12. 文件与事务一致性

- 请求内容先写 UUID `.part` 文件，同时计算摘要与大小。
- 校验完成后写数据库记录；数据库提交或最终改名失败时清理已创建文件并回滚。
- 入队发生在数据库提交之后；入队失败不删除有效草稿，由 sweep 恢复。
- worker 产物使用临时名，成功后原子替换。
- 音频索引写入前删除该媒体的旧分块；失败时清理新半成品，全文仍可用于幂等重试。
- 知识索引在新版本目录完整构建，活动指针只在成功后切换。

## 13. 前端变化

- 媒体表单保存所选技艺对象，上传时发送 `craft_id` 与匹配的 `craft_name`。
- 文件选择器使用明确扩展名/MIME，不再使用宽泛的 `image/*`、`audio/*`。
- 页面展示格式、大小和音频时长限制。
- 上传失败展示后端安全错误摘要，同时避免暴露服务器路径和堆栈。
- 保持媒体列表、草稿审核和发布流程不变。

当前没有正式文档上传管理页；阶段 1B 先提供受保护的管理员 API，后续内容治理阶段再接完整审核界面。

## 14. 部署设计

- API 镜像保持轻量，不安装 Whisper/OCR 运行依赖。
- 新增 worker 依赖清单和 Docker `worker` 构建目标。
- Compose 新增独立 worker 服务，并确保 Redis、数据库、运行时上传卷和索引卷正确共享。
- 运行时卷挂载到 `/app/runtime` 等独立目录，不覆盖镜像内置 `/app/data` 语料。
- API lifespan 不再创建音频 worker 任务。
- 本地开发文档提供分别启动 Redis、API 和 worker 的 PowerShell 命令。
- `frontend/nginx.conf` 与生产模板都设置 `client_max_body_size 52m` 及合理上传超时。
- 部署文档补充 Alembic 升级、worker 健康检查、失败任务处理和回滚步骤。

## 15. 可观测性与审计

- 日志记录任务 ID、实体 ID、类型、输入规模、耗时、状态和失败类别。
- 不记录文件正文、绝对存储路径、认证令牌或密钥。
- 上传、重试和删除动作写入现有 `AuditLog`。
- worker 定期更新数据库 `WorkerHeartbeat`，使管理接口能区分正常排队、Redis 故障与消费者离线。
- 失败信息对管理员保留可行动摘要；公开接口只返回必要错误，不返回内部异常堆栈。

## 16. 测试与验收

实施遵循 TDD，先写失败测试，再写最小实现。至少覆盖：

- 恶意路径、Windows 分隔符、盘符、控制字符和超长文件名。
- 伪扩展名、MIME/签名冲突、非法媒体类型和未知技艺。
- 空文件、刚好等于上限、超一字节、分块过程中越界。
- 图片解压炸弹、DOCX ZIP 炸弹、PDF 页数/OCR 页数、音频时长和文本量上限。
- 子进程硬超时与临时文件清理。
- 数据库提交失败、最终改名失败、Redis 中断、重复消息和陈旧任务恢复。
- `craft_id`/`craft_name` 一致、冲突及旧客户端兼容路径。
- 文档始终草稿隔离；公开媒体只展示 `published`。
- 维护索引失败时旧版本继续可用。
- Alembic 对空库与既有库两种路径的升级测试。
- 前端表单发送规范技艺字段、精确 `accept` 和错误展示。

最终验证包括：

- 后端全量测试与新增阶段 1B 安全测试。
- 前端单元测试和生产构建。
- Python 编译检查及可用的静态检查。
- Alembic 升级/降级检查。
- `docker compose config`、Nginx 配置和 worker 启动契约检查。
- 针对路线图每一条上传安全要求的审计矩阵。

所有测试数量、耗时和结论以真实命令输出为准，不预填数字。

## 17. 风险与缓解

- **隔离子进程增加模型冷启动成本**：当前上传为管理员低频操作，优先保证安全；处理进程可保持存活，仅在超时后重建。
- **旧表不在完整 Alembic 历史中**：007 使用结构探测兼容空库和既有库，并用两条迁移测试路径约束。
- **活动图书目录与旧 23 项目录不同**：统一由 `CraftCatalog` 生成，API、前端和 worker 不再各自维护映射。
- **Redis 故障导致通知丢失**：数据库 pending 状态和周期 sweep 保证最终补偿。
- **worker 与 API 共享索引时发生半写**：只写版本化临时目录并原子切换，不原地覆盖活动索引。
- **Windows 与 Linux 进程语义不同**：处理器使用 spawn 兼容设计，测试覆盖 Windows 本地入口；Docker 继续在 Linux 下运行。

## 18. 实施顺序约束

1. 先补测试夹具、配置和纯校验组件。
2. 再实现目录解析、有限流式落盘和事务清理。
3. 引入数据模型与迁移后接媒体、文档和相似图片 API。
4. 抽离统一队列和独立 worker，再迁移音频处理。
5. 实现文档解析限制和隔离超时。
6. 实现版本化索引维护。
7. 更新前端、Docker、Nginx 和文档。
8. 执行全量回归与路线图审计。

任何步骤不得通过放宽测试、篡改样本或伪造指标获得通过。
