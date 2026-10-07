import time

from sqlalchemy.orm import Session

from ..models import (
    Agent,
    AgentVersion,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from ..runtime.runner import run_agent
from .evaluator import evaluate_case


def _active_version(db: Session, agent_id: str) -> AgentVersion | None:
    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent_id, AgentVersion.is_active.is_(True))
        .first()
    )


async def run_evaluation(dataset: EvaluationDataset, db: Session) -> EvaluationRun:
    """
    Execute every enabled case in the dataset against the agent's active version,
    persist results, and return the EvaluationRun.
    """
    agent: Agent | None = None
    if dataset.agent_id:
        agent = db.query(Agent).filter(Agent.id == dataset.agent_id).first()
    if not agent:
        raise ValueError("Dataset has no agent")

    version = _active_version(db, agent.id)

    run = EvaluationRun(
        dataset_id=dataset.id,
        agent_version_id=version.id if version else None,
        agent_version_number=version.version if version else None,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    cases = (
        db.query(EvaluationCase)
        .filter(EvaluationCase.dataset_id == dataset.id, EvaluationCase.enabled.is_(True))
        .all()
    )

    passed = 0
    failed = 0
    total_score = 0.0
    total_latency = 0.0
    count = 0

    for case in cases:
        t0 = time.time()
        actual_output = ""
        actual_tools: list[str] = []
        error_msg: str | None = None
        try:
            result = await run_agent(agent, db, case.input_text, history=None, enable_tools=True)
            actual_output = result.get("response") or ""
            actual_tools = [
                t.get("name") for t in (result.get("tool_traces") or []) if t.get("name")
            ]
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
        latency_ms = int((time.time() - t0) * 1000)

        outcome = evaluate_case(
            case_input=case.input_text,
            expected_output=case.expected_output,
            expected_tools=case.expected_tools or [],
            max_latency_ms=case.max_latency_ms,
            actual_output=actual_output,
            actual_tools=actual_tools,
            latency_ms=latency_ms,
            error=error_msg,
        )

        db.add(EvaluationResult(
            run_id=run.id,
            case_id=case.id,
            status=outcome["status"],
            score=outcome["score"],
            answer_score=outcome["answer_score"],
            tool_score=outcome["tool_score"],
            latency_score=outcome["latency_score"],
            error_score=outcome["error_score"],
            input_text=case.input_text,
            expected_output=case.expected_output,
            actual_output=outcome["actual_output"],
            expected_tools=case.expected_tools or [],
            actual_tools=outcome["actual_tools"],
            latency_ms=outcome["latency_ms"],
            error=outcome["error"],
        ))

        if outcome["status"] == "passed":
            passed += 1
        else:
            failed += 1
        total_score += outcome["score"]
        total_latency += latency_ms
        count += 1

    db.commit()

    run.total_cases = count
    run.passed_cases = passed
    run.failed_cases = failed
    run.pass_rate = (passed / count * 100.0) if count else 0.0
    run.average_score = (total_score / count) if count else 0.0
    run.avg_latency_ms = (total_latency / count) if count else 0.0
    run.status = "completed"

    # Regression: compare to previous completed run
    previous = (
        db.query(EvaluationRun)
        .filter(
            EvaluationRun.dataset_id == dataset.id,
            EvaluationRun.id != run.id,
            EvaluationRun.status == "completed",
        )
        .order_by(EvaluationRun.created_at.desc())
        .first()
    )
    if previous:
        score_delta = run.average_score - previous.average_score
        pass_delta = run.pass_rate - previous.pass_rate
        regression = score_delta < -5 or pass_delta < -10
        run.regression_detected = regression
        run.regression_details = {
            "previous_run_id": previous.id,
            "previous_version": previous.agent_version_number,
            "current_version": run.agent_version_number,
            "score_delta": score_delta,
            "pass_rate_delta": pass_delta,
            "previous_score": previous.average_score,
            "current_score": run.average_score,
            "previous_pass_rate": previous.pass_rate,
            "current_pass_rate": run.pass_rate,
        }

    db.commit()
    db.refresh(run)
    return run
