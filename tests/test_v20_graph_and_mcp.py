"""v2.0 graph merge and external-tool safety contracts."""

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.models.user import User


def test_only_approved_candidate_can_change_the_graph():
    from src.models.platform import GraphChangeCandidate  # noqa: F401
    from src.services.graph_curation import merge_approved_candidate
    from src.services.platform_content import create_graph_candidate

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, username="admin", email="admin@example.com", password_hash="hash", role="admin"))
    db.commit()
    candidate = create_graph_candidate(
        db,
        source_entity="Example Inheritor", source_type="inheritor", relation="mastered_by",
        target_entity="Test Craft", target_type="craft", evidence_text="A cited relationship.",
        source_url="https://www.ihchina.cn/example",
    )
    graph = HeritageKnowledgeGraph()

    try:
        merge_approved_candidate(db, candidate_id=candidate.id, graph=graph)
        assert False, "pending candidate must not mutate the graph"
    except ValueError as error:
        assert "approved" in str(error)

    candidate.status = "approved"
    merge_approved_candidate(db, candidate_id=candidate.id, graph=graph)
    assert graph.get_neighbors("Example Inheritor")[0]["node"]["name"] == "Test Craft"


def test_unconfigured_web_tool_is_explicit_and_does_not_make_a_network_call():
    from src.services.mcp_tools import search_web

    result = asyncio.run(search_web("test query", endpoint="", api_key=""))

    assert result.status == "not_configured"
    assert result.items == []


def test_wikipedia_tool_normalizes_a_public_api_response_without_leaking_transport_details():
    from src.services.mcp_tools import search_wikipedia

    class Response:
        status_code = 200

        def json(self):
            return {"pages": [{"title": "Cloisonne", "description": "craft", "thumbnail": {"url": "https://img"}}]}

    class Client:
        async def get(self, url, params):
            assert url.startswith("https://zh.wikipedia.org/")
            assert params["q"] == "cloisonne"
            return Response()

    result = asyncio.run(search_wikipedia("cloisonne", client=Client()))

    assert result.status == "ok"
    assert result.items == [{"title": "Cloisonne", "summary": "craft", "url": "https://zh.wikipedia.org/wiki/Cloisonne"}]
