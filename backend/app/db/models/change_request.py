"""ChangeRequest Model - Governed High-Risk Production Change Workflow

Phase 3: Enforcement Integration (FLAGSHIP FEATURE)
Purpose: Formal approval workflow for high-risk production changes

This is the FLAGSHIP use case for the S.S.O. Control Plane:
- Production deployments of AI agents/workflows
- Changes to PHI/PII-handling workflows
- Modifications to safety-critical capabilities
- AI model updates in production

Key Principles:
- Human-in-the-loop for high-risk decisions
- Multi-stage approval (requester → reviewer → approver)
- Time-bounded execution windows
- Automatic rollback on failure
- Post-deployment verification required

Compliance:
- NIST AI RMF GOVERN-1.3: Risk tolerance and decision authority
- NIST AI RMF MANAGE-1.1: Risk-based decision making
- SOC 2 CC8.1: Change management
- ISO 27001 A.12.1.2: Change management
- HIPAA §164.308(a)(8): Evaluation of changes
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class ChangeType(str, enum.Enum):
    """Types of changes requiring approval."""
    WORKFLOW_DEPLOYMENT = "WORKFLOW_DEPLOYMENT"  # Deploy new/updated workflow
    WORKFLOW_MODIFICATION = "WORKFLOW_MODIFICATION"  # Modify existing workflow
    CAPABILITY_GRANT = "CAPABILITY_GRANT"  # Grant new capability to agent
    CAPABILITY_REVOKE = "CAPABILITY_REVOKE"  # Revoke capability
    CONTROL_POLICY_UPDATE = "CONTROL_POLICY_UPDATE"  # Update control policy
    EMERGENCY_ACCESS = "EMERGENCY_ACCESS"  # Break-glass access
    MODEL_DEPLOYMENT = "MODEL_DEPLOYMENT"  # Deploy AI model
    CONFIG_CHANGE = "CONFIG_CHANGE"  # Infrastructure/config change


class ChangeStatus(str, enum.Enum):
    """Change request lifecycle states."""
    DRAFT = "DRAFT"  # Being prepared
    SUBMITTED = "SUBMITTED"  # Awaiting review
    UNDER_REVIEW = "UNDER_REVIEW"  # Being reviewed
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Awaiting final approval
    APPROVED = "APPROVED"  # Approved, ready for execution
    SCHEDULED = "SCHEDULED"  # Scheduled for future execution
    IN_PROGRESS = "IN_PROGRESS"  # Currently executing
    COMPLETED = "COMPLETED"  # Successfully completed
    FAILED = "FAILED"  # Execution failed
    ROLLED_BACK = "ROLLED_BACK"  # Automatically rolled back
    REJECTED = "REJECTED"  # Rejected by reviewer/approver
    CANCELLED = "CANCELLED"  # Cancelled by requester


class ChangeRiskLevel(str, enum.Enum):
    """Risk level of change (determines approval requirements)."""
    LOW = "LOW"  # Single approval, short window
    MEDIUM = "MEDIUM"  # Two approvals, standard window
    HIGH = "HIGH"  # Three approvals, extended review
    CRITICAL = "CRITICAL"  # Board approval, maximum scrutiny


class ChangeRequest(Base):
    """Governed change request for high-risk production changes.
    
    This is the FLAGSHIP feature demonstrating the full control plane:
    1. Requester submits change with rationale and evidence
    2. Technical reviewer validates feasibility and safety
    3. Business approver confirms impact and timing
    4. System executes within time-bounded window
    5. Post-deployment verification confirms success
    6. Automatic rollback if verification fails
    
    Every approved change creates:
    - Enforcement gates for execution
    - Audit events for traceability
    - Evidence capture for compliance
    - Rollback procedures for safety
    """
    __tablename__ = "change_requests"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Change Identification
    change_key = Column(String(100), nullable=False, unique=True, index=True)
    """Unique identifier (e.g., 'CHG-2025-001')"""
    
    change_type = Column(SQLEnum(ChangeType), nullable=False, index=True)
    risk_level = Column(SQLEnum(ChangeRiskLevel), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    """Business/technical justification for this change"""
    
    # Associated Resources
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='SET NULL'), nullable=True, index=True)
    capability_id = Column(UUID(as_uuid=True), ForeignKey('capabilities.id', ondelete='SET NULL'), nullable=True, index=True)
    control_policy_id = Column(UUID(as_uuid=True), ForeignKey('control_policies.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Requester Information
    requested_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    requested_by_email = Column(String(255), nullable=False)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Approval Workflow
    status = Column(SQLEnum(ChangeStatus), nullable=False, default=ChangeStatus.DRAFT, index=True)
    
    reviewer_id = Column(UUID(as_uuid=True), nullable=True)
    reviewer_email = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    approver_id = Column(UUID(as_uuid=True), nullable=True)
    approver_email = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Execution Window
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    """Time-bounded execution window (required for HIGH/CRITICAL risk)"""
    
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    
    # Change Details
    change_details = Column(JSONB, nullable=False, default=dict)
    """Specific change parameters:
    - For WORKFLOW_DEPLOYMENT: workflow_config, env_vars, resource_limits
    - For CAPABILITY_GRANT: capability_id, agent_id, constraints
    - For MODEL_DEPLOYMENT: model_artifact, validation_results, rollback_plan
    """
    
    # Impact Assessment
    impact_assessment = Column(JSONB, nullable=False, default=dict)
    """Required fields:
    - affected_systems: List of systems impacted
    - downtime_required: Boolean
    - estimated_duration: Minutes
    - rollback_time: Minutes to roll back if needed
    - data_impact: Description of data/PHI affected
    - compliance_impact: Regulatory considerations
    """
    
    # Testing and Validation
    testing_evidence = Column(JSONB, nullable=False, default=dict)
    """Pre-production testing results:
    - test_env_results: Staging environment test results
    - validation_passed: Boolean
    - test_coverage: Percentage
    - regression_tests: Results of regression testing
    """
    
    # Post-Deployment Verification
    verification_required = Column(Boolean, nullable=False, default=True)
    verification_criteria = Column(JSONB, nullable=False, default=list)
    """Success criteria to verify after deployment:
    [
        {
            "criterion": "Workflow completes successfully",
            "check_type": "AUTOMATED",
            "threshold": "100% success rate for 10 executions"
        }
    ]
    """
    
    verification_completed = Column(Boolean, nullable=False, default=False)
    verification_passed = Column(Boolean, nullable=True)
    verification_results = Column(JSONB, nullable=True)
    
    # Rollback
    rollback_required = Column(Boolean, nullable=False, default=False)
    rollback_procedure = Column(JSONB, nullable=False, default=dict)
    """Automated rollback steps if deployment fails"""
    
    rollback_executed = Column(Boolean, nullable=False, default=False)
    rollback_executed_at = Column(DateTime, nullable=True)
    rollback_successful = Column(Boolean, nullable=True)
    
    # Audit Trail
    audit_event_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    """Links to all audit events generated by this change"""
    
    # Metadata
    extra_metadata = Column(JSONB, nullable=False, default=dict, name="metadata")
    """Additional metadata:
    - compliance_tags: Frameworks addressed (HIPAA, SOC2, etc.)
    - stakeholders: List of notified parties
    - communication_plan: How stakeholders were informed
    - emergency_contact: Who to call if issues arise
    """
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    workflow = relationship("Workflow", foreign_keys=[workflow_id], backref="change_requests")
    capability = relationship("Capability", foreign_keys=[capability_id], backref="change_requests")
    control_policy = relationship("ControlPolicy", foreign_keys=[control_policy_id], backref="change_requests")

    __table_args__ = (
        Index('idx_change_status_risk', 'status', 'risk_level'),
        Index('idx_change_requested', 'requested_by', 'requested_at'),
        Index('idx_change_execution_window', 'scheduled_start', 'scheduled_end'),
        Index('idx_change_workflow', 'workflow_id', 'status'),
        {'comment': 'Governed change requests for high-risk production changes (Phase 3: Enforcement - FLAGSHIP)'}
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeRequest(key='{self.change_key}', "
            f"type='{self.change_type.value}', "
            f"status='{self.status.value}', "
            f"risk='{self.risk_level.value}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "id": str(self.id),
            "change_key": self.change_key,
            "change_type": self.change_type.value,
            "risk_level": self.risk_level.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "status": self.status.value,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "capability_id": str(self.capability_id) if self.capability_id else None,
            "control_policy_id": str(self.control_policy_id) if self.control_policy_id else None,
            "requester": {
                "id": str(self.requested_by),
                "email": self.requested_by_email,
                "requested_at": self.requested_at.isoformat() if self.requested_at else None
            },
            "reviewer": {
                "id": str(self.reviewer_id) if self.reviewer_id else None,
                "email": self.reviewer_email,
                "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
                "notes": self.review_notes
            } if self.reviewer_id else None,
            "approver": {
                "id": str(self.approver_id) if self.approver_id else None,
                "email": self.approver_email,
                "approved_at": self.approved_at.isoformat() if self.approved_at else None,
                "notes": self.approval_notes
            } if self.approver_id else None,
            "rejection": {
                "reason": self.rejection_reason,
                "rejected_by": str(self.rejected_by) if self.rejected_by else None,
                "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None
            } if self.rejection_reason else None,
            "execution_window": {
                "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None,
                "scheduled_end": self.scheduled_end.isoformat() if self.scheduled_end else None,
                "started_at": self.execution_started_at.isoformat() if self.execution_started_at else None,
                "completed_at": self.execution_completed_at.isoformat() if self.execution_completed_at else None
            },
            "change_details": self.change_details,
            "impact_assessment": self.impact_assessment,
            "testing_evidence": self.testing_evidence,
            "verification": {
                "required": self.verification_required,
                "criteria": self.verification_criteria,
                "completed": self.verification_completed,
                "passed": self.verification_passed,
                "results": self.verification_results
            },
            "rollback": {
                "required": self.rollback_required,
                "procedure": self.rollback_procedure,
                "executed": self.rollback_executed,
                "executed_at": self.rollback_executed_at.isoformat() if self.rollback_executed_at else None,
                "successful": self.rollback_successful
            },
            "audit_event_ids": [str(eid) for eid in self.audit_event_ids],
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def is_within_execution_window(self) -> bool:
        """Check if current time is within the approved execution window."""
        if not self.scheduled_start or not self.scheduled_end:
            return False
        now = datetime.utcnow()
        return self.scheduled_start <= now <= self.scheduled_end

    def requires_multi_stage_approval(self) -> bool:
        """Check if this change requires reviewer + approver."""
        return self.risk_level in (ChangeRiskLevel.MEDIUM, ChangeRiskLevel.HIGH, ChangeRiskLevel.CRITICAL)

    def can_auto_approve(self) -> bool:
        """Check if this change can be auto-approved (LOW risk only)."""
        return self.risk_level == ChangeRiskLevel.LOW
