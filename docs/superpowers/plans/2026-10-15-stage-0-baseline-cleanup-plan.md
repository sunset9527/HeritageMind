# HeritageMind 阶段 0：口径与历史债务清理实施计划

> 对应设计：`../specs/2026-10-15-stage-0-baseline-cleanup-design.md`

## 1. 用失败测试固化阶段 0 契约

1. 新建 `tests/test_stage0_baseline_contract.py`。
2. 断言 FastAPI 应用版本与根接口响应复用同一 `APP_VERSION`。
3. 断言 OpenAPI 描述不包含“23 种”“55,000”“65 节点”等旧固定规模，并明确指向三个动态统计端点。
4. 断言 `/query/simple` 与旧 `/upload` 不再出现在 OpenAPI 路由中。
5. 断言根 Dockerfile、Compose、配置与当前 README 不再包含 Streamlit 运行链路，且默认 Compose 的 `frontend` 服务构建 Vue 前端。
6. 先运行该测试并确认失败原因均来自现有旧行为，不接受导入错误或测试拼写错误作为 RED。

## 2. 统一版本与 API 口径

1. 新建 `src/app_metadata.py`，作为 `APP_VERSION` 和当前 API 描述的单一来源。
2. 修改 `api.py`，让 FastAPI 元数据与根接口复用 `APP_VERSION`。
3. 删除 OpenAPI 中的历史固定规模，改为指向 `/dashboard/summary`、`/documents/summary` 与 `/graph/stats`。
4. 删除 `/query/simple`、旧 `/upload` 及其专用响应模型和不再需要的 FastAPI 导入。
5. 删除 `frontend/src/api/query.ts` 中没有调用者的 `sendQuerySimple()`。
6. 运行阶段 0 契约测试，确认版本和路由相关断言转绿。

## 3. 移除失效 Streamlit 链路并统一 Vue 启动方式

1. 删除根 `Dockerfile` 的 Streamlit 阶段，只保留 API 镜像。
2. 修改 `docker-compose.yml`，让默认 `frontend` 服务从 `frontend/Dockerfile` 的 development 阶段构建并代理 API；保留 production profile 的 Nginx 服务。
3. 删除 `config.py` 的 `streamlit_port`。
4. 同步 README 与 `deploy/README.md` 中的前端、版本、部署状态和已知限制，不把未部署能力写成已上线。
5. 使用 `docker compose config` 验证静态配置；本机无 Docker 时明确记录跳过原因。
6. 运行阶段 0 契约测试，确认 Vue 唯一前端相关断言转绿。

## 4. 盘点死代码与活动语料残留

1. 用仓库全文引用和 AST 名称引用盘点 `dispatcher.fuse_with_debate` 及专家辅助方法。
2. 仅删除仓库零调用、测试零依赖且现行工作流已有替代实现的方法；其余写入 `docs/stage-0-cleanup-audit.md` 并说明保留理由。
3. 枚举 `data/local_books_corpus` 下临时后缀、异常名称和未被 `catalog.json`/清单引用的文件。
4. 仅删除能够证明是原子写入或构建残留的文件；合法本地图书语料和 Git 忽略正文不动。
5. 在审计记录中列出检查命令、结论和未处理项，不以“未发现”代替可复核证据。

## 5. 回归与真实口径回写

1. 运行阶段 0 契约测试和受影响的 API/部署相关测试。
2. 运行后端全量离线 `pytest`，记录通过、跳过、失败、耗时与警告。
3. 在 `frontend` 运行 Vitest 和 `npm run build`，记录测试文件数、测试数、构建结果和包体警告。
4. 更新 README 的复测日期、基线提交、测试数量和已知限制；文档不得声称域名、HTTPS 或生产部署已完成。
5. 再运行契约测试、后端全量测试、前端测试与构建，确保 README 回写没有破坏文本契约。
6. 运行 `git diff --check` 和敏感信息定向扫描，确认改动只属于阶段 0 且未引入凭证。

## 交付顺序

按“失败测试 → 版本与 API → Vue 唯一前端 → 审计清理 → 全量回归 → README 回写”的顺序推进。正式检索指标、数据质量评测、消融实验和生产验收全部留到阶段 7。
