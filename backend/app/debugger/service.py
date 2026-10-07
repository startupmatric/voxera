from sqlalchemy.orm import Session

from ..models import Call, DebugReport, EvaluationResult, Message, Trace
from .classifier import classify_call
from .evidence import collect_evidence
from .recommendations import recommend


def _analyze(db: Session, tenant_id: str, call: Call) -> DebugReport:
    traces = (
        db.query(Trace)
        .filter(Trace.call_id == call.id, Trace.tenant_id == tenant_id)
        .order_by(Trace.created_at.asc())
        .all()
    )
    messages = (
        db.query(Message)
        .filter(Message.call_id == call.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    cls = classify_call(call, traces, messages)
    evidence = collect_evidence(traces, messages)
    recs = recommend(cls["category"])

    report = DebugReport(
        tenant_id=tenant_id,
        call_id=call.id,
        evaluation_result_id=None,
        category=cls["category"],
        stage=cls["stage"],
        severity=cls["severity"],
        root_cause=cls["root_cause"],
        evidence=evidence,
        recommendation=recs,
        confidence=cls["confidence"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def analyze_call(db: Session, tenant_id: str, call_id: str) -> DebugReport:
    call = (
        db.query(Call)
        .filter(Call.id == call_id, Call.tenant_id == tenant_id)
        .first()
    )
    if not call:
        raise ValueError("Call not found")
    return _analyze(db, tenant_id, call)


def analyze_evaluation_result(
    db: Session, tenant_id: str, result_id: str
) -> DebugReport:
    result = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == result_id)
        .first()
    )
    if not result:
        raise ValueError("Result not found")

    # Find the parent run to confirm tenant
    from ..models import EvaluationRun, EvaluationDataset
    run = db.query(EvaluationRun).filter(EvaluationRun.id == result.run_id).first()
    if not run:
        raise ValueError("Run not found")
    ds = db.query(EvaluationDataset).filter(EvaluationDataset.id == run.dataset_id).first()
    if not ds or ds.tenant_id != tenant_id:
        raise ValueError("Result not in tenant")

    # Reuse the classifier against the call (if any) or synthesize from the result itself
    call_id = None
    if result.actual_tools is not None and result.case_id:
        # Try to find the call linked to the same agent at the same time? Skip.
        pass

    # Simple approach: build a synthetic report from the result
    category = "LLM_FAILURE"
    stage = "llm"
    severity = "medium"
    root_cause = "Evaluation case failed."
    confidence = 0.7

    if result.expected_tools and set(result.expected_tools) - set(result.actual_tools or []):
        category = "LLM_FAILURE"
        stage = "llm"
        severity = "high"
        root_cause = (
            f"Expected tools {result.expected_tools} but got {result.actual_tools or []}."
        )
        confidence = 0.95
    elif result.error:
        category = "TOOL_FAILURE"
        stage = "tool_execution"
        severity = "high"
        root_cause = result.error
        confidence = 0.9
    elif result.expected_output and result.actual_output:
        if result.expected_output.lower() not in (result.actual_output or "").lower():
            category = "LLM_FAILURE"
            stage = "llm"
            severity = "medium"
            root_cause = (
                f"Answer did not contain '{result.expected_output}'."
            )
            confidence = 0.8

    evidence = [
        {
            "type": "evaluation_result",
            "result_id": result.id,
            "input_text": result.input_text,
            "expected_output": result.expected_output,
            "actual_output": result.actual_output,
            "expected_tools": result.expected_tools,
            "actual_tools": result.actual_tools,
            "latency_ms": result.latency_ms,
            "error": result.error,
        }
    ]
    recs = recommend(category)

    report = DebugReport(
        tenant_id=tenant_id,
        call_id=None,
        evaluation_result_id=result.id,
        category=category,
        stage=stage,
        severity=severity,
        root_cause=root_cause,
        evidence=evidence,
        recommendation=recs,
        confidence=confidence,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
