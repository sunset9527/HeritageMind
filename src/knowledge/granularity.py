"""
多粒度回答控制器 - 根据用户画像生成不同深度的回答
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import GRANULARITY_PROMPTS, get_adaptive_prompt

logger = logging.getLogger(__name__)


class GranularityController:
    """
    多粒度回答控制器
    
    支持三种用户画像：
    - curious（好奇者）：浅层了解，1-2段，300-500字
    - learner（学习者）：系统学习，3-5段，800-1500字
    - researcher（研究者）：深度资料，2000+字
    
    功能：
    1. 根据用户画像调整回答深度
    2. 根据用户画像调整回答篇幅
    3. 根据用户画像调整内容重点
    4. 生成引用来源和参考资源
    """
    
    # 用户画像配置
    PROFILES = {
        "curious": {
            "name": "好奇者",
            "description": "对非遗技艺有初步兴趣，想要了解基本情况",
            "depth": "shallow",
            "length_range": (300, 500),
            "focus": ["基本概念", "趣味点", "简单历史"]
        },
        "learner": {
            "name": "学习者",
            "description": "想要深入学习非遗技艺，具备一定基础",
            "depth": "medium",
            "length_range": (800, 1500),
            "focus": ["完整知识体系", "操作要点", "练习建议"]
        },
        "researcher": {
            "name": "研究者",
            "description": "需要深度资料用于学术研究或专业创作",
            "depth": "deep",
            "length_range": (2000, 5000),
            "focus": ["完整技术细节", "历史文献", "统计数据"]
        }
    }
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化多粒度控制器
        
        Args:
            llm: 可选的语言模型实例
        """
        if llm is None:
            llm_config = get_llm_config()
            self.llm = ChatOpenAI(
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"] * 2,  # 深度内容需要更多token
            )
        else:
            self.llm = llm
    
    def adapt_content(
        self,
        base_content: str,
        user_profile: str,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据用户画像调整内容
        
        Args:
            base_content: 基础回答内容
            user_profile: 用户画像类型
            question: 原始问题
            context: 可选的上下文信息
        
        Returns:
            Dict: 包含调整后内容和元数据的字典
        """
        profile = self.PROFILES.get(user_profile, self.PROFILES["curious"])
        
        try:
            adapted_content = self._generate_adapted_content(
                base_content, profile, question, context
            )
            
            return {
                "success": True,
                "content": adapted_content,
                "user_profile": user_profile,
                "profile_name": profile["name"],
                "depth": profile["depth"],
                "metadata": {
                    "focus_areas": profile["focus"],
                    "length_range": profile["length_range"]
                }
            }
            
        except Exception as e:
            logger.error(f"内容适配失败: {e}")
            return {
                "success": False,
                "content": base_content,  # 返回原始内容作为降级
                "user_profile": user_profile,
                "error": str(e)
            }
    
    def _generate_adapted_content(
        self,
        base_content: str,
        profile: Dict[str, Any],
        question: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成适配后的内容"""
        
        # 构建适配Prompt
        prompt = f"""{GRANULARITY_PROMPTS.get(profile['name'], GRANULARITY_PROMPTS['curious'])}

## 原始问题
{question}

## 用户画像
- 类型：{profile['name']}
- 描述：{profile['description']}
- 深度：{profile['depth']}
- 重点：{', '.join(profile['focus'])}

## 基础回答内容
{base_content}

## 上下文信息（可选）
{context if context else '无'}

## 输出要求
1. 根据用户画像调整回答的深度和篇幅
2. 突出用户关心的重点内容
3. 添加适当的学习建议（如果适用）
4. 如有引用，注明来源

请生成适配后的回答：
"""
        
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    
    def generate_researcher_content(
        self,
        base_content: str,
        question: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        生成研究者级别内容（带引用）
        
        Args:
            base_content: 基础内容
            question: 原始问题
            sources: 参考文献列表
        
        Returns:
            str: 带引用的学术级内容
        """
        sources_text = ""
        if sources:
            sources_text = "\n## 参考文献\n"
            for i, source in enumerate(sources, 1):
                sources_text += f"{i}. {source.get('title', '未知来源')}"
                if source.get('author'):
                    sources_text += f" - {source['author']}"
                sources_text += "\n"
        
        prompt = f"""{GRANULARITY_PROMPTS['researcher']}

## 原始问题
{question}

## 基础回答内容
{base_content}
{sources_text}

## 额外要求
1. 提供详尽的技术细节
2. 包含历史文献引用
3. 添加统计和数据支持
4. 列出延伸阅读资源
5. 保持学术严谨性

请生成学术级回答：
"""
        
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    
    def generate_learner_content(
        self,
        base_content: str,
        question: str,
        craft_name: Optional[str] = None
    ) -> str:
        """
        生成学习者级别内容（带学习建议）
        
        Args:
            base_content: 基础内容
            question: 原始问题
            craft_name: 技艺名称
        
        Returns:
            str: 带学习建议的内容
        """
        learning_suggestion = ""
        if craft_name:
            learning_suggestion = f"""

## 学习建议
针对{craft_name}的学习，建议按以下路径：
1. 入门：了解基本概念和历史背景
2. 基础：掌握主要工艺流程和工具使用
3. 进阶：深入学习关键技术难点
4. 实践：通过观看视频或实地考察加深理解
5. 交流：加入相关社群，与从业者交流经验
"""
        
        prompt = f"""{GRANULARITY_PROMPTS['learner']}

## 原始问题
{question}

## 基础回答内容
{base_content}
{learning_suggestion}

## 额外要求
1. 提供结构化的知识体系
2. 包含实践操作建议
3. 给出具体的学习路径
4. 推荐学习资源

请生成学习者友好的回答：
"""
        
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    
    def generate_curious_content(
        self,
        base_content: str,
        question: str
    ) -> str:
        """
        生成好奇者级别内容（趣味性强）
        
        Args:
            base_content: 基础内容
            question: 原始问题
        
        Returns:
            str: 趣味性强、简单易懂的内容
        """
        prompt = f"""{GRANULARITY_PROMPTS['curious']}

## 原始问题
{question}

## 基础回答内容
{base_content}

## 额外要求
1. 语言生动有趣
2. 适当使用比喻和故事
3. 突出有趣的冷知识
4. 引发进一步探索的兴趣
5. 控制在300-500字

请生成通俗易懂、趣味性强的回答：
"""
        
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    
    def get_profile_info(self, user_profile: str) -> Dict[str, Any]:
        """
        获取用户画像信息
        
        Args:
            user_profile: 用户画像类型
        
        Returns:
            Dict: 画像信息
        """
        return self.PROFILES.get(user_profile, self.PROFILES["curious"])
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        列出所有用户画像
        
        Returns:
            List[Dict]: 画像列表
        """
        return [
            {"id": key, **value}
            for key, value in self.PROFILES.items()
        ]
    
    def estimate_reading_time(self, content: str) -> int:
        """
        估算阅读时间（分钟）
        
        Args:
            content: 内容文本
        
        Returns:
            int: 阅读时间（分钟）
        """
        # 假设中文阅读速度：400字/分钟
        char_count = len(content)
        return max(1, char_count // 400)
    
    def add_toc(self, content: str, user_profile: str) -> str:
        """
        为长内容添加目录
        
        Args:
            content: 内容文本
            user_profile: 用户画像类型
        
        Returns:
            str: 带目录的内容
        """
        # 仅对学习者和研究者添加目录
        if user_profile not in ["learner", "researcher"]:
            return content
        
        # 简单实现：按标题提取
        lines = content.split("\n")
        toc_entries = []
        
        for line in lines:
            stripped = line.strip()
            # 检测标题（以#开头或以数字/汉字序号开头）
            if stripped.startswith("#") or (len(stripped) > 0 and stripped[0].isdigit()):
                if len(stripped) > 3:
                    toc_entries.append(stripped[:50])  # 截断长标题
        
        if toc_entries:
            toc = "\n".join([f"- {entry}" for entry in toc_entries[:10]])
            return f"## 目录\n{toc}\n\n---\n\n{content}"
        
        return content
