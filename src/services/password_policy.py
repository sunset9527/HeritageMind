"""Password checks for newly created or changed accounts.

Existing password hashes are deliberately not revalidated at login.  This lets
older accounts continue to sign in while all new credentials follow the safer
policy.
"""

from __future__ import annotations

import re


_WEAK_PASSWORDS = frozenset(
    {
        "1234567890",
        "123456789",
        "12345678",
        "password",
        "password123",
        "qwerty123",
        "qwertyuiop",
        "letmein",
        "admin123",
    }
)
_IDENTITY_RE = re.compile(r"[^a-z0-9]+")


class PasswordPolicyError(ValueError):
    """Stable, user-safe password-policy validation error."""

    def __init__(self, code: str, public_message: str):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


def _identity_token(value: str) -> str:
    return _IDENTITY_RE.sub("", value.casefold())


def _is_too_similar(password: str, username: str, email: str) -> bool:
    candidate = _identity_token(password)
    identities = (_identity_token(username), _identity_token(email.split("@", 1)[0]))
    return any(len(identity) >= 3 and (candidate == identity or candidate.startswith(identity)) for identity in identities)


def validate_password(password: str, *, username: str, email: str, is_admin: bool) -> None:
    """Validate a password without retaining or logging its value."""
    if not password.strip():
        raise PasswordPolicyError("password_blank", "密码不能只包含空白字符")
    if len(password) > 128:
        raise PasswordPolicyError("password_too_long", "密码不能超过 128 位")

    minimum = 12 if is_admin else 10
    if len(password) < minimum:
        role = "管理员" if is_admin else "密码"
        raise PasswordPolicyError("password_too_short", f"{role}密码至少需要 {minimum} 位" if is_admin else "密码至少需要 10 位")
    if password.casefold() in _WEAK_PASSWORDS:
        raise PasswordPolicyError("password_too_weak", "密码过于常见，请使用更难猜测的密码")
    if _is_too_similar(password, username, email):
        raise PasswordPolicyError("password_too_similar", "密码不能与用户名或邮箱过于相似")
