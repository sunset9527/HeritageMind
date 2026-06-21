"""
知识模块 - 知识缺口检测、多粒度控制、叙事生成
"""

from .gap_detector import KnowledgeGapDetector
from .granularity import GranularityController
from .narrative import NarrativeGenerator

__all__ = [
    "KnowledgeGapDetector",
    "GranularityController",
    "NarrativeGenerator",
]
