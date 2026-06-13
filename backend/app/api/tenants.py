"""Tenants API Router

Provides REST API endpoints for tenant management in the S.S.O. Control Plane.
Tenants represent organizational units with isolated data and resources.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.tenant import Tenant
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
)

# Pydantic Schemas
class TenantBase(BaseModel):
    name: str = Field(..., description="Tenant organization name")
    domain: str = Field(..., description="Tenant domain identifier")
    is_active: bool = Field(default=True, description="Tenant active status")

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    is_active: bool | None = None

class TenantResponse(TenantBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True

# API Endpoints
@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db)
):
    """Create a new tenant organization."""
    # Check if domain already exists
    existing = db.query(Tenant).filter(Tenant.domain == tenant.domain).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with domain '{tenant.domain}' already exists"
        )
    
    db_tenant = Tenant(**tenant.dict())
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all tenant organizations."""
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific tenant by ID."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    return tenant

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db)
):
    """Update a tenant organization."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    update_data = tenant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    return tenant

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a tenant organization."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    db.delete(tenant)
    db.commit()
    return None
