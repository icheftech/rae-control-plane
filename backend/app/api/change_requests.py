"""Reviewed change tracking. Execution is recorded, never performed by this API."""
from datetime import datetime
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.schemas import Strict
from app.api.registry import serialize, require, save
from app.db.database import get_db
from app.db.models import ChangeRequest, Workflow
from app.services.tenancy import scoped
from app.db.models.change_request import ChangeType, ChangeRiskLevel, ChangeStatus
from app.security import Actor, current_actor, operator, admin
router = APIRouter(prefix='/change-requests', dependencies=[Depends(current_actor)])
class Create(Strict):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    change_type: ChangeType = ChangeType.CONFIG_CHANGE
    risk_level: ChangeRiskLevel = ChangeRiskLevel.MEDIUM
    workflow_id: UUID | None = None
    rollback_procedure: dict = Field(default_factory=dict)
class Decision(Strict):
    notes: str = Field(min_length=1)
@router.get('')
def listing(db: Session=Depends(get_db)):
    return [serialize(x) for x in db.scalars(scoped(db, ChangeRequest).order_by(ChangeRequest.created_at.desc()).limit(100))]
@router.post('', status_code=201)
def create(data: Create, db: Session=Depends(get_db), actor: Actor=Depends(operator)):
    if data.workflow_id:
        require(db, Workflow, data.workflow_id)
    obj=ChangeRequest(**data.model_dump(),change_key='CHG-'+str(uuid4()),requested_by=actor.id,requested_by_email=actor.name,status=ChangeStatus.DRAFT)
    return save(db,actor,obj,'CHANGE_CREATED')
@router.post('/{id}/submit')
def submit(id: UUID, db: Session=Depends(get_db), actor: Actor=Depends(operator)):
    obj=require(db,ChangeRequest,id)
    if obj.status != ChangeStatus.DRAFT: raise HTTPException(409,'Only drafts can be submitted')
    if not obj.rollback_procedure: raise HTTPException(422,'A rollback procedure is required')
    obj.status=ChangeStatus.UNDER_REVIEW
    return save(db,actor,obj,'CHANGE_SUBMITTED')
@router.post('/{id}/review')
def review(id: UUID, data: Decision, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    obj=db.scalar(scoped(db, ChangeRequest).where(ChangeRequest.id==id).with_for_update())
    if not obj: raise HTTPException(404,'Resource not found')
    if obj.status != ChangeStatus.UNDER_REVIEW: raise HTTPException(409,'Request is not under review')
    if obj.requested_by in (actor.id,actor.legacy_id): raise HTTPException(403,'Requester cannot review their own change')
    obj.reviewer_id=actor.id; obj.review_notes=data.notes; obj.reviewed_at=datetime.utcnow(); obj.status=ChangeStatus.PENDING_APPROVAL
    return save(db,actor,obj,'CHANGE_REVIEWED')
@router.post('/{id}/approve')
def approve(id: UUID, data: Decision, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    obj=db.scalar(scoped(db, ChangeRequest).where(ChangeRequest.id==id).with_for_update())
    if not obj: raise HTTPException(404,'Resource not found')
    if obj.status != ChangeStatus.PENDING_APPROVAL: raise HTTPException(409,'Review is required before approval')
    if any(identity in (obj.requested_by,obj.reviewer_id) for identity in (actor.id,actor.legacy_id)): raise HTTPException(403,'Approval requires a separate administrator')
    obj.approver_id=actor.id; obj.approval_notes=data.notes; obj.approved_at=datetime.utcnow(); obj.status=ChangeStatus.APPROVED
    return save(db,actor,obj,'CHANGE_APPROVED')
@router.post('/{id}/reject')
def reject(id: UUID, data: Decision, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    obj=require(db,ChangeRequest,id)
    if obj.status not in (ChangeStatus.UNDER_REVIEW,ChangeStatus.PENDING_APPROVAL): raise HTTPException(409,'Request is not awaiting a decision')
    obj.status=ChangeStatus.REJECTED; obj.rejection_reason=data.notes; obj.rejected_by=actor.id; obj.rejected_at=datetime.utcnow()
    return save(db,actor,obj,'CHANGE_REJECTED')
