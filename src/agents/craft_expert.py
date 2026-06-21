"""
技艺知识Agent - 专注于工艺流程、材料、工具等技艺知识
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import CRAFT_EXPERT_SYSTEM_PROMPT
from src.retrieval.retriever import MultiSourceRetriever

logger = logging.getLogger(__name__)


class CraftExpertAgent:
    """
    技艺知识专家Agent
    
    专注于传统工艺的技术细节和制作流程：
    - 工艺流程：详细制作步骤、工序顺序、操作要点
    - 材料特性：原材料种类、特性、处理方法、配比
    - 工具使用：传统工具、现代工具、工具选择、使用技巧
    - 技术要点：关键技术难点、技巧窍门、质量标准
    """
    
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        retriever: Optional[MultiSourceRetriever] = None
    ):
        """
        初始化技艺知识Agent
        
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
        self.system_prompt = CRAFT_EXPERT_SYSTEM_PROMPT
        
        # 技艺知识库上下文
        self.craft_context = {
            "景泰蓝": {
                "工艺": ["制胎", "掐丝", "烧焊", "点蓝", "烧蓝", "磨光", "镀金"],
                "材料": ["紫铜", "铜丝", "珐琅釉料", "金箔"],
                "工具": ["掐丝工具", "焊枪", "蓝枪", "磨石"],
                "特点": "色彩丰富，线条流畅，立体感强"
            },
            "苏绣": {
                "工艺": ["勾样", "上绷", "配线", "刺绣", "落绷"],
                "材料": ["真丝", "绸缎", "蚕丝线"],
                "工具": ["绣针", "绣绷", "绣架", "剪刀"],
                "特点": "图案秀丽，针法活泼，色彩典雅"
            },
            "龙泉青瓷": {
                "工艺": ["淘泥", "拉坯", "利坯", "上釉", "烧制"],
                "材料": ["紫金土", "石英", "长石", "瓷土"],
                "工具": ["拉坯机", "修坯刀", "釉缸"],
                "特点": "釉色青翠，如玉似冰，釉层丰润"
            },
            "宜兴紫砂": {
                "工艺": ["炼泥", "打泥片", "身筒", "成型", "烧制"],
                "材料": ["紫砂泥", "段泥", "红泥"],
                "工具": ["泥凳", "拍子", "木转盘", "各种成型工具"],
                "特点": "透气性好，造型丰富，泡茶味佳"
            },
            "芜湖铁画": {
                "工艺": ["锻造", "退火", "焊接", "整形", "装裱"],
                "材料": ["熟铁", "低碳钢"],
                "工具": ["铁锤", "砧子", "炉子", "钳子"],
                "特点": "以铁为墨，以砧为砚，刚劲有力"
            },
            "蜀锦": {
                "工艺": ["设计", "装机", "织造"],
                "材料": ["蚕丝", "人造丝", "金银线"],
                "工具": ["花楼织机", "梭子", "竹竿"],
                "特点": "色彩艳丽，图案繁华，质地坚韧"
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
            context: 可选的上下文信息（如识别出的技艺名称）
        
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
                "source": "craft_expert",
                "craft_name": craft_name,
                "retrieved_docs_count": len(retrieved_docs),
                "metadata": {
                    "documents": retrieved_docs
                }
            }
            
        except Exception as e:
            logger.error(f"技艺知识Agent处理失败: {e}")
            return {
                "success": False,
                "answer": f"处理您的问题时出现错误：{str(e)}",
                "source": "craft_expert",
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
                filter_type="craft"
            )
            return results
        except Exception as e:
            logger.warning(f"文档检索失败: {e}")
            return []
    
    def _identify_craft(self, question: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """识别问题中提到的技艺名称"""
        # 从上下文获取
        if context and "key_entities" in context:
            for entity in context["key_entities"]:
                if entity in self.craft_context:
                    return entity
        
        # 从问题中匹配
        for craft_name in self.craft_context.keys():
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
        
        # 构建上下文信息
        context_parts = []
        
        if craft_name and craft_name in self.craft_context:
            craft_info = self.craft_context[craft_name]
            context_parts.append(f"【{craft_name}技艺基本信息】")
            context_parts.append(f"主要工艺流程：{' → '.join(craft_info['工艺'])}")
            context_parts.append(f"主要材料：{', '.join(craft_info['材料'])}")
            context_parts.append(f"主要工具：{', '.join(craft_info['工具'])}")
            context_parts.append(f"特点：{craft_info['特点']}")
        
        # 添加检索到的文档内容
        if retrieved_docs:
            context_parts.append("\n【相关文档资料】")
            for i, doc in enumerate(retrieved_docs[:3], 1):
                if "content" in doc:
                    context_parts.append(f"{i}. {doc['content'][:300]}...")
        
        context_str = "\n".join(context_parts) if context_parts else "没有找到相关的技艺资料。"
        
        # 构建Prompt
        prompt = f"""{self.system_prompt}

## 用户问题
{question}

## 相关信息
{context_str}

## 你的任务
请根据上述信息，以技艺知识专家的身份回答用户问题。
回答要：
1. 精确描述工艺流程或技术要点
2. 使用步骤化、结构化的表达
3. 关键步骤用编号标注
4. 技术难点要重点说明
5. 如有专业术语，要提供通俗解释

请开始回答：
"""
        
        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            return answer
        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            return f"抱歉，生成回答时遇到技术问题：{str(e)}"
    
    def get_craft_info(self, craft_name: str) -> Optional[Dict[str, Any]]:
        """
        获取特定技艺的详细信息
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            技艺信息字典，如果不存在返回None
        """
        return self.craft_context.get(craft_name)
    
    def list_supported_crafts(self) -> List[str]:
        """
        列出支持的技艺列表
        
        Returns:
            技艺名称列表
        """
        return list(self.craft_context.keys())
    
    def explain_technique(
        self,
        craft_name: str,
        technique_name: str,
        detail_level: str = "medium"
    ) -> str:
        """
        详细解释特定技艺的某个技术要点
        
        Args:
            craft_name: 技艺名称
            technique_name: 技术名称
            detail_level: 详细程度 (brief/medium/detailed)
        
        Returns:
            技术说明
        """
        prompt = f"""你是一个传统技艺专家，请详细解释{craft_name}的{technique_name}技术。

详细程度：{detail_level}

请从以下角度进行说明：
1. 技术定义和目的
2. 操作步骤和要点
3. 常见问题和解决方法
4. 技巧和竅门
5. 与其他工序的配合

请用专业但易懂的语言解释：
"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"技术解释生成失败: {e}")
            return f"抱歉，无法生成技术解释：{str(e)}"
