from uuid import uuid4
from unittest.mock import AsyncMock
from sqlalchemy import select
from app.db.models import OrchestrationRun
from app.main import app
from app.services.model_provider import get_model_provider
from app.services.telemetry import logger


def test_history_success_and_privacy(client):
    workflow = client.post('/api/workflows', json={'name':'History', 'version':'1'}).json()['id']
    response = client.post('/api/orchestrations/runs', json={'workflow_id': workflow,
        'steps':[{'id':'copy', 'type':'set_context', 'output_key':'out', 'value':'PRIVATE_EMAIL_CONTENT'}]})
    assert response.status_code == 201
    run_id = response.json()['run_id']
    detail = client.get('/api/orchestrations/runs/'+run_id)
    assert detail.json()['status'] == 'success'
    assert detail.json()['steps'][0]['completed_at']
    assert 'PRIVATE_EMAIL_CONTENT' not in detail.text
    assert 'PRIVATE_EMAIL_CONTENT' not in client.get('/api/orchestrations/runs').text
    assert len(client.get('/api/orchestrations/runs?status=success').json()) == 1
    assert client.get('/api/orchestrations/runs?status=denied').json() == []
    assert client.get('/api/orchestrations/runs?started_after=2100-01-01T00:00:00Z').json() == []
    assert client.get('/api/orchestrations/runs?limit=101').status_code == 422
    assert client.get('/api/orchestrations/runs/'+str(uuid4())).status_code == 404
    assert client.get('/api/orchestrations/runs', headers={'Authorization':'Bearer bad'}).status_code == 401


def test_direct_call_denial_and_failure_history(client, test_db):
    workflow = client.post('/api/workflows', json={'name':'Direct', 'version':'1'}).json()['id']
    provider = AsyncMock()
    provider.default_model = 'test-model'
    provider.api_key = 'test'
    app.dependency_overrides[get_model_provider] = lambda: provider
    payload = {'workflow_id':workflow, 'messages':[{'role':'user','content':'PRIVATE_PROMPT'}]}
    response = client.post('/v1/chat/completions', json=payload)
    assert response.status_code == 403
    detail = client.get('/api/orchestrations/runs/'+response.headers['X-Run-ID']).json()
    assert detail['status'] == 'denied'
    assert detail['steps'][0]['decision_reason'] == 'No matching allow policy'
    provider.generate_chat.assert_not_called()
    client.post('/api/control-policies', json={'name':'allow', 'policy_action':'allow', 'conditions':{}})
    provider.generate_chat.side_effect = RuntimeError('PRIVATE_PROVIDER_ERROR')
    response = client.post('/v1/chat/completions', json=payload)
    assert response.status_code == 502
    detail = client.get('/api/orchestrations/runs/'+response.headers['X-Run-ID'])
    assert detail.json()['status'] == 'error'
    assert detail.json()['steps'][0]['status'] == 'error'
    assert 'PRIVATE' not in detail.text
    provider.generate_chat.side_effect = None
    provider.generate_chat.return_value = {'content':'PRIVATE_RESPONSE','audit_metadata':{},
        'usage':{'total_tokens':5,'untrusted':'PRIVATE_USAGE'}}
    response = client.post('/v1/chat/completions', json=payload)
    assert response.status_code == 200
    detail = client.get('/api/orchestrations/runs/'+response.json()['audit_metadata']['run_id'])
    assert detail.json()['steps'][0]['token_usage'] == {'total_tokens':5}
    assert 'PRIVATE' not in detail.text


def test_request_telemetry(client, monkeypatch):
    messages = []
    monkeypatch.setattr(logger, 'info', messages.append)
    response = client.get('/api/me?secret=DO_NOT_LOG')
    assert response.headers['X-Request-ID']
    assert 'http_request' in messages[-1]
    assert 'DO_NOT_LOG' not in str(messages)
    assert 'test-key' not in str(messages)
