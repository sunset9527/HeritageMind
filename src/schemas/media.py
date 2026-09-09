"""多媒体文档请求/响应模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MediaResponse(BaseModel):
    id: int
    craft_name: str
    media_type: str
    filename: str
    original_name: str
    mime_type: str
    size: int
    title: str
    status: str = "draft"
    created_at: datetime
    url: str = ""
    # v1.4：音频专有，可选向后兼容
    transcript_status: Optional[str] = None
    transcript_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int


class MediaUpdateStatus(BaseModel):
    status: str = Field(..., pattern="^(draft|reviewed|published)$")
