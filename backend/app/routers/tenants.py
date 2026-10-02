from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Organization, Tenant
from ..schemas.tenant import TenantCreate, TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == payload.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    exists = (
        db.query(Tenant)
        .filter(Tenant.organization_id == payload.organization_id, Tenant.slug == payload.slug)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Tenant slug already exists in organization")
    tenant = Tenant(
        organization_id=payload.organization_id, name=payload.name, slug=payload.slug
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("", response_model=list[TenantOut])
def list_tenants(organization_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Tenant)
    if organization_id:
        q = q.filter(Tenant.organization_id == organization_id)
    return q.order_by(Tenant.created_at.desc()).all()


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
