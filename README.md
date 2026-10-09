# HeritageMind｜证据可追溯的非遗 AI 知识平台

> 用本地可追溯资料、检索重排与多智能体协作，帮助用户理解中国非物质文化遗产；证据不足时明确展示知识边界。

FastAPI · Vue 3 · LangGraph · BM25 · BGE-M3 · bge-reranker-base · ChromaDB · MySQL

## 项目定位

非遗问答要解决三件事：资料来自哪里、回答能否回到原始证据、资料不足时是否会把猜测说成事实。HeritageMind 的工程链路：

~~~text
用户提问 → 会话与问题路由 → 候选检索 → Cross-Encoder 重排 → 多专家协作
   │                                                       │
   └──── 本地来源化资料 / 活动图书语料 ───────────→ 引用、轨迹与知识缺口提示
~~~

检索指标只评价标注证据是否被找回，不等同于最终生成回答的事实正确率；回答还受引用、工作流和 Gap Detector 约束。

## 项目速览

| 项目 | 当前状态与可核对位置 |
| --- | --- |
| 默认可切换语料 | 可将本地 PDF/EPUB 构建为活动图书语料；正文目录被 Git 忽略，避免提交受版权保护的原文。 |
| 当前评测语料 | heritage-books-v1：10 本书、7,688 个片段；哈希、题集和判分口径见 [图书评测协议](docs/evaluation-protocol-books-v1.md)。 |
| Rerank 对照 | 本地 bge-reranker-base 实际加载成功；120 题中，项目关键词 Recall@1 从 61.0% 升至 80.0%，BM25 Recall@5 从 89.0% 升至 95.0%。 |
| 工程回归 | 最近一次后端全量离线回归为 331 通过、1 跳过、0 失败，耗时 35.56 秒；见 [工程化测试记录](docs/engineering-test-2026-10-05.md)。 |
| 历史资料包 | data/knowledge_sources 保留已发布来源化资料，供未激活图书语料时加载；它不等于当前活动图书语料。 |

## 功能与边界

| 能力 | 实现 | 边界 |
| --- | --- | --- |
| 多智能体问答 | 调度器分发技艺、历史、传承专家，由 LangGraph 汇总。 | 问答需要 LLM Key；无证据时应查看知识缺口提示。 |
| 检索与重排 | 关键词、BM25、BGE-M3 向量、RRF 与 Cross-Encoder。 | 当前图书语料实测关键词/BM25 加 rerank；本轮没有 BGE-M3 向量或 RRF 数据。 |
| 证据追溯 | 图书片段保存书名、页码、内容哈希、原生文字或 OCR 来源。 | 图书正文不随仓库发布，复现需要同一份本地语料。 |
| 知识图谱与百科 | NetworkX 图谱、百科、传承人和管理员审核。 | 图谱候选和公开内容都需要人工审核。 |
| 会话与媒体 | 登录会话、回答反馈、图片/音频/文档上传与音频文本检索。 | Redis 不可用时使用进程内缓存。 |

## 架构

~~~text
Vue 3 (5173) ── /api 代理 ──> FastAPI (8001，本机开发)
                                      │
          LangGraph ── Retriever（BM25 / vector / RRF / rerank）
                                      │
            活动图书语料 或 来源化资料 ── MySQL / ChromaDB / NetworkX
~~~

Docker 容器内 API 使用 8000，与本机开发端口 8001 不同。

---

# 使用手册

## 1. 安装与配置

### 前置软件

| 软件 | 建议版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | 后端、数据构建、评测；当前本机验证是 3.13.7。 |
| Node.js | 18+ | Vue 前端。 |
| MySQL | 8.x | 账号、会话、公开内容等关系数据。 |
| Docker Desktop | 可选 | Compose 容器运行。 |

BGE-M3 用于向量能力，bge-reranker-base 用于交叉编码重排。模型首次调用时加载；运行时加载失败会按原排序回退。Rerank 评测必须使用项目自带的校验脚本，避免把回退结果误记为模型结果。

