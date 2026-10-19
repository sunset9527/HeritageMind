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
    status: Optional[str] = None,
) -> tuple:
    """列出媒体文件"""
    stmt = select(MediaDocument)
    if craft_name:
        stmt = stmt.where(MediaDocument.craft_name == craft_name)
    if media_type:
        stmt = stmt.where(MediaDocument.media_type == MediaType(media_type))
    if status:
        stmt = stmt.where(MediaDocument.status == status)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    stmt = stmt.order_by(MediaDocument.created_at.desc()).offset(offset).limit(limit)

    total = db.scalar(count_stmt)
    items = db.scalars(stmt).all()
    return items, total or 0


def get_media(
    db: Session,
    media_id: int,
    status: Optional[str] = None,
) -> Optional[MediaDocument]:
    stmt = select(MediaDocument).where(MediaDocument.id == media_id)
    if status:
        stmt = stmt.where(MediaDocument.status == status)
    return db.scalar(stmt)


def get_media_by_storage_key(
    db: Session,
    media_type: str,
    filename: str,
    status: Optional[str] = None,
) -> Optional[MediaDocument]:
    """按数据库记录解析媒体文件，避免公开接口绕过审核状态。"""
    try:
        normalized_type = MediaType(media_type)
    except ValueError:
        return None
    stmt = select(MediaDocument).where(
        MediaDocument.media_type == normalized_type,
        MediaDocument.filename == filename,
    )
    if status:
        stmt = stmt.where(MediaDocument.status == status)
    return db.scalar(stmt)


def list_published_media(
    db: Session,
    craft_name: Optional[str] = None,
    media_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple:
    """公开媒体列表：发布状态由服务层固定，调用者不能放宽。"""
    return list_media(
        db,
        craft_name=craft_name,
        media_type=media_type,
        limit=limit,
        offset=offset,
        status="published",
    )


def get_published_media(db: Session, media_id: int) -> Optional[MediaDocument]:
    """返回已发布媒体；草稿、审核中和不存在记录均视为不可见。"""
    return get_media(db, media_id, status="published")


def get_published_media_by_storage_name(
    db: Session,
    media_type: str,
    filename: str,
) -> Optional[MediaDocument]:
    """按存储名返回已发布媒体，供公开文件路由使用。"""
    return get_media_by_storage_key(
        db,
        media_type=media_type,
        filename=filename,
        status="published",
    )


def delete_media(db: Session, media_id: int) -> bool:
    doc = db.get(MediaDocument, media_id)
    if not doc:
        return False
    # 删文件
    file_path = _get_storage_path(doc.media_type.value) / doc.filename
    if file_path.exists():
        file_path.unlink()
    # v1.4：音频——删 sidecar 行 + chroma 向量（无 sidecar 的媒体跳过，避免图片删除也初始化音频向量库）
    _cleanup_audio_index(db, media_id)
    db.delete(doc)
    db.commit()
    return True


def _cleanup_audio_index(db: Session, media_id: int) -> None:
    """删 AudioTranscript sidecar 行并清理对应 chroma 向量；失败仅 warning，不阻断主记录删除。"""
    from sqlalchemy import delete

    from src.models.audio_transcript import AudioTranscript
    from src.services.audio_transcript import get_transcript

    has_sidecar = get_transcript(db, media_id) is not None
    if has_sidecar:
        db.execute(delete(AudioTranscript).where(AudioTranscript.media_id == media_id))
        try:
            # 曾有转写索引才打开音频向量库（get_audio_store 懒建 PersistentClient）
            from src.retrieval.audio_store import get_audio_store
            get_audio_store().delete_media(media_id)
        except Exception as e:
            logger.warning(f"清理音频向量失败 media_id={media_id}: {e}")


def get_media_url(media: MediaDocument) -> str:
    """获取媒体访问 URL"""
    return f"/media/file/{media.media_type.value}/{media.filename}"
