from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..models import Agent, Call, Message, Tenant, Trace
from ..schemas.call import (
    CallDetail,
    CallMessageIn,
    CallOut,
    CallStart,
    CallSummary,
    LatencyBreakdown,
    MessageOut,
    TimelineEvent,
    TraceOut,
)
from ..runtime.runner import run_agent

router = APIRouter(prefix="/calls", tags=["calls"])


def _load_call_for_tenant(db: Session, call_id: str, tenant_id: str) -> Call:
    call = (
        db.query(Call)
        .filter(Call.id == call_id, Call.tenant_id == tenant_id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


def _call_summary(db: Session, call: Call) -> dict:
    msg_count = (
        db.query(func.count(Message.id))
        .filter(Message.call_id == call.id)
        .scalar()
        or 0
    )
    trc_count = (
        db.query(func.count(Trace.id))
        .filter(Trace.call_id == call.id)
        .scalar()
        or 0
    )
    agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
    duration_ms = 0
    if call.created_at and call.updated_at:
        delta = call.updated_at - call.created_at
        duration_ms = int(delta.total_seconds() * 1000)

    return {
        "id": call.id,
        "tenant_id": call.tenant_id,
        "agent_id": call.agent_id,
        "agent_name": agent.name if agent else None,
        "model_name": agent.model_name if agent else None,
        "status": call.status,
        "channel": call.channel,
        "created_at": call.created_at,
        "updated_at": call.updated_at,
        "duration_ms": duration_ms,
        "message_count": msg_count,
        "trace_count": trc_count,
        "metadata_json": call.metadata_json or {},
    }


@router.post("", response_model=CallOut, status_code=status.HTTP_201_CREATED)
def start_call(
    payload: CallStart,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(Agent.id == payload.agent_id, Agent.tenant_id == tenant.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    call = Call(tenant_id=tenant.id, agent_id=agent.id, status="active", channel="simulated")
    db.add(call)
    db.commit()
    db.refresh(call)

    greeting = Message(
        call_id=call.id,
        role="assistant",
        content=f"Hi! I'm {agent.name}. How can I help you today?",
        tool_traces=[],
        meta={"greeting": True},
    )
    db.add(greeting)
    db.commit()

    return call


@router.get("", response_model=list[CallSummary])
def list_calls(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    calls = (
        db.query(Call)
        .filter(Call.tenant_id == tenant.id)
        .order_by(Call.created_at.desc())
        .all()
    )
    return [_call_summary(db, c) for c in calls]


@router.get("/{call_id}", response_model=CallSummary)
def get_call(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = _load_call_for_tenant(db, call_id, tenant.id)
    return _call_summary(db, call)


@router.get("/{call_id}/messages", response_model=list[MessageOut])
def get_call_messages(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_call_for_tenant(db, call_id, tenant.id)
    return (
        db.query(Message)
        .filter(Message.call_id == call_id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.get("/{call_id}/traces", response_model=list[TraceOut])
def get_call_traces(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_call_for_tenant(db, call_id, tenant.id)
    return (
        db.query(Trace)
        .filter(Trace.call_id == call_id)
        .order_by(Trace.created_at.asc())
        .all()
    )


@router.get("/{call_id}/timeline", response_model=list[TimelineEvent])
def get_call_timeline(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = _load_call_for_tenant(db, call_id, tenant.id)

    events: list[dict] = []

    # Lifecycle
    if call.created_at:
        events.append({
            "ts": call.created_at,
            "kind": "lifecycle",
            "name": "CALL_STARTED",
            "status": "success",
            "latency_ms": 0.0,
            "summary": f"Channel: {call.channel}",
            "data": {},
        })

    # Messages
    for m in (
        db.query(Message)
        .filter(Message.call_id == call_id)
        .order_by(Message.created_at.asc())
        .all()
    ):
        events.append({
            "ts": m.created_at,
            "kind": "message",
            "name": f"{m.role.upper()}_MESSAGE",
            "status": "success",
            "latency_ms": 0.0,
            "summary": (m.content or "")[:200],
            "data": {"role": m.role, "message_id": m.id},
        })

    # Traces
    for t in (
        db.query(Trace)
        .filter(Trace.call_id == call_id)
        .order_by(Trace.created_at.asc())
        .all()
    ):
        events.append({
            "ts": t.created_at,
            "kind": "trace",
            "name": t.name,
            "status": t.status,
            "latency_ms": float(t.latency_ms or 0.0),
            "summary": t.error or "",
            "data": {
                "trace_kind": t.kind,
                "input": t.input_data or {},
                "output": t.output_data or {},
                "error": t.error,
            },
        })

    # End lifecycle
    if call.status == "ended" and call.updated_at:
        events.append({
            "ts": call.updated_at,
            "kind": "lifecycle",
            "name": "CALL_ENDED",
            "status": "success",
            "latency_ms": 0.0,
            "summary": "",
            "data": {},
        })

    events.sort(key=lambda e: e["ts"])
    return events


@router.get("/{call_id}/latency", response_model=LatencyBreakdown)
def get_call_latency(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = _load_call_for_tenant(db, call_id, tenant.id)

    rows = (
        db.query(Trace)
        .filter(Trace.call_id == call_id)
        .all()
    )

    total_ms = 0
    if call.created_at and call.updated_at:
        total_ms = int((call.updated_at - call.created_at).total_seconds() * 1000)

    llm_ms = sum(float(r.latency_ms or 0) for r in rows if r.kind == "llm")
    tools_ms = sum(float(r.latency_ms or 0) for r in rows if r.kind == "tool")
    stt_ms = sum(float(r.latency_ms or 0) for r in rows if r.kind == "stt")
    tts_ms = sum(float(r.latency_ms or 0) for r in rows if r.kind == "tts")

    accounted = llm_ms + tools_ms + stt_ms + tts_ms
    other = max(0, total_ms - accounted)

    return {
        "call_id": call_id,
        "total_ms": total_ms,
        "llm_ms": int(llm_ms),
        "tools_ms": int(tools_ms),
        "stt_ms": int(stt_ms),
        "tts_ms": int(tts_ms),
        "other_ms": int(other),
    }


@router.post("/{call_id}/messages", response_model=MessageOut)
async def send_message(
    call_id: str,
    payload: CallMessageIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = _load_call_for_tenant(db, call_id, tenant.id)
    if call.status != "active":
        raise HTTPException(status_code=409, detail="Call is not active")

    agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent no longer exists")

    user_msg = Message(call_id=call.id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    prior = (
        db.query(Message)
        .filter(Message.call_id == call.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in prior
        if m.role in ("user", "assistant")
    ]

    try:
        result = await run_agent(
            agent,
            db,
            payload.content,
            history=history[:-1],
            enable_tools=True,
            call_id=call.id,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent runtime failed: {e}")

    assistant_msg = Message(
        call_id=call.id,
        role="assistant",
        content=result["response"],
        tool_traces=result.get("tool_traces") or [],
        meta=result.get("meta") or {},
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


@router.post("/{call_id}/end", response_model=CallOut)
def end_call(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = _load_call_for_tenant(db, call_id, tenant.id)
    call.status = "ended"
    db.commit()
    db.refresh(call)
    return call
