from pathlib import Path

FILES = {}

# ---------------- Models ----------------

FILES["backend/app/models/knowledge.py"] = '''from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # embedding is added via Alembic migration as a raw SQL vector(768) column.
    # We don't declare it here to avoid pulling in pgvector types in the model.

    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument", back_populates="chunks"
    )
'''

FILES["backend/app/models/__init__.py"] = '''from .base import Base
from .organization import Organization
from .user import User
from .tenant import Tenant
from .agent import Agent
from .agent_version import AgentVersion
from .calendar_event import CalendarEvent
from .customer import Customer
from .lead import Lead
from .trace import Trace
from .call import Call
from .message import Message
from .evaluation import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationResult,
)
from .debug_report import DebugReport
from .knowledge import KnowledgeDocument, KnowledgeChunk

__all__ = [
    "Base",
    "Organization",
    "User",
    "Tenant",
    "Agent",
    "AgentVersion",
    "CalendarEvent",
    "Customer",
    "Lead",
    "Trace",
    "Call",
    "Message",
    "EvaluationDataset",
    "EvaluationCase",
    "EvaluationRun",
    "EvaluationResult",
    "DebugReport",
    "KnowledgeDocument",
    "KnowledgeChunk",
]
'''

# ---------------- Knowledge package ----------------

FILES["backend/app/knowledge/__init__.py"] = ""

FILES["backend/app/knowledge/chunker.py"] = '''def chunk_text(text: str, target_chars: int = 1800, overlap: int = 200) -> list[str]:
    """
    Simple paragraph-aware chunker.

    - target_chars ≈ 500 tokens (roughly 1800 chars)
    - overlap ≈ 50-100 tokens
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\\n\\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) + 2 <= target_chars:
            current = (current + "\\n\\n" + p).strip() if current else p
        else:
            if current:
                chunks.append(current)
            # if paragraph itself is too big, hard-split it
            if len(p) > target_chars:
                start = 0
                while start < len(p):
                    end = min(start + target_chars, len(p))
                    chunks.append(p[start:end])
                    start = end - overlap if end < len(p) else len(p)
                current = ""
            else:
                current = p

    if current:
        chunks.append(current)

    return chunks
'''

FILES["backend/app/knowledge/embeddings.py"] = '''import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


async def embed_one(text: str, timeout: float = 120.0) -> list[float]:
    """Get a single embedding from Ollama."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        r.raise_for_status()
        data = r.json()
    return data.get("embedding") or []


async def embed_many(texts: list[str]) -> list[list[float]]:
    """Sequential to keep memory reasonable on CPU."""
    out = []
    for t in texts:
        out.append(await embed_one(t))
    return out
'''

FILES["backend/app/knowledge/search.py"] = '''from sqlalchemy import text
from sqlalchemy.orm import Session


def vector_search(
    db: Session,
    tenant_id: str,
    query_embedding: list[float],
    top_k: int = 5,
    agent_id: str | None = None,
) -> list[dict]:
    """
    Cosine similarity search restricted to a single tenant.

    Returns a list of {chunk_id, document_id, document_name, content, score}.
    """
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    agent_clause = ""
    params = {
        "tenant_id": tenant_id,
        "emb": embedding_str,
        "k": top_k,
    }
    if agent_id:
        agent_clause = "AND d.agent_id = :agent_id"
        params["agent_id"] = agent_id

    sql = text(f"""
        SELECT
            c.id            AS chunk_id,
            d.id            AS document_id,
            d.name          AS document_name,
            c.content       AS content,
            1 - (c.embedding <=> CAST(:emb AS vector)) AS score
        FROM knowledge_chunks c
        JOIN knowledge_documents d ON d.id = c.document_id
        WHERE c.tenant_id = :tenant_id
          AND c.embedding IS NOT NULL
          {agent_clause}
        ORDER BY c.embedding <=> CAST(:emb AS vector)
        LIMIT :k
    """)

    rows = db.execute(sql, params).fetchall()
    return [
        {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "document_name": r.document_name,
            "content": r.content,
            "score": float(r.score or 0.0),
        }
        for r in rows
    ]
'''

