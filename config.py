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
    
    # 用户画像配置
    default_user_profile: str = Field(
        default="curious",
        description="默认用户画像：curious(好奇者)/learner(学习者)/researcher(研究者)"
    )
    
    # API服务配置
    api_host: str = Field(default="0.0.0.0", description="API服务主机")
    api_port: int = Field(default=8000, description="API服务端口")
    
    # Streamlit配置
    streamlit_port: int = Field(default=8501, description="Streamlit服务端口")
    
    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    # 传承人视角配置
    enable_narrative_mode: bool = Field(
        default=True,
        description="是否启用传承人视角叙事模式"
    )
    
    # Embedding配置
    embedding_model: str = Field(
        default="BAAI/bge-large-zh-v1.5",
        description="Embedding模型名称"
    )
    embedding_dimensions: int = Field(
        default=1024,
        description="嵌入向量维度"
    )
    
    # BM25配置
    bm25_enabled: bool = Field(
        default=True,
        description="是否启用BM25检索"
    )
    
    # Reranker配置
    reranker_model: str = Field(
        default="BAAI/bge-reranker-base",
        description="Cross-Encoder Reranker模型名称"
    )
    reranker_enabled: bool = Field(
        default=True,
        description="是否启用Reranker重排序"
    )
    
    # 查询重写配置
    query_rewriting_enabled: bool = Field(
        default=True,
        description="是否启用查询重写"
    )
    
    # RRF融合配置
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF融合算法参数k"
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
