"""
传承人视角叙事生成器 - 将知识点转化为师徒对话风格
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import NARRATIVE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """
    传承人视角叙事生成器
    
    功能：
    1. 将知识点转化为老匠人口吻
    2. 模拟师徒对话风格
    3. 融入技艺故事和人生感悟
    4. 保持知识准确性的同时增加温度
    
    特点：
    - 亲切、耐心、有长辈风范
    - 喜欢用比喻和俗语
    - 传授技艺时循循善诱
    - 会回忆学艺经历增加亲切感
    - 说话有节奏感，适合朗读
    """
    
    # 预设的师傅角色
    CRAFT_MASTERS = {
        "景泰蓝": {
            "name": "张老师傅",
            "specialty": "掐丝珐琅",
            "years_experience": 60,
            "style": "沉稳持重，话少但句句实在"
        },
        "苏绣": {
            "name": "王绣娘",
            "specialty": "刺绣",
            "years_experience": 50,
            "style": "温柔细腻，说话像唱曲"
        },
        "龙泉青瓷": {
            "name": "李窑工",
            "specialty": "青瓷烧制",
            "years_experience": 55,
            "style": "豁达开朗，喜欢讲道家故事"
        },
        "宜兴紫砂": {
            "name": "陈壶师",
            "specialty": "紫砂壶制作",
            "years_experience": 45,
            "style": "儒雅斯文，话说半句留半句"
        },
        "芜湖铁画": {
            "name": "杨铁匠",
            "specialty": "铁画锻制",
            "years_experience": 40,
            "style": "豪爽直率，嗓门大但心细"
        },
        "蜀锦": {
            "name": "刘织娘",
            "specialty": "蜀锦织造",
            "years_experience": 50,
            "style": "爽朗干练，说话语速快"
        }
    }
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化叙事生成器
        
        Args:
            llm: 可选的语言模型实例
        """
        if llm is None:
            llm_config = get_llm_config()
            self.llm = ChatOpenAI(
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=0.8,  # 叙事模式使用较高温度
                max_tokens=1500,
            )
        else:
            self.llm = llm
    
    def generate_narrative(
        self,
        content: str,
        craft_name: Optional[str] = None,
        topic: Optional[str] = None
    ) -> str:
        """
        生成传承人口吻的叙事
        
        Args:
            content: 原始知识点内容
            craft_name: 技艺名称
            topic: 主题（如：掐丝技艺、青瓷烧制等）
        
        Returns:
            str: 传承人口吻的叙事内容
        """
        # 获取师傅角色
        master = self.CRAFT_MASTERS.get(craft_name, {
            "name": "老匠人",
            "specialty": "传统技艺",
            "years_experience": 40,
            "style": "和蔼可亲"
        })
        
        prompt = f"""{NARRATIVE_GENERATION_PROMPT}

## 师傅信息
- 姓名：{master['name']}
- 专长：{master['specialty']}
- 从业年限：{master['years_experience']}年
- 说话风格：{master['style']}

## 要讲述的内容主题
{topic if topic else '传统技艺知识'}

## 原始知识点
{content}

## 叙事要求
1. 用老匠人的口吻讲述，有亲切感
2. 可以融入学艺经历和人生感悟
3. 使用恰当的比喻和俗语
4. 传递对技艺的热爱和敬畏
5. 保持知识准确性，不能为了叙事牺牲准确性
6. 每段200-400字，有完整的起承转合
7. 开头用"[传承人口述]"或"[师傅说]"标注

请开始讲述：
"""
        
        try:
            response = self.llm.invoke(prompt)
            narrative = response.content if hasattr(response, 'content') else str(response)
            
            # 确保开头有标注
            if not narrative.startswith("[传承人口述]") and not narrative.startswith("[师傅说]"):
                narrative = f"[传承人口述] {narrative}"
            
            return narrative
            
        except Exception as e:
            logger.error(f"叙事生成失败: {e}")
            return self._fallback_narrative(content, craft_name, topic)
    
    def _fallback_narrative(
        self,
        content: str,
        craft_name: Optional[str],
        topic: Optional[str]
    ) -> str:
        """备用叙事：当LLM失败时使用模板"""
        master_name = self.CRAFT_MASTERS.get(craft_name, {}).get("name", "老师傅")
        
        return f"""[传承人口述]

咳咳，既然你问到这个，我就跟你唠唠。

{content}

这些啊，都是我这些年摸爬滚打总结出来的经验。说起来容易，做起来难。你要是有心学，就慢慢琢磨，不懂的就问。我当年学这门手艺，也是这么过来的。

好了，就先说这么多吧。有什么问题，随时来问。
—— {master_name}
"""
    
    def generate_dialogue(
        self,
        user_question: str,
        knowledge_content: str,
        craft_name: Optional[str] = None
    ) -> str:
        """
        生成师徒对话形式的内容
        
        Args:
            user_question: 用户的问题
            knowledge_content: 知识内容
            craft_name: 技艺名称
        
        Returns:
            str: 师徒对话形式的内容
        """
        master = self.CRAFT_MASTERS.get(craft_name, {
            "name": "老匠人",
            "years_experience": 40
        })
        
        prompt = f"""请将以下知识内容转化为师徒对话形式。

## 师傅信息
姓名：{master['name']}
从业年限：{master['years_experience']}年

## 徒弟的问题
「{user_question}」

## 需要传授的知识
{knowledge_content}

## 对话要求
1. 以师傅回答徒弟问题的形式展开
2. 师傅语气亲切、有耐心、有长辈风范
3. 适当加入比喻、俗语，增加生动性
4. 可以有简短的师徒互动
5. 保持知识的准确性和完整性
6. 全程300-500字

请生成对话：
"""
        
        try:
            response = self.llm.invoke(prompt)
            dialogue = response.content if hasattr(response, 'content') else str(response)
            return f"[师徒对话]\n\n{dialogue}"
        except Exception as e:
            logger.error(f"对话生成失败: {e}")
            return self.generate_narrative(knowledge_content, craft_name)
    
    def generate_story(
        self,
        topic: str,
        craft_name: Optional[str] = None,
        story_type: str = "apprentice"
    ) -> str:
        """
        生成技艺相关的故事
        
        Args:
            topic: 故事主题
            craft_name: 技艺名称
            story_type: 故事类型（apprentice:学艺故事, master:匠人故事, craft:技艺传说）
        
        Returns:
            str: 故事内容
        """
        story_styles = {
            "apprentice": "学艺故事",
            "master": "匠人故事",
            "craft": "技艺传说"
        }
        
        master = self.CRAFT_MASTERS.get(craft_name, {
            "name": "老匠人"
        })
        
        style = story_styles.get(story_type, "学艺故事")
        
        prompt = f"""请讲述一个关于{topic}的{style}。

## 讲述者
{master['name']}（{master.get('years_experience', 40)}年从业经验）

## 要求
1. 第一人称叙述，有画面感
2. 融入真实的技艺细节
3. 体现技艺传承的精神
4. 有情感共鸣
5. 篇幅300-600字
6. 适合朗读

请开始讲述：
"""
        
        try:
            response = self.llm.invoke(prompt)
            story = response.content if hasattr(response, 'content') else str(response)
            return f"[{style}]\n\n{story}"
        except Exception as e:
            logger.error(f"故事生成失败: {e}")
            return f"抱歉，无法生成{style}。"
    
    def add_narrative_intro(
        self,
        content: str,
        craft_name: Optional[str] = None
    ) -> str:
        """
        为内容添加叙事性引言
        
        Args:
            content: 原始内容
            craft_name: 技艺名称
        
        Returns:
            str: 添加了引言的内容
        """
        intros = {
            "景泰蓝": "这景泰蓝啊，是咱们老祖宗留下的宝贝。你要问它好在哪儿？且听我慢慢道来——",
            "苏绣": "说起这苏绣，我这辈子就干了这一件事。一针一线，绣的是咱们江南的山水，也是绣娘的心——",
            "龙泉青瓷": "这青瓷啊，烧的是土用的是火，可出的是韵是魂。你看着简单，里头的门道可深着呢——",
            "宜兴紫砂": "紫砂壶这东西，喝茶的人爱它，咱做壶的更爱它。为啥？这里头有咱的命——",
            "芜湖铁画": "都说画是用笔画的，咱们铁画是用锤子敲出来的。你别看这铁硬，在咱手里，它跟纸似的——",
            "蜀锦": "这蜀锦啊，织的是咱们四川人的脾气。你看这花纹，热热闹闹的，就跟咱们的生活一样——"
        }
        
        intro = intros.get(craft_name, "说起这传统技艺啊，是咱们文化的根。你且听我细细道来——")
        
        return f"{intro}\n\n{content}"
    
    def get_master_quote(self, craft_name: str, theme: str) -> str:
        """
        获取师傅关于特定主题的名言
        
        Args:
            craft_name: 技艺名称
            theme: 主题（如：耐心、细节、传承等）
        
        Returns:
            str: 师傅的名言
        """
        quotes = {
            "景泰蓝": {
                "耐心": "做景泰蓝，急不得。铜丝要一根根掐，釉色要一遍遍烧，急了就出不了好活儿。",
                "细节": "这掐丝的活儿，差一毫都不行。铜丝歪了，整件活儿就废了。",
                "传承": "这手艺传到我手里，不能在我这儿断了。"
            },
            "苏绣": {
                "耐心": "绣花这事儿，心不静，针就乱。",
                "细节": "一针一线都是讲究，差一针，整幅画就不对味儿。",
                "传承": "我娘教我，我教徒弟，就这么一代代传下来的。"
            },
            "龙泉青瓷": {
                "耐心": "烧瓷器，三分靠人，七分靠天。急不得。",
                "细节": "这釉色啊，厚一分浅了，薄一分枯了。",
                "传承": "青瓷的魂在'青'字上，这个青是天的青，也是人心的青。"
            }
        }
        
        craft_quotes = quotes.get(craft_name, {})
        return craft_quotes.get(theme, f"做{craft_name}这门手艺，最重要的是用心。")
    
    def switch_narrative_mode(
        self,
        content: str,
        craft_name: Optional[str] = None,
        mode: str = "narrative"
    ) -> str:
        """
        切换叙事模式
        
        Args:
            content: 原始内容
            craft_name: 技艺名称
            mode: 模式（narrative:叙事模式, dialogue:对话模式, standard:标准模式）
        
        Returns:
            str: 转换后的内容
        """
        if mode == "standard":
            return content  # 标准模式直接返回
        
        if mode == "dialogue":
            return self.generate_dialogue(
                "请讲讲相关知识",
                content,
                craft_name
            )
        
        return self.generate_narrative(content, craft_name)
