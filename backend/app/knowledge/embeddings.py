import os

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
