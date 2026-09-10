"""Single-installation API-key authentication. Keys map to server-owned identities."""
import os, json, secrets
from dataclasses import dataclass
from uuid import UUID, uuid5, NAMESPACE_URL
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)
@dataclass(frozen=True)
class Actor:
    name: str
    role: str
    @property
    def id(self) -> UUID:
        return uuid5(NAMESPACE_URL, 'rae:actor:' + self.name)

def current_actor(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> Actor:
    try:
        keys = json.loads(os.getenv('RAE_API_KEYS', '{}'))
    except (ValueError, TypeError):
        raise HTTPException(503, 'Authentication configuration is invalid')
    if not keys:
        raise HTTPException(503, 'Configure RAE_API_KEYS before using the control plane')
    if credentials:
        for key, identity in keys.items():
            if secrets.compare_digest(credentials.credentials, key):
                if identity.get('role') not in ('admin', 'operator', 'viewer') or not identity.get('name'):
                    raise HTTPException(503, 'Invalid API-key identity')
                return Actor(identity['name'], identity['role'])
    raise HTTPException(401, 'Invalid or missing API key', headers={'WWW-Authenticate':'Bearer'})

def operator(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role not in ('operator', 'admin'):
        raise HTTPException(403, 'Operator access required')
    return actor

def admin(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return actor
