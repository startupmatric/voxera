from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    agent_id: str | None = None


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str | None
    name: str
    description: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    input_text: str = Field(..., min_length=1)
    expected_output: str | None = None
    expected_tools: list[str] = []
    max_latency_ms: int = Field(120000, ge=1000, le=600000)
    enabled: bool = True


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str
    input_text: str
    expected_output: str | None
    expected_tools: list
    max_latency_ms: int
    enabled: bool
    created_at: datetime


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str | None
    status: str
    score: float
    answer_score: float
    tool_score: float
    latency_score: float
    error_score: float
    input_text: str
    expected_output: str | None
    actual_output: str | None
    expected_tools: list
    actual_tools: list
    latency_ms: float
    error: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    agent_version_id: str | None
    agent_version_number: int | None
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    average_score: float
    avg_latency_ms: float
    regression_detected: bool
    regression_details: dict
    created_at: datetime


class RunDetail(RunOut):
    results: list[ResultOut] = []
