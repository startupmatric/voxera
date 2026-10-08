import os

import httpx
from fastapi import APIRouter

from ..database import check_database, check_redis

router = APIRouter(prefix="/health", tags=["health"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper:9000")
PIPER_URL = os.getenv("PIPER_URL", "http://piper:8000")


async def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url)
            return r.status_code < 500
    except Exception:
        return False


@router.get("/full")
async def health_full():
    postgres = check_database()
    redis = check_redis()
    ollama = await _http_ok(f"{OLLAMA_URL}/api/tags")
    whisper = await _http_ok(f"{WHISPER_URL}/docs")
    piper = await _http_ok(f"{PIPER_URL}/v1/models")

    all_ok = all([postgres, redis, ollama, whisper, piper])
    return {
        "status": "ok" if all_ok else "degraded",
        "services": {
            "postgres": "ok" if postgres else "error",
            "redis": "ok" if redis else "error",
            "ollama": "ok" if ollama else "error",
            "whisper": "ok" if whisper else "error",
            "piper": "ok" if piper else "error",
        },
    }
