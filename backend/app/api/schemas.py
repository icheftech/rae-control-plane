"""Request contracts match the existing database schema; reject unknown fields."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.workflow import RiskLevel
from app.db.models.connector import ConnectorType
from app.db.models.control_policy import PolicyAction
from app.db.models.kill_switch import KillSwitchMode, KillSwitchTrigger

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')
class WorkflowCreate(Strict):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(default='1.0.0', min_length=1, max_length=50)
    description: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
class WorkflowUpdate(Strict):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
class CapabilityCreate(Strict):
    name: str = Field(min_length=1, max_length=255)
    workflow_id: UUID
    description: Optional[str] = None
class ConnectorCreate(Strict):
    name: str = Field(min_length=1, max_length=255)
    capability_id: UUID
    connector_type: ConnectorType
    endpoint_url: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = None
    config: dict = Field(default_factory=dict, description='Non-secret configuration only. Use secret references.')
class PolicyCreate(Strict):
    name: str = Field(min_length=1, max_length=255)
    workflow_id: Optional[UUID] = None
    description: Optional[str] = None
    policy_action: PolicyAction
    conditions: dict = Field(default_factory=dict)
    auto_deny_conditions: dict = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=1000)
class SwitchCreate(Strict):
    name: str = Field(min_length=1, max_length=255)
    workflow_id: Optional[UUID] = None
    mode: KillSwitchMode = KillSwitchMode.HARD_STOP
    trigger: KillSwitchTrigger = KillSwitchTrigger.MANUAL
    reason: str = Field(min_length=1)
class SwitchAction(Strict):
    reason: str = Field(min_length=1)
