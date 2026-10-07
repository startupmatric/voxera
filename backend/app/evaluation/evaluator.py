from .scoring import (
    is_pass,
    score_answer,
    score_error,
    score_latency,
    score_tools,
    total_score,
)


def evaluate_case(
    case_input: str,
    expected_output: str | None,
    expected_tools: list[str],
    max_latency_ms: int,
    actual_output: str | None,
    actual_tools: list[str],
    latency_ms: float,
    error: str | None,
) -> dict:
    answer = score_answer(actual_output, expected_output)
    tools = score_tools(actual_tools, expected_tools)
    latency = score_latency(latency_ms, max_latency_ms)
    err = score_error(error)
    total = total_score(answer, tools, latency, err)
    passed = is_pass(total)

    return {
        "status": "passed" if passed else "failed",
        "score": total,
        "answer_score": answer,
        "tool_score": tools,
        "latency_score": latency,
        "error_score": err,
        "actual_output": actual_output,
        "actual_tools": actual_tools,
        "latency_ms": latency_ms,
        "error": error,
    }
