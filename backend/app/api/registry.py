"""Registry and control administration for one installation."""
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Workflow, Capability, Connector, ControlPolicy, KillSwitch
from app.security import Actor, current_actor, admin, operator
from app.services.audit import append_event
from app.services.tenancy import scoped, own, require_owned
from app.api.schemas import WorkflowCreate, WorkflowUpdate, CapabilityCreate, ConnectorCreate, PolicyCreate, SwitchCreate, SwitchAction
router = APIRouter(dependencies=[Depends(current_actor)])

def serialize(obj):
    return jsonable_encoder({a.key: getattr(obj, a.key) for a in inspect(type(obj)).column_attrs})

def require(db, model, id):
    return require_owned(db, model, id)

def save(db, actor, obj, action):
    own(db, actor, obj)
    db.add(obj)
    db.flush()
    append_event(db, actor, action, obj)
    db.commit()
    db.refresh(obj)
    return serialize(obj)

def add_reads(path, model):
    def listing(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
        return [serialize(x) for x in db.scalars(scoped(db, model).order_by(model.created_at.desc()).offset(skip).limit(limit))]
    def detail(id: UUID, db: Session = Depends(get_db)):
        return serialize(require(db, model, id))
    router.add_api_route(path, listing, methods=['GET'], name='list_' + model.__tablename__)
    router.add_api_route(path+'/{id}', detail, methods=['GET'], name='get_' + model.__tablename__)

for path, model in [('/workflows/', Workflow),('/capabilities', Capability),('/connectors', Connector),('/control-policies', ControlPolicy),('/kill-switches/', KillSwitch)]:
    add_reads(path.rstrip('/'), model)

@router.post('/workflows', status_code=201)
def create_workflow(data: WorkflowCreate, db: Session=Depends(get_db), actor: Actor=Depends(operator)):
    return save(db, actor, Workflow(**data.model_dump(), workflow_key=str(uuid4()), created_by=actor.name), 'WORKFLOW_CREATED')

@router.put('/workflows/{id}')
def update_workflow(id: UUID, data: WorkflowUpdate, db: Session=Depends(get_db), actor: Actor=Depends(operator)):
    obj = require(db, Workflow, id)
    for k,v in data.model_dump().items(): setattr(obj,k,v)
    return save(db, actor, obj, 'WORKFLOW_UPDATED')

@router.post('/capabilities', status_code=201)
def create_capability(data: CapabilityCreate, db: Session=Depends(get_db), actor: Actor=Depends(operator)):
    require(db, Workflow, data.workflow_id)
    return save(db, actor, Capability(**data.model_dump(), capability_key=str(uuid4()), created_by=actor.name), 'CAPABILITY_CREATED')

@router.post('/connectors', status_code=201)
def create_connector(data: ConnectorCreate, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    require(db, Capability, data.capability_id)
    return save(db, actor, Connector(**data.model_dump(), connector_key=str(uuid4()), created_by=actor.name), 'CONNECTOR_CREATED')

@router.post('/control-policies', status_code=201)
def create_policy(data: PolicyCreate, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    if data.workflow_id: require(db, Workflow, data.workflow_id)
    supported = {'model', 'workflow_id', 'operation'}
    if (set(data.conditions) | set(data.auto_deny_conditions)) - supported:
        raise HTTPException(422, 'Condition keys must be model, workflow_id, or operation')
    return save(db, actor, ControlPolicy(**data.model_dump(), policy_key=str(uuid4()), created_by=actor.name, last_modified_by=actor.name), 'POLICY_CREATED')

@router.post('/kill-switches', status_code=201)
def create_switch(data: SwitchCreate, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    if data.workflow_id: require(db, Workflow, data.workflow_id)
    return save(db, actor, KillSwitch(**data.model_dump(), switch_key=str(uuid4()), is_active=False), 'KILL_SWITCH_CREATED')

@router.post('/kill-switches/{id}/activate')
def activate(id: UUID, data: SwitchAction, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    obj = require(db, KillSwitch, id)
    obj.activate(actor.name, data.reason)
    obj.auto_deactivate_at = None
    return save(db, actor, obj, 'KILL_SWITCH_ACTIVATED')

@router.post('/kill-switches/{id}/deactivate')
def deactivate(id: UUID, data: SwitchAction, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
    obj = require(db, KillSwitch, id)
    obj.deactivate(actor.name, data.reason)
    return save(db, actor, obj, 'KILL_SWITCH_DEACTIVATED')

def add_deactivate(path, model):
    def deactivate_resource(id: UUID, db: Session=Depends(get_db), actor: Actor=Depends(admin)):
        obj = require(db, model, id)
        obj.is_active = False
        save(db, actor, obj, model.__tablename__.upper() + '_DEACTIVATED')
    router.add_api_route(path+'/{id}', deactivate_resource, methods=['DELETE'], status_code=204, name='deactivate_'+model.__tablename__)
for path, model in [('/workflows',Workflow),('/capabilities',Capability),('/connectors',Connector),('/control-policies',ControlPolicy)]:
    add_deactivate(path, model)
