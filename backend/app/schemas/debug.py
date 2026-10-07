from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DebugReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    call_id: str | None
    evaluation_result_id: str | None
    category: str
    stage: str
    severity: str
    root_cause: str
    evidence: list
    recommendation: list
    confidence: float
    created_at: datetime
