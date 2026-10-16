# HeritageMind 阶段 0 工程测试记录

测试日期：2026-10-16

功能基线：`6e6b156`（`refactor: complete stage 0 baseline cleanup`）

环境：Windows 11、PowerShell 5.1、Python 3.13.7、Node/Vite 使用仓库现有锁文件与 `node_modules`

## 测试范围

本记录验证阶段 0 的版本与文档口径、旧接口删除、Vue 唯一前端、死代码清理和既有工程回归。它不包含正式检索评测、回答质量评测、多 Agent 消融、性能压测或生产部署验收。

## 后端

命令：

```powershell
python -m pytest tests -q -p no:cacheprovider --basetemp '<可写临时目录>'
```

结果：`338 passed, 1 skipped, 7 warnings in 40.13s`。

其中阶段 0 新增契约测试 7 条，先在旧实现上得到 7 个预期失败，再完成最小实现并转绿。契约覆盖：

- FastAPI 元数据版本与根接口版本一致；
- OpenAPI 删除历史固定规模并指向动态统计端点；
- `/query/simple` 与旧 `/upload` 不再暴露；
- 前端不再保留旧简单问答封装；
- 当前 Docker、Compose、配置和 README 不再提供旧前端运行链路；
- 默认 Compose 前端为 Vue；
- README 区分交付状态和统计口径。

7 条警告不是本轮新增失败：4 条 Pydantic 类式 `Config` 弃用警告、1 条 jieba 对 `pkg_resources` 的依赖警告、1 条 LangGraph 序列化默认值待变更警告；同类 Pydantic 警告在多个 schema 位置汇总展示。Pydantic 迁移属于路线图阶段 4。

## 前端

命令：

```powershell
Push-Location frontend
npm run test
npm run build
Pop-Location
```

Vitest 结果：`19 passed` 测试文件、`32 passed` 测试，耗时 20.12 秒。

生产构建结果：TypeScript 检查和 Vite 构建通过，1,778 个模块完成转换。入口 JS 为 1,096.62 kB，gzip 后 364.79 kB；Vite 报告大于 500 kB 的分包警告。该警告保留到路线图阶段 5 处理，没有把“构建通过”写成“性能验收通过”。

## Compose、静态检查与敏感信息

- `docker-compose config --quiet`：配置解析通过。当前 Docker 客户端因沙箱不能读取 `C:\Users\lenovo\.docker\config.json` 输出权限警告，但命令退出码为 0。
- `ruff check src/app_metadata.py tests/test_stage0_baseline_contract.py`：通过。
- `python -m py_compile api.py config.py src/app_metadata.py src/agents/dispatcher.py tests/test_stage0_baseline_contract.py`：通过。
- 对常见 API Key、AWS Key 与私钥头执行定向扫描：无命中。
- `git diff --check`：通过。

## 已知限制

- 域名、HTTPS、ECS 当前主分支部署、备份恢复与回滚尚未验收。
- CORS、管理员写接口、上传边界、默认密钥和 readiness 属于阶段 1，本轮只在 README 中如实标记状态。
- `api.py` 分层、Pydantic `ConfigDict` 迁移和更广泛死代码治理属于阶段 4。
- 前端入口包分拆与性能收口属于阶段 5。
