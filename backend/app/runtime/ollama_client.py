import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


async def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    tools: list[dict] | None = None,
    timeout: float = 900.0,
) -> dict:
    """
    Chat with Ollama. Optionally pass a list of tool schemas to enable tool calling.

    Returns:
        {
          "content": str,
          "tool_calls": [{"name": str, "arguments": dict}, ...],
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
        "options": {
            "temperature": temperature,
            "num_predict": 512,   # cap response length; keeps CPU latency sane
            "num_ctx": 4096,      # context window
        },
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()

    msg = data.get("message") or {}
    raw_calls = msg.get("tool_calls") or []

    parsed_calls = []
    for c in raw_calls:
        fn = c.get("function") or {}
        args = fn.get("arguments") or {}
        # Ollama sometimes returns arguments as a JSON string
        if isinstance(args, str):
            import json
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        parsed_calls.append({"name": fn.get("name", ""), "arguments": args})

    return {
        "content": msg.get("content", "") or "",
        "tool_calls": parsed_calls,
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
