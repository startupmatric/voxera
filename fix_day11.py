from pathlib import Path

FILES = {}

# ---------------- Model ----------------

FILES["backend/app/models/debug_report.py"] = '''from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_str


class DebugReport(Base, TimestampMixin):
    __tablename__ = "debug_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    call_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("calls.id", ondelete="CASCADE"), nullable=True, index=True
    )
    evaluation_result_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    category: Mapped[str] = mapped_column(String(40), nullable=False)
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommendation: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
'''

FILES["backend/app/models/__init__.py"] = '''from .base import Base
from .organization import Organization
from .user import User
from .tenant import Tenant
from .agent import Agent
from .agent_version import AgentVersion
from .calendar_event import CalendarEvent
from .customer import Customer
from .lead import Lead
from .trace import Trace
from .call import Call
from .message import Message
from .evaluation import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationResult,
)
from .debug_report import DebugReport

__all__ = [
    "Base",
    "Organization",
    "User",
    "Tenant",
    "Agent",
    "AgentVersion",
    "CalendarEvent",
    "Customer",
    "Lead",
    "Trace",
    "Call",
    "Message",
    "EvaluationDataset",
    "EvaluationCase",
    "EvaluationRun",
    "EvaluationResult",
    "DebugReport",
]
'''

# ---------------- Debugger package ----------------

FILES["backend/app/debugger/__init__.py"] = ""

FILES["backend/app/debugger/classifier.py"] = '''"""
Deterministic classifier: inspects call traces + messages and returns
(category, stage, severity, root_cause, confidence).
"""

CATEGORY_STT      = "STT_FAILURE"
CATEGORY_LLM      = "LLM_FAILURE"
CATEGORY_TOOL     = "TOOL_FAILURE"
CATEGORY_TTS      = "TTS_FAILURE"
CATEGORY_TIMEOUT  = "TIMEOUT"
CATEGORY_VALID    = "VALIDATION_FAILURE"
CATEGORY_UNKNOWN  = "UNKNOWN"


def classify_call(call, traces, messages) -> dict:
    """
    Returns:
        {
          "category": str,
          "stage": str,
          "severity": str,        # low | medium | high | critical
          "root_cause": str,
          "confidence": float,    # 0..1
        }
    """
    # 1) Any error trace? Pick the most severe, prioritizing tool > llm > stt > tts
    error_traces = [t for t in traces if t.status == "error"]

    def _first(kinds):
        for t in error_traces:
            if t.kind in kinds:
                return t
        return None

    tool_err = _first({"tool"})
    llm_err  = _first({"llm"})
    stt_err  = _first({"stt"})
    tts_err  = _first({"tts"})

    if tool_err:
        return {
            "category": CATEGORY_TOOL,
            "stage": "tool_execution",
            "severity": "high",
            "root_cause": (
                f"Tool '{tool_err.name}' failed"
                + (f": {tool_err.error}" if tool_err.error else ".")
            ),
            "confidence": 0.98,
        }

    if llm_err:
        return {
            "category": CATEGORY_LLM,
            "stage": "llm",
            "severity": "high",
            "root_cause": (
                f"LLM step '{llm_err.name}' failed"
                + (f": {llm_err.error}" if llm_err.error else ".")
            ),
            "confidence": 0.95,
        }

    if stt_err:
        return {
            "category": CATEGORY_STT,
            "stage": "stt",
            "severity": "medium",
            "root_cause": (
                f"Speech-to-text failed"
                + (f": {stt_err.error}" if stt_err.error else ".")
            ),
            "confidence": 0.9,
        }

    if tts_err:
        return {
            "category": CATEGORY_TTS,
            "stage": "tts",
            "severity": "medium",
            "root_cause": (
                f"Text-to-speech failed"
                + (f": {tts_err.error}" if tts_err.error else ".")
            ),
            "confidence": 0.9,
        }

    # 2) Latency: any single trace over 5 minutes?
    slow = [t for t in traces if (t.latency_ms or 0) > 300_000]
    if slow:
        worst = max(slow, key=lambda t: t.latency_ms or 0)
        return {
            "category": CATEGORY_TIMEOUT,
            "stage": "llm",
            "severity": "medium",
            "root_cause": (
                f"Step '{worst.name}' took {worst.latency_ms/1000:.1f}s (over 300s cap)."
            ),
            "confidence": 0.85,
        }

    # 3) Empty conversation
    user_msgs = [m for m in messages if m.role == "user"]
    asst_msgs = [m for m in messages if m.role == "assistant"]
    if not user_msgs and not asst_msgs:
        return {
            "category": CATEGORY_VALID,
            "stage": "input",
            "severity": "low",
            "root_cause": "Call contains no user or assistant messages.",
            "confidence": 0.7,
        }

    # 4) No issues
    return {
        "category": CATEGORY_UNKNOWN,
        "stage": "output",
        "severity": "low",
        "root_cause": "No failures detected in this call.",
        "confidence": 1.0,
    }
'''

