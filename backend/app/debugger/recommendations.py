def recommend(category: str) -> list[str]:
    if category == "TOOL_FAILURE":
        return [
            "Inspect the failed tool's input schema and error output.",
            "Add retry/backoff for transient failures (network, API timeouts).",
            "Verify credentials and endpoints for external integrations.",
            "If the tool failed on bad arguments, refine the tool description so the LLM passes valid inputs.",
        ]
    if category == "LLM_FAILURE":
        return [
            "Check the LLM provider status and rate limits.",
            "Reduce the system prompt size if it exceeds the context window.",
            "Lower temperature if the model is producing unstable outputs.",
            "Try a larger model if the failure is due to reasoning depth.",
        ]
    if category == "STT_FAILURE":
        return [
            "Ensure the microphone is not muted and the browser has permission.",
            "Check that the audio format is supported (WebM/Opus → WAV via ffmpeg).",
            "Increase the recording length; very short clips are often rejected.",
            "Verify Whisper service health: `docker compose logs whisper`.",
        ]
    if category == "TTS_FAILURE":
        return [
            "Verify the Piper service is reachable.",
            "Check that the requested voice is installed.",
            "Review Piper logs for decode/format errors.",
        ]
    if category == "TIMEOUT":
        return [
            "Raise the client/nginx timeout if the model is simply slow.",
            "Reduce the system prompt or tool set to shorten generation.",
            "Consider a smaller model or GPU acceleration.",
        ]
    if category == "VALIDATION_FAILURE":
        return [
            "Check that the call has user input before expecting a response.",
            "Verify the agent's system prompt is not blocking all responses.",
        ]
    return [
        "No specific failure detected. Review the full trace timeline for anomalies.",
    ]
