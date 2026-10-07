from fastapi import APIRouter, Depends, HTTPException, status
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
