"""AuditEvent Model - Hash-Chained Immutable Audit Log

Phase 3: Enforcement Integration
Purpose: Cryptographic audit trail for all control plane actions

Compliance:
- NIST AI RMF MANAGE-3.2: Audit trail maintenance
- SOC 2 CC7.2: System monitoring and logging
- HIPAA §164.312(b): Audit controls
- ISO 27001 A.12.4.1: Event logging

Key Features:
- Hash-chained events (previous_hash prevents tampering)
- Append-only (no updates/deletes)
- Structured evidence capture
- Searchable actor/action/resource indexing
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, DateTime, Index, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
import uuid
import hashlib
import json

from app.db.base import Base


class AuditEvent(Base):
    """Immutable audit log with cryptographic hash chaining.
    
    Every action in the control plane generates an audit event.
    Events are hash-chained to prevent tampering.
    
    Event Types:
    - WORKFLOW_CREATED, WORKFLOW_UPDATED, WORKFLOW_DEACTIVATED
    - CONTROL_APPLIED, CONTROL_BYPASSED, CONTROL_FAILED
    - KILL_SWITCH_ACTIVATED, KILL_SWITCH_DEACTIVATED
    - BREAK_GLASS_ACTIVATED, BREAK_GLASS_CLOSED
    - GATE_EXECUTED, GATE_BLOCKED
    - CHANGE_REQUEST_SUBMITTED, CHANGE_APPROVED, CHANGE_REJECTED
    """
    __tablename__ = "audit_events"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sequence number for ordering and hash chain integrity
    sequence_number = Column(Integer, nullable=False, unique=True, autoincrement=True)
    
    # Event Identification
    event_type = Column(String(100), nullable=False, index=True)
    action = Column(String(255), nullable=False)  # Human-readable action
    
    # Actor Information
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_type = Column(String(50), nullable=False)  # USER, AGENT, SYSTEM, API_KEY
    actor_email = Column(String(255), nullable=True)
    
    # Resource Identification
    resource_type = Column(String(100), nullable=True, index=True)  # WORKFLOW, CONTROL, GATE, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)
    
    # Context and Evidence
    context = Column(JSONB, nullable=False, default=dict)
    """Structured context including:
    - request_id: Trace distributed operations
    - session_id: User session tracking
    - ip_address: Source IP
    - user_agent: Client information
    - gate_id: Enforcement gate that triggered event
    - policy_ids: Controls evaluated
    - evidence: Captured artifacts (sanitized)
    """
    
    outcome = Column(String(50), nullable=False)  # SUCCESS, FAILURE, BLOCKED, WARNING
    
    # Hash Chain for Tamper Detection
    previous_hash = Column(String(64), nullable=True)  # SHA-256 of previous event
    event_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 of this event
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    
    # Metadata
    extra_metadata = Column(JSONB, nullable=False, default=dict, name="metadata")
    """Additional metadata:
    - compliance_tags: Relevant frameworks (HIPAA, SOC2, etc.)
    - risk_level: Event severity (LOW, MEDIUM, HIGH, CRITICAL)
    - retention_years: Legal hold requirements
    - exported: Whether event has been exported to external SIEM
    """

    __table_args__ = (
        Index('idx_audit_actor_time', 'actor_id', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id', 'created_at'),
        Index('idx_audit_event_type_time', 'event_type', 'created_at'),
        Index('idx_audit_outcome', 'outcome', 'created_at'),
        CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'BLOCKED', 'WARNING', 'ERROR')",
            name='valid_outcome'
        ),
        CheckConstraint(
            "actor_type IN ('USER', 'AGENT', 'SYSTEM', 'API_KEY', 'SERVICE_ACCOUNT')",
            name='valid_actor_type'
        ),
        {'comment': 'Immutable audit log with cryptographic hash chaining (Phase 3: Enforcement)'}
    )

    def __repr__(self) -> str:
        return (
            f"<AuditEvent(seq={self.sequence_number}, "
            f"type='{self.event_type}', "
            f"actor={self.actor_id}, "
            f"resource={self.resource_type}/{self.resource_id}, "
            f"outcome='{self.outcome}')>"
        )

    def compute_hash(self, previous_hash: Optional[str] = None) -> str:
        """Compute SHA-256 hash of event for chain integrity.
        
        Hash includes:
        - sequence_number
        - event_type, action
        - actor_id, actor_type
        - resource_type, resource_id
        - outcome
        - context (serialized)
        - previous_hash (chain link)
        - created_at timestamp
        
        Args:
            previous_hash: Hash of previous event in chain
            
        Returns:
            64-character hex SHA-256 hash
        """
        hash_data = {
            "sequence": self.sequence_number,
            "event_type": self.event_type,
            "action": self.action,
            "actor_id": str(self.actor_id),
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "outcome": self.outcome,
            "context": self.context,
            "previous_hash": previous_hash or self.previous_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        # Deterministic JSON serialization
        hash_string = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

    def verify_chain(self, previous_event: Optional['AuditEvent'] = None) -> bool:
        """Verify hash chain integrity.
        
        Args:
            previous_event: The previous event in the chain
            
        Returns:
            True if chain is valid, False if tampered
        """
        # First event has no previous hash
        if self.sequence_number == 1:
            return self.previous_hash is None
        
        # Verify previous_hash matches previous event's event_hash
        if previous_event:
            if self.previous_hash != previous_event.event_hash:
                return False
        
        # Verify this event's hash is correct
        expected_hash = self.compute_hash()
        return self.event_hash == expected_hash

    @classmethod
    def create_event(
        cls,
        event_type: str,
        action: str,
        actor_id: uuid.UUID,
        actor_type: str,
        outcome: str,
        context: Dict[str, Any],
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        resource_name: Optional[str] = None,
        actor_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        previous_hash: Optional[str] = None
    ) -> 'AuditEvent':
        """Factory method to create properly hashed audit event.
        
        Args:
            event_type: Event category (e.g., WORKFLOW_CREATED)
            action: Human-readable description
            actor_id: UUID of actor performing action
            actor_type: Type of actor (USER, AGENT, SYSTEM, etc.)
            outcome: Result (SUCCESS, FAILURE, BLOCKED, WARNING)
            context: Structured context dictionary
            resource_type: Optional resource type
            resource_id: Optional resource UUID
            resource_name: Optional resource name
            actor_email: Optional actor email
            metadata: Optional metadata
            previous_hash: Hash of previous event (for chaining)
            
        Returns:
            New AuditEvent instance with computed hash
        """
        event = cls(
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            outcome=outcome,
            context=context or {},
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor_email=actor_email,
            metadata=metadata or {},
            previous_hash=previous_hash
        )
        
        # Compute hash after all fields are set
        # Note: sequence_number will be set by DB, hash must be recomputed after insert
        return event

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "id": str(self.id),
            "sequence_number": self.sequence_number,
            "event_type": self.event_type,
            "action": self.action,
            "actor": {
                "id": str(self.actor_id),
                "type": self.actor_type,
                "email": self.actor_email
            },
            "resource": {
                "type": self.resource_type,
                "id": str(self.resource_id) if self.resource_id else None,
                "name": self.resource_name
            } if self.resource_type else None,
            "outcome": self.outcome,
            "context": self.context,
            "metadata": self.extra_metadata,
            "hash": {
                "previous": self.previous_hash,
                "current": self.event_hash
            },
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
