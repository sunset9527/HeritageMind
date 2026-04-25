"""
LangGraph主工作流 - 多智能体编排
"""

import logging
from typing import Dict, List, Any, Literal, Optional
from langgraph.graph import StateGraph, END

from src.workflow.state import WorkflowState, create_initial_state, state_to_response, QueryResponse
from src.workflow.nodes import (
    analyze_question_node,
    dispatch_to_experts_node,
    collect_expert_responses_node,
    fuse_knowledge_node,
    detect_gaps_node,
    generate_response_node,
    should_include_narrative,
    should_detect_gaps,
    has_expert_responses,
)

logger = logging.getLogger(__name__)


class HeritageWorkflowGraph:
    """
    非遗知识问答工作流
    
    基于LangGraph的多智能体编排系统，支持：
    - 问题分析与专家分派
    - 多专家并行处理
    - 知识融合
    - 知识缺口检测
    - 多粒度回答生成
    - 叙事模式切换
    """
    
    def __init__(self):
        """初始化工作流"""
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """构建工作流图"""
        
        # 创建状态图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("analyze_question", analyze_question_node)
        workflow.add_node("dispatch_to_experts", dispatch_to_experts_node)
        workflow.add_node("collect_responses", collect_expert_responses_node)
        workflow.add_node("fuse_knowledge", fuse_knowledge_node)
        workflow.add_node("detect_gaps", detect_gaps_node)
        workflow.add_node("generate_response_narrative", generate_response_node)
        workflow.add_node("generate_response_standard", generate_response_node)
        
        # 设置入口点
        workflow.set_entry_point("analyze_question")
        
        # 添加边
        workflow.add_edge("analyze_question", "dispatch_to_experts")
        workflow.add_edge("dispatch_to_experts", "collect_responses")
        
        # 条件边：检查是否有专家响应
        workflow.add_conditional_edges(
            "collect_responses",
            has_expert_responses,
            {
                "fuse": "fuse_knowledge",
                "error": END
            }
        )
        
        # 从融合到缺口检测的条件边
        workflow.add_edge("fuse_knowledge", "detect_gaps")
        
        # 条件边：是否进行缺口检测
        workflow.add_conditional_edges(
            "detect_gaps",
            should_detect_gaps,
            {
                "skip_gaps": "generate_response_standard",
                "detect_gaps": "generate_response_standard"
            }
        )
        
        # 生成响应后的条件边
        workflow.add_conditional_edges(
            "generate_response_standard",
            should_include_narrative,
            {
                "narrative": "generate_response_narrative",
                "standard": END
            }
        )
        
        workflow.add_edge("generate_response_narrative", END)
        
        # 编译图（不需要checkpointer，每次查询独立无状态）
        self.graph = workflow.compile()
        
        logger.info("工作流图编译完成")
    
    def query(
        self,
        question: str,
        user_profile: str = "curious",
        include_narrative: bool = False,
        thread_id: Optional[str] = None
    ) -> QueryResponse:
        """
        执行问答查询
        
        Args:
            question: 用户问题
            user_profile: 用户画像
            include_narrative: 是否使用传承人口吻
            thread_id: 会话线程ID
        
        Returns:
            QueryResponse: 问答响应
        """
        # 创建初始状态
        initial_state = create_initial_state(
            question=question,
            user_profile=user_profile,
            include_narrative=include_narrative
        )
        
        try:
            # 执行工作流
            final_state = None
            for state in self.graph.stream(initial_state):
                final_state = state
                logger.debug(f"工作流状态更新: {list(state.keys())}")
            
            # 获取最终状态
            if final_state:
                # 取最后一个状态的值
                last_state = None
                for state_values in final_state.values():
                    last_state = state_values
                
                if last_state:
                    return state_to_response(last_state)
            
            # 降级响应
            return QueryResponse(
                question=question,
                answer="处理过程中出现问题，请稍后重试。",
                user_profile=user_profile,
                source_agents=[],
                has_gaps=False,
                gap_report="",
                reading_time=1,
                metadata={"error": "工作流执行异常"}
            )
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            return QueryResponse(
                question=question,
                answer=f"处理过程中出现错误：{str(e)}",
                user_profile=user_profile,
                source_agents=[],
                has_gaps=False,
                gap_report="",
                reading_time=1,
                metadata={"error": str(e)}
            )
    
    def get_graph可视化(self) -> Dict[str, Any]:
        """
        获取工作流图的可视化数据
        
        Returns:
            Dict: 图结构数据
        """
        if self.graph is None:
            return {}
        
        # 获取图的节点和边
        nodes = []
        edges = []
        
        # 节点定义
        node_defs = [
            {"id": "analyze_question", "name": "问题分析", "type": "start"},
            {"id": "dispatch_to_experts", "name": "专家分派", "type": "process"},
            {"id": "collect_responses", "name": "收集响应", "type": "process"},
            {"id": "fuse_knowledge", "name": "知识融合", "type": "process"},
            {"id": "detect_gaps", "name": "缺口检测", "type": "decision"},
            {"id": "generate_response_narrative", "name": "叙事生成", "type": "end"},
            {"id": "generate_response_standard", "name": "标准生成", "type": "end"},
        ]
        
        nodes = node_defs
        
        # 边定义
        edge_defs = [
            {"source": "analyze_question", "target": "dispatch_to_experts"},
            {"source": "dispatch_to_experts", "target": "collect_responses"},
            {"source": "collect_responses", "target": "fuse_knowledge"},
            {"source": "fuse_knowledge", "target": "detect_gaps"},
            {"source": "detect_gaps", "target": "generate_response_standard"},
            {"source": "generate_response_standard", "target": "generate_response_narrative"},
        ]
        
        edges = edge_defs
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "description": "非遗知识问答工作流",
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
    
    async def aquery(
        self,
        question: str,
        user_profile: str = "curious",
        include_narrative: bool = False,
        thread_id: Optional[str] = None
    ) -> QueryResponse:
        """
        异步执行问答查询
        
        Args:
            question: 用户问题
            user_profile: 用户画像
            include_narrative: 是否使用传承人口吻
            thread_id: 会话线程ID
        
        Returns:
            QueryResponse: 问答响应
        """
        import asyncio
        
        # 创建初始状态
        initial_state = create_initial_state(
            question=question,
            user_profile=user_profile,
            include_narrative=include_narrative
        )
        
        try:
            # 异步执行工作流
            final_state = None
            async for state in self.graph.astream(initial_state):
                final_state = state
                logger.debug(f"工作流状态更新: {list(state.keys())}")
            
            # 获取最终状态
            if final_state:
                last_state = None
                for state_values in final_state.values():
                    last_state = state_values
                
                if last_state:
                    return state_to_response(last_state)
            
            # 降级响应
            return QueryResponse(
                question=question,
                answer="处理过程中出现问题，请稍后重试。",
                user_profile=user_profile,
                source_agents=[],
                has_gaps=False,
                gap_report="",
                reading_time=1,
                metadata={"error": "工作流执行异常"}
            )
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            return QueryResponse(
                question=question,
                answer=f"处理过程中出现错误：{str(e)}",
                user_profile=user_profile,
                source_agents=[],
                has_gaps=False,
                gap_report="",
                reading_time=1,
                metadata={"error": str(e)}
            )


# 全局工作流实例
_workflow_instance: Optional[HeritageWorkflowGraph] = None


def get_workflow() -> HeritageWorkflowGraph:
    """获取工作流实例（单例）"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = HeritageWorkflowGraph()
    return _workflow_instance


def query_heritage(
    question: str,
    user_profile: str = "curious",
    include_narrative: bool = False
) -> QueryResponse:
    """
    便捷函数：执行非遗问答
    
    Args:
        question: 用户问题
        user_profile: 用户画像
        include_narrative: 是否使用传承人口吻
    
    Returns:
        QueryResponse: 问答响应
    """
    workflow = get_workflow()
    return workflow.query(
        question=question,
        user_profile=user_profile,
        include_narrative=include_narrative
    )
