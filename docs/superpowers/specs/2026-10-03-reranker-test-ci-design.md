# Reranker 回归隔离与前端 CI 设计

## 目标

在不改变生产检索默认行为的前提下，使后端常规回归测试不加载本地 CrossEncoder 模型，并让 GitHub Actions 同时验证前端单元测试和生产构建。

## 范围与决策

- 生产默认保持 `reranker_enabled=True`。模型不可用或推理失败时继续沿用现有的排序降级行为。
- 全局 pytest fixture 在每个常规测试开始前禁用 reranker，并在结束后恢复原设置及 reranker 单例状态。测试不得因本机是否存在 1.1 GB 模型而改变耗时或结果。
- reranker 接线测试显式启用或禁用开关，并通过替身验证降级和置顶保护；真实模型推理不进入常规离线回归。
- CI 的前端 job 先执行 `npm run test`，再执行 `npm run build`。两步任一失败都应阻断合并。
- 现有 `config.py` 与两份 reranker 测试的未提交变更，同本次 fixture、CI 更新一起以单个语义清晰的提交入库。

## 实现边界

测试隔离只修改进程内的 `settings.reranker_enabled` 和 reranker 全局单例，不修改 `.env`、模型目录或生产配置。其作用域为 pytest，不影响 API 运行时的默认 reranker 行为。

不在本次修改中增加覆盖率门槛、包体积分析工具或前端拆包策略；它们属于后续质量/性能优化，避免与回归收口混杂。

## 验收标准

1. 新增的隔离测试先失败：证明常规测试启动/结束时 reranker 均被隔离且原状态可恢复。
2. 全量 `python -m pytest tests/` 不尝试加载本地 CrossEncoder，且通过。
3. `tests/test_reranker_wiring.py` 保留默认开启、禁用、模型不可用降级和技艺置顶保护的覆盖。
4. `npm run test` 与 `npm run build` 都通过。
5. CI 配置包含上述两条前端命令，且工作区在提交后干净。

## 风险与回退

风险是全局 fixture 意外掩盖 reranker 接线行为。通过让接线测试显式恢复/设置开关并对 `get_reranker_model` 使用受控替身规避。若该隔离破坏了现有接线测试，优先缩小 fixture 作用域或为该测试显式退出隔离，而不把生产默认改回关闭。

若线上模型加载异常，现有异常捕获会退回初检排序；该行为由现有接线测试验证。
