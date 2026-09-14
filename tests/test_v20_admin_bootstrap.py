from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.user import User


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
