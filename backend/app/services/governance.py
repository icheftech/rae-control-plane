"""Conservative preflight governance for LLM calls."""
from sqlalchemy import select, or_
from app.db.models import Workflow, ControlPolicy, KillSwitch
from app.db.models.control_policy import PolicyAction

def evaluate(db, workflow_id, model):
    switches = db.scalars(select(KillSwitch).where(KillSwitch.is_active == True, or_(KillSwitch.workflow_id == None, KillSwitch.workflow_id == workflow_id))).all()
    # All stop modes block new model calls; no inferred degraded operation is safe.
    if switches: return False, 'Emergency stop is active'
    workflow = db.get(Workflow, workflow_id)
    if workflow is None or not workflow.is_active: return False, 'Workflow is missing or inactive'
    context = {'model': model, 'workflow_id': str(workflow_id), 'operation': 'chat_completion'}
    policies = db.scalars(select(ControlPolicy).where(ControlPolicy.is_active == True, or_(ControlPolicy.workflow_id == None, ControlPolicy.workflow_id == workflow_id)).order_by(ControlPolicy.priority.desc())).all()
    allowed = False
    for policy in policies:
        if any(k in context and context[k] == v for k,v in (policy.auto_deny_conditions or {}).items()):
            return False, 'Automatic deny condition matched'
        if not all(k in context and context[k] == v for k,v in (policy.conditions or {}).items()): continue
        if policy.policy_action != PolicyAction.ALLOW:
            return False, 'Policy denies execution or requires review'
        allowed = True
    return (True, 'Allowed by policy') if allowed else (False, 'No matching allow policy')
