"""Deterministic, explainable process-quality scoring without an LLM."""

from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from src.models.evaluation import AnswerEvaluation


RULE_VERSION = "v1"


@dataclass(frozen=True)
class EvaluationDetail:
    code: str
    score: int
    max_score: int
    reason: str


@dataclass(frozen=True)
class EvaluationResult:
    total_score: int
    rule_version: str
    details: tuple[EvaluationDetail, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "rule_version": self.rule_version,
            "details": [detail.__dict__ for detail in self.details],
        }


def evaluate_response(
    *,
    answer: str,
    citations: Iterable[dict[str, Any]] | None,
    source_agents: Iterable[dict[str, Any]] | None,
    has_gaps: bool,
    gap_report: str,
    workflow_trace: Iterable[dict[str, Any]] | None,
) -> EvaluationResult:
    """Return a versioned process signal; it does not claim factual correctness."""
    answer_present = bool((answer or "").strip()) and len((answer or "").strip()) >= 8
    citation_count = len({str(item.get("title", "")).strip() for item in (citations or []) if item.get("title")})
    successful_agents = len({str(item.get("id", "")).strip() for item in (source_agents or []) if item.get("id")})
    statuses = {str(item.get("status", "")) for item in (workflow_trace or [])}
    workflow_healthy = not statuses.intersection({"fallback", "error"})
    gap_disclosed = bool((gap_report or "").strip())

    details = (
        EvaluationDetail("answer_present", 20 if answer_present else 0, 20, "回答已生成" if answer_present else "回答为空或过短"),
        EvaluationDetail("evidence_available", 25 if citation_count else 0, 25, "存在可追溯引用" if citation_count else "未提供引用"),
        EvaluationDetail("experts_completed", min(successful_agents, 2) * 10, 20, f"{successful_agents} 位专家进入最终来源"),
        EvaluationDetail("workflow_resilient", 20 if workflow_healthy else 10, 20, "未检测到降级" if workflow_healthy else "工作流发生安全降级"),
        EvaluationDetail(
            "gap_handled",
            15 if not has_gaps or gap_disclosed else 0,
            15,
            "无知识缺口" if not has_gaps else ("已明确说明知识缺口" if gap_disclosed else "缺口未说明"),
        ),
    )
    return EvaluationResult(
        total_score=sum(item.score for item in details), rule_version=RULE_VERSION, details=details
    )


def persist_evaluation(
    db: Session,
    *,
    chat_id: int,
    answer: str,
    citations: Iterable[dict[str, Any]] | None,
    source_agents: Iterable[dict[str, Any]] | None,
    has_gaps: bool,
    gap_report: str,
    workflow_trace: Iterable[dict[str, Any]] | None,
) -> AnswerEvaluation:
    """Create or refresh the one deterministic evaluation for a saved answer."""
    result = evaluate_response(
        answer=answer,
        citations=citations,
        source_agents=source_agents,
        has_gaps=has_gaps,
        gap_report=gap_report,
        workflow_trace=workflow_trace,
    )
    evaluation = db.query(AnswerEvaluation).filter(AnswerEvaluation.chat_id == chat_id).first()
    if evaluation is None:
        evaluation = AnswerEvaluation(chat_id=chat_id)
        db.add(evaluation)
    evaluation.total_score = result.total_score
    evaluation.rule_version = result.rule_version
    evaluation.score_details = [detail.__dict__ for detail in result.details]
    db.flush()
    return evaluation
