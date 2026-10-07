from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..models import Trace, Tenant

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("")
def list_traces(
    limit: int = Query(100, ge=1, le=500),
    kind: str | None = None,
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    q = db.query(Trace).filter(Trace.tenant_id == tenant.id)
    if kind:
        q = q.filter(Trace.kind == kind)
    if status:
        q = q.filter(Trace.status == status)

    rows = q.order_by(Trace.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "agent_id": r.agent_id,
            "call_id": r.call_id,
            "kind": r.kind,
            "name": r.name,
            "status": r.status,
            "latency_ms": r.latency_ms,
            "error": r.error,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
