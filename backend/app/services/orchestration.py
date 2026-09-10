"""Minimal workflow orchestration runtime for governed local agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import Workflow
from app.security import Actor
from app.services.audit import append_event
from app.services.governance import evaluate
from app.services.model_provider import ModelProvider
from app.services.run_history import RunHistory, safe_usage


class OrchestrationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=32000)


class OrchestrationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80, pattern="^[a-zA-Z0-9_.-]+$")
    type: str = Field(pattern="^(set_context|llm_chat)$")
    input_key: str | None = Field(default=None, min_length=1, max_length=80)
    output_key: str = Field(min_length=1, max_length=80, pattern="^[a-zA-Z0-9_.-]+$")
    value: Any | None = None
    messages: list[OrchestrationMessage] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=120)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=8192)


class OrchestrationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: UUID
    inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[OrchestrationStep] = Field(min_length=1, max_length=25)


@dataclass
class StepResult:
    id: str
    type: str
    status: str
    output_key: str
    model: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    run_id: str
    workflow_id: str
    status: str
    outputs: dict[str, Any]
    steps: list[StepResult]


class OrchestrationRunner:
    """Executes ordered workflow steps with governance before model calls."""

    def __init__(self, db: Session, actor: Actor, provider: ModelProvider):
        self.db = db
        self.actor = actor
        self.provider = provider

    async def run(self, request: OrchestrationRunRequest) -> RunResult:
        with RunHistory(self.db, self.actor, request.workflow_id, len(request.steps)) as history:
            return await self._execute(request, history)

    async def _execute(self, request: OrchestrationRunRequest, history: RunHistory) -> RunResult:
        workflow = self.db.get(Workflow, request.workflow_id)
        if workflow is None or not workflow.is_active:
            raise HTTPException(404, "Workflow is missing or inactive")

        run_id = str(history.run.id)
        context = dict(request.inputs)
        step_results: list[StepResult] = []
        append_event(
            self.db,
            self.actor,
            "ORCHESTRATION_STARTED",
            resource=workflow,
            context={"run_id": run_id, "step_count": len(request.steps)},
        )
        self.db.commit()

        try:
            for position, step in enumerate(request.steps):
                model = (step.model or self.provider.default_model) if step.type == 'llm_chat' else None
                with history.step(position, step.id, step.type, model) as event:
                    result = await self._run_step(workflow, run_id, context, step)
                    event.token_usage = safe_usage(result.usage)
                    step_results.append(result)
        except HTTPException as exc:
            append_event(
                self.db,
                self.actor,
                "ORCHESTRATION_FAILED",
                resource=workflow,
                outcome="BLOCKED" if exc.status_code == 403 else "ERROR",
                context={"run_id": run_id, "reason": exc.detail},
            )
            self.db.commit()
            raise
        except Exception:
            append_event(
                self.db,
                self.actor,
                "ORCHESTRATION_FAILED",
                resource=workflow,
                outcome="ERROR",
                context={"run_id": run_id},
            )
            self.db.commit()
            raise HTTPException(500, "Workflow orchestration failed")

        append_event(
            self.db,
            self.actor,
            "ORCHESTRATION_COMPLETED",
            resource=workflow,
            context={"run_id": run_id, "step_count": len(step_results)},
        )
        self.db.commit()
        return RunResult(
            run_id=run_id,
            workflow_id=str(request.workflow_id),
            status="completed",
            outputs=context,
            steps=step_results,
        )

    async def _run_step(
        self,
        workflow: Workflow,
        run_id: str,
        context: dict[str, Any],
        step: OrchestrationStep,
    ) -> StepResult:
        if step.type == "set_context":
            value = context.get(step.input_key) if step.input_key else step.value
            context[step.output_key] = value
            append_event(
                self.db,
                self.actor,
                "ORCHESTRATION_STEP_COMPLETED",
                resource=workflow,
                context={"run_id": run_id, "step_id": step.id, "step_type": step.type},
            )
            self.db.commit()
            return StepResult(id=step.id, type=step.type, status="completed", output_key=step.output_key)

        if not step.messages:
            raise HTTPException(422, "llm_chat steps require messages")

        model = step.model or self.provider.default_model
        allowed, reason = evaluate(self.db, workflow.id, model)
        audit_context = {
            "run_id": run_id,
            "step_id": step.id,
            "workflow_id": str(workflow.id),
            "model": model,
            "reason": reason,
        }
        append_event(
            self.db,
            self.actor,
            "ORCHESTRATION_STEP_ALLOWED" if allowed else "ORCHESTRATION_STEP_BLOCKED",
            resource=workflow,
            outcome="SUCCESS" if allowed else "BLOCKED",
            context=audit_context,
        )
        self.db.commit()
        if not allowed:
            raise HTTPException(403, reason)
        if not self.provider.api_key:
            raise HTTPException(503, "LLM provider key is not configured")

        messages = [{"role": message.role, "content": render_template(message.content, context)} for message in step.messages]
        try:
            result = await self.provider.generate_chat(
                messages=messages,
                model=model,
                workflow_id=str(workflow.id),
                temperature=step.temperature,
                max_tokens=step.max_tokens,
            )
        except Exception:
            append_event(
                self.db,
                self.actor,
                "ORCHESTRATION_STEP_FAILED",
                resource=workflow,
                outcome="ERROR",
                context=audit_context,
            )
            self.db.commit()
            raise HTTPException(502, "Model provider request failed")

        context[step.output_key] = result.get("content", "")
        append_event(
            self.db,
            self.actor,
            "ORCHESTRATION_STEP_COMPLETED",
            resource=workflow,
            context={**audit_context, "usage": safe_usage(result.get("usage", {}))},
        )
        self.db.commit()
        return StepResult(
            id=step.id,
            type=step.type,
            status="completed",
            output_key=step.output_key,
            model=model,
            usage=result.get("usage", {}),
        )


def render_template(template: str, context: dict[str, Any]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered
