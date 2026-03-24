"""
调度Agent - 负责分析问题、分配专家、融合回答
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import settings, get_llm_config
from src.utils.prompts import DISPATCHER_SYSTEM_PROMPT, get_question_analysis_prompt, get_fusion_prompt

logger = logging.getLogger(__name__)


class QuestionAnalysis(BaseModel):
    """问题分析结果模型"""
    intent_analysis: str = Field(description="问题意图的详细分析")
    required_experts: List[str] = Field(description="需要的专家Agent列表")
    reasoning: str = Field(description="为什么需要这些专家的解释")
    key_entities: List[str] = Field(description="识别出的关键实体")
    complexity: str = Field(description="问题复杂度：simple/medium/complex")


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
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, debate_engine: Optional[Any] = None):
        """
        初始化调度Agent
        
        Args:
            llm: 可选的语言模型实例，默认使用DeepSeek配置
            debate_engine: 可选的辩论引擎实例，用于多轮辩论融合
        """
        if llm is None:
            llm_config = get_llm_config()
            self.llm = ChatOpenAI(
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                request_timeout=120,
                max_retries=1
            )
        else:
            self.llm = llm
        
        self.system_prompt = DISPATCHER_SYSTEM_PROMPT
        self.debate_engine = debate_engine
        
    def analyze_question(self, question: str) -> QuestionAnalysis:
        """
        分析用户问题，确定需要的专家Agent
        
        Args:
            question: 用户问题
        
        Returns:
            QuestionAnalysis: 问题分析结果
        """
        try:
            prompt = get_question_analysis_prompt(question)
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 尝试解析JSON响应
            # 提取JSON部分（处理可能的markdown代码块）
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            result = json.loads(content)

            required = result.get("required_experts", [])
            # LLM 返回空列表时，回退到关键词匹配
            if not required:
                logger.warning("LLM返回空专家列表，使用关键词回退")
                return self._fallback_analysis(question)

            return QuestionAnalysis(
                intent_analysis=result.get("intent_analysis", ""),
                required_experts=required,
                reasoning=result.get("reasoning", ""),
                key_entities=result.get("key_entities", []),
                complexity=result.get("complexity", "medium")
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，使用默认分析: {e}")
            return self._fallback_analysis(question)
        except Exception as e:
            logger.error(f"问题分析出错: {e}")
            return self._fallback_analysis(question)
    
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
    
    def fuse_responses(
        self,
        responses: Dict[str, str],
        question: str,
        user_profile: str = "curious"
    ) -> str:
        """
        融合多个专家的回答
        
        Args:
            responses: 专家回答字典 {agent_name: response}
            question: 原始问题
            user_profile: 用户画像类型
        
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
            prompt = get_fusion_prompt(responses, question)
            
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
    
    def add_source_annotations(
        self,
        content: str,
        agent_names: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为回答添加来源标注
        
        Args:
            content: 回答内容
            agent_names: 参与的Agent名称列表
            metadata: 额外元数据
        
        Returns:
            Dict: 包含内容和元数据的字典
        """
        result = {
            "content": content,
            "source_agents": [
                {
                    "id": agent,
                    "name": self.EXPERT_MAPPING.get(agent, agent),
                    "type": self._get_agent_type(agent)
                }
                for agent in agent_names
            ],
            "metadata": metadata or {}
        }
        
        return result
    
    def _get_agent_type(self, agent_name: str) -> str:
        """获取Agent类型描述"""
        types = {
            "craft_expert": "技艺知识专家",
            "history_expert": "历史文化专家",
            "heritage_expert": "传承现状专家"
        }
        return types.get(agent_name, "未知专家")
    
    def should_include_narrative(self, question: str, include_narrative: bool = False) -> bool:
        """
        判断是否应该使用传承人口吻
        
        Args:
            question: 用户问题
            include_narrative: 用户显式请求
        
        Returns:
            bool: 是否使用叙事模式
        """
        narrative_keywords = ["讲讲", "说说", "听听", "师傅", "传承人", "口述", "故事"]
        
        # 用户显式请求
        if include_narrative:
            return True
        
        # 问题中包含叙事性关键词
        if any(kw in question for kw in narrative_keywords):
            return True
        
        return False


    def fuse_with_debate(
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
