import asyncio
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
