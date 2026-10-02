from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_tenants_org_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="tenants")
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="tenant", cascade="all, delete-orphan"
    )
