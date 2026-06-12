"""Control Policies API Router

Provides REST endpoints for managing control policies - the governance
Add Phase 4: Control Policies API router - Governance rule engine
NIST AI RMF Mapping:
- GOVERN-1.2: Organizational governance structures
- GOVERN-4.1: AI system operation constraints
- MANAGE-2.1: Risk-based decision making

Compliance:
- SOC 2 CC3.1: Policy definition and enfoComplete control policies REST API for governance rule management.

Features:
- List policies with outcome filtering (ALLOW/DENY/REVIEW)
- Create policies with condition-based evaluation
- Priority ordering (lower number = higher priority)
- Update policy configuration
- Soft-delete (deactivate) policies

Schemas:
- ControlPolicyBase: Core policy fields with outcomes
- ControlPolicyCreate: Validation for new policies
- ControlPolicyUpdate: Optional fields for updates
- ControlPolicyResponse: API response format

Governance Outcomes:
- ALLOW: Operation proceeds without restriction
- DENY: Operation is blocked
- REVIEW: Operation requires human approval

NIST AI RMF: GOVERN-1.2, GOVERN-4.1, MANAGE-2.1
Compliance: SOC 2 CC3.1, ISO 27001rcement
- ISO 27001: Security policy management
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models.control_policy import ControlPolicy, PolicyAction as PolicyOutcome
from pydantic import BaseModel, Field


router = APIRouter(tags=["control-policies"])


class ControlPolicyBase(BaseModel):
    """Base control policy schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    outcome: PolicyOutcome
    conditions: dict = Field(..., description="JSON conditions for policy evaluation")
    priority: int = Field(default=100, ge=0, le=1000)
    metadata: dict = Field(default_factory=dict)


class ControlPolicyCreate(ControlPolicyBase):
    """Schema for creating control policies."""
    pass


class ControlPolicyUpdate(BaseModel):
    """Schema for updating control policies."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    outcome: Optional[PolicyOutcome] = None
    conditions: Optional[dict] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    metadata: Optional[dict] = None


class ControlPolicyResponse(ControlPolicyBase):
    """Schema for control policy responses."""
    id: UUID
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/control-policies", response_model=List[ControlPolicyResponse])
async def list_control_policies(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    outcome: Optional[PolicyOutcome] = None,
    search: Optional[str] = None,
    is_active: bool = True,
):
    """
    List all control policies with filtering.
    
    Policies are evaluated in priority order (lower number = higher priority).
    
    Query Parameters:
    - skip: Pagination offset
    - limit: Maximum records to return
    - outcome: Filter by ALLOW/DENY/REVIEW
    - search: Search in name/description
    - is_active: Include only active policies
    """
    query = select(ControlPolicy).where(ControlPolicy.is_active == is_active)
    
    if outcome:
        query = query.where(ControlPolicy.outcome == outcome)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                ControlPolicy.name.ilike(search_pattern),
                ControlPolicy.description.ilike(search_pattern),
            )
        )
    
    # Order by priority (lower = higher priority)
    query = query.order_by(ControlPolicy.priority.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    policies = result.scalars().all()
    
    return policies


@router.post("/control-policies", response_model=ControlPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_control_policy(
    policy_data: ControlPolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new control policy.
    
    Policies define governance rules:
    - ALLOW: Operation proceeds without restriction
    - DENY: Operation is blocked
    - REVIEW: Operation requires human approval
    
    Conditions are evaluated against operation context.
    """
    # Check duplicate name
    existing = await db.execute(
        select(ControlPolicy).where(
            ControlPolicy.name == policy_data.name,
            ControlPolicy.is_active == True,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Control policy '{policy_data.name}' already exists",
        )
    
    policy = ControlPolicy(**policy_data.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    
    return policy


@router.get("/control-policies/{policy_id}", response_model=ControlPolicyResponse)
async def get_control_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve specific control policy details."""
    result = await db.execute(
        select(ControlPolicy).where(ControlPolicy.id == policy_id)
    )
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Control policy {policy_id} not found",
        )
    
    return policy


@router.put("/control-policies/{policy_id}", response_model=ControlPolicyResponse)
async def update_control_policy(
    policy_id: UUID,
    policy_data: ControlPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update control policy configuration.
    
    CAUTION: Changing policy outcomes or conditions affects
    all operations evaluated against this policy.
    """
    result = await db.execute(
        select(ControlPolicy).where(ControlPolicy.id == policy_id)
    )
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Control policy {policy_id} not found",
        )
    
    update_data = policy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    
    await db.commit()
    await db.refresh(policy)
    
    return policy


@router.delete("/control-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_control_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a control policy (soft delete).
    
    Deactivated policies are no longer evaluated during
    enforcement gate checks.
    
    CRITICAL: Test impact before deactivating production policies.
    """
    result = await db.execute(
        select(ControlPolicy).where(ControlPolicy.id == policy_id)
    )
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Control policy {policy_id} not found",
        )
    
    policy.is_active = False
    await db.commit()
    
    return None
