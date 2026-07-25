"""
聊天历史相关 Pydantic Schema
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    """聊天历史列表项（摘要）"""
    id: int
    question: str = Field(..., description="用户问题（截取前100字）")
    answer_preview: str = Field(..., description="回答摘要（截取前100字）")
    user_profile: str = Field(..., description="用户画像")
    agents_used: Optional[List[str]] = Field(default=None, description="参与的Agent")
    has_gaps: bool = Field(default=False, description="是否存在知识缺口")
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryListResponse(BaseModel):
    """聊天历史列表响应"""
    items: List[ChatHistoryItem] = Field(default_factory=list)
    total: int = Field(default=0, description="总记录数")


class ChatDetailResponse(BaseModel):
    """单条聊天详情响应"""
    id: int
    question: str
    answer: str
    user_profile: str
    agents_used: Optional[Any] = Field(default=None, description="参与的Agent详情")
    has_gaps: bool
    created_at: datetime

    class Config:
        from_attributes = True
