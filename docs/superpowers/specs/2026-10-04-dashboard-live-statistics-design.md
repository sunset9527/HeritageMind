# 首页实时统计

## 目标

首页统计只反映后台管理使用的 MySQL 内容，不再从硬编码技艺清单或本地文件汇总数字。

## 接口

新增公开接口 `GET /dashboard/summary`，返回：

- `published_crafts`：`craft_entries.status = "published"` 的数量。
- `published_documents`：`knowledge_documents.status = "published"` 且 `is_current = true` 的数量。
- `traceable_crafts`：已发布且至少存在一条 `source_evidence` 的技艺数量。

## 前端

首页创建一个共享的统计数据源，Hero 区与底部统计条只请求一次该接口。第三项展示为
`{traceable_crafts} / {published_crafts} 可追溯`。加载前或请求失败时显示 `—`；不保留伪造的默认数字。

## 验收

后端测试覆盖草稿条目、历史资料版本和无来源条目不计入对应统计；前端测试验证首页渲染接口返回值及失败占位符。