### 安装依赖

在 PowerShell 的项目根目录执行：

~~~powershell
git clone https://github.com/sunset9527/HeritageMind.git
cd HeritageMind
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env

Push-Location frontend
npm ci
Pop-Location
~~~

若锁文件不匹配，再使用 npm install。 .env 包含密钥和本机路径，不能提交到 Git。

### 配置 .env

先创建数据库：

~~~powershell
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS heritagemind CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
~~~

在 .env 填入实际值：

~~~dotenv
DATABASE_URL=mysql+pymysql://root:<你的MySQL密码>@127.0.0.1:3306/heritagemind
DEEPSEEK_API_KEY=<你的LLM密钥>

# Windows 路径可使用正斜杠
EMBEDDING_MODE=local_first
LOCAL_EMBEDDING_MODEL_PATH=E:/huggingface/model
RERANKER_ENABLED=true
RERANKER_MODEL=E:/huggingface/bge-reranker-base
~~~

- 没有 DEEPSEEK_API_KEY 时，模型问答会受限；数据、百科和图谱接口仍可检查。
- 没有本地 BGE-M3 时，按 .env.example 选择 API 向量模式，或暂不启用向量检索。
- RERANKER_ENABLED=false 可用于排查模型或降低 CPU 延迟，但不能复现“开启 rerank”的指标。

### 初始化

~~~powershell
python -m alembic upgrade head
python -m src.services.public_content_seed
~~~

public_content_seed 从已审核资料清单创建缺失公开内容，可重复运行，不创建重复项，也不会覆盖已有非空人工内容。它服务于旧来源资料投影；图书语料投影见第 4 节。

## 2. 启动开发环境

第一个 PowerShell 窗口：

~~~powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8001 --reload
~~~

- 健康检查：http://127.0.0.1:8001/health
- OpenAPI 文档：http://127.0.0.1:8001/docs

确认 frontend/.env.development 的目标端口：

~~~dotenv
VITE_API_BASE_URL=/api
VITE_PROXY_TARGET=http://127.0.0.1:8001
~~~

第二个窗口：

~~~powershell
cd frontend
npm run dev
~~~

访问 http://127.0.0.1:5173。Vite 将 /api 代理给后端，不要将 API 地址写死在页面代码里。

最小验收：访问 /health；打开百科和图谱确认前端代理可用；配置 LLM 和模型后提交一个有明确出处的问题，检查引用与知识缺口提示。

## 3. 日常开发与验证

### 后端回归

~~~powershell
python -m pytest tests/ -q -p no:cacheprovider --basetemp (Join-Path $env:TEMP 'heritagemind-pytest')
~~~

该命令不调用外部 LLM 或本地模型。2026-10-06 当前工作区复测为 331 passed, 1 skipped；测试范围与首次失败定位见 [工程化测试记录](docs/engineering-test-2026-10-05.md)。

### 前端测试和构建

~~~powershell
Push-Location frontend
npm run test
npm run build
Pop-Location
~~~

npm run build 同时执行 Vue TypeScript 检查和 Vite 生产构建。最近一次工程记录中，28 个前端测试通过，构建通过但入口包有体积警告；构建成功不能替代性能验收。

### 静态检查现状

~~~powershell
ruff check src/ api.py config.py --statistics
~~~

截至 2026-10-05，检查仍报告 72 条既有问题，主要是未使用导入、未使用变量和一行多语句。它是待清理项，不能描述为已通过的质量门禁。

### 验证 Rerank 是否真正启用

先确认活动图书语料、RERANKER_ENABLED=true 和本地模型路径，再运行：

~~~powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
python -m pytest tests/test_books_rerank_evaluation.py -q -p no:cacheprovider
python -m src.evaluation.run_books_rerank --dataset data/evaluation/retrieval-books-v1.jsonl --output data/evaluation/reports/retrieval-books-v1-rerank-local.json --candidate-k 15 --top-k 5
Get-FileHash data/local_books_corpus/documents.jsonl -Algorithm SHA256
~~~

