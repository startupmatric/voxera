import base64
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth.security import decode_access_token
from ..database import SessionLocal
from ..models import Agent, Call, Message, Tenant, User
from ..runtime.piper_client import synthesize as piper_synthesize
from ..runtime.runner import run_agent
from ..runtime.whisper_client import transcribe as whisper_transcribe

router = APIRouter()

# Per-connection audio buffer is keyed by the WebSocket object; simplest is a
# local dict inside the connection handler.
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB safety cap


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
    audio_buffer = bytearray()
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

        call = Call(tenant_id=agent.tenant_id, agent_id=agent.id, status="active", channel="websocket")
        db.add(call)
        db.commit()
        db.refresh(call)

        greeting = f"Hi! I'm {agent.name}. How can I help you today?"
        db.add(Message(call_id=call.id, role="assistant", content=greeting, tool_traces=[], meta={"greeting": True}))
        db.commit()

        await websocket.send_json({
            "type": "call_started",
            "call_id": call.id,
            "agent": {"id": agent.id, "name": agent.name},
            "greeting": greeting,
        })

        # ------------------------------------------------------------------
        # Helpers used by the loop
        # ------------------------------------------------------------------
        async def handle_text(content: str):
            content = content.strip()
            if not content:
                return

            # Persist user message
            db.add(Message(call_id=call.id, role="user", content=content))
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
                result = await run_agent(agent, db, content, history=history[:-1], enable_tools=True)
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": f"Runtime error: {e}"})
                return

            # Emit tool events
            for t in result.get("tool_traces") or []:
                await websocket.send_json({
                    "type": "tool_call",
                    "tool": t.get("name"),
                    "status": t.get("status"),
                })

            # Persist assistant message
            assistant_msg = Message(
                call_id=call.id,
                role="assistant",
                content=result["response"],
                tool_traces=result.get("tool_traces") or [],
                meta=result.get("meta") or {},
            )
            db.add(assistant_msg)
            db.commit()

            # TTS: convert response to audio (if TTS is enabled)
            audio_b64 = None
            try:
                wav_bytes = await piper_synthesize(result["response"])
                audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
            except Exception as e:
                # TTS failure is non-fatal — the browser will just show text
                print(f"[piper] TTS failed: {e}")

            out = {
                "type": "assistant_message",
                "content": result["response"],
                "version": result["version"],
                "meta": result.get("meta") or {},
                "tool_traces": result.get("tool_traces") or [],
            }
            if audio_b64:
                out["audio"] = audio_b64
                out["audio_format"] = "wav"
            await websocket.send_json(out)

        async def handle_audio_end():
            nonlocal audio_buffer
            if not audio_buffer:
                await websocket.send_json({"type": "error", "detail": "Empty audio"})
                return
            if len(audio_buffer) > MAX_AUDIO_BYTES:
                await websocket.send_json({"type": "error", "detail": "Audio too large"})
                audio_buffer = bytearray()
                return

            audio_bytes = bytes(audio_buffer)
            audio_buffer = bytearray()

            await websocket.send_json({"type": "stt_started"})
            try:
                transcript = await whisper_transcribe(audio_bytes)
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": f"STT failed: {e}"})
                return

            await websocket.send_json({
                "type": "transcript",
                "content": transcript,
            })

            if transcript:
                await handle_text(transcript)
            else:
                await websocket.send_json({"type": "error", "detail": "No speech detected"})

        # ------------------------------------------------------------------
        # Main loop
        # ------------------------------------------------------------------
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            mtype = msg.get("type")

            if mtype == "end_call":
                call.status = "ended"
                db.commit()
                await websocket.send_json({"type": "call_ended", "call_id": call.id})
                break

            if mtype == "user_message":
                await handle_text(msg.get("content") or "")
                continue

            if mtype == "audio_chunk":
                chunk_b64 = msg.get("audio") or ""
                try:
                    chunk = base64.b64decode(chunk_b64)
                except Exception:
                    await websocket.send_json({"type": "error", "detail": "Invalid audio chunk"})
                    continue
                audio_buffer.extend(chunk)
                continue

            if mtype == "audio_end":
                await handle_audio_end()
                continue

            if mtype == "audio_cancel":
                audio_buffer = bytearray()
                await websocket.send_json({"type": "audio_cancelled"})
                continue

            await websocket.send_json({"type": "error", "detail": f"Unknown message type: {mtype}"})

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
