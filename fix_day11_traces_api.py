from pathlib import Path

content = '''from fastapi import APIRouter, Depends, Query
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
'''

p = Path("backend/app/routers/traces.py")
p.write_text(content, encoding="utf-8")
print("wrote", p)

# register the router in main.py
main = Path("backend/app/main.py")
text = main.read_text(encoding="utf-8")

if "traces" not in text.split("from .routers import")[1].split(")")[0]:
    text = text.replace(
        "    tenants,\n    users,",
        "    tenants,\n    traces,\n    users,",
        1,
    )
if "app.include_router(traces.router)" not in text:
    text = text.replace(
        "app.include_router(tenants.router)",
        "app.include_router(tenants.router)\napp.include_router(traces.router)",
        1,
    )

main.write_text(text, encoding="utf-8")
print("updated main.py")
print("has traces import:", "traces" in main.read_text(encoding="utf-8"))
