# 本地图书逐页断点导入设计

## 目标

将本地图书导入改为逐页持久化：可查看已完成/总页数与百分比，可随时停止；下次在相同图书内容下从最后的完成页继续。新语料保持 `staged`，仅全部来源完成后才允许 `active`，旧资料不删除。

## 选择的方案

每个语料集输出目录包含：

- `documents.jsonl`：每完成一页，追加该页产生的片段并立即 flush；重复运行前会读取其中的稳定 document ID，跳过已完成页。
- `progress.json`：每页完成后原子更新。含所有源的 SHA-256、总单元数、已完成单元数、空页数、片段数、状态和当前 source/page；百分比由 completed/total 计算。
- `catalog.json`：仅在所有来源完成后一次性写入 `staged`。`--activate` 只接受完整 staged catalog。

文档 ID 包含 source SHA、页码/章节号和 chunk 序号，因此同一文件内容的重复执行自然去重。文件 SHA 变化时 ID 变化，旧片段不会被误当作新版本完成页。

## 错误和停止

进程被杀、断电或发生异常时，已经 flush 的页和最后一次原子 progress 都保留；没有 catalog，所以默认检索不会切换。重新执行时跳过完成 ID，并继续未完成页。单页 OCR 错误被记录为失败页，不会伪造为空页；构建结束时保留 `incomplete` 状态并拒绝激活。

## 验收

1. 第一页完成后立即存在 documents 与 progress，progress 显示正确百分比。
2. 模拟在第二页异常中断，再运行会跳过第一页，只处理第二页及以后。
3. 全部页成功才生成 staged catalog；中断/失败时不能激活。
4. 进度命令只读 `progress.json`，不触发 PDF/OCR。
