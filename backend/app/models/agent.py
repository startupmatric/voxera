from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_agents_tenant_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    model_provider: Mapped[str] = mapped_column(String(50), default="ollama", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="llama3", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    voice_language: Mapped[str] = mapped_column(String(10), default="en-US", nullable=False)
    stt_provider: Mapped[str] = mapped_column(String(50), default="whisper", nullable=False)
    tts_provider: Mapped[str] = mapped_column(String(50), default="piper", nullable=False)

    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="agents")
    versions: Mapped[list["AgentVersion"]] = relationship(
        "AgentVersion", back_populates="agent", cascade="all, delete-orphan"
    )
