"""v1.6 Graph Agent 的离线行为契约。"""

import src.agents as agents
from src.graph.heritage_graph import HeritageKnowledgeGraph


def test_graph_agent_is_available_as_a_first_class_agent():
    assert getattr(agents, "GraphAgent", None) is not None


def test_graph_agent_returns_local_relation_evidence_for_matched_entity():
    graph = HeritageKnowledgeGraph()
    graph.add_node("jingtailan", "craft", name="景泰蓝")
    graph.add_node("beijing", "region", name="北京")
    graph.add_edge("jingtailan", "beijing", "originates_from")

    result = agents.GraphAgent(graph).research("景泰蓝发源于哪里？", ["景泰蓝"])

    assert result["success"] is True
    assert result["evidence"][0]["source"] == "local_knowledge_graph"
    assert result["evidence"][0]["relation"] == "发源于"
    assert result["evidence"][0]["target"]["name"] == "北京"


def test_graph_agent_matches_entity_substring_without_inventing_a_relation():
    graph = HeritageKnowledgeGraph()
    graph.add_node("jingtailan", "craft", name="景泰蓝")
    graph.add_node("beijing", "region", name="北京")
    graph.add_edge("jingtailan", "beijing", "originates_from")

    result = agents.GraphAgent(graph).research("景泰的产地是什么？", ["景泰"])

    assert result["success"] is True
    assert result["evidence"] == [
        {
            "source": "local_knowledge_graph",
            "source_node": {"id": "jingtailan", "name": "景泰蓝", "type": "craft", "properties": {}},
            "target": {"id": "beijing", "name": "北京", "type": "region", "properties": {}},
            "relation": "发源于",
            "depth": 1,
            "title": "景泰蓝 —发源于→ 北京",
        }
    ]
