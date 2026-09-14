"""
配置文件 - 非遗知识问答系统配置管理
使用pydantic-settings管理配置，API Key从环境变量读取
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """系统配置类"""

    # DeepSeek API配置
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API密钥，从环境变量DEEPSEEK_API_KEY读取"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API基础URL"
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek模型名称"
    )

    # 向量数据库配置
    vector_db_path: str = Field(
        default="./data/vector_db",
        description="Chroma向量数据库存储路径"
    )

    # 知识图谱配置
    heritage_graph_path: str = Field(
        default="./data/heritage_graph.json",
        description="非遗知识图谱JSON文件路径"
    )

    # 文档路径配置
    crafts_doc_path: str = Field(
        default="./data/crafts",
        description="非遗技艺文档目录"
    )
    user_profiles_path: str = Field(
        default="./data/user_profiles.json",
        description="用户画像配置文件路径"
    )

    # LLM配置
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM生成温度"
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="LLM最大生成token数"
    )

    # 检索配置
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="检索返回的Top-K结果数"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="相似度阈值"
    )
    chunk_size: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="文档分块大小（字符数）"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=200,
        description="文档分块重叠大小"
    )

    # 工作流配置
    max_expert_agents: int = Field(
        default=3,
        ge=1,
        le=5,
        description="最大并行专家Agent数量"
    )
    gap_detection_threshold: int = Field(
        default=3,
        ge=1,
        description="知识缺口检测阈值：文档数小于此值认为存在缺口"
    )
    gap_detection_min_relevance: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="知识缺口检测的最低平均相关度，用于LLM不可用时的规则兜底"
    )

    # 用户画像配置
    default_user_profile: str = Field(
        default="curious",
        description="默认用户画像：curious(好奇者)/learner(学习者)/researcher(研究者)"
    )

    # API服务配置
    api_host: str = Field(default="0.0.0.0", description="API服务主机")
    api_port: int = Field(default=8001, description="API服务端口")

    # Streamlit配置
    streamlit_port: int = Field(default=8501, description="Streamlit服务端口")

    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )

    # 数据库配置
    database_url: str = Field(
        default="mysql+pymysql://root:123456@localhost:3306/heritagemind",
        description="数据库连接URL。默认 MySQL，也可 SQLite: sqlite:///./data/heritage.db"
    )

    # JWT认证配置
    jwt_secret_key: str = Field(
        default="heritagemind-dev-secret-change-in-production",
        description="JWT签名密钥，生产环境必须修改为强随机字符串"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT签名算法"
    )
    jwt_expire_minutes: int = Field(
        default=60,
        ge=1,
        le=43200,
        description="JWT过期时间（分钟），默认60分钟，最长30天"
    )

    # Langfuse可观测性配置
    langfuse_public_key: str = Field(
        default="",
        description="Langfuse Public Key，用于LLM调用追踪"
    )
    langfuse_secret_key: str = Field(
        default="",
        description="Langfuse Secret Key"
    )
    langfuse_host: str = Field(
        default="http://localhost:3000",
        description="Langfuse服务地址"
    )
    langfuse_enabled: bool = Field(
        default=False,
        description="是否启用Langfuse LLM调用追踪"
    )

    # 传承人视角配置
    enable_narrative_mode: bool = Field(
        default=True,
        description="是否启用传承人视角叙事模式"
    )

    # Embedding配置
    embedding_model: str = Field(
        default="embedding-2",
        description="Embedding模型名称（API 模式用智谱模型名，本地模式用 BGE-M3 路径）"
    )
    embedding_dimensions: int = Field(
        default=1024,
        description="嵌入向量维度"
    )
    embedding_mode: str = Field(
        default="local_first",
        description="嵌入模式: 'local_first' 本地优先API兜底 / 'local' 仅本地 / 'api' 仅API"
    )
    local_embedding_model_path: str = Field(
        default="./models/bge-m3",
        description="本地 BGE-M3 模型路径（Docker 内 /models/bge-m3，Windows 本机 E:/huggingface/model）"
    )
    zhipu_api_key: str = Field(
        default="",
        description="智谱AI API Key"
    )
    zhipu_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        description="智谱AI API 基础URL"
    )

    # BM25配置
    bm25_enabled: bool = Field(
        default=True,
        description="是否启用BM25检索"
    )

    # Reranker配置
    reranker_model: str = Field(
        default="E:/huggingface/bge-reranker-base",
        description="Cross-Encoder Reranker模型路径（本地目录，2026-08-15 改为本地路径；"
                    "之前用 HF 模型名 BAAI/bge-reranker-base 走缓存目录，权重不完整会卡网络超时）"
    )
    reranker_enabled: bool = Field(
        default=False,
        description="是否启用Reranker重排序。v2.2 已接入检索链路（retriever.retrieve 精排）。"
                    "模型已下载到 E:/huggingface/bge-reranker-base（2026-08-15 完整），"
                    "确认加载成功后置 True；未启用时检索走 BM25+向量+RRF 三路融合"
    )

    # 查询重写配置
    query_rewriting_enabled: bool = Field(
        default=True,
        description="检索链路是否启用查询重写（v1.4 起由 dispatch 节点读取并真正接线）"
    )
    query_rewriting_use_llm: bool = Field(
        default=False,
        description="查询重写接线时是否启用 LLM 改写候选（默认关；完整版 LLM 改写见 v1.6）"
    )

    # Planner配置（v1.4：复杂问题的子方面大纲，只影响生成结构）
    planner_enabled: bool = Field(
        default=True,
        description="复杂问题是否启用 Planner 大纲分解（complex 或 ≥2 专家时触发）；关闭则完全跳过 plan 节点"
    )

    # RRF融合配置
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF融合算法参数k"
    )

    # 辩论引擎配置（P1优化：上下文瘦身与辩论降级）
    debate_enabled: bool = Field(
        default=True,
        description="辩论总开关，关闭后所有问题直接走普通融合（降级）"
    )
    debate_max_rounds: int = Field(
        default=3,
        ge=1,
        le=10,
        description="辩论最大轮次，超过此轮次提前结束"
    )
    collaboration_max_messages: int = Field(
        default=3,
        ge=1,
        le=10,
        description="v1.8 动态协作的最大可见消息数，限制额外模型调用"
    )
    debate_history_chars: int = Field(
        default=800,
        ge=50,
        description="辩论历史传给下一轮时每段截断字符数，防止上下文随轮次无限增长"
    )
    expert_answer_max_chars: int = Field(
        default=600,
        ge=50,
        description="专家单次回答/单轮发言最大字符数，超长自动截断"
    )

    # 热门问答缓存配置（P1优化：减少重复问题对LLM的重复调用）
    cache_enabled: bool = Field(
        default=True,
        description="热门问答缓存开关"
    )
    cache_max_entries: int = Field(
        default=100,
        ge=1,
        description="缓存最大条数，超过后按LRU淘汰最旧"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="缓存TTL（秒），过期后自动失效"
    )

    # 检索优化配置（P2优化：召回颗粒度 + 重排）
    craft_boost_enabled: bool = Field(
        default=True,
        description="技艺名精确匹配置顶开关：query 含技艺名时该技艺文档置顶 rank1"
    )
    craft_group_enabled: bool = Field(
        default=True,
        description="层级聚合开关：检索结果按「技艺→工序→细节」聚合成组返回"
    )
    craft_group_max_chars: int = Field(
        default=1500,
        ge=100,
        description="层级聚合时每组合并上下文的最大字符数，控制生成阶段上下文体积"
    )

    # ================= 音频转写与检索（v1.4） =================
    audio_transcribe_enabled: bool = Field(
        default=True,
        description="上传 media_type=audio 时是否自动入队转写（关闭则只存文件）"
    )
    audio_worker_enabled: bool = Field(
        default=True,
        description="lifespan 是否启动 asyncio 转写 worker（仅在 Redis 可达时真正消费）"
    )
    whisper_model_dir: str = Field(
        default="E:/huggingface/faster-whisper-small",
        description="faster-whisper CTranslate2 模型目录（本地加载，无需联网下载）"
    )
    whisper_device: str = Field(
        default="cpu",
        description="推理设备：cpu / cuda（本机 torch 为 CPU 版，默认 cpu）"
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="CPU 量化：int8 / int8_float32 / float32"
    )
    whisper_cpu_threads: int = Field(
        default=4,
        ge=1,
        description="Whisper CPU 线程数"
    )
    whisper_language: str = Field(
        default="zh",
        description="识别语言代码；None 则自动检测"
    )
    whisper_beam_size: int = Field(
        default=5,
        ge=1,
        description="beam search 宽度"
    )
    audio_chunk_max_chars: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="转写文本分块上限（入库 chroma 前切块）"
    )
    audio_chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="转写分块重叠字符"
    )
    audio_index_collection: str = Field(
        default="audio_transcripts",
        description="音频向量 collection 名（3-512 字符，[a-zA-Z0-9._-]）"
    )
    audio_index_path: str = Field(
        default="./data/audio_chroma",
        description="音频向量 PersistentClient 根目录（与文本向量隔离）"
    )
    audio_max_attempts: int = Field(
        default=3,
        ge=1,
        description="单条音频转写最大尝试次数，超过置 FAILED"
    )
    audio_stale_minutes: int = Field(
        default=15,
        ge=1,
        description="TRANSCRIBING 超过此时长视为陈旧，worker 启动 sweep 复位重入队"
    )

    # ================= Redis 缓存与任务队列（v1.4） =================
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis 连接串（缓存 + 转写任务队列共用）"
    )
    cache_backend: str = Field(
        default="auto",
        description="热门问答缓存后端：auto(Redis 可达用 Redis，否则进程内 LRU) / redis / memory"
    )
    redis_cache_prefix: str = Field(
        default="qa:v1",
        description="问答缓存 Redis key 前缀"
    )
    audio_queue_key: str = Field(
        default="heritagemind:audio:transcribe",
        description="音频转写任务队列 Redis key"
    )

    @field_validator("deepseek_api_key", mode="before")
    @classmethod
    def get_api_key_from_env(cls, v: str) -> str:
        """从环境变量读取API Key"""
        if not v:
            env_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not env_key:
                # 尝试从SECRET.md读取（如果存在）
                secret_path = os.path.join(os.path.dirname(__file__), "..", "SECRET.md")
                if os.path.exists(secret_path):
                    try:
                        with open(secret_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            for line in content.split("\n"):
                                if line.startswith("DEEPSEEK_API_KEY"):
                                    return line.split("=", 1)[1].strip()
                    except Exception:
                        pass
                return ""
        return v

    class Config:
        """Pydantic配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def validate_api_key() -> bool:
    """验证API Key是否配置"""
    return bool(settings.deepseek_api_key)


def get_retriever_config() -> dict:
    """获取检索器配置"""
    return {
        "top_k": settings.top_k,
        "similarity_threshold": settings.similarity_threshold,
    }


def get_llm_config() -> dict:
    """获取LLM配置"""
    return {
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
    }
