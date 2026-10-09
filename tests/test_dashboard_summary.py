"""首页统计必须只计入后台已发布的当前内容。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.knowledge import KnowledgeDocument
from src.models.platform import CraftEntry, SourceEvidence


def make_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_dashboard_summary_only_counts_published_current_and_traceable_content():
    from src.services.dashboard_summary import get_dashboard_summary

    db = make_db()
    traceable = CraftEntry(name="可追溯技艺", slug="traceable", status="published")
    untraceable = CraftEntry(name="无来源技艺", slug="untraceable", status="published")
    draft = CraftEntry(name="草稿技艺", slug="draft", status="draft")
    db.add_all([traceable, untraceable, draft])
    db.flush()
    db.add(SourceEvidence(
        subject_type="craft", subject_id=traceable.id,
        source_url="https://example.com/source", source_name="示例来源", evidence_text="可核查证据",
    ))
    db.add_all([
        KnowledgeDocument(craft_entry_id=traceable.id, document_key="current", title="当前资料", content="正文", content_sha256="a" * 64, version=1, status="published", is_current=True, source_name="来源", source_url="https://example.com/current", accessed_at="2026-10-04"),
        KnowledgeDocument(craft_entry_id=traceable.id, document_key="old", title="历史资料", content="正文", content_sha256="b" * 64, version=1, status="published", is_current=False, source_name="来源", source_url="https://example.com/old", accessed_at="2026-10-04"),
        KnowledgeDocument(craft_entry_id=draft.id, document_key="draft", title="草稿资料", content="正文", content_sha256="c" * 64, version=1, status="draft", is_current=True, source_name="来源", source_url="https://example.com/draft", accessed_at="2026-10-04"),
    ])
    db.commit()

    assert get_dashboard_summary(db) == {
        "published_crafts": 2,
        "published_documents": 1,
        "traceable_crafts": 1,
    }
