"""Capture the exact decision inputs and append causal event records."""
import hashlib
import json
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import JSONB
from app.db.models import ExecutionEvent, PolicySnapshot, Workflow, ControlPolicy, KillSwitch
from app.services.tenancy import scoped, require_owned, tenant_id


def record(db, event_type, state, details=None, snapshot_id=None, step_id=None, parent=None, cause=None):
    active = db.info.get('execution')
    if not active:
        raise RuntimeError('Execution identity is required')
    event = ExecutionEvent(tenant_id=tenant_id(db), run_id=active['run_id'],
        context_id=active['context_id'], actor_id=active['actor_id'],
        event_type=event_type, state=state, details=details or {},
        step_id=step_id if step_id is not None else active.get('step_id'),
        parent_event_id=parent or active.get('step_event_id') or active.get('root'),
        caused_by_event_id=cause or active.get('last'), policy_snapshot_id=snapshot_id)
    db.add(event)
    db.flush()
    active['last'] = event.id
    return event


def capture(db, workflow_id, model):
    workflow = require_owned(db, Workflow, workflow_id)
    # One SQL statement obtains all decision inputs under one MVCC snapshot.
    from sqlalchemy import select, func, literal
    def rows(model_class):
        table = model_class.__table__
        return select(func.coalesce(func.jsonb_agg(table.table_valued()), literal('[]').cast(JSONB))).where(
            table.c.tenant_id == tenant_id(db), table.c.is_active == True,
            or_(table.c.workflow_id == None, table.c.workflow_id == workflow_id)).scalar_subquery()
    workflow_active, policy_rows, stop_rows = db.execute(select(Workflow.is_active, rows(ControlPolicy), rows(KillSwitch)).where(
        Workflow.id == workflow_id, Workflow.tenant_id == tenant_id(db))).one()
    content = {'schema_version':1, 'evaluator_version':'exact-match-v1',
        'workflow_id':str(workflow.id), 'workflow_active':workflow_active,
        'request':{'model':model, 'workflow_id':str(workflow.id), 'operation':'chat_completion'},
        'policies':[{'id':p['id'], 'action':p['policy_action'].lower(), 'priority':p['priority'],
                     'conditions':p['conditions'] or {}, 'auto_deny_conditions':p['auto_deny_conditions'] or {}}
                    for p in sorted(policy_rows, key=lambda p:(-p['priority'],p['id']))],
        'stops':[{'id':s['id'], 'mode':s['mode']} for s in sorted(stop_rows,key=lambda s:s['id'])]}
    snapshot = PolicySnapshot(tenant_id=tenant_id(db), context_id=db.info['execution']['context_id'],
        content=content, content_hash=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    db.add(snapshot)
    db.flush()
    return snapshot


def evaluate_snapshot(content):
    if content['stops']:
        return False, 'Emergency stop is active: '+content['stops'][0]['id']
    if not content['workflow_active']:
        return False, 'Workflow is missing or inactive'
    allowed = False
    context = content['request']
    for policy in content['policies']:
        if any(k in context and context[k] == v for k,v in policy['auto_deny_conditions'].items()):
            return False, 'Automatic deny condition matched: policy '+policy['id']
        if not all(k in context and context[k] == v for k,v in policy['conditions'].items()):
            continue
        if policy['action'] != 'allow':
            return False, 'Policy denies execution or requires review: '+policy['id']
        allowed = True
    return (True,'Allowed by policy') if allowed else (False,'No matching allow policy')
