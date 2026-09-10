"""Capability Model - Registry Backbone (Phase 1)

NIST AI RMF MAP function: Define operational capabilities per workflow
Links workflows to specific AI operations (model serving, data processing, etc.)
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Capability(Base):
    """Operational capabilities tied to workflows
    
    Examples:
    - "model_serving" capability for ML inference workflows
    - "data_pipeline" capability for ETL workflows
    - "phi_access" capability for PHI/PII handling
    
    Immutable once created - deactivation only
    """
    __tablename__ = "capabilities"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Workflow association
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Descriptive metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    
    # Configuration and constraints
    extra_metadata = Column(JSONB, nullable=True, default=dict, name="metadata")
    
    # Relationships
    workflow = relationship("Workflow", back_populates="capabilities")
    connectors = relationship("Connector", back_populates="capability", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Capability(key='{self.capability_key}', workflow_id={self.workflow_id}, active={self.is_active})>"

    @property
    def full_key(self) -> str:
        """Composite key: workflow_key.capability_key for audit trails"""
        return f"{self.workflow.workflow_key}.{self.capability_key}"
