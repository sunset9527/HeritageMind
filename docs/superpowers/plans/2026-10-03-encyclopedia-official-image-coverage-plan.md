# 百科官方图片覆盖实施计划

> 对应设计：`2026-10-03-encyclopedia-official-image-coverage-design.md`

## 1. 固化图片清单解析器与后端契约

1. 新建 `src/services/encyclopedia_images.py`，定义图片状态、图片记录和版本化 JSON 清单读取器。
2. 先写失败测试：拒绝重复技艺、未知状态、`verified` 条目缺来源页或来源机构、非本地旧图缺 URL。
3. 建立 `data/knowledge_sources/image_manifest.json`：先收录 23 项已有本地资源为 `legacy_local`，其他公开条目由解析器返回 `unavailable`；不预填伪造的图片地址。
4. 为百科响应 DTO 添加 `image: { url | null, status }`；`/encyclopedia` 和 `/encyclopedia/{slug}` 都返回同一结构。
5. 先写 API 契约测试，验证旧图、无映射、已核验外链分别返回正确状态；再以最小实现通过测试。

## 2. 建立官方图源候选与人工核验流程

1. 新建只读候选清单 `data/knowledge_sources/image_candidates/`，记录技艺名、来源页、候选图片地址、机构、搜索日期和候选状态。
2. 仅允许中国非遗网、文化和旅游系统、地方政府或公立博物馆来源；候选不直接写入发布清单。
3. 为每项检查名称对应关系、图片是否来自来源页、直链可访问性和机构身份；通过后才移动为 `verified`。
4. 逐小批提交，记录已核验数、待复核数、拒绝原因和外链可用性；外链失效会退回 `pending_review`/`unavailable`。

## 3. 前端共用图片组件

1. 先写 Vitest 失败测试，描述已核验图片、加载失败、无图状态及无破损 `<img>` 的预期 DOM。
2. 新建 `EncyclopediaImage.vue`：骨架加载、图片加载成功、失败后替换为“待补充图像”视觉卡片；`alt` 包含技艺名。
3. 修改 `EncyclopediaView.vue`、`CraftCarousel.vue`，移除 `/crafts/${name}.jpg` 拼接，统一传入 API 的 `entry.image`。
4. 在 `CraftDetailView.vue` 添加同一组件，使列表、首页和详情使用一致视觉与降级逻辑。
5. 运行前端单测、类型检查与生产构建。

## 4. 回归、演示与治理验证

1. 后端运行图片清单测试、平台 API 测试和完整 `pytest`。
2. 前端运行 `npm test` 与 `npm run build`。
3. 启动前后端，检查旧 23 项图片、已核验官方外链、`unavailable` 兜底以及窄屏布局。
4. 验收只报告已核验的官方实拍图数量；不把候选数或百科条目数表述为图片已完成覆盖。

## 交付顺序

先交付“接口携带图片状态 + 前端无破图降级 + 23 项旧图兼容”，再逐批补齐官方图源。这样可立即解决截图中的破图，同时不降低来源治理标准。
