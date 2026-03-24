"""
非遗多智能体知识问答系统
基于多智能体协作的非遗知识保存与传承平台
"""

from .dispatcher import DispatcherAgent
from .craft_expert import CraftExpertAgent
from .history_expert import HistoryExpertAgent
from .heritage_expert import HeritageExpertAgent
from .debate_engine import DebateEngine, DebateRound, DebateSession

__all__ = [
    "DispatcherAgent",
    "CraftExpertAgent",
    "HistoryExpertAgent",
    "HeritageExpertAgent",
    "DebateEngine",
    "DebateRound",
    "DebateSession",
]
