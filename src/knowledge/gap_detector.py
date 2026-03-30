"""
知识缺口检测器 - 检测知识库中的空白领域
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from config import settings, get_llm_config
from src.utils.prompts import GAP_DETECTION_PROMPT

logger = logging.getLogger(__name__)


class KnowledgeGap(BaseModel):
    """知识缺口模型"""
    aspect: str = Field(description="缺失的方面")
    description: str = Field(description="具体描述缺失什么")
    suggestion: str = Field(description="建议补充什么方向的资料")


class GapDetectionResult(BaseModel):
    """缺口检测结果模型"""
    coverage_level: str = Field(description="覆盖程度：sufficient/partial/missing")
    relevant_documents: int = Field(description="相关文档数量")
    coverage_score: float = Field(description="覆盖评分0-1")
    identified_gaps: List[KnowledgeGap] = Field(description="识别的缺口列表")
    can_answer: bool = Field(description="能否充分回答")
    confidence: float = Field(description="置信度0-1")
    reasoning: str = Field(description="评估理由")


class KnowledgeGapDetector:
    """
    知识缺口检测器
    
    功能：
    1. 分析检索结果，判断知识库覆盖度
    2. 识别知识库中的空白领域
    3. 生成知识缺口报告
    4. 为知识补充提供方向性建议
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化知识缺口检测器
        
        Args:
            llm: 可选的语言模型实例
        """
        if llm is None:
            llm_config = get_llm_config()
            self.llm = ChatOpenAI(
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=0.3,  # 缺口检测使用较低温度
                max_tokens=1500,
            )
        else:
            self.llm = llm
        
        self.system_prompt = GAP_DETECTION_PROMPT
        self.threshold = settings.gap_detection_threshold
    
    def detect(
        self,
        question: str,
        retrieved_docs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> GapDetectionResult:
        """
        检测知识缺口
        
        Args:
            question: 用户问题
            retrieved_docs: 检索到的文档列表
            context: 可选的上下文信息
        
        Returns:
            GapDetectionResult: 缺口检测结果
        """
        # 基本评估
        doc_count = len(retrieved_docs)
        doc_contents = [doc.get("content", "")[:500] for doc in retrieved_docs if "content" in doc]
        
        # 使用LLM进行深度分析
        try:
            prompt = self._build_detection_prompt(question, doc_count, doc_contents)
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析JSON结果
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            result = json.loads(content)
            
            gaps = [
                KnowledgeGap(
                    aspect=g.get("aspect", ""),
                    description=g.get("description", ""),
                    suggestion=g.get("suggestion", "")
                )
                for g in result.get("identified_gaps", [])
            ]
            
            return GapDetectionResult(
                coverage_level=result.get("coverage_level", "partial"),
                relevant_documents=doc_count,
                coverage_score=result.get("coverage_score", 0.5),
                identified_gaps=gaps,
                can_answer=result.get("can_answer", doc_count >= self.threshold),
                confidence=result.get("confidence", 0.7),
                reasoning=result.get("reasoning", "")
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，使用备用逻辑: {e}")
            return self._fallback_detection(doc_count)
        except Exception as e:
            logger.error(f"缺口检测失败: {e}")
            return self._fallback_detection(doc_count)
    
    def _build_detection_prompt(
        self,
        question: str,
        doc_count: int,
        doc_contents: List[str]
    ) -> str:
        """构建检测Prompt"""
        docs_text = "\n".join([f"文档{i+1}: {content}" for i, content in enumerate(doc_contents)]) if doc_contents else "无"
        
        return f"""{self.system_prompt}

## 用户问题
{question}

## 检索结果统计
- 相关文档数量：{doc_count}
- 文档内容摘要：
{docs_text}

## 评估标准
- 充足：3条以上高度相关文档，知识覆盖完整
- 部分覆盖：1-3条相关文档，存在明显缺失
- 缺失：无相关文档或相似度太低

