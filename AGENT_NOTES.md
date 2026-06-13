# 🔒 R.A.E. CONTROL PLANE — AGENT IMPLEMENTATION NOTES

## CRITICAL: READ THIS SECTION FIRST

**You are building a PRODUCTION SYSTEM for ENTERPRISE CLIENTS in REGULATED INDUSTRIES.**

You are implementing the **R.A.E. (Runtime Authority Engine)** control plane for **Southern Shade Technologies (SST)**.

R.A.E. is a **governed autonomy platform** designed for:
- Regulated enterprises
- Government, healthcare, finance
- Environments handling PHI/PII
- High-risk automated changes

**Code Quality Standards**:
- Type hints on ALL functions
- Docstrings on ALL classes and public methods
- Error handling on EVERY external call
- Logging at appropriate levels
- Security-first mindset (never trust input)
- Performance considerations (use indexes, cache appropriately)

---

## SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Web    │  │  Mobile  │  │   CLI    │  │   API    │   │
│  │  Browser │  │   App    │  │   Tool   │  │  Client  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS (TLS 1.3)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway Layer                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Nginx / AWS ALB                                       │ │
│  │  - Rate Limiting                                       │ │
│  │  - CORS                                                │ │
│  │  - Security Headers                                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Authentication Layer (Entra ID)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  OAuth 2.0 / OIDC                                      │ │
│  │  - Token Validation                                    │ │
│  │  - Role/Permission Mapping                             │ │
│  │  - Session Management                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer (FastAPI)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Workflow   │  │    Change    │  │     Kill     │     │
│  │   Service    │  │   Request    │  │    Switch    │     │
│  │              │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Audit     │  │  Enforcement │  │  Capability  │     │
│  │   Service    │  │     Gate     │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Enforcement Layer                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  1. Kill Switch Check (PRIORITY 1 - ALWAYS FIRST)     │ │
│  │  2. Break-Glass Check                                  │ │
│  │  3. Policy Evaluation                                  │ │
│  │  4. Approval Check                                     │ │
│  │  5. Rate Limit Check                                   │ │
│  │  6. Capability Check                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │    Redis     │  │  S3 (Audit)  │     │
│  │  (Primary)   │  │  (Cache)     │  │  (Archive)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Observability Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Metrics    │  │     Logs     │  │    Traces    │     │
│  │ (Prometheus) │  │  (ELK/Cloud) │  │   (Jaeger)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## DATABASE SCHEMA DEEP DIVE

### Audit Event Hash Chain

**CRITICAL SECURITY COMPONENT** - This is what makes the audit trail tamper-evident.

```python
# How the hash chain works:

# Event 1 (First event in chain)
event_1 = AuditEvent(
    event_type="SYSTEM_INIT",
    action="System initialized",
    # ... other fields ...
    previous_hash=None  # No previous event
)
event_1.event_hash = event_1.calculate_hash()
# event_hash = SHA256(event_data + previous_hash)
# Result: "a1b2c3d4e5f6..."

# Event 2 (Linked to Event 1)
event_2 = AuditEvent(
    event_type="USER_LOGIN",
    action="User logged in",
    # ... other fields ...
    previous_hash=event_1.event_hash  # Link to previous
)
event_2.event_hash = event_2.calculate_hash()
# event_hash = SHA256(event_data + "a1b2c3d4e5f6...")
# Result: "f6e5d4c3b2a1..."

# Event 3 (Linked to Event 2)
event_3 = AuditEvent(
    event_type="WORKFLOW_EXECUTED",
    action="Workflow executed",
    # ... other fields ...
    previous_hash=event_2.event_hash  # Link to previous
)
event_3.event_hash = event_3.calculate_hash()
# event_hash = SHA256(event_data + "f6e5d4c3b2a1...")

# Verification
is_valid = event_2.verify_chain(previous_event=event_1)
# This recalculates event_2's hash and checks if it matches stored value
# If someone tampered with event_1, event_2's hash wouldn't match
```

