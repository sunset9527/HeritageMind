# HeritageMind 阶段 1B：上传、文件与资源边界实施计划

> 对应设计：`2026-10-20-stage-1b-upload-resource-boundaries-design.md`
>
> 执行原则：严格 TDD；每个任务先运行新增测试观察预期失败，再写最小实现使其通过，最后重构并复跑受影响测试。不得通过修改安全预期、放宽夹具或伪造结果换取通过。

## 0. 开工前基线与分支纪律

1. 确认 `git status --short` 为空，并记录起始提交。
2. 运行当前后端全量测试、前端测试与构建，保存真实基线；如出现既有失败，先判断是否与阶段 1B 无关，不把它混入功能修改。
3. 检查本机可用的 Ruff、Docker Compose、Node 和 Alembic；缺失工具如实记录，不伪造验证结果。
4. 阶段 1B 期间保留阶段 1A 的管理员权限和 published 可见性测试，任何上传改造不得回退授权边界。

基线命令：

```powershell
python -m pytest tests -q
Set-Location frontend
npm run test
npm run build
Set-Location ..
python -m compileall -q api.py config.py src
docker compose config
docker compose -f docker-compose.production.yml config
```

## 1. 配置资源预算与统一技艺目录

**新增测试**

- `tests/test_stage1b_upload_settings.py`
- `tests/test_stage1b_craft_catalog.py`

**修改/新增实现**

- 修改 `config.py`
- 新建 `src/services/craft_catalog.py`
- 修改 `api.py`

**RED**

1. 为图片、相似图片、音频、PDF、DOCX、文本、PDF 页数、OCR 页数、提取字符数、任务超时、最大尝试、索引文档数和索引总字符数写默认值及 Pydantic 边界测试。
2. 写目录测试：活动图书投影优先；没有投影时返回旧 23 项；ID 和名称可以双向唯一解析；未知 ID、未知名称、ID/名称冲突失败。
3. 写 `/crafts` 契约测试，断言公开列表与上传解析器使用同一目录源。

**GREEN**

1. 在 `Settings` 增加设计中的资源参数与存储根目录配置。
2. 把旧 23 项常量从 `api.py` 移到 `craft_catalog.py`，提供不可变目录项和 `resolve(craft_id, craft_name)`。
3. `/crafts` 改用共享目录服务；删除 `_get_craft_list()` 的重复事实源。

**验证**

```powershell
python -m pytest tests/test_stage1b_upload_settings.py tests/test_stage1b_craft_catalog.py -q
```

## 2. 建立上传安全纯组件与请求体总上限

**新增测试**

- `tests/test_stage1b_upload_security.py`
- `tests/test_stage1b_request_size_limit.py`
- `tests/fixtures/uploads/` 下最小合法/非法二进制夹具

**修改/新增实现**

- 新建 `src/services/upload_security.py`
- 新建 `src/middleware/__init__.py`
- 新建 `src/middleware/request_size.py`
- 修改 `api.py`
- 修改 `requirements.txt`、`requirements.production.txt`

**RED**

1. 文件名：拒绝 `../`、`..\\`、绝对路径、盘符、任一路径分隔符、控制字符、空名和超长名。
2. 类型：覆盖 JPEG、PNG、WebP、MP3、WAV、M4A、FLAC、OGG、PDF、DOCX、Markdown、TXT 的合法签名；覆盖扩展名/MIME/签名任意冲突。
3. 流读取：覆盖空文件、恰好等于上限、超一字节、多个 chunk 后才越界、异常中止后 `.part` 清理和 SHA-256 正确性。
4. 图片：覆盖无法解码、宽高异常和总像素超限。
5. DOCX：覆盖必要成员缺失、成员数超限、声明解压总量超限和异常压缩比。
6. ASGI 中间件：覆盖有/无 `Content-Length`、chunked receive 越界、普通 JSON 请求不受误伤，并断言越界返回统一 `413`。

**GREEN**

1. 建立 `UploadPolicy`、结构化 `UploadValidationError`、安全文件名校验、纯 Python 文件签名识别和 MIME 兼容表。
2. 提供异步有限读取到 UUID `.part` 的函数，以及相似图片使用的有限内存读取函数；禁止无参数 `read()`。
3. 使用 Pillow 做图片完整性、尺寸和像素检查；DOCX 只读取 ZIP 中央目录做预检，不在 API 解压正文。
4. 增加最外层 ASGI 请求体计数中间件，在 multipart 解析前执行 52 MiB 总上限。

