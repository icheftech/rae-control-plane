from app.security import admin, Actor
from app.services.audit import append_event
"""Tenants API Router

Provides REST API endpoints for tenant management in the R.A.E. Control Plane.
Tenants are organization directory records in this single installation.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.tenant import Tenant
from pydantic import BaseModel, Field
from datetime import datetime
from app.services.tenancy import tenant_id as current_tenant_id

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
@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin)])
async def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(admin)
):
    """Create a new tenant organization."""
    raise HTTPException(403, 'Tenant provisioning requires an installation administrator outside this API')

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all tenant organizations."""
    tenants = db.query(Tenant).filter(Tenant.id == current_tenant_id(db)).offset(skip).limit(limit).all()
    return tenants

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific tenant by ID."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.id == current_tenant_id(db)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    return tenant

@router.patch("/{tenant_id}", response_model=TenantResponse, dependencies=[Depends(admin)])
async def update_tenant(
    tenant_id: UUID,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(admin)
):
    """Update a tenant organization."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.id == current_tenant_id(db)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )

    update_data = tenant_update.model_dump(exclude_unset=True)
    if 'tenant_key' in update_data:
        raise HTTPException(422, 'Tenant key is immutable')
    for field, value in update_data.items():
        setattr(tenant, field, value)

    append_event(db, actor, "TENANT_UPDATED", tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin)])
async def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    actor: Actor = Depends(admin)
):
    """Delete a tenant organization."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.id == current_tenant_id(db)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )

    append_event(db, actor, "TENANT_DELETED", tenant)
    tenant.is_active = False
    db.commit()
    return None