**Implementation Requirements**:
```python
# In backend/app/db/models/audit_event.py

import hashlib
import json
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB

class AuditEvent(Base):
    """
    Immutable audit event with cryptographic hash chain.
    
    Security Properties:
    - Append-only (no updates or deletes allowed)
    - Hash-chained (tampering breaks the chain)
    - Timestamped (cannot backdate events)
    - Signed (cannot repudiate events)
    
    Compliance Mappings:
    - NIST AI RMF MANAGE-3.2 (Audit trail maintenance)
    - SOC 2 CC7.2 (System monitoring)
    - HIPAA §164.312(b) (Audit controls)
    """
    
    __tablename__ = "audit_events"
    
    id = Column(String(36), primary_key=True)  # UUID
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(Text, nullable=False)
    actor_id = Column(String(36), nullable=False, index=True)
    actor_type = Column(String(20), nullable=False)  # USER, AGENT, SYSTEM
    outcome = Column(String(20), nullable=False)  # SUCCESS, FAILURE, PARTIAL
    
    # Contextual data (IP, user agent, request ID, etc.)
    context = Column(JSONB, nullable=True)
    
    # Resource being acted upon
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    
    # Hash chain fields (CRITICAL)
    event_hash = Column(String(64), nullable=False, unique=True)  # SHA-256
    previous_hash = Column(String(64), nullable=True)  # Links to prior event
    
    # Timestamps (IMMUTABLE - set once)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def calculate_hash(self) -> str:
        """
        Calculate SHA-256 hash of event data.
        
        Hash includes:
        - Event metadata (type, action, actor, outcome)
        - Resource info (type, ID)
        - Timestamp
        - Previous event hash (creates chain)
        
        Returns:
            64-character hex string (SHA-256)
        """
        # Create deterministic JSON representation
        event_data = {
            "event_type": self.event_type,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "outcome": self.outcome,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "created_at": self.created_at.isoformat(),
            "previous_hash": self.previous_hash
        }
        
        # Convert to JSON (sorted keys for consistency)
        json_str = json.dumps(event_data, sort_keys=True)
        
        # Calculate SHA-256
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def verify_chain(self, previous_event: 'AuditEvent' = None) -> bool:
        """
        Verify this event's hash and chain integrity.
        
        Checks:
        1. Event hash matches calculated value
        2. Previous hash matches previous event's hash (if provided)
        
        Args:
            previous_event: The event that should precede this one
            
        Returns:
            True if chain is valid, False if tampered
        """
        # Check 1: Verify this event's hash
        calculated = self.calculate_hash()
        if calculated != self.event_hash:
            return False
        
        # Check 2: Verify link to previous event
        if previous_event is not None:
            if self.previous_hash != previous_event.event_hash:
                return False
        
        return True
    
    @classmethod
    def create_event(
        cls,
        event_type: str,
        action: str,
        actor_id: str,
        actor_type: str,
        outcome: str,
        context: dict = None,
        resource_type: str = None,
        resource_id: str = None,
        previous_hash: str = None
    ) -> 'AuditEvent':
        """
        Factory method to create a new audit event.
        
        ALWAYS use this method instead of direct instantiation to ensure
        hash is calculated correctly.
        
        Args:
            event_type: Type of event (e.g., "USER_LOGIN", "WORKFLOW_EXECUTED")
            action: Human-readable description
            actor_id: ID of user/agent performing action
            actor_type: USER, AGENT, or SYSTEM
            outcome: SUCCESS, FAILURE, or PARTIAL
            context: Additional metadata (IP, user agent, etc.)
            resource_type: Type of resource (e.g., "WORKFLOW", "CHANGE_REQUEST")
            resource_id: ID of resource
            previous_hash: Hash of previous event in chain
            
        Returns:
            New AuditEvent with calculated hash
        """
        import uuid
        
        event = cls(
            id=str(uuid.uuid4()),
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            outcome=outcome,
            context=context or {},
            resource_type=resource_type,
            resource_id=resource_id,
            previous_hash=previous_hash,
            created_at=datetime.utcnow()
        )
        
        # Calculate and set hash
        event.event_hash = event.calculate_hash()
        
        return event
```

---

## ENFORCEMENT GATE IMPLEMENTATION

**This is the core security mechanism** - every action goes through gates.

```python
# In backend/app/services/enforcement.py

from typing import Dict, Any, Optional
from datetime import datetime
from app.db.models import (
    EnforcementGate,
    GateExecution,
    KillSwitch,
    KillSwitchStatus,
    ControlPolicy,
    AuditEvent
)
from app.db.database import SessionLocal

class EnforcementService:
    """
    Central enforcement service that evaluates all control policies.
    
    Gate Execution Order (NON-NEGOTIABLE):
    1. Kill Switch Check (ALWAYS FIRST - hardcoded priority)
    2. Break-Glass Check
    3. Policy Evaluation
    4. Approval Check
    5. Rate Limit Check
    6. Capability Check
    
    If ANY check fails, execution stops immediately.
    """
    
    def __init__(self):
        self.db = SessionLocal()
    
    def evaluate_gate(
        self,
        gate_type: str,
        workflow_id: str,
        capability_id: Optional[str],
        context: Dict[str, Any]
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Evaluate an enforcement gate.
        
        Args:
            gate_type: PRE_EXECUTION, POST_EXECUTION, etc.
            workflow_id: Workflow being executed
            capability_id: Specific capability (if applicable)
            context: Execution context (user, request, data, etc.)
            
        Returns:
            (allowed, reason, metadata)
            - allowed: True if action is permitted
            - reason: Why action was allowed/denied
            - metadata: Additional info (policies evaluated, etc.)
        """
        start_time = datetime.utcnow()
        
        try:
            # PRIORITY 1: Kill Switch Check (ALWAYS FIRST)
            kill_switch_result = self._check_kill_switches(
                workflow_id, capability_id
            )
            if not kill_switch_result['allowed']:
                self._log_gate_execution(
                    gate_type, workflow_id, capability_id,
                    allowed=False,
                    reason=kill_switch_result['reason'],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return False, kill_switch_result['reason'], kill_switch_result
            
            # PRIORITY 2: Break-Glass Check
            break_glass_result = self._check_break_glass(context)
            if break_glass_result['active']:
                # Break-glass is active - allow but log extensively
                self._log_break_glass_usage(workflow_id, context)
                return True, "Break-glass access granted", break_glass_result
            
            # PRIORITY 3: Policy Evaluation
            policy_result = self._evaluate_policies(
                gate_type, workflow_id, capability_id, context
            )
            if not policy_result['allowed']:
                self._log_gate_execution(
                    gate_type, workflow_id, capability_id,
                    allowed=False,
                    reason=policy_result['reason'],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return False, policy_result['reason'], policy_result
            
            # PRIORITY 4: Approval Check (for high-risk workflows)
            approval_result = self._check_approvals(workflow_id, context)
            if not approval_result['allowed']:
                self._log_gate_execution(
                    gate_type, workflow_id, capability_id,
                    allowed=False,
                    reason=approval_result['reason'],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return False, approval_result['reason'], approval_result
            
            # PRIORITY 5: Rate Limit Check
            rate_limit_result = self._check_rate_limits(workflow_id, context)
            if not rate_limit_result['allowed']:
                self._log_gate_execution(
                    gate_type, workflow_id, capability_id,
                    allowed=False,
                    reason=rate_limit_result['reason'],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return False, rate_limit_result['reason'], rate_limit_result
            
            # PRIORITY 6: Capability Check
            capability_result = self._check_capabilities(capability_id, context)
            if not capability_result['allowed']:
                self._log_gate_execution(
                    gate_type, workflow_id, capability_id,
                    allowed=False,
                    reason=capability_result['reason'],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return False, capability_result['reason'], capability_result
            
            # All checks passed
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._log_gate_execution(
                gate_type, workflow_id, capability_id,
                allowed=True,
                reason="All checks passed",
                duration_ms=duration_ms
            )
            
            return True, "Execution authorized", {
                'checks_passed': [
                    'kill_switch',
                    'break_glass',
                    'policy',
                    'approval',
                    'rate_limit',
                    'capability'
                ],
                'duration_ms': duration_ms
            }
            
        except Exception as e:
            # FAIL CLOSED - if anything goes wrong, deny
            self._log_gate_execution(
                gate_type, workflow_id, capability_id,
                allowed=False,
                reason=f"Gate evaluation error: {str(e)}",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            return False, f"Gate evaluation error: {str(e)}", {'error': str(e)}
    
    def _check_kill_switches(
        self,
        workflow_id: str,
        capability_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Check if any kill switches are active.
        
        Kill Switch Hierarchy:
        1. GLOBAL - Stops entire system
        2. WORKFLOW - Stops specific workflow
        3. CAPABILITY - Stops specific capability
        
        Returns immediately on first active kill switch.
        """
        # Check GLOBAL kill switch first
        global_ks = self.db.query(KillSwitch).filter(
            KillSwitch.scope == "GLOBAL",
            KillSwitch.status == KillSwitchStatus.ACTIVE
        ).first()
        
        if global_ks:
            return {
                'allowed': False,
                'reason': f"GLOBAL kill switch active: {global_ks.reason}",
                'kill_switch_id': global_ks.id,
                'scope': 'GLOBAL'
            }
        
        # Check WORKFLOW kill switch
        workflow_ks = self.db.query(KillSwitch).filter(
            KillSwitch.scope == "WORKFLOW",
            KillSwitch.workflow_id == workflow_id,
            KillSwitch.status == KillSwitchStatus.ACTIVE
        ).first()
        
        if workflow_ks:
            return {
                'allowed': False,
                'reason': f"Workflow kill switch active: {workflow_ks.reason}",
                'kill_switch_id': workflow_ks.id,
                'scope': 'WORKFLOW'
            }
        
        # Check CAPABILITY kill switch (if capability provided)
        if capability_id:
            capability_ks = self.db.query(KillSwitch).filter(
                KillSwitch.scope == "CAPABILITY",
                KillSwitch.capability_id == capability_id,
                KillSwitch.status == KillSwitchStatus.ACTIVE
            ).first()
            
            if capability_ks:
                return {
                    'allowed': False,
                    'reason': f"Capability kill switch active: {capability_ks.reason}",
                    'kill_switch_id': capability_ks.id,
                    'scope': 'CAPABILITY'
                }
        
        # No active kill switches
        return {'allowed': True, 'reason': 'No active kill switches'}
    
    def _check_break_glass(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if break-glass access is active for this user."""
        # Implementation details...
        pass
    
    def _evaluate_policies(
        self,
        gate_type: str,
        workflow_id: str,
        capability_id: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate all applicable control policies."""
        # Implementation details...
        pass
    
    def _check_approvals(
        self,
        workflow_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if required approvals are present."""
        # Implementation details...
        pass
    
    def _check_rate_limits(
        self,
        workflow_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if rate limits are exceeded."""
        # Implementation details...
        pass
    
    def _check_capabilities(
        self,
        capability_id: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if capability is allowed."""
        # Implementation details...
        pass
    
    def _log_gate_execution(
        self,
        gate_type: str,
        workflow_id: str,
        capability_id: Optional[str],
        allowed: bool,
        reason: str,
        duration_ms: float
    ):
        """Log gate execution to database."""
        # Implementation details...
        pass
    
    def _log_break_glass_usage(
        self,
        workflow_id: str,
        context: Dict[str, Any]
    ):
        """Log break-glass access (requires post-incident review)."""
        # Implementation details...
        pass
```

