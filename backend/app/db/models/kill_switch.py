"""Kill Switch Model - Phase 2: Controls (NIST AI RMF MANAGE)

Emergency stop mechanism - overrides ALL policies
Critical safety feature for PHI/PII and production incidents
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum

from app.db.base import Base


class KillSwitchMode(enum.Enum):
    """Kill switch activation modes"""
    HARD_STOP = "hard_stop"      # Deny ALL changes (highest priority)
    SOFT_STOP = "soft_stop"      # Deny new changes, allow in-flight to complete
    READ_ONLY = "read_only"      # Allow reads, block writes
    DEGRADE = "degrade"          # Minimal operations only


class KillSwitchTrigger(enum.Enum):
    """What triggered the kill switch"""
    MANUAL = "manual"            # Human operator
    INCIDENT = "incident"        # P0/P1 production incident
    SECURITY = "security"        # Security breach detected
    COMPLIANCE = "compliance"    # Audit failure
    AUTOMATED = "automated"      # System health check
    DATA_ANOMALY = "data_anomaly"  # PHI/PII exposure risk


class KillSwitch(Base):
    """Emergency stop for all or specific workflows
    
    CRITICAL: Kill switch has HIGHEST priority
    - Overrides ALL control policies
    - Checked FIRST in every gate
    - Cannot be bypassed (even by break-glass)
    
    Use Cases:
    1. Production Incident (P0): HARD_STOP all deployments
    2. Security Breach: READ_ONLY mode while investigating
    3. PHI/PII Exposure: HARD_STOP workflow_id=phi_ml_pipeline
    4. After-hours freeze: SOFT_STOP new changes, allow scheduled jobs
    
    Activation requires:
    - Authorized personnel (ops lead, security team)
    - Reason documentation
    - Approval for deactivation (post-incident review)
    """
    __tablename__ = "kill_switches"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    switch_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Scope (NULL = global, affects everything)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Kill switch configuration
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    mode = Column(SQLEnum(KillSwitchMode), nullable=False)
    trigger = Column(SQLEnum(KillSwitchTrigger), nullable=False)
    
    # Activation state
    is_active = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime, nullable=True)  # When switch was pulled
    deactivated_at = Column(DateTime, nullable=True)  # When switch was released
    
    # Time-based controls
    auto_deactivate_at = Column(DateTime, nullable=True)  # Auto-release after X time
    
    # Audit and justification
    activated_by = Column(String(255), nullable=True)  # Who pulled the switch
    deactivated_by = Column(String(255), nullable=True)  # Who released it
    reason = Column(Text, nullable=False)  # WHY was it pulled
    resolution_notes = Column(Text, nullable=True)  # Post-incident notes
    
    # Related incident tracking
    incident_id = Column(String(255), nullable=True, index=True)  # PagerDuty, Jira, etc
    extra_metadata = Column(JSONB, nullable=True, default=dict, name="metadata")
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", backref="kill_switches")

    def __repr__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        scope = f"workflow={self.workflow_id}" if self.workflow_id else "GLOBAL"
        return f"<KillSwitch({status}, mode={self.mode.value}, {scope})>"

    @property
    def is_global(self) -> bool:
        """Check if kill switch affects ALL workflows"""
        return self.workflow_id is None

    @property
    def blocks_writes(self) -> bool:
        """Check if kill switch blocks write operations"""
        return self.mode in (KillSwitchMode.HARD_STOP, KillSwitchMode.SOFT_STOP, KillSwitchMode.READ_ONLY)

    @property
    def should_auto_deactivate(self) -> bool:
        """Check if kill switch should auto-release"""
        if not self.is_active or not self.auto_deactivate_at:
            return False
        return datetime.utcnow() >= self.auto_deactivate_at

    def activate(self, activated_by: str, reason: str, auto_deactivate_minutes: int = None):
        """Activate the kill switch
        
        Args:
            activated_by: User/service principal pulling the switch
            reason: Incident ID, security alert, etc
            auto_deactivate_minutes: Auto-release after X minutes (optional)
        """
        self.is_active = True
        self.activated_at = datetime.utcnow()
        self.activated_by = activated_by
        self.reason = reason
        
        if auto_deactivate_minutes:
            self.auto_deactivate_at = datetime.utcnow() + timedelta(minutes=auto_deactivate_minutes)

    def deactivate(self, deactivated_by: str, resolution_notes: str):
        """Deactivate the kill switch (post-incident)
        
        Args:
            deactivated_by: User releasing the switch
            resolution_notes: What was fixed, lessons learned
        """
        self.is_active = False
        self.deactivated_at = datetime.utcnow()
        self.deactivated_by = deactivated_by
        self.resolution_notes = resolution_notes
