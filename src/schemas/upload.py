"""上传草稿与后台任务的公开响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: int
    craft_id: str
    craft_name: str
    original_name: str
    extension: str
    mime_type: str
    size_bytes: int
    content_sha256: str
    char_count: int
    page_count: int
    ocr_page_count: int
    review_status: str
    processing_status: str
    attempts: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadListResponse(BaseModel):
    items: list[DocumentUploadResponse]
    total: int
    worker_status: str