---

## CHANGE REQUEST WORKFLOW (FLAGSHIP)

```python
# In backend/app/services/change_request.py

from enum import Enum
from typing import List, Dict, Any
from datetime import datetime
from app.db.models import (
    ChangeRequest,
    ChangeType,
    ChangeRiskLevel,
    ChangeStatus,
    Workflow,
    AuditEvent
)
from app.services.enforcement import EnforcementService

class ChangeRequestService:
    """
    Flagship workflow: Governed production changes.
    
    This showcases S.S.O.'s core value:
    - AI agents propose changes
    - Humans approve based on risk
    - Cryptographic audit trail
    - No direct execution by agents
    
    Flow:
    1. Agent creates ChangeRequest
    2. Risk assessment (auto-calculated)
    3. Route to approvers based on risk
    4. Approvals collected
    5. Enforcement gates evaluated
    6. Change executed
    7. Audit trail updated
    8. Stakeholders notified
    """
    
    def __init__(self):
        self.db = SessionLocal()
        self.enforcement = EnforcementService()
    
    def create_change_request(
        self,
        change_type: ChangeType,
        title: str,
        description: str,
        rationale: str,
        requested_by: str,
        requested_by_email: str,
        workflow_id: str = None,
        capability_id: str = None,
        connector_id: str = None,
        change_data: Dict[str, Any] = None
    ) -> ChangeRequest:
        """
        Create a new change request.
        
        This is the ONLY way to propose production changes.
        Agents cannot execute changes directly.
        
        Args:
            change_type: Type of change (WORKFLOW_DEPLOYMENT, etc.)
            title: Short description
            description: Detailed description
            rationale: Why is this change needed?
            requested_by: User ID of requester
            requested_by_email: Email for notifications
            workflow_id: If deploying/modifying workflow
            capability_id: If adding/modifying capability
            connector_id: If adding/modifying connector
            change_data: Structured change details
            
        Returns:
            New ChangeRequest in PENDING status
        """
        import uuid
        
        # Calculate risk level automatically
        risk_level = self._assess_risk(
            change_type, workflow_id, capability_id, connector_id, change_data
        )
        
        # Create change request
        change_request = ChangeRequest(
            id=str(uuid.uuid4()),
            change_key=self._generate_change_key(),
            change_type=change_type,
            risk_level=risk_level,
            title=title,
            description=description,
            rationale=rationale,
            requested_by=requested_by,
            requested_by_email=requested_by_email,
            workflow_id=workflow_id,
            capability_id=capability_id,
            connector_id=connector_id,
            change_data=change_data or {},
            status=ChangeStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        self.db.add(change_request)
        self.db.commit()
        
        # Create audit event
        self._create_audit_event(
            event_type="CHANGE_REQUEST_CREATED",
            action=f"Created change request: {title}",
            actor_id=requested_by,
            resource_id=change_request.id,
            context={
                'change_type': change_type.value,
                'risk_level': risk_level.value
            }
        )
        
        # Route to approvers
        self._route_to_approvers(change_request)
        
        return change_request
    
    def _assess_risk(
        self,
        change_type: ChangeType,
        workflow_id: str,
        capability_id: str,
        connector_id: str,
        change_data: Dict[str, Any]
    ) -> ChangeRiskLevel:
        """
        Auto-calculate risk level based on change characteristics.
        
        Risk Factors:
        - Change type (deployment > config > documentation)
        - Affected workflow risk level
        - Production vs. staging environment
        - Data sensitivity (PHI/PII)
        - Blast radius (how many users affected)
        
        Returns:
            LOW, MEDIUM, HIGH, or CRITICAL
        """
        risk_score = 0
        
        # Factor 1: Change type
        type_risk = {
            ChangeType.WORKFLOW_DEPLOYMENT: 3,
            ChangeType.WORKFLOW_MODIFICATION: 3,
            ChangeType.CAPABILITY_ADDITION: 2,
            ChangeType.CONNECTOR_ADDITION: 2,
            ChangeType.POLICY_UPDATE: 3,
            ChangeType.CONFIGURATION_CHANGE: 2,
            ChangeType.DATA_MIGRATION: 3,
            ChangeType.EMERGENCY_FIX: 1,  # Pre-approved, high urgency
        }
        risk_score += type_risk.get(change_type, 1)
        
        # Factor 2: Workflow risk level
        if workflow_id:
            workflow = self.db.query(Workflow).filter(
                Workflow.id == workflow_id
            ).first()
            if workflow:
                workflow_risk = {
                    WorkflowRiskLevel.LOW: 1,
                    WorkflowRiskLevel.MEDIUM: 2,
                    WorkflowRiskLevel.HIGH: 3,
                    WorkflowRiskLevel.CRITICAL: 4
                }
                risk_score += workflow_risk.get(workflow.risk_level, 1)
        
        # Factor 3: Environment
        if change_data and change_data.get('environment') == 'production':
            risk_score += 2
        
        # Factor 4: Data sensitivity
        if change_data and change_data.get('handles_phi_pii'):
            risk_score += 2
        
        # Factor 5: Blast radius
        estimated_users = change_data.get('estimated_affected_users', 0) if change_data else 0
        if estimated_users > 1000:
            risk_score += 2
        elif estimated_users > 100:
            risk_score += 1
        
        # Convert score to risk level
        if risk_score >= 10:
            return ChangeRiskLevel.CRITICAL
        elif risk_score >= 7:
            return ChangeRiskLevel.HIGH
        elif risk_score >= 4:
            return ChangeRiskLevel.MEDIUM
        else:
            return ChangeRiskLevel.LOW
    
    def _route_to_approvers(self, change_request: ChangeRequest):
        """
        Route change request to appropriate approvers based on risk.
        
        Approval Requirements:
        - LOW: Auto-approve (if policy allows)
        - MEDIUM: 1 approver
        - HIGH: 2 approvers
        - CRITICAL: 3 approvers + compliance officer
        """
        # Implementation: Send notifications, create approval records
        pass
    
    def approve_change(
        self,
        change_request_id: str,
        approver_id: str,
        approver_email: str,
        comments: str = None
    ) -> ChangeRequest:
        """
        Approve a change request.
        
        Checks:
        1. Approver has permission to approve this risk level
        2. Approver is not the requester (separation of duties)
        3. Required number of approvals not yet met
        
        Args:
            change_request_id: ID of change request
            approver_id: User ID of approver
            approver_email: Email for audit trail
            comments: Optional approval comments
            
        Returns:
            Updated ChangeRequest
        """
        # Implementation details...
        pass
    
    def execute_change(self, change_request_id: str) -> Dict[str, Any]:
        """
        Execute approved change.
        
        Pre-Execution Checks:
        1. Change is in APPROVED status
        2. All required approvals collected
        3. No kill switches active
        4. Pre-execution enforcement gate passes
        
        Execution:
        1. Run through enforcement gates
        2. Execute change
        3. Verify success
        4. Update audit trail
        5. Notify stakeholders
        
        Post-Execution:
        1. Post-execution enforcement gate
        2. Update change status to COMPLETED
        3. Archive change record
        
        Returns:
            Execution result with audit trail
        """
        # Implementation details...
        pass
    
    def _generate_change_key(self) -> str:
        """Generate unique change key (e.g., CHG-2025-001)."""
        # Format: CHG-YYYY-NNN
        year = datetime.utcnow().year
        # Query for highest change number this year
        # ... implementation
        return f"CHG-{year}-001"  # Placeholder
    
    def _create_audit_event(
        self,
        event_type: str,
        action: str,
        actor_id: str,
        resource_id: str,
        context: Dict[str, Any]
    ):
        """Create audit event in hash-chained log."""
        # Get last event's hash
        last_event = self.db.query(AuditEvent).order_by(
            AuditEvent.created_at.desc()
        ).first()
        
        # Create new event
        event = AuditEvent.create_event(
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type="USER",
            outcome="SUCCESS",
            context=context,
            resource_type="CHANGE_REQUEST",
            resource_id=resource_id,
            previous_hash=last_event.event_hash if last_event else None
        )
        
        self.db.add(event)
        self.db.commit()
```

