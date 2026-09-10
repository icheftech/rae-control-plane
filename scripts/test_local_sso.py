"""Exercise real local OIDC redirects, PKCE, session, run history, and logout."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import httpx


class LoginForm(HTMLParser):
    action = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form' and attrs.get('id') == 'kc-form-login':
            self.action = attrs['action']


root = Path(__file__).resolve().parents[1]
user = json.loads((root/'local-state/sso-realm.json').read_text())['users'][0]
api = 'http://127.0.0.1:18000'
with httpx.Client(timeout=30, follow_redirects=False) as client:
    config = client.get(api+'/api/auth/config', headers={'Origin':'http://127.0.0.1:13000'})
    assert config.headers.get('access-control-allow-origin') == 'http://127.0.0.1:13000'
    assert config.headers.get('access-control-allow-credentials') == 'true'
    response = client.get(api+'/api/auth/login')
    assert response.status_code == 302, f'Login status: {response.status_code}'
    location = response.headers['location']
    assert urlparse(location).netloc == '127.0.0.1:18080'
    page = client.get(location)
    form = LoginForm()
    form.feed(page.text)
    # Browsers treat loopback as trustworthy; httpx does not send Secure cookies
    # over HTTP even on loopback. Limit this test-only adaptation to local Keycloak.
    for cookie in client.cookies.jar:
        if cookie.domain == '127.0.0.1' and cookie.path.startswith('/realms/southern-shade'):
            cookie.secure = False
    assert form.action and urlparse(form.action).netloc == '127.0.0.1:18080', 'Missing local sign-in form'
    response = client.post(form.action, data={'username': user['username'], 'password': user['credentials'][0]['value']})
    if response.status_code != 302:
        import re
        errors = re.findall(r'<(?:span|p)[^>]*(?:kc-feedback-text|pf-v5-c-alert__title)[^>]*>(.*?)</(?:span|p)>', response.text, re.S)
        print('Provider feedback:', [re.sub('<[^>]+>', '', error).strip() for error in errors])
        raise AssertionError(f'Provider login status: {response.status_code}')
    callback = response.headers['location']
    assert callback.startswith(api+'/api/auth/callback?')
    response = client.get(callback)
    assert response.status_code == 303, f'Callback status: {response.status_code}'
    assert 'HttpOnly' in response.headers.get('set-cookie', '')
    assert client.get(api+'/api/me').json()['role'] == 'admin'
    headers = {'Origin':'http://127.0.0.1:13000'}
    workflow = client.post(api+'/api/workflows', headers=headers,
        json={'name':'SSO verification '+str(uuid4())[:8], 'version':'1.0.0', 'risk_level':'low'})
    assert workflow.status_code == 201
    response = client.post(api+'/api/orchestrations/runs', headers=headers, json={
        'workflow_id':workflow.json()['id'], 'steps':[
            {'id':'local-check', 'type':'set_context', 'output_key':'check', 'value':'SSO works'}]})
    assert response.status_code == 201
    run_id = response.json()['run_id']
    detail = client.get(api+'/api/orchestrations/runs/'+run_id)
    assert detail.json()['status'] == 'success'
    assert 'SSO works' not in detail.text
    # The old callback must not authenticate again after its state/code were consumed.
    assert client.get(callback).status_code == 401
    assert client.post(api+'/api/auth/logout', headers=headers).status_code == 200
    assert client.get(api+'/api/me').status_code == 401
print('PASS: real Keycloak sign-in, PKCE callback, session, workflow, run timeline, replay rejection, logout')
