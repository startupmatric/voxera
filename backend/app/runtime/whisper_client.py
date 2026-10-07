import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper:9000")


def _to_wav(audio_bytes: bytes) -> bytes:
    """
    Convert any input audio to 16-bit PCM WAV using ffmpeg.
    Returns the WAV bytes. If ffmpeg is missing, returns the original bytes.
    """
    if not shutil.which("ffmpeg"):
        return audio_bytes

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in"
        dst = Path(td) / "out.wav"
        src.write_bytes(audio_bytes)

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(src),
                    "-ar", "16000",
                    "-ac", "1",
                    "-c:a", "pcm_s16le",
                    str(dst),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            return dst.read_bytes()
        except Exception:
            return audio_bytes


async def transcribe(audio_bytes: bytes, filename: str = "audio.wav", timeout: float = 120.0) -> str:
    if len(audio_bytes) < 2000:
        return ""

    wav_bytes = _to_wav(audio_bytes)

    files = {"audio_file": ("audio.wav", wav_bytes, "audio/wav")}
    params = {"output": "json", "task": "transcribe", "language": "en"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{WHISPER_URL}/asr", files=files, params=params)
        if r.status_code >= 500:
            return ""
        r.raise_for_status()
        data = r.json()

    return (data.get("text") or "").strip()


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{WHISPER_URL}/docs")
            return r.status_code == 200
    except Exception:
        return False
