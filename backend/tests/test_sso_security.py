import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.api.sso import digest
from app.db.models import BrowserSession
from app.db.models.tenant import Tenant


def session_cookie(client, test_db, monkeypatch):
    monkeypatch.setenv('RAE_TENANT_KEY', 'sst-test')
    monkeypatch.setenv('RAE_FRONTEND_URL', 'http://127.0.0.1:13000')
    monkeypatch.setenv('RAE_SSO_MEMBERS', json.dumps({'subject': {'name': 'Owner', 'role': 'admin'}}))
    tenant = Tenant(tenant_key='sst-test', tenant_name='SST', created_by='test')
    test_db.add(tenant)
    test_db.flush()
    session = BrowserSession(token_hash=digest('test-session'), subject='subject', tenant_id=tenant.id,
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1))
    test_db.add(session)
    test_db.commit()
    client.headers.pop('Authorization')
    client.cookies.set('rae_session', 'test-session')
    return tenant, session


def test_sso_cookie_csrf_revocation_and_logout(client, test_db, monkeypatch):
    tenant, session = session_cookie(client, test_db, monkeypatch)
    assert client.get('/api/me').json()['name'] == 'Owner'
    payload = {'name':'SSO workflow', 'version':'1'}
    assert client.post('/api/workflows', json=payload).status_code == 403
    origin = {'Origin':'http://127.0.0.1:13000'}
    assert client.post('/api/workflows', json=payload, headers=origin).status_code == 201
    monkeypatch.setenv('RAE_SSO_MEMBERS', '{}')
    assert client.get('/api/me').status_code == 403
    monkeypatch.setenv('RAE_SSO_MEMBERS', '{"subject":{"name":"Owner","role":"admin"}}')
    tenant.is_active = False
    test_db.commit()
    assert client.get('/api/me').status_code == 403
    tenant.is_active = True
    session.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
    test_db.commit()
    assert client.get('/api/me').status_code == 401
    assert client.post('/api/auth/logout').status_code == 403
    assert client.post('/api/auth/logout', headers=origin).status_code == 200
    assert test_db.get(BrowserSession, digest('test-session')) is None


def test_unconfigured_sso_and_invalid_callback(client, monkeypatch):
    monkeypatch.delenv('RAE_OIDC_ISSUER', raising=False)
    assert client.get('/api/auth/config').json()['enabled'] is False
    assert client.get('/api/auth/login').status_code == 503


def test_hashed_credentials_expiry_and_rate_limit(client, monkeypatch):
    identity = {'name':'hashed-agent','role':'operator','expires_at':'2100-01-01T00:00:00Z'}
    monkeypatch.setenv('RAE_API_KEY_HASHES', json.dumps({digest('agent-secret'): identity}))
    headers = {'Authorization':'Bearer agent-secret'}
    assert client.get('/api/me', headers=headers).status_code == 200
    identity['expires_at'] = '2000-01-01T00:00:00Z'
    monkeypatch.setenv('RAE_API_KEY_HASHES', json.dumps({digest('agent-secret'): identity}))
    assert client.get('/api/me', headers=headers).status_code == 401
    identity['revoked'] = True
    monkeypatch.setenv('RAE_API_KEY_HASHES', json.dumps({digest('agent-secret'): identity}))
    assert client.get('/api/me', headers=headers).status_code == 401
    monkeypatch.setenv('RAE_REQUESTS_PER_MINUTE', '1')
    assert client.get('/api/me').status_code == 200
    response = client.get('/api/me')
    assert response.status_code == 429
    assert int(response.headers['Retry-After']) > 0
