"""Workflow orchestration endpoints."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.security import Actor, operator, current_actor
from app.db.models import OrchestrationRun, OrchestrationRunEvent
from app.services.model_provider import ModelProvider, get_model_provider
from app.services.orchestration import OrchestrationRunRequest, OrchestrationRunner

router = APIRouter(prefix="/api/orchestrations", tags=["orchestrations"])


def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@router.get('/runs')
def list_runs(status: Literal['pending', 'success', 'error', 'denied'] | None = None,
              started_after: datetime | None = None, started_before: datetime | None = None,
              workflow_id: UUID | None = None, limit: int = Query(100, ge=1, le=100),
              offset: int = Query(0, ge=0), actor: Actor = Depends(current_actor),
              db: Session = Depends(get_db)):
    query = select(OrchestrationRun)
    if status:
        query = query.where(OrchestrationRun.status == status)
    if started_after:
        query = query.where(OrchestrationRun.started_at >= started_after)
    if started_before:
        query = query.where(OrchestrationRun.started_at <= started_before)
    if workflow_id:
        query = query.where(OrchestrationRun.workflow_id == workflow_id)
    return [serialize(row) for row in db.scalars(query.order_by(
        OrchestrationRun.started_at.desc(), OrchestrationRun.id).offset(offset).limit(limit))]


@router.get('/runs/{run_id}')
def get_run(run_id: UUID, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    run = db.get(OrchestrationRun, run_id)
    if run is None:
        raise HTTPException(404, 'Run not found')
    events = db.scalars(select(OrchestrationRunEvent).where(
        OrchestrationRunEvent.run_id == run_id).order_by(OrchestrationRunEvent.position)).all()
    return {**serialize(run), 'steps': [serialize(event) for event in events]}


@router.post("/runs", status_code=201)
async def run_orchestration(
    request: OrchestrationRunRequest,
    actor: Actor = Depends(operator),
    db: Session = Depends(get_db),
    provider: ModelProvider = Depends(get_model_provider),
):
    result = await OrchestrationRunner(db, actor, provider).run(request)
    return {
        "run_id": result.run_id,
        "workflow_id": result.workflow_id,
        "status": result.status,
        "outputs": result.outputs,
        "steps": [step.__dict__ for step in result.steps],
    }
