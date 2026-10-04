from pathlib import Path

FILES = {}

FILES["backend/app/models/call.py"] = '''from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="simulated", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="call", cascade="all, delete-orphan", order_by="Message.created_at"
    )
'''

FILES["backend/app/models/message.py"] = '''from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    call_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | tool | system
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_traces: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    call: Mapped["Call"] = relationship("Call", back_populates="messages")
'''

FILES["backend/app/models/__init__.py"] = '''from .base import Base
from .organization import Organization
from .user import User
from .tenant import Tenant
from .agent import Agent
from .agent_version import AgentVersion
from .calendar_event import CalendarEvent
from .customer import Customer
from .lead import Lead
from .trace import Trace
from .call import Call
from .message import Message

__all__ = [
    "Base",
    "Organization",
    "User",
    "Tenant",
    "Agent",
    "AgentVersion",
    "CalendarEvent",
    "Customer",
    "Lead",
    "Trace",
    "Call",
    "Message",
]
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")