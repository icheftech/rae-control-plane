"""R.A.E. local control plane. Authentication is required for every data route."""
import os, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from app.db.database import check_db_connection, engine
from app.security import current_actor, Actor
from app.api import registry, tenants, llm, audit, change_requests, orchestrations
from app.services import model_provider
from app.services.telemetry import RequestTelemetry
from app.api import sso
from starlette.middleware.sessions import SessionMiddleware

@asynccontextmanager
async def lifespan(app):
    yield
    if model_provider._provider_instance:
        await model_provider._provider_instance.close()
        model_provider._provider_instance = None
    engine.dispose()
app = FastAPI(title='R.A.E. Control Plane', version='0.2.0', lifespan=lifespan, docs_url='/api/docs')
app.add_middleware(RequestTelemetry)
if os.getenv('RAE_SESSION_SECRET'):
    app.add_middleware(SessionMiddleware, secret_key=os.environ['RAE_SESSION_SECRET'],
                       session_cookie='rae_oidc_state', max_age=600,
                       https_only=os.getenv('RAE_COOKIE_SECURE', 'true') == 'true')
app.include_router(sso.router)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('ALLOWED_ORIGINS','http://localhost:3000').split(','), allow_methods=['GET','POST','PUT','PATCH','DELETE'], allow_headers=['Authorization','Content-Type'], allow_credentials=True, expose_headers=["X-Request-ID","X-Run-ID"])
app.include_router(registry.router, prefix='/api')
app.include_router(tenants.router, prefix='/api', dependencies=[Depends(current_actor)])
app.include_router(change_requests.router, prefix='/api')
app.include_router(audit.router, prefix='/api')
app.include_router(orchestrations.router)
app.include_router(llm.router)
@app.get('/api/me')
def me(actor: Actor=Depends(current_actor)):
    return {'name':actor.name, 'role':actor.role}
@app.get('/health')
def health():
    healthy = check_db_connection()
    return JSONResponse({'status':'healthy' if healthy else 'degraded','database':'connected' if healthy else 'disconnected','version':'0.2.0'}, status_code=200 if healthy else 503)
@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({'detail':'Resource conflicts with existing data or a required relationship'}, status_code=409)
@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger(__name__).error('Unhandled API exception: %s', type(exc).__name__)
    return JSONResponse({'detail':'Internal server error'}, status_code=500)
