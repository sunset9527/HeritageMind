"""
工作流节点定义 - LangGraph各处理节点
"""

import logging
import time
from typing import Dict, Any, List, Literal, Callable, Optional
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.agents.dispatcher import DispatcherAgent
from src.agents.graph_agent import GraphAgent
from src.agents.craft_expert import CraftExpertAgent
from src.agents.history_expert import HistoryExpertAgent
from src.agents.heritage_expert import HeritageExpertAgent
from src.agents.debate_engine import DebateEngine
from src.knowledge.gap_detector import KnowledgeGapDetector
from src.knowledge.granularity import GranularityController
from src.knowledge.narrative import NarrativeGenerator
from src.retrieval.retriever import MultiSourceRetriever
from src.retrieval.query_rewriter import select_best_query
from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.workflow.state import WorkflowState, AgentResponse

logger = logging.getLogger(__name__)


def _apply_retrieval_query(state: WorkflowState, question: str) -> None:
    """把改写后的检索 query 写入 state（v1.4 接线，规则模式）。

    语义：
    - query_rewriting_enabled 关闭 → 不做任何改写，search_query 恒 = question；
    - 开启 → select_best_query 选最佳候选（无规则命中则等于原文）。
    改写只作用于检索 query；专家识别技艺名 / 生成回答仍用原始 question。
    """
    if not getattr(settings, "query_rewriting_enabled", True):
        state["search_query"] = question
        state["search_query_meta"] = None
        return
    try:
        conversation_context = state.get("conversation_context") or None
        best = (
            select_best_query(question, conversation_context=conversation_context)
            if conversation_context else select_best_query(question)
        )
    except Exception as e:
        logger.warning(f"检索 query 改写异常，回退原文: {e}")
        state["search_query"] = question
        state["search_query_meta"] = None
        return
    state["search_query"] = best.rewritten
    state["search_query_meta"] = {
        "original": best.original,
        "rewritten": best.rewritten,
        "method": best.method,
        "score": best.score,
    }
    if best.rewritten != question:
        logger.info(
            f"检索 query 改写: {question} -> {best.rewritten} "
            f"(method={best.method}, score={best.score})"
        )
    else:
        logger.debug(f"检索 query 无需改写: {question}")


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
        analysis = dispatcher.analyze_question(
            question, conversation_context=state.get("conversation_context") or None
        )
        
        # 更新状态
        state["question_analysis"] = {
            "intent": analysis.intent_analysis,
            "required_experts": analysis.required_experts,
            "reasoning": analysis.reasoning,
            "key_entities": analysis.key_entities,
            "complexity": analysis.complexity,
            "question_type": analysis.question_type,
            "execution_route": analysis.execution_route,
            "use_memory": analysis.use_memory,
            "route_reason": analysis.route_reason,
        }
        state["required_experts"] = analysis.required_experts
        state["key_entities"] = analysis.key_entities
        state["complexity"] = analysis.complexity
        state["route"] = {
            "question_type": analysis.question_type,
            "execution_route": analysis.execution_route,
            "use_memory": analysis.use_memory,
            "reason": analysis.route_reason,
        }
        
        logger.info(f"问题分析完成，需要专家: {analysis.required_experts}")
        
    except Exception as e:
        logger.error(f"问题分析失败: {e}")
        state["errors"].append(f"问题分析错误: {str(e)}")
        # 使用默认配置
        state["required_experts"] = ["craft_expert"]
    
    return state


def plan_question_node(state: WorkflowState) -> WorkflowState:
    """
    Planner 节点 - 为复杂问题制定回答大纲（只影响生成结构，不触发额外检索）

    Args:
        state: 当前状态

    Returns:
        WorkflowState: 更新后的状态
    """
    try:
        question = state["question"]
        dispatcher = DispatcherAgent()
        plan = dispatcher.plan_question(
            question=question,
            complexity=state.get("complexity", "medium"),
            required_experts=state.get("required_experts", []),
            key_entities=state.get("key_entities", []),
        )
        state["plan"] = plan.model_dump() if plan else None
        logger.info(f"Planner: plan={'生成' if plan else '跳过'}")
    except Exception as e:
        logger.warning(f"Planner 节点异常，跳过 plan: {e}")
        state["errors"].append(f"Planner 错误: {str(e)}")
        state["plan"] = None
    return state


def _plan_outline_text(state: WorkflowState) -> Optional[str]:
    """把 state['plan'] 渲染成注入融合/生成的大纲文本；无 plan 返回 None。"""
    plan = state.get("plan")
    if not plan:
        return None
    parts = []
    aspects = plan.get("aspects") or []
    if aspects:
        parts.append("子方面：")
        for i, a in enumerate(aspects, 1):
            parts.append(f"{i}. {a}")
    outline = plan.get("outline")
    if outline:
        parts.append(f"组织顺序：{outline}")
    text = "\n".join(parts).strip()
    return text or None


