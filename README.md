# HeritageMind｜非遗 AI 知识平台

> 用可追溯的本地资料、混合检索、知识图谱与多智能体协作，帮助用户理解中国非物质文化遗产；证据不足时明确说明边界。

`FastAPI` · `Vue 3` · `LangGraph` · `BM25 + BGE-M3 + RRF` · `ChromaDB` · `MySQL` · `NetworkX`

## 项目展示

HeritageMind 面向“非遗知识如何被可靠解释”构建。回答附带本地证据、执行路线与知识缺口提示；百科、传承人和图谱页面都能回到明确的资料来源。

- **23 项非遗技艺**，覆盖陶瓷、丝织、雕刻、印染、纸艺、金属与戏曲等门类；
- **46 条已发布、可追溯的来源化资料**，每项技艺配有两条来源摘要；
- **23 个公开百科条目**与 **6 位有公开来源证据的传承人档案**；
- 完成公开内容初始化后，图谱有 **117 个节点、91 条关系**，包括 46 个资料来源节点。

## 核心能力

| 模块 | 实现与边界 |
| --- | --- |
| 混合检索 | jieba + BM25、BGE-M3 向量检索、RRF 融合与重排序；结果保留来源元数据。 |
| 多智能体问答 | 调度器按问题分派技艺、历史、传承专家，由 LangGraph 编排融合回答。 |
| 知识边界 | Gap Detector 在证据不足时提示知识缺口，不以模型补全替代事实。 |
| 知识图谱 | NetworkX + pyvis 可视化；资料来源节点以“收录来源”连接对应技艺。 |
| 公开内容 | 百科与传承人仅展示已发布记录；传承人发布必须包含公开来源证据。 |
| 质量闭环 | 登录用户可保留会话、评价回答；管理员可维护内容、审核图谱候选。 |
| 多媒体基础 | 支持图片、音频、文档上传与音频文本检索；Redis 不可用时降级为进程内缓存。 |

## 架构

```text
Vue 3 → FastAPI → LangGraph Workflow
                    ├─ Router / 会话上下文
                    ├─ 混合检索 / 多专家协作
                    ├─ 本地知识图谱
                    └─ 引用、轨迹与知识缺口提示
                         │
              MySQL · ChromaDB · 本地来源化资料
```

## 快速开始

环境要求：Python 3.11+、Node.js 18+、MySQL。向量检索使用本地 BGE-M3 模型；未配置模型或 LLM Key 时，百科、图谱和公开数据页面仍可启动，但部分问答能力会降级。

```powershell
git clone https://github.com/sunset9527/HeritageMind.git
cd HeritageMind
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env：配置 DATABASE_URL；按需填写 DEEPSEEK_API_KEY 和本地模型路径
python -m alembic upgrade head
cd frontend
npm install
cd ..
```

初始化公开内容。脚本由仓库内经过校验的资料清单生成百科和传承人记录；可重复执行，不会创建重复数据，也不会覆盖已有非空人工内容。

```powershell
python -m src.services.public_content_seed
```

```powershell
# 终端 1：后端，默认 http://127.0.0.1:8001
python -m uvicorn api:app --host 0.0.0.0 --port 8001 --reload

# 终端 2：前端，默认 http://127.0.0.1:5173
cd frontend
npm run dev
```

- 前端：<http://127.0.0.1:5173>
- API 文档：<http://127.0.0.1:8001/docs>

## 数据与评测

### 数据治理

来源化资料位于 `data/knowledge_sources/`。每条记录保存资料标题、来源机构、原始链接、采集日期、许可说明与正文摘要。`manifest.json` 是唯一清单入口，加载与导入时会校验文件路径、状态、链接格式、重复键和内容哈希。

百科内容与图谱资料节点均由同一份清单生成，避免检索、页面和图谱数据彼此漂移。

### 检索基线

评测集 `data/evaluation/retrieval-v1.jsonl` 有 120 条证据级问题：40 条直问、30 条混淆、25 条比较、15 条多轮追问、10 条知识库外问题。指标仅衡量检索是否找回可接受来源，**不等同于回答事实正确率**。

在同一 46 条来源化资料和同一题集上的实际结果：

| 方法 | Recall@1 | Recall@3 | Recall@5 | MRR | 知识库外正确拒答率 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 68.2% | 94.5% | 97.3% | 0.811 | 0% |
| 向量检索 | 78.2% | 95.5% | 97.3% | 0.866 | 0% |
| RRF | 72.7% | 97.3% | 98.2% | 0.848 | 0% |

RRF 的 Top-5 召回最高，向量检索的首位证据与 MRR 更好；三种纯检索方法对库外问题都不能正确拒答。完整口径、环境与失败样本见 [评测协议](docs/evaluation-protocol-v1.md)。

## 验证命令

```powershell
# 后端离线回归；使用当前用户的临时目录
python -m pytest tests/ --basetemp "$env:TEMP\heritagemind-pytest"

# 前端类型检查与生产构建
cd frontend
npm run build
```

GitHub Actions 会运行后端测试、来源清单/指标校验与前端生产构建；不下载本地模型，也不调用外部 LLM。

## 工程导航

```text
src/agents/                  调度器、技艺/历史/传承专家与辩论引擎
src/workflow/                LangGraph 状态、节点与工作流
src/retrieval/               BM25、向量检索、RRF、重排序与文档加载
src/graph/                   NetworkX 图谱与 pyvis 可视化
src/services/                数据清单校验、公开内容初始化、图谱投影、会话与媒体服务
frontend/                    Vue 3、Pinia、百科、图谱与问答页面
data/knowledge_sources/      46 条来源化资料及其版本化清单
data/evaluation/             120 条证据级检索评测与历史报告
tests/                       不依赖外网和模型的确定性回归测试
docs/                        数据治理、评测协议、设计与部署文档
```

## 贡献约定

欢迎提交 Issue 和 Pull Request。涉及知识库或指标的变更，请同时提供来源、适用范围和可复现命令；不要通过删除失败题、修改预期证据或编造数据来提高指标。

## License

当前仓库尚未声明开源许可证。复用前请先联系作者确认。
