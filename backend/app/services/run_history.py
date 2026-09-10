"""Durable start/completion records shared by orchestration and direct chat."""
from contextlib import contextmanager
from uuid import uuid4
from fastapi import HTTPException
from app.db.models.orchestration_run import OrchestrationRun, OrchestrationRunEvent, now
from app.services.telemetry import request_id, emit
from app.services.tenancy import require_owned
from app.db.models import Workflow, ExecutionContext
from app.services.evidence import record


def safe_usage(usage):
    return {key: value for key, value in (usage or {}).items()
            if key in ('prompt_tokens', 'completion_tokens', 'total_tokens')
            and type(value) is int and value >= 0}


class RunHistory:
    def __init__(self, db, actor, workflow_id, step_count, source='orchestration', run_id=None):
        self.db = db
        require_owned(db, Workflow, workflow_id)
        self.context = ExecutionContext(id=uuid4(), tenant_id=actor.tenant_id, actor_id=actor.id,
            workflow_id=workflow_id, protected_resource_scope={'workflow_id':str(workflow_id)})
        self.run = OrchestrationRun(id=run_id or uuid4(), workflow_id=workflow_id,
            source=source, request_id=request_id.get() or str(uuid4()), actor_id=actor.id,
            step_count=step_count, tenant_id=actor.tenant_id, context_id=self.context.id)

    def __enter__(self):
        self.db.add(self.context)
        self.db.flush()
        self.db.add(self.run)
        self.db.flush()
        self.db.info['execution'] = {'run_id':self.run.id,'context_id':self.context.id,'actor_id':self.run.actor_id}
        root = record(self.db, 'run_started', 'pending')
        self.db.info['execution']['root'] = root.id
        self.db.commit()
        emit('run_started', run_id=str(self.run.id), workflow_id=str(self.run.workflow_id), tenant_id=str(self.run.tenant_id), context_id=str(self.run.context_id), actor_id=str(self.run.actor_id))
        return self

    def __exit__(self, typ, exc, tb):
        status, reason = outcome(exc)
        self.run.status, self.run.decision_reason = status, reason
        self.run.completed_at = now()
        record(self.db, 'run_completed', status, {'reason':reason} if reason else {})
        self.db.commit()
        emit('run_completed', run_id=str(self.run.id), status=status, decision_reason=reason)
        if isinstance(exc, HTTPException):
            exc.headers = {**(exc.headers or {}), 'X-Run-ID': str(self.run.id)}
        self.db.info.pop('execution', None)
        self.db.info.pop('policy_snapshot_id', None)

    @contextmanager
    def step(self, position, step_id, step_type, model=None):
        self.db.info.pop('policy_snapshot_id', None)
        active = self.db.info['execution']
        active['step_id'] = step_id
        started = record(self.db, 'step_started', 'pending', {'step_type':step_type, 'position':position})
        active['step_event_id'] = started.id
        if step_type == 'set_context':
            record(self.db, 'authorization', 'success', {'rule':'active registered workflow; local context assignment'})
        event = OrchestrationRunEvent(run_id=self.run.id, position=position, tenant_id=self.run.tenant_id,
            step_id=step_id, step_type=step_type, model=model,
            input_ref=f'run:{self.run.id}:step:{position}:input')
        self.db.add(event)
        self.db.commit()
        emit('step_started', run_id=str(self.run.id), step_id=step_id, step_type=step_type)
        try:
            yield event
        except BaseException as exc:
            event.status, event.decision_reason = outcome(exc)
            raise
        else:
            event.status = 'success'
            event.output_ref = f'run:{self.run.id}:step:{position}:output'
        finally:
            event.completed_at = now()
            record(self.db, 'step_completed', event.status, {'reason':event.decision_reason, 'token_usage':event.token_usage},
                   snapshot_id=self.db.info.get('policy_snapshot_id'))
            self.db.commit()
            active.pop('step_event_id', None)
            active.pop('step_id', None)
            emit('step_completed', run_id=str(self.run.id), step_id=step_id,
                 status=event.status, decision_reason=event.decision_reason,
                 model=event.model, token_usage=event.token_usage)


def outcome(exc):
    if exc is None:
        return 'success', None
    if isinstance(exc, HTTPException):
        # These exceptions are raised with fixed, content-free messages internally.
        return ('denied' if exc.status_code == 403 else 'error'), str(exc.detail)[:500]
    return 'error', 'Execution interrupted or failed'
