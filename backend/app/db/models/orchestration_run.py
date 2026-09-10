"""Content-free execution history; independent from the audit hash chain."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


def now():
    return datetime.now(timezone.utc)


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source = Column(String(30), nullable=False)
    request_id = Column(String(36), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    context_id = Column(UUID(as_uuid=True), ForeignKey('execution_contexts.id'))
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=False, default=now)
    completed_at = Column(DateTime(timezone=True))
    step_count = Column(Integer, nullable=False)
    decision_reason = Column(String(500))
    __table_args__ = (
        CheckConstraint("status IN ('pending','success','error','denied')", name="run_status"),
        Index("ix_runs_status_time", "status", "started_at"),
    )


class OrchestrationRunEvent(Base):
    __tablename__ = "orchestration_run_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("orchestration_runs.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    step_id = Column(String(80), nullable=False)
    step_type = Column(String(30), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=now)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="pending")
    decision_reason = Column(String(500))
    model = Column(String(120))
    token_usage = Column(JSONB, nullable=False, default=dict)
    input_ref = Column(String(160), nullable=False)
    output_ref = Column(String(160))
    __table_args__ = (CheckConstraint("status IN ('pending','success','error','denied')", name="run_event_status"),)