**验证**

```powershell
python -m pytest tests/test_stage1b_upload_security.py tests/test_stage1b_request_size_limit.py -q
```

## 3. 增加持久化模型与兼容迁移

**新增测试**

- `tests/test_stage1b_upload_models.py`
- `tests/test_stage1b_upload_migration.py`

**修改/新增实现**

- 修改 `src/models/media.py`
- 新建 `src/models/upload.py`
- 修改 `src/models/__init__.py`
- 修改 `src/database.py`
- 新建 `migrations/versions/007_stage1b_upload_boundaries.py`

**RED**

1. 断言 `MediaDocument` 包含可审计的 `craft_id`、`content_sha256`、`uploaded_by_user_id`。
2. 断言 `DocumentUpload` 把审核状态和处理状态分开，并包含文件、解析统计、尝试次数、错误和时间字段。
3. 断言 `MaintenanceJob` 可以区分知识、图片、音频三类索引任务。
4. 断言 `WorkerHeartbeat` 可按 worker ID 更新且不会产生无限重复行。
5. 构造两条迁移路径：只到 006 的空库，以及已由 `Base.metadata.create_all()` 产生媒体/音频表的旧库；两者升级 007 后结构一致、旧媒体数据保留。
6. 验证降级不误删 007 之前已存在的旧媒体数据，并清理本阶段新增结构。

**GREEN**

1. 添加 SQLAlchemy 模型、枚举/字符串状态约束和必要索引。
2. 编写结构探测型 bridge migration，只补缺失表/列/索引；对可唯一映射的旧名称回填 ID，不能可靠映射的保持空。
3. 确保模型注册与 Alembic `target_metadata` 完整。

**验证**

```powershell
python -m pytest tests/test_stage1b_upload_models.py tests/test_stage1b_upload_migration.py -q
$env:DATABASE_URL = "sqlite:///./.stage1b-migration-check.db"
python -m alembic upgrade head
python -m alembic downgrade 006
python -m alembic upgrade head
Remove-Item -LiteralPath .stage1b-migration-check.db
Remove-Item Env:DATABASE_URL
```

## 4. 重写媒体上传的事务与草稿语义

**新增/修改测试**

- 新建 `tests/test_stage1b_media_upload.py`
- 扩展 `tests/test_audio_transcript_model.py`
- 扩展 `tests/test_stage1a_media_visibility.py`
- 扩展 `tests/test_stage1a_route_authorization.py`

**修改/新增实现**

- 修改 `src/services/media.py`
- 修改 `src/services/audio_transcript.py`
- 修改 `src/schemas/media.py`
- 修改 `api.py`

**RED**

1. 合法图片只以 UUID 名进入图片目录，原文件名只在数据库出现，且初始状态固定为 `draft`。
2. `craft_id` 优先、仅名称兼容、双字段冲突拒绝。
3. 数据库提交失败时最终文件被删除；最终改名失败时数据库回滚；验证失败只留下零个临时文件。
4. 音频的媒体行、转写 sidecar 和审计记录在同一数据库事务建立，Redis 通知只在提交成功后发送。
5. Redis 失败时接口仍返回已保存草稿，转写状态保持可 sweep 的 `UPLOADED`。
6. 旧测试创建的 legacy 媒体仍可读取；公开接口依旧只看 `published`。

**GREEN**

1. 将 `upload_media` 改为接受已验证的暂存结果，不再调用无界 `file.read()`。
2. 调整音频 sidecar 创建函数，移除内部隐式 commit，使调用方控制事务。
3. 统一审计写入，不记录正文、绝对路径或令牌。
4. API 返回规范技艺字段、摘要和处理状态。

**验证**

```powershell
python -m pytest tests/test_stage1b_media_upload.py tests/test_audio_transcript_model.py tests/test_stage1a_media_visibility.py tests/test_stage1a_route_authorization.py -q
```

## 5. 收紧公开以图搜图入口

**新增测试**

- `tests/test_stage1b_similar_image_upload.py`

**修改实现**

- 修改 `api.py`
- 按需修改 `src/retrieval/multimodal_search.py`

**RED**

1. 非图片、伪图片、超 10 MiB、空文件和异常图片返回对应 `413/415`。
2. `top_k=0`、负数或大于 20 被 Pydantic/FastAPI 拒绝。
3. 请求处理后不留下暂存文件。
4. 检索结果继续只包含 published 图片。

