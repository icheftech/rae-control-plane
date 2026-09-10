"""Immutable identity, decision inputs, and causal execution events."""
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
from .orchestration_run import now


class ExecutionContext(Base):
    __tablename__ = 'execution_contexts'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    protected_resource_scope = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)


class PolicySnapshot(Base):
    __tablename__ = 'policy_snapshots'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    context_id = Column(UUID(as_uuid=True), ForeignKey('execution_contexts.id'), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    content = Column(JSONB, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)


class ExecutionEvent(Base):
    __tablename__ = 'execution_events'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey('orchestration_runs.id'), nullable=False, index=True)
    context_id = Column(UUID(as_uuid=True), ForeignKey('execution_contexts.id'), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(40), nullable=False)
    step_id = Column(String(80))
    parent_event_id = Column(UUID(as_uuid=True), ForeignKey('execution_events.id'))
    caused_by_event_id = Column(UUID(as_uuid=True), ForeignKey('execution_events.id'))
    policy_snapshot_id = Column(UUID(as_uuid=True), ForeignKey('policy_snapshots.id'))
    state = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    details = Column(JSONB, nullable=False, default=dict)
