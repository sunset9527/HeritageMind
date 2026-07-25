"""
LLM工厂 - 统一创建ChatOpenAI实例，集成Langfuse追踪

项目中所有LLM实例化都应通过此工厂，
避免分散的ChatOpenAI构造，同时统一注入Langfuse callback。

支持请求级覆盖：API端点可设置 _request_override dict，
让单次请求使用用户自定义的 api_key / base_url / model。
"""

import logging
from typing import Optional, List, Any, Dict
from threading import local
from langchain_openai import ChatOpenAI

# 线程本地存储，用于请求级 LLM 配置覆盖（api_key / base_url / model）
_thread_local = local()

from config import settings, get_llm_config

logger = logging.getLogger(__name__)

# 单例Langfuse CallbackHandler（全局复用）
_langfuse_handler: Optional[Any] = None


def set_request_override(api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
    """设置当前请求的 LLM 配置覆盖（线程安全）"""
    _thread_local.llm_override = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def clear_request_override():
    """清除当前请求的 LLM 配置覆盖"""
    _thread_local.llm_override = None


def _get_request_override() -> Optional[Dict[str, Optional[str]]]:
    """获取当前请求的 LLM 配置覆盖"""
    return getattr(_thread_local, "llm_override", None)


def _get_langfuse_handler() -> Optional[Any]:
    """
    获取Langfuse CallbackHandler单例。

    仅在settings.langfuse_enabled=True时初始化。
    初始化失败不阻塞业务——仅记录警告。
    """
    global _langfuse_handler

    if not settings.langfuse_enabled:
        return None

    if _langfuse_handler is not None:
        return _langfuse_handler

    try:
        from langfuse.langchain import CallbackHandler
        _langfuse_handler = CallbackHandler()
        logger.info("Langfuse CallbackHandler 初始化成功")
        return _langfuse_handler
    except ImportError:
        logger.warning("langfuse 包未安装，LLM追踪已禁用")
        return None
    except Exception as e:
        logger.warning(f"Langfuse初始化失败（不影响业务）: {e}")
        return None


def create_llm(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    extra_callbacks: Optional[List[Any]] = None,
) -> ChatOpenAI:
    """
    创建ChatOpenAI实例（统一工厂）。

    自动：
    - 从config读取默认temperature/max_tokens/model
    - 如果启用了Langfuse，注入CallbackHandler进行LLM调用追踪
    - 支持用户自定义 api_key / base_url / model（从 HTTP Header 传入）

    Args:
        temperature: 覆盖默认temperature
        max_tokens: 覆盖默认max_tokens
        model: 覆盖默认模型名（用户可通过 X-Model header 传入）
        api_key: 覆盖默认 API Key（用户可通过 X-API-Key header 传入）
        base_url: 覆盖默认 Base URL（用户可通过 X-API-Base header 传入）
        extra_callbacks: 额外的callback列表

    Returns:
        ChatOpenAI: 配置好的LLM实例
    """
    llm_config = get_llm_config()

    # 组装callback列表
    callbacks: List[Any] = extra_callbacks or []
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        callbacks.append(langfuse_handler)

    # 请求级覆盖（用户通过 X-Model / X-API-Key header 传入）
    override = _get_request_override()

    # 优先级：显式参数 > 请求级覆盖 > 服务器默认值
    kwargs = {
        "model": model or (override.get("model") if override else None) or settings.deepseek_model,
        "base_url": base_url or (override.get("base_url") if override else None) or settings.deepseek_base_url,
        "api_key": api_key or (override.get("api_key") if override else None) or settings.deepseek_api_key,
        "temperature": temperature if temperature is not None else llm_config["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else llm_config["max_tokens"],
        "request_timeout": 30,
        "max_retries": 0,
    }

    if callbacks:
        kwargs["callbacks"] = callbacks

    return ChatOpenAI(**kwargs)
