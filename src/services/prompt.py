"""Prompt 模板管理服务"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from src.models.prompt import Prompt
from src.schemas.prompt import PromptCreate, PromptUpdate

logger = logging.getLogger(__name__)


def create_prompt(db: Session, data: PromptCreate) -> Prompt:
    prompt = Prompt(**data.model_dump())
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def get_prompt(db: Session, prompt_id: int) -> Optional[Prompt]:
    return db.get(Prompt, prompt_id)


def get_prompt_by_name(db: Session, name: str) -> Optional[Prompt]:
    return db.scalar(select(Prompt).where(Prompt.name == name))


def list_prompts(db: Session, limit: int = 50, offset: int = 0):
    total = db.scalar(select(func.count(Prompt.id)))
    items = db.scalars(
        select(Prompt).order_by(Prompt.updated_at.desc()).offset(offset).limit(limit)
    ).all()
    return items, total or 0


def update_prompt(db: Session, prompt_id: int, data: PromptUpdate) -> Optional[Prompt]:
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        return None
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(prompt, key, value)
    prompt.version += 1
    db.commit()
    db.refresh(prompt)
    return prompt


def delete_prompt(db: Session, prompt_id: int) -> bool:
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        return False
    db.delete(prompt)
    db.commit()
    return True


def get_prompt_system_text(db: Session, name: str) -> Optional[str]:
    """获取 Prompt 的 system_prompt 文本（供 Agent 调用时热加载）"""
    prompt = get_prompt_by_name(db, name)
    return prompt.system_prompt if prompt else None