评测脚本要求结果含 rerank_score；模型加载失败而回退时，脚本报错而不生成“开启 rerank”的分数。输出 JSON 保存逐题候选、排序、指标和延迟。

## 4. 管理本地图书语料

### 语料工作流

~~~text
本地 PDF / EPUB → 预检 → 可续跑的分页/分段构建 → staged → --activate
          → 技艺元数据 → 审核候选与来源审计 → 发布公开投影
~~~

输出默认在 data/local_books_corpus，目录被 Git 忽略。保留图书来源、许可和文件哈希；不要提交原书或生成的正文片段。

### 预检、构建与激活

将 <图书目录> 替换为 PDF/EPUB 所在目录：

~~~powershell
# 只检查文件与格式；不读取图书正文，不写输出
python tools/build_local_books_corpus.py --library '<图书目录>' --dry-run

# 实际构建；成功后切换默认检索语料
python tools/build_local_books_corpus.py --library '<图书目录>' --corpus-id heritage-books-v1 --activate

# 查看进度
python tools/build_local_books_corpus.py --progress
~~~

构建写入 progress.json，中断后用原命令继续，已完成页会跳过。构建完成后才会写入并激活 catalog。激活后重启后端，使内存检索器加载新语料。

当 catalog 状态为 active 时，加载器只读取图书语料。catalog 或 documents.jsonl 损坏时，加载器拒绝静默回退到旧资料，避免混用两套知识库。

### 生成并审核公开投影

~~~powershell
# 从活动图书语料生成基础技艺元数据
python tools/build_craft_metadata.py data/local_books_corpus

# 生成只供审核的候选与来源覆盖审计
python tools/build_reviewed_books_candidate.py
python -X utf8 tools/activate_reviewed_books_candidate.py --check

# 仅在审核和校验通过后执行
python -X utf8 tools/activate_reviewed_books_candidate.py
~~~

候选文件位于 data/knowledge_sources/candidates/books-rebuild。激活脚本会备份已有 craft_metadata.json。先人工核对名称、OCR、页码与覆盖审计，再发布公开页面。

### 回退

停止后端并备份 data/local_books_corpus。将 catalog.json 移出该目录，或把 status 从 active 改为 staged，再重启后端；加载器会回到 data/crafts 与 data/knowledge_sources。回退后应重新运行对应测试和评测。

## 5. 检索与 Rerank 评测

2026-10-05，对已激活的 heritage-books-v1 做了 120 题内部探索性评测：100 条可回答题（60 条直问、40 条改写）和 20 条库外题。Cross-Encoder 本地模型 bge-reranker-base 已实际加载；每种初检用同一 Top-15 候选，比较关闭/开启 rerank 后的 Top-5：

| 初检路径 | Rerank | Recall@1 | Recall@3 | Recall@5 | MRR | Top-15 候选召回 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 项目关键词 | 关闭 | 61/100（61.0%） | 77/100（77.0%） | 81/100（81.0%） | 0.692 | 85/100（85.0%） |
| 项目关键词 | 开启 | 80/100（80.0%） | 85/100（85.0%） | 85/100（85.0%） | 0.823 | 85/100（85.0%） |
| BM25 | 关闭 | 79/100（79.0%） | 85/100（85.0%） | 89/100（89.0%） | 0.826 | 95/100（95.0%） |
| BM25 | 开启 | 85/100（85.0%） | 95/100（95.0%） | 95/100（95.0%） | 0.897 | 95/100（95.0%） |

CPU 上 rerank 增量延迟中位数为：项目关键词 3,359.66 ms/题，BM25 为 3,335.33 ms/题；不含首次模型加载 14.50 秒。它们是单题串行统计，不能当成并发吞吐量或线上延迟。

正确解读这些指标：

