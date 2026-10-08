from sqlalchemy import text
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
