from unittest.mock import AsyncMock

from sqlalchemy import select

from app.db.models import AuditEvent
from app.main import app
from app.services.model_provider import get_model_provider


def create_workflow(client):
    response = client.post("/api/workflows", json={"name": "Local Agent", "version": "1.0.0"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def allow_model(client, model="test-model"):
    response = client.post(
        "/api/control-policies",
        json={"name": "Allow local model", "policy_action": "allow", "conditions": {"model": model}},
    )
    assert response.status_code == 201, response.text


def test_orchestration_runs_ordered_governed_steps(client, test_db):
    workflow_id = create_workflow(client)
    allow_model(client)
    provider = AsyncMock()
    provider.default_model = "test-model"
    provider.api_key = "local-key"
    provider.generate_chat.return_value = {
        "content": "Check the latest unread Gmail headers and summarize only metadata.",
        "usage": {"total_tokens": 12},
        "model": "test-model",
        "audit_metadata": {},
    }
    app.dependency_overrides[get_model_provider] = lambda: provider

    response = client.post(
        "/api/orchestrations/runs",
        json={
            "workflow_id": workflow_id,
            "inputs": {"goal": "check personal Gmail safely"},
            "steps": [
                {"id": "capture_goal", "type": "set_context", "input_key": "goal", "output_key": "task"},
                {
                    "id": "plan",
                    "type": "llm_chat",
                    "output_key": "plan",
                    "messages": [{"role": "user", "content": "Plan this workflow: {{task}}"}],
                    "model": "test-model",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["outputs"]["task"] == "check personal Gmail safely"
    assert "Gmail" in body["outputs"]["plan"]
    provider.generate_chat.assert_awaited_once()
    assert provider.generate_chat.await_args.kwargs["messages"][0]["content"] == "Plan this workflow: check personal Gmail safely"
    audit_text = "\n".join(event.action + str(event.context) for event in test_db.scalars(select(AuditEvent)).all())
    assert "ORCHESTRATION_STARTED" in audit_text
    assert "ORCHESTRATION_COMPLETED" in audit_text
    assert "Plan this workflow" not in audit_text


def test_orchestration_blocks_model_step_without_policy(client):
    workflow_id = create_workflow(client)
    provider = AsyncMock()
    provider.default_model = "test-model"
    provider.api_key = "local-key"
    app.dependency_overrides[get_model_provider] = lambda: provider

    response = client.post(
        "/api/orchestrations/runs",
        json={
            "workflow_id": workflow_id,
            "steps": [
                {
                    "id": "blocked",
                    "type": "llm_chat",
                    "output_key": "result",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            ],
        },
    )

    assert response.status_code == 403, response.text
    provider.generate_chat.assert_not_called()
