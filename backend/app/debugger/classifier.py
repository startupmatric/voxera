"""
Deterministic classifier: inspects call traces + messages and returns
(category, stage, severity, root_cause, confidence).
"""

CATEGORY_STT      = "STT_FAILURE"
CATEGORY_LLM      = "LLM_FAILURE"
CATEGORY_TOOL     = "TOOL_FAILURE"
CATEGORY_TTS      = "TTS_FAILURE"
CATEGORY_TIMEOUT  = "TIMEOUT"
CATEGORY_VALID    = "VALIDATION_FAILURE"
CATEGORY_UNKNOWN  = "UNKNOWN"


def classify_call(call, traces, messages) -> dict:
    """
    Returns:
        {
          "category": str,
          "stage": str,
          "severity": str,        # low | medium | high | critical
          "root_cause": str,
          "confidence": float,    # 0..1
        }
    """
    # 1) Any error trace? Pick the most severe, prioritizing tool > llm > stt > tts
    error_traces = [t for t in traces if t.status == "error"]

    def _first(kinds):
        for t in error_traces:
            if t.kind in kinds:
                return t
        return None

    tool_err = _first({"tool"})
    llm_err  = _first({"llm"})
    stt_err  = _first({"stt"})
    tts_err  = _first({"tts"})

    if tool_err:
        return {
            "category": CATEGORY_TOOL,
            "stage": "tool_execution",
            "severity": "high",
            "root_cause": (
                f"Tool '{tool_err.name}' failed"
                + (f": {tool_err.error}" if tool_err.error else ".")
            ),
            "confidence": 0.98,
        }

    if llm_err:
        return {
            "category": CATEGORY_LLM,
            "stage": "llm",
            "severity": "high",
            "root_cause": (
                f"LLM step '{llm_err.name}' failed"
                + (f": {llm_err.error}" if llm_err.error else ".")
            ),
            "confidence": 0.95,
        }

    if stt_err:
        return {
            "category": CATEGORY_STT,
            "stage": "stt",
            "severity": "medium",
            "root_cause": (
                f"Speech-to-text failed"
                + (f": {stt_err.error}" if stt_err.error else ".")
            ),
            "confidence": 0.9,
        }

    if tts_err:
        return {
            "category": CATEGORY_TTS,
            "stage": "tts",
            "severity": "medium",
            "root_cause": (
                f"Text-to-speech failed"
                + (f": {tts_err.error}" if tts_err.error else ".")
            ),
            "confidence": 0.9,
        }

    # 2) Latency: any single trace over 5 minutes?
    slow = [t for t in traces if (t.latency_ms or 0) > 300_000]
    if slow:
        worst = max(slow, key=lambda t: t.latency_ms or 0)
        return {
            "category": CATEGORY_TIMEOUT,
            "stage": "llm",
            "severity": "medium",
            "root_cause": (
                f"Step '{worst.name}' took {worst.latency_ms/1000:.1f}s (over 300s cap)."
            ),
            "confidence": 0.85,
        }

    # 3) Empty conversation
    user_msgs = [m for m in messages if m.role == "user"]
    asst_msgs = [m for m in messages if m.role == "assistant"]
    if not user_msgs and not asst_msgs:
        return {
            "category": CATEGORY_VALID,
            "stage": "input",
            "severity": "low",
            "root_cause": "Call contains no user or assistant messages.",
            "confidence": 0.7,
        }

    # 4) No issues
    return {
        "category": CATEGORY_UNKNOWN,
        "stage": "output",
        "severity": "low",
        "root_cause": "No failures detected in this call.",
        "confidence": 1.0,
    }
