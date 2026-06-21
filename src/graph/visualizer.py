"""
非遗知识图谱可视化器 - 基于pyvis的交互式图谱渲染
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from pyvis.network import Network
except ImportError:
    Network = None
    logger.warning("pyvis未安装，图谱可视化功能不可用。请运行: pip install pyvis>=2.1.0")


class HeritageGraphVisualizer:
    """
    非遗知识图谱可视化器
    
    基于pyvis生成交互式HTML图谱，支持：
    - 节点颜色按类型区分
    - 节点大小按连接度调整
    - 边的关系标签显示
    - 支持过滤和布局切换
    """
    
    # 节点类型到颜色的映射
    NODE_COLORS = {
        "craft": "#8B4513",         # 棕色 - 技艺
        "material": "#2E7D32",      # 绿色 - 材料
        "tool": "#1565C0",           # 蓝色 - 工具
        "inheritor": "#EF6C00",     # 橙色 - 传承人
        "region": "#7B1FA2",        # 紫色 - 地域
        "dynasty": "#C62828",       # 红色 - 朝代
        "unknown": "#757575"        # 灰色 - 未知
    }
    
    # 节点类型中文名称
    NODE_TYPE_NAMES = {
        "craft": "技艺",
        "material": "材料",
        "tool": "工具",
        "inheritor": "传承人",
        "region": "地域",
        "dynasty": "朝代",
        "unknown": "其他"
    }
    
    # 边类型中文名称
    EDGE_TYPE_NAMES = {
        "uses_material": "使用材料",
        "uses_tool": "使用工具",
        "mastered_by": "传承人掌握",
        "originates_from": "发源于",
        "originated_in": "起源于",
        "related_to": "与...相关",
        "influenced_by": "受...影响"
    }
    
    def __init__(self, graph: Optional[Any] = None):
        """
        初始化可视化器
        
        Args:
            graph: HeritageKnowledgeGraph实例
        """
        self.graph = graph
        self._html_template = None
    
    def set_graph(self, graph: Any):
        """设置知识图谱"""
        self.graph = graph
    
    def _get_node_color(self, node_type: str) -> str:
        """
        根据节点类型返回颜色
        
        Args:
            node_type: 节点类型
        
        Returns:
            颜色代码（十六进制）
        """
        return self.NODE_COLORS.get(node_type, self.NODE_COLORS["unknown"])
    
    def _get_node_size(self, node_data: Dict, degree: int) -> int:
        """
        根据节点数据返回大小
        
        Args:
            node_data: 节点数据字典
            degree: 节点度数
        
        Returns:
            节点大小
        """
        base_size = 15
        # 根据度数增加大小
        return base_size + min(degree * 2, 25)
    
    def _get_edge_color(self, relation: str) -> str:
        """
        根据关系类型返回边的颜色
        
        Args:
            relation: 关系类型
        
        Returns:
            颜色代码
        """
        if "material" in relation:
            return "#2E7D32"
        elif "tool" in relation:
            return "#1565C0"
        elif "mastered" in relation:
            return "#EF6C00"
        else:
            return "#9E9E9E"
    
    def render_interactive(
        self,
        filter_type: Optional[str] = None,
        layout: str = "force",
        height: str = "600px"
    ) -> str:
        """
        生成交互式HTML图谱
        
        Args:
            filter_type: 节点类型过滤（可选）
            layout: 布局类型 ("force", "random", "circular", "hierarchical")
            height: 图表高度
        
        Returns:
            HTML字符串
        """
        if Network is None:
            return self._render_fallback_html("pyvis未安装")
        
        if self.graph is None:
            return self._render_fallback_html("知识图谱未加载")
        
        # 创建pyvis网络
        net = Network(
            height=height,
            width="100%",
            bgcolor="#FFF8F0",
            font_color="#333333",
            directed=True,
            notebook=False,
            select_menu=True,
            filter_menu=True
        )
        
        # 设置物理引擎参数
        if layout == "force":
            net.barnes_hut(
                gravity=-5000,
                central_gravity=0.3,
                spring_length=150,
                spring_strength=0.01,
                damping=0.09
            )
        elif layout == "circular":
            net.from_nx(self.graph.to_networkx())
            # 设置为圆形布局
            for node in net.nodes:
                node["physics"] = False
        
        # 添加节点
        nodes_to_add = []
        edges_to_add = []
        
        graph_nx = self.graph.to_networkx()
        
        for node_id, attrs in self.graph.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            
            # 类型过滤
            if filter_type and node_type != filter_type:
                continue
            
            node_name = attrs.get("name", node_id)
            degree = graph_nx.degree(node_id)
            size = self._get_node_size(attrs, degree)
            color = self._get_node_color(node_type)
            
            # 构建悬停文本
            properties = attrs.get("properties", {})
            hover_text = f"<b>{node_name}</b><br>"
            hover_text += f"类型: {self.NODE_TYPE_NAMES.get(node_type, '未知')}<br>"
            if properties:
                for key, value in list(properties.items())[:3]:
                    hover_text += f"{key}: {value}<br>"
            
            nodes_to_add.append({
                "id": node_id,
                "label": node_name,
                "title": hover_text,
                "color": {
                    "background": color,
                    "border": "#333333",
                    "highlight": {
                        "background": color,
                        "border": "#FFD700"
                    }
                },
                "size": size,
                "font": {
                    "size": 14,
                    "color": "#333333"
                },
                "borderWidth": 2,
                "borderWidthSelected": 4
            })
        
        # 添加边
        for source, target, attrs in self.graph.graph.edges(data=True):
            # 类型过滤
            if filter_type:
                source_type = self.graph.graph.nodes[source].get("type", "unknown")
                target_type = self.graph.graph.nodes[target].get("type", "unknown")
                if source_type != filter_type and target_type != filter_type:
                    continue
            
            relation = attrs.get("relation", "related_to")
            relation_name = self.EDGE_TYPE_NAMES.get(relation, relation)
            
            # 获取节点名称
            source_name = self.graph.graph.nodes[source].get("name", source)
            target_name = self.graph.graph.nodes[target].get("name", target)
            
            edges_to_add.append({
                "from": source,
                "to": target,
                "title": f"{source_name} → {relation_name} → {target_name}",
                "label": relation_name,
                "color": self._get_edge_color(relation),
                "arrows": "to",
                "arrowStrikethrough": False,
                "font": {
                    "size": 10,
                    "color": "#666666",
                    "strokeWidth": 0
                },
                "smooth": {
                    "type": "continuous",
                    "roundness": 0.5
                }
            })
        
        # 添加到网络
        net.add_nodes([n["id"] for n in nodes_to_add])
        for node in nodes_to_add:
            net.add_node(**node)
        
        for edge in edges_to_add:
            net.add_edge(**edge)
        
        # 设置选项
        net.set_options("""
        {
            "nodes": {
                "shapeProperties": {
                    "borderRadius": 10
                }
            },
            "edges": {
                "color": {
                    "inherit": false
                },
                "smooth": {
                    "type": "continuous"
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 100,
                "hideEdgesOnDrag": true,
                "navigationButtons": true,
                "keyboard": true
            },
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -5000,
                    "centralGravity": 0.3,
                    "springLength": 150,
                    "springConstant": 0.01,
                    "damping": 0.09
                }
            }
        }
        """)
        
        # 生成HTML
        try:
            html_content = net.generate_html()
            
            # 添加自定义样式和脚本
            html_content = self._enhance_html(html_content, nodes_to_add, edges_to_add)
            
            return html_content
        except Exception as e:
            logger.error(f"图谱渲染失败: {e}")
            return self._render_fallback_html(str(e))
    
    def _enhance_html(
        self,
        html: str,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> str:
        """
        增强HTML，添加图例和说明
        
        Args:
            html: 原始HTML
            nodes: 节点列表
            edges: 边列表
        
        Returns:
            增强后的HTML
        """
        # 统计各类型节点数量
        type_counts = {}
        for node in nodes:
            # 从颜色推断类型
            color = node.get("color", {}).get("background", "#757575")
            for ntype, ncolor in self.NODE_COLORS.items():
                if ncolor.lower() == color.lower():
                    type_counts[ntype] = type_counts.get(ntype, 0) + 1
                    break
            else:
                type_counts["unknown"] = type_counts.get("unknown", 0) + 1
        
        # 构建图例HTML
        legend_html = '<div style="position:absolute;top:10px;left:10px;z-index:1000;background:white;padding:15px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);font-family:sans-serif;font-size:12px;">'
        legend_html += '<b style="color:#8B4513;">📚 图例</b><br><br>'
        
        for ntype, color in self.NODE_COLORS.items():
            if ntype == "unknown":
                continue
            count = type_counts.get(ntype, 0)
            type_name = self.NODE_TYPE_NAMES.get(ntype, ntype)
            legend_html += f'<span style="display:inline-block;width:12px;height:12px;background:{color};border-radius:50%;margin-right:5px;"></span>'
            legend_html += f'{type_name}: {count}<br>'
        
        legend_html += '<br><b style="color:#666;">🖱️ 操作提示</b><br>'
        legend_html += '<span style="color:#888;font-size:10px;">拖动节点查看详情<br>滚轮缩放<br>双击节点居中</span>'
        legend_html += '</div>'
        
        # 在HTML body中插入图例
        if "<body>" in html:
            html = html.replace("<body>", f"<body>\n{legend_html}")
        
        return html
    
    def render_subgraph(
        self,
        center_node: str,
        depth: int = 2
    ) -> str:
        """
        渲染子图（以某节点为中心）
        
        Args:
            center_node: 中心节点ID
            depth: 扩展深度
        
        Returns:
            HTML字符串
        """
        if self.graph is None:
            return self._render_fallback_html("知识图谱未加载")
        
        # 获取子图
        subgraph_data = self.graph.get_subgraph(center_node, depth)
        
        if not subgraph_data or not subgraph_data.get("nodes"):
            return self._render_fallback_html(f"未找到节点: {center_node}")
        
        # 创建临时图谱用于渲染
        if Network is None:
            return self._render_fallback_html("pyvis未安装")
        
        net = Network(
            height="500px",
            width="100%",
            bgcolor="#FFF8F0",
            font_color="#333333",
            directed=True,
            notebook=False
        )
        
        graph_nx = self.graph.to_networkx()
        
        # 添加节点
        for node in subgraph_data.get("nodes", []):
            node_id = node["id"]
            node_type = node.get("type", "unknown")
            node_name = node.get("name", node_id)
            color = self._get_node_color(node_type)
            
            # 获取完整属性
            full_node = self.graph.get_node(node_id) or {}
            properties = full_node.get("properties", {})
            degree = graph_nx.degree(node_id)
            size = self._get_node_size(full_node, degree)
            
            hover_text = f"<b>{node_name}</b><br>"
            hover_text += f"类型: {self.NODE_TYPE_NAMES.get(node_type, '未知')}<br>"
            if properties:
                for key, value in list(properties.items())[:3]:
                    hover_text += f"{key}: {value}<br>"
            
            # 高亮中心节点
            is_center = (node_id == center_node)
            
            net.add_node(
                node_id,
                label=node_name,
                title=hover_text,
                color={
                    "background": color if not is_center else "#FFD700",
                    "border": "#333333" if not is_center else "#8B4513",
                    "highlight": {"background": "#FFD700", "border": "#8B4513"}
                },
                size=size if not is_center else size + 10,
                font={"size": 14, "color": "#333333", "bold": is_center},
                borderWidth=3 if is_center else 2
            )
        
        # 添加边
        for edge in subgraph_data.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            relation = edge.get("relation", "related_to")
            relation_name = self.EDGE_TYPE_NAMES.get(relation, relation)
            
            net.add_edge(
                source,
                target,
                title=relation_name,
                label=relation_name,
                color=self._get_edge_color(relation),
                arrows="to",
                font={"size": 10, "color": "#666666"}
            )
        
        # 生成HTML
        html = net.generate_html()
        
        # 添加标题
        center_name = self.graph.get_node(center_node).get("name", center_node) if self.graph.get_node(center_node) else center_node
        title_html = f'<div style="text-align:center;padding:10px;background:#FFF8F0;color:#8B4513;font-family:sans-serif;"><b>📍 {center_name}</b> 的知识网络（{depth}度关联）</div>'
        
        if "<body>" in html:
            html = html.replace("<body>", f"<body>\n{title_html}")
        
        return html
    
    def render_comparison(
        self,
        node_ids: List[str],
        title: str = "对比视图"
    ) -> str:
        """
        渲染多个节点的对比视图
        
        Args:
            node_ids: 节点ID列表
            title: 标题
        
        Returns:
            HTML字符串
        """
        if self.graph is None:
            return self._render_fallback_html("知识图谱未加载")
        
        if Network is None:
            return self._render_fallback_html("pyvis未安装")
        
        # 收集相关节点和边
        related_nodes = set()
        related_edges = []
        
        graph_nx = self.graph.to_networkx()
        
        for node_id in node_ids:
            if node_id in graph_nx:
                related_nodes.add(node_id)
                # 添加邻居
                for neighbor in graph_nx.neighbors(node_id):
                    related_nodes.add(neighbor)
        
        # 构建子图
        subgraph = graph_nx.subgraph(related_nodes)
        
        net = Network(
            height="500px",
            width="100%",
            bgcolor="#FFF8F0",
            font_color="#333333",
            directed=True,
            notebook=False
        )
        
        for node in subgraph.nodes():
            attrs = self.graph.graph.nodes[node]
            node_type = attrs.get("type", "unknown")
            node_name = attrs.get("name", node)
            color = self._get_node_color(node_type)
            degree = graph_nx.degree(node)
            size = self._get_node_size(attrs, degree)
            
            is_selected = node in node_ids
            
            hover_text = f"<b>{node_name}</b><br>"
            hover_text += f"类型: {self.NODE_TYPE_NAMES.get(node_type, '未知')}"
            
            net.add_node(
                node,
                label=node_name,
                title=hover_text,
                color={
                    "background": color if not is_selected else "#FFD700",
                    "border": "#333333" if not is_selected else "#8B4513",
                    "highlight": {"background": "#FFD700", "border": "#8B4513"}
                },
                size=size + 5 if is_selected else size,
                font={"size": 14, "color": "#333333", "bold": is_selected},
                borderWidth=3 if is_selected else 2
            )
        
        for u, v in subgraph.edges():
            attrs = subgraph.edges[u, v]
            relation = attrs.get("relation", "related_to")
            relation_name = self.EDGE_TYPE_NAMES.get(relation, relation)
            
            net.add_edge(
                u, v,
                title=relation_name,
                label=relation_name,
                color=self._get_edge_color(relation),
                arrows="to",
                font={"size": 10, "color": "#666666"}
            )
        
        html = net.generate_html()
        
        # 添加标题
        names = [self.graph.get_node(n).get("name", n) if self.graph.get_node(n) else n for n in node_ids]
        title_html = f'<div style="text-align:center;padding:10px;background:#FFF8F0;color:#8B4513;font-family:sans-serif;"><b>📊 {title}</b><br><small>{" vs ".join(names)}</small></div>'
        
        if "<body>" in html:
            html = html.replace("<body>", f"<body>\n{title_html}")
        
        return html
    
    def _render_fallback_html(self, message: str) -> str:
        """
        渲染降级HTML（当pyvis不可用时）
        
        Args:
            message: 提示信息
        
        Returns:
            HTML字符串
        """
        return f"""
        <div style="
            width: 100%;
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #FFF8F0;
            border: 2px dashed #D2691E;
            border-radius: 10px;
            font-family: 'Microsoft YaHei', sans-serif;
            color: #8B4513;
        ">
            <div style="text-align: center;">
                <p style="font-size: 48px; margin: 0;">📊</p>
                <p style="margin-top: 10px;">{message}</p>
                <p style="color: #666; font-size: 12px; margin-top: 5px;">
                    提示: pip install pyvis>=2.1.0
                </p>
            </div>
        </div>
        """
    
    def get_statistics_html(self) -> str:
        """
        获取图谱统计信息的HTML
        
        Returns:
            HTML字符串
        """
        if self.graph is None:
            return "<p>知识图谱未加载</p>"
        
        stats = self.graph.get_statistics()
        
        html = '<div style="font-family: sans-serif; padding: 15px; background: #FFF8F0; border-radius: 10px;">'
        html += '<h4 style="color: #8B4513; margin-top: 0;">📈 图谱统计</h4>'
        html += f'<p><b>节点总数:</b> {stats.get("total_nodes", 0)}</p>'
        html += f'<p><b>边总数:</b> {stats.get("total_edges", 0)}</p>'
        
        html += '<hr style="border: none; border-top: 1px solid #D2691E; margin: 15px 0;">'
        html += '<h5 style="color: #8B4513;">节点类型分布</h5>'
        html += '<ul style="list-style: none; padding: 0;">'
        
        for ntype, count in stats.get("node_types", {}).items():
            type_name = self.NODE_TYPE_NAMES.get(ntype, ntype)
            color = self._get_node_color(ntype)
            html += f'<li style="padding: 5px 0;">'
            html += f'<span style="display: inline-block; width: 12px; height: 12px; background: {color}; border-radius: 50%; margin-right: 8px;"></span>'
            html += f'{type_name}: <b>{count}</b>'
            html += '</li>'
        
        html += '</ul>'
        html += '</div>'
        
        return html
