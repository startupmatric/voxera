from langgraph.graph import END, StateGraph

from .ollama_client import chat as ollama_chat
from .state import AgentState


async def _llm_node(state: AgentState) -> AgentState:
    """
    Core LLM node. Builds the final chat message list and calls Ollama.
    The system prompt comes from the agent's active version.
    """
    system = state.get("system_prompt") or "You are a helpful AI assistant."
    history = state.get("messages") or []

    messages = [{"role": "system", "content": system}] + history

    result = await ollama_chat(
        messages=messages,
        model=state.get("model_name") or "llama3.2:3b",
        temperature=float(state.get("temperature") or 0.7),
    )

    state["response"] = result["content"]
    state["meta"] = {
        "model": result["model"],
        "version": state.get("version"),
        "latency_ms": result["total_duration_ms"],
        "prompt_tokens": result["prompt_eval_count"],
        "completion_tokens": result["eval_count"],
    }
    return state


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("llm", _llm_node)
    g.set_entry_point("llm")
    g.add_edge("llm", END)
    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
