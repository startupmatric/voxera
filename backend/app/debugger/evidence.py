def collect_evidence(traces, messages, limit: int = 10) -> list[dict]:
    """
    Return a small list of evidence items:
      - failed traces
      - error strings
      - last few messages
    """
    evidence: list[dict] = []

    # error traces first
    for t in traces:
        if t.status == "error":
            evidence.append({
                "type": "trace",
                "trace_id": t.id,
                "kind": t.kind,
                "name": t.name,
                "status": t.status,
                "latency_ms": t.latency_ms,
                "error": t.error,
                "input": t.input_data or {},
                "output": t.output_data or {},
            })

    # successful tool traces (context)
    for t in traces:
        if t.kind == "tool" and t.status == "success" and len(evidence) < limit:
            evidence.append({
                "type": "trace",
                "trace_id": t.id,
                "kind": t.kind,
                "name": t.name,
                "status": t.status,
                "latency_ms": t.latency_ms,
            })

    # last few messages
    for m in messages[-4:]:
        evidence.append({
            "type": "message",
            "message_id": m.id,
            "role": m.role,
            "content": (m.content or "")[:500],
        })

    return evidence[:limit]
