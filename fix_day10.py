from pathlib import Path

FILES = {}

# ---------------- Models ----------------

FILES["backend/app/models/evaluation.py"] = '''from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class EvaluationDataset(Base, TimestampMixin):
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cases: Mapped[list["EvaluationCase"]] = relationship(
        "EvaluationCase", back_populates="dataset", cascade="all, delete-orphan"
    )
    runs: Mapped[list["EvaluationRun"]] = relationship(
        "EvaluationRun", back_populates="dataset", cascade="all, delete-orphan"
    )


class EvaluationCase(Base, TimestampMixin):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    max_latency_ms: Mapped[int] = mapped_column(Integer, default=120000, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset", back_populates="cases")


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    agent_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    regression_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    regression_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset", back_populates="runs")
    results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base, TimestampMixin):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    answer_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tool_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    input_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    expected_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    actual_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="results")
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
]
'''

# ---------------- Schemas ----------------

FILES["backend/app/schemas/evaluation.py"] = '''from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    agent_id: str | None = None


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str | None
    name: str
    description: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    input_text: str = Field(..., min_length=1)
    expected_output: str | None = None
    expected_tools: list[str] = []
    max_latency_ms: int = Field(120000, ge=1000, le=600000)
    enabled: bool = True


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str
    input_text: str
    expected_output: str | None
    expected_tools: list
    max_latency_ms: int
    enabled: bool
    created_at: datetime


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str | None
    status: str
    score: float
    answer_score: float
    tool_score: float
    latency_score: float
    error_score: float
    input_text: str
    expected_output: str | None
    actual_output: str | None
    expected_tools: list
    actual_tools: list
    latency_ms: float
    error: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    agent_version_id: str | None
    agent_version_number: int | None
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_score: float
    avg_latency_ms: float
    regression_detected: bool
    regression_details: dict
    created_at: datetime


class RunDetail(RunOut):
    results: list[ResultOut] = []
'''

# ---------------- Runner / Scoring ----------------

FILES["backend/app/evaluation/__init__.py"] = ""

FILES["backend/app/evaluation/scoring.py"] = '''def score_answer(actual: str | None, expected: str | None) -> float:
    """40 points if the expected substring appears in the actual output."""
    if not expected:
        return 40.0
    if not actual:
        return 0.0
    return 40.0 if expected.lower() in actual.lower() else 0.0


def score_tools(actual_tools: list[str], expected_tools: list[str]) -> float:
    """30 points if every expected tool was called."""
    if not expected_tools:
        return 30.0
    actual_set = set(actual_tools or [])
    expected_set = set(expected_tools)
    return 30.0 if expected_set.issubset(actual_set) else 0.0


def score_latency(latency_ms: float, max_latency_ms: int) -> float:
    """20 points if latency under the cap."""
    return 20.0 if latency_ms <= max_latency_ms else 0.0


def score_error(error: str | None) -> float:
    """10 points if no error occurred."""
    return 10.0 if not error else 0.0


def total_score(answer: float, tools: float, latency: float, error: float) -> float:
    return answer + tools + latency + error


def is_pass(score: float) -> bool:
    return score >= 70.0
'''

FILES["backend/app/evaluation/evaluator.py"] = '''from .scoring import (
    is_pass,
    score_answer,
    score_error,
    score_latency,
    score_tools,
    total_score,
)


def evaluate_case(
    case_input: str,
    expected_output: str | None,
    expected_tools: list[str],
    max_latency_ms: int,
    actual_output: str | None,
    actual_tools: list[str],
    latency_ms: float,
    error: str | None,
) -> dict:
    answer = score_answer(actual_output, expected_output)
    tools = score_tools(actual_tools, expected_tools)
    latency = score_latency(latency_ms, max_latency_ms)
    err = score_error(error)
    total = total_score(answer, tools, latency, err)
    passed = is_pass(total)

    return {
        "status": "passed" if passed else "failed",
        "score": total,
        "answer_score": answer,
        "tool_score": tools,
        "latency_score": latency,
        "error_score": err,
        "actual_output": actual_output,
        "actual_tools": actual_tools,
        "latency_ms": latency_ms,
        "error": error,
    }
'''

