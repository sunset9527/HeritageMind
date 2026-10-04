# 中国非物质文化遗产网项目候选采集器设计

**日期：** 2026-10-04  
**状态：** 已确认，待实现

## 目标

提供一个按单个技艺名称运行的命令行采集器。它只从中国非物质文化遗产网（`https://www.ihchina.cn`）的站内搜索和国家级代表性项目详情页采集待审核候选资料，输出项目元数据、受限长度的简介摘录与页面关联图片候选链接。

该工具不将任何内容直接导入 `knowledge_documents`、不发布知识资料、不下载媒体文件，也不改变百科图片的 `verified` 状态。

## 非目标

- 不遍历或全量抓取全站、国家级名录或搜索结果；
- 不抓取新闻、图集、影音、附件或第三方域名资源；
- 不下载、镜像、二次分发图片、音视频或原始网页；
- 不依据简称、相似名称或多个搜索结果自动选择项目；
- 不自动把网页简介当作可发布的深度资料。

## 使用方式

```powershell
python tools/crawl_ihchina_project.py "宜兴紫砂陶制作技艺" --acknowledge-ihchina-terms
```

默认输出到 `data/knowledge_sources/candidates/ihchina-projects/`。单次运行只处理一个名称；可用 `--output` 指定输出 JSON 文件，用 `--delay` 调整请求间隔（默认 2 秒），用 `--max-candidates` 限制最多访问的详情候选数（默认 3）。

## 数据流

```text
输入技艺名
  → IHChina 站内搜索页
  → 提取 /project_details/*.html 候选链接
  → 最多请求 3 个同域详情页（限速）
  → 标题规范化精确匹配
  → 解析项目元数据、简介摘录、页面图片候选
  → candidate JSON（needs_review）
```

若没有候选，输出 `not_found`；有候选但没有唯一精确名称匹配，输出 `ambiguous` 并保留候选 URL；网络、HTTP 或结构异常输出 `fetch_failed` 或 `parse_failed`，不得伪装成空结果。

## 输出模型

```json
{
  "dataset_version": "ihchina-project-candidate-v1",
  "query_name": "宜兴紫砂陶制作技艺",
  "status": "needs_review",
  "searched_at": "2026-10-04",
  "source_name": "中国非物质文化遗产网·中国非物质文化遗产数字博物馆",
  "source_page_url": "https://www.ihchina.cn/project_details/12345.html",
  "matched_craft_name": "宜兴紫砂陶制作技艺",
  "project_code": "Ⅷ-114",
  "category": "传统技艺",
  "declaring_region_or_unit": "江苏省宜兴市",
  "protection_unit": "示例保护单位",
  "introduction_excerpt": "不超过 500 个字符的页面简介摘录",
  "image_candidates": [
    {
      "image_url": "https://www.ihchina.cn/...jpg",
      "alt": "页面中可见的替代文本",
      "context": "详情页图片候选",
      "source_page_url": "https://www.ihchina.cn/project_details/12345.html",
      "status": "pending_review"
    }
  ],
  "license_note": "候选资料仅供人工核验；图片未下载、未镜像、未获再发布授权。"
}
```

`introduction_excerpt` 只供编辑人员核验和自行整理事实摘要，不能直接作为 `deep_summary` 正文。图片候选需另行核验项目关联、来源稳定性与使用边界，才可按现有图片治理流程进入图片清单。

## 安全与来源边界

- 请求前必须显式传入 `--acknowledge-ihchina-terms`；这是对站点版权与免责声明的人工确认，而不是授权替代。
- 仅允许 `https` 且 `www.ihchina.cn` 主机；重定向后的地址也必须复核。
- 每个请求设置连接和总超时，使用有限重试；默认相邻请求等待 2 秒。
- `robots.txt` 在设计核验日返回 404，因此采集器不以此推定网站允许大规模访问，始终维持“单名称、小候选、低频”模式。
- 只保存来源 URL、结构化事实、受限摘录和候选图片 URL；不保存图片二进制、不创建本地媒体文件。

## 组件边界

- `src/services/ihchina_project_parser.py`：纯离线函数。解析搜索页候选、详情页字段、图片候选；不发网络请求。
- `tools/crawl_ihchina_project.py`：CLI 编排、输入校验、受控 HTTP 获取、延时、状态输出与 JSON 落盘。
- `tests/test_ihchina_project_parser.py`：用精简的合成 HTML fixture 测试解析、精确匹配和图片同域过滤。
- `tests/test_crawl_ihchina_project.py`：用注入的假获取函数测试状态转换、术语确认开关和不匹配时不输出项目详情。

网络层通过依赖注入与解析层隔离，离线测试不访问网站、不依赖 BGE、数据库或浏览器。

## 验收与测试

1. 搜索页能提取去重后的 `/project_details/*.html` 同域候选；
2. 详情页能提取项目编号、类别、申报地区或单位、保护单位和最大 500 字的简介摘录；缺失字段保持 `null`，不填造；
3. 仅唯一精确匹配产生 `needs_review`，否则为 `not_found` 或 `ambiguous`；
4. 图片只保留 `www.ihchina.cn` 的 HTTPS 直链并标记 `pending_review`；
5. 未传确认参数时 CLI 在发起请求前失败；
6. 所有新测试离线通过，现有候选发现测试保持通过。

## 与现有数据治理的关系

该工具替代不了深度资料验收：每个项目仍须由不同来源机构、不同 URL 与事实维度支持。它只能生成一个可追溯的官方来源候选；编辑人员审核并撰写自己的事实摘要后，才可进入 `draft` 与 `published` 流程。
