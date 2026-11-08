"""One-time, explicit administration account bootstrap service."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.user import User
from src.services.auth import hash_password
from src.services.password_policy import PasswordPolicyError, validate_password


@dataclass(frozen=True)
class BootstrapResult:
    user: User
    created: bool


def bootstrap_admin(db: Session, *, username: str, email: str, password: str) -> BootstrapResult:
    username, email = username.strip(), email.strip().lower()
    if not username or not email:
        raise ValueError("username and email are required")
    try:
        validate_password(password, username=username, email=email, is_admin=True)
    except PasswordPolicyError as exc:
        raise ValueError(exc.public_message) from exc
    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing is not None:
        if existing.username != username or existing.email != email:
            raise ValueError("username or email is already used by another account")
        if existing.role != "admin":
            existing.role = "admin"
            db.commit()
        return BootstrapResult(user=existing, created=False)
    user = User(username=username, email=email, password_hash=hash_password(password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return BootstrapResult(user=user, created=True)
