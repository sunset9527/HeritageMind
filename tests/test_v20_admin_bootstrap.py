from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.user import User


def test_bootstrap_admin_uses_the_admin_password_policy():
    import pytest

    from src.services.admin_bootstrap import bootstrap_admin

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    with pytest.raises(ValueError, match="管理员密码至少需要 12 位"):
        bootstrap_admin(db, username="operator", email="operator@example.com", password="short-pass")

    with pytest.raises(ValueError, match="过于相似"):
        bootstrap_admin(db, username="operator", email="operator@example.com", password="operator-2026")


def test_bootstrap_admin_creates_and_reuses_a_single_admin_account():
    from src.services.admin_bootstrap import bootstrap_admin

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    created = bootstrap_admin(db, username="operator", email="operator@example.com", password="safe-password")
    again = bootstrap_admin(db, username="operator", email="operator@example.com", password="another-password")

    assert created.created is True
    assert again.created is False
    assert db.query(User).filter_by(username="operator", role="admin").count() == 1
