"""本地非遗知识图谱查询 Agent。"""

from typing import Any, Dict, List

from src.graph.heritage_graph import HeritageKnowledgeGraph


class GraphAgent:
    """封装工作流对只读本地知识图谱的查询职责。"""

    def __init__(self, graph: HeritageKnowledgeGraph):
        self.graph = graph

    def research(self, question: str, key_entities: List[str]) -> Dict[str, Any]:
        """返回与识别实体直接相连的本地图谱证据。"""
        evidence = []
        seen_edges = set()
        for entity in key_entities:
            entity_text = str(entity).strip()
            if not entity_text:
                continue
            for node_id, attrs in self.graph.graph.nodes(data=True):
                node_name = str(attrs.get("name", node_id))
                if (
                    entity_text != node_id
                    and entity_text != node_name
                    and entity_text not in node_id
                    and entity_text not in node_name
                ):
                    continue
                for neighbor in self.graph.get_neighbors(node_id):
                    target = neighbor["node"]
                    relation_code = neighbor["relation"]
                    edge_key = (node_id, target["id"], relation_code)
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    relation = self.graph.EDGE_TYPES.get(relation_code, relation_code)
                    evidence.append({
                        "source": "local_knowledge_graph",
                        "source_node": self.graph.get_node(node_id),
                        "target": target,
                        "relation": relation,
                        "depth": 1,
                        "title": f"{node_name} —{relation}→ {target['name']}",
                    })

        return {
            "success": bool(evidence),
            "evidence": evidence,
            "reason": "" if evidence else "本地知识图谱未命中相关实体关系",
        }
