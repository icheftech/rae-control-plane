"""Single-installation API-key authentication. Keys map to server-owned identities."""
import os, json, secrets
import hashlib
from app.services.rate_limit import limit_actor
from dataclasses import dataclass
from uuid import UUID, uuid5, NAMESPACE_URL
from fastapi import Depends, HTTPException, Request
from datetime import datetime, timezone
from app.db.database import get_db
from app.db.models.browser_session import BrowserSession
from app.db.models.tenant import Tenant
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)
@dataclass(frozen=True)
class Actor:
    name: str
    role: str
    subject: str | None = None
    @property
    def id(self) -> UUID:
        return uuid5(NAMESPACE_URL, 'rae:actor:' + (self.subject or self.name))

def current_actor(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)) -> Actor:
    if not credentials and request.cookies.get('rae_session'):
        from app.api.sso import digest, member, check_origin
        session = db.get(BrowserSession, digest(request.cookies['rae_session']))
        if session is None or session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(401, 'Session expired; sign in again')
        tenant = db.get(Tenant, session.tenant_id)
        if not tenant or not tenant.is_active or tenant.tenant_key != os.getenv('RAE_TENANT_KEY'):
            raise HTTPException(403, 'Installation tenant is inactive')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            check_origin(request)
        identity = member(session.subject)
        return limit_actor(Actor(identity['name'], identity['role'], os.getenv('RAE_OIDC_ISSUER', '')+':'+session.subject))
    try:
        keys = json.loads(os.getenv('RAE_API_KEYS', '{}'))
        hashed_keys = json.loads(os.getenv('RAE_API_KEY_HASHES', '{}'))
    except (ValueError, TypeError):
        raise HTTPException(503, 'Authentication configuration is invalid')
    if not keys and not hashed_keys:
        raise HTTPException(503, 'Configure RAE_API_KEYS before using the control plane')
    if credentials:
        presented_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        candidates = [(key, identity, credentials.credentials) for key, identity in keys.items()]
        candidates += [(key, identity, presented_hash) for key, identity in hashed_keys.items()]
        for key, identity, presented in candidates:
            if secrets.compare_digest(presented, key):
                if identity.get('revoked'):
                    raise HTTPException(401, 'API key revoked')
                if identity.get('expires_at'):
                    try:
                        expiry = datetime.fromisoformat(identity['expires_at'].replace('Z', '+00:00'))
                        if expiry.tzinfo is None:
                            raise ValueError('Timezone required')
                    except (ValueError, TypeError):
                        raise HTTPException(503, 'Invalid API-key expiry configuration')
                    if expiry <= datetime.now(timezone.utc):
                        raise HTTPException(401, 'API key expired')
                if identity.get('role') not in ('admin', 'operator', 'viewer') or not identity.get('name'):
                    raise HTTPException(503, 'Invalid API-key identity')
                return limit_actor(Actor(identity['name'], identity['role']))
    raise HTTPException(401, 'Invalid or missing API key', headers={'WWW-Authenticate':'Bearer'})

def operator(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role not in ('operator', 'admin'):
        raise HTTPException(403, 'Operator access required')
    return actor

def admin(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return actor
