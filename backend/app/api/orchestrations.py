"""Workflow orchestration endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.security import Actor, operator
from app.services.model_provider import ModelProvider, get_model_provider
from app.services.orchestration import OrchestrationRunRequest, OrchestrationRunner

router = APIRouter(prefix="/api/orchestrations", tags=["orchestrations"])


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
