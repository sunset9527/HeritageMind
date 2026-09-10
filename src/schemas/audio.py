"""音频转写/检索 API 模型（v1.4）"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptStatusResponse(BaseModel):
    """GET /media/{id}/transcript 轮询响应；无 sidecar 时 status='none'"""
    media_id: int
    status: str = Field(..., description="none/UPLOADED/TRANSCRIBING/INDEXED/FAILED")
    craft_name: str = ""
    attempts: int = 0
    language: Optional[str] = None
    duration_ms: Optional[int] = None
    chunk_count: int = 0
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AudioSearchHit(BaseModel):
    """按 media_id 聚合后的单条命中音频"""
    media_id: int
    craft_name: str
    title: str
    original_name: str
    url: str = ""
    snippet: str = ""            # 命中分块文本
    score: float = 0.0           # 1 - chroma cosine 距离（降级子串匹配时为 0）
    media_status: str = "draft"


class AudioSearchResponse(BaseModel):
    query: str
    top_k: int
    total: int
    results: List[AudioSearchHit]


class AudioTranscribeEnqueueResponse(BaseModel):
    """POST /media/{id}/transcribe 手动/重试触发"""
    media_id: int
    status: str
    enqueued: bool = Field(..., description="是否成功入队（Redis push 失败也置 True，靠 sweep 兜底）")
    detail: str = ""
