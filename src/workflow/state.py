"""
工作流状态定义 - LangGraph状态模型
"""

from typing import Dict, List, Optional, Any, TypedDict, Literal
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Agent响应模型"""
    agent_name: str = Field(description="Agent名称")
    content: str = Field(description="响应内容")
    success: bool = Field(description="是否成功")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class KnowledgeGap(BaseModel):
    """知识缺口模型"""
    aspect: str = Field(description="缺口方面")
    description: str = Field(description="缺口描述")
    suggestion: str = Field(description="补充建议")
    severity: str = Field(default="medium", description="严重程度")


class WorkflowState(TypedDict):
    """
    LangGraph工作流状态定义
    
    包含问答流程中的所有状态信息：
    - 用户输入
    - 中间结果
    - 最终输出
    """
    
    # === 用户输入 ===
    question: str = Field(default="", description="用户问题")
    user_profile: str = Field(default="curious", description="用户画像")
    thread_id: Optional[str] = Field(default=None, description="会话线程ID（v1.5 MySQL 会话标识）")
    conversation_context: str = Field(default="", description="同一会话的近期问答上下文")
    memory_preferences: Dict[str, Any] = Field(default_factory=dict, description="用户已学习偏好")
    
    # === 问题分析 ===
    question_analysis: Optional[Dict[str, Any]] = Field(default=None, description="问题分析结果")
    required_experts: List[str] = Field(default_factory=list, description="需要的专家Agent")
    key_entities: List[str] = Field(default_factory=list, description="识别的关键实体")
    complexity: str = Field(default="medium", description="问题复杂度")
    route: Dict[str, Any] = Field(default_factory=dict, description="v1.6 结构化执行路线")

    # === 查询重写（v1.4 接线：改写后的检索 query 供 dispatch / detect_gaps 复用） ===
    search_query: str = Field(default="", description="实际用于检索的 query（改写后；未改写时等于 question）")
    search_query_meta: Optional[Dict[str, Any]] = Field(default=None, description="改写元数据：original/rewritten/method/score，未改写为 None")

    # === Planner（v1.4：复杂问题的子方面大纲，只影响生成结构） ===
    plan: Optional[Dict[str, Any]] = Field(default=None, description="复杂问题的回答大纲（aspects/outline）；跳过或失败为 None")
    research_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="RAG 侧的精简证据")
    graph_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="本地知识图谱证据")
    workflow_trace: List[Dict[str, Any]] = Field(default_factory=list, description="面向用户的执行轨迹")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="最终回答采用的引用")

    # === Agent响应 ===
    expert_responses: Dict[str, AgentResponse] = Field(default_factory=dict, description="各专家Agent的响应")
    
    # === 层级聚合检索（P2优化①：技艺→工序→细节） ===
    retrieval_groups: Optional[Dict[str, Any]] = Field(default=None, description="层级聚合检索结果（按技艺分组的完整视图）")
    
    # === 知识融合 ===
    fused_content: str = Field(default="", description="融合后的内容")
    use_debate: bool = Field(default=False, description="是否使用辩论模式")
    debate_session: Optional[Dict[str, Any]] = Field(default=None, description="辩论会话结果")
    debate_mode: str = Field(default="", description="辩论模式")
    
    # === 知识缺口检测 ===
    gap_detection: Optional[Dict[str, Any]] = Field(default=None, description="缺口检测结果")
    has_gaps: bool = Field(default=False, description="是否存在知识缺口")
    gap_report: str = Field(default="", description="知识缺口报告")
    
    # === 多粒度控制 ===
    adapted_content: str = Field(default="", description="适配用户画像后的内容")
    include_narrative: bool = Field(default=False, description="是否使用传承人口吻")
    
    # === 最终输出 ===
    final_response: str = Field(default="", description="最终响应")
    source_agents: List[Dict[str, str]] = Field(default_factory=list, description="参与的Agent信息")
    
    # === 错误处理 ===
    errors: List[str] = Field(default_factory=list, description="处理过程中的错误")
    
    # === 元数据 ===
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(description="用户问题")
    user_profile: str = Field(default="curious", description="用户画像")
    include_narrative: bool = Field(default=False, description="是否使用传承人口吻")
    craft_filter: Optional[str] = Field(default=None, description="技艺过滤")


class QueryResponse(BaseModel):
    """查询响应模型"""
    question: str = Field(description="原始问题")
    answer: str = Field(description="回答内容")
    user_profile: str = Field(description="用户画像")
    source_agents: List[Dict[str, str]] = Field(description="参与的Agent")
    has_gaps: bool = Field(description="是否存在知识缺口")
    gap_report: str = Field(description="缺口报告")
    reading_time: int = Field(description="预估阅读时间(分钟)")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="回答采用的证据引用")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class GapReport(BaseModel):
    """缺口报告模型"""
    coverage_level: str = Field(description="覆盖程度")
    relevant_documents: int = Field(description="相关文档数")
    coverage_score: float = Field(description="覆盖评分")
    gaps: List[KnowledgeGap] = Field(description="缺口列表")
    can_answer: bool = Field(description="能否回答")
    suggestions: List[str] = Field(description="补充建议")


class GraphQueryResult(BaseModel):
    """图谱查询结果模型"""
    query: str = Field(description="查询内容")
    results: List[Dict[str, Any]] = Field(description="查询结果")
    graph_stats: Dict[str, Any] = Field(description="图谱统计")


def create_initial_state(
    question: str,
    user_profile: str = "curious",
    include_narrative: bool = False,
    thread_id: Optional[str] = None,
    conversation_context: str = "",
    memory_preferences: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    """
    创建初始工作流状态
    
    Args:
        question: 用户问题
        user_profile: 用户画像
        include_narrative: 是否使用叙事模式
    
    Returns:
        WorkflowState: 初始状态
    """
    return WorkflowState(
        question=question,
        user_profile=user_profile,
        thread_id=thread_id,
        conversation_context=conversation_context,
        memory_preferences=memory_preferences or {},
        include_narrative=include_narrative,
        question_analysis=None,
        required_experts=[],
        key_entities=[],
        complexity="medium",
        route={},
        search_query="",
        search_query_meta=None,
        plan=None,
        research_evidence=[],
        graph_evidence=[],
        workflow_trace=[],
        citations=[],
        expert_responses={},
        retrieval_groups=None,
        fused_content="",
        use_debate=False,
        debate_session=None,
        debate_mode="",
        gap_detection=None,
        has_gaps=False,
        gap_report="",
        adapted_content="",
        final_response="",
        source_agents=[],
        errors=[],
        metadata={}
    )


def state_to_response(state: WorkflowState) -> QueryResponse:
    """
    将状态转换为API响应
    
    Args:
        state: 工作流状态
    
    Returns:
        QueryResponse: API响应
    """
    # 估算阅读时间
    char_count = len(state.get("final_response", ""))
    reading_time = max(1, char_count // 400)
    
    metadata = dict(state.get("metadata", {}))
    metadata["route"] = state.get("route", {})
    metadata["workflow_trace"] = state.get("workflow_trace", [])

    return QueryResponse(
        question=state.get("question", ""),
        answer=state.get("final_response", ""),
        user_profile=state.get("user_profile", "curious"),
        source_agents=state.get("source_agents", []),
        has_gaps=state.get("has_gaps", False),
        gap_report=state.get("gap_report", ""),
        reading_time=reading_time,
        citations=state.get("citations", []),
        metadata=metadata,
    )
