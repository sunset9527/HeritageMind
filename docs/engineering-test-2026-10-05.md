# HeritageMind 工程化测试记录（2026-10-05）

## 测试口径

- 对象：本机当前工作区，Git HEAD `35d530c`，测试前有 72 条未提交的文件变更。以下数字不是该提交的干净检出结果，也不能与历史报告直接比较。
- 环境：Windows 11、Python 3.13.7、pytest 9.0.3、coverage.py 7.16.2、Ruff 0.12.0、Node 24.14.1、npm 11.11.0。CI 配置使用 Python 3.11 和 Node 20，因此本次不能代替 CI 环境验证。
- 范围：离线后端回归、前端组件测试、前端类型检查与生产构建、静态检查、后端行覆盖率、当前语料与旧评测集的契约核对。未运行外部 LLM、在线数据库、向量模型端到端问答或生产环境压测。

## 实测结果

| 检查 | 结果 | 可核对数据 |
| --- | --- | --- |
| 后端 `pytest tests/` | 失败 | 322 个用例：315 通过、6 失败、1 跳过；耗时 66.03 秒；9 条警告。6 个失败都在检索真实数据或证据 ID 检查。 |
| 后端行覆盖率 | 61.58% | `src/`、`api.py`、`config.py` 共 8,098 个可执行语句，覆盖 4,987，未覆盖 3,111。关键模块：`api.py` 33%、`src/workflow/nodes.py` 37%、`src/retrieval/retriever.py` 48%、`src/retrieval/document_loader.py` 30%。这是行覆盖率，不代表功能正确率。 |
| 前端 `npm run test` | 单独运行通过 | 18 个测试文件、28 个用例全部通过，耗时 8.03 秒。首次与后端测试及构建并行运行时为 27 通过、1 个 `App.spec.ts` 超过 5 秒时限；该用例单独复跑通过（1.90 秒）。目前只能判定其存在时间敏感性，不能据此确定根因。 |
| 前端 `npm run build` | 通过，有体积警告 | TypeScript 检查与 Vite 构建成功；Vite 报告 1,778 个模块、构建 13.38 秒。入口 JS 为 1,096.62 kB，gzip 后 364.80 kB，超过 Vite 的 500 kB 分块提示阈值。 |
| `ruff check src/ api.py config.py` | 失败 | 共 72 条：F401 36、F541 11、E702 7、F841 7、E701 4、F811 4、E402 2、E741 1。`api.py` 占 18 条。当前工作区不能通过 CI 中同名静态检查。 |

## 检索失败的定位

当前 `data/local_books_corpus/catalog.json` 的状态是 `active`，记录 10 个来源、7,688 个文档片段和 88 个空页。`HeritageDocumentLoader.load_craft_documents()` 因此优先返回 7,688 个 `book:*` 文档，不再返回旧的 23 篇技艺文档和 591 条来源化资料；这是当前代码明确实现的切换行为。

6 个失败中，`test_craft_retrieval.py` 的 4 个真实数据用例、`test_reranker_wiring.py` 的 1 个置顶用例仍断言旧语料的 `craft_id`、中文技艺名或 `curated:*` ID；`test_retrieval_dataset_v1.py` 的 1 个用例要求旧评测证据 ID 存在于当前加载器输出。当前图书片段中，带有 `craft_id`、`craft_name`、`publication_status`、`source_url` 的数量均为 **0/7,688**，带 `book_title` 的数量为 **7,688/7,688**。4 条包含技艺名的旧置顶检查查询，Top 1 均返回 `book:*`，没有技艺 ID。

旧 `retrieval-v1` 评测集有 120 题，使用 45 个不同的预期证据 ID；这些 ID 在当前语料中命中 **0/45**。只有 10 条本来就没有预期证据的库外题满足“预期 ID 均存在”的空集条件。由此，历史 Recall@K 不能作为当前图书语料的检索质量数据；上述 6 个失败也不能直接解释为 6 次语义检索错误。

## 后续验收建议

1. 将旧语料的回归用例显式绑定旧语料目录；为激活后的图书语料单独设契约测试，至少检查 `book:*` ID、来源、页码和正文可追溯性。这样两套语料的测试都能稳定运行。
2. 为图书语料重新标注一组带 `book:*` 证据 ID 的题集，固定题目、来源版本和判分规则后，才报告 Recall@1/3/5、MRR 与库外拒答率。不要改写旧题答案来凑指标。
3. 清理 Ruff 72 条错误，优先处理重复定义和未使用变量；给 `App.spec.ts` 的耗时来源做独立诊断，再决定是否调整测试隔离或超时。
4. 针对 API、工作流节点、检索器和文档加载器的未覆盖路径，增加数据库/服务替身下的契约测试；单独安排真实数据库、模型及多轮问答的集成评测。入口 JS 体积应在确定目标设备和加载预算后再做性能验收。

## 复现命令（PowerShell）

在项目根目录运行：

```powershell
$env:COVERAGE_FILE = Join-Path $env:TEMP 'heritagemind-coverage-20261005'
python -m coverage run --source=src,api,config -m pytest tests/ --basetemp (Join-Path $env:TEMP 'heritagemind-pytest-20261005') -q --tb=short -p no:cacheprovider
python -m coverage report -m
ruff check src/ api.py config.py --statistics
Push-Location frontend
npm run test
npm run build
Pop-Location
```

后端第一次运行未禁用 pytest 缓存插件，因此出现 2 条本地 `.pytest_cache` 写入警告；上面的复现命令加入 `-p no:cacheprovider` 避免该环境噪声。测试失败数和覆盖率来自第一次实际运行，没有因上述命令改写。

## 当日后续复测

已把旧语料的 6 个失败用例显式绑定旧资料目录，并新增图书语料评测校验测试。随后全量后端回归实测为 **325 通过、1 跳过、0 失败**（47.67 秒）；这是后续工作区状态，不覆盖上面的首次测试记录。新的活动图书检索与本地 rerank 对照见[评测协议](evaluation-protocol-books-v1.md)。仓库原有的 Ruff 72 条错误仍未清理。

## 120 题评测集扩容后的复测（2026-10-06）

活动图书题集从 40 条扩为 120 条（60 条直问、40 条改写、20 条库外），并保留片段 ID、页码、引文和内容哈希校验。执行 `python -m pytest tests/ -q -p no:cacheprovider --basetemp (Join-Path $env:TEMP 'heritagemind-pytest-120cases')` 的结果为 **331 通过、1 跳过、0 失败**，耗时 **35.56 秒**。本次出现 7 条依赖弃用警告；没有运行外部 LLM 或本地向量模型。新的 rerank 实测结果见[120 题评测协议](evaluation-protocol-books-v1.md)。
