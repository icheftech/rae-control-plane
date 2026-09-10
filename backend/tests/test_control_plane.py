from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from app.db.models import AuditEvent
from app.services.model_provider import get_model_provider
from app.main import app

def workflow(client):
    response=client.post('/api/workflows',json={'name':'Agent','version':'1.0.0'})
    assert response.status_code==201, response.text
    return response.json()['id']
def policy(client, **kw):
    response=client.post('/api/control-policies',json={'name':'Policy','policy_action':'allow',**kw})
    assert response.status_code==201,response.text
    return response.json()

def test_auth_fail_closed(client):
    assert client.get('/api/workflows',headers={'Authorization':''}).status_code==401
    assert client.post('/api/workflows',headers={'Authorization':'Bearer viewer-key'},json={'name':'No'}).status_code==403
    assert client.get('/api/me').json()['role']=='admin'

def test_workflow_contract(client):
    id=workflow(client)
    assert client.get('/api/workflows').json()[0]['version']=='1.0.0'
    assert client.get('/api/workflows/'+id).status_code==200
    assert client.put('/api/workflows/'+id,json={'name':'Renamed','risk_level':'high'}).json()['name']=='Renamed'
    assert client.post('/api/workflows',json={'name':'Bad','created_by':'spoof'}).status_code==422
    assert client.delete('/api/workflows/'+id).status_code==204
    assert client.get('/api/workflows/'+id).json()['is_active'] is False
    assert client.get('/api/audit-events/verify').json()=={'valid':True,'verified_count':3}

def test_registry_relations(client):
    id=workflow(client)
    cap=client.post('/api/capabilities',json={'name':'Read','workflow_id':id})
    assert cap.status_code==201,cap.text
    conn=client.post('/api/connectors',json={'name':'Model','capability_id':cap.json()['id'],'connector_type':'ml_model'})
    assert conn.status_code==201,conn.text
    assert len(client.get('/api/connectors').json())==1
    assert client.post('/api/connectors',json={'name':'Unsafe','capability_id':cap.json()['id'],'connector_type':'api','credentials':{'password':'secret'}}).status_code==422
    assert client.get('/api/capabilities').status_code==200
    assert client.delete('/api/connectors/'+conn.json()['id']).status_code==204

def test_audit_tampering(client,test_db):
    workflow(client)
    event=test_db.scalar(select(AuditEvent))
    event.action='tampered'
    test_db.commit()
    assert client.get('/api/audit-events/verify').json()['valid'] is False

@pytest.mark.parametrize('mode',['hard_stop','soft_stop','read_only','degrade'])
def test_governance_stops(client,mode):
    id=workflow(client)
    policy(client)
    stop=client.post('/api/kill-switches',json={'name':'Incident','reason':'Testing','mode':mode}).json()
    assert client.post('/api/kill-switches/'+stop['id']+'/activate',json={'reason':'Incident'}).status_code==200
    response=client.post('/v1/chat/completions',json={'workflow_id':id,'messages':[{'role':'user','content':'hello'}]})
    assert response.status_code==403,response.text
    assert 'Emergency' in response.json()['detail']
    assert client.post('/api/kill-switches/'+stop['id']+'/deactivate',json={'reason':'Resolved'}).json()['is_active'] is False

def test_governed_model_call(client):
    id=workflow(client)
    provider=AsyncMock()
    provider.default_model='test-model';provider.api_key='fake'
    provider.generate_chat.return_value={'content':'ok','usage':{},'model':'test-model','audit_metadata':{}}
    app.dependency_overrides[get_model_provider]=lambda:provider
    body={'workflow_id':id,'messages':[{'role':'user','content':'private prompt'}]}
    assert client.post('/v1/chat/completions',json=body).status_code==403
    provider.generate_chat.assert_not_called()
    allow=policy(client,conditions={'model':'test-model'})
    assert client.post('/v1/chat/completions',json=body).status_code==200
    provider.generate_chat.assert_awaited_once()
    assert 'private prompt' not in client.get('/api/audit-events').text
    policy(client,policy_action='deny')
    assert client.post('/v1/chat/completions',json=body).status_code==403
    assert provider.generate_chat.await_count==1
    assert client.get('/api/audit-events/verify').json()['valid']

def test_change_separation(client):
    response=client.post('/api/change-requests',json={'title':'Deploy','description':'A change','rationale':'Needed','rollback_procedure':{'steps':'Restore'}})
    assert response.status_code==201,response.text
    id=response.json()['id'];path='/api/change-requests/'+id
    assert client.post(path+'/approve',json={'notes':'skip'}).status_code==409
    assert client.post(path+'/submit').json()['status']=='UNDER_REVIEW'
    assert client.post(path+'/review',json={'notes':'self'}).status_code==403
    assert client.post(path+'/review',headers={'Authorization':'Bearer review-key'},json={'notes':'Reviewed'}).status_code==200
    assert client.post(path+'/approve',headers={'Authorization':'Bearer review-key'},json={'notes':'Self'}).status_code==403
    assert client.post(path+'/approve',headers={'Authorization':'Bearer approve-key'},json={'notes':'Approved'}).json()['status']=='APPROVED'
    assert client.get('/api/change-requests').status_code==200