---

## MICROSOFT ENTRA ID INTEGRATION

```python
# In backend/app/auth/entra.py

from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from msal import ConfidentialClientApplication
import os

class EntraIDService:
    """
    Microsoft Entra ID (Azure AD) authentication service.
    
    OAuth 2.0 Flow:
    1. User clicks "Sign in with Microsoft"
    2. Redirect to Microsoft login
    3. User authenticates
    4. Microsoft redirects back with auth code
    5. Exchange code for access token
    6. Validate token
    7. Create/update user in database
    8. Create session
    
    Configuration:
    - ENTRA_TENANT_ID: Your Azure AD tenant ID
    - ENTRA_CLIENT_ID: Application (client) ID
    - ENTRA_CLIENT_SECRET: Client secret
    - ENTRA_REDIRECT_URI: Callback URL
    """
    
    def __init__(self):
        self.tenant_id = os.getenv("ENTRA_TENANT_ID")
        self.client_id = os.getenv("ENTRA_CLIENT_ID")
        self.client_secret = os.getenv("ENTRA_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ENTRA_REDIRECT_URI")
        
        # Validate configuration
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Entra ID configuration incomplete")
        
        # Create MSAL client
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        # Scopes to request
        self.scopes = [
            "User.Read",  # Read user profile
            "User.ReadBasic.All",  # Read all users' basic profiles
            "GroupMember.Read.All"  # Read group memberships
        ]
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate Microsoft login URL.
        
        Args:
            state: CSRF token (recommended for security)
            
        Returns:
            URL to redirect user to
        """
        auth_url = self.app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state
        )
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from Microsoft
            
        Returns:
            Token response with access_token, refresh_token, etc.
            
        Raises:
            HTTPException: If token exchange fails
        """
        result = self.app.acquire_token_by_authorization_code(
            code=auth_code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token exchange failed: {result.get('error_description')}"
            )
        
        return result
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            New token response
        """
        result = self.app.acquire_token_by_refresh_token(
            refresh_token=refresh_token,
            scopes=self.scopes
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )
        
        return result
    
    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get user profile from Microsoft Graph API.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User profile with email, name, groups, etc.
        """
        import requests
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get user profile
        profile_response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
        
        # Get user's group memberships
        groups_response = requests.get(
            "https://graph.microsoft.com/v1.0/me/memberOf",
            headers=headers
        )
        groups_response.raise_for_status()
        groups = groups_response.json().get("value", [])
        
        return {
            "id": profile.get("id"),
            "email": profile.get("userPrincipalName"),
            "name": profile.get("displayName"),
            "given_name": profile.get("givenName"),
            "family_name": profile.get("surname"),
            "groups": [g.get("displayName") for g in groups]
        }
```

