# 阶段 1A 权限与资源归属审计记录

检查日期：2026-10-18

对应设计：`docs/superpowers/specs/2026-10-17-stage-1a-authorization-design.md`

功能提交：`33880f9`

## 已实施边界

- Prompt 增删改查、媒体上传/删除/状态修改、转写状态/重试、三类索引重建和知识文档上传均绑定后端 `require_admin`。
- 新增管理员媒体列表 `/admin/media`；公开 `/media/list`、`/media/{id}` 和文件直链只读取 `published`。
- 媒体 Service 提供显式 `list/get_published_*` 公开投影，避免公开路由依赖调用者手动传审核状态。
- 图片文字搜索、相似图片搜索和音频搜索均以数据库当前 `published` 状态为最终过滤条件。
- 收藏携带 `chat_id` 时验证聊天属于当前用户；不存在或越权统一返回 404。
- 前端根据认证 Store 的角色选择公开/管理员媒体列表；非管理员不渲染上传、删除和审核状态操作。
- 修复媒体筛选把媒体类型同时误传为 `craft_name` 的问题，并补充独立技艺筛选。

## TDD 记录

主要 RED 结果均在修改生产代码前复现：

- 敏感路由契约：15 failed / 1 passed；缺少管理员依赖和 `/admin/media`。
- 公共媒体列表与详情：2 failed / 2 passed；草稿仍出现在列表和详情。
- 文件直链与多模态搜索：3 failed / 4 passed；草稿可经文件、图片或音频搜索暴露。
- 收藏归属：2 failed / 2 passed；跨用户和不存在的 `chat_id` 可被收藏。
- 前端首轮：3 failed；缺少管理员列表、角色控件和正确筛选参数。
- 前端审核补充：2 failed / 2 passed；缺少技艺筛选绑定和状态修改操作。
- 管理媒体 URL：1 failed；草稿记录仍返回公开 URL。

最终阶段 1A 定向测试：

```text
29 passed, 7 warnings in 10.32s
```

## 全量验证

后端：

```powershell
python -m pytest -q -p no:cacheprovider --basetemp E:\codex\2026-10-15\a\work\pytest-stage1a-full-final
```

```text
367 passed, 1 skipped, 7 warnings in 39.34s
```

警告来自既有 Pydantic v2 旧式 Config、`pkg_resources` 和 LangGraph 待弃用提示，本阶段没有新增失败。

前端：

```powershell
npm test
npm run build
```

```text
Test Files  20 passed (20)
Tests       36 passed (36)
vite build passed
```

构建仍有既有的单个超 500 kB chunk 提示，不影响产物生成。

其他检查：

- `docker compose config --quiet`：通过。
- `git diff --check`：通过。
- `python -m py_compile`（本阶段修改的 Python 文件与测试）：通过。
- Ruff：当前 Python 环境未安装该模块，命令返回 `No module named ruff`；未伪报为通过，也未为静态检查临时联网安装依赖。

## 尚未完成

本记录只证明阶段 1A 完成，不代表阶段 1 全部完成：

- 1B：上传 MIME/魔数/扩展名、大小、页数、时长、流式写入和路径资源边界；
- 1C：CORS、密码策略、生产密钥、API Key 存储、限流和统一异常响应；
- 1D：liveness/readiness、依赖超时、重试、熔断和降级状态。
