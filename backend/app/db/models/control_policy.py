"""Control Policy Model - Phase 2: Controls (NIST AI RMF MANAGE)

Governance policies for production change management
The heart of R.A.E.: No changes without approval
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class PolicyAction(enum.Enum):
    """Actions a control policy can take"""
    ALLOW = "allow"          # Permit the change
    DENY = "deny"            # Block the change
    REQUIRE_APPROVAL = "require_approval"  # Human-in-the-loop
    DEGRADE = "degrade"      # Allow with limitations (read-only, etc)


class ApprovalType(enum.Enum):
    """Types of approvals required"""
    NONE = "none"
    SINGLE = "single"        # One approver
    DUAL = "dual"            # Two approvers (4-eyes principle)
    COMMITTEE = "committee"  # Review board


class ControlPolicy(Base):
    """Core governance policies
    
    Golden Path Example: Production Model Deployment
    - workflow_id: production_ml_deployment
    - policy_action: REQUIRE_APPROVAL
    - approval_type: DUAL (data scientist + ops lead)
    - approval_required_for: ["model_version_change", "infrastructure_change"]
    - auto_deny_conditions: {"after_hours": true, "high_severity_incidents": true}
    
    Kill switch: Overrides all policies (see kill_switch.py)
    """
    __tablename__ = "control_policies"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Workflow association (optional - can apply globally)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Policy details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    policy_action = Column(SQLEnum(PolicyAction), nullable=False)
    
    # Approval requirements
    approval_type = Column(SQLEnum(ApprovalType), nullable=False, default=ApprovalType.NONE)
    approval_required_for = Column(JSONB, nullable=True, default=list)  # List of change types
    approver_roles = Column(JSONB, nullable=True, default=list)  # Required approver roles
    
    # Conditions and constraints
    conditions = Column(JSONB, nullable=True, default=dict)  # When policy applies
    auto_deny_conditions = Column(JSONB, nullable=True, default=dict)  # Instant deny rules
    
    # Priority (higher number = higher priority)
    priority = Column(Integer, nullable=False, default=100)
    
    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    last_modified_by = Column(String(255), nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", backref="control_policies")

    def __repr__(self):
        return f"<ControlPolicy(key='{self.policy_key}', action={self.policy_action.value}, approval={self.approval_type.value})>"

    @property
    def requires_approval(self) -> bool:
        """Check if policy requires human approval"""
        return self.policy_action == PolicyAction.REQUIRE_APPROVAL

    @property
    def is_blocking(self) -> bool:
        """Check if policy can block changes"""
        return self.policy_action in (PolicyAction.DENY, PolicyAction.REQUIRE_APPROVAL)

    def evaluate_conditions(self, context: dict) -> bool:
        """Evaluate if policy applies to current context
        
        Args:
            context: Request context (time, user, change type, etc)
        
        Returns:
            True if policy should be applied
        """
        if not self.conditions:
            return True  # No conditions = always applies
        
        # Check auto-deny conditions first
        if self.auto_deny_conditions:
            for key, expected_value in self.auto_deny_conditions.items():
                if context.get(key) == expected_value:
                    return True  # Auto-deny triggered
        
        # Check standard conditions
        for key, expected_value in self.conditions.items():
            if context.get(key) != expected_value:
                return False
        
        return True
