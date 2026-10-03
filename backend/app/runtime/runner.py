from ..models import Agent, AgentVersion
from .graph import get_graph
from .state import AgentState


def active_version_for(agent: Agent, db) -> AgentVersion | None:
    """
    Returns the currently active version snapshot, or None if the agent has none.
    """
    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent.id, AgentVersion.is_active.is_(True))
        .first()
    )


async def run_agent(agent: Agent, db, user_message: str, history: list[dict] | None = None) -> dict:
    """
    Executes the LangGraph workflow for one turn.
    Returns {"response": str, "meta": {...}, "version": int}.
    """
    version = active_version_for(agent, db)

    # If there is no active version, fall back to the live agent row
    if version is not None:
        system_prompt = version.system_prompt
        model_name = version.model_name
        temperature = version.temperature
        version_number = version.version
    else:
        system_prompt = agent.system_prompt
        model_name = agent.model_name
        temperature = agent.temperature
        version_number = 0

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    state: AgentState = {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "version": version_number,
        "system_prompt": system_prompt or "You are a helpful AI assistant.",
        "model_name": model_name or "llama3.2:3b",
        "temperature": float(temperature or 0.7),
        "messages": messages,
    }

    graph = get_graph()
    final = await graph.ainvoke(state)

    return {
        "response": final.get("response", ""),
        "meta": final.get("meta", {}),
        "version": version_number,
    }
