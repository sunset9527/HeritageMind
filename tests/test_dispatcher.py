"""
测试调度Agent
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.dispatcher import DispatcherAgent, QuestionAnalysis


class TestDispatcherAgent:
    """测试调度Agent"""
    
    @pytest.fixture
    def dispatcher(self):
        """创建调度Agent实例"""
        # 使用mock LLM避免实际API调用
        with patch('src.agents.dispatcher.ChatOpenAI'):
            agent = DispatcherAgent()
            return agent
    
    def test_analyze_question_craft(self, dispatcher):
        """测试技艺相关问题分析"""
        question = "景泰蓝的制作流程是什么？"
        result = dispatcher.analyze_question(question)
        
        assert isinstance(result, QuestionAnalysis)
        assert result.complexity in ["simple", "medium", "complex"]
        assert isinstance(result.required_experts, list)
    
    def test_analyze_question_history(self, dispatcher):
        """测试历史相关问题分析"""
        question = "苏绣起源于哪个朝代？"
        result = dispatcher.analyze_question(question)
        
        assert isinstance(result, QuestionAnalysis)
        assert "history_expert" in result.required_experts or len(result.required_experts) > 0
    
    def test_fallback_analysis(self, dispatcher):
        """测试备用分析逻辑"""
        # 模拟LLM失败时的关键词匹配
        question = "如何学习龙泉青瓷？"
        result = dispatcher._fallback_analysis(question)
        
        assert isinstance(result, QuestionAnalysis)
        assert len(result.required_experts) > 0
        assert result.complexity in ["simple", "medium", "complex"]
    
    def test_fuse_responses_single(self, dispatcher):
        """测试单一响应融合"""
        responses = {
            "craft_expert": "这是技艺知识专家的回答。"
        }
        
        result = dispatcher.fuse_responses(responses, "测试问题")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "技艺知识" in result or "craft_expert" in result.lower()
    
    def test_fuse_responses_multiple(self, dispatcher):
        """测试多响应融合"""
        responses = {
            "craft_expert": "技艺知识：制作流程包括制胎、掐丝、点蓝等步骤。",
            "history_expert": "历史文化：景泰蓝起源于元代，在明代达到鼎盛。"
        }
        
        result = dispatcher.fuse_responses(responses, "景泰蓝是什么？")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_should_include_narrative_explicit(self, dispatcher):
        """测试显式请求叙事模式"""
        question = "请讲讲景泰蓝的故事"
        
        result = dispatcher.should_include_narrative(question, include_narrative=True)
        assert result is True
    
    def test_should_include_narrative_keyword(self, dispatcher):
        """测试关键词触发叙事模式"""
        question = "师傅讲讲景泰蓝"
        
        result = dispatcher.should_include_narrative(question)
        assert result is True
    
    def test_should_include_narrative_false(self, dispatcher):
        """测试不触发叙事模式"""
        question = "景泰蓝的制作流程是什么？"
        
        result = dispatcher.should_include_narrative(question)
        assert result is False
    
    def test_add_source_annotations(self, dispatcher):
        """测试来源标注"""
        content = "这是回答内容。"
        agent_names = ["craft_expert", "history_expert"]
        
        result = dispatcher.add_source_annotations(content, agent_names)
        
        assert "content" in result
        assert "source_agents" in result
        assert len(result["source_agents"]) == 2
    
    def test_get_agent_type(self, dispatcher):
        """测试Agent类型映射"""
        assert dispatcher._get_agent_type("craft_expert") == "技艺知识专家"
        assert dispatcher._get_agent_type("history_expert") == "历史文化专家"
        assert dispatcher._get_agent_type("heritage_expert") == "传承现状专家"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
