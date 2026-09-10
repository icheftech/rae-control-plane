"""EnforcementGate Model - Policy Enforcement Execution Points

Phase 3: Enforcement Integration
Purpose: Define enforcement gates where controls are evaluated

Gates are checkpoints in workflow execution where:
- Control policies are evaluated
- Kill switches are checked (FIRST)
- Evidence is captured
- Audit events are generated
- Execution is allowed/blocked based on policy

Compliance:
- NIST AI RMF MANAGE-2.1: Risk management processes
- NIST AI RMF MANAGE-4.1: Incident response
- SOC 2 CC6.1: Logical access controls
- ISO 27001 A.9.4.1: Information access restriction
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class GateType(str, enum.Enum):
    """Types of enforcement gates."""
    PRE_EXECUTION = "PRE_EXECUTION"  # Before workflow/agent runs
    POST_EXECUTION = "POST_EXECUTION"  # After workflow/agent completes
    CAPABILITY_REQUEST = "CAPABILITY_REQUEST"  # When agent requests capability
    PRODUCTION_CHANGE = "PRODUCTION_CHANGE"  # High-risk production changes
    DATA_ACCESS = "DATA_ACCESS"  # PHI/PII access gates
    MODEL_DEPLOYMENT = "MODEL_DEPLOYMENT"  # AI model deployment gates
    BREAK_GLASS_ENTRY = "BREAK_GLASS_ENTRY"  # Emergency access gates


class GateOutcome(str, enum.Enum):
    """Possible gate execution outcomes."""
    ALLOW = "ALLOW"  # All controls passed, proceed
    BLOCK = "BLOCK"  # One or more controls failed, block execution
    WARNING = "WARNING"  # Controls passed with warnings, proceed with caution
    HARD_STOP = "HARD_STOP"  # Kill switch active, deny all
    DEGRADE = "DEGRADE"  # Degraded mode, allow read-only or limited operations


class EnforcementGate(Base):
    """Enforcement gate where control policies are evaluated.
    
    Gates are checkpoints in workflow execution. When a gate is triggered:
    1. Check kill switches FIRST (hard stop if active)
    2. Evaluate applicable control policies
    3. Capture evidence (context, inputs, state)
    4. Generate audit event
    5. Return outcome (ALLOW/BLOCK/WARNING/HARD_STOP/DEGRADE)
    
    Gates can be:
    - Pre-configured for workflows/capabilities
    - Dynamically created for ad-hoc enforcement
    - Linked to change requests for high-risk operations
    """
    __tablename__ = "enforcement_gates"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Gate Identification
    gate_key = Column(String(100), nullable=False, unique=True, index=True)
    """Unique identifier for this gate (e.g., 'workflow.acme_invoice.pre_execution')"""
    
    gate_type = Column(SQLEnum(GateType), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Associated Resources
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='SET NULL'), nullable=True, index=True)
    capability_id = Column(UUID(as_uuid=True), ForeignKey('capabilities.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Control Policy Associations
    control_policy_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    """List of control policy UUIDs to evaluate at this gate"""
    
    # Enforcement Configuration
    enforcement_mode = Column(String(50), nullable=False, default='BLOCKING')
    """BLOCKING (fail-closed) or MONITORING (fail-open with warnings)"""
    
    require_all_pass = Column(Boolean, nullable=False, default=True)
    """If True, all controls must pass (AND logic). If False, any control can pass (OR logic)."""
    
    check_kill_switches = Column(Boolean, nullable=False, default=True)
    """If True, check kill switches before evaluating policies (RECOMMENDED)"""
    
    # Evidence Capture
    capture_inputs = Column(Boolean, nullable=False, default=True)
    capture_outputs = Column(Boolean, nullable=False, default=True)
    capture_context = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    extra_metadata = Column(JSONB, nullable=False, default=dict, name="metadata")
    """Additional configuration:
    - timeout_seconds: Max time for gate evaluation
    - retry_policy: Retry configuration for transient failures
    - notification_channels: Where to send alerts on failures
    - compliance_tags: Frameworks this gate addresses (HIPAA, SOC2, etc.)
    - risk_level: Gate criticality (LOW, MEDIUM, HIGH, CRITICAL)
    """
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    workflow = relationship("Workflow", foreign_keys=[workflow_id], backref="enforcement_gates")
    capability = relationship("Capability", foreign_keys=[capability_id], backref="enforcement_gates")

    __table_args__ = (
        Index('idx_gate_workflow', 'workflow_id', 'gate_type', 'is_active'),
        Index('idx_gate_capability', 'capability_id', 'gate_type', 'is_active'),
        Index('idx_gate_active', 'is_active', 'gate_type'),
        {'comment': 'Enforcement gates for control policy evaluation (Phase 3: Enforcement)'}
    )

    def __repr__(self) -> str:
        return (
            f"<EnforcementGate(key='{self.gate_key}', "
            f"type='{self.gate_type.value}', "
            f"mode='{self.enforcement_mode}', "
            f"active={self.is_active})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "id": str(self.id),
            "gate_key": self.gate_key,
            "gate_type": self.gate_type.value,
            "name": self.name,
            "description": self.description,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "capability_id": str(self.capability_id) if self.capability_id else None,
            "control_policy_ids": [str(pid) for pid in self.control_policy_ids],
            "enforcement_mode": self.enforcement_mode,
            "require_all_pass": self.require_all_pass,
            "check_kill_switches": self.check_kill_switches,
            "evidence_capture": {
                "inputs": self.capture_inputs,
                "outputs": self.capture_outputs,
                "context": self.capture_context
            },
            "metadata": self.extra_metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by),
            "updated_by": str(self.updated_by)
        }


class GateExecution(Base):
    """Record of a gate execution (for analytics and debugging).
    
    Every time a gate is triggered, we create a GateExecution record.
    This is separate from AuditEvent to allow detailed technical analysis.
    """
    __tablename__ = "gate_executions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Gate Reference
    gate_id = Column(UUID(as_uuid=True), ForeignKey('enforcement_gates.id', ondelete='CASCADE'), nullable=False, index=True)
    gate_key = Column(String(100), nullable=False, index=True)
    
    # Execution Context
    execution_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    """Links to workflow execution or capability invocation"""
    
    request_id = Column(String(100), nullable=True, index=True)
    """Distributed tracing ID"""
    
    # Actor
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_type = Column(String(50), nullable=False)  # USER, AGENT, SYSTEM
    
    # Evaluation Results
    outcome = Column(SQLEnum(GateOutcome), nullable=False, index=True)
    
    controls_evaluated = Column(JSONB, nullable=False, default=list)
    """List of control evaluations:
    [
        {
            "policy_id": "uuid",
            "policy_name": "Human Review Required",
            "result": "PASS" | "FAIL" | "ERROR",
            "reason": "Human reviewer approved",
            "evidence_ref": "uuid"
        }
    ]
    """
    
    kill_switches_checked = Column(JSONB, nullable=False, default=list)
    """List of kill switches checked:
    [
        {
            "switch_id": "uuid",
            "switch_name": "Emergency Stop - Production",
            "is_active": false,
            "scope": "GLOBAL"
        }
    ]
    """
    
    # Evidence
    captured_evidence = Column(JSONB, nullable=False, default=dict)
    """Captured context, inputs, outputs (sanitized for PHI/PII)"""
    
    # Performance
    duration_ms = Column(Integer, nullable=True)
    """Gate evaluation duration in milliseconds"""
    
    # Error Handling
    errors = Column(JSONB, nullable=False, default=list)
    """Any errors encountered during evaluation"""
    
    # Timestamps
    executed_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    # Relationships
    gate = relationship("EnforcementGate", foreign_keys=[gate_id], backref="executions")

    __table_args__ = (
        Index('idx_gate_exec_gate_time', 'gate_id', 'executed_at'),
        Index('idx_gate_exec_outcome_time', 'outcome', 'executed_at'),
        Index('idx_gate_exec_actor', 'actor_id', 'executed_at'),
        Index('idx_gate_exec_request', 'request_id'),
        {'comment': 'Gate execution history for analytics and debugging (Phase 3: Enforcement)'}
    )

    def __repr__(self) -> str:
        return (
            f"<GateExecution(gate_key='{self.gate_key}', "
            f"outcome='{self.outcome.value}', "
            f"duration={self.duration_ms}ms)>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "id": str(self.id),
            "gate_id": str(self.gate_id),
            "gate_key": self.gate_key,
            "execution_id": str(self.execution_id),
            "request_id": self.request_id,
            "actor": {
                "id": str(self.actor_id),
                "type": self.actor_type
            },
            "outcome": self.outcome.value,
            "controls_evaluated": self.controls_evaluated,
            "kill_switches_checked": self.kill_switches_checked,
            "captured_evidence": self.captured_evidence,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None
        }
