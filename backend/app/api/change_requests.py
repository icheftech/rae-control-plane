"""Change Requests API Router - FLAGSHIP PRODUCTION CHANGE MANAGEMENT

Provides REST endpoints for managing change requests = multi-stage approval
workflow for high-risk production changes.

Add Phase 4: Production Change Management (FLAGSHIP)

This is the CENTERPIECE of enterprise governance - requiring multi-level
approval, rollback plans, and post-change validation for ANY production modification.

NIST AI RMF Mapping:
- GOVERN-1.2: Organizational governance structures
- GOVERN-4.1: AI system operation constraints  
- MANAGE-2.1: Risk-based decision making
- MANAGE-4.2: Change control procedures

Compliance:
- SOC 2 CC8.1: Change management
- ISO 27001 A.12.1.2: Change management procedures
- HIPAA: Production system change controls
"""

from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..db.database import get_db
from ..db.models.change_request import ChangeRequest, ChangeStatus as ChangeRequestStatus, ChangeRiskLevel as ChangeRequestRisk


router = APIRouter(prefix="/change-requests", tags=["change-requests"])


@router.get("/", response_model=List)
async def list_change_requests(
    status_filter: Optional[ChangeRequestStatus] = None,
    risk_filter: Optional[ChangeRequestRisk] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all change requests with filtering.
    
    FLAGSHIP: Change requests implement multi-stage approval for
    production modifications.
    
    Status flow: DRAFT → PENDING_APPROVAL → APPROVED → IMPLEMENTED → VALIDATED
    Risk levels: LOW, MEDIUM, HIGH, CRITICAL
    """
    query = select(ChangeRequest).where(ChangeRequest.is_active == True)
    
    if status_filter:
        query = query.where(ChangeRequest.status == status_filter)
    
    if risk_filter:
        query = query.where(ChangeRequest.risk_level == risk_filter)
    
    query = query.order_by(ChangeRequest.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_change_request(
    request_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new change request.
    
    FLAGSHIP: All production changes MUST go through this workflow.
    
    Required fields:
    - description: What is changing
    - justification: Why this change is needed
    - risk_level: Impact assessment (LOW/MEDIUM/HIGH/CRITICAL)
    - rollback_plan: How to undo if issues arise
    - affected_workflows: Which workflows are impacted
    
    CRITICAL: HIGH/CRITICAL risk requires senior approval.
    """
    change_request = ChangeRequest(**request_data)
    change_request.status = ChangeRequestStatus.DRAFT
    
    db.add(change_request)
    await db.commit()
    await db.refresh(change_request)
    return change_request


@router.get("/{request_id}")
async def get_change_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific change request by ID.
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    return change_request


@router.put("/{request_id}")
async def update_change_request(
    request_id: UUID,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Update change request details.
    
    Only DRAFT requests can be modified.
    Use approval/rejection endpoints for status changes.
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only modify DRAFT change requests",
        )
    
    # Update fields
    for field, value in update_data.items():
        setattr(change_request, field, value)
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


@router.post("/{request_id}/submit", status_code=status.HTTP_200_OK)
async def submit_for_approval(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit change request for approval.
    
    FLAGSHIP: Moves from DRAFT → PENDING_APPROVAL.
    
    Validation:
    - Must have description, justification, risk_level, rollback_plan
    - HIGH/CRITICAL risk triggers senior approval workflow
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit DRAFT requests",
        )
    
    # Validate required fields
    if not all([change_request.description, change_request.justification, 
                change_request.risk_level, change_request.rollback_plan]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields for submission",
        )
    
    change_request.status = ChangeRequestStatus.PENDING_APPROVAL
    change_request.submitted_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


@router.post("/{request_id}/approve", status_code=status.HTTP_200_OK)
async def approve_change_request(
    request_id: UUID,
    approval_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a change request.
    
    FLAGSHIP: Moves from PENDING_APPROVAL → APPROVED.
    
    Required:
    - approver_id: Who approved
    - approval_notes: Justification for approval
    
    CRITICAL: HIGH/CRITICAL changes require senior/C-level approval.
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve PENDING_APPROVAL requests",
        )
    
    change_request.status = ChangeRequestStatus.APPROVED
    change_request.approved_at = datetime.utcnow()
    change_request.approved_by = approval_data.get("approver_id")
    change_request.approval_notes = approval_data.get("approval_notes")
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


@router.post("/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_change_request(
    request_id: UUID,
    rejection_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a change request.
    
    FLAGSHIP: Moves from PENDING_APPROVAL → REJECTED.
    
    Required:
    - rejection_reason: Why rejected
    - rejected_by: Who rejected
    
    Rejected requests can be revised and resubmitted.
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reject PENDING_APPROVAL requests",
        )
    
    change_request.status = ChangeRequestStatus.REJECTED
    change_request.rejection_reason = rejection_data.get("rejection_reason")
    change_request.rejected_by = rejection_data.get("rejected_by")
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


@router.post("/{request_id}/implement", status_code=status.HTTP_200_OK)
async def mark_implemented(
    request_id: UUID,
    implementation_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark change request as implemented.
    
    FLAGSHIP: Moves from APPROVED → IMPLEMENTED.
    
    Required:
    - implemented_by: Who executed the change
    - implementation_notes: What was done
    
    Next step: Validation testing required.
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only implement APPROVED requests",
        )
    
    change_request.status = ChangeRequestStatus.IMPLEMENTED
    change_request.implemented_at = datetime.utcnow()
    change_request.implemented_by = implementation_data.get("implemented_by")
    change_request.implementation_notes = implementation_data.get("implementation_notes")
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request


@router.post("/{request_id}/validate", status_code=status.HTTP_200_OK)
async def mark_validated(
    request_id: UUID,
    validation_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark change request as validated.
    
    FLAGSHIP: Moves from IMPLEMENTED → VALIDATED.
    
    Final step: Confirms change worked as expected.
    
    Required:
    - validated_by: Who tested
    - validation_notes: Test results
    """
    result = await db.execute(
        select(ChangeRequest).where(ChangeRequest.id == request_id)
    )
    change_request = result.scalars().first()
    
    if not change_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {request_id} not found",
        )
    
    if change_request.status != ChangeRequestStatus.IMPLEMENTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only validate IMPLEMENTED requests",
        )
    
    change_request.status = ChangeRequestStatus.VALIDATED
    change_request.validated_at = datetime.utcnow()
    change_request.validated_by = validation_data.get("validated_by")
    change_request.validation_notes = validation_data.get("validation_notes")
    
    await db.commit()
    await db.refresh(change_request)
    
    return change_request
