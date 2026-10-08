from datetime import datetime

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
