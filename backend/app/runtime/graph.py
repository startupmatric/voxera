import json
import re
import time

from langgraph.graph import END, StateGraph

from .ollama_client import chat as ollama_chat
from .state import AgentState
from .tools.registry import execute_tool

MAX_TOOL_HOPS = 2


def _try_parse_text_tool_call(text: str) -> dict | None:
    """
    Parse a tool call emitted as JSON text by small models.
    Returns {"name": str, "arguments": dict} or None.
    """
    if not text:
        return None

    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)

    start = t.find("{")
    if start == -1:
        return None

    depth = 0
    end = -1
    for i in range(start, len(t)):
        c = t[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return None

    candidate = t[start : end + 1]

    try:
        data = json.loads(candidate)
    except Exception:
        return None

    name = None
    args = None

    if isinstance(data, dict):
        if "function" in data and isinstance(data["function"], dict):
            fn = data["function"]
            name = fn.get("name")
            args = fn.get("arguments") or fn.get("parameters") or {}
        elif "name" in data:
            name = data.get("name")
            args = data.get("parameters") or data.get("arguments") or {}

    if not name or not isinstance(name, str):
        return None

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}

    cleaned = {}
    for k, v in args.items():
        if isinstance(v, str) and v.lower() in ("null", "none", ""):
            continue
        cleaned[k] = v
    return {"name": name, "arguments": cleaned}


def _summarize_tool_result(traces: list[dict]) -> str:
    """
    Fallback: turn raw tool results into a plain-English reply when the model
    produces nothing useful.
    """
    if not traces:
        return "I wasn't able to complete that."

    last = traces[-1]
    name = last.get("name", "tool")
    status = last.get("status", "unknown")
    output = last.get("output") or {}
    error = last.get("error")

    if status == "error" or error:
        return f"I tried to use {name} but it failed: {error or 'unknown error'}."

    if name == "get_current_time":
        return f"The current time is {output.get('now', 'unknown')}."
    if name == "calculate":
        return f"The answer is {output.get('result', 'unknown')}."
    if name == "calendar.create_event":
        return (
            f"I've created the event '{output.get('title', '')}' "
            f"starting at {output.get('start_at', '')}."
        )
    if name == "crm.create_lead":
        return f"I've created a lead for {output.get('name', 'unknown')}."
    if name == "crm.search_contact":
        c = output.get("count", 0)
        if c == 0:
            return "I couldn't find any matching contacts."
        return f"I found {c} matching contact(s)."

    return f"The {name} tool returned: {output}"


async def _llm_node(state: AgentState) -> AgentState:
    system = state.get("system_prompt") or "You are a helpful AI assistant."
    history = state.get("messages") or []
    hops = state.get("tool_hops") or 0

    # Only offer tools on hop 0
    tool_schemas = state.get("tool_schemas") if hops == 0 else None

    messages = [{"role": "system", "content": system}] + history

    result = await ollama_chat(
        messages=messages,
        model=state.get("model_name") or "llama3.2:3b",
        temperature=float(state.get("temperature") or 0.7),
        tools=tool_schemas,
    )

    content = result["content"] or ""
    tool_calls = result.get("tool_calls") or []

    # Fallback parser - only on hop 0
    if hops == 0 and not tool_calls and content:
        print(f"[graph] hop=0 no structured tool_calls, content len={len(content)}", flush=True)
        print(f"[graph] content head: {content[:200]!r}", flush=True)
        parsed = _try_parse_text_tool_call(content)
        print(f"[graph] parsed: {parsed}", flush=True)
        if parsed:
            tool_calls = [parsed]
            content = ""
    elif hops == 0 and tool_calls:
        print(f"[graph] hop=0 structured tool_calls: {len(tool_calls)}", flush=True)
    else:
        print(f"[graph] hop={hops} content len={len(content)}", flush=True)

    # Post-tool: replace garbage with a plain summary
    if hops > 0:
        looks_like_tool_json = (
            '{"type":"function"' in content
            or '"tool_calls"' in content
            or (content.strip().startswith("{") and "function" in content)
        )
        if looks_like_tool_json or not content.strip():
            content = _summarize_tool_result(state.get("traces") or [])

    state["last_content"] = content
    state["last_tool_calls"] = tool_calls
    state["meta"] = {
        "model": result["model"],
        "version": state.get("version"),
        "latency_ms": result["total_duration_ms"],
        "prompt_tokens": result["prompt_eval_count"],
        "completion_tokens": result["eval_count"],
    }
    # Record an LLM trace for latency attribution
    state.setdefault("traces", []).append({
        "kind": "llm",
        "name": "ollama.generate",
        "status": "success",
        "input": {"messages": len(messages)},
        "output": {"eval_count": result.get("eval_count", 0)},
        "error": None,
        "latency_ms": float(result.get("total_duration_ms", 0)),
    })
    return state


async def _tool_node(state: AgentState) -> AgentState:
    history = list(state.get("messages") or [])
    tool_calls = state.get("last_tool_calls") or []
    ctx = state.get("tool_ctx") or {}
    traces = state.get("traces") or []

    history.append({
        "role": "assistant",
        "content": state.get("last_content") or "",
        "tool_calls": [
            {"function": {"name": tc["name"], "arguments": tc["arguments"]}}
            for tc in tool_calls
        ],
    })

    for tc in tool_calls:
        name = tc["name"]
        args = tc["arguments"] or {}
        t0 = time.time()
        try:
            output = execute_tool(name, args, ctx)
            status = "success"
            error = None
        except Exception as e:
            output = {"error": str(e)}
            status = "error"
            error = str(e)

        latency_ms = int((time.time() - t0) * 1000)

        traces.append({
            "kind": "tool",
            "name": name,
            "status": status,
            "input": args,
            "output": output if isinstance(output, dict) else {"result": output},
            "error": error,
            "latency_ms": latency_ms,
        })

        history.append({
            "role": "tool",
            "name": name,
            "content": json.dumps(output if isinstance(output, dict) else {"result": output}),
        })

    state["messages"] = history
    state["traces"] = traces
    state["last_tool_calls"] = []
    state["tool_hops"] = (state.get("tool_hops") or 0) + 1
    return state


def _route_after_llm(state: AgentState) -> str:
    if state.get("last_tool_calls") and (state.get("tool_hops") or 0) < MAX_TOOL_HOPS:
        return "tools"
    return "end"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("llm", _llm_node)
    g.add_node("tools", _tool_node)

    g.set_entry_point("llm")
    g.add_conditional_edges("llm", _route_after_llm, {"tools": "tools", "end": END})
    g.add_edge("tools", "llm")
    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
