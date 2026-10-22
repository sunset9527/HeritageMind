# HeritageMind 阶段 1B 上传与资源边界验收记录

验收日期：2026-10-22

对应设计：`docs/plans/2026-10-20-stage-1b-upload-resource-boundaries-design.md`

对应计划：`docs/plans/2026-10-21-stage-1b-upload-resource-boundaries-plan.md`

## 结论

阶段 1B 的上传入口、独立 Worker、有界解析、版本化索引和部署契约已经实现，并通过后端、前端、迁移和 Compose 验证。本文只记录实际执行结果，不把未运行的线上或模型集成验证写成通过。

## 安全要求映射

| 要求 | 主要实现 | 自动化证据 | 结果 |
|---|---|---|---|
| 技艺、类型、文件名白名单与路径 containment | `src/services/craft_catalog.py`、`src/services/upload_security.py` | `test_stage1b_craft_catalog.py`、`test_stage1b_upload_security.py` | 通过；覆盖未知/冲突技艺、Windows/Unix 路径、控制字符和越界路径 |
| UUID 存储，原名只入数据库 | `src/services/media.py`、`src/services/document_upload.py` | `test_stage1b_media_upload.py`、`test_stage1b_document_upload.py` | 通过；临时文件和最终文件均不采用用户文件名 |
| 扩展名、MIME、魔数一致性 | `src/services/upload_security.py` | `test_stage1b_upload_security.py`、`test_stage1b_similar_image_upload.py` | 通过；图片、音频、PDF、DOCX、Markdown、TXT 均有类型校验 |
| FastAPI/Nginx 双层与分类型大小限制 | `src/middleware/request_size.py`、`config.py`、两份 Nginx 配置 | `test_stage1b_request_size_limit.py`、`test_stage1b_upload_settings.py`、`test_stage1b_deployment_contract.py` | 通过；请求总上限 52 MiB，业务类型另有限制 |
| 上传入口无无界读取 | `stage_upload()` 分块读取；相似图片先有限落盘再读取 | 静态 `rg` 扫描与上传测试 | 通过；未发现无参数 `UploadFile.read()` |
| PDF/OCR、转写和索引资源边界 | `document_parser.py`、`transcription.py`、`isolated_runner.py`、`index_builders.py` | 文档处理、音频限制、隔离进程、索引构建测试 | 通过；页数、OCR 页数、字符数、音频时长、输入规模和硬超时均有边界 |
| 默认草稿与 published 可见性 | 媒体/文档状态模型及公开查询过滤 | `test_stage1a_media_visibility.py`、上传与管理员测试 | 通过；上传默认草稿，文档解析产物不直接进入公开语料 |
| 部分失败可回滚或重试 | 文件/数据库事务、Redis 通知补偿、CAS 抢占、sweep、版本清单切换 | 媒体/文档事务、队列、Worker 生命周期、索引版本测试 | 通过；失败不切换活动索引，pending/陈旧任务可恢复 |

## 维护索引闭环

- 知识索引写入文档和 BGE/API embeddings；`MultiSourceRetriever` 在查询边界检测活动版本并热加载。
- 图片索引同时保存文本向量和 CLIP 视觉向量；文搜图和以图搜图优先读取活动快照。
- 音频索引把已完成转写重放到新 Chroma collection，成功后才切换活动清单；查询进程按版本重建 store。
- 三类构建均在 spawn 子进程内执行，受 `INDEX_TASK_TIMEOUT_SECONDS` 硬超时约束；异常或终止不覆盖旧活动版本。
- Worker 启动时恢复 pending 与陈旧 processing 文档/维护任务；管理员文档列表返回 `online`、`stale` 或 `offline` 心跳状态。

## 实际验证结果

```text
python -m pytest tests -q
480 passed, 1 skipped, 7 warnings in 37.80s

npm run test -- --run
21 test files passed, 40 tests passed

npm run build
成功（1778 modules transformed）

python -m compileall -q api.py config.py src migrations
通过

Alembic SQLite smoke
upgrade head -> downgrade 006 -> upgrade head 通过

docker compose -f docker-compose.yml config --quiet
通过

docker compose -f docker-compose.production.yml config --quiet
通过（未设置生产密码时 Compose 按预期输出变量警告）

git diff --check
通过
```

后端唯一跳过项来自环境条件测试（真实 Redis 或本地图书语料依赖）；阶段 1B 的纯单元/契约测试未通过放宽预期来规避失败。

## 已知限制与未冒充验证的项目

- 当前环境没有安装 Ruff（`python -m ruff` 返回 `No module named ruff`），因此未把 Ruff 写成通过；Python 编译与 `git diff --check` 已通过。
- 前端生产构建有既存的大 chunk 警告（主包约 1.10 MB），不影响本阶段构建成功，但应在后续性能阶段拆包。
- Pydantic 旧式 Config、jieba `pkg_resources` 和 LangGraph serializer 存在弃用警告；本阶段没有扩大处理范围。
- 没有启动真实 MySQL/Redis/Docker 容器，也没有下载并运行 BGE、CLIP、Whisper/OCR 模型；已验证 Compose 配置、依赖声明、模型挂载和无模型时的失败状态，线上部署仍需按 `deploy/README.md` 做集成验收。
- CORS、限流、生产密钥轮换和外部依赖降级属于阶段 1C/1D，不在本记录中标为完成。
