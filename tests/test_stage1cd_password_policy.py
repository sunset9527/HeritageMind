import pytest


@pytest.mark.parametrize(
    ("password", "username", "email"),
    [
        ("short-pass", "reader", "reader@example.com"),
        ("a" * 128, "reader", "reader@example.com"),
        ("two words are allowed", "reader", "reader@example.com"),
    ],
)
def test_regular_password_policy_accepts_long_memorable_passwords(password, username, email):
    from src.services.password_policy import validate_password

    validate_password(password, username=username, email=email, is_admin=False)


@pytest.mark.parametrize(
    ("password", "username", "email", "is_admin", "code"),
    [
        ("123456789", "reader", "reader@example.com", False, "password_too_short"),
        ("12345678901", "operator", "operator@example.com", True, "password_too_short"),
        ("a" * 129, "reader", "reader@example.com", False, "password_too_long"),
        ("          ", "reader", "reader@example.com", False, "password_blank"),
        ("password123", "reader", "reader@example.com", False, "password_too_weak"),
        ("Reader-2026", "reader", "reader@example.com", False, "password_too_similar"),
        ("reader2026", "someone", "reader@example.com", False, "password_too_similar"),
    ],
)
def test_password_policy_rejects_unsafe_passwords(password, username, email, is_admin, code):
    from src.services.password_policy import PasswordPolicyError, validate_password

    with pytest.raises(PasswordPolicyError) as raised:
        validate_password(password, username=username, email=email, is_admin=is_admin)

    assert raised.value.code == code
    assert password not in str(raised.value)


def test_create_user_applies_new_policy_but_authentication_keeps_legacy_passwords():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from src.database import Base
    from src.models.user import User
    from src.services.auth import authenticate_user, create_user, hash_password

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    rejected, error = create_user(db, "new-reader", "new-reader@example.com", "123456")
    assert rejected is None
    assert error == "密码至少需要 10 位"

    legacy = User(
        username="legacy",
        email="legacy@example.com",
        password_hash=hash_password("oldpass"),
        role="user",
    )
    db.add(legacy)
    db.commit()

    authenticated, error = authenticate_user(db, "legacy", "oldpass")
    assert authenticated is not None
    assert error is None

    missing, missing_error = authenticate_user(db, "missing", "wrong")
    wrong_password, wrong_password_error = authenticate_user(db, "legacy", "wrong")
    assert missing is None
    assert wrong_password is None
    assert missing_error == wrong_password_error == "用户名或密码错误"
