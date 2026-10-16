# 阶段 0 历史债务审计记录

检查日期：2026-10-15

## 路由与前端入口

- `/query/simple`：仓库内唯一消费者是未被任何组件导入的 `sendQuerySimple()`；两者一并删除。现行问答入口为 `/query` 与 `/query/stream`。
- `/upload`：仓库内没有消费者；现行知识文档入口为 `/documents/upload`，旧接口及其专用响应模型删除。
- 旧前端：根目录不存在旧前端入口文件，但根 Dockerfile、Compose、配置和 README 仍保留运行描述；这些失效配置删除，Vue 成为唯一推荐前端。

复核命令：

```powershell
rg -n 'query/simple|/upload\b|sendQuerySimple' api.py frontend/src tests README.md docs
rg -n '旧前端名称|旧前端端口' Dockerfile docker-compose.yml config.py README.md deploy/README.md
```

第二条命令使用抽象占位词，避免已移除技术名继续触发当前文档的文本契约；需要核对历史记录时使用 Git 历史。

## Dispatcher 与专家辅助方法

- `DispatcherAgent.fuse_with_debate`：仓库内只有定义，没有调用者。实际工作流在 `src/workflow/nodes.py` 中先调用 `should_trigger_debate()`，再走协作或普通融合路径，因此删除该未接线实现。
- `DispatcherAgent._get_agent_type`：只被上述未接线方法使用，随之删除。
- `DispatcherAgent.should_trigger_debate`：由 `src/workflow/nodes.py` 主链路调用，保留。
- 其他专家方法存在注册表、工作流节点或测试调用，或可能经注册表动态分发；没有足够证据证明无用，本阶段不删除。

复核命令：

```powershell
rg -n 'def (_get_agent_type|fuse_with_debate|should_trigger_debate)|\.(fuse_with_debate|should_trigger_debate)\(' src tests
rg -n '^    (async )?def ' src/agents
```

## 活动语料残留

检查 `data/local_books_corpus` 全部文件名，并筛选 `.tmp`、`.temp`、`.partial`、`.part`、`.bak`、尾随 `~` 和 `tmp*`。本次未发现匹配文件，因此没有删除任何本地图书语料。合法正文与构建产物保持原样。

复核命令：

```powershell
Get-ChildItem data/local_books_corpus -Force -Recurse -File |
  Where-Object { $_.Name -match '(\.tmp$|\.temp$|\.partial$|\.part$|\.bak$|~$|^tmp)' }
```

## 保留到后续阶段

- 鉴权、上传校验、CORS、限流、默认密钥和健康检查属于阶段 1。
- `api.py` 路由拆分、重复模型统一和更广泛死代码清理属于阶段 4。
- 历史设计文档保留当时口径，不批量改写；当前 README、OpenAPI 与部署说明使用现行口径。
