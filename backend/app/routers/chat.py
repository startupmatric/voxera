from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..models import Agent, Tenant
from ..runtime.ollama_client import health as ollama_health
from ..runtime.runner import run_agent
from ..schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/agents", tags=["runtime"])


@router.get("/runtime/health")
async def runtime_health():
    ok = await ollama_health()
    return {"ollama": "ok" if ok else "unreachable"}


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    agent_id: str,
    payload: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.tenant_id == tenant.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    history = None
    if payload.history:
        history = [{"role": m.role, "content": m.content} for m in payload.history]

    try:
        result = await run_agent(agent, db, payload.message, history)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent runtime failed: {e}",
        )

    return ChatResponse(response=result["response"], version=result["version"], meta=result["meta"])
