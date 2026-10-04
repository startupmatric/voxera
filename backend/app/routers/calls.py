from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..models import Agent, Call, Message, Tenant
from ..schemas.call import CallDetail, CallMessageIn, CallOut, CallStart, MessageOut
from ..runtime.runner import run_agent

router = APIRouter(prefix="/calls", tags=["calls"])


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

    # Greeting message so the conversation isn't empty
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


@router.get("", response_model=list[CallOut])
def list_calls(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(Call)
        .filter(Call.tenant_id == tenant.id)
        .order_by(Call.created_at.desc())
        .all()
    )


@router.get("/{call_id}", response_model=CallDetail)
def get_call(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = (
        db.query(Call)
        .filter(Call.id == call_id, Call.tenant_id == tenant.id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/{call_id}/messages", response_model=MessageOut)
async def send_message(
    call_id: str,
    payload: CallMessageIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    call = (
        db.query(Call)
        .filter(Call.id == call_id, Call.tenant_id == tenant.id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.status != "active":
        raise HTTPException(status_code=409, detail="Call is not active")

    agent = db.query(Agent).filter(Agent.id == call.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent no longer exists")

    # Persist the user's message
    user_msg = Message(call_id=call.id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Build history from all prior messages
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

    # Run the existing Day 6/7 runtime
    try:
        result = await run_agent(agent, db, payload.content, history=history[:-1], enable_tools=True)
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
    call = (
        db.query(Call)
        .filter(Call.id == call_id, Call.tenant_id == tenant.id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    call.status = "ended"
    db.commit()
    db.refresh(call)
    return call
