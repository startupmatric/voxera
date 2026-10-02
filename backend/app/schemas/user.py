from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    organization_id: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    role: str = "member"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
