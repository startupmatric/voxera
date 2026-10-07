from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_str


class EvaluationDataset(Base, TimestampMixin):
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cases: Mapped[list["EvaluationCase"]] = relationship(
        "EvaluationCase", back_populates="dataset", cascade="all, delete-orphan"
    )
    runs: Mapped[list["EvaluationRun"]] = relationship(
        "EvaluationRun", back_populates="dataset", cascade="all, delete-orphan"
    )


class EvaluationCase(Base, TimestampMixin):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    max_latency_ms: Mapped[int] = mapped_column(Integer, default=120000, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset", back_populates="cases")


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    agent_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    regression_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    regression_details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset", back_populates="runs")
    results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base, TimestampMixin):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    answer_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tool_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    input_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    expected_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    actual_tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="results")
