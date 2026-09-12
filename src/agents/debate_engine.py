"""
辩论引擎 - 支持Agent间的多轮对话与互相质疑补充
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Any, Tuple
from src.utils.llm import create_llm

from config import settings, get_llm_config
from src.utils.prompts import CRAFT_EXPERT_SYSTEM_PROMPT, HISTORY_EXPERT_SYSTEM_PROMPT, HERITAGE_EXPERT_SYSTEM_PROMPT
from src.retrieval.retriever import MultiSourceRetriever

logger = logging.getLogger(__name__)


@dataclass
class DebateRound:
    """辩论轮次数据类"""
    round_num: int                    # 轮次编号 (1, 2, 3...)
    agent_name: str                   # "craft_expert" / "history_expert" / "heritage_expert"
    agent_avatar: str                 # "🎨" / "📜" / "🏛️"
    role: str                         # "主答" / "补充" / "质疑" / "回应"
    content: str                      # 发言内容
    references: List[str] = field(default_factory=list)  # 引用的知识来源


@dataclass
class DebateSession:
    """辩论会话数据类"""
    question: str                      # 原始问题
    debate_mode: str                   # "progressive" / "parallel" / "multi_perspective"
    rounds: List[DebateRound] = field(default_factory=list)
    final_synthesis: str = ""          # 最终综合
    key_insights: List[str] = field(default_factory=list)  # 关键洞见

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "question": self.question,
            "debate_mode": self.debate_mode,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "agent_name": r.agent_name,
                    "agent_avatar": r.agent_avatar,
                    "role": r.role,
                    "content": r.content,
                    "references": r.references
                }
                for r in self.rounds
            ],
            "final_synthesis": self.final_synthesis,
            "key_insights": self.key_insights
        }


@dataclass(frozen=True)
class CollaborationAction:
    """One runtime-planned, user-visible message between two participating Agents."""

    from_agent: str
    to_agent: str
    kind: str


@dataclass(frozen=True)
class CollaborationMessage:
    """A short, user-safe representation of one completed collaboration action."""

    from_agent: str
    to_agent: str
    kind: str
    summary: str


@dataclass
class DynamicCollaborationResult:
    """Revised expert responses plus visible messages and safe fallback metadata."""

    responses: Dict[str, str]
    messages: List[CollaborationMessage] = field(default_factory=list)
    fallback_agents: List[str] = field(default_factory=list)


def build_collaboration_plan(
    participants: List[str], *, max_messages: int
) -> List[CollaborationAction]:
    """Create a bounded plan from the actual Router-selected participants.

    The plan contains no expert-specific ordering; it only preserves Router order.
    """
    ordered = list(dict.fromkeys(participants))
    if len(ordered) < 2 or max_messages <= 0:
        return []

    actions: List[CollaborationAction] = [
        CollaborationAction(ordered[0], ordered[1], "challenge"),
        CollaborationAction(ordered[1], ordered[0], "response"),
    ]
    for participant in ordered[2:]:
        actions.extend(
            (
                CollaborationAction(participant, ordered[0], "supplement"),
                CollaborationAction(ordered[0], participant, "agree"),
            )
        )
    return actions[:max_messages]


def _user_safe_summary(content: Any, limit: int = 240) -> str:
    text = " ".join(str(content or "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def run_dynamic_collaboration(
    *,
    question: str,
    initial_responses: Dict[str, str],
    agents: Dict[str, Any],
    max_messages: int,
    on_message: Optional[Callable[[CollaborationMessage], None]] = None,
) -> DynamicCollaborationResult:
    """Let the Router-selected Agents challenge or extend existing answers.

    This function deliberately receives existing answers instead of a Retriever, so
    collaboration cannot create another retrieval pass.
    """
    responses = dict(initial_responses)
    result = DynamicCollaborationResult(responses=responses)
    for action in build_collaboration_plan(list(responses), max_messages=max_messages):
        agent = agents.get(action.from_agent)
        llm = getattr(agent, "llm", None)
        if llm is None:
            result.fallback_agents.append(action.from_agent)
            continue

        prompt = (
            f"用户问题：{question}\n"
            f"你的已有回答：{responses.get(action.from_agent, '')}\n"
            f"对方（{action.to_agent}）的回答：{responses.get(action.to_agent, '')}\n"
            f"协作动作：{action.kind}。请只补充、质疑或回应可由已有资料支持的内容，"
            "不要编造来源，并给出简短的修订回答。"
        )
        try:
            response = llm.invoke(prompt)
            content = getattr(response, "content", response)
            text = str(content or "").strip()
            if not text:
                raise ValueError("协作 Agent 返回空内容")
            responses[action.from_agent] = text
            message = CollaborationMessage(
                from_agent=action.from_agent,
                to_agent=action.to_agent,
                kind=action.kind,
                summary=_user_safe_summary(text),
            )
            result.messages.append(message)
            if on_message is not None:
                on_message(message)
        except Exception as exc:
            logger.warning("协作 Agent %s 失败，降级到首轮回答：%s", action.from_agent, exc)
            result.fallback_agents.append(action.from_agent)
    return result


class DebateEngine:
    """
    辩论引擎 - 支持多智能体多轮辩论
    
    功能：
    1. 判断是否触发辩论及辩论模式
    2. 执行多轮辩论
    3. 提取关键洞见
    4. 综合辩论结果
    """
    
    # Agent信息映射
    AGENT_INFO = {
        "craft_expert": {
            "avatar": "🎨",
            "system_prompt": CRAFT_EXPERT_SYSTEM_PROMPT,
            "display_name": "技艺知识专家",
            "focus": "工艺流程、材料特性、工具使用、技术要点"
        },
        "history_expert": {
            "avatar": "📜",
            "system_prompt": HISTORY_EXPERT_SYSTEM_PROMPT,
            "display_name": "历史文化专家",
            "focus": "起源考证、演变历程、文化意义、地域特色"
        },
        "heritage_expert": {
            "avatar": "🏛️",
            "system_prompt": HERITAGE_EXPERT_SYSTEM_PROMPT,
            "display_name": "传承现状专家",
            "focus": "传承人信息、濒危程度、保护政策、学习途径"
        }
    }
    
    def __init__(
        self,
        agents: Dict[str, Any],
        llm: Optional[Any] = None
    ):
        """
        初始化辩论引擎
        
        Args:
            agents: 三个Agent实例字典 {"craft_expert": ..., "history_expert": ..., "heritage_expert": ...}
            llm: 可选的语言模型实例
        """
        self.agents = agents
        
        if llm is None:
            self.llm = create_llm()
        else:
            self.llm = llm
        
        self.retriever = MultiSourceRetriever()
    
    def should_debate(self, question: str, analysis: dict) -> Tuple[bool, str]:
        """
        判断是否触发辩论及辩论模式
        
        Args:
            question: 用户问题
            analysis: 问题分析结果
        
        Returns:
            Tuple[bool, str]: (是否触发辩论, 辩论模式)
                - 模式: "progressive" / "parallel" / "multi_perspective" / ""
        """
        # P1优化：辩论总开关——关闭后直接降级为普通融合，不触发任何辩论
        if not settings.debate_enabled:
            logger.info("辩论已关闭（debate_enabled=False），降级为普通融合")
            return False, ""

        required_experts = analysis.get("required_experts", [])
        complexity = analysis.get("complexity", "medium")
        question_lower = question.lower()
        
        # 简单事实查询不触发辩论
        simple_keywords = ["是什么", "叫什么", "有多少", "哪个朝代", "在哪里"]
        if all(kw not in question_lower for kw in ["为什么", "如何", "怎么", "怎么样", "原因", "分析", "比较"]):
            if len(required_experts) == 1 and complexity == "simple":
                return False, ""
        
        # 判断辩论模式
        
        # 1. 递进辩论模式：单一技艺 + "为什么"类问题
        #    例："景泰蓝为什么能成为国宝级非遗？"
        why_keywords = ["为什么", "原因", "为何", "分析", "道理"]
        if len(required_experts) >= 1 and any(kw in question_lower for kw in why_keywords):
            return True, "progressive"
        
        # 2. 并列辩论模式：多个技艺比较
        #    例："景泰蓝和苏绣有什么区别？"
        craft_names = ["景泰蓝", "苏绣", "龙泉青瓷", "宜兴紫砂", "芜湖铁画", "蜀锦"]
        craft_count = sum(1 for craft in craft_names if craft in question)
        if craft_count >= 2:
            return True, "parallel"
        
        # 3. 多视角辩论模式：技艺传承/困境类问题
        #    例："苏绣的传承面临哪些挑战？"
        heritage_keywords = ["传承", "困境", "挑战", "危机", "濒危", "保护", "发展"]
        if any(kw in question_lower for kw in heritage_keywords) and len(required_experts) >= 2:
            return True, "multi_perspective"
        
        # 4. 复杂问题触发多视角辩论
        if complexity == "complex" and len(required_experts) >= 2:
            return True, "multi_perspective"
        
        # 默认不触发
        return False, ""
    
    def run_debate(
        self,
        question: str,
        mode: str,
        context: Optional[Dict[str, Any]] = None,
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> DebateSession:
        """
        执行辩论
        
        Args:
            question: 用户问题
            mode: 辩论模式 ("progressive" / "parallel" / "multi_perspective")
            context: 上下文信息
            shared_docs: 共享检索文档（P1优化：整个辩论流程只检索一次，各轮复用）
        
        Returns:
            DebateSession: 辩论会话结果
        """
        context = context or {}
        
        if mode == "progressive":
            return self._run_progressive_debate(question, context, shared_docs)
        elif mode == "parallel":
            return self._run_parallel_debate(question, context, shared_docs)
        elif mode == "multi_perspective":
            return self._run_multi_perspective_debate(question, context, shared_docs)
        else:
            # 降级：单轮简单回答
            return self._run_simple_session(question, context, shared_docs)
    
    def _run_progressive_debate(
        self,
        question: str,
        context: Dict[str, Any],
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> DebateSession:
        """
        递进辩论模式：层层深入
        Round1: 主答(craft) → Round2: 补充(heritage) → Round3: 历史视角(history)
        P1优化：由4轮减为3轮（去掉Round4回应），轮次受 settings.debate_max_rounds 约束
        """
        session = DebateSession(question=question, debate_mode="progressive")
        
        # 准备辩论历史（传递给后续Agent）
        debate_history = []
        
        # Round 1: 技艺专家主答
        logger.info("递进辩论 Round 1: 技艺专家主答")
        content, refs = self._call_agent(
            "craft_expert",
            question,
            self._build_round_prompt(
                question,
                "craft_expert",
                role="主答",
                context=context,
                history=None,
                shared_docs=shared_docs
            )
        )
        round1 = DebateRound(
            round_num=1,
            agent_name="craft_expert",
            agent_avatar="🎨",
            role="主答",
            content=content,
            references=refs
        )
        session.rounds.append(round1)
        debate_history.append(("craft_expert", "主答", content))
        
        # P1优化：轮次上限约束
        if len(session.rounds) >= settings.debate_max_rounds:
            return session
        
        # Round 2: 传承专家补充
        logger.info("递进辩论 Round 2: 传承专家补充")
        content, refs = self._call_agent(
            "heritage_expert",
            question,
            self._build_round_prompt(
                question,
                "heritage_expert",
                role="补充",
                context=context,
                history=debate_history,
                shared_docs=shared_docs
            )
        )
        round2 = DebateRound(
            round_num=2,
            agent_name="heritage_expert",
            agent_avatar="🏛️",
            role="补充",
            content=content,
            references=refs
        )
        session.rounds.append(round2)
        debate_history.append(("heritage_expert", "补充", content))
        
        # P1优化：轮次上限约束
        if len(session.rounds) >= settings.debate_max_rounds:
            return session
        
        # Round 3: 历史专家视角
        logger.info("递进辩论 Round 3: 历史专家视角")
        content, refs = self._call_agent(
            "history_expert",
            question,
            self._build_round_prompt(
                question,
                "history_expert",
                role="深化",
                context=context,
                history=debate_history,
                shared_docs=shared_docs
            )
        )
        round3 = DebateRound(
            round_num=3,
            agent_name="history_expert",
            agent_avatar="📜",
            role="深化",
            content=content,
            references=refs
        )
        session.rounds.append(round3)
        debate_history.append(("history_expert", "深化", content))
        
        return session
    
    def _run_parallel_debate(
        self,
        question: str,
        context: Dict[str, Any],
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> DebateSession:
        """
        并列辩论模式：多技艺同时发言后交叉质疑
        Round1: 三个Agent同时发言 → Round2: 交叉质疑（仅保留 craft 质疑）
        P1优化：去掉 heritage 回应，轮次受 settings.debate_max_rounds 约束
        """
        session = DebateSession(question=question, debate_mode="parallel")
        
        debate_history = []
        
        # Round 1: 三个Agent同时发言
        logger.info("并列辩论 Round 1: 三专家同时发言")
        
        for i, (agent_name, agent_info) in enumerate(self.AGENT_INFO.items()):
            content, refs = self._call_agent(
                agent_name,
                question,
                self._build_round_prompt(
                    question,
                    agent_name,
                    role="并列发言",
                    context=context,
                    history=None,
                    parallel_mode=True,
                    shared_docs=shared_docs
                )
            )
            debate_round = DebateRound(
                round_num=1,
                agent_name=agent_name,
                agent_avatar=agent_info["avatar"],
                role="并列发言",
                content=content,
                references=refs
            )
            session.rounds.append(debate_round)
            debate_history.append((agent_name, "并列发言", content))
        
        # P1优化：轮次上限约束——若 max_rounds 不足以支撑 Round2 则提前结束
        if settings.debate_max_rounds < 2:
            return session
        
        # Round 2: 交叉质疑（仅保留 craft 质疑，去掉 heritage 回应）
        logger.info("并列辩论 Round 2: 交叉质疑（craft）")
        
        # 技艺专家质疑其他
        content, refs = self._call_agent(
            "craft_expert",
            question,
            self._build_cross_examination_prompt(question, debate_history, "craft_expert")
        )
        debate_round = DebateRound(
            round_num=2,
            agent_name="craft_expert",
            agent_avatar="🎨",
            role="质疑",
            content=content,
            references=refs
        )
        session.rounds.append(debate_round)
        debate_history.append(("craft_expert", "质疑", content))
        
        return session
    
    def _run_multi_perspective_debate(
        self,
        question: str,
        context: Dict[str, Any],
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> DebateSession:
        """
        多视角辩论模式：全面多角度讨论
        3个Agent各发言一轮（技艺/历史/传承视角）
        P1优化：由5轮减为3轮（去掉Round4质疑与Round5综合回应），轮次受 settings.debate_max_rounds 约束
        """
        session = DebateSession(question=question, debate_mode="multi_perspective")
        
        debate_history = []
        
        # Round 1: 技艺专家视角
        logger.info("多视角辩论 Round 1: 技艺专家视角")
        content, refs = self._call_agent(
            "craft_expert",
            question,
            self._build_round_prompt(
                question,
                "craft_expert",
                role="技艺视角",
                context=context,
                history=None,
                shared_docs=shared_docs
            )
        )
        round1 = DebateRound(
            round_num=1,
            agent_name="craft_expert",
            agent_avatar="🎨",
            role="技艺视角",
            content=content,
            references=refs
        )
        session.rounds.append(round1)
        debate_history.append(("craft_expert", "技艺视角", content))
        
        # P1优化：轮次上限约束
        if len(session.rounds) >= settings.debate_max_rounds:
            return session
        
        # Round 2: 历史专家视角
        logger.info("多视角辩论 Round 2: 历史专家视角")
        content, refs = self._call_agent(
            "history_expert",
            question,
            self._build_round_prompt(
                question,
                "history_expert",
                role="历史视角",
                context=context,
                history=debate_history,
                shared_docs=shared_docs
            )
        )
        round2 = DebateRound(
            round_num=2,
            agent_name="history_expert",
            agent_avatar="📜",
            role="历史视角",
            content=content,
            references=refs
        )
        session.rounds.append(round2)
        debate_history.append(("history_expert", "历史视角", content))
        
        # P1优化：轮次上限约束
        if len(session.rounds) >= settings.debate_max_rounds:
            return session
        
        # Round 3: 传承专家视角
        logger.info("多视角辩论 Round 3: 传承专家视角")
        content, refs = self._call_agent(
            "heritage_expert",
            question,
            self._build_round_prompt(
                question,
                "heritage_expert",
                role="传承视角",
                context=context,
                history=debate_history,
                shared_docs=shared_docs
            )
        )
        round3 = DebateRound(
            round_num=3,
            agent_name="heritage_expert",
            agent_avatar="🏛️",
            role="传承视角",
            content=content,
            references=refs
        )
        session.rounds.append(round3)
        debate_history.append(("heritage_expert", "传承视角", content))
        
        return session
    
    def _run_simple_session(
        self,
        question: str,
        context: Dict[str, Any],
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> DebateSession:
        """简单会话：单轮快速回答（降级方案）"""
        session = DebateSession(question=question, debate_mode="simple")
        
        content, refs = self._call_agent(
            "craft_expert",
            question,
            self._build_round_prompt(
                question,
                "craft_expert",
                role="主答",
                context=context,
                history=None,
                shared_docs=shared_docs
            )
        )
        
        debate_round = DebateRound(
            round_num=1,
            agent_name="craft_expert",
            agent_avatar="🎨",
            role="主答",
            content=content,
            references=refs
        )
        session.rounds.append(debate_round)
        
        return session
    
    def _call_agent(
        self,
        agent_name: str,
        question: str,
        prompt: str
    ) -> Tuple[str, List[str]]:
        """
        调用Agent生成回答
        
        Args:
            agent_name: Agent名称
            question: 原始问题
            prompt: 构建好的Prompt
        
        Returns:
            Tuple[str, List[str]]: (回答内容, 引用来源列表)
        """
        try:
            agent = self.agents.get(agent_name)
            if agent is None:
                # 降级：直接使用LLM
                response = self.llm.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
                return content, []
            
            # 使用Agent自己的LLM
            if hasattr(agent, 'llm') and agent.llm is not None:
                response = agent.llm.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
            else:
                response = self.llm.invoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取引用（如果有）
            refs = self._extract_references(content)
            
            return content, refs
            
        except Exception as e:
            logger.error(f"Agent {agent_name} 调用失败: {e}")
            return f"[{agent_name}响应失败]", []
    
    def _extract_references(self, content: str) -> List[str]:
        """从回答中提取引用来源"""
        refs = []
        # 简单实现：查找可能的来源标记
        import re
        patterns = [
            r'来源[:：]\s*(.+?)(?:\n|$)',
            r'出自[:：]\s*(.+?)(?:\n|$)',
            r'参考[:：]\s*(.+?)(?:\n|$)'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content)
            refs.extend(matches)
        return refs[:5]  # 最多5个引用
    
    def _build_round_prompt(
        self,
        question: str,
        agent_name: str,
        role: str,
        context: Dict[str, Any],
        history: Optional[List[Tuple[str, str, str]]] = None,
        parallel_mode: bool = False,
        shared_docs: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        构建辩论轮次Prompt
        
        Args:
            question: 用户问题
            agent_name: 当前Agent名称
            role: 当前角色（主答/补充/质疑/回应）
            context: 上下文信息
            history: 辩论历史 [(agent, role, content), ...]
            parallel_mode: 是否为并列发言模式
            shared_docs: 共享检索文档（P1优化：有则复用，避免每轮重复检索）
        
        Returns:
            str: 构建好的Prompt
        """
        agent_info = self.AGENT_INFO.get(agent_name, {})
        system_prompt = agent_info.get("system_prompt", "")
        
        # 检索相关文档（P1优化：优先复用 run_full_debate 检索一次的 shared_docs，无则自行检索以向后兼容）
        retrieved_docs = []
        if shared_docs:
            retrieved_docs = [r.get("content", "")[:200] for r in shared_docs if r.get("content")]
        else:
            try:
                results = self.retriever.retrieve(question, top_k=settings.top_k)
                retrieved_docs = [r.get("content", "")[:200] for r in results if r.get("content")]
            except Exception:
                pass
        
        prompt_parts = [
            f"# {agent_info.get('display_name', agent_name)} 辩论发言",
            f"## 当前角色: {role}",
            f"## 原始问题\n{question}",
            f"## 你的专业领域\n{agent_info.get('focus', '')}",
        ]
        
        # 添加辩论历史（P1优化：每段截断到 settings.debate_history_chars，防止上下文随轮次无限增长）
        if history:
            prompt_parts.append("\n## 之前的辩论内容\n")
            for prev_agent, prev_role, prev_content in history:
                prev_info = self.AGENT_INFO.get(prev_agent, {})
                if len(prev_content) > settings.debate_history_chars:
                    prev_content = prev_content[:settings.debate_history_chars] + "…"
                prompt_parts.append(
                    f"【{prev_info.get('display_name', prev_agent)} - {prev_role}】\n{prev_content}\n"
                )
            prompt_parts.append(f"\n## 你的任务\n作为{agent_info.get('display_name', agent_name)}，请基于以上辩论内容，以【{role}】的身份继续讨论：")
            if role == "补充":
                prompt_parts.append("\n- 补充之前未涉及的重要观点")
                prompt_parts.append("- 从你的专业角度深化讨论")
            elif role == "深化" or role == "历史视角":
                prompt_parts.append("\n- 提供历史维度的深度分析")
                prompt_parts.append("- 揭示问题的历史渊源和演变")
            elif role == "回应" or role == "回应质疑" or role == "综合回应":
                prompt_parts.append("\n- 回应之前的讨论观点")
                prompt_parts.append("- 综合各方观点给出综合判断")
        else:
            prompt_parts.append(f"\n## 你的任务\n作为{agent_info.get('display_name', agent_name)}，请以【{role}】的身份回答问题：")
        
        # 添加文档参考
        if retrieved_docs:
            prompt_parts.append("\n## 参考资料\n")
            for i, doc in enumerate(retrieved_docs[:3], 1):
                prompt_parts.append(f"{i}. {doc}...")
        
        prompt_parts.append("\n## 要求\n")
        prompt_parts.append("1. 内容要有深度和专业性")
        prompt_parts.append("2. 适当引用之前的讨论内容进行互动")
        prompt_parts.append("3. 引用来源请标注")
        
        if parallel_mode:
            prompt_parts.append("4. 简洁精炼，适合并列呈现")
        else:
            prompt_parts.append("4. 可以展开深入讨论")
        
        # P1优化：回答字数限制——控制单轮输出体积，减少Token消耗
        prompt_parts.append(f"5. 回答控制在 {settings.expert_answer_max_chars} 字以内，精炼直接")
        
        return "\n".join(prompt_parts)
    
    def _build_cross_examination_prompt(
        self,
        question: str,
        history: List[Tuple[str, str, str]],
        from_agent: str
    ) -> str:
        """
        构建交叉质疑Prompt
        
        Args:
            question: 用户问题
            history: 辩论历史
            from_agent: 发起质疑的Agent
        
        Returns:
            str: 质疑Prompt
        """
        prompt_parts = [
            f"# 交叉质疑环节",
            f"## 原始问题\n{question}",
            "\n## 当前辩论内容\n",
        ]
        
        for agent, role, content in history:
            agent_info = self.AGENT_INFO.get(agent, {})
            prompt_parts.append(
                f"【{agent_info.get('display_name', agent)} - {role}】\n{content[:500]}...\n"
            )
        
        prompt_parts.append(
            f"\n## 你的任务\n作为{self.AGENT_INFO.get(from_agent, {}).get('display_name', from_agent)}，"
            "请基于以上讨论提出质疑和问题：\n"
            "- 指出其他观点中可能存在的不足或争议\n"
            "- 提出你认为需要进一步澄清的问题\n"
            "- 从你的专业视角提出不同看法\n"
        )
        
        return "\n".join(prompt_parts)
    
    def synthesize(self, session: DebateSession) -> str:
        """
        综合辩论结果
        
        Args:
            session: 辩论会话
        
        Returns:
            str: 综合后的回答
        """
        if not session.rounds:
            return "无法生成回答。"
        
        # 构建综合Prompt
        prompt_parts = [
            "# 辩论综合总结",
            f"## 原始问题\n{session.question}",
            f"## 辩论模式\n{session.debate_mode}",
            "\n## 辩论过程\n",
        ]
        
        for round_data in session.rounds:
            agent_info = self.AGENT_INFO.get(round_data.agent_name, {})
            prompt_parts.append(
                f"【{agent_info.get('display_name', round_data.agent_name)} - {round_data.role}】\n"
                f"{round_data.content}\n"
            )
        
        prompt_parts.append(
            "\n## 综合要求\n"
            "请将以上辩论内容整合成一篇连贯、专业的回答：\n"
            "1. 保留各专家的核心观点\n"
            "2. 消除矛盾，达成共识\n"
            "3. 突出关键洞见\n"
            "4. 回答要有逻辑性和完整性\n"
            "5. 标注信息来源"
        )
        
        prompt = "\n".join(prompt_parts)
        
        try:
            response = self.llm.invoke(prompt)
            synthesis = response.content if hasattr(response, 'content') else str(response)
            session.final_synthesis = synthesis
            return synthesis
        except Exception as e:
            logger.error(f"综合辩论结果失败: {e}")
            # 降级：拼接所有内容
            fallback = "\n\n".join([r.content for r in session.rounds])
            session.final_synthesis = fallback
            return fallback
    
    def _extract_insights(self, session: DebateSession) -> List[str]:
        """
        提取关键洞见
        
        Args:
            session: 辩论会话
        
        Returns:
            List[str]: 关键洞见列表
        """
        # 构建提取Prompt
        prompt = f"""# 提取关键洞见

## 原始问题
{session.question}

## 辩论内容摘要
"""
        for round_data in session.rounds:
            agent_info = self.AGENT_INFO.get(round_data.agent_name, {})
            prompt += f"\n{round_data.agent_name}({round_data.role}): {round_data.content[:300]}...\n"
        
        prompt += """
## 任务
请从以上辩论中提取3-5个关键洞见，以JSON数组格式输出：
```json
{
  "insights": ["洞见1", "洞见2", "洞见3"]
}
```

关键洞见标准：
- 具有深度和启发性
- 非显而易见
- 有实践指导价值
"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            # 清理markdown
            content = content.strip().strip("```").strip()
            
            data = json.loads(content)
            insights = data.get("insights", [])
            session.key_insights = insights
            return insights
        except Exception as e:
            logger.error(f"提取关键洞见失败: {e}")
            return []
    
    def run_full_debate(
        self,
        question: str,
        mode: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DebateSession:
        """
        运行完整辩论流程：执行辩论 → 提取洞见 → 综合结果
        
        P1优化：整个辩论流程只检索一次（shared_docs），各轮复用，
        避免每轮 Prompt 构建时重复检索（原实现每轮 top_k=5 检索一次）。
        
        Args:
            question: 用户问题
            mode: 辩论模式
            context: 上下文信息
        
        Returns:
            DebateSession: 完整的辩论会话（含综合和洞见）
        """
        # P1优化：检索复用——整个辩论流程只检索一次
        shared_docs: List[Dict[str, Any]] = []
        try:
            shared_docs = self.retriever.retrieve(question, top_k=settings.top_k)
        except Exception as e:
            logger.warning(f"辩论引擎检索失败，降级为无参考文档: {e}")
        
        session = self.run_debate(question, mode, context, shared_docs=shared_docs)
        self._extract_insights(session)
        self.synthesize(session)
        return session
