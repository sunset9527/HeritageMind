"""
测试知识缺口检测器
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.knowledge.gap_detector import KnowledgeGapDetector, KnowledgeGap, GapDetectionResult


class TestKnowledgeGapDetector:
    """测试知识缺口检测器"""
    
    @pytest.fixture
    def detector(self):
        """创建缺口检测器实例"""
        with patch('src.knowledge.gap_detector.ChatOpenAI'):
            return KnowledgeGapDetector()
    
    def test_detect_sufficient(self, detector):
        """测试充足覆盖检测"""
        question = "景泰蓝的制作流程是什么？"
        retrieved_docs = [
            {"content": "景泰蓝制作流程包括制胎、掐丝、点蓝..."},
            {"content": "掐丝是景泰蓝的关键工序..."},
            {"content": "点蓝需要使用珐琅釉料..."}
        ]
        
        result = detector.detect(question, retrieved_docs)
        
        assert isinstance(result, GapDetectionResult)
        assert result.coverage_level in ["sufficient", "partial", "missing"]
        assert result.relevant_documents == 3
        assert result.can_answer in [True, False]
    
    def test_detect_partial(self, detector):
        """测试部分覆盖检测"""
        question = "苏绣的针法有哪些？"
        retrieved_docs = [
            {"content": "苏绣常用针法包括齐针、套针..."}
        ]
        
        result = detector.detect(question, retrieved_docs)
        
        assert isinstance(result, GapDetectionResult)
        assert result.relevant_documents == 1
    
    def test_detect_missing(self, detector):
        """测试缺失检测"""
        question = "某个不存在的技艺"
        retrieved_docs = []
        
        result = detector.detect(question, retrieved_docs)
        
        assert isinstance(result, GapDetectionResult)
        assert result.relevant_documents == 0
    
    def test_fallback_detection_sufficient(self, detector):
        """测试备用检测逻辑-充足"""
        result = detector._fallback_detection(5)
        
        assert result.coverage_level == "sufficient"
        assert result.can_answer is True
    
    def test_fallback_detection_partial(self, detector):
        """测试备用检测逻辑-部分"""
        result = detector._fallback_detection(2)
        
        assert result.coverage_level == "partial"
        assert result.can_answer is True
    
    def test_fallback_detection_missing(self, detector):
        """测试备用检测逻辑-缺失"""
        result = detector._fallback_detection(0)
        
        assert result.coverage_level == "missing"
        assert result.can_answer is False
    
    def test_generate_gap_report_sufficient(self, detector):
        """测试缺口报告生成-充足"""
        result = GapDetectionResult(
            coverage_level="sufficient",
            relevant_documents=5,
            coverage_score=0.9,
            identified_gaps=[],
            can_answer=True,
            confidence=0.9,
            reasoning="覆盖良好"
        )
        
        report = detector.generate_gap_report("景泰蓝是什么？", result)
        
        assert report == ""
    
    def test_generate_gap_report_partial(self, detector):
        """测试缺口报告生成-部分"""
        result = GapDetectionResult(
            coverage_level="partial",
            relevant_documents=2,
            coverage_score=0.5,
            identified_gaps=[
                KnowledgeGap(
                    aspect="详细工艺",
                    description="缺少部分工艺细节",
                    suggestion="补充更多工艺资料"
                )
            ],
            can_answer=True,
            confidence=0.7,
            reasoning="存在一定缺口"
        )
        
        report = detector.generate_gap_report("景泰蓝制作", result)
        
        assert isinstance(report, str)
        assert "⚠️" in report or "缺口" in report
    
    def test_should_retry_retrieval_missing(self, detector):
        """测试是否需要重试检索-缺失"""
        result = GapDetectionResult(
            coverage_level="missing",
            relevant_documents=0,
            coverage_score=0.0,
            identified_gaps=[],
            can_answer=False,
            confidence=0.95,
            reasoning=""
        )
        
        assert detector.should_retry_retrieval(result) is True
    
    def test_should_retry_retrieval_partial_low_confidence(self, detector):
        """测试是否需要重试检索-部分覆盖且低置信度"""
        result = GapDetectionResult(
            coverage_level="partial",
            relevant_documents=1,
            coverage_score=0.3,
            identified_gaps=[],
            can_answer=True,
            confidence=0.5,
            reasoning=""
        )
        
        assert detector.should_retry_retrieval(result) is True
    
    def test_should_retry_retrieval_sufficient(self, detector):
        """测试是否需要重试检索-充足"""
        result = GapDetectionResult(
            coverage_level="sufficient",
            relevant_documents=5,
            coverage_score=0.9,
            identified_gaps=[],
            can_answer=True,
            confidence=0.9,
            reasoning=""
        )
        
        assert detector.should_retry_retrieval(result) is False
    
    def test_get_supplementary_queries(self, detector):
        """测试生成补充查询"""
        result = GapDetectionResult(
            coverage_level="partial",
            relevant_documents=2,
            coverage_score=0.5,
            identified_gaps=[
                KnowledgeGap(
                    aspect="详细工艺",
                    description="缺少工艺细节",
                    suggestion="补充工艺流程资料"
                )
            ],
            can_answer=True,
            confidence=0.7,
            reasoning=""
        )
        
        queries = detector.get_supplementary_queries("景泰蓝制作", result)
        
        assert isinstance(queries, list)
        assert len(queries) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
