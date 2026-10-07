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


class CallSummary(BaseModel):
    id: str
    tenant_id: str
    agent_id: str | None
    agent_name: str | None
    model_name: str | None
    status: str
    channel: str
    created_at: datetime
    updated_at: datetime
    duration_ms: int
    message_count: int
    trace_count: int
    metadata_json: dict


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


class TraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str | None
    call_id: str | None
    kind: str
    name: str
    status: str
    input_data: dict
    output_data: dict
    error: str | None
    latency_ms: float
    created_at: datetime


class TimelineEvent(BaseModel):
    ts: datetime
    kind: str         # lifecycle | message | trace
    name: str
    status: str
    latency_ms: float
    summary: str
    data: dict


class LatencyBreakdown(BaseModel):
    call_id: str
    total_ms: int
    llm_ms: int
    tools_ms: int
    stt_ms: int
    tts_ms: int
    other_ms: int
