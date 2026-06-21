# 🏺 非遗知识问答系统

基于多智能体架构的非遗知识保存与传承平台，以传统技艺传承为例。

> **核心理念**：非遗知识是"正在消失的活知识"，不只是问答问题，更是知识保存与传承问题。

## 🎯 项目简介

本项目旨在构建一个基于多智能体的非遗（非物质文化遗产）知识问答系统，通过模拟不同领域的专家Agent协作，覆盖完整的知识链条，实现知识的智能化保存、检索和传承。

### 五大深度点

| 深度点 | 说明 |
|--------|------|
| **多专家Agent协作** | 不同领域Agent各自检索+生成，调度Agent融合，各有知识边界 |
| **知识缺口检测** | Agent识别知识库中的空白领域，能发现"不知道什么" |
| **多粒度知识服务** | 同一问题，入门者/学习者/研究者看到不同深度 |
| **非遗知识图谱** | 技艺→材料→工具→传承人→地域的多维关联 |
| **传承人视角叙事** | 用传承人师傅的口吻讲述技艺（模拟师徒对话风格） |

## 🏗️ 系统架构

```
用户提问（如：景泰蓝制作流程是什么？）
  → 调度Agent（分析问题类型，分配给专家Agent）
    → 技艺知识Agent（工艺流程、材料、工具）
    → 历史文化Agent（起源、演变、文化意义）
    → 传承现状Agent（传承人、濒危程度、保护措施）
  → 知识融合（多视角整合）
  → 知识缺口检测（知识库够不够？有没有缺失？）
    → 充足 → 生成回答
    → 不足 → 标注"知识缺口"+提示需要补充的方向
  → 自适应学习路径（根据用户身份：好奇者/学习者/研究者，给不同深度）
```

## 📁 项目结构

```
项目二_非遗多智能体问答/
├── README.md
├── requirements.txt
├── config.py                    # 配置管理
├── main.py                      # Streamlit前端
├── api.py                       # FastAPI后端
├── src/
│   ├── agents/                  # Agent模块
│   │   ├── dispatcher.py        # 调度Agent
│   │   ├── craft_expert.py      # 技艺知识Agent
│   │   ├── history_expert.py    # 历史文化Agent
│   │   └── heritage_expert.py   # 传承现状Agent
│   ├── knowledge/               # 知识模块
│   │   ├── gap_detector.py      # 知识缺口检测
│   │   ├── granularity.py       # 多粒度控制
│   │   └── narrative.py         # 叙事生成
│   ├── graph/                   # 知识图谱
│   │   ├── heritage_graph.py    # NetworkX图谱
│   │   └── builder.py           # 图谱构建
│   ├── retrieval/               # 检索模块
│   │   ├── document_loader.py    # 文档加载
│   │   └── retriever.py         # 多源检索
│   ├── workflow/                # LangGraph工作流
│   │   ├── graph.py            # 主工作流
│   │   ├── nodes.py            # 工作流节点
│   │   └── state.py            # 状态定义
│   └── utils/                  # 工具模块
│       └── prompts.py          # Prompt模板
├── data/
│   ├── crafts/                 # 非遗技艺文档
│   │   ├── 景泰蓝.txt
│   │   ├── 苏绣.txt
│   │   ├── 龙泉青瓷.txt
│   │   ├── 宜兴紫砂.txt
│   │   ├── 芜湖铁画.txt
│   │   └── 蜀锦.txt
│   ├── heritage_graph.json     # 预构建知识图谱
│   └── user_profiles.json     # 用户画像
└── tests/                      # 测试文件
```

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 多Agent编排 | LangGraph |
| 文档检索 | LangChain |
| 向量数据库 | ChromaDB |
| 知识图谱 | NetworkX |
| LLM | DeepSeek API |
| 后端API | FastAPI |
| 前端界面 | Streamlit |
| 配置管理 | Pydantic Settings |

## 🚀 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key

设置环境变量或创建 `.env` 文件：

```bash
export DEEPSEEK_API_KEY="your-api-key"
```

或在项目根目录创建 `SECRET.md`：

```
DEEPSEEK_API_KEY=your-api-key
```

### 3. 启动服务

**方式一：分别启动后端和前端**

```bash
# 终端1：启动FastAPI后端
python api.py

# 终端2：启动Streamlit前端
streamlit run main.py --server.port 8501
```

**方式二：直接运行**

```bash
# 访问 http://localhost:8501 查看前端界面
streamlit run main.py

# API服务
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### 4. 运行测试

```bash
pytest tests/ -v
```

## 📡 API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/query` | POST | 非遗知识问答 |
| `/upload` | POST | 上传非遗文档 |
| `/graph/stats` | GET | 知识图谱统计 |
| `/graph/query` | POST | 图谱查询 |
| `/gap-report` | GET | 知识缺口报告 |
| `/switch-profile` | POST | 切换用户画像 |
| `/crafts` | GET | 技艺列表 |
| `/profiles` | GET | 用户画像列表 |

## 👤 用户画像

| 画像 | 说明 | 内容深度 |
|------|------|----------|
| 好奇者 | 对非遗有初步兴趣 | 浅层，300-500字 |
| 学习者 | 想要系统学习 | 中层，800-1500字 |
| 研究者 | 需要深度资料 | 深层，2000+字 |

## 🎭 特色功能

### 传承人视角叙事

开启后，系统会以老匠人口吻讲述技艺知识：

> "这一步叫掐丝，铜丝得顺着花纹走，手不能抖，力道要匀。我师父当年说，掐丝就是跟铜丝说话，你急了它就歪。"

### 知识缺口检测

当知识库信息不足时，系统会提示：

> ⚠️ **知识缺口提示**：针对您的问题，当前知识库覆盖情况为"部分覆盖"，建议补充以下方向的资料：...

## 🔄 与通用多Agent的对比

| 特性 | 通用多Agent | 本系统 |
|------|------------|--------|
| 问题理解 | 通用意图识别 | 非遗领域深度理解 |
| Agent协作 | 固定组合 | 动态分配，按需调度 |
| 知识边界 | 模糊 | 清晰的专业分工 |
| 知识缺口 | 忽略 | 主动检测与报告 |
| 用户适配 | 单一输出 | 多粒度自适应 |
| 叙事风格 | 无 | 传承人视角可选 |

## 📚 支持的非遗技艺

- 🏛️ **景泰蓝** - 国家级非遗
- 🪡 **苏绣** - 国家级非遗  
- 🏺 **龙泉青瓷** - 国家级非遗
- 🍵 **宜兴紫砂** - 国家级非遗
- 🔨 **芜湖铁画** - 国家级非遗
- 🧵 **蜀锦** - 国家级非遗

## 📄 License

MIT License

## 🙏 致谢

本项目受非遗保护理念启发，旨在用现代技术助力传统文化传承。
