"""Persistent job metadata; task content stays in local definition files."""
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from .orchestration_run import now


class LocalJob(Base):
    __tablename__ = 'local_jobs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    idempotency_key = Column(UUID(as_uuid=True), nullable=False)
    task_key = Column(String(80), nullable=False)
    task_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default='queued', index=True)
    run_id = Column(UUID(as_uuid=True), unique=True)
    worker_id = Column(UUID(as_uuid=True), ForeignKey('local_workers.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    reason = Column(String(500))
    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_job_submission'),
        CheckConstraint("status IN ('queued','running','success','denied','error','interrupted')", name='local_job_status'),
    )


class LocalWorker(Base):
    __tablename__ = 'local_workers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=now)
    heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=now)
    stopped_at = Column(DateTime(timezone=True))
