import json
from uuid import UUID, uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from app.db.models.tenant import Tenant
from app.main import app
from app.services.model_provider import get_model_provider
from app.services.evidence import evaluate_snapshot


def other_tenant(client,test_db,monkeypatch):
    tenant=Tenant(tenant_key='other',tenant_name='Other Company',created_by='test')
    test_db.add(tenant);test_db.commit()
    import os
    keys=json.loads(os.environ['RAE_API_KEYS'])
    keys['other-key']={'name':'test-harness','role':'admin','tenant_key':'other'}
    monkeypatch.setenv('RAE_API_KEYS',json.dumps(keys))
    return {'Authorization':'Bearer other-key'}


def test_cross_tenant_crud_relations_and_runs(client,test_db,monkeypatch):
    other=other_tenant(client,test_db,monkeypatch)
    workflow=client.post('/api/workflows',json={'name':'Same name','version':'1'}).json()
    wid=workflow['id']
    assert client.post('/api/workflows',headers=other,json={'name':'Same name','version':'1'}).status_code == 201
    cap=client.post('/api/capabilities',json={'name':'Read','workflow_id':wid}).json()
    conn=client.post('/api/connectors',json={'name':'Connector','connector_type':'api','capability_id':cap['id']}).json()
    policy=client.post('/api/control-policies',json={'name':'Allow','policy_action':'allow'}).json()
    stop=client.post('/api/kill-switches',json={'name':'Stop','reason':'Test','workflow_id':wid}).json()
    change=client.post('/api/change-requests',json={'title':'Change','description':'Test','rationale':'Test','workflow_id':wid}).json()
    for path,obj in [('workflows',workflow),('capabilities',cap),('connectors',conn),('control-policies',policy),('kill-switches',stop)]:
        assert client.get('/api/'+path+'/'+obj['id'],headers=other).status_code == 404
        assert obj['id'] not in [r['id'] for r in client.get('/api/'+path,headers=other).json()]
    for path,payload in [('capabilities',{'name':'Cross','workflow_id':wid}),('connectors',{'name':'Cross','connector_type':'api','capability_id':cap['id']}),('control-policies',{'name':'Cross','workflow_id':wid}),('kill-switches',{'name':'Cross','reason':'Test','workflow_id':wid}),('change-requests',{'title':'Cross','description':'Test','rationale':'Test','workflow_id':wid})]:
        if path == 'control-policies':
            payload['policy_action']='allow'
        assert client.post('/api/'+path,headers=other,json=payload).status_code == 404
    assert client.put('/api/workflows/'+wid,headers=other,json={'name':'Cross'}).status_code == 404
    assert client.delete('/api/workflows/'+wid,headers=other).status_code == 404
    assert client.post('/api/kill-switches/'+stop['id']+'/activate',headers=other,json={'reason':'Cross'}).status_code == 404
    assert client.post('/api/change-requests/'+change['id']+'/submit',headers=other).status_code == 404
    run=client.post('/api/orchestrations/runs',json={'workflow_id':wid,'steps':[{'id':'copy','type':'set_context','output_key':'x','value':'private'}]}).json()
    assert client.get('/api/orchestrations/runs/'+run['run_id'],headers=other).status_code == 404
    assert client.get('/api/orchestrations/runs',headers=other).json() == []
    assert client.post('/v1/chat/completions',headers=other,json={'workflow_id':wid,'messages':[{'role':'user','content':'test'}]}).status_code == 404
    events=client.get('/api/audit-events',headers=other).json()
    assert all(e['resource']['id'] != wid for e in events if e['resource'])
    assert client.get('/api/audit-events/verify',headers=other).json()['valid']


def test_snapshot_survives_policy_change_and_stop(client,test_db,monkeypatch):
    other=other_tenant(client,test_db,monkeypatch)
    wid=client.post('/api/workflows',json={'name':'Evidence','version':'1'}).json()['id']
    client.post('/api/control-policies',json={'name':'Allow','policy_action':'allow'})
    foreign_stop=client.post('/api/kill-switches',headers=other,json={'name':'Other stop','reason':'Test'}).json()
    client.post('/api/kill-switches/'+foreign_stop['id']+'/activate',headers=other,json={'reason':'Test'})
    provider=AsyncMock();provider.default_model='test';provider.api_key='local';provider.generate_chat.return_value={'content':'secret response','usage':{},'audit_metadata':{}}
    app.dependency_overrides[get_model_provider]=lambda:provider
    payload={'workflow_id':wid,'steps':[{'id':'plan','type':'llm_chat','output_key':'result','messages':[{'role':'user','content':'secret prompt'}]}]}
    first=client.post('/api/orchestrations/runs',json=payload)
    assert first.status_code == 201,first.text
    original=client.get('/api/orchestrations/runs/'+first.json()['run_id']).json()
    snapshot=original['policy_snapshots'][0]
    assert evaluate_snapshot(snapshot['content'])[0]
    stop=client.post('/api/kill-switches',json={'name':'Own stop','reason':'Test','workflow_id':wid}).json()
    client.post('/api/kill-switches/'+stop['id']+'/activate',json={'reason':'Test'})
    denied=client.post('/api/orchestrations/runs',json=payload)
    assert denied.status_code == 403
    second=client.get('/api/orchestrations/runs/'+denied.headers['X-Run-ID']).json()
    assert second['context_id'] != original['context_id']
    assert second['context']['tenant_id'] == original['tenant_id']
    assert not evaluate_snapshot(second['policy_snapshots'][0]['content'])[0]
    assert client.get('/api/orchestrations/runs/'+original['id']).json()['policy_snapshots'][0] == snapshot
    assert 'secret prompt' not in json.dumps(original) and 'secret response' not in json.dumps(original)
    event_ids={e['id'] for e in original['events']}
    assert all(e['parent_event_id'] in event_ids for e in original['events'] if e['parent_event_id'])
    assert all(e['caused_by_event_id'] in event_ids for e in original['events'] if e['caused_by_event_id'])
    assert any(e['event_type']=='authorization' and e['policy_snapshot_id']==snapshot['id'] for e in original['events'])
    provider.generate_chat.assert_awaited_once()
    for table,id_value in [('policy_snapshots',snapshot['id']),('execution_contexts',original['context_id']),('execution_events',original['events'][0]['id'])]:
        with pytest.raises(DBAPIError):
            with test_db.begin_nested():
                test_db.execute(text(f'DELETE FROM {table} WHERE id=:id'),{'id':UUID(id_value)})
    with pytest.raises(DBAPIError):
        with test_db.begin_nested():
            test_db.execute(text('UPDATE orchestration_runs SET actor_id=:id WHERE id=:run'),{'id':uuid4(),'run':UUID(original['id'])})
