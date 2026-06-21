"""
传承现状Agent - 专注于传承人、濒危程度、保护措施等现状知识
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import HERITAGE_EXPERT_SYSTEM_PROMPT
from src.retrieval.retriever import MultiSourceRetriever

logger = logging.getLogger(__name__)


class HeritageExpertAgent:
    """
    传承现状专家Agent
    
    专注于传统技艺的当代传承和保护状况：
    - 传承人信息：各级传承人数量、分布、代表性传承人介绍
    - 濒危程度：技艺的生存状态、保护等级、危机因素
    - 保护政策：国家/地方保护政策、非遗法规定、扶持措施
    - 学习途径：传统拜师、院校教育、培训班、线上资源
    - 产业现状：市场规模、从业人数、产业发展趋势
    """
    
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        retriever: Optional[MultiSourceRetriever] = None
    ):
        """
        初始化传承现状Agent
        
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
        self.system_prompt = HERITAGE_EXPERT_SYSTEM_PROMPT
        
        # 传承现状知识库
        self.heritage_context = {
            "景泰蓝": {
                "保护等级": "国家级非物质文化遗产",
                "濒危程度": "中低 - 传承人数相对充足，但技艺全面掌握者较少",
                "传承人": {
                    "国家级": ["钱美华（已故）", "张禄祺", "李佩卿（已故）"],
                    "省级": ["约15人"],
                    "市级": ["约30人"]
                },
                "分布": "北京为主要传承地，河北、广东等地也有分布",
                "保护措施": [
                    "列入国家级非遗名录",
                    "建立传承人制度",
                    "设立专项保护资金",
                    "推动产学研结合"
                ],
                "学习途径": {
                    "院校": ["北京工艺术美术职业学院", "清华大学美术学院"],
                    "机构": ["北京珐琅厂（传承基地）"],
                    "拜师": "可联系当地工艺美术行业协会"
                }
            },
            "苏绣": {
                "保护等级": "国家级非物质文化遗产",
                "濒危程度": "中 - 传承人数较多，但高水平绣娘较少",
                "传承人": {
                    "国家级": ["姚建萍", "王金山", "张玉英（已故）"],
                    "省级": ["约50人"],
                    "市级": ["约150人"]
                },
                "分布": "江苏苏州为中心，辐射上海、无锡等地",
                "保护措施": [
                    "建立苏绣小镇",
                    "苏州刺绣研究所",
                    "非遗进校园活动",
                    "数字化保护工程"
                ],
                "学习途径": {
                    "院校": ["苏州工艺美术职业技术学院", "南京艺术学院"],
                    "机构": ["苏州刺绣研究所", "镇湖刺绣协会"],
                    "拜师": "可联系苏州工艺美术行业协会"
                }
            },
            "龙泉青瓷": {
                "保护等级": "国家级非物质文化遗产（传统烧制技艺）",
                "濒危程度": "中 - 传统烧制技艺面临失传风险",
                "传承人": {
                    "国家级": ["徐朝兴", "毛正聪", "夏侯文"],
                    "省级": ["约20人"],
                    "市级": ["约50人"]
                },
                "分布": "浙江龙泉市为主要传承地",
                "保护措施": [
                    "龙泉青瓷宝剑苑",
                    "青瓷研究所",
                    "龙泉青瓷行业协会",
                    "国际龙泉青瓷展"
                ],
                "学习途径": {
                    "院校": ["景德镇陶瓷大学", "龙泉青瓷学院"],
                    "机构": ["龙泉青瓷研究所", "青瓷小镇"],
                    "拜师": "可联系龙泉青瓷行业协会"
                }
            },
            "宜兴紫砂": {
                "保护等级": "国家级非物质文化遗产",
                "濒危程度": "低 - 产业活跃，传承状况良好",
                "传承人": {
                    "国家级": ["汪寅仙（已故）", "周桂珍", "顾绍培"],
                    "省级": ["约80人"],
                    "市级": ["约200人"]
                },
                "分布": "江苏宜兴市丁蜀镇为核心产区",
                "保护措施": [
                    "宜兴紫砂博物馆",
                    "紫砂陶艺协会",
                    "紫砂文化节",
                    "知识产权保护"
                ],
                "学习途径": {
                    "院校": ["宜兴陶瓷博物馆", "无锡工艺职业技术学院"],
                    "机构": ["宜兴紫砂厂", "紫砂陶艺协会"],
                    "拜师": "可联系宜兴紫砂行业协会"
                }
            },
            "芜湖铁画": {
                "保护等级": "国家级非物质文化遗产",
                "濒危程度": "高 - 传承人稀少，技艺濒临失传",
                "传承人": {
                    "国家级": ["杨光辉"],
                    "省级": ["张家康", "沈飞鹰"],
                    "市级": ["约10人"]
                },
                "分布": "安徽芜湖市为主要传承地",
                "保护措施": [
                    "列入国家非遗保护名录",
                    "建立铁画博物馆",
                    "培养年轻传承人",
                    "探索创新发展"
                ],
                "学习途径": {
                    "院校": ["安徽师范大学", "芜湖职业技术学院"],
                    "机构": ["芜湖市铁画研究所"],
                    "拜师": "可联系芜湖市文化局非遗保护中心"
                }
            },
            "蜀锦": {
                "保护等级": "国家级非物质文化遗产",
                "濒危程度": "中高 - 传统技艺掌握者少",
                "传承人": {
                    "国家级": ["刘晨霞"],
                    "省级": ["郝淑萍", "孟德芝"],
                    "市级": ["约20人"]
                },
                "分布": "四川成都为主要传承地",
                "保护措施": [
                    "成都蜀锦博物馆",
                    "蜀锦研究所",
                    "非遗主题街区",
                    "数字化保护"
                ],
                "学习途径": {
                    "院校": ["四川大学", "成都纺织高等专科学校"],
                    "机构": ["成都蜀锦研究所", "锦门景区"],
                    "拜师": "可联系成都市非遗保护中心"
                }
            }
        }
        
        # 学习资源
        self.learning_resources = {
            "景泰蓝": [
                {"名称": "《景泰蓝制作技艺》", "类型": "书籍", "来源": "中国轻工业出版社"},
                {"名称": "北京珐琅厂官网", "类型": "网站", "来源": "bjflc.com"},
                {"名称": "国家级传承人李佩卿作品集", "类型": "视频", "来源": "B站/优酷"}
            ],
            "苏绣": [
                {"名称": "《苏绣》", "类型": "书籍", "来源": "苏州大学出版社"},
                {"名称": "苏州刺绣研究所", "类型": "机构", "来源": "苏州"},
                {"名称": "姚建萍苏绣艺术中心", "类型": "机构", "来源": "苏州"}
            ],
            "龙泉青瓷": [
                {"名称": "《龙泉青瓷》", "类型": "书籍", "来源": "文物出版社"},
                {"名称": "龙泉青瓷宝剑城", "类型": "景区", "来源": "浙江龙泉"},
                {"名称": "龙泉青瓷协会", "类型": "机构", "来源": "龙泉"}
            ],
            "宜兴紫砂": [
                {"名称": "《宜兴紫砂》", "类型": "书籍", "来源": "上海古籍出版社"},
                {"名称": "宜兴陶瓷博物馆", "类型": "博物馆", "来源": "江苏宜兴"},
                {"名称": "紫砂壶爱好者论坛", "类型": "社区", "来源": "网络"}
            ],
            "芜湖铁画": [
                {"名称": "《芜湖铁画》", "类型": "书籍", "来源": "安徽美术出版社"},
                {"名称": "芜湖铁画研究所", "类型": "机构", "来源": "安徽芜湖"},
                {"名称": "铁画制作技艺纪录片", "类型": "视频", "来源": "央视"}
            ],
            "蜀锦": [
                {"名称": "《蜀锦》", "类型": "书籍", "来源": "四川美术出版社"},
                {"名称": "成都蜀锦博物馆", "类型": "博物馆", "来源": "四川成都"},
                {"名称": "锦门景区", "类型": "景区", "来源": "成都"}
            ]
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
                "source": "heritage_expert",
                "craft_name": craft_name,
                "retrieved_docs_count": len(retrieved_docs),
                "metadata": {
                    "documents": retrieved_docs
                }
            }
            
        except Exception as e:
            logger.error(f"传承现状Agent处理失败: {e}")
            return {
                "success": False,
                "answer": f"处理您的问题时出现错误：{str(e)}",
                "source": "heritage_expert",
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
                filter_type="heritage"
            )
            return results
        except Exception as e:
            logger.warning(f"文档检索失败: {e}")
            return []
    
    def _identify_craft(self, question: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """识别问题中提到的技艺名称"""
        if context and "key_entities" in context:
            for entity in context["key_entities"]:
                if entity in self.heritage_context:
                    return entity
        
        for craft_name in self.heritage_context.keys():
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
        
        if craft_name and craft_name in self.heritage_context:
            heritage_info = self.heritage_context[craft_name]
            context_parts.append(f"【{craft_name}传承现状】")
            context_parts.append(f"保护等级：{heritage_info['保护等级']}")
            context_parts.append(f"濒危程度：{heritage_info['濒危程度']}")
            context_parts.append(f"\n传承人信息：")
            for level, people in heritage_info['传承人'].items():
                context_parts.append(f"  • {level}：{', '.join(people)}")
            context_parts.append(f"\n分布区域：{heritage_info['分布']}")
            context_parts.append(f"\n保护措施：")
            for i, measure in enumerate(heritage_info['保护措施'], 1):
                context_parts.append(f"  {i}. {measure}")
            context_parts.append(f"\n学习途径：")
            for category, paths in heritage_info['学习途径'].items():
                context_parts.append(f"  • {category}：{paths}")
        
        # 添加学习资源
        if craft_name and craft_name in self.learning_resources:
            context_parts.append(f"\n【推荐学习资源】")
            for resource in self.learning_resources[craft_name]:
                context_parts.append(f"  • {resource['名称']}（{resource['类型']}）- {resource['来源']}")
        
        if retrieved_docs:
            context_parts.append("\n【相关文档资料】")
            for i, doc in enumerate(retrieved_docs[:3], 1):
                if "content" in doc:
                    context_parts.append(f"{i}. {doc['content'][:300]}...")
        
        context_str = "\n".join(context_parts) if context_parts else "没有找到相关的传承信息。"
        
        prompt = f"""{self.system_prompt}

## 用户问题
{question}

## 相关信息
{context_str}

## 你的任务
请根据上述信息，以传承现状专家的身份回答用户问题。
回答要：
1. 务实，提供可操作的具体信息
2. 善用数据说话
3. 给出清晰的行动路径
4. 客观分析传承挑战与机遇
5. 如涉及学习，要给出具体建议

请开始回答：
"""
        
        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            return answer
        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            return f"抱歉，生成回答时遇到技术问题：{str(e)}"
    
    def get_heritage_info(self, craft_name: str) -> Optional[Dict[str, Any]]:
        """获取特定技艺的传承信息"""
        return self.heritage_context.get(craft_name)
    
    def get_inheritors(self, craft_name: str) -> List[Dict[str, str]]:
        """获取传承人列表"""
        if craft_name in self.heritage_context:
            return [
                {"level": level, "names": names}
                for level, names in self.heritage_context[craft_name]['传承人'].items()
            ]
        return []
    
    def get_learning_paths(self, craft_name: str) -> Dict[str, str]:
        """获取学习途径"""
        if craft_name in self.heritage_context:
            return self.heritage_context[craft_name]['学习途径']
        return {}
    
    def get_endangerment_assessment(self, craft_name: str) -> str:
        """
        获取濒危程度评估
        
        Args:
            craft_name: 技艺名称
        
        Returns:
            濒危程度描述
        """
        if craft_name in self.heritage_context:
            return self.heritage_context[craft_name]['濒危程度']
        return "未知"
    
    def generate_learning_guide(self, craft_name: str, level: str = "beginner") -> str:
        """
        生成学习指南
        
        Args:
            craft_name: 技艺名称
            level: 学习者水平 (beginner/intermediate/advanced)
        
        Returns:
            学习指南
        """
        if craft_name not in self.heritage_context:
            return f"抱歉，没有找到{craft_name}的相关信息。"
        
        heritage_info = self.heritage_context[craft_name]
        learning_paths = heritage_info['学习途径']
        resources = self.learning_resources.get(craft_name, [])
        
        prompt = f"""请为{craft_name}的学习者生成一份{level}级别的学习指南。

技艺信息：
- 保护等级：{heritage_info['保护等级']}
- 濒危程度：{heritage_info['濒危程度']}
- 学习途径：{learning_paths}

推荐资源：
{chr(10).join([f"- {r['名称']}（{r['类型']}）" for r in resources])}

学习者水平：{level}

请提供：
1. 学习路径规划（按阶段划分）
2. 每个阶段的学习内容
3. 推荐的学习资源
4. 实践建议
5. 注意事项

请用务实、行动导向的语言：
"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"学习指南生成失败: {e}")
            return f"抱歉，无法生成学习指南：{str(e)}"
