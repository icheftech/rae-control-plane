"""Tenant Model - Multi-Tenancy Support

Enables R.A.E. Control Plane to serve multiple organizations (tenants)
with complete data isolation and tenant-specific configuration.

Southern Shade LLC is the first tenant onboarding.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Tenant(Base):
    """Tenant model for multi-tenant SaaS deployment
    
    Each tenant represents an independent organization using the R.A.E. platform.
    All resources (workflows, capabilities, connectors, etc.) are scoped to a tenant.
    """
    __tablename__ = "tenants"
    
    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_key = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "southern_shade_llc"
    
    # Tenant metadata
    tenant_name = Column(String(255), nullable=False)  # e.g., "Southern Shade LLC"
    description = Column(Text, nullable=True)
    
    # Tenant status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Tenant-specific configuration (flexible JSON)
    settings = Column(JSONB, nullable=True, default=dict)
    # Example settings:
    # {
    #   "allowed_environments": ["dev", "staging", "prod"],
    #   "max_workflows": 100,
    #   "max_api_calls_per_hour": 10000,
    #   "data_retention_days": 365,
    #   "features": ["govcon_intel", "compliance_monitoring"]
    # }
    
    # Contact and billing
    primary_contact_email = Column(String(255), nullable=True)
    billing_email = Column(String(255), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)  # User/service principal
    
    # Relationships (all tenant-scoped resources)
    workflows = relationship("Workflow", back_populates="tenant", cascade="all, delete-orphan")
    capabilities = relationship("Capability", back_populates="tenant", cascade="all, delete-orphan")
    connectors = relationship("Connector", back_populates="tenant", cascade="all, delete-orphan")
    control_policies = relationship("ControlPolicy", back_populates="tenant", cascade="all, delete-orphan")
    kill_switches = relationship("KillSwitch", back_populates="tenant", cascade="all, delete-orphan")
    break_glass_records = relationship("BreakGlass", back_populates="tenant", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="tenant")
    change_requests = relationship("ChangeRequest", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(key='{self.tenant_key}', name='{self.tenant_name}', active={self.is_active})>"
    
    @property
    def is_operational(self) -> bool:
        """Check if tenant can create and execute workflows"""
        return self.is_active
    
    def get_setting(self, key: str, default=None):
        """Get tenant-specific setting by key"""
        if self.settings:
            return self.settings.get(key, default)
        return default
