def score_answer(actual: str | None, expected: str | None) -> float:
    """40 points if the expected substring appears in the actual output."""
    if not expected:
        return 40.0
    if not actual:
        return 0.0
    return 40.0 if expected.lower() in actual.lower() else 0.0


def score_tools(actual_tools: list[str], expected_tools: list[str]) -> float:
    """30 points if every expected tool was called."""
    if not expected_tools:
        return 30.0
    actual_set = set(actual_tools or [])
    expected_set = set(expected_tools)
    return 30.0 if expected_set.issubset(actual_set) else 0.0


def score_latency(latency_ms: float, max_latency_ms: int) -> float:
    """20 points if latency under the cap."""
    return 20.0 if latency_ms <= max_latency_ms else 0.0


def score_error(error: str | None) -> float:
    """10 points if no error occurred."""
    return 10.0 if not error else 0.0


def total_score(answer: float, tools: float, latency: float, error: float) -> float:
    return answer + tools + latency + error


def is_pass(score: float) -> bool:
    return score >= 70.0