**GREEN**

1. 使用有限内存读取和共享图片验证器替代 `await file.read()`。
2. 用 `Query(ge=1, le=20)` 固化结果数量边界。

**验证**

```powershell
python -m pytest tests/test_stage1b_similar_image_upload.py tests/test_stage1a_media_visibility.py -q
```

## 6. 建立文档草稿上传和管理员生命周期 API

**新增测试**

- `tests/test_stage1b_document_upload.py`
- `tests/test_stage1b_document_admin.py`

**修改/新增实现**

- 新建 `src/services/document_upload.py`
- 新建 `src/schemas/upload.py`
- 修改 `src/services/queue.py`
- 修改 `api.py`

**RED**

1. `/documents/upload` 合法请求返回 `202`、UUID 存储名、`draft/pending`，并断言 `crafts_doc_path` 未产生文件。
2. 验证文档扩展名/MIME/签名、类型大小和技艺映射错误。
3. 数据库失败、原子改名失败和审计失败时无孤儿文件或半提交记录。
4. 管理列表/详情只能由管理员访问，且不暴露绝对存储路径。
5. 只有 `failed` 且未耗尽尝试的记录可重试；`processing` 删除返回 `409`；删除其他草稿同时清理原件和解析产物。

**GREEN**

1. 实现文档暂存、事务、审计，并先加入最小通用 `push_job` 通知；任务 7 再补齐统一消费、sweep 和兼容包装器。
2. 实现管理员列表、详情、重试和删除接口。
3. 移除旧的同步 `parse_document` 和 `craft_name + "_upload.txt"` 路径。

**验证**

```powershell
python -m pytest tests/test_stage1b_document_upload.py tests/test_stage1b_document_admin.py tests/test_stage1a_route_authorization.py -q
```

## 7. 泛化 Redis 队列并抽离独立 worker

**新增/修改测试**

- 新建 `tests/test_stage1b_task_queue.py`
- 新建 `tests/test_stage1b_worker_lifecycle.py`
- 扩展 `tests/redis_stub.py`
- 重构 `tests/test_redis_backend_and_queue.py`
- 重构 `tests/test_audio_worker.py`

**修改/新增实现**

- 修改 `src/services/queue.py`
- 新建 `src/services/task_state.py`
- 新建 `src/workers/__init__.py`
- 新建 `src/workers/upload_worker.py`
- 修改 `api.py`

**RED**

1. 验证统一任务信封的版本、kind 和 entity ID；非法/未知消息安全丢弃并记录原因。
2. 重复消息只能有一个 worker 原子抢占成功。
3. Redis 通知丢失后，启动/周期 sweep 能恢复 pending 和陈旧 processing；未陈旧任务不被抢走。
4. 尝试次数耗尽进入终态 failed，不形成无限重试风暴。
5. worker 定期更新数据库心跳，`GET /admin/documents` 的管理响应可以区分在线、离线和心跳过期。
6. 导入 `api.py` 或运行 lifespan 不再启动任何上传/转写消费者。

**GREEN**

1. 将 `push_audio_job/pop_audio_job` 迁移到兼容的 `push_job/pop_job`，旧包装器暂时保留以减少回归。
2. 实现统一抢占、失败、成功、sweep 和心跳服务。
3. 提供 `python -m src.workers.upload_worker` 独立入口。
4. 删除 API lifespan 中的 `_worker_task` 和 `run_worker` 接线，仅保留 API 所需 Redis 缓存资源关闭。

**验证**

```powershell
python -m pytest tests/test_stage1b_task_queue.py tests/test_stage1b_worker_lifecycle.py tests/test_redis_backend_and_queue.py tests/test_audio_worker.py -q
```

## 8. 实现有界文档解析与真正的硬超时

**新增/修改测试**

- 新建 `tests/test_stage1b_document_processing.py`
- 新建 `tests/test_stage1b_isolated_runner.py`
- 扩展 `tests/test_pdf_parser.py`
- 新增最小 DOCX、Markdown、TXT 夹具

**修改/新增实现**

- 修改 `src/services/document_parser.py`
- 修改 `src/services/pdf_parser.py`
- 新建 `src/workers/processors.py`
- 新建 `src/workers/isolated_runner.py`
- 修改 `requirements.txt`
- 新建 `requirements.worker.txt`

**RED**

