"""Serialized, transaction-bound audit appends. No prompt or credential content."""
from datetime import datetime
from sqlalchemy import select, text
from app.db.models.audit_event import AuditEvent
from app.services.telemetry import request_id

def append_event(db, actor, action, resource=None, outcome='SUCCESS', context=None):
    # Serialize writers across API workers; the lock is released at transaction end.
    db.execute(text('SELECT pg_advisory_xact_lock(72401391)'))
    previous = db.execute(select(AuditEvent).order_by(AuditEvent.sequence_number.desc()).limit(1)).scalar_one_or_none()
    event = AuditEvent(
        sequence_number=previous.sequence_number + 1 if previous else 1,
        previous_hash=previous.event_hash if previous else None,
        event_type=action, action=action, actor_id=actor.id, actor_type='USER' if actor.subject else 'API_KEY',
        resource_type=resource.__tablename__ if resource is not None else 'llm',
        resource_id=resource.id if resource is not None else None,
        context={**(context or {}), **({'request_id':request_id.get()} if request_id.get() else {})}, outcome=outcome, created_at=datetime.utcnow(), extra_metadata={},
    )
    event.event_hash = event.compute_hash()
    db.add(event)
    db.flush()
    return event
