from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    tenant_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    model_provider: str = "ollama"
    model_name: str = "llama3"
    temperature: float = 0.7
    voice_language: str = "en-US"
    system_prompt: str | None = None


class AgentUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str | None = None
    description: str | None = None
    status: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    voice_language: str | None = None
    system_prompt: str | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    tenant_id: str
    name: str
    description: str | None
    status: str
    model_provider: str
    model_name: str
    temperature: float
    voice_language: str
    system_prompt: str | None
    created_at: datetime
    updated_at: datetime