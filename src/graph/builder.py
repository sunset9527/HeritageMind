"""
知识图谱构建器 - 从文档和数据构建非遗知识图谱
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from config import settings
from src.graph.heritage_graph import HeritageKnowledgeGraph

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    知识图谱构建器
    
    功能：
    1. 从预定义数据构建初始图谱
    2. 从文档中抽取实体和关系
    3. 增量更新图谱
    4. 验证图谱一致性
    """
    
    def __init__(self):
        """初始化构建器"""
        self.graph = HeritageKnowledgeGraph()
    
    def build_initial_graph(self) -> HeritageKnowledgeGraph:
        """
        构建初始知识图谱
        
        Returns:
            HeritageKnowledgeGraph: 构建好的图谱
        """
        logger.info("开始构建初始知识图谱...")
        
        # 添加节点类型定义
        self._add_craft_nodes()
        self._add_material_nodes()
        self._add_tool_nodes()
        self._add_inheritor_nodes()
        self._add_region_nodes()
        self._add_dynasty_nodes()
        
        # 添加关系
        self._add_craft_relations()
        
        self.graph._initialized = True
        logger.info(f"初始图谱构建完成：{len(self.graph.graph.nodes)}节点，{len(self.graph.graph.edges)}边")
        
        return self.graph
    
    def _add_craft_nodes(self):
        """添加技艺节点"""
        crafts = [
            ("jingtailan", "景泰蓝", "北京市", "国家级非遗"),
            ("suxiu", "苏绣", "苏州市", "国家级非遗"),
            ("longquan_ci", "龙泉青瓷", "龙泉市", "国家级非遗"),
            ("yixing_zisha", "宜兴紫砂", "宜兴市", "国家级非遗"),
            ("wuhu_tiehua", "芜湖铁画", "芜湖市", "国家级非遗"),
            ("shujin", "蜀锦", "成都市", "国家级非遗"),
        ]
        
        for node_id, name, region, level in crafts:
            self.graph.add_node(
                node_id=node_id,
                node_type="craft",
                name=name,
                properties={
                    "region": region,
                    "protection_level": level
                }
            )
    
    def _add_material_nodes(self):
        """添加材料节点"""
        materials = [
            ("tongsi", "铜丝", "景泰蓝的主要材料"),
            ("flame_glaze", "珐琅釉料", "景泰蓝的釉料"),
            ("zijin", "紫铜", "景泰蓝的胎料"),
            ("sichou", "蚕丝线", "苏绣的主要材料"),
            ("si_duan", "丝绸缎", "苏绣的底料"),
            ("ci_tu", "瓷土", "龙泉青瓷的原料"),
            ("zijin_tu", "紫金土", "龙泉青瓷的着色剂"),
            ("zisha_ni", "紫砂泥", "紫砂壶的原料"),
            ("duan_ni", "段泥", "紫砂壶的泥料"),
            ("shu_tie", "熟铁", "芜湖铁画的材料"),
            ("canye_si", "蚕丝", "蜀锦的原料"),
            ("jinyin_xian", "金银线", "蜀锦的装饰线"),
        ]
        
        for node_id, name, description in materials:
            self.graph.add_node(
                node_id=node_id,
                node_type="material",
                name=name,
                properties={"description": description}
            )
    
    def _add_tool_nodes(self):
        """添加工具节点"""
        tools = [
            ("cas_tool", "掐丝工具", "景泰蓝掐丝专用"),
            ("hanqiang", "焊枪", "焊接工具"),
            ("lanqiang", "蓝枪", "点蓝工具"),
            ("moshi", "磨石", "打磨工具"),
            ("xiu_zhen", "绣针", "刺绣工具"),
            ("xiu_peng", "绣绷", "刺绣辅助工具"),
            ("ladder_loom", "花楼织机", "蜀锦织造工具"),
            ("lathe", "拉坯机", "瓷器成型工具"),
            ("tiewan", "铁锤", "铁画锻造工具"),
            ("zhu_zi", "砧子", "铁画锻造工具"),
        ]
        
        for node_id, name, description in tools:
            self.graph.add_node(
                node_id=node_id,
                node_type="tool",
                name=name,
                properties={"description": description}
            )
    
    def _add_inheritor_nodes(self):
        """添加传承人节点"""
        inheritors = [
            ("qian_meihua", "钱美华", "景泰蓝", "国家级传承人"),
            ("zhang_luqi", "张禄祺", "景泰蓝", "国家级传承人"),
            ("yao_jianping", "姚建萍", "苏绣", "国家级传承人"),
            ("xu_chaoxing", "徐朝兴", "龙泉青瓷", "国家级传承人"),
            ("wang_yinxian", "汪寅仙", "宜兴紫砂", "国家级传承人"),
            ("yang_guanghui", "杨光辉", "芜湖铁画", "国家级传承人"),
            ("liu_chenxia", "刘晨霞", "蜀锦", "国家级传承人"),
        ]
        
        for node_id, name, craft, level in inheritors:
            self.graph.add_node(
                node_id=node_id,
                node_type="inheritor",
                name=name,
                properties={
                    "main_craft": craft,
                    "level": level
                }
            )
    
    def _add_region_nodes(self):
        """添加地域节点"""
        regions = [
            ("beijing", "北京市", "华北地区"),
            ("suzhou", "苏州市", "江苏省"),
            ("longquan", "龙泉市", "浙江省"),
            ("yixing", "宜兴市", "江苏省"),
            ("wuhu", "芜湖市", "安徽省"),
            ("chengdu", "成都市", "四川省"),
        ]
        
        for node_id, name, location in regions:
            self.graph.add_node(
                node_id=node_id,
                node_type="region",
                name=name,
                properties={"location": location}
            )
    
    def _add_dynasty_nodes(self):
        """添加朝代节点"""
        dynasties = [
            ("yuan", "元代", "1271-1368"),
            ("ming", "明代", "1368-1644"),
            ("qing", "清代", "1644-1912"),
            ("modern", "近代", "1840-1949"),
            ("contemporary", "当代", "1949-至今"),
        ]
        
        for node_id, name, period in dynasties:
            self.graph.add_node(
                node_id=node_id,
                node_type="dynasty",
                name=name,
                properties={"period": period}
            )
    
    def _add_craft_relations(self):
        """添加技艺相关关系"""
        # 景泰蓝关系
        self.graph.add_edge("jingtailan", "tongsi", "uses_material")
        self.graph.add_edge("jingtailan", "flame_glaze", "uses_material")
        self.graph.add_edge("jingtailan", "zijin", "uses_material")
        self.graph.add_edge("jingtailan", "cas_tool", "uses_tool")
        self.graph.add_edge("jingtailan", "hanqiang", "uses_tool")
        self.graph.add_edge("jingtailan", "beijing", "originates_from")
        self.graph.add_edge("jingtailan", "ming", "originated_in")
        self.graph.add_edge("qian_meihua", "jingtailan", "mastered_by")
        self.graph.add_edge("zhang_luqi", "jingtailan", "mastered_by")
        
        # 苏绣关系
        self.graph.add_edge("suxiu", "sichou", "uses_material")
        self.graph.add_edge("suxiu", "si_duan", "uses_material")
        self.graph.add_edge("suxiu", "xiu_zhen", "uses_tool")
        self.graph.add_edge("suxiu", "xiu_peng", "uses_tool")
        self.graph.add_edge("suxiu", "suzhou", "originates_from")
        self.graph.add_edge("suxiu", "ming", "originated_in")
        self.graph.add_edge("yao_jianping", "suxiu", "mastered_by")
        
        # 龙泉青瓷关系
        self.graph.add_edge("longquan_ci", "ci_tu", "uses_material")
        self.graph.add_edge("longquan_ci", "zijin_tu", "uses_material")
        self.graph.add_edge("longquan_ci", "lathe", "uses_tool")
        self.graph.add_edge("longquan_ci", "longquan", "originates_from")
        self.graph.add_edge("longquan_ci", "song", "originated_in")
        self.graph.add_edge("xu_chaoxing", "longquan_ci", "mastered_by")
        
        # 宜兴紫砂关系
        self.graph.add_edge("yixing_zisha", "zisha_ni", "uses_material")
        self.graph.add_edge("yixing_zisha", "duan_ni", "uses_material")
        self.graph.add_edge("yixing_zisha", "yixing", "originates_from")
        self.graph.add_edge("yixing_zisha", "ming", "originated_in")
        self.graph.add_edge("wang_yinxian", "yixing_zisha", "mastered_by")
        
        # 芜湖铁画关系
        self.graph.add_edge("wuhu_tiehua", "shu_tie", "uses_material")
        self.graph.add_edge("wuhu_tiehua", "tiewan", "uses_tool")
        self.graph.add_edge("wuhu_tiehua", "zhu_zi", "uses_tool")
        self.graph.add_edge("wuhu_tiehua", "wuhu", "originates_from")
        self.graph.add_edge("wuhu_tiehua", "qing", "originated_in")
        self.graph.add_edge("yang_guanghui", "wuhu_tiehua", "mastered_by")
        
        # 蜀锦关系
        self.graph.add_edge("shujin", "canye_si", "uses_material")
        self.graph.add_edge("shujin", "jinyin_xian", "uses_material")
        self.graph.add_edge("shujin", "ladder_loom", "uses_tool")
        self.graph.add_edge("shujin", "chengdu", "originates_from")
        self.graph.add_edge("shujin", "han", "originated_in")
        self.graph.add_edge("liu_chenxia", "shujin", "mastered_by")
        
        # 添加朝代朝代
        self.graph.add_node("song", "dynasty", "宋代", {"period": "960-1279"})
        self.graph.add_edge("longquan_ci", "song", "originated_in")
    
    def build_from_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> HeritageKnowledgeGraph:
        """
        从文档构建知识图谱
        
        Args:
            documents: 文档列表，每篇文档包含 id, content, metadata
        
        Returns:
            HeritageKnowledgeGraph: 构建好的图谱
        """
        logger.info(f"从{len(documents)}篇文档构建图谱...")
        
        for doc in documents:
            self._extract_entities_from_doc(doc)
        
        self.graph._initialized = True
        return self.graph
    
    def _extract_entities_from_doc(self, doc: Dict[str, Any]):
        """从文档中抽取实体和关系"""
        # 这里可以接入NER模型进行实体抽取
        # 当前实现为基于规则的简单抽取
        content = doc.get("content", "")
        doc_id = doc.get("id", "")
        
        # 简单的基于关键词的实体识别
        craft_keywords = ["景泰蓝", "苏绣", "龙泉青瓷", "宜兴紫砂", "芜湖铁画", "蜀锦"]
        for craft in craft_keywords:
            if craft in content:
                self.graph.add_node(
                    node_id=craft,
                    node_type="craft",
                    name=craft,
                    properties={"source_doc": doc_id}
                )
    
    def update_graph(
        self,
        new_nodes: List[Dict[str, Any]],
        new_edges: List[Dict[str, Any]]
    ):
        """
        更新图谱
        
        Args:
            new_nodes: 新增节点列表
            new_edges: 新增边列表
        """
        for node in new_nodes:
            self.graph.add_node(
                node_id=node["id"],
                node_type=node.get("type", "unknown"),
                name=node.get("name", node["id"]),
                properties=node.get("properties", {})
            )
        
        for edge in new_edges:
            self.graph.add_edge(
                source=edge["source"],
                target=edge["target"],
                relation=edge.get("relation", "related_to"),
                properties=edge.get("properties", {})
            )
        
        logger.info(f"图谱更新完成：新增{len(new_nodes)}节点，{len(new_edges)}边")
    
    def validate_graph(self) -> Dict[str, Any]:
        """
        验证图谱一致性
        
        Returns:
            验证结果
        """
        issues = []
        
        # 检查孤立节点
        for node in self.graph.graph.nodes():
            if self.graph.graph.degree(node) == 0:
                issues.append(f"孤立节点：{node}")
        
        # 检查重复节点
        names = {}
        for node, attrs in self.graph.graph.nodes(data=True):
            name = attrs.get("name", node)
            if name in names:
                issues.append(f"重复名称：{name}（{node}, {names[name]}）")
            names[name] = node
        
        # 检查无效边
        for u, v in self.graph.graph.edges():
            if u not in self.graph.graph or v not in self.graph.graph:
                issues.append(f"无效边：{u} -> {v}")
        
        return {
            "valid": len(issues) == 0,
            "node_count": len(self.graph.graph.nodes),
            "edge_count": len(self.graph.graph.edges),
            "issues": issues
        }
    
    def merge_graph(self, other_graph: 'HeritageKnowledgeGraph'):
        """
        合并另一个图谱
        
        Args:
            other_graph: 要合并的图谱
        """
        # 合并节点
        for node, attrs in other_graph.graph.nodes(data=True):
            if node not in self.graph.graph:
                self.graph.add_node(
                    node_id=node,
                    node_type=attrs.get("type", "unknown"),
                    name=attrs.get("name", node),
                    properties=attrs.get("properties", {})
                )
        
        # 合并边
        for u, v, attrs in other_graph.graph.edges(data=True):
            if not self.graph.graph.has_edge(u, v):
                self.graph.add_edge(
                    source=u,
                    target=v,
                    relation=attrs.get("relation", "related_to"),
                    properties=attrs.get("properties", {})
                )
        
        logger.info(f"图谱合并完成：{len(other_graph.graph.nodes)}节点，{len(other_graph.graph.edges)}边")
