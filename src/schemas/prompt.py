"""Prompt 请求/响应模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    system_prompt: str = Field(..., min_length=1)


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None


class PromptResponse(BaseModel):
    id: int
    name: str
    description: str
    system_prompt: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    items: list[PromptResponse]
    total: int
