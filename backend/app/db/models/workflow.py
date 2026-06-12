"""Workflow Model - Registry Backbone (Phase 1)

NIST AI RMF MAP function: Catalog high-risk AI workflows
Enterprise-grade model for PHI/PII regulated environments
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum as SQLEnum
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
    workflow_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Descriptive metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # NIST AI RMF classification
    risk_level = Column(SQLEnum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    
    # Lifecycle management
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.ACTIVE)
    
    # Audit trail (append-only)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)  # User/service principal
    
    # Flexible schema for domain-specific metadata
    extra_metadata = Column(JSONB, nullable=True, default=dict, name="metadata")
    
    # Relationships
    capabilities = relationship("Capability", back_populates="workflow", cascade="all, delete-orphan")
    change_requests = relationship("ChangeRequest", back_populates="workflow")

    def __repr__(self):
        return f"<Workflow(key='{self.workflow_key}', risk={self.risk_level.value}, status={self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if workflow accepts new change requests"""
        return self.status == WorkflowStatus.ACTIVE

    @property
    def is_high_risk(self) -> bool:
        """High-risk workflows require additional controls"""
        return self.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)
