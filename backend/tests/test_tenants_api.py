"""Tenant administrators may manage their organization, not the directory."""
from uuid import uuid4
from app.db.models.tenant import Tenant


def test_directory_is_tenant_scoped(client, test_db):
    other=Tenant(tenant_key='another',tenant_name='Private tenant',created_by='test')
    test_db.add(other); test_db.commit()
    response=client.get('/api/tenants/')
    assert len(response.json()) == 1
    own=response.json()[0]
    assert own['tenant_key'] == 'southern_shade_technologies'
    assert client.get('/api/tenants/'+str(other.id)).status_code == 404
    assert client.patch('/api/tenants/'+str(other.id),json={'tenant_name':'Hijacked'}).status_code == 404
    assert client.delete('/api/tenants/'+str(other.id)).status_code == 404
    assert client.get('/api/tenants/'+str(uuid4())).status_code == 404
    assert client.post('/api/tenants/',json={'tenant_name':'New','tenant_key':'new','created_by':'spoof'}).status_code == 403
    assert client.patch('/api/tenants/'+own['id'],json={'tenant_key':'replacement'}).status_code == 422
    assert client.patch('/api/tenants/'+own['id'],json={'description':'Our organization'}).status_code == 200
    assert client.delete('/api/tenants/'+own['id']).status_code == 204
    assert client.get('/api/workflows').status_code == 403
