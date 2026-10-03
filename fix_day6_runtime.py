from pathlib import Path

FILES = {}

# ---------- runtime/__init__.py ----------
FILES["backend/app/runtime/__init__.py"] = ""

# ---------- runtime/ollama_client.py ----------
FILES["backend/app/runtime/ollama_client.py"] = '''import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


async def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> dict:
    """
    Send a chat completion request to Ollama and return the parsed response.

    Returns:
        {
          "content": str,
          "model": str,
          "total_duration_ms": int,
          "prompt_eval_count": int,
          "eval_count": int,
        }
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()

    msg = data.get("message") or {}
    return {
        "content": msg.get("content", ""),
        "model": data.get("model", model),
        "total_duration_ms": int((data.get("total_duration") or 0) / 1_000_000),
        "prompt_eval_count": data.get("prompt_eval_count") or 0,
        "eval_count": data.get("eval_count") or 0,
    }


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def list_models() -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
'''

# ---------- runtime/state.py ----------
FILES["backend/app/runtime/state.py"] = '''from typing import TypedDict


class AgentState(TypedDict, total=False):
    agent_id: str
    agent_name: str
    version: int
    system_prompt: str
    model_name: str
    temperature: float
    messages: list[dict]      # OpenAI-style chat history: [{"role": "...", "content": "..."}]
    response: str
    meta: dict
'''

# ---------- runtime/graph.py ----------
FILES["backend/app/runtime/graph.py"] = '''from langgraph.graph import END, StateGraph

from .ollama_client import chat as ollama_chat
from .state import AgentState


async def _llm_node(state: AgentState) -> AgentState:
    """
    Core LLM node. Builds the final chat message list and calls Ollama.
    The system prompt comes from the agent's active version.
    """
    system = state.get("system_prompt") or "You are a helpful AI assistant."
    history = state.get("messages") or []

    messages = [{"role": "system", "content": system}] + history

    result = await ollama_chat(
        messages=messages,
        model=state.get("model_name") or "llama3.2:3b",
        temperature=float(state.get("temperature") or 0.7),
    )

    state["response"] = result["content"]
    state["meta"] = {
        "model": result["model"],
        "version": state.get("version"),
        "latency_ms": result["total_duration_ms"],
        "prompt_tokens": result["prompt_eval_count"],
        "completion_tokens": result["eval_count"],
    }
    return state


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("llm", _llm_node)
    g.set_entry_point("llm")
    g.add_edge("llm", END)
    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
'''

# ---------- runtime/runner.py ----------
FILES["backend/app/runtime/runner.py"] = '''from ..models import Agent, AgentVersion
from .graph import get_graph
from .state import AgentState


def active_version_for(agent: Agent, db) -> AgentVersion | None:
    """
    Returns the currently active version snapshot, or None if the agent has none.
    """
    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent.id, AgentVersion.is_active.is_(True))
        .first()
    )


async def run_agent(agent: Agent, db, user_message: str, history: list[dict] | None = None) -> dict:
    """
    Executes the LangGraph workflow for one turn.
    Returns {"response": str, "meta": {...}, "version": int}.
    """
    version = active_version_for(agent, db)

    # If there is no active version, fall back to the live agent row
    if version is not None:
        system_prompt = version.system_prompt
        model_name = version.model_name
        temperature = version.temperature
        version_number = version.version
    else:
        system_prompt = agent.system_prompt
        model_name = agent.model_name
        temperature = agent.temperature
        version_number = 0

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    state: AgentState = {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "version": version_number,
        "system_prompt": system_prompt or "You are a helpful AI assistant.",
        "model_name": model_name or "llama3.2:3b",
        "temperature": float(temperature or 0.7),
        "messages": messages,
    }

    graph = get_graph()
    final = await graph.ainvoke(state)

    return {
        "response": final.get("response", ""),
        "meta": final.get("meta", {}),
        "version": version_number,
    }
'''

# ---------- schemas/chat.py ----------
FILES["backend/app/schemas/chat.py"] = '''from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    response: str
    version: int
    meta: dict
'''

# ---------- routers/chat.py ----------
FILES["backend/app/routers/chat.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
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
'''

# ---------- main.py ----------
FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import agents, chat, me, organizations, tenants, users

app = FastAPI(title=settings.app_name, version="0.6.0")

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
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.6.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(agents.router)
app.include_router(chat.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal backend files: {len(FILES)}")