FILES["backend/app/evaluation/runner.py"] = '''import time

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
'''

# ---------------- Router ----------------

FILES["backend/app/routers/evaluations.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..evaluation.runner import run_evaluation
from ..models import (
    Agent,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    Tenant,
)
from ..schemas.evaluation import (
    CaseCreate,
    CaseOut,
    DatasetCreate,
    DatasetOut,
    ResultOut,
    RunDetail,
    RunOut,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _load_dataset(db: Session, dataset_id: str, tenant_id: str) -> EvaluationDataset:
    dataset = (
        db.query(EvaluationDataset)
        .filter(EvaluationDataset.id == dataset_id, EvaluationDataset.tenant_id == tenant_id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("", response_model=list[DatasetOut])
def list_datasets(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(EvaluationDataset)
        .filter(EvaluationDataset.tenant_id == tenant.id)
        .order_by(EvaluationDataset.created_at.desc())
        .all()
    )


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = None
    if payload.agent_id:
        agent = db.query(Agent).filter(Agent.id == payload.agent_id, Agent.tenant_id == tenant.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

    dataset = EvaluationDataset(
        tenant_id=tenant.id,
        agent_id=agent.id if agent else None,
        name=payload.name,
        description=payload.description,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return _load_dataset(db, dataset_id, tenant.id)


@router.get("/{dataset_id}/cases", response_model=list[CaseOut])
def list_cases(
    dataset_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    return (
        db.query(EvaluationCase)
        .filter(EvaluationCase.dataset_id == dataset_id)
        .order_by(EvaluationCase.created_at.asc())
        .all()
    )


@router.post("/{dataset_id}/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    dataset_id: str,
    payload: CaseCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    case = EvaluationCase(
        dataset_id=dataset_id,
        name=payload.name,
        input_text=payload.input_text,
        expected_output=payload.expected_output,
        expected_tools=payload.expected_tools,
        max_latency_ms=payload.max_latency_ms,
        enabled=payload.enabled,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{dataset_id}/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    dataset_id: str,
    case_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    case = (
        db.query(EvaluationCase)
        .filter(EvaluationCase.id == case_id, EvaluationCase.dataset_id == dataset_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return None


@router.post("/{dataset_id}/run", response_model=RunOut)
async def start_run(
    dataset_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    dataset = _load_dataset(db, dataset_id, tenant.id)
    try:
        run = await run_evaluation(dataset, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")
    return run


@router.get("/{dataset_id}/runs", response_model=list[RunOut])
def list_runs(
    dataset_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    return (
        db.query(EvaluationRun)
        .filter(EvaluationRun.dataset_id == dataset_id)
        .order_by(EvaluationRun.created_at.desc())
        .all()
    )


@router.get("/{dataset_id}/runs/{run_id}", response_model=RunDetail)
def get_run(
    dataset_id: str,
    run_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.id == run_id, EvaluationRun.dataset_id == dataset_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{dataset_id}/runs/{run_id}/results", response_model=list[ResultOut])
def list_results(
    dataset_id: str,
    run_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_dataset(db, dataset_id, tenant.id)
    run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.id == run_id, EvaluationRun.dataset_id == dataset_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return (
        db.query(EvaluationResult)
        .filter(EvaluationResult.run_id == run_id)
        .order_by(EvaluationResult.created_at.asc())
        .all()
    )
'''

# ---------------- Register router in main ----------------

FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import (
    agents,
    calls,
    chat,
    evaluations,
    me,
    organizations,
    tenants,
    users,
    ws_calls,
)

app = FastAPI(title=settings.app_name, version="0.10.0")

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
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.10.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(calls.router)
app.include_router(evaluations.router)
app.include_router(ws_calls.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")