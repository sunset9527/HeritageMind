"""Application metadata shared by the API and service discovery response."""

APP_VERSION = "2.2.0"

API_DESCRIPTION = """
## 概述
基于可追溯知识库与多智能体协作的非遗知识平台。

### 功能模块
- **问答**：三专家 Agent 协作、辩论引擎与知识缺口检测
- **知识库**：来源化资料与可切换的活动图书语料
- **知识图谱**：公开内容投影与交互式可视化
- **多媒体**：图片、音频、转写与检索
- **认证**：JWT 登录注册

### 当前统计口径
运行实例的当前统计请分别读取 `/dashboard/summary`、`/documents/summary`
和 `/graph/stats`。名录、深度资料、图书片段与图谱节点是不同口径。

### 使用方式
1. 无需认证的端点可直接调用；需要认证的端点需携带 `Authorization: Bearer <token>`。
2. 可通过 `X-API-Key`、`X-API-Base` 与 `X-Model` 请求头自定义 LLM 配置。
3. 未配置模型或可选依赖时，接口应明确返回受限或降级状态。
"""
