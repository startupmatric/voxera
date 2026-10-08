from sqlalchemy import text
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
