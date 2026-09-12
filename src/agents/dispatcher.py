"""
调度Agent - 负责分析问题、分配专家、融合回答
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage

from config import settings, get_llm_config
from src.utils.prompts import (
    DISPATCHER_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    get_question_analysis_prompt,
    get_question_plan_prompt,
    get_fusion_prompt,
)
from src.utils.llm import create_llm
from src.agents.registry import AgentRegistry, get_default_agent_registry

logger = logging.getLogger(__name__)


class QuestionAnalysis(BaseModel):
    """问题分析结果模型"""
    intent_analysis: str = Field(description="问题意图的详细分析")
    required_experts: List[str] = Field(description="需要的专家Agent列表")
    reasoning: str = Field(description="为什么需要这些专家的解释")
    key_entities: List[str] = Field(description="识别出的关键实体")
    complexity: str = Field(description="问题复杂度：simple/medium/complex")
    question_type: str = Field(default="open_ended", description="问题类型：factual/comparative/procedural/open_ended")
    execution_route: str = Field(default="rag", description="执行路线：rag/graph/hybrid")
    use_memory: bool = Field(default=False, description="是否使用会话记忆辅助理解")
    route_reason: str = Field(default="", description="面向用户的简短路由理由")


class QuestionPlan(BaseModel):
    """复杂问题的回答大纲（Planner 产物；只影响生成结构）"""
    aspects: List[str] = Field(description="必须覆盖的子方面（3-6 个），每个一句话概括")
    outline: str = Field(description="回答总纲：子方面的组织顺序说明")
    sub_questions: Optional[List[str]] = Field(default=None, description="预留：子问题检索（本版不使用）")


# 路由工具 schema（裸 dict 以固定工具名 route_question；字段约束内嵌，引导模型输出合法参数）
QUESTION_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "route_question",
        "description": "分析一条中国非遗相关的用户提问，决定需要哪些专家 Agent 参与回答，并给出意图、关键实体与复杂度。",
        "parameters": {
            "type": "object",
            "properties": {
                "intent_analysis": {"type": "string", "description": "问题意图的详细分析"},
                "required_experts": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["craft_expert", "history_expert", "heritage_expert"]},
                    "description": "需要参与的专家，限定三类：craft_expert / history_expert / heritage_expert",
                },
                "reasoning": {"type": "string", "description": "为什么需要这些专家的解释"},
                "key_entities": {"type": "array", "items": {"type": "string"}, "description": "识别出的关键实体（技艺名称、人物、地域、朝代等）"},
                "complexity": {"type": "string", "enum": ["simple", "medium", "complex"], "description": "问题复杂度：simple/medium/complex"},
                "question_type": {"type": "string", "enum": ["factual", "comparative", "procedural", "open_ended"], "description": "问题类型"},
                "execution_route": {"type": "string", "enum": ["rag", "graph", "hybrid"], "description": "执行路线"},
                "use_memory": {"type": "boolean", "description": "是否使用会话记忆辅助理解"},
                "route_reason": {"type": "string", "description": "面向用户的简短路由理由"},
            },
            "required": ["required_experts", "complexity"],
        },
    },
}


def build_question_analysis_tool(registry: AgentRegistry) -> dict:
    """Build the Router tool schema from the currently registered Agent IDs."""
    from copy import deepcopy

    tool = deepcopy(QUESTION_ANALYSIS_TOOL)
    items = tool["function"]["parameters"]["properties"]["required_experts"]["items"]
    items["enum"] = list(registry.ids)
    items["description"] = f"可参与的专家：{' / '.join(registry.ids)}"
    return tool


# Planner 工具 schema（裸 dict 以固定工具名 create_plan）
QUESTION_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "create_plan",
        "description": "为一个复杂的中国非遗相关问题制定回答大纲：拆解出必须覆盖的子方面并给出组织顺序。",
        "parameters": {
            "type": "object",
            "properties": {
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 6,
                    "description": "必须覆盖的子方面，3-6 个，每个一句话概括",
                },
                "outline": {"type": "string", "description": "回答总纲：子方面的组织顺序与说明"},
            },
            "required": ["aspects", "outline"],
        },
    },
}


class DispatcherAgent:
    """
    调度Agent
    
    职责：
    1. 分析用户问题，判断意图和知识需求
    2. 决定需要哪些专家Agent参与
    3. 融合各专家的回答生成最终回复
    4. 标注回答来源
    """
    
    # 专家Agent映射
    EXPERT_MAPPING = {
        "craft_expert": "技艺知识Agent",
        "history_expert": "历史文化Agent",
        "heritage_expert": "传承现状Agent",
    }
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        debate_engine: Optional[Any] = None,
        agent_registry: Optional[AgentRegistry] = None,
    ):
        """
        初始化调度Agent
        
        Args:
            llm: 可选的语言模型实例，默认使用DeepSeek配置
            debate_engine: 可选的辩论引擎实例，用于多轮辩论融合
        """
        if llm is None:
            self.llm = create_llm()
        else:
            self.llm = llm

        self.system_prompt = DISPATCHER_SYSTEM_PROMPT
        self.debate_engine = debate_engine
        self.agent_registry = agent_registry or get_default_agent_registry()

        # 原生 function calling：绑定单一路由工具；不支持 bind_tools 的端点退回裸 llm
        self.router_llm = (
            self.llm.bind_tools([build_question_analysis_tool(self.agent_registry)])
            if hasattr(self.llm, "bind_tools")
            else self.llm
        )
        # Planner：绑定 create_plan 工具；不支持 bind_tools 的端点退回裸 llm
        self.planner_llm = self.llm.bind_tools([QUESTION_PLAN_TOOL]) if hasattr(self.llm, "bind_tools") else self.llm
    def analyze_question(self, question: str, conversation_context: Optional[str] = None) -> QuestionAnalysis:
        """
        分析用户问题，确定需要的专家Agent

        采用单次 LLM 调用、三分支降级：
        ① 原生 tool_calls（route_question）→ ② content 口述 JSON → ③ 关键词回退。
        任一支路失败都不会二次调用 LLM，保证旧行为不劣化。

        Args:
            question: 用户问题

        Returns:
            QuestionAnalysis: 问题分析结果
        """
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=get_question_analysis_prompt(question, conversation_context)),
            ]
            response = self.router_llm.invoke(messages)
        except Exception as e:
            logger.warning(f"路由调用失败，使用关键词回退: {e}")
            return self._fallback_analysis(question)

        # 分支一：原生工具调用
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls and tool_calls[0].get("name") == "route_question":
            args = tool_calls[0].get("args") or {}
            analysis = self._build_analysis(question, args)
            if analysis is not None:
                return analysis
            logger.warning("路由工具调用返回空专家列表，使用关键词回退")
            return self._fallback_analysis(question)

        # 分支二：模型口述 JSON 到 content（未触发/不支持工具调用时）
        content = getattr(response, "content", None)
        if content:
            analysis = self._parse_content_analysis(question, str(content))
            if analysis is not None:
                return analysis

        # 分支三：全部分支失败
        logger.warning("路由无法解析 LLM 输出，使用关键词回退")
        return self._fallback_analysis(question)

    def _parse_content_analysis(self, question: str, content: str) -> Optional[QuestionAnalysis]:
        """
        从 LLM 的 content 文本解析 JSON 分析结果（兼容 markdown 代码块）。
        解析/结构非法返回 None（由调用方决定降级路径）。
        """
        text = content.strip()
        try:
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            data = json.loads(text)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return self._build_analysis(question, data)

    def _build_analysis(self, question: str, data: dict) -> Optional[QuestionAnalysis]:
        """
        把 LLM 返回的 args/JSON 清洗为 QuestionAnalysis。
        清洗后 required_experts 为空返回 None（触发关键词回退）；complexity 非法时按专家数回推。
        """
        required = self._normalize_experts(data.get("required_experts"))
        if not required:
            return None
        complexity = str(data.get("complexity", "") or "")
        if complexity not in ("simple", "medium", "complex"):
            complexity = {1: "simple", 2: "medium"}.get(len(required), "complex")
        key_entities = data.get("key_entities") or []
        question_type = str(data.get("question_type", "open_ended") or "open_ended")
        if question_type not in {"factual", "comparative", "procedural", "open_ended"}:
            question_type = "open_ended"
        execution_route = str(data.get("execution_route", "rag") or "rag")
        if execution_route not in {"rag", "graph", "hybrid"}:
            execution_route = "rag"
        return QuestionAnalysis(
            intent_analysis=str(data.get("intent_analysis", "") or ""),
            required_experts=required,
            reasoning=str(data.get("reasoning", "") or ""),
            key_entities=[str(e) for e in key_entities if e],
            complexity=complexity,
            question_type=question_type,
            execution_route=execution_route,
            use_memory=bool(data.get("use_memory", False)),
            route_reason=str(data.get("route_reason", "") or ""),
        )

    def _normalize_experts(self, required) -> List[str]:
        """白名单清洗：只保留当前注册的 Agent，去重且保持出现顺序。"""
        return [definition.id for definition in self.agent_registry.resolve(required or [])]
    
    def _fallback_analysis(self, question: str) -> QuestionAnalysis:
        """
        备用分析逻辑：当LLM分析失败时使用关键词匹配
        
        Args:
            question: 用户问题
        
        Returns:
            QuestionAnalysis: 基础分析结果
        """
        # 关键词匹配规则
        craft_keywords = ["制作", "流程", "工艺", "材料", "工具", "步骤", "技术", "做法", "工序", "配方"]
        history_keywords = ["历史", "起源", "演变", "朝代", "文化", "意义", "传说", "来历", "发展"]
        heritage_keywords = ["传承", "传承人", "学习", "保护", "现状", "濒危", "非遗", "政策", "如何学", "哪里学"]
        
        required = []
        
        question_lower = question.lower()
        
        # 检查各类型关键词
        if any(kw in question for kw in craft_keywords):
            required.append("craft_expert")
        if any(kw in question for kw in history_keywords):
            required.append("history_expert")
        if any(kw in question for kw in heritage_keywords):
            required.append("heritage_expert")
        
        # 如果没有匹配任何类型，默认使用技艺专家
        if not required:
            required = ["craft_expert"]
        
        # 判断复杂度
        complexity = "simple" if len(required) == 1 else "medium" if len(required) == 2 else "complex"
        
        return QuestionAnalysis(
            intent_analysis=f"根据关键词分析，该问题涉及{'、'.join([self.EXPERT_MAPPING.get(e, e) for e in required])}领域",
            required_experts=required,
            reasoning=f"问题中检测到相关领域关键词，因此分配{len(required)}个专家Agent处理",
            key_entities=[],
            complexity=complexity
        )
    
    def plan_question(
        self,
        question: str,
        complexity: str = "",
        required_experts: Optional[List[str]] = None,
        key_entities: Optional[List[str]] = None,
    ) -> Optional[QuestionPlan]:
        """
        为复杂问题制定回答大纲（Planner，只影响生成结构）。

        采用单次 LLM 调用、三分支降级（与路由一致）：
        ① 原生 tool_calls（create_plan）→ ② content 口述 JSON → ③ 失败。
        任一支路失败都返回 None（None = 跳过 plan，最安全降级，不额外调 LLM）。

        Returns:
            Optional[QuestionPlan]: 生成成功返回大纲；失败/空子方面返回 None。
        """
        try:
            messages = [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=get_question_plan_prompt(
                    question, complexity or "medium", required_experts or [], key_entities or []
                )),
            ]
            response = self.planner_llm.invoke(messages)
        except Exception as e:
            logger.warning(f"Planner 调用失败，跳过 plan: {e}")
            return None

        # 分支一：原生工具调用
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls and tool_calls[0].get("name") == "create_plan":
            plan = self._build_plan(tool_calls[0].get("args") or {})
            if plan is not None:
                logger.info(f"Planner 生成 {len(plan.aspects)} 个子方面: {plan.aspects}")
                return plan
            logger.warning("Planner 工具调用返回空子方面，跳过 plan")
            return None

        # 分支二：模型口述 JSON 到 content
        content = getattr(response, "content", None)
        if content:
            plan = self._parse_content_plan(str(content))
            if plan is not None:
                logger.info(f"Planner(content) 生成 {len(plan.aspects)} 个子方面: {plan.aspects}")
                return plan

        # 分支三：全部失败 → 跳过 plan
        logger.warning("Planner 无法解析 LLM 输出，跳过 plan")
        return None

    @staticmethod
    def _parse_content_plan(content: str) -> Optional[QuestionPlan]:
        """从 content 文本解析 JSON 大纲（兼容 markdown 代码块）；结构非法返回 None。"""
        text = content.strip()
        try:
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            data = json.loads(text)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return DispatcherAgent._build_plan(data)

    @staticmethod
    def _build_plan(data: dict) -> Optional[QuestionPlan]:
        """把 LLM 返回的 args/JSON 清洗为 QuestionPlan；清洗后无有效子方面返回 None。"""
        raw_aspects = data.get("aspects") or []
        aspects = []
        for a in raw_aspects:
            a = str(a).strip()
            if a and a not in aspects:
                aspects.append(a)
        if not aspects:
            return None
        return QuestionPlan(
            aspects=aspects,
            outline=str(data.get("outline", "") or ""),
        )

    def fuse_responses(
        self,
        responses: Dict[str, str],
        question: str,
        user_profile: str = "curious",
        plan_outline: Optional[str] = None
    ) -> str:
        """
        融合多个专家的回答

        Args:
            responses: 专家回答字典 {agent_name: response}
            question: 原始问题
            user_profile: 用户画像类型
            plan_outline: 可选的 Planner 大纲文本（复杂问题）；非空时要求按大纲组织

        Returns:
            str: 融合后的回答
        """
        if not responses:
            return "抱歉，暂时没有找到相关信息。"

        # 如果只有一个专家回答，直接返回并添加标注
        if len(responses) == 1:
            agent_name, response = list(responses.items())[0]
            expert_display = self.EXPERT_MAPPING.get(agent_name, agent_name)
            return f"[{expert_display}]\n\n{response}"

        try:
            prompt = get_fusion_prompt(responses, question, plan_outline)

            response = self.llm.invoke(prompt)
            fused_content = response.content if hasattr(response, 'content') else str(response)

            return fused_content

        except Exception as e:
            logger.error(f"回答融合失败: {e}")
            # 降级处理：简单拼接
            return self._simple_fusion(responses)
    
    def _simple_fusion(self, responses: Dict[str, str]) -> str:
        """
        简单融合策略：按固定顺序拼接
        
        Args:
            responses: 专家回答字典
        
        Returns:
            str: 拼接后的回答
        """
        # 按专家优先级排序
        priority = ["craft_expert", "history_expert", "heritage_expert"]
        
        parts = []
        for expert in priority:
            if expert in responses:
                expert_display = self.EXPERT_MAPPING.get(expert, expert)
                parts.append(f"[{expert_display}]\n\n{responses[expert]}\n")
        
        return "\n".join(parts)
    def _get_agent_type(self, agent_name: str) -> str:
        """获取Agent类型描述"""
        types = {
            "craft_expert": "技艺知识专家",
            "history_expert": "历史文化专家",
            "heritage_expert": "传承现状专家"
        }
        return types.get(agent_name, "未知专家")
    
    def fuse_with_debate(
        # ⚠️ TODO(2026-08-15): 当前未接线，仅供后续功能扩展
        self,
        responses: Dict[str, str],
        question: str,
        analysis: Dict[str, Any],
        agents: Optional[Dict[str, Any]] = None,
        user_profile: str = "curious"
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        使用辩论引擎融合回答（如果适合辩论）
        
        Args:
            responses: 专家回答字典 {agent_name: response}
            question: 原始问题
            analysis: 问题分析结果
            agents: 可选的Agent实例字典
            user_profile: 用户画像类型
        
        Returns:
            Tuple[str, Optional[Dict]]: (融合结果, 辩论会话字典或None)
        """
        # 如果没有辩论引擎，降级到普通融合
        if self.debate_engine is None:
            return self.fuse_responses(responses, question, user_profile), None
        
        # 判断是否应该使用辩论模式
        should_debate, mode = self.debate_engine.should_debate(question, analysis)
        
        if not should_debate:
            return self.fuse_responses(responses, question, user_profile), None
        
        logger.info(f"触发辩论模式: {mode}")
        
        try:
            # 运行完整辩论流程
            debate_session = self.debate_engine.run_full_debate(
                question=question,
                mode=mode,
                context={"analysis": analysis, "initial_responses": responses}
            )
            
            # 返回综合结果和辩论会话
            return debate_session.final_synthesis, debate_session.to_dict()
            
        except Exception as e:
            logger.error(f"辩论融合失败，降级到普通融合: {e}")
            return self.fuse_responses(responses, question, user_profile), None

    def should_trigger_debate(
        self,
        question: str,
        analysis: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        判断是否应该触发辩论
        
        Args:
            question: 用户问题
            analysis: 问题分析结果
        
        Returns:
            Tuple[bool, str]: (是否触发, 辩论模式)
        """
        if self.debate_engine is None:
            return False, ""
        
        return self.debate_engine.should_debate(question, analysis)