- 题目由同一人从图书片段编写，且 60/100 是直问；各书题目数量为 3–22 条，不能外推为真实用户问题的线上准确率或各书的等权表现。
- 每题当前仅标注一个金标准片段，可能漏标其他有效证据，因此判分保守但不完整。
- 20 条库外题在纯检索与重排中都是 0/20 正确拒答，因为本轮未接入 Gap Detector；这不评价完整问答工作流的拒答能力。
- 当前图书语料没有已建成的 BGE-M3 全量向量索引。本轮没有 BGE-M3 或 RRF 的结果，不能用旧资料包的历史基线替代。

完整题集、语料 SHA-256、逐题排序、候选上限、模型加载校验和失败样本见 [活动图书语料检索与 Rerank 评测](docs/evaluation-protocol-books-v1.md)。历史来源资料包的实验在 [历史评测协议](docs/evaluation-protocol-v1.md)，不能和本表混合比较。

## 6. 容器运行

Compose 的 api 服务与 MySQL 运行在 Docker 网络中，API 内部端口是 8000；Vue 开发容器通过 http://api:8000 访问它。

~~~powershell
# 启动 MySQL 与 API；不会启动默认 Streamlit 前端
docker compose up --build mysql api

# 另开窗口启动 Vue 开发容器，浏览器访问 5173
docker compose --profile vue up --build vue-frontend
~~~

默认 frontend 服务是保留的 Streamlit 界面，端口 8501；Vue 服务是 vue profile 下的 vue-frontend。生产 Nginx 使用 production profile；域名、HTTPS、管理员初始化和上线边界见 [部署交接文档](deploy/README.md)。不要把 Compose 示例默认密码用于公网。

## 7. 常见问题

**前端打开但 API 失败**：确认后端运行在 8001，且 frontend/.env.development 的 VITE_PROXY_TARGET 是 http://127.0.0.1:8001。修改后重启 npm run dev。

**Rerank 很慢或没有生效**：检查日志中的模型加载消息，以及结果是否含 rerank_score。本机 CPU 实测单题约 3.3 秒，适合离线评测和低并发。临时设 RERANKER_ENABLED=false 可排查问题，但会改变检索链路。

**图书构建中断**：运行 python tools/build_local_books_corpus.py --progress，再用原构建命令继续。不要手工混合不同图书版本生成的 documents.jsonl 与 catalog.json。

**图书切换后旧测试失败**：旧资料证据 ID 和活动图书片段 ID 是两套契约。激活图书语料时使用图书题集和图书专属测试；回退后再验证旧资料测试。

**MySQL 连不上**：检查 MySQL 服务、DATABASE_URL 的主机/端口/密码，以及 heritagemind 是否已创建。先访问 /health 区分 API 是否启动成功，再查看启动日志中的数据库异常。

## 8. 项目目录

~~~text
api.py                         FastAPI 入口与应用生命周期
config.py                      环境变量与配置
src/agents/                    调度器、专家 Agent、辩论引擎
src/workflow/                  LangGraph 状态、节点与工作流
src/retrieval/                 文档加载、BM25、向量、RRF、重排
src/services/                  语料构建、来源清单、公开投影、会话、媒体
src/evaluation/                活动图书语料评测运行器
frontend/                      Vue 3、Pinia、百科、图谱、问答与管理界面
data/knowledge_sources/        来源资料清单与审核候选
data/evaluation/               题集、报告与指标校验
data/local_books_corpus/       本地图书输出（Git 忽略）
tests/                         离线回归与评测契约测试
docs/                          评测、数据治理、工程记录和部署说明
tools/                         构建、审核、激活等可执行工具
~~~

## 9. 贡献约定

欢迎 Issue 和 Pull Request。涉及知识库、检索、公开内容或指标的变更，请同时提交：

1. 来源与许可/使用边界；
2. 数据版本、题集和复现命令；
3. 新旧结果的分母、判分规则和失败样本；
4. 不通过删除失败题、重写金标准证据或编造数据提高指标的说明。

## License

当前仓库尚未声明开源许可证。复用前请先联系作者确认。
