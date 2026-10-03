from pathlib import Path

FILES = {}

FILES["backend/app/routers/me.py"] = '''from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import Agent, Organization, Tenant, User

router = APIRouter(prefix="/me", tags=["me"])


class StatsResponse(BaseModel):
    organization_id: str
    organization_name: str
    tenants_count: int
    users_count: int
    agents_count: int


class ActivityItem(BaseModel):
    kind: str
    id: str
    name: str
    tenant_id: str | None
    updated_at: datetime


@router.get("/stats", response_model=StatsResponse)
def stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    tenants_count = (
        db.query(func.count(Tenant.id))
        .filter(Tenant.organization_id == user.organization_id)
        .scalar()
        or 0
    )
    users_count = (
        db.query(func.count(User.id))
        .filter(User.organization_id == user.organization_id)
        .scalar()
        or 0
    )
    agents_count = (
        db.query(func.count(Agent.id))
        .join(Tenant, Agent.tenant_id == Tenant.id)
        .filter(Tenant.organization_id == user.organization_id)
        .scalar()
        or 0
    )
    return StatsResponse(
        organization_id=user.organization_id,
        organization_name=org.name if org else "Unknown",
        tenants_count=tenants_count,
        users_count=users_count,
        agents_count=agents_count,
    )


@router.get("/recent-activity", response_model=list[ActivityItem])
def recent_activity(
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Agent)
        .join(Tenant, Agent.tenant_id == Tenant.id)
        .filter(Tenant.organization_id == user.organization_id)
        .order_by(Agent.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ActivityItem(
            kind="agent",
            id=a.id,
            name=a.name,
            tenant_id=a.tenant_id,
            updated_at=a.updated_at,
        )
        for a in rows
    ]
'''

FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import agents, me, organizations, tenants, users

app = FastAPI(title=settings.app_name, version="0.4.0")

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
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.4.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(agents.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal backend files: {len(FILES)}")