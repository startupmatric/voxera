from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] | None = None
    enable_tools: bool = True


class ChatResponse(BaseModel):
    response: str
    version: int
    meta: dict
    tool_traces: list[dict] = []
