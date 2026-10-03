from pathlib import Path

FILES = {}

FILES["backend/app/schemas/chat.py"] = '''from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] | None = None
    enable_tools: bool = True


class ChatResponse(BaseModel):
    response: str
    version: int
    meta: dict
    tool_traces: list[dict] = []
'''

FILES["backend/app/routers/chat.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..models import Agent, Tenant
from ..runtime.ollama_client import health as ollama_health
from ..runtime.runner import run_agent
from ..runtime.tools.registry import TOOLS, all_schemas, register_all
from ..schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/agents", tags=["runtime"])


@router.get("/runtime/health")
async def runtime_health():
    ok = await ollama_health()
    register_all()
    return {"ollama": "ok" if ok else "unreachable", "tools": len(TOOLS)}


@router.get("/runtime/tools")
async def list_tools():
    register_all()
    return {
        "count": len(TOOLS),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "schema": t.input_model.model_json_schema(),
            }
            for t in TOOLS.values()
        ],
    }


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
        result = await run_agent(
            agent, db, payload.message, history, enable_tools=payload.enable_tools
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent runtime failed: {e}",
        )

    return ChatResponse(
        response=result["response"],
        version=result["version"],
        meta=result["meta"],
        tool_traces=result.get("tool_traces") or [],
    )
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")