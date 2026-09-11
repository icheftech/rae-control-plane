"""R.A.E. Control Plane - Database Models Package

This package contains all SQLAlchemy ORM models for the control plane.

Phase 1: Registry Backbone (MAP)
- Workflow: AI agent workflows/tasks
- Capability: Granular permissions for agents
- Connector: External system integrations

Phase 2: Controls (MANAGE)
- ControlPolicy: Governance policies
- KillSwitch: Emergency stop mechanisms
- BreakGlass: Emergency access procedures

Phase 3: Enforcement Integration
- AuditEvent: Immutable audit log with hash chaining
- EnforcementGate: Policy evaluation checkpoints
- GateExecution: Gate execution history
- ChangeRequest: Governed production change workflow (FLAGSHIP)

Usage:
    from app.db.models import Workflow, Capability, ControlPolicy
    from app.db.models import KillSwitch, BreakGlass, ChangeRequest
    from app.db.models import AuditEvent, EnforcementGate
"""

# Base class for all models
from app.db.base import Base
from .orchestration_run import OrchestrationRun, OrchestrationRunEvent
from .browser_session import BrowserSession
from .local_job import LocalJob, LocalWorker
from .execution_evidence import ExecutionContext, PolicySnapshot, ExecutionEvent

# Phase 1: Registry Backbone (MAP)
from .workflow import Workflow, WorkflowStatus, RiskLevel as WorkflowRiskLevel
from .capability import Capability
from .connector import Connector, ConnectorType

# Phase 2: Controls (MANAGE)
from .control_policy import (
    ControlPolicy,
    PolicyAction,
    ApprovalType,
)
from .kill_switch import (
    KillSwitch,
    KillSwitchMode,
    KillSwitchTrigger,
)
from .break_glass import (
    BreakGlass,
    BreakGlassReason,
    BreakGlassStatus
)

# Phase 3: Enforcement Integration
from .audit_event import AuditEvent
from .enforcement_gate import (
    EnforcementGate,
    GateExecution,
    GateType,
    GateOutcome
)
from .change_request import (
    ChangeRequest,
    ChangeType,
    ChangeStatus,
    ChangeRiskLevel
)

# Export all models and enums
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

# Every resource served by the control plane has explicit organization ownership.
# Historical audit hashes are preserved: tenant ownership is an additional column.
for _owned_model in (Capability, Connector, ControlPolicy, KillSwitch,
                     BreakGlass, AuditEvent, EnforcementGate, GateExecution,
                     ChangeRequest, OrchestrationRun, OrchestrationRunEvent):
    _owned_model.tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

__all__ = [
    # Base
    "Base",
    
    # Phase 1: Registry
    "Workflow",
    "WorkflowStatus",
    "WorkflowRiskLevel",
    "Capability",
    "Connector",
    "ConnectorType",

    # Phase 2: Controls
    "ControlPolicy",
    "PolicyAction",
    "ApprovalType",
    "KillSwitch",
    "KillSwitchMode",
    "KillSwitchTrigger",
    "BreakGlass",
    "BreakGlassReason",
    "BreakGlassStatus",
    
    # Phase 3: Enforcement
    "AuditEvent",
    "EnforcementGate",
    "GateExecution",
    "GateType",
    "GateOutcome",
    "ChangeRequest",
    "ChangeType",
    "ChangeStatus",
    "ChangeRiskLevel",
]

# Version info
__version__ = "0.1.0"
__author__ = "Southern Shade Technologies (SST)"
__description__ = "R.A.E. Control Plane - Enterprise AI Governance Platform"
