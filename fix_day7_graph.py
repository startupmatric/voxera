from pathlib import Path

content = '''import json
import time
from typing import Any

from langgraph.graph import END, StateGraph

from .ollama_client import chat as ollama_chat
from .state import AgentState
from .tools.registry import execute_tool

MAX_TOOL_HOPS = 5


async def _llm_node(state: AgentState) -> AgentState:
    """
    LLM node. Sends the system prompt + history + any tool schemas.
    If the LLM requests tools, we set state['pending_tools'] and route to the tool node.
    """
    system = state.get("system_prompt") or "You are a helpful AI assistant."
    history = state.get("messages") or []
    tool_schemas = state.get("tool_schemas") or None

    messages = [{"role": "system", "content": system}] + history

    result = await ollama_chat(
        messages=messages,
        model=state.get("model_name") or "llama3.2:3b",
        temperature=float(state.get("temperature") or 0.7),
        tools=tool_schemas,
    )

    state["last_content"] = result["content"]
    state["last_tool_calls"] = result.get("tool_calls") or []
    state["meta"] = {
        "model": result["model"],
        "version": state.get("version"),
        "latency_ms": result["total_duration_ms"],
        "prompt_tokens": result["prompt_eval_count"],
        "completion_tokens": result["eval_count"],
    }
    return state


async def _tool_node(state: AgentState) -> AgentState:
    """
    Executes every tool call the LLM requested, appends the assistant's tool_call
    message + each tool result to history, then returns control to the LLM.
    """
    history = list(state.get("messages") or [])
    tool_calls = state.get("last_tool_calls") or []
    ctx = state.get("tool_ctx") or {}
    traces = state.get("traces") or []

    # Represent the assistant's tool-call request
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
    if state.get("last_tool_calls"):
        if (state.get("tool_hops") or 0) >= MAX_TOOL_HOPS:
            return "end"
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
'''

Path("backend/app/runtime/graph.py").write_text(content, encoding="utf-8")
print("Wrote graph.py")
print("Has tool loop:", "_tool_node" in content)