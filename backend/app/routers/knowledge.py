from fastapi import APIRouter, Depends, HTTPException, status
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
