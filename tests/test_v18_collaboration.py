import src.agents.debate_engine as debate_engine
from config import settings


class _Message:
    def __init__(self, content):
        self.content = content


class _Llm:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return _Message(self.response)


class _Agent:
    def __init__(self, response):
        self.llm = _Llm(response)


def test_collaboration_plan_uses_actual_participants_and_respects_message_cap():
    plan = debate_engine.build_collaboration_plan(
        ["history_expert", "craft_expert", "heritage_expert"], max_messages=2
    )

    assert [(message.from_agent, message.to_agent, message.kind) for message in plan] == [
        ("history_expert", "craft_expert", "challenge"),
        ("craft_expert", "history_expert", "response"),
    ]


def test_collaboration_plan_skips_when_fewer_than_two_participants():
    assert debate_engine.build_collaboration_plan(["craft_expert"], max_messages=3) == []


def test_dynamic_collaboration_updates_responses_and_emits_user_safe_messages():
    emitted = []
    agents = {
        "history_expert": _Agent("补充了年代依据。"),
        "craft_expert": _Agent("回应了工艺细节。"),
    }

    result = debate_engine.run_dynamic_collaboration(
        question="景泰蓝在明代如何发展？",
        initial_responses={"history_expert": "初答 A", "craft_expert": "初答 B"},
        agents=agents,
        max_messages=2,
        on_message=emitted.append,
    )

    assert [message.kind for message in result.messages] == ["challenge", "response"]
    assert result.responses["history_expert"] == "补充了年代依据。"
    assert emitted[0].summary == "补充了年代依据。"


def test_collaboration_message_cap_has_a_safe_default():
    assert settings.collaboration_max_messages == 3
