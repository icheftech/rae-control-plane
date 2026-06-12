"""Break Glass Model - Phase 2: Controls (NIST AI RMF MANAGE)

Emergency override for critical situations
Bypass policies EXCEPT kill switches
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

from app.db.base import Base


class BreakGlassReason(enum.Enum):
    """Valid reasons for breaking glass"""
    P0_INCIDENT = "p0_incident"          # Critical production incident
    DATA_LOSS = "data_loss"              # Prevent data loss
    SECURITY_RESPONSE = "security_response"  # Active security incident
    REGULATORY = "regulatory"            # Compliance requirement
    CUSTOMER_IMPACT = "customer_impact"  # Severe customer impact
    SYSTEM_FAILURE = "system_failure"    # System unavailable


class BreakGlassStatus(enum.Enum):
    """Break glass request lifecycle"""
    PENDING = "pending"      # Awaiting approval
    APPROVED = "approved"    # Approved, active
    DENIED = "denied"        # Rejected
    EXPIRED = "expired"      # Time limit exceeded
    REVOKED = "revoked"      # Manually revoked


class BreakGlass(Base):
    """Emergency override mechanism
    
    "Break glass in case of emergency"
    
    CRITICAL RULES:
    1. Cannot override kill switches (safety first)
    2. Time-bounded (auto-expire after X hours)
    3. Requires approval (dual authorization)
    4. Full audit trail (who, what, when, why)
    5. Post-incident review MANDATORY
    
    Use Cases:
    1. P0 Production Incident: Deploy hotfix immediately
       - Normal: Requires dual approval + testing
       - Break glass: Deploy now, justify later
    
    2. Data Loss Prevention: Emergency backup
       - Normal: Standard change management
       - Break glass: Immediate action to prevent loss
    
    3. Security Incident: Patch critical vulnerability
       - Normal: Standard deployment cycle
       - Break glass: Deploy security fix immediately
    
    Process:
    1. Incident commander requests break glass
    2. On-call approver grants (or denies)
    3. Window opens (e.g., 2 hours)
    4. Actions taken (logged separately)
    5. Window auto-closes
    6. Post-incident review (required)
    """
    __tablename__ = "break_glass"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    break_glass_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Scope (optional - can be global)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Request details
    name = Column(String(255), nullable=False)
    reason = Column(SQLEnum(BreakGlassReason), nullable=False)
    justification = Column(Text, nullable=False)  # Detailed explanation
    
    # Status and approval
    status = Column(SQLEnum(BreakGlassStatus), nullable=False, default=BreakGlassStatus.PENDING)
    
    # Time bounds (CRITICAL: Always time-limited)
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_from = Column(DateTime, nullable=True)  # When approved
    valid_until = Column(DateTime, nullable=True)  # Auto-expire
    duration_hours = Column(Integer, nullable=False, default=2)  # Default 2-hour window
    
    # People involved
    requested_by = Column(String(255), nullable=False)  # Incident commander
    approved_by = Column(String(255), nullable=True)    # On-call approver
    denied_by = Column(String(255), nullable=True)      # If denied
    revoked_by = Column(String(255), nullable=True)     # If revoked early
    
    # Approver comments
    approval_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Post-incident
    post_incident_review_completed = Column(Boolean, nullable=False, default=False)
    post_incident_notes = Column(Text, nullable=True)
    
    # Related incident tracking
    incident_id = Column(String(255), nullable=True, index=True)
    extra_metadata = Column(JSONB, nullable=True, default=dict, name="metadata")
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", backref="break_glass_requests")

    def __repr__(self):
        return f"<BreakGlass({self.status.value}, reason={self.reason.value}, requested_by={self.requested_by})>"

    @property
    def is_active(self) -> bool:
        """Check if break glass window is currently active"""
        if self.status != BreakGlassStatus.APPROVED:
            return False
        if not self.valid_from or not self.valid_until:
            return False
        now = datetime.utcnow()
        return self.valid_from <= now <= self.valid_until

    @property
    def is_expired(self) -> bool:
        """Check if break glass window has expired"""
        if not self.valid_until:
            return False
        return datetime.utcnow() > self.valid_until

    @property
    def needs_post_incident_review(self) -> bool:
        """Check if post-incident review is required"""
        return (self.status == BreakGlassStatus.APPROVED and 
                self.is_expired and 
                not self.post_incident_review_completed)

    def approve(self, approved_by: str, approval_notes: str = None):
        """Approve break glass request
        
        Args:
            approved_by: On-call approver
            approval_notes: Optional notes from approver
        """
        self.status = BreakGlassStatus.APPROVED
        self.approved_by = approved_by
        self.approval_notes = approval_notes
        self.valid_from = datetime.utcnow()
        self.valid_until = self.valid_from + timedelta(hours=self.duration_hours)

    def deny(self, denied_by: str, denial_reason: str):
        """Deny break glass request
        
        Args:
            denied_by: Person denying the request
            denial_reason: Why it was denied
        """
        self.status = BreakGlassStatus.DENIED
        self.denied_by = denied_by
        self.denial_reason = denial_reason

    def revoke(self, revoked_by: str, revocation_reason: str):
        """Revoke active break glass (early termination)
        
        Args:
            revoked_by: Person revoking
            revocation_reason: Why revoked early
        """
        self.status = BreakGlassStatus.REVOKED
        self.revoked_by = revoked_by
        self.revocation_reason = revocation_reason
        self.valid_until = datetime.utcnow()  # End immediately
