from typing import TypedDict


class AgentState(TypedDict, total=False):
    agent_id: str
    agent_name: str
    version: int
    system_prompt: str
    model_name: str
    temperature: float

    messages: list[dict]
    tool_schemas: list[dict] | None
    tool_ctx: dict
    traces: list[dict]
    tool_hops: int

    last_content: str
    last_tool_calls: list[dict]

    response: str
    meta: dict
