"""
测试非遗知识图谱
"""

import pytest
import json
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.heritage_graph import HeritageKnowledgeGraph


class TestHeritageKnowledgeGraph:
    """测试非遗知识图谱"""
    
    @pytest.fixture
    def graph(self):
        """创建知识图谱实例"""
        return HeritageKnowledgeGraph()
    
    @pytest.fixture
    def sample_data_path(self):
        """创建临时测试数据文件"""
        data = {
            "nodes": [
                {"id": "jingtailan", "name": "景泰蓝", "type": "craft", "properties": {}},
                {"id": "tongsi", "name": "铜丝", "type": "material", "properties": {}},
                {"id": "qian_meihua", "name": "钱美华", "type": "inheritor", "properties": {}}
            ],
            "edges": [
                {"source": "jingtailan", "target": "tongsi", "relation": "uses_material"},
                {"source": "qian_meihua", "target": "jingtailan", "relation": "mastered_by"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            return f.name
    
    def test_add_node(self, graph):
        """测试添加节点"""
        graph.add_node("test_node", "craft", "测试技艺", {"key": "value"})
        
        assert "test_node" in graph.graph.nodes()
        attrs = graph.graph.nodes["test_node"]
        assert attrs["name"] == "测试技艺"
        assert attrs["type"] == "craft"
    
    def test_add_edge(self, graph):
        """测试添加边"""
        graph.add_node("craft1", "craft")
        graph.add_node("material1", "material")
        graph.add_edge("craft1", "material1", "uses_material", {"note": "测试"})
        
        assert graph.graph.has_edge("craft1", "material1")
        edge_attrs = graph.graph.edges["craft1", "material1"]
        assert edge_attrs["relation"] == "uses_material"
    
    def test_get_node(self, graph):
        """测试获取节点"""
        graph.add_node("test_node", "craft", "测试技艺")
        
        result = graph.get_node("test_node")
        
        assert result is not None
        assert result["name"] == "测试技艺"
        assert result["type"] == "craft"
    
    def test_get_node_not_exists(self, graph):
        """测试获取不存在的节点"""
        result = graph.get_node("not_exists")
        assert result is None
    
    def test_get_neighbors(self, graph):
        """测试获取邻居节点"""
        graph.add_node("craft", "craft")
        graph.add_node("material1", "material")
        graph.add_node("material2", "material")
        graph.add_edge("craft", "material1", "uses_material")
        graph.add_edge("craft", "material2", "uses_material")
        
        neighbors = graph.get_neighbors("craft")
        
        assert len(neighbors) == 2
    
    def test_get_neighbors_with_relation(self, graph):
        """测试按关系类型获取邻居"""
        graph.add_node("craft", "craft")
        graph.add_node("material", "material")
        graph.add_node("tool", "tool")
        graph.add_edge("craft", "material", "uses_material")
        graph.add_edge("craft", "tool", "uses_tool")
        
        neighbors = graph.get_neighbors("craft", "uses_material")
        
        assert len(neighbors) == 1
        assert neighbors[0]["node"]["name"] == "material"
    
    def test_query_craft_materials(self, graph):
        """测试查询技艺使用的材料"""
        graph.add_node("jingtailan", "craft", "景泰蓝")
        graph.add_node("tongsi", "material", "铜丝")
        graph.add_node("flame_glaze", "material", "珐琅釉料")
        graph.add_edge("jingtailan", "tongsi", "uses_material")
        graph.add_edge("jingtailan", "flame_glaze", "uses_material")
        
        materials = graph.query_craft_materials("景泰蓝")
        
        assert len(materials) == 2
        assert "铜丝" in materials
        assert "珐琅釉料" in materials
    
    def test_query_craft_tools(self, graph):
        """测试查询技艺使用的工具"""
        graph.add_node("jingtailan", "craft", "景泰蓝")
        graph.add_node("cas_tool", "tool", "掐丝工具")
        graph.add_edge("jingtailan", "cas_tool", "uses_tool")
        
        tools = graph.query_craft_tools("景泰蓝")
        
        assert len(tools) == 1
        assert "掐丝工具" in tools
    
    def test_query_inheritor_crafts(self, graph):
        """测试查询传承人掌握的技艺"""
        graph.add_node("qian_meihua", "inheritor", "钱美华")
        graph.add_node("jingtailan", "craft", "景泰蓝")
        graph.add_edge("qian_meihua", "jingtailan", "mastered_by")
        
        crafts = graph.query_inheritor_crafts("钱美华")
        
        assert len(crafts) == 1
        assert "景泰蓝" in crafts
    
    def test_query_craft_inheritors(self, graph):
        """测试查询技艺的传承人"""
        graph.add_node("jingtailan", "craft", "景泰蓝")
        graph.add_node("qian_meihua", "inheritor", "钱美华")
        graph.add_node("zhang_luqi", "inheritor", "张禄祺")
        graph.add_edge("qian_meihua", "jingtailan", "mastered_by")
        graph.add_edge("zhang_luqi", "jingtailan", "mastered_by")
        
        inheritors = graph.query_craft_inheritors("景泰蓝")
        
        assert len(inheritors) == 2
    
    def test_save_and_load_json(self, graph, sample_data_path):
        """测试保存和加载JSON"""
        # 加载
        success = graph.load_from_json(sample_data_path)
        
        assert success is True
        assert len(graph.graph.nodes) == 3
        assert len(graph.graph.edges) == 2
    
    def test_save_json(self, graph):
        """测试保存图谱到JSON"""
        graph.add_node("test", "craft", "测试")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            success = graph.save_to_json(temp_path)
            
            assert success is True
            
            # 验证文件内容
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert "nodes" in data
            assert "edges" in data
            assert len(data["nodes"]) == 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_get_statistics(self, graph):
        """测试获取统计信息"""
        graph.add_node("craft1", "craft")
        graph.add_node("material1", "material")
        graph.add_node("inheritor1", "inheritor")
        graph.add_edge("craft1", "material1", "uses_material")
        
        stats = graph.get_statistics()
        
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 1
        assert "node_types" in stats
        assert "edge_types" in stats
    
    def test_search_nodes(self, graph):
        """测试搜索节点"""
        graph.add_node("jingtailan", "craft", "景泰蓝")
        graph.add_node("suxiu", "craft", "苏绣")
        graph.add_node("qian_meihua", "inheritor", "钱美华")
        
        results = graph.search_nodes("景泰")
        
        assert len(results) >= 1
        assert any(r["name"] == "景泰蓝" for r in results)
    
    def test_get_subgraph(self, graph):
        """测试获取子图"""
        graph.add_node("craft", "craft")
        graph.add_node("material1", "material")
        graph.add_node("material2", "material")
        graph.add_node("tool", "tool")
        graph.add_edge("craft", "material1", "uses_material")
        graph.add_edge("craft", "material2", "uses_material")
        graph.add_edge("material1", "tool", "uses_tool")
        
        subgraph = graph.get_subgraph("craft", depth=1)
        
        assert "nodes" in subgraph
        assert "edges" in subgraph
        # craft + material1 + material2
        assert len(subgraph["nodes"]) >= 3
    
    def test_is_initialized(self, graph):
        """测试初始化状态检查"""
        assert graph.is_initialized() is False
        
        graph.add_node("test", "craft")
        
        assert graph.is_initialized() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
