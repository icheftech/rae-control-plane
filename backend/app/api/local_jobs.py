"""Authenticated metadata-only local queue API."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert
from app.db.database import get_db
from app.db.models import LocalJob, LocalWorker, Workflow
from app.db.models.orchestration_run import now
from app.security import current_actor, operator
from app.services.tenancy import scoped, require_owned
from app.services.local_tasks import load_task
from app.api.orchestrations import serialize
from app.services.audit import append_event

router = APIRouter(prefix='/api/local-jobs', tags=['local-worker'])


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workflow_id: UUID
    task_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    idempotency_key: UUID


@router.post('', status_code=202)
def submit(body: Submission, actor=Depends(operator), db=Depends(get_db)):
    workflow = require_owned(db, Workflow, body.workflow_id)
    if not workflow.is_active:
        raise HTTPException(409, 'Workflow is inactive')
    request, digest = load_task(body.task_key, actor.tenant_id)
    if request.workflow_id != body.workflow_id:
        raise HTTPException(422, 'Local task belongs to a different workflow')
    inserted = db.scalar(insert(LocalJob).values(tenant_id=actor.tenant_id, workflow_id=body.workflow_id,
        requested_by=actor.id, task_key=body.task_key, task_hash=digest,
        idempotency_key=body.idempotency_key).on_conflict_do_nothing(constraint='uq_job_submission').returning(LocalJob.id))
    job = db.scalar(scoped(db, LocalJob).where(LocalJob.idempotency_key == body.idempotency_key))
    if (job.workflow_id, job.task_key, job.task_hash, job.requested_by) != (body.workflow_id, body.task_key, digest, actor.id):
        raise HTTPException(409, 'Idempotency key was used for a different submission')
    if inserted:
        append_event(db, actor, 'LOCAL_JOB_QUEUED', resource=workflow,
                     context={'job_id':str(job.id), 'task_key':body.task_key, 'task_hash':digest})
    db.commit()
    return serialize(job)


@router.get('')
def list_jobs(limit: int = Query(100, ge=1, le=100), actor=Depends(current_actor), db=Depends(get_db)):
    return [serialize(j) for j in db.scalars(scoped(db, LocalJob).order_by(LocalJob.created_at.desc()).limit(limit))]


@router.get('/workers')
def workers(actor=Depends(current_actor), db=Depends(get_db)):
    return [{**serialize(w), 'connected':w.stopped_at is None and (now()-w.heartbeat_at).total_seconds()<30}
            for w in db.scalars(scoped(db, LocalWorker).order_by(LocalWorker.started_at.desc()).limit(10))]


@router.get('/{job_id}')
def get_job(job_id: UUID, actor=Depends(current_actor), db=Depends(get_db)):
    return serialize(require_owned(db, LocalJob, job_id))