---

## API ENDPOINTS (FastAPI)

```python
# In backend/app/api/routes/change_requests.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.services.change_request import ChangeRequestService
from app.services.auth import get_current_user
from app.schemas.change_request import (
    ChangeRequestCreate,
    ChangeRequestResponse,
    ChangeRequestApprove
)

router = APIRouter(prefix="/change-requests", tags=["Change Requests"])

@router.post("/", response_model=ChangeRequestResponse)
async def create_change_request(
    request: ChangeRequestCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new change request (FLAGSHIP WORKFLOW).
    
    Only authenticated users can create change requests.
    AI agents must act on behalf of a user.
    
    Request Body:
    ```json
    {
        "change_type": "WORKFLOW_DEPLOYMENT",
        "title": "Deploy Invoice Processor to Production",
        "description": "Deploy automated invoice processing workflow",
        "rationale": "Business requirement to reduce manual processing",
        "workflow_id": "uuid-of-workflow",
        "change_data": {
            "environment": "production",
            "handles_phi_pii": false,
            "estimated_affected_users": 50
        }
    }
    ```
    
    Response:
    ```json
    {
        "id": "uuid",
        "change_key": "CHG-2025-001",
        "status": "PENDING",
        "risk_level": "HIGH",
        "required_approvals": 2,
        "approvals_received": 0
    }
    ```
    """
    service = ChangeRequestService()
    
    change_request = service.create_change_request(
        change_type=request.change_type,
        title=request.title,
        description=request.description,
        rationale=request.rationale,
        requested_by=current_user.id,
        requested_by_email=current_user.email,
        workflow_id=request.workflow_id,
        capability_id=request.capability_id,
        connector_id=request.connector_id,
        change_data=request.change_data
    )
    
    return change_request

@router.get("/", response_model=List[ChangeRequestResponse])
async def list_change_requests(
    status: str = None,
    risk_level: str = None,
    current_user = Depends(get_current_user)
):
    """
    List change requests with optional filters.
    
    Query Parameters:
    - status: Filter by status (PENDING, APPROVED, REJECTED, etc.)
    - risk_level: Filter by risk (LOW, MEDIUM, HIGH, CRITICAL)
    
    Returns list of change requests the user has permission to see.
    """
    # Implementation...
    pass

@router.put("/{change_id}/approve", response_model=ChangeRequestResponse)
async def approve_change_request(
    change_id: str,
    approval: ChangeRequestApprove,
    current_user = Depends(get_current_user)
):
    """
    Approve a change request.
    
    Permissions Required:
    - MEDIUM risk: APPROVE_MEDIUM_RISK permission
    - HIGH risk: APPROVE_HIGH_RISK permission
    - CRITICAL risk: APPROVE_CRITICAL_RISK permission
    
    Request Body:
    ```json
    {
        "comments": "Reviewed and approved. Deployment window: Friday 10 PM."
    }
    ```
    """
    service = ChangeRequestService()
    
    # Check if user has permission to approve this risk level
    # ... permission check implementation
    
    change_request = service.approve_change(
        change_request_id=change_id,
        approver_id=current_user.id,
        approver_email=current_user.email,
        comments=approval.comments
    )
    
    return change_request

@router.put("/{change_id}/execute", response_model=Dict[str, Any])
async def execute_change_request(
    change_id: str,
    current_user = Depends(get_current_user)
):
    """
    Execute an approved change request.
    
    Pre-Execution Checks:
    1. Change is in APPROVED status
    2. All required approvals collected
    3. No active kill switches
    4. Enforcement gates pass
    
    Returns execution result with audit trail.
    """
    service = ChangeRequestService()
    
    result = service.execute_change(change_id)
    
    return result
```

