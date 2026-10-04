from pathlib import Path

FILES = {}

FILES["backend/app/schemas/call.py"] = '''from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CallStart(BaseModel):
    agent_id: str


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str | None
    status: str
    channel: str
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    call_id: str
    role: str
    content: str
    tool_traces: list
    meta: dict
    created_at: datetime


class CallDetail(CallOut):
    messages: list[MessageOut] = []


class CallMessageIn(BaseModel):
    content: str = Field(..., min_length=1)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")