FILES["backend/app/knowledge/service.py"] = '''from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import KnowledgeChunk, KnowledgeDocument
from .chunker import chunk_text
from .embeddings import embed_one
from .search import vector_search


async def create_document(
    db: Session,
    tenant_id: str,
    agent_id: str | None,
    name: str,
    content: str,
    source: str | None = None,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        tenant_id=tenant_id,
        agent_id=agent_id,
        name=name,
        source=source,
        content=content,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunks = chunk_text(content)
    for i, c in enumerate(chunks):
        vec = await embed_one(c)
        # Insert chunk + embedding via raw SQL (embedding is not on the ORM model)
        db.execute(
            text("""
                INSERT INTO knowledge_chunks
                  (id, document_id, tenant_id, chunk_index, content, embedding, created_at, updated_at)
                VALUES
                  (gen_random_uuid()::text, :doc_id, :tenant_id, :idx, :content, CAST(:emb AS vector), NOW(), NOW())
            """),
            {
                "doc_id": doc.id,
                "tenant_id": tenant_id,
                "idx": i,
                "content": c,
                "emb": "[" + ",".join(str(x) for x in vec) + "]",
            },
        )
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session, tenant_id: str) -> list[KnowledgeDocument]:
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.tenant_id == tenant_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )


def get_document(db: Session, tenant_id: str, doc_id: str) -> KnowledgeDocument | None:
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.id == doc_id, KnowledgeDocument.tenant_id == tenant_id)
        .first()
    )


def delete_document(db: Session, tenant_id: str, doc_id: str) -> bool:
    doc = get_document(db, tenant_id, doc_id)
    if not doc:
        return False
    db.delete(doc)
    db.commit()
    return True


async def search(
    db: Session,
    tenant_id: str,
    query: str,
    top_k: int = 5,
    agent_id: str | None = None,
) -> list[dict]:
    vec = await embed_one(query)
    if not vec:
        return []
    return vector_search(db, tenant_id, vec, top_k=top_k, agent_id=agent_id)
'''

# ---------------- Schemas ----------------

FILES["backend/app/schemas/knowledge.py"] = '''from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source: str | None = None
    agent_id: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str | None
    name: str
    source: str | None
    created_at: datetime


class DocumentDetail(DocumentOut):
    content: str


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    content: str
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    agent_id: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
'''

# ---------------- Router ----------------

