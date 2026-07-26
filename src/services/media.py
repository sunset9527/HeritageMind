"""多媒体文件存储服务 — 本地文件系统（可切换 MinIO）"""
import os
import uuid
import logging
from typing import Optional, List, BinaryIO
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from config import settings
from src.models.media import MediaDocument, MediaType

logger = logging.getLogger(__name__)

# 存储根目录
STORAGE_ROOT = Path(settings.crafts_doc_path).parent / "media"


def _get_storage_path(media_type: str) -> Path:
    p = STORAGE_ROOT / media_type
    p.mkdir(parents=True, exist_ok=True)
    return p


def _generate_filename(original_name: str) -> str:
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else ""
    return f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex


def upload_media(
    db: Session,
    file: BinaryIO,
    original_name: str,
    mime_type: str,
    craft_name: str,
    media_type: str,
    title: str = "",
) -> MediaDocument:
    """上传媒体文件"""
    # 保存到本地
    filename = _generate_filename(original_name)
    storage_path = _get_storage_path(media_type)
    file_path = storage_path / filename

    content = file.read()
    file_size = len(content)
    file_path.write_bytes(content)

    # 写数据库
    doc = MediaDocument(
        craft_name=craft_name,
        media_type=MediaType(media_type),
        filename=filename,
        original_name=original_name,
        mime_type=mime_type,
        size=file_size,
        title=title or original_name,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"Media uploaded: {filename} ({file_size} bytes) -> {craft_name}")
    return doc


def list_media(
    db: Session,
    craft_name: Optional[str] = None,
    media_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple:
    """列出媒体文件"""
    stmt = select(MediaDocument)
    if craft_name:
        stmt = stmt.where(MediaDocument.craft_name == craft_name)
    if media_type:
        stmt = stmt.where(MediaDocument.media_type == MediaType(media_type))
    stmt = stmt.order_by(MediaDocument.created_at.desc()).offset(offset).limit(limit)

    total = db.scalar(select(func.count(MediaDocument.id)))
    items = db.scalars(stmt).all()
    return items, total or 0


def get_media(db: Session, media_id: int) -> Optional[MediaDocument]:
    return db.get(MediaDocument, media_id)


def delete_media(db: Session, media_id: int) -> bool:
    doc = db.get(MediaDocument, media_id)
    if not doc:
        return False
    # 删文件
    file_path = _get_storage_path(doc.media_type.value) / doc.filename
    if file_path.exists():
        file_path.unlink()
    db.delete(doc)
    db.commit()
    return True


def get_media_url(media: MediaDocument) -> str:
    """获取媒体访问 URL"""
    return f"/media/file/{media.media_type.value}/{media.filename}"
