import time

from ..models import Agent, AgentVersion, Trace
from .graph import get_graph
from .state import AgentState
from .tools.registry import all_schemas


def active_version_for(agent: Agent, db) -> AgentVersion | None:
    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent.id, AgentVersion.is_active.is_(True))
        .first()
    )


def _persist_traces(
    db,
    tenant_id: str,
    agent_id: str,
    call_id: str | None,
    traces: list[dict],
) -> None:
    for t in traces or []:
        row = Trace(
            tenant_id=tenant_id,
            agent_id=agent_id,
            call_id=call_id,
            kind=t.get("kind", "tool"),
            name=t.get("name", "unknown"),
            status=t.get("status", "success"),
            input_data=t.get("input") or {},
            output_data=t.get("output") or {},
            error=t.get("error"),
            latency_ms=float(t.get("latency_ms") or 0),
        )
        db.add(row)
    db.commit()


async def run_agent(
    agent: Agent,
    db,
    user_message: str,
    history: list[dict] | None = None,
    enable_tools: bool = True,
    call_id: str | None = None,
) -> dict:
    version = active_version_for(agent, db)

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

    tool_schemas = all_schemas() if enable_tools else None

    state: AgentState = {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "version": version_number,
        "system_prompt": system_prompt or "You are a helpful AI assistant.",
        "model_name": model_name or "llama3.2:3b",
        "temperature": float(temperature or 0.7),
        "messages": messages,
        "tool_schemas": tool_schemas,
        "tool_ctx": {"db": db, "tenant_id": agent.tenant_id, "agent_id": agent.id},
        "traces": [],
        "tool_hops": 0,
    }

    graph = get_graph()
    t0 = time.time()
    final = await graph.ainvoke(state)
    total_ms = int((time.time() - t0) * 1000)

    _persist_traces(
        db,
        agent.tenant_id,
        agent.id,
        call_id,
        final.get("traces") or [],
    )

    return {
        "response": final.get("last_content", ""),
        "meta": {
            **(final.get("meta") or {}),
            "tool_calls": len(final.get("traces") or []),
            "total_ms": total_ms,
        },
        "version": version_number,
        "tool_traces": final.get("traces") or [],
    }