def should_plan(state: WorkflowState) -> Literal["plan", "skip_plan"]:
    """
    条件判断：是否执行 Planner（复杂问题分解）

    触发条件：planner_enabled 开启，且 复杂度为 complex 或 需 ≥2 个专家。
    未触发时走 skip_plan 直接进入专家分派（旧路径，无 plan 节点延迟）。

    Returns:
        str: "plan" 或 "skip_plan"
    """
    if not getattr(settings, "planner_enabled", True):
        return "skip_plan"
    complexity = state.get("complexity", "medium")
    expert_count = len(state.get("required_experts", []))
    if complexity == "complex" or expert_count >= 2:
        return "plan"
    return "skip_plan"


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

        # v1.4：查询重写接线 — 计算实际用于检索的 query（改写后 / 未改写恒等于 question）
        _apply_retrieval_query(state, question)
        sq = state.get("search_query") or question

        logger.info(f"分派给专家: {required_experts} (检索 query: {sq})")

        # 初始化检索器
        retriever = MultiSourceRetriever()

        # P2优化①：层级聚合检索（技艺→工序→细节），结果写入 state 供融合/生成阶段使用。
        # 检索一次、分组一次，不改变专家分派主流程；可配置关闭（craft_group_enabled）
        if getattr(settings, "craft_group_enabled", True):
            try:
                grouped = retriever.retrieve_grouped(
                    sq,
                    top_k=settings.top_k,
                    max_chars_per_group=getattr(settings, "craft_group_max_chars", 1500),
                )
                state["retrieval_groups"] = grouped
                logger.info(
                    f"层级聚合检索: {grouped['group_count']} 组 / {grouped['total_docs']} 篇，"
                    f"命中技艺 {grouped['matched_crafts']}"
                )
            except Exception as e:
                logger.warning(f"层级聚合检索失败（不影响主流程）: {e}")

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
                    result = agent.process(question, context, search_query=sq)

                    # P1优化：截断专家响应体积，控制后续融合阶段上下文长度
                    answer = result.get("answer", "")
                    if len(answer) > settings.expert_answer_max_chars:
                        answer = answer[:settings.expert_answer_max_chars] + "…"

                    responses[expert_name] = AgentResponse(
                        agent_name=expert_name,
                        content=answer,
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
                fused = dispatcher.fuse_responses(
                    response_dict, question, plan_outline=_plan_outline_text(state)
                )
                state["fused_content"] = fused
        else:
            # 普通融合模式
            logger.info("使用普通融合模式")
            state["use_debate"] = False
            fused = dispatcher.fuse_responses(
                response_dict, question, plan_outline=_plan_outline_text(state)
            )
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
        
        # 获取检索到的文档（复用 dispatch 阶段改写后的 query；未改写时恒等于 question）
        retriever = MultiSourceRetriever()
        docs = retriever.retrieve(state.get("search_query") or question, top_k=5)
        
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


def query_graph_node(state: WorkflowState) -> WorkflowState:
    """v1.6 图谱查询节点：只读查询本地知识图谱。"""
    started_at = time.perf_counter()
    route = state.get("route") or {}
    if route.get("execution_route") not in {"graph", "hybrid"}:
        state["workflow_trace"].append({
            "node": "query_graph",
            "status": "skipped",
            "elapsed_ms": 0,
            "message": "当前路线不需要知识图谱查询",
        })
        return state

    try:
        graph = HeritageKnowledgeGraph()
        if not graph.load_from_json():
            raise RuntimeError("本地知识图谱加载失败")
        result = GraphAgent(graph).research(
            state.get("question", ""), state.get("key_entities", [])
        )
        state["graph_evidence"] = result["evidence"]
        state["citations"].extend(
            {"title": item["title"], "source": item["source"]}
            for item in result["evidence"]
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        if result["success"]:
            state["workflow_trace"].append({
                "node": "query_graph",
                "status": "completed",
                "elapsed_ms": elapsed_ms,
                "message": f"本地知识图谱命中 {len(result['evidence'])} 条关系",
            })
        else:
            route["fallback_reason"] = result["reason"]
            state["route"] = route
            state["workflow_trace"].append({
                "node": "query_graph",
                "status": "fallback",
                "elapsed_ms": elapsed_ms,
                "message": result["reason"],
            })
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        route["fallback_reason"] = "本地知识图谱不可用"
        state["route"] = route
        state["errors"].append(f"图谱查询错误: {str(e)}")
        state["workflow_trace"].append({
            "node": "query_graph",
            "status": "fallback",
            "elapsed_ms": elapsed_ms,
            "message": "本地知识图谱不可用，已转为检索路线",
        })
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
        
        # 多粒度适配（v1.4：注入 Planner 大纲作为可选上下文，约束生成结构）
        granularity = GranularityController()
        response_context = {"plan": _plan_outline_text(state)}
        if state.get("conversation_context"):
            response_context["conversation_memory"] = state["conversation_context"]
        adapted = granularity.adapt_content(
            fused_content,
            user_profile,
            question,
            context=response_context,
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
            has_gaps = state.get("has_gaps", False)
            if has_gaps:
                # 严重缺口：报告放后面
                adapted_content = f"{adapted_content}\n\n---\n{gap_report}"
            else:
                # 轻度不足：只加一行提示，答案优先
                adapted_content = f"{adapted_content}\n\n> 💡 当前知识库对此问题覆盖有限，回答可能不够详尽。"
        
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
    "plan_question": plan_question_node,
    "dispatch_to_experts": dispatch_to_experts_node,
    "collect_responses": collect_expert_responses_node,
    "fuse_knowledge": fuse_knowledge_node,
    "detect_gaps": detect_gaps_node,
    "query_graph": query_graph_node,
    "generate_response": generate_response_node,
}


def get_node(name: str) -> Callable:
    """获取指定名称的节点"""
    return NODES.get(name, analyze_question_node)
