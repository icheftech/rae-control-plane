"""Tenants API Router

Provides REST API endpoints for tenant management in the R.A.E. Control Plane.
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
    tenant_name: str = Field(..., description="Tenant organization name")
    tenant_key: str = Field(..., description="Unique tenant identifier (e.g. 'southern_shade_llc')")
    is_active: bool = Field(default=True, description="Tenant active status")

class TenantCreate(TenantBase):
    created_by: str = Field(..., description="User or service principal creating this tenant")
    description: str | None = None
    primary_contact_email: str | None = None
    billing_email: str | None = None

class TenantUpdate(BaseModel):
    tenant_name: str | None = None
    tenant_key: str | None = None
    is_active: bool | None = None
    description: str | None = None
    primary_contact_email: str | None = None
    billing_email: str | None = None

class TenantResponse(TenantBase):
    id: UUID
    description: str | None
    primary_contact_email: str | None
    billing_email: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# API Endpoints
@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db)
):
    """Create a new tenant organization."""
    existing = db.query(Tenant).filter(Tenant.tenant_key == tenant.tenant_key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with key '{tenant.tenant_key}' already exists"
        )

    db_tenant = Tenant(**tenant.model_dump())
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

    update_data = tenant_update.model_dump(exclude_unset=True)
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
