from pathlib import Path

FILES = {}

FILES["backend/app/routers/calls.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
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
'''

FILES["backend/app/routers/ws_calls.py"] = '''import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth.security import decode_access_token
from ..database import SessionLocal
from ..models import Agent, Call, Message, Tenant, User
from ..runtime.runner import run_agent

router = APIRouter()


def _send(ws: WebSocket, payload: dict) -> None:
    # FastAPI WebSocket send_json is async; wrap in a task when called from sync code
    pass


@router.websocket("/ws/calls/{agent_id}")
async def call_ws(websocket: WebSocket, agent_id: str, token: str = ""):
    await websocket.accept()

    # --- Auth
    try:
        payload = decode_access_token(token) if token else {}
    except Exception:
        await websocket.send_json({"type": "error", "detail": "Invalid token"})
        await websocket.close(code=4401)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.send_json({"type": "error", "detail": "Missing token"})
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user:
            await websocket.send_json({"type": "error", "detail": "User not found"})
            await websocket.close(code=4401)
            return

        agent = (
            db.query(Agent)
            .join(Tenant, Agent.tenant_id == Tenant.id)
            .filter(
                Agent.id == agent_id,
                Tenant.organization_id == user.organization_id,
                Tenant.is_active.is_(True),
            )
            .first()
        )
        if not agent:
            await websocket.send_json({"type": "error", "detail": "Agent not found"})
            await websocket.close(code=4404)
            return

        # --- Create the Call row
        call = Call(tenant_id=agent.tenant_id, agent_id=agent.id, status="active", channel="websocket")
        db.add(call)
        db.commit()
        db.refresh(call)

        greeting = f"Hi! I'm {agent.name}. How can I help you today?"
        greeting_msg = Message(
            call_id=call.id, role="assistant", content=greeting, tool_traces=[], meta={"greeting": True}
        )
        db.add(greeting_msg)
        db.commit()

        await websocket.send_json({
            "type": "call_started",
            "call_id": call.id,
            "agent": {"id": agent.id, "name": agent.name},
            "greeting": greeting,
        })

        # --- Conversation loop
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            if msg.get("type") == "end_call":
                call.status = "ended"
                db.commit()
                await websocket.send_json({"type": "call_ended", "call_id": call.id})
                break

            if msg.get("type") != "user_message":
                await websocket.send_json({"type": "error", "detail": "Unknown message type"})
                continue

            content = (msg.get("content") or "").strip()
            if not content:
                continue

            # Persist user message
            user_msg = Message(call_id=call.id, role="user", content=content)
            db.add(user_msg)
            db.commit()

            await websocket.send_json({"type": "user_message", "content": content})
            await websocket.send_json({"type": "llm_started"})

            # Build history
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
                    agent, db, content, history=history[:-1], enable_tools=True
                )
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": f"Runtime error: {e}"})
                continue

            # Emit tool events (from the traces recorded during this turn)
            for t in result.get("tool_traces") or []:
                await websocket.send_json({
                    "type": "tool_call",
                    "tool": t.get("name"),
                    "status": t.get("status"),
                })

            # Persist the assistant message
            assistant_msg = Message(
                call_id=call.id,
                role="assistant",
                content=result["response"],
                tool_traces=result.get("tool_traces") or [],
                meta=result.get("meta") or {},
            )
            db.add(assistant_msg)
            db.commit()

            await websocket.send_json({
                "type": "assistant_message",
                "content": result["response"],
                "version": result["version"],
                "meta": result.get("meta") or {},
                "tool_traces": result.get("tool_traces") or [],
            })

    except WebSocketDisconnect:
        pass
    finally:
        try:
            if "call" in dir() and call and call.status == "active":
                call.status = "ended"
                db.commit()
        except Exception:
            pass
        db.close()
'''

FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import agents, calls, chat, me, organizations, tenants, users, ws_calls

app = FastAPI(title=settings.app_name, version="0.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "voxera"}


@app.get("/health/database")
def health_database():
    return {"status": "ok" if check_database() else "error", "service": "postgres"}


@app.get("/health/redis")
def health_redis():
    return {"status": "ok" if check_redis() else "error", "service": "redis"}


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.8.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(calls.router)
app.include_router(ws_calls.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")