请进行严格评估：
"""
    
    def _fallback_detection(self, doc_count: int) -> GapDetectionResult:
        """
        备用检测逻辑：当LLM分析失败时使用规则判断
        
        Args:
            doc_count: 文档数量
        
        Returns:
            GapDetectionResult: 基础检测结果
        """
        if doc_count >= 3:
            return GapDetectionResult(
                coverage_level="sufficient",
                relevant_documents=doc_count,
                coverage_score=0.85,
                identified_gaps=[],
                can_answer=True,
                confidence=0.9,
                reasoning=f"检索到{doc_count}条相关文档，覆盖度良好"
            )
        elif doc_count >= 1:
            return GapDetectionResult(
                coverage_level="partial",
                relevant_documents=doc_count,
                coverage_score=0.5,
                identified_gaps=[
                    KnowledgeGap(
                        aspect="详细信息",
                        description=f"仅找到{doc_count}条相关文档，可能不够全面",
                        suggestion="建议补充更多相关文献和资料"
                    )
                ],
                can_answer=True,
                confidence=0.7,
                reasoning=f"检索到{doc_count}条相关文档，存在一定缺口"
            )
        else:
            return GapDetectionResult(
                coverage_level="missing",
                relevant_documents=0,
                coverage_score=0.0,
                identified_gaps=[
                    KnowledgeGap(
                        aspect="全部内容",
                        description="知识库中未找到相关信息",
                        suggestion="需要收集该领域的系统资料"
                    )
                ],
                can_answer=False,
                confidence=0.95,
                reasoning="未检索到任何相关文档"
            )
    
    def generate_gap_report(
        self,
        question: str,
        gap_result: GapDetectionResult
    ) -> str:
        """
        生成知识缺口报告（人类可读格式）
        
        Args:
            question: 用户问题
            gap_result: 缺口检测结果
        
        Returns:
            str: 缺口报告
        """
        if gap_result.coverage_level == "sufficient":
            return ""
        
        report_parts = [f"⚠️ 知识缺口提示"]
        report_parts.append(f"\n针对您的问题「{question}」，当前知识库覆盖情况：")
        report_parts.append(f"\n覆盖程度：{self._get_coverage_label(gap_result.coverage_level)}")
        report_parts.append(f"相关文档：{gap_result.relevant_documents}条")
        
        if gap_result.identified_gaps:
            report_parts.append(f"\n识别到的知识缺口：")
            for i, gap in enumerate(gap_result.identified_gaps, 1):
                report_parts.append(f"\n{i}. {gap.aspect}")
                report_parts.append(f"   描述：{gap.description}")
                report_parts.append(f"   建议：{gap.suggestion}")
        
        if not gap_result.can_answer:
            report_parts.append(f"\n💡 温馨提示：由于知识库信息不足，回答可能不够完整，")
            report_parts.append(f"   建议参考上述建议方向补充相关资料。")
        
        return "\n".join(report_parts)
    
    def _get_coverage_label(self, level: str) -> str:
        """获取覆盖程度标签"""
        labels = {
            "sufficient": "✅ 充足",
            "partial": "⚠️ 部分覆盖",
            "missing": "❌ 缺失"
        }
        return labels.get(level, level)
    
    def should_retry_retrieval(
        self,
        gap_result: GapDetectionResult,
        max_retries: int = 2
    ) -> bool:
        """
        判断是否应该重新检索
        
        Args:
            gap_result: 缺口检测结果
            max_retries: 最大重试次数
        
        Returns:
            bool: 是否应该重试
        """
        # 缺失情况需要重试
        if gap_result.coverage_level == "missing":
            return True
        
        # 部分覆盖且置信度低时重试
        if gap_result.coverage_level == "partial" and gap_result.confidence < 0.6:
            return True
        
        return False
    
    def get_supplementary_queries(
        self,
        question: str,
        gap_result: GapDetectionResult
    ) -> List[str]:
        """
        生成补充检索的查询词
        
        Args:
            question: 用户问题
            gap_result: 缺口检测结果
        
        Returns:
            List[str]: 补充查询词列表
        """
        if gap_result.identified_gaps:
            return [gap.suggestion for gap in gap_result.identified_gaps]
        
        # 如果没有识别的缺口，返回一些通用的补充查询
        return [
            f"{question}的历史背景",
            f"{question}的制作技艺",
            f"{question}的传承现状"
        ]