1. PDF 超 100 页、OCR 页超 25、单页渲染像素异常、累计文本超限和截止时间到达时返回结构化失败。
2. DOCX ZIP 通过入口预检后，解析仍按累计文本和截止时间受限；Markdown/TXT 必须是有效 UTF-8 且不含 NUL。
3. 缺少解析依赖时任务失败，正文绝不能是“某依赖未安装”。
4. 子进程正常返回、抛错、卡死、超时终止和后续任务恢复均有测试；超时进程不能继续修改产物。
5. worker 只在完整成功后原子发布解析文本；失败清理 `.part` 并保留原始草稿供重试。

**GREEN**

1. 把解析 API 改为基于路径/流的受限解析，返回正文和页数/OCR 页数等元数据。
2. PDF 逐页检查截止时间和资源累计量；DOCX 不无界解压。
3. 实现基于 `multiprocessing` spawn 的隔离处理器；调度器超时后 terminate/join 并重建处理进程。
4. worker 父进程拥有最终数据库状态迁移和原子产物发布权。

**验证**

```powershell
python -m pytest tests/test_stage1b_document_processing.py tests/test_stage1b_isolated_runner.py tests/test_pdf_parser.py -q
```

## 9. 迁移音频转写并补齐时长、超时和索引恢复

**新增/修改测试**

- 新建 `tests/test_stage1b_audio_limits.py`
- 扩展 `tests/test_transcription_service.py`
- 扩展 `tests/test_audio_worker.py`
- 扩展 `tests/test_audio_store_chroma.py`

**修改实现**

- 修改 `src/services/transcription.py`
- 修改 `src/services/audio_transcript.py`
- 修改 `src/services/audio_worker.py` 或将其收敛为新 worker 的处理适配器
- 修改 `src/retrieval/audio_store.py`
- 修改 `api.py`

**RED**

1. PyAV 无法解码、真实时长超过 30 分钟和未知时长均失败且不加载 Whisper。
2. Whisper 超时由隔离处理器终止；重试次数和失败原因正确。
3. 转写完成、向量索引失败时先保存 `full_text`；再次处理跳过 Whisper，只重试索引。
4. 索引重试先按 `media_id` 清理旧分块；失败不把转写状态误标为完成。
5. 手动转写接口继续保持管理员、409 和最大尝试语义。

**GREEN**

1. 增加 PyAV 元数据预检和转写文本上限。
2. 将 Whisper 调用接到隔离处理器，父 worker 控制状态。
3. 把“转写完成”和“索引完成”持久化步骤拆开，保持幂等恢复。

**验证**

```powershell
python -m pytest tests/test_stage1b_audio_limits.py tests/test_transcription_service.py tests/test_audio_worker.py tests/test_audio_store_chroma.py -q
```

## 10. 将三类索引重建改为版本化维护任务

**新增测试**

- `tests/test_stage1b_maintenance_jobs.py`
- `tests/test_stage1b_index_versioning.py`

**修改/新增实现**

- 新建 `src/services/maintenance_jobs.py`
- 新建 `src/retrieval/index_snapshot.py`
- 修改 `src/retrieval/retriever.py`
- 修改 `src/retrieval/audio_store.py`
- 修改 `src/retrieval/multimodal_search.py`
- 修改 `api.py`

**RED**

1. `/knowledge/rebuild-embeddings`、`/search/index-images`、`/search/audio/index` 都只创建任务并返回 `202`，不在请求线程调用模型或遍历全库。
2. 同类任务已有 pending/processing 时返回 `409`，防止并发重建。
3. 知识索引超过 1,000 篇、500 万字符或 10 分钟时失败。
4. 新索引在临时版本中构建；失败、超时或进程终止后活动版本不变。
5. 成功时用 `os.replace()` 切换小型活动版本清单；API 在请求边界发现版本变化并换载。
6. 音频索引先构建新 collection，成功才切换；失败继续查询旧 collection。

**GREEN**

1. 实现维护任务去重、入队、状态查询和 worker processor。
2. 建立版本目录、清单校验、原子活动指针和旧版本保留/清理策略。
3. 为 retriever/audio store 增加按活动版本懒换载，避免 worker 修改 API 进程内对象。

**验证**

```powershell
python -m pytest tests/test_stage1b_maintenance_jobs.py tests/test_stage1b_index_versioning.py tests/test_retrieval.py tests/test_audio_store_chroma.py -q
```

