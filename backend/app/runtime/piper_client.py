import os

import httpx

PIPER_URL = os.getenv("PIPER_URL", "http://piper:8000")


async def synthesize(text: str, voice: str = "alloy", timeout: float = 120.0) -> bytes:
    """
    OpenAI-compatible TTS endpoint: POST /v1/audio/speech
    Body: {"model": "tts-1", "input": "...", "voice": "alloy"}
    Returns WAV bytes.
    """
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": "wav",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{PIPER_URL}/v1/audio/speech", json=payload)
        r.raise_for_status()
        return r.content


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{PIPER_URL}/v1/models")
            return r.status_code == 200
    except Exception:
        return False
