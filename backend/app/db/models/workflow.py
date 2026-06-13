"""Workflow Model - Registry Backbone (Phase 1)

NIST AI RMF MAP function: Catalog high-risk AI workflows
Enterprise-grade model for PHI/PII regulated environments
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class RiskLevel(enum.Enum):
    """NIST AI RMF Risk Classifications"""
    CRITICAL = "critical"  # PHI/PII, production deployment
    HIGH = "high"          # Model serving, data pipelines
    MEDIUM = "medium"      # Development, staging
    LOW = "low"            # Testing, non-production


class WorkflowStatus(enum.Enum):
    """Lifecycle status for workflows"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"  # Never delete - audit chain integrity
    DEACTIVATED = "deactivated"  # Soft delete


class Workflow(Base):
    """Core registry model for AI workflows

    Immutable audit trail: workflow_key NEVER changes once created
    Deactivation only - no deletions allowed
    """
    __tablename__ = "workflows"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_key = Column(String(255), unique=True, nullable=True, index=True)

    # Descriptive metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Schema version (semver string, e.g. "1.0.0") — required, no default
    version = Column(String(50), nullable=False)

    # NIST AI RMF classification
    risk_level = Column(SQLEnum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)

    # Lifecycle management
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.ACTIVE)

    # Soft-delete flag — True means workflow is operational
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit trail (append-only)
    # Both timestamps are set to the SAME instant at creation so that
    # created_at == updated_at holds immediately after the first commit.
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=None, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)  # User/service principal

    # Flexible schema for domain-specific metadata
    extra_metadata = Column(JSONB, nullable=True, default=dict, name="metadata")

    # Relationships
    capabilities = relationship("Capability", back_populates="workflow", cascade="all, delete-orphan")
    change_requests = relationship("ChangeRequest", back_populates="workflow")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_workflow_name_version"),
    )

    def __init__(self, **kwargs):
        # Ensure created_at and updated_at share the exact same timestamp on creation
        if "created_at" not in kwargs and "updated_at" not in kwargs:
            now = datetime.utcnow()
            kwargs.setdefault("created_at", now)
            kwargs.setdefault("updated_at", now)
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Workflow(key='{self.workflow_key}', risk={self.risk_level.value}, status={self.status.value})>"

    @property
    def is_high_risk(self) -> bool:
        """High-risk workflows require additional controls"""
        return self.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)
