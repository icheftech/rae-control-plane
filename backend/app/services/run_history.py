"""Durable start/completion records shared by orchestration and direct chat."""
from contextlib import contextmanager
from uuid import uuid4
from fastapi import HTTPException
from app.db.models.orchestration_run import OrchestrationRun, OrchestrationRunEvent, now
from app.services.telemetry import request_id, emit


def safe_usage(usage):
    return {key: value for key, value in (usage or {}).items()
            if key in ('prompt_tokens', 'completion_tokens', 'total_tokens')
            and type(value) is int and value >= 0}


class RunHistory:
    def __init__(self, db, actor, workflow_id, step_count, source='orchestration', run_id=None):
        self.db = db
        self.run = OrchestrationRun(id=run_id or uuid4(), workflow_id=workflow_id,
            source=source, request_id=request_id.get() or str(uuid4()), actor_id=actor.id,
            step_count=step_count)

    def __enter__(self):
        self.db.add(self.run)
        self.db.commit()
        emit('run_started', run_id=str(self.run.id), workflow_id=str(self.run.workflow_id))
        return self

    def __exit__(self, typ, exc, tb):
        status, reason = outcome(exc)
        self.run.status, self.run.decision_reason = status, reason
        self.run.completed_at = now()
        self.db.commit()
        emit('run_completed', run_id=str(self.run.id), status=status, decision_reason=reason)
        if isinstance(exc, HTTPException):
            exc.headers = {**(exc.headers or {}), 'X-Run-ID': str(self.run.id)}

    @contextmanager
    def step(self, position, step_id, step_type, model=None):
        event = OrchestrationRunEvent(run_id=self.run.id, position=position,
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
            self.db.commit()
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
