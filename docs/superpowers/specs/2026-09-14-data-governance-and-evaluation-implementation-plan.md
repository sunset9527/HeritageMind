# HeritageMind 数据治理与效果评测实施计划

> 前置规格：[数据治理、知识扩充与效果评测设计](2026-09-14-data-governance-and-evaluation-design.md)

## 实施原则

- 先丰富现有 23 项资料，首批把景泰蓝、苏绣、龙泉青瓷、南京云锦、京剧、皮影戏做成多来源、可追溯的知识主题；新增技艺放在本期验收后。
- 复用已存在的 `CraftEntry`、`SourceEvidence` 与 `AuditLog`，不另造与 v2.0 平台平行的内容体系。
- 所有新行为先写离线确定性 pytest 并确认失败，再写最小实现；不把过程质量分数称作事实正确率。
- 未审核或无来源资料不能进入默认公开检索；旧文件保持原样，迁移只创建新记录与报告。

## 1. 清单格式与纯校验服务

**文件：** 新增 `src/services/knowledge_manifest.py`、`tests/test_knowledge_manifest.py`、`data/knowledge_sources/manifest.json` 和说明文档。

1. 定义 UTF-8 JSON 清单：稳定 `document_key`、`craft_name`、`title`、正文相对路径、来源机构、URL、访问日期、版权/使用说明与 `draft|published|legacy_unverified` 状态。
2. 先测试缺字段、非 HTTP(S) URL、路径越界、重复 key、重复内容哈希和非法状态均被拒绝；合法清单可得到规范化对象与 SHA-256 内容哈希。
3. 实现不依赖数据库的加载、校验和规范化函数，禁止读取清单目录之外的文件。
4. 提供一个最小示例，但不把假 URL 或编造事实标为 `published`。

**验收：** 数据包能脱离模型、数据库和网络完成校验；错误信息能定位到文档 key 和字段。

## 2. 多文档知识模型与审计

**文件：** 新增 `src/models/knowledge.py`、`src/services/knowledge_ingest.py`、迁移 `006_add_knowledge_documents.py`；更新 `src/models/__init__.py`、`src/database.py`；新增 `tests/test_knowledge_ingest.py`。

1. 先测试一次合法导入会创建一个 `KnowledgeDocument`、其来源证据与导入批次审计；重复导入不产生第二份文档；正文改变创建新版本并保留上一版本。
2. 添加 `KnowledgeDocument`：稳定 key、关联 `craft_entries`、标题、正文、内容哈希、版本、状态和时间；添加 `KnowledgeIngestRun`：清单版本、开始/结束时间、成功/跳过/失败统计与错误摘要。
3. 扩展既有 `SourceEvidence` 的可选来源机构、标题、访问日期、许可证说明和文档片段定位字段，保持现有传承人/百科接口兼容。
4. 导入服务将 `published` 文档和来源证据写入同一事务，失败回滚；写入 `AuditLog`，并让每次运行都有可查询结果。

**验收：** 同一包可幂等运行；更新有版本而不是静默覆盖；来源数据可由文档、证据和审计三处回溯。

## 3. 发布过滤、引用与旧资料迁移

**文件：** 更新 `src/retrieval/document_loader.py`、检索引用序列化服务；新增 `src/migrate_legacy_crafts.py`、`tests/test_knowledge_retrieval_filter.py`、`tests/test_legacy_craft_migration.py`。

1. 先测试默认加载只包含 `published` 新文档，显式兼容开关才读取 `legacy_unverified`；`draft`、`deprecated` 绝不进入默认结果。
2. 将新文档切分时写入 `document_key`、`evidence_id`、`source_url`、`source_name`、`dataset_version`、`publication_status`；回答引用展示文档标题、机构、URL 与片段。
3. 迁移脚本仅读取 `data/crafts/*.txt`，创建对应 `legacy_unverified` 记录和来源缺失报告，不改写原始文件。
4. 在管理端/API 已有来源展示结构中保留向后兼容字段，并提供新证据字段。

**验收：** 公开回答不会伪称旧资料为权威来源；每条新资料引用均能打开原始 URL 并定位到导入片段。

## 4. 六项重点技艺的首批资料包

**文件：** `data/knowledge_sources/documents/`、`data/knowledge_sources/manifest.json`、`docs/data-sources-v1.md`。

1. 对六项重点技艺分别选择至少两个独立的权威公开来源，记录 URL、机构、访问日期、可用范围和支持的具体事实。
2. 资料正文使用自行整理的摘要和结构化事实；不批量复制受版权保护的网页全文、图片或音视频。
3. 每项覆盖至少历史/工艺、代表特征或传承现状中的两个维度；事实不确定时在正文中保留限定语或不写入。
4. 导入后由管理员流程发布，生成数据集版本、数量清单和缺口清单。

**验收：** 六项均至少有两份不同来源的已发布文档；资料包能重复导入，且在默认检索中给出来源级引用。

## 5. 独立评测集与报告

**文件：** 新增 `data/evaluation/retrieval-v1.jsonl`、`data/evaluation/answer-v1.jsonl`、`src/evaluation/retrieval_metrics.py`、`src/evaluation/run_retrieval_baseline.py`、`tests/test_retrieval_metrics.py`、`docs/evaluation-protocol-v1.md`。

1. 先测试 evidence 级 Recall@k、MRR、无答案正确拒答率的固定输入输出；不允许脚本按锚词缺失静默删题。
2. 建立至少 120 条检索评测：直问、相近技艺混淆、跨文档比较/流程、多轮指代和知识库外问题分别统计。
3. 建立至少 40 条回答评测，记录参考证据、人工评分维度与标注/复核状态；有单人标注时在报告显示局限。
4. 比较 BM25、向量、RRF 与 RRF+重排，固定数据集版本、Git 提交、检索配置和运行环境；生成带日期的新报告，不覆盖历史结果。

**验收：** 指标口径、数据版本和失败样本可复现；检索命中与回答事实评价清楚分开。

## 6. CI、文档与回归

**文件：** 更新 `.github/workflows/ci.yml`、`README.md`；新增数据校验/轻量评测测试。

1. 在 CI 中运行清单校验、纯指标测试、pytest、Vue 类型检查和生产构建；不下载 BGE 或调用外部模型。
2. 完整基线作为本地命令运行，README 清楚说明其模型、数据路径、输出目录和不能代表的结论。
3. 运行所有后端测试和前端生产构建；记录真实结果、跳过项与无法在离线环境验证的依赖。

**验收：** 新数据和评测口径进入持续回归，README 不再将 Hit@5 误写为回答准确率。

## 推进节奏

先完成第 1–3 项，形成可验证的导入与发布链路；再收集并导入六项资料；最后构建评测集和 CI。每完成一个边界就运行其单测和受影响的回归测试，不在尚未通过的基础上叠加后续改动。