---

## NEXT STEPS FOR AGENT

1. **Read this entire document** - Understand architecture before writing code
2. **Set up development environment** - Follow setup in SOUTHERN_SHADE_ONBOARDING.md
3. **Implement in this order**:
   - Phase 1: Database models (DONE)
   - Phase 2: Entra ID integration
   - Phase 3: Enforcement service
   - Phase 4: Change request service
   - Phase 5: API endpoints
   - Phase 6: Frontend components
   - Phase 7: Testing
   - Phase 8: Deployment

4. **Code quality checklist** for every file:
   - [ ] Type hints on all functions
   - [ ] Docstrings on all classes/public methods
   - [ ] Error handling on all external calls
   - [ ] Logging at appropriate levels
   - [ ] Security considerations documented
   - [ ] Performance notes added
   - [ ] Tests written

5. **Security checklist** for every feature:
   - [ ] Input validation
   - [ ] Authentication required
   - [ ] Authorization enforced
   - [ ] Audit trail generated
   - [ ] Kill switch honored
   - [ ] Rate limiting applied
   - [ ] OWASP Top 10 mitigations

---

**This is production software. Write it accordingly.**

## Data Protection & Tokenization

This system assumes PHI/PII is tokenized at the data layer and only minimally detokenized through governed capabilities. See [TOKENIZATION_STRATEGY.md](./TOKENIZATION_STRATEGY.md) for full implementation details.
