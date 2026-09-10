"""OIDC sign-in: validated provider identity, explicit membership, opaque session."""
import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select, delete
from app.db.database import get_db
from app.db.models import BrowserSession
from app.db.models.tenant import Tenant

router = APIRouter(prefix='/api/auth', tags=['sso'])
COOKIE = 'rae_session'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def member(subject):
    try:
        identity = json.loads(os.getenv('RAE_SSO_MEMBERS', '{}')).get(subject)
        if identity and identity.get('role') in ('admin', 'operator', 'viewer') and identity.get('name'):
            return identity
    except (ValueError, AttributeError):
        pass
    raise HTTPException(403, 'No active Southern Shade membership for this identity')


def oidc():
    issuer = os.getenv('RAE_OIDC_ISSUER')
    client_id = os.getenv('RAE_OIDC_CLIENT_ID')
    if not issuer or not client_id or not os.getenv('RAE_SESSION_SECRET'):
        raise HTTPException(503, 'SSO is not configured')
    oauth = OAuth()
    return oauth.register('sst', client_id=client_id,
        client_secret=os.getenv('RAE_OIDC_CLIENT_SECRET'),
        server_metadata_url=issuer.rstrip('/')+'/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile', 'code_challenge_method': 'S256',
                       'token_endpoint_auth_method': 'client_secret_basic' if os.getenv('RAE_OIDC_CLIENT_SECRET') else 'none'})


@router.get('/config')
def config():
    return {'enabled': bool(os.getenv('RAE_OIDC_ISSUER') and os.getenv('RAE_SESSION_SECRET')),
            'tenant_name': 'Southern Shade Technologies'}


@router.get('/login')
async def login(request: Request):
    try:
        return await oidc().authorize_redirect(request, os.environ['RAE_OIDC_REDIRECT_URI'])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'SSO provider is unavailable')


@router.get('/callback')
async def callback(request: Request, db=Depends(get_db)):
    try:
        token = await oidc().authorize_access_token(request)
        claims = token.get('userinfo')
        if not claims or claims.get('iss') != os.getenv('RAE_OIDC_ISSUER'):
            raise ValueError('Invalid issuer')
        subject = claims['sub']
        member(subject)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, 'SSO validation failed; please sign in again')
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_key == os.getenv('RAE_TENANT_KEY'), Tenant.is_active == True))
    if tenant is None:
        raise HTTPException(403, 'Installation tenant is inactive or not provisioned')
    value = secrets.token_urlsafe(32)
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(BrowserSession).where(BrowserSession.token_hash == digest(old)))
    db.add(BrowserSession(token_hash=digest(value), subject=subject, tenant_id=tenant.id,
                         expires_at=datetime.now(timezone.utc)+timedelta(hours=8)))
    db.commit()
    request.session.clear()
    response = RedirectResponse(os.environ['RAE_FRONTEND_URL'], status_code=303)
    response.set_cookie(COOKIE, value, httponly=True, secure=os.getenv('RAE_COOKIE_SECURE', 'true') == 'true',
                        samesite='lax', max_age=28800, path='/api')
    return response


def check_origin(request):
    if request.headers.get('origin') != os.getenv('RAE_FRONTEND_URL'):
        raise HTTPException(403, 'Untrusted session request origin')


@router.post('/logout')
def logout(request: Request, db=Depends(get_db)):
    check_origin(request)
    value = request.cookies.get(COOKIE)
    if value:
        db.execute(delete(BrowserSession).where(BrowserSession.token_hash == digest(value)))
        db.commit()
    response = JSONResponse({'signed_out': True})
    response.delete_cookie(COOKIE, path='/api')
    return response