FILES["backend/app/routers/knowledge.py"] = '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant
from ..database import get_db
from ..knowledge import service
from ..models import KnowledgeChunk, Tenant
from ..schemas.knowledge import (
    ChunkOut,
    DocumentCreate,
    DocumentDetail,
    DocumentOut,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return service.list_documents(db, tenant.id)


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    try:
        doc = await service.create_document(
            db,
            tenant_id=tenant.id,
            agent_id=payload.agent_id,
            name=payload.name,
            content=payload.content,
            source=payload.source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
    return doc


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    doc = service.get_document(db, tenant.id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    doc = service.get_document(db, tenant.id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.chunk_index.asc())
        .all()
    )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if not service.delete_document(db, tenant.id, doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return None


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    results = await service.search(
        db,
        tenant.id,
        payload.query,
        top_k=payload.top_k,
        agent_id=payload.agent_id,
    )
    return {"results": results}
'''

# ---------------- knowledge.search tool ----------------

FILES["backend/app/runtime/tools/builtin.py"] = '''import ast
import operator as _op
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...models import CalendarEvent, Customer, Lead
from ...knowledge import service as knowledge_service

# ------------------------------------------------------------------
# get_current_time
# ------------------------------------------------------------------


class _TimeInput(BaseModel):
    pass


def _time_handler(_: _TimeInput, ctx: dict) -> dict:
    return {"now": datetime.now(timezone.utc).isoformat()}


# ------------------------------------------------------------------
# calculate
# ------------------------------------------------------------------

_OPS = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.Mod: _op.mod, ast.Pow: _op.pow,
    ast.USub: _op.neg, ast.UAdd: _op.pos,
}


def _eval_expr(node):
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval_expr(node.operand))
    raise ValueError("unsupported expression")


class _CalcInput(BaseModel):
    expression: str = Field(..., description="Arithmetic expression, e.g. '2 + 3 * 4'")


def _calc_handler(inp: _CalcInput, ctx: dict) -> dict:
    tree = ast.parse(inp.expression, mode="eval")
    return {"result": _eval_expr(tree.body)}


# ------------------------------------------------------------------
# calendar.create_event
# ------------------------------------------------------------------


class _CreateEventInput(BaseModel):
    title: str
    start_at: str = Field(..., description="ISO 8601 datetime, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, ge=0, le=1440)
    notes: str | None = None


def _create_event_handler(inp: _CreateEventInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    raw = inp.start_at.strip().replace("Z", "+00:00")
    try:
        start = datetime.fromisoformat(raw)
    except ValueError:
        start = datetime.fromisoformat(raw.replace("+00:00", ""))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    from datetime import timedelta
    duration = int(inp.duration_minutes or 60)
    if duration <= 0:
        duration = 60
    end = start + timedelta(minutes=duration)

    ev = CalendarEvent(
        tenant_id=tenant_id,
        title=inp.title,
        start_at=start,
        end_at=end,
        notes=inp.notes,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "title": ev.title,
        "start_at": ev.start_at.isoformat(),
        "end_at": ev.end_at.isoformat(),
    }


# ------------------------------------------------------------------
# crm.search_contact
# ------------------------------------------------------------------


class _SearchContactInput(BaseModel):
    query: str = Field(..., description="Name fragment or email to match")


def _search_contact_handler(inp: _SearchContactInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    q = inp.query.strip().lower()
    rows = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            (Customer.email.ilike(f"%{q}%")) | (Customer.name.ilike(f"%{q}%")),
        )
        .limit(5)
        .all()
    )
    return {
        "count": len(rows),
        "results": [
            {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
            for c in rows
        ],
    }


# ------------------------------------------------------------------
# crm.create_lead
# ------------------------------------------------------------------


class _CreateLeadInput(BaseModel):
    name: str
    email: str | None = None
    source: str | None = Field(None, description="e.g. 'website', 'phone', 'referral'")
    notes: str | None = None


def _create_lead_handler(inp: _CreateLeadInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    lead = Lead(
        tenant_id=tenant_id,
        name=inp.name,
        email=inp.email,
        source=inp.source,
        status="new",
        notes=inp.notes,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {"id": lead.id, "name": lead.name, "status": lead.status}


# ------------------------------------------------------------------
# knowledge.search  (RAG)
# ------------------------------------------------------------------


class _KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="Natural language search query")


def _knowledge_search_handler(inp: _KnowledgeSearchInput, ctx: dict) -> dict:
    import asyncio
    from ...knowledge.service import search as kn_search
    from ...database import SessionLocal

    # We're called from a synchronous tool node; create a fresh session
    # to avoid mixing ORM state across threads/events.
    db = SessionLocal()
    try:
        results = asyncio.get_event_loop().run_until_complete(
            kn_search(db, ctx["tenant_id"], inp.query, top_k=5)
        )
    except RuntimeError:
        # no running loop in this thread
        results = asyncio.run(kn_search(db, ctx["tenant_id"], inp.query, top_k=5))
    finally:
        db.close()

    return {
        "count": len(results),
        "results": [
            {
                "document": r["document_name"],
                "content": r["content"][:600],
                "score": round(r["score"], 4),
            }
            for r in results
        ],
    }
'''

# ---------------- Update registry ----------------

FILES["backend/app/runtime/tools/registry.py"] = '''from .base import ToolDef
from .builtin import (
    _CalcInput,
    _CreateEventInput,
    _CreateLeadInput,
    _KnowledgeSearchInput,
    _SearchContactInput,
    _TimeInput,
    _calc_handler,
    _create_event_handler,
    _create_lead_handler,
    _knowledge_search_handler,
    _search_contact_handler,
    _time_handler,
)

TOOLS: dict[str, ToolDef] = {}


def _register(t: ToolDef) -> None:
    TOOLS[t.name] = t


def register_all() -> None:
    if TOOLS:
        return

    _register(ToolDef(
        name="get_current_time",
        description="Return the current UTC time in ISO 8601 format.",
        input_model=_TimeInput,
        handler=_time_handler,
    ))
    _register(ToolDef(
        name="calculate",
        description="Evaluate a simple arithmetic expression like '2 + 3 * 4'.",
        input_model=_CalcInput,
        handler=_calc_handler,
    ))
    _register(ToolDef(
        name="calendar.create_event",
        description="Create a calendar event for the current tenant.",
        input_model=_CreateEventInput,
        handler=_create_event_handler,
    ))
    _register(ToolDef(
        name="crm.search_contact",
        description="Search customers by partial name or email.",
        input_model=_SearchContactInput,
        handler=_search_contact_handler,
    ))
    _register(ToolDef(
        name="crm.create_lead",
        description="Create a sales lead in the CRM.",
        input_model=_CreateLeadInput,
        handler=_create_lead_handler,
    ))
    _register(ToolDef(
        name="knowledge.search",
        description="Search the tenant's knowledge base for relevant documents. Use this when the user asks a question that may be covered by uploaded documents.",
        input_model=_KnowledgeSearchInput,
        handler=_knowledge_search_handler,
    ))


def all_schemas() -> list[dict]:
    register_all()
    return [t.schema() for t in TOOLS.values()]


def execute_tool(name: str, arguments: dict, ctx: dict) -> dict:
    register_all()
    tool = TOOLS.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    validated = tool.input_model(**arguments)
    return tool.handler(validated, ctx)
'''

# ---------------- Update main.py ----------------

FILES["backend/app/main.py"] = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import settings
from .database import check_database, check_redis
from .routers import (
    agents,
    calls,
    chat,
    debug,
    evaluations,
    knowledge,
    me,
    organizations,
    tenants,
    traces,
    users,
    ws_calls,
)

app = FastAPI(title=settings.app_name, version="0.12.0")

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
    return {"service": settings.app_name, "env": settings.app_env, "version": "0.12.0"}


app.include_router(auth_router.router)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(users.router)
app.include_router(tenants.router)
app.include_router(traces.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(calls.router)
app.include_router(evaluations.router)
app.include_router(debug.router)
app.include_router(knowledge.router)
app.include_router(ws_calls.router)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")