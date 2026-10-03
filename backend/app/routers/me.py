from datetime import datetime

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
