"""
历史文化Agent - 专注于起源演变、文化意义等历史知识
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import HISTORY_EXPERT_SYSTEM_PROMPT
from src.retrieval.retriever import MultiSourceRetriever

logger = logging.getLogger(__name__)


class HistoryExpertAgent:
    """
    历史文化专家Agent
    
    专注于传统技艺的历史脉络和文化内涵：
    - 起源考证：技艺起源朝代、创始人物、历史文献
    - 演变历程：技艺在不同时代的发展变化
    - 文化意义：技艺承载的文化价值、象征意义、社会功能
    - 地域特色：不同地区的风格差异、流派特色
    - 人物故事：与技艺相关的历史人物、传说故事
    """
    
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        retriever: Optional[MultiSourceRetriever] = None
    ):
        """
        初始化历史文化Agent
        
        Args:
            llm: 可选的语言模型实例
            retriever: 可选的检索器实例
        """
        if llm is None:
            llm_config = get_llm_config()
            self.llm = ChatOpenAI(
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
            )
        else:
            self.llm = llm
        
        self.retriever = retriever
        self.system_prompt = HISTORY_EXPERT_SYSTEM_PROMPT
        
        # 技艺历史知识库
        self.history_context = {
            "景泰蓝": {
                "起源": "元代从中东地区传入中国",
                "发展": [
                    ("元代", "传入期", "由阿拉伯工匠传入，制作器物供宫廷使用"),
                    ("明代", "成熟期", "景泰年间(1450-1457)达到鼎盛，蓝色珐琅最为出色"),
                    ("清代", "繁荣期", "品种增多，工艺更加精湛，成为宫廷珍玩"),
                    ("近代", "转型期", "从宫廷走向民间，开始出口外销"),
                    ("当代", "复兴期", "被列为国家级非遗，获得保护与传承")
                ],
                "文化意义": "象征皇权富贵，体现中西文化交流，工艺美术瑰宝",
                "代表人物": ["钱进（明代宫廷匠师）", "金世权（近现代传承人）"]
            },
            "苏绣": {
                "起源": "春秋战国时期苏州地区已有刺绣活动",
                "发展": [
                    ("春秋战国", "萌芽期", "吴地已有绣品，用于服饰"),
                    ("宋代", "成熟期", "技艺精湛，图案写实，形成独特风格"),
                    ("明代", "鼎盛期", "出现专门绣娘，技艺分工细化"),
                    ("清代", "高峰期", "康熙、乾隆年间达到顶峰，享誉天下"),
                    ("当代", "传承期", "形成苏、宁、扬、沪四大流派")
                ],
                "文化意义": "江南文化的代表，展现东方女性的智慧与审美",
                "代表人物": ["马蕙绣（《刺绣红楼梦》作者）", "姚建萍（当代刺绣艺术大师）"]
            },
            "龙泉青瓷": {
                "起源": "三国两晋时期浙江龙泉地区开始烧制瓷器",
                "发展": [
                    ("三国两晋", "萌芽期", "烧制原始瓷器，胎质粗糙"),
                    ("唐代", "发展期", "质量提升，开始外销"),
                    ("宋代", "顶峰期", "哥窑、弟窑名扬天下，釉色青翠如玉"),
                    ("明代", "辉煌期", "郑和下西洋携带龙泉青瓷作为礼品"),
                    ("清代", "衰落期", "景德镇瓷器兴起，龙泉窑逐渐衰落"),
                    ("当代", "复兴期", "恢复传统烧制技艺，重现梅子青、粉青釉色")
                ],
                "文化意义": "青瓷文化代表中国瓷器审美的最高境界，体现道家天人合一思想",
                "代表人物": ["章生一、章生二（宋代哥窑创始人传说）", "徐朝兴（当代龙泉青瓷大师）"]
            },
            "宜兴紫砂": {
                "起源": "宋代宜兴金沙寺僧人开始制作紫砂器",
                "发展": [
                    ("宋代", "萌芽期", "金沙寺僧创制粗砂茶壶"),
                    ("明代", "繁荣期", "供春制出第一把紫砂壶，技艺大进"),
                    ("清代", "鼎盛期", "陈鸣远开创花货壶艺，名家辈出"),
                    ("近代", "创新期", "顾景舟成为紫砂艺术一代宗师"),
                    ("当代", "繁荣期", "紫砂壶成为收藏品，壶艺与文化结合")
                ],
                "文化意义": "茶文化的重要载体，文人雅士的精神寄托",
                "代表人物": ["供春（明代紫砂壶鼻祖）", "顾景舟（近代紫砂泰斗）", "汪寅仙（当代紫砂大师）"]
            },
            "芜湖铁画": {
                "起源": "清代康熙年间，由芜湖铁匠汤鹏创立",
                "发展": [
                    ("清代康熙", "创立期", "汤鹏创立铁画技艺，以铁为墨"),
                    ("清代乾隆", "发展期", "技艺成熟，名声远扬"),
                    ("近代", "衰落期", "战乱影响，铁画技艺濒临失传"),
                    ("建国后", "恢复期", "在政府扶持下恢复生产"),
                    ("当代", "创新期", "铁画技艺得到保护，出现新的表现形式")
                ],
                "文化意义": "将锻铁技艺提升为艺术形式，展现刚健之美",
                "代表人物": ["汤鹏（铁画创始人）", "储炎庆（现代铁画传承人）"]
            },
            "蜀锦": {
                "起源": "汉代成都地区已有织锦生产",
                "发展": [
                    ("汉代", "兴起期", "成都成为全国织锦中心，蜀锦闻名天下"),
                    ("蜀汉", "鼎盛期", "诸葛亮大力发展织锦，蜀锦成为军费来源"),
                    ("唐代", "繁荣期", "技艺精湛，图案华丽，远销海外"),
                    ("宋代", "转型期", "品种增加，纹样更加丰富"),
                    ("清代", "复兴期", "蜀锦生产恢复，出现多家织锦作坊"),
                    ("当代", "保护期", "蜀锦技艺被列为非遗，进行保护性生产")
                ],
                "文化意义": "天府文化的重要符号，古代丝绸之路的重要商品",
                "代表人物": ["张窕娘（唐代织锦高手传说）", "刘晨霞（当代蜀锦传承人）"]
            }
        }
    
    def set_retriever(self, retriever: MultiSourceRetriever):
        """设置检索器"""
        self.retriever = retriever
    
    def process(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户问题
        
        Args:
            question: 用户问题
            context: 可选的上下文信息
        
        Returns:
            Dict: 包含回答内容和元数据的字典
        """
        try:
            # 1. 检索相关文档
            retrieved_docs = self._retrieve_documents(question)
            
            # 2. 识别问题中的技艺
            craft_name = self._identify_craft(question, context)
            
            # 3. 生成回答
            answer = self._generate_answer(question, craft_name, retrieved_docs)
            
            return {
                "success": True,
                "answer": answer,
                "source": "history_expert",
                "craft_name": craft_name,
                "retrieved_docs_count": len(retrieved_docs),
                "metadata": {
                    "documents": retrieved_docs
                }
            }
            
        except Exception as e:
            logger.error(f"历史文化Agent处理失败: {e}")
            return {
                "success": False,
                "answer": f"处理您的问题时出现错误：{str(e)}",
                "source": "history_expert",
                "error": str(e)
            }
    
    def _retrieve_documents(self, question: str) -> List[Dict[str, Any]]:
        """检索相关文档"""
        if self.retriever is None:
            return []
        
        try:
            results = self.retriever.retrieve(
                query=question,
                top_k=settings.top_k,
                filter_type="history"
            )
            return results
        except Exception as e:
            logger.warning(f"文档检索失败: {e}")
            return []
    
    def _identify_craft(self, question: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """识别问题中提到的技艺名称"""
        if context and "key_entities" in context:
            for entity in context["key_entities"]:
                if entity in self.history_context:
                    return entity
        
        for craft_name in self.history_context.keys():
            if craft_name in question:
                return craft_name
        
        return None
    
    def _generate_answer(
        self,
        question: str,
        craft_name: Optional[str],
        retrieved_docs: List[Dict[str, Any]]
    ) -> str:
        """生成回答"""
        
        context_parts = []
        
        if craft_name and craft_name in self.history_context:
            history_info = self.history_context[craft_name]
            context_parts.append(f"【{craft_name}历史沿革】")
            context_parts.append(f"起源：{history_info['起源']}")
            context_parts.append(f"\n发展脉络：")
            for period, stage, desc in history_info['发展']:
                context_parts.append(f"  • {period}（{stage}）：{desc}")
            context_parts.append(f"\n文化意义：{history_info['文化意义']}")
            if history_info.get('代表人物'):
                context_parts.append(f"代表人物：{', '.join(history_info['代表人物'])}")
        
        if retrieved_docs:
            context_parts.append("\n【相关历史文献】")
            for i, doc in enumerate(retrieved_docs[:3], 1):
                if "content" in doc:
                    context_parts.append(f"{i}. {doc['content'][:300]}...")
        
        context_str = "\n".join(context_parts) if context_parts else "没有找到相关的历史资料。"
        
        prompt = f"""{self.system_prompt}

## 用户问题
{question}

## 相关信息
{context_str}

## 你的任务
请根据上述信息，以历史文化专家的身份回答用户问题。
回答要：
1. 具有叙事性，讲述有血有肉的历史故事
2. 按时间顺序组织内容
3. 挖掘表象背后的文化内涵
4. 适当引用史料或传说增加可信度
5. 揭示技艺背后的文化密码

请开始回答：
"""
        
        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            return answer
        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            return f"抱歉，生成回答时遇到技术问题：{str(e)}"
    
    def get_craft_history(self, craft_name: str) -> Optional[Dict[str, Any]]:
        """获取特定技艺的历史信息"""
        return self.history_context.get(craft_name)
    
    def get_timeline(self, craft_name: str) -> List[tuple]:
        """获取技艺发展时间线"""
        if craft_name in self.history_context:
            return self.history_context[craft_name]['发展']
        return []
    
    def explain_cultural_significance(self, craft_name: str) -> str:
        """
        解释特定技艺的文化意义
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            文化意义说明
        """
        if craft_name not in self.history_context:
            return f"抱歉，没有找到{craft_name}的相关信息。"
        
        history_info = self.history_context[craft_name]
        
        prompt = f"""请深入分析{craft_name}的文化意义。

基本信息：
- 起源：{history_info['起源']}
- 文化意义：{history_info['文化意义']}

请从以下角度进行深度解读：
1. 技艺与当地文化的关系
2. 技艺承载的价值观和审美
3. 技艺在历史中的社会功能
4. 技艺对中国文化的独特贡献
5. 技艺的当代文化价值

请用富有文化底蕴的语言进行解读：
"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"文化意义解读失败: {e}")
            return f"抱歉，无法生成文化解读：{str(e)}"
