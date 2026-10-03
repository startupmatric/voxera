from typing import TypedDict


class AgentState(TypedDict, total=False):
    agent_id: str
    agent_name: str
    version: int
    system_prompt: str
    model_name: str
    temperature: float
    messages: list[dict]      # OpenAI-style chat history: [{"role": "...", "content": "..."}]
    response: str
    meta: dict
