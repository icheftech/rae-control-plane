"""Explicit tenant scope for application resource access."""
from sqlalchemy import select
from fastapi import HTTPException

DEFAULT_TENANT_KEY = 'southern_shade_technologies'


def tenant_id(db):
    value = db.info.get('tenant_id')
    if value is None:
        raise HTTPException(503, 'Tenant identity is required')
    return value


def scoped(db, model):
    return select(model).where(model.tenant_id == tenant_id(db))


def require_owned(db, model, resource_id):
    value = db.scalar(scoped(db, model).where(model.id == resource_id))
    if value is None:
        raise HTTPException(404, 'Resource not found')
    return value


def own(db, actor, obj):
    if actor.tenant_id != tenant_id(db):
        raise HTTPException(403, 'Tenant identity mismatch')
    if getattr(obj, 'tenant_id', None) not in (None, actor.tenant_id):
        raise HTTPException(404, 'Resource not found')
    obj.tenant_id = actor.tenant_id
    return obj
