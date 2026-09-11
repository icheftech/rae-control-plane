"""Run the local worker. No API keys, prompts or model responses are printed."""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Recover old jobs, process one queued job, then exit')
    args = parser.parse_args()
    values = dotenv_values(ROOT / '.env')
    for key, value in values.items():
        if value is not None:
            os.environ.setdefault(key, value)
    os.environ.setdefault('DATABASE_URL', 'postgresql://rae_user:'+values['POSTGRES_PASSWORD']+'@127.0.0.1:55432/rae_control_plane')
    sys.path.insert(0, str(ROOT / 'backend'))
    from sqlalchemy import select
    from app.db.database import engine, SessionLocal
    from app.db.models.tenant import Tenant
    from app.services.tenancy import DEFAULT_TENANT_KEY
    from app.services.local_worker import LocalWorkerProcess
    from app.services.model_provider import ModelProvider
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_key == os.getenv('RAE_TENANT_KEY', DEFAULT_TENANT_KEY), Tenant.is_active == True))
        if not tenant:
            raise RuntimeError('Active installation tenant required')
        tenant_id = tenant.id
    provider = ModelProvider()
    worker = LocalWorkerProcess(engine, SessionLocal, tenant_id, provider)
    try:
        worker.start()
        print('Local worker connected. Ctrl+C to stop.', flush=True)
        if args.once:
            print('Processed one job.' if await worker.run_once() else 'No queued jobs.', flush=True)
        else:
            await worker.serve()
    finally:
        worker.close()
        await provider.close()
        engine.dispose()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Worker stopped. Restart to reconcile unfinished jobs.')
    except Exception as exc:
        print('Worker stopped: '+type(exc).__name__+'. Check database, task installation and tenant configuration.', file=sys.stderr)
        sys.exit(1)
