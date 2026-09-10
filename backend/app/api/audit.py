from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.security import current_actor
from app.db.database import get_db
from app.db.models import AuditEvent
from app.services.tenancy import scoped, tenant_id
router = APIRouter(prefix='/audit-events', dependencies=[Depends(current_actor)])
@router.get('')
def events(limit: int=Query(100, ge=1, le=500), db: Session=Depends(get_db)):
    return [e.to_dict() for e in db.scalars(scoped(db, AuditEvent).order_by(AuditEvent.sequence_number.desc()).limit(limit))]
@router.get('/verify')
def verify(db: Session=Depends(get_db)):
    previous = None
    count = 0
    for event in db.scalars(select(AuditEvent).order_by(AuditEvent.sequence_number)):
        if not event.verify_chain(previous):
            return {'valid':False, 'verified_count':count}
        previous = event
        if event.tenant_id == tenant_id(db):
            count += 1
    return {'valid':True, 'verified_count':count}
