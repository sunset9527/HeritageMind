"""多媒体文件存储服务 — 本地文件系统（可切换 MinIO）"""
import json
import os
import logging
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from config import settings
from src.models.media import MediaDocument, MediaType
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.models.platform import AuditLog
from src.services.upload_security import StagedUpload, resolve_under

logger = logging.getLogger(__name__)

# 存储根目录
STORAGE_ROOT = Path(settings.media_storage_path)


def _get_storage_path(media_type: str) -> Path:
    p = STORAGE_ROOT / media_type
    p.mkdir(parents=True, exist_ok=True)
    return p


def persist_staged_media(
    db: Session,
    *,
    staged: StagedUpload,
    storage_root: Path | str = STORAGE_ROOT,
    craft_id: str,
    craft_name: str,
    media_type: str,
    title: str = "",
    uploaded_by_user_id: int | None = None,
) -> MediaDocument:
    """原子发布已验证媒体，并在同一事务写媒体、sidecar 与审计记录。

    文件先以 ``.part`` 存在。数据库 flush 成功后才原子改名；最终 commit
    失败则删除已发布文件，避免数据库与文件系统任一侧出现孤儿。
    """
    normalized_type = MediaType(media_type)
    target_directory = Path(storage_root) / normalized_type.value
    target_directory.mkdir(parents=True, exist_ok=True)
    final_path = resolve_under(target_directory, staged.storage_name)
    published = False

    doc = MediaDocument(
        craft_id=craft_id,
        craft_name=craft_name,
        media_type=normalized_type,
        filename=staged.storage_name,
        original_name=staged.original_name,
        mime_type=staged.mime_type,
        size=staged.size_bytes,
        content_sha256=staged.content_sha256,
        uploaded_by_user_id=uploaded_by_user_id,
        title=title or staged.original_name,
        status="draft",
    )
    try:
        db.add(doc)
        db.flush()
        if normalized_type is MediaType.AUDIO:
            db.add(
                AudioTranscript(
                    media_id=doc.id,
                    craft_name=craft_name,
                    status=AudioTranscriptStatus.UPLOADED.value,
                    attempts=0,
                )
            )
        db.add(
            AuditLog(
                actor_user_id=uploaded_by_user_id,
                action="media.uploaded",
                subject_type="media",
                subject_id=doc.id,
                detail=json.dumps(
                    {
                        "craft_id": craft_id,
                        "media_type": normalized_type.value,
                        "size_bytes": staged.size_bytes,
                        "sha256": staged.content_sha256,
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.flush()
        os.replace(staged.temp_path, final_path)
        published = True
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        try:
            (final_path if published else staged.temp_path).unlink(missing_ok=True)
        except OSError:
            logger.exception("清理失败的媒体上传文件时出错")
        raise

    logger.info(
        "Media uploaded: %s (%s bytes) -> %s",
        staged.storage_name,
        staged.size_bytes,
        craft_id,
    )
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
