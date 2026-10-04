from datetime import datetime

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
