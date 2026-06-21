"""
测试多粒度控制器
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.knowledge.granularity import GranularityController


class TestGranularityController:
    """测试多粒度控制器"""
    
    @pytest.fixture
    def controller(self):
        """创建控制器实例"""
        with patch('src.knowledge.granularity.ChatOpenAI'):
            return GranularityController()
    
    def test_adapt_content_curious(self, controller):
        """测试好奇者内容适配"""
        base_content = "景泰蓝是一种传统工艺品，起源于元代..."
        question = "景泰蓝是什么？"
        
        result = controller.adapt_content(base_content, "curious", question)
        
        assert isinstance(result, dict)
        assert "content" in result
        assert result.get("user_profile") == "curious"
        assert result.get("profile_name") == "好奇者"
    
    def test_adapt_content_learner(self, controller):
        """测试学习者内容适配"""
        base_content = "景泰蓝制作包括制胎、掐丝、点蓝、烧蓝、磨光、镀金等工序..."
        question = "如何学习景泰蓝？"
        
        result = controller.adapt_content(base_content, "learner", question)
        
        assert isinstance(result, dict)
        assert result.get("user_profile") == "learner"
        assert result.get("profile_name") == "学习者"
    
    def test_adapt_content_researcher(self, controller):
        """测试研究者内容适配"""
        base_content = "景泰蓝工艺的历史演变经历了元明清三个时期..."
        question = "景泰蓝工艺的历史研究"
        
        result = controller.adapt_content(base_content, "researcher", question)
        
        assert isinstance(result, dict)
        assert result.get("user_profile") == "researcher"
        assert result.get("profile_name") == "研究者"
    
    def test_get_profile_info(self, controller):
        """测试获取画像信息"""
        info = controller.get_profile_info("curious")
        
        assert isinstance(info, dict)
        assert info.get("name") == "好奇者"
        assert "depth" in info
        assert "focus" in info
    
    def test_get_profile_info_invalid(self, controller):
        """测试无效画像"""
        info = controller.get_profile_info("invalid_profile")
        
        assert isinstance(info, dict)
        assert info.get("name") == "好奇者"  # 返回默认
    
    def test_list_profiles(self, controller):
        """测试列出所有画像"""
        profiles = controller.list_profiles()
        
        assert isinstance(profiles, list)
        assert len(profiles) == 3
        
        profile_ids = [p["id"] for p in profiles]
        assert "curious" in profile_ids
        assert "learner" in profile_ids
        assert "researcher" in profile_ids
    
    def test_estimate_reading_time(self, controller):
        """测试估算阅读时间"""
        # 400字约1分钟
        content_short = "这是简短内容。"  # ~10字
        content_medium = "A" * 400  # ~400字
        content_long = "A" * 800  # ~800字
        
        assert controller.estimate_reading_time(content_short) == 1
        assert controller.estimate_reading_time(content_medium) == 1
        assert controller.estimate_reading_time(content_long) == 2
    
    def test_add_toc_to_long_content(self, controller):
        """测试为长内容添加目录"""
        content = """景泰蓝工艺

## 一、历史起源

元代传入中国

## 二、制作流程

1. 制胎
2. 掐丝

## 三、传承现状

传承人数量
"""
        result = controller.add_toc(content, "learner")
        
        assert "## 目录" in result
    
    def test_add_toc_to_short_content(self, controller):
        """测试为短内容添加目录（不应添加）"""
        content = "这是简短内容。"
        result = controller.add_toc(content, "curious")
        
        assert result == content  # 不应添加目录


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
