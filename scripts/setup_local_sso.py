"""Provision local SST identity files and first organization, without printing secrets."""
import json
import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4
from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[1]
state = root / 'local-state'
state.mkdir(exist_ok=True)
os.chmod(state, 0o700)


def private_file(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as file:
        file.write(content)


if not (state / 'sso-realm.json').exists():
    subject = str(uuid4())
    password, bootstrap = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    realm = {'realm': 'southern-shade', 'enabled': True, 'displayName': 'Southern Shade Technologies',
        'registrationAllowed': False, 'sslRequired': 'external',
        'clients': [{'clientId': 'rae-local', 'enabled': True, 'publicClient': True,
            'standardFlowEnabled': True, 'directAccessGrantsEnabled': False,
            'redirectUris': ['http://127.0.0.1:18000/api/auth/callback'],
            'attributes': {'pkce.code.challenge.method': 'S256'}}],
        'users': [{'id': subject, 'username': 'sst-owner', 'enabled': True,
            'firstName': 'Southern Shade', 'lastName': 'Owner',
            'email': 'owner@sst.local', 'emailVerified': True,
            'credentials': [{'type': 'password', 'value': password, 'temporary': False}]}]}
    private_file(state / 'sso-realm.json', json.dumps(realm))
    private_file(state / 'sso.env', f'KC_BOOTSTRAP_ADMIN_USERNAME=bootstrap\nKC_BOOTSTRAP_ADMIN_PASSWORD={bootstrap}\n')
    private_file(state / 'SSO_ACCESS.txt', f'Local Southern Shade SSO\nUsername: sst-owner\nPassword: {password}\n\nKeycloak admin: http://127.0.0.1:18080/admin\nUsername: bootstrap\nPassword: {bootstrap}\n')
else:
    subject = json.loads((state / 'sso-realm.json').read_text())['users'][0]['id']

imports = state / 'sso-import'
imports.mkdir(exist_ok=True)
if not (imports / 'southern-shade-realm.json').exists():
    private_file(imports / 'southern-shade-realm.json', (state / 'sso-realm.json').read_text())

settings = {
    'RAE_TENANT_KEY': 'southern_shade_technologies',
    'RAE_OIDC_ISSUER': 'http://127.0.0.1:18080/realms/southern-shade',
    'RAE_OIDC_CLIENT_ID': 'rae-local',
    'RAE_OIDC_REDIRECT_URI': 'http://127.0.0.1:18000/api/auth/callback',
    'RAE_FRONTEND_URL': 'http://127.0.0.1:13000',
    'RAE_COOKIE_SECURE': 'false',
    'RAE_SSO_MEMBERS': json.dumps({subject: {'name': 'Southern Shade Owner', 'role': 'admin'}}),
}
existing = dotenv_values(root / '.env')
origins = [value.strip() for value in (existing.get('ALLOWED_ORIGINS') or '').split(',') if value.strip()]
settings['ALLOWED_ORIGINS'] = ','.join(dict.fromkeys([*origins, settings['RAE_FRONTEND_URL']]))
settings['RAE_SESSION_SECRET'] = existing.get('RAE_SESSION_SECRET') or secrets.token_urlsafe(48)
for key, value in settings.items():
    set_key(root / '.env', key, value)
for key, value in dotenv_values(root / '.env').items():
    if value is not None:
        os.environ.setdefault(key, value)
os.environ.setdefault('DATABASE_URL', 'postgresql://rae_user:' + os.environ['POSTGRES_PASSWORD'] + '@127.0.0.1:55432/rae_control_plane')
sys.path.insert(0, str(root / 'backend'))
os.chdir(root / 'backend')
from alembic import command
from alembic.config import Config
command.upgrade(Config('alembic.ini'), 'head')
from app.db.database import SessionLocal
from app.db.models.tenant import Tenant
from app.services.audit import append_event
from app.security import Actor
with SessionLocal() as db:
    tenant = db.query(Tenant).filter_by(tenant_key=settings['RAE_TENANT_KEY']).first()
    if not tenant:
        tenant = Tenant(tenant_key=settings['RAE_TENANT_KEY'], tenant_name='Southern Shade Technologies',
                        created_by='local-provisioner', settings={'deployment': 'single-tenant'})
        db.add(tenant)
        db.flush()
        append_event(db, Actor('local-provisioner', 'admin', tenant_id=tenant.id), 'TENANT_CREATED', tenant)
        db.commit()
print('Southern Shade organization provisioned. Local credentials: local-state/SSO_ACCESS.txt')
