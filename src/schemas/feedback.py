"""Request/response contracts for answer feedback."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    chat_id: int = Field(gt=0)
    sentiment: Optional[Literal["up", "down"]] = None
    comment: Optional[str] = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    chat_id: int
    sentiment: Optional[Literal["up", "down"]] = None
    comment: Optional[str] = None