## 11. 对齐前端媒体上传契约与错误体验

**新增/修改测试**

- 扩展 `frontend/src/views/MediaView.spec.ts`
- 新建 `frontend/src/api/media.spec.ts`

**修改实现**

- 修改 `frontend/src/api/media.ts`
- 修改 `frontend/src/views/MediaView.vue`
- 按需修改 `frontend/src/types/index.ts`

**RED**

1. 选项保留完整 `{id,name}`，表单同时发送匹配的 `craft_id` 和 `craft_name`。
2. 图片、音频的 `accept` 为设计允许的精确扩展名/MIME。
3. 页面显示 10 MiB 图片、50 MiB/30 分钟音频限制。
4. Axios 的 `detail` 能转为用户可读错误，不再统一显示“上传失败”。
5. 管理员可上传，普通用户仍看不到上传/删除/审核控件。

**GREEN**

1. 更新 API 类型、FormData 和媒体响应字段。
2. 调整选择器模型、文件输入和错误提示，不扩建文档审核 UI。

**验证**

```powershell
Set-Location frontend
npm run test -- src/api/media.spec.ts src/views/MediaView.spec.ts
npm run build
Set-Location ..
```

## 12. 完成 worker 镜像、共享卷与 Nginx 双层限制

**新增测试/静态契约**

- 新建 `tests/test_stage1b_deployment_contract.py`

**修改实现**

- 修改 `Dockerfile`
- 修改 `docker-compose.yml`
- 修改 `docker-compose.production.yml`
- 修改 `frontend/nginx.conf`
- 修改 `deploy/nginx/heritagemind.conf.template`
- 修改 `deploy/README.md`
- 修改根 `README.md`
- 修改 `.env.example`

**RED**

1. 静态断言 API 服务关闭内嵌 worker，Compose 存在独立 worker、Redis、共享运行时卷和独立索引卷。
2. 断言运行时卷不覆盖 `/app/data` 内置语料。
3. 两份 Nginx 配置都有 `client_max_body_size 52m` 和上传超时。
4. 部署文档包含 Alembic、PowerShell 本地 worker 启动、健康检查、失败任务处理和回滚步骤。

**GREEN**

1. 新增 worker dependencies/build target；API 镜像继续不安装 Whisper/OCR 重依赖。
2. 开发和生产 Compose 均接入 worker、Redis 和共享路径。
3. 补齐环境变量示例与部署操作说明。

**验证**

```powershell
python -m pytest tests/test_stage1b_deployment_contract.py -q
docker compose config
docker compose -f docker-compose.production.yml config
```

## 13. 全量回归、安全审计与验证记录

**新增文档**

- `docs/stage-1b-upload-resource-boundaries-audit.md`

**审计矩阵**

逐条映射路线图的八项要求到：实现文件、测试名称、运行结果和已知限制：

1. 技艺/类型/文件名白名单与路径 containment。
2. UUID 存储，原名只入数据库。
3. 扩展名、MIME、魔数一致性。
4. FastAPI 与 Nginx 双层、分类型大小限制。
5. 无界读取清零。
6. PDF/OCR、转写、三类索引的数量/文本/时长/超时/队列边界。
7. 默认草稿与 published 可见性。
8. 文件、数据库、队列、索引部分失败的回滚或可重试状态。

**最终命令**

```powershell
python -m pytest tests -q
Set-Location frontend
npm run test
npm run build
Set-Location ..
python -m compileall -q api.py config.py src
python -m ruff check src api.py config.py tests
git diff --check
docker compose config
docker compose -f docker-compose.production.yml config
rg -n "await file\.read\(\)|file\.read\(\)|craft_name \+.*upload|create_task\(run_worker" api.py src
```

对 `rg` 命中逐条人工分类：测试夹具或已有受限读取可保留，上传入口和解析链路不得存在无界读取。Ruff 或 Docker 若本机不可用，记录为“未安装/不可用”，不能写成通过。

## 提交顺序

1. `test/feat: add upload validation and persistence boundaries`
2. `feat: move document and audio processing to durable worker`
3. `feat: queue versioned index maintenance jobs`
4. `feat: align media upload frontend and deployment`
5. `docs: record stage 1b upload security verification`

每个功能提交前必须让对应定向测试转绿；最终提交只记录真实验证结果。全部完成后工作区应干净，阶段 1C/1D 的 CORS、限流、密钥、健康检查和依赖降级不得误标为已完成。
