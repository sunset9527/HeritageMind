from src.graph.heritage_graph import HeritageKnowledgeGraph


def test_sync_curated_sources_projects_each_published_document_to_its_craft():
    from src.services.graph_projection import sync_curated_source_nodes

    graph = HeritageKnowledgeGraph()
    assert graph.load_from_json()

    source_count = sync_curated_source_nodes(graph)

    assert source_count == 46
    source_id = "curated:source:jingtailan-ihchina-001"
    source = graph.get_node(source_id)
    assert source["type"] == "source"
    assert source["properties"]["source_url"] == "https://www.ihchina.cn/art/detail/id/14341.html"
    assert graph.graph.has_edge("jingtailan", source_id)
    assert graph.graph.edges["jingtailan", source_id]["relation"] == "has_source"
