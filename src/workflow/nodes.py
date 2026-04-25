"""
工作流节点定义 - LangGraph各处理节点
"""

import logging
from typing import Dict, Any, List, Literal, Callable, Optional
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.agents.dispatcher import DispatcherAgent
from src.agents.craft_expert import CraftExpertAgent
from src.agents.history_expert import HistoryExpertAgent
from src.agents.heritage_expert import HeritageExpertAgent
from src.agents.debate_engine import DebateEngine
from src.knowledge.gap_detector import KnowledgeGapDetector
from src.knowledge.granularity import GranularityController
from src.knowledge.narrative import NarrativeGenerator
from src.retrieval.retriever import MultiSourceRetriever
from src.workflow.state import WorkflowState, AgentResponse

logger = logging.getLogger(__name__)


def analyze_question_node(state: WorkflowState) -> WorkflowState:
    """
    问题分析节点 - 分析用户问题，确定需要的专家Agent
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        question = state["question"]
        logger.info(f"分析问题: {question[:50]}...")
        
        # 初始化调度Agent
        dispatcher = DispatcherAgent()
        
        # 分析问题
        analysis = dispatcher.analyze_question(question)
        
        # 更新状态
        state["question_analysis"] = {
            "intent": analysis.intent_analysis,
            "required_experts": analysis.required_experts,
            "reasoning": analysis.reasoning,
            "key_entities": analysis.key_entities,
            "complexity": analysis.complexity
        }
        state["required_experts"] = analysis.required_experts
        state["key_entities"] = analysis.key_entities
        state["complexity"] = analysis.complexity
        
        logger.info(f"问题分析完成，需要专家: {analysis.required_experts}")
        
    except Exception as e:
        logger.error(f"问题分析失败: {e}")
        state["errors"].append(f"问题分析错误: {str(e)}")
        # 使用默认配置
        state["required_experts"] = ["craft_expert"]
    
    return state


def dispatch_to_experts_node(state: WorkflowState) -> WorkflowState:
    """
    专家分派节点 - 将问题分派给相应的专家Agent
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        required_experts = state.get("required_experts", [])
        question = state["question"]
        context = {
            "key_entities": state.get("key_entities", [])
        }
        
        logger.info(f"分派给专家: {required_experts}")
        
        # 初始化检索器
        retriever = MultiSourceRetriever()
        
        # 根据需要的专家，初始化对应的Agent
        expert_map = {
            "craft_expert": CraftExpertAgent(retriever=retriever),
            "history_expert": HistoryExpertAgent(retriever=retriever),
            "heritage_expert": HeritageExpertAgent(retriever=retriever)
        }
        
        # 分派问题
        responses = {}
        for expert_name in required_experts:
            if expert_name in expert_map:
                logger.info(f"调用 {expert_name}...")
                try:
                    agent = expert_map[expert_name]
                    result = agent.process(question, context)
                    
                    responses[expert_name] = AgentResponse(
                        agent_name=expert_name,
                        content=result.get("answer", ""),
                        success=result.get("success", False),
                        metadata=result
                    )
                except Exception as e:
                    logger.error(f"专家 {expert_name} 处理失败: {e}")
                    responses[expert_name] = AgentResponse(
                        agent_name=expert_name,
                        content=f"处理失败: {str(e)}",
                        success=False,
                        metadata={"error": str(e)}
                    )
        
        state["expert_responses"] = {
            name: resp.model_dump() for name, resp in responses.items()
        }
        
        logger.info(f"专家响应收集完成: {len(responses)}个")
        
    except Exception as e:
        logger.error(f"专家分派失败: {e}")
        state["errors"].append(f"专家分派错误: {str(e)}")
    
    return state


