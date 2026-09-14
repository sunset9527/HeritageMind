# HeritageMind 检索评测协议 v1

## 评测对象与边界

`retrieval-v1.jsonl` 是版本化的证据级检索评测集，不使用历史 `hm100` 的“锚词存在才保留题目”规则。每条可回答问题关联一个或多个 `curated:{document_key}`；知识库外问题的期望证据为空。加载、指标与数据完整性校验遇到缺题、重复 ID 或无效证据都会失败，不能静默剔除样本。

题型固定为 120 条：直问 40 条、混淆 30 条、比较 25 条、多轮追问 15 条、知识库外问题 10 条。第一版由单人编写，比较和多轮题应在后续版本接受第二人复核；因此它是当前可复现的工程基线，不是对通用非遗问答能力的外推结论。

## 指标

- Recall@1 / @3 / @5：可回答问题中，任一可接受来源文档是否进入前 k。
- MRR：可回答问题中首个可接受来源文档的倒数排名；未命中计为 0。
- 正确拒答率：知识库外问题中，检索基线是否按预定义阈值拒答。

比较题有多个可接受来源文档；当前 Recall 只要求至少召回其中一个来源，不能表示多证据答案已完整覆盖。回答事实正确性、引用完整性与可读性需要在单独的人工盲标回答评测中报告，不能用这里的检索指标代替。

## 本地复现

```powershell
python -m pytest tests/test_retrieval_metrics.py tests/test_retrieval_dataset_v1.py tests/test_retrieval_baseline.py -q -p no:cacheprovider
python -m src.evaluation.run_retrieval_baseline --output data/evaluation/reports/retrieval-v1-bm25-YYYYMMDD.json
```

基线仅加载 `published` 的来源化文档，不加载缺乏来源状态的旧 `data/crafts/*.txt`。当前算法为 jieba 分词的 BM25，Top-K=5；库外题的临时拒答规则是最高 BM25 分数小于等于 0。该阈值仅用于暴露当前能力缺口，不代表生产级知识缺口检测策略。

## 首次真实基线

报告：[retrieval-v1-bm25-20260914.json](../data/evaluation/reports/retrieval-v1-bm25-20260914.json)。运行时语料为 46 份已发布来源化摘要，Git 提交为 `3397c56`。

| 范围 | Recall@1 | Recall@3 | Recall@5 | MRR | 正确拒答率 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 可回答 110 条 | 68.2% | 94.5% | 97.3% | 0.811 | — |
| 库外 10 条 | — | — | — | — | 0.0% |

分题型结果和全部排序、拒答状态、13 条失败明细均在报告中保留。下一步应将当前工作流的 gap detector 接入同一批库外题，并增加向量、RRF 和重排序在相同语料与题集下的对比；不应通过删除失败题或改写预期证据提高分数。
