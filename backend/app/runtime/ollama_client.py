import os

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
