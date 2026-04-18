"""
非遗知识图谱 - 基于NetworkX的知识图谱实现
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import networkx as nx

from config import settings

logger = logging.getLogger(__name__)


class HeritageKnowledgeGraph:
    """
    非遗知识图谱
    
    基于NetworkX实现，支持：
    - 节点类型：技艺(craft)/材料(material)/工具(tool)/传承人(inheritor)/地域(region)/朝代(dynasty)
    - 边类型：使用材料/使用工具/传承人掌握/发源于/起源于
    - 图查询：技艺→材料、技艺→工具、传承人→技艺 等多跳查询
    """
    
    # 节点类型定义
    NODE_TYPES = {
        "craft": "技艺",
        "material": "材料",
        "tool": "工具",
        "inheritor": "传承人",
        "region": "地域",
        "dynasty": "朝代"
    }
    
    # 边类型定义
    EDGE_TYPES = {
        "uses_material": "使用材料",
        "uses_tool": "使用工具",
        "mastered_by": "传承人掌握",
        "originates_from": "发源于",
        "originated_in": "起源于",
        "related_to": "与...相关",
        "influenced_by": "受...影响"
    }
    
    def __init__(self):
        """初始化知识图谱"""
        self.graph = nx.DiGraph()
        self._initialized = False
    
    def load_from_json(self, file_path: Optional[str] = None) -> bool:
        """
        从JSON文件加载知识图谱
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            bool: 是否加载成功
        """
        if file_path is None:
            file_path = settings.heritage_graph_path
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 加载节点
            self.graph.clear()
            for node in data.get("nodes", []):
                self.graph.add_node(
                    node["id"],
                    name=node.get("name", node["id"]),
                    type=node.get("type", "unknown"),
                    properties=node.get("properties", {})
                )
            
            # 加载边
            for edge in data.get("edges", []):
                self.graph.add_edge(
                    edge["source"],
                    edge["target"],
                    relation=edge.get("relation", "related_to"),
                    properties=edge.get("properties", {})
                )
            
            self._initialized = True
            logger.info(f"知识图谱加载成功：{len(self.graph.nodes)}节点，{len(self.graph.edges)}边")
            return True
            
        except FileNotFoundError:
            logger.warning(f"图谱文件不存在：{file_path}")
            return False
        except Exception as e:
            logger.error(f"图谱加载失败: {e}")
            return False
    
    def save_to_json(self, file_path: Optional[str] = None) -> bool:
        """
        保存知识图谱到JSON文件
        
        Args:
            file_path: 保存路径
        
        Returns:
            bool: 是否保存成功
        """
        if file_path is None:
            file_path = settings.heritage_graph_path
        
        try:
            nodes = []
            for node_id, attrs in self.graph.nodes(data=True):
                nodes.append({
                    "id": node_id,
                    "name": attrs.get("name", node_id),
                    "type": attrs.get("type", "unknown"),
                    "properties": attrs.get("properties", {})
                })
            
            edges = []
            for source, target, attrs in self.graph.edges(data=True):
                edges.append({
                    "source": source,
                    "target": target,
                    "relation": attrs.get("relation", "related_to"),
                    "properties": attrs.get("properties", {})
                })
            
            data = {
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "node_count": len(nodes),
                    "edge_count": len(edges)
                }
            }
            
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识图谱已保存：{file_path}")
            return True
            
        except Exception as e:
            logger.error(f"图谱保存失败: {e}")
            return False
    
    def add_node(
        self,
        node_id: str,
        node_type: str,
        name: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        添加节点
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            name: 节点名称
            properties: 节点属性
        """
        if name is None:
            name = node_id
        
        if properties is None:
            properties = {}
        
        self.graph.add_node(
            node_id,
            name=name,
            type=node_type,
            properties=properties
        )
    
    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        添加边
        
        Args:
            source: 源节点ID
            target: 目标节点ID
            relation: 关系类型
            properties: 边属性
        """
        if properties is None:
            properties = {}
        
        self.graph.add_edge(
            source,
            target,
            relation=relation,
            properties=properties
        )
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        获取节点信息
        
        Args:
            node_id: 节点ID
        
        Returns:
            节点信息字典
        """
        if node_id not in self.graph:
            return None
        
        attrs = self.graph.nodes[node_id]
        return {
            "id": node_id,
            "name": attrs.get("name", node_id),
            "type": attrs.get("type", "unknown"),
            "properties": attrs.get("properties", {})
        }
    
    def get_neighbors(
        self,
        node_id: str,
        relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取节点的邻居
        
        Args:
            node_id: 节点ID
            relation: 可选的关系类型过滤
        
        Returns:
            邻居节点列表
        """
        if node_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            if relation is None or edge_data.get("relation") == relation:
                neighbors.append({
                    "node": self.get_node(neighbor),
                    "relation": edge_data.get("relation", "related_to")
                })
        
        return neighbors
    
    def query_craft_materials(self, craft_name: str) -> List[str]:
        """
        查询某技艺使用的所有材料
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            材料名称列表
        """
        neighbors = self.get_neighbors(craft_name, "uses_material")
        return [n["node"]["name"] for n in neighbors]
    
    def query_craft_tools(self, craft_name: str) -> List[str]:
        """
        查询某技艺使用的所有工具
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            工具名称列表
        """
        neighbors = self.get_neighbors(craft_name, "uses_tool")
        return [n["node"]["name"] for n in neighbors]
    
    def query_inheritor_crafts(self, inheritor_name: str) -> List[str]:
        """
        查询某传承人掌握的所有技艺
        
        Args:
            inheritor_name: 传承人名称
        
        Returns:
            技艺名称列表
        """
        neighbors = self.get_neighbors(inheritor_name, "mastered_by")
        return [n["node"]["name"] for n in neighbors]
    
    def query_craft_inheritors(self, craft_name: str) -> List[str]:
        """
        查询掌握某技艺的所有传承人
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            传承人名称列表
        """
        # 反向查询
        neighbors = []
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == "inheritor":
                if self.graph.has_edge(node_id, craft_name):
                    edge_data = self.graph.get_edge_data(node_id, craft_name)
                    if edge_data.get("relation") == "mastered_by":
                        neighbors.append(attrs.get("name", node_id))
        return neighbors
    
    def query_craft_region(self, craft_name: str) -> List[str]:
        """
        查询某技艺的起源/分布地域
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            地域名称列表
        """
        neighbors = self.get_neighbors(craft_name, "originates_from")
        return [n["node"]["name"] for n in neighbors]
    
    def query_craft_history(self, craft_name: str) -> List[Tuple[str, str]]:
        """
        查询某技艺的历史朝代
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            (朝代, 关系描述)列表
        """
        neighbors = self.get_neighbors(craft_name, "originated_in")
        return [(n["node"]["name"], n["relation"]) for n in neighbors]
    
    def find_path(
        self,
        source: str,
        target: str,
        max_length: int = 3
    ) -> List[List[str]]:
        """
        查找两个节点之间的路径
        
        Args:
            source: 源节点
            target: 目标节点
            max_length: 最大路径长度
        
        Returns:
            路径列表
        """
        try:
            paths = list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_subgraph(
        self,
        center_node: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        获取以某节点为中心的子图
        
        Args:
            center_node: 中心节点
            depth: 扩展深度
        
        Returns:
            子图数据
        """
        if center_node not in self.graph:
            return {}
        
        # BFS获取相关节点
        nodes = {center_node}
        current_level = {center_node}
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                next_level.update(self.graph.neighbors(node))
            nodes.update(next_level)
            current_level = next_level
        
        # 构建子图
        subgraph = self.graph.subgraph(nodes)
        
        return {
            "nodes": [
                {
                    "id": n,
                    "name": self.graph.nodes[n].get("name", n),
                    "type": self.graph.nodes[n].get("type", "unknown")
                }
                for n in subgraph.nodes()
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "relation": self.graph.edges[u, v].get("relation", "related_to")
                }
                for u, v in subgraph.edges()
            ]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Returns:
            统计信息字典
        """
        node_types = {}
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        edge_types = {}
        for u, v, attrs in self.graph.edges(data=True):
            relation = attrs.get("relation", "related_to")
            edge_types[relation] = edge_types.get(relation, 0) + 1
        
        return {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "is_directed": self.graph.is_directed()
        }
    
    def search_nodes(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索节点
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的节点列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        for node_id, attrs in self.graph.nodes(data=True):
            name = attrs.get("name", node_id).lower()
            if keyword_lower in name or keyword_lower in node_id.lower():
                results.append({
                    "id": node_id,
                    "name": attrs.get("name", node_id),
                    "type": attrs.get("type", "unknown")
                })
        
        return results
    
    def get_related_entities(
        self,
        entity_name: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取与某实体相关的所有实体
        
        Args:
            entity_name: 实体名称
            relation_type: 关系类型过滤
        
        Returns:
            相关实体列表
        """
        # 找到实体节点
        entity_node = None
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("name") == entity_name or node_id == entity_name:
                entity_node = node_id
                break
        
        if entity_node is None:
            return []
        
        return self.get_neighbors(entity_node, relation_type)
    
    def to_networkx(self) -> nx.DiGraph:
        """获取NetworkX图对象"""
        return self.graph
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized or len(self.graph.nodes) > 0
