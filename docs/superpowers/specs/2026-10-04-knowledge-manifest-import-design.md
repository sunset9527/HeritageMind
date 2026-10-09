# 来源化资料导入命令

## 根因

`data/knowledge_sources/manifest.json` 有 591 条 `published` 资料，已有导入服务却没有可执行入口，因此 MySQL 的 `knowledge_documents` 为空，首页实时统计显示 0。

## 设计

新增显式命令 `python tools/import_knowledge_manifest.py`。命令初始化表、校验清单、在单一数据库事务中调用既有版本化导入服务；成功后提交并输出创建、更新和跳过数，异常时回滚并返回失败。

## 边界

不在 FastAPI 启动时自动导入；不修改清单、不伪造统计。重复导入未变内容只会跳过，内容变化时由既有逻辑创建新版本。

## 验收

测试覆盖命令在成功时提交、失败时回滚并关闭会话；既有导入测试继续覆盖幂等和版本控制。
