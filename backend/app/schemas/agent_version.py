from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    version: int
    system_prompt: str | None
    model_name: str
    temperature: float
    configuration: dict
    is_active: bool
    created_at: datetime


class AgentVersionDiff(BaseModel):
    from_version: int
    to_version: int
    changes: list[dict]
