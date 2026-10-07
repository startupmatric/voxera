from fastapi import APIRouter, Depends, HTTPException, status
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