def collect_expert_responses_node(state: WorkflowState) -> WorkflowState:
    """
    收集专家响应节点 - 等待所有专家响应完成
    
    此节点主要用于状态同步和日志记录
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    responses = state.get("expert_responses", {})
    
    success_count = sum(1 for r in responses.values() if r.get("success", False))
    total_count = len(responses)
    
    logger.info(f"专家响应统计: {success_count}/{total_count} 成功")
    
    # 检查是否有失败的专家
    for name, response in responses.items():
        if not response.get("success", False):
            logger.warning(f"专家 {name} 处理失败")
    
    return state


def fuse_knowledge_node(state: WorkflowState) -> WorkflowState:
    """
    知识融合节点 - 将各专家的回答融合成统一内容
    
    支持辩论模式：对于复杂问题，触发多轮辩论获得更深入的回答
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        responses = state.get("expert_responses", {})
        question = state["question"]
        question_analysis = state.get("question_analysis", {})
        
        if not responses:
            state["fused_content"] = "抱歉，暂时没有找到相关信息。"
            return state
        
        logger.info(f"融合{len(responses)}个专家的响应...")
        
        # 初始化调度Agent
        dispatcher = DispatcherAgent()
        
        # 构建响应字典
        response_dict = {
            name: resp.get("content", "")
            for name, resp in responses.items()
            if resp.get("success", False) and resp.get("content")
        }
        
        if not response_dict:
            state["fused_content"] = "抱歉，所有专家都无法回答此问题。"
            return state
        
        # 检查是否应该使用辩论模式
        debate_mode = ""
        should_debate = False
        try:
            should_debate, debate_mode = dispatcher.should_trigger_debate(
                question, question_analysis
            )
        except Exception as e:
            logger.warning(f"辩论模式判断失败: {e}")
        
        if should_debate and len(responses) >= 2:
            logger.info(f"使用辩论模式融合: {debate_mode}")
            state["use_debate"] = True
            state["debate_mode"] = debate_mode
            
            # 初始化Agent实例用于辩论引擎
            retriever = MultiSourceRetriever()
            agents = {
                "craft_expert": CraftExpertAgent(retriever=retriever),
                "history_expert": HistoryExpertAgent(retriever=retriever),
                "heritage_expert": HeritageExpertAgent(retriever=retriever)
            }
            
            # 初始化辩论引擎
            debate_engine = DebateEngine(agents=agents)
            
            try:
                # 运行完整辩论
                debate_session = debate_engine.run_full_debate(
                    question=question,
                    mode=debate_mode,
                    context={
                        "analysis": question_analysis,
                        "initial_responses": response_dict
                    }
                )
                
                # 存储辩论结果
                state["debate_session"] = debate_session.to_dict()
                state["fused_content"] = debate_session.final_synthesis
                
                # 添加关键洞见到metadata
                if debate_session.key_insights:
                    state["metadata"]["key_insights"] = debate_session.key_insights
                
                logger.info("辩论融合完成")
                
            except Exception as e:
                logger.error(f"辩论融合失败: {e}")
                state["use_debate"] = False
                state["debate_session"] = None
                # 降级到普通融合
                fused = dispatcher.fuse_responses(response_dict, question)
                state["fused_content"] = fused
        else:
            # 普通融合模式
            logger.info("使用普通融合模式")
            state["use_debate"] = False
            fused = dispatcher.fuse_responses(response_dict, question)
            state["fused_content"] = fused
        
        # 记录参与的Agent
        state["source_agents"] = [
            {
                "id": name,
                "type": _get_agent_type(name),
                "contribution": "提供专业知识"
            }
            for name in responses.keys()
        ]
        
        logger.info("知识融合完成")
        
    except Exception as e:
        logger.error(f"知识融合失败: {e}")
        state["errors"].append(f"知识融合错误: {str(e)}")
        # 降级处理：简单拼接
        responses = state.get("expert_responses", {})
        parts = [resp.get("content", "") for resp in responses.values() if resp.get("content")]
        state["fused_content"] = "\n\n".join(parts)
    
    return state


def _get_agent_type(agent_name: str) -> str:
    """获取Agent类型"""
    types = {
        "craft_expert": "技艺知识专家",
        "history_expert": "历史文化专家",
        "heritage_expert": "传承现状专家"
    }
    return types.get(agent_name, "未知专家")