FILES["backend/app/debugger/evidence.py"] = '''def collect_evidence(traces, messages, limit: int = 10) -> list[dict]:
    """
    Return a small list of evidence items:
      - failed traces
      - error strings
      - last few messages
    """
    evidence: list[dict] = []

    # error traces first
    for t in traces:
        if t.status == "error":
            evidence.append({
                "type": "trace",
                "trace_id": t.id,
                "kind": t.kind,
                "name": t.name,
                "status": t.status,
                "latency_ms": t.latency_ms,
                "error": t.error,
                "input": t.input_data or {},
                "output": t.output_data or {},
            })

    # successful tool traces (context)
    for t in traces:
        if t.kind == "tool" and t.status == "success" and len(evidence) < limit:
            evidence.append({
                "type": "trace",
                "trace_id": t.id,
                "kind": t.kind,
                "name": t.name,
                "status": t.status,
                "latency_ms": t.latency_ms,
            })

    # last few messages
    for m in messages[-4:]:
        evidence.append({
            "type": "message",
            "message_id": m.id,
            "role": m.role,
            "content": (m.content or "")[:500],
        })

    return evidence[:limit]
'''

FILES["backend/app/debugger/recommendations.py"] = '''def recommend(category: str) -> list[str]:
    if category == "TOOL_FAILURE":
        return [
            "Inspect the failed tool's input schema and error output.",
            "Add retry/backoff for transient failures (network, API timeouts).",
            "Verify credentials and endpoints for external integrations.",
            "If the tool failed on bad arguments, refine the tool description so the LLM passes valid inputs.",
        ]
    if category == "LLM_FAILURE":
        return [
            "Check the LLM provider status and rate limits.",
            "Reduce the system prompt size if it exceeds the context window.",
            "Lower temperature if the model is producing unstable outputs.",
            "Try a larger model if the failure is due to reasoning depth.",
        ]
    if category == "STT_FAILURE":
        return [
            "Ensure the microphone is not muted and the browser has permission.",
            "Check that the audio format is supported (WebM/Opus → WAV via ffmpeg).",
            "Increase the recording length; very short clips are often rejected.",
            "Verify Whisper service health: `docker compose logs whisper`.",
        ]
    if category == "TTS_FAILURE":
        return [
            "Verify the Piper service is reachable.",
            "Check that the requested voice is installed.",
            "Review Piper logs for decode/format errors.",
        ]
    if category == "TIMEOUT":
        return [
            "Raise the client/nginx timeout if the model is simply slow.",
            "Reduce the system prompt or tool set to shorten generation.",
            "Consider a smaller model or GPU acceleration.",
        ]
    if category == "VALIDATION_FAILURE":
        return [
            "Check that the call has user input before expecting a response.",
            "Verify the agent's system prompt is not blocking all responses.",
        ]
    return [
        "No specific failure detected. Review the full trace timeline for anomalies.",
    ]
'''

FILES["backend/app/debugger/service.py"] = '''from sqlalchemy.orm import Session

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
'''

FILES["backend/app/debugger/analyzer.py"] = '''from .service import analyze_call, analyze_evaluation_result

__all__ = ["analyze_call", "analyze_evaluation_result"]
'''

# ---------------- Schemas ----------------

FILES["backend/app/schemas/debug.py"] = '''from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DebugReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    call_id: str | None
    evaluation_result_id: str | None
    category: str
    stage: str
    severity: str
    root_cause: str
    evidence: list
    recommendation: list
    confidence: float
    created_at: datetime
'''

# ---------------- Router ----------------

FILES["backend/app/routers/debug.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..debugger.analyzer import analyze_call, analyze_evaluation_result
from ..models import DebugReport, Tenant
from ..schemas.debug import DebugReportOut

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/calls/{call_id}", response_model=DebugReportOut)
def debug_call(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    try:
        report = analyze_call(db, tenant.id, call_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return report


@router.get("/calls/{call_id}", response_model=DebugReportOut)
def get_call_debug(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    report = (
        db.query(DebugReport)
        .filter(DebugReport.call_id == call_id, DebugReport.tenant_id == tenant.id)
        .order_by(DebugReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No debug report for this call yet")
    return report


@router.post("/evaluation-results/{result_id}", response_model=DebugReportOut)
def debug_evaluation_result(
    result_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    try:
        report = analyze_evaluation_result(db, tenant.id, result_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return report


@router.get("/reports", response_model=list[DebugReportOut])
def list_reports(
    limit: int = 100,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(DebugReport)
        .filter(DebugReport.tenant_id == tenant.id)
        .order_by(DebugReport.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
'''

# ---------------- Update main.py ----------------

FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import (
    agents,
    calls,
    chat,
    debug,
    evaluations,
    me,
    organizations,
    tenants,
    traces,
    users,
    ws_calls,
)

app = FastAPI(title=settings.app_name, version="0.11.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voxera"}


@app.get("/health/database")
def health_database():
    return {"status": "ok" if check_database() else "error", "service": "postgres"}


@app.get("/health/redis")
def health_redis():
    return {"status": "ok" if check_redis() else "error", "service": "redis"}


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.11.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(traces.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(calls.router)
app.include_router(evaluations.router)
app.include_router(debug.router)
app.include_router(ws_calls.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")