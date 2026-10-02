from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import require_roles
from ..auth.security import hash_password
from ..database import get_db
from ..models import Organization, User
from ..schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == payload.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    existing = (
        db.query(User)
        .filter(User.organization_id == payload.organization_id, User.email == payload.email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use for this organization")

    user = User(
        organization_id=payload.organization_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    _: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user