def detect_gaps_node(state: WorkflowState) -> WorkflowState:
    """
    知识缺口检测节点 - 检测知识库中的空白
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        question = state["question"]
        fused_content = state.get("fused_content", "")
        
        logger.info("检测知识缺口...")
        
        # 初始化缺口检测器
        gap_detector = KnowledgeGapDetector()
        
        # 获取检索到的文档
        retriever = MultiSourceRetriever()
        docs = retriever.retrieve(question, top_k=5)
        
        # 检测缺口
        gap_result = gap_detector.detect(question, docs)
        
        # 更新状态
        state["gap_detection"] = gap_result.model_dump()
        state["has_gaps"] = not gap_result.can_answer
        
        # 生成缺口报告
        if gap_result.coverage_level != "sufficient":
            state["gap_report"] = gap_detector.generate_gap_report(question, gap_result)
        
        logger.info(f"缺口检测完成: {gap_result.coverage_level}")
        
    except Exception as e:
        logger.error(f"缺口检测失败: {e}")
        state["errors"].append(f"缺口检测错误: {str(e)}")
    
    return state


def generate_response_node(state: WorkflowState) -> WorkflowState:
    """
    响应生成节点 - 根据用户画像生成最终响应
    
    Args:
        state: 当前状态
    
    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        fused_content = state.get("fused_content", "")
        user_profile = state.get("user_profile", "curious")
        include_narrative = state.get("include_narrative", False)
        question = state.get("question", "")
        
        logger.info(f"生成响应 (profile={user_profile}, narrative={include_narrative})")
        
        # 多粒度适配
        granularity = GranularityController()
        adapted = granularity.adapt_content(
            fused_content,
            user_profile,
            question
        )
        
        adapted_content = adapted.get("content", fused_content)
        
        # 叙事模式处理
        if include_narrative:
            narrative_gen = NarrativeGenerator()
            
            # 识别技艺名称
            craft_name = None
            for cn in ["景泰蓝", "苏绣", "龙泉青瓷", "宜兴紫砂", "芜湖铁画", "蜀锦"]:
                if cn in question or cn in adapted_content:
                    craft_name = cn
                    break
            
            adapted_content = narrative_gen.switch_narrative_mode(
                adapted_content,
                craft_name,
                mode="narrative"
            )
        
        # 添加缺口报告
        gap_report = state.get("gap_report", "")
        if gap_report:
            adapted_content = f"{adapted_content}\n\n{gap_report}"
        
        state["adapted_content"] = adapted_content
        state["final_response"] = adapted_content
        
        logger.info("响应生成完成")
        
    except Exception as e:
        logger.error(f"响应生成失败: {e}")
        state["errors"].append(f"响应生成错误: {str(e)}")
        # 降级处理
        state["final_response"] = state.get("fused_content", "处理过程中出现错误。")
    
    return state


def should_include_narrative(state: WorkflowState) -> Literal["narrative", "standard"]:
    """
    条件判断：是否使用叙事模式
    
    Args:
        state: 当前状态
    
    Returns:
        str: "narrative" 或 "standard"
    """
    if state.get("include_narrative", False):
        return "narrative"
    return "standard"


def should_detect_gaps(state: WorkflowState) -> Literal["detect_gaps", "skip_gaps"]:
    """
    条件判断：是否进行缺口检测
    
    Args:
        state: 当前状态
    
    Returns:
        str: "detect_gaps" 或 "skip_gaps"
    """
    # 复杂问题进行缺口检测
    if state.get("complexity") == "complex":
        return "detect_gaps"
    return "skip_gaps"


def has_expert_responses(state: WorkflowState) -> Literal["fuse", "error"]:
    """
    条件判断：是否有专家响应
    
    Args:
        state: 当前状态
    
    Returns:
        str: "fuse" 或 "error"
    """
    responses = state.get("expert_responses", {})
    success_count = sum(1 for r in responses.values() if r.get("success", False))
    
    if success_count > 0:
        return "fuse"
    return "error"


# 节点映射表
NODES = {
    "analyze_question": analyze_question_node,
    "dispatch_to_experts": dispatch_to_experts_node,
    "collect_responses": collect_expert_responses_node,
    "fuse_knowledge": fuse_knowledge_node,
    "detect_gaps": detect_gaps_node,
    "generate_response": generate_response_node,
}


def get_node(name: str) -> Callable:
    """获取指定名称的节点"""
    return NODES.get(name, analyze_question_node)
