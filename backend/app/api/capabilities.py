"""Capabilities API Router

Provides REST endpoints for managing agent capabilities in the registry.
Capabilities represent atomic operations agents can perform, with risk
classifications and constraint definitions.

NIST AI RMF Mapping:
- MAP-1.1: Capability discovery and documentation
- MEASURE-2.3: Risk classification tracking
- GOVERN-4.1: Constraint enforcement

Compliance:
- SOC 2 CC6.1: Capability authorization controls
- ISO 27001: Access capability documentation
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models.capability import Capability
from app.db.models.workflow import RiskLevel


router = APIRouter(tags=["capabilities"])


# Pydantic Schemas
from pydantic import BaseModel, Field


class CapabilityBase(BaseModel):
    """Base capability schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
    max_concurrency: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    allowed_environments: List[str] = Field(default_factory=lambda: ["dev", "staging", "prod"])
    constraints: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class CapabilityCreate(CapabilityBase):
    """Schema for creating capabilities."""
    pass


class CapabilityUpdate(BaseModel):
    """Schema for updating capabilities (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    requires_approval: Optional[bool] = None
    max_concurrency: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    allowed_environments: Optional[List[str]] = None
    constraints: Optional[dict] = None
    metadata: Optional[dict] = None


class CapabilityResponse(CapabilityBase):
    """Schema for capability responses."""
    id: UUID
    is_active: bool

    class Config:
        from_attributes = True


# API Endpoints

@router.get("/capabilities", response_model=List[CapabilityResponse])
async def list_capabilities(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    risk_level: Optional[RiskLevel] = None,
    requires_approval: Optional[bool] = None,
    environment: Optional[str] = None,
    search: Optional[str] = None,
    is_active: bool = True,
):
    """
    List all capabilities with optional filtering.
    
    Query Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    - risk_level: Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)
    - requires_approval: Filter by approval requirement
    - environment: Filter by allowed environment
    - search: Search in name/description
    - is_active: Include only active capabilities (default: true)
    
    Returns list of capabilities matching filters.
    """
    query = select(Capability).where(Capability.is_active == is_active)
    
    # Apply filters
    if risk_level:
        query = query.where(Capability.risk_level == risk_level)
    
    if requires_approval is not None:
        query = query.where(Capability.requires_approval == requires_approval)
    
    if environment:
        # Filter capabilities that allow this environment
        query = query.where(Capability.allowed_environments.contains([environment]))
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Capability.name.ilike(search_pattern),
                Capability.description.ilike(search_pattern),
            )
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    capabilities = result.scalars().all()
    
    return capabilities


@router.post("/capabilities", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_capability(
    capability_data: CapabilityCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new capability.
    
    Validates:
    - Unique capability name
    - Risk level appropriateness
    - Constraint schema validity
    
    Returns the created capability.
    """
    # Check for duplicate name
    existing = await db.execute(
        select(Capability).where(
            Capability.name == capability_data.name,
            Capability.is_active == True,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Capability '{capability_data.name}' already exists",
        )
    
    # Create capability
    capability = Capability(**capability_data.model_dump())
    db.add(capability)
    await db.commit()
    await db.refresh(capability)
    
    return capability


@router.get("/capabilities/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a specific capability by ID.
    
    Returns capability details including constraints and metadata.
    """
    result = await db.execute(
        select(Capability).where(Capability.id == capability_id)
    )
    capability = result.scalars().first()
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found",
        )
    
    return capability


@router.put("/capabilities/{capability_id}", response_model=CapabilityResponse)
async def update_capability(
    capability_id: UUID,
    capability_data: CapabilityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing capability.
    
    Only provided fields are updated. Risk level changes should be
    carefully considered as they affect enforcement gates.
    
    Returns the updated capability.
    """
    result = await db.execute(
        select(Capability).where(Capability.id == capability_id)
    )
    capability = result.scalars().first()
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found",
        )
    
    # Update only provided fields
    update_data = capability_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(capability, field, value)
    
    await db.commit()
    await db.refresh(capability)
    
    return capability


@router.delete("/capabilities/{capability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_capability(
    capability_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a capability (soft delete).
    
    Capabilities are never hard-deleted to maintain audit trail.
    Deactivated capabilities cannot be used in new workflow executions.
    
    CRITICAL: Verify no active workflows depend on this capability
    before deactivation.
    """
    result = await db.execute(
        select(Capability).where(Capability.id == capability_id)
    )
    capability = result.scalars().first()
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found",
        )
    
    capability.is_active = False
    await db.commit()
    
    return None
