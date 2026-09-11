"""One local worker per tenant, with durable claims and conservative recovery.

The session advisory lock is held on a dedicated connection across commits.
Losing that connection stops this worker; interrupted jobs are never reclaimed.
"""
import asyncio
import hashlib
import threading
from uuid import uuid4
from sqlalchemy import select, text, update
from fastapi import HTTPException
from app.db.models import LocalJob, LocalWorker, OrchestrationRun, OrchestrationRunEvent, ExecutionEvent
from app.db.models.tenant import Tenant
from app.db.models.orchestration_run import now
from app.security import Actor
from app.services.tenancy import scoped
from app.services.local_tasks import load_task
from app.services.orchestration import OrchestrationRunner
from app.services.evidence import record


class LocalWorkerProcess:
    def __init__(self, engine, sessions, tenant_id, provider):
        self.engine, self.sessions, self.tenant_id, self.provider = engine, sessions, tenant_id, provider
        self.id = uuid4()
        self.actor = Actor('local-worker', 'operator', tenant_id=tenant_id)
        self.lock_key = int.from_bytes(hashlib.sha256(('rae-worker:'+str(tenant_id)).encode()).digest()[:8], 'big', signed=True)
        self.lock = None
        self.stop_heartbeat = threading.Event()
        self.heartbeat_failed = threading.Event()
        self.thread = None

    def session(self):
        db = self.sessions()
        db.info['tenant_id'] = self.tenant_id
        return db

    def start(self):
        self.lock = self.engine.connect()
        locked = self.lock.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key':self.lock_key})
        if not locked:
            self.lock.close()
            self.lock = None
            raise RuntimeError('Another worker already owns this tenant')
        self.pid = self.lock.scalar(text('SELECT pg_backend_pid()'))
        self.lock.commit()
        try:
            self.guard()
            self.recover()
            with self.session() as db:
                db.add(LocalWorker(id=self.id, tenant_id=self.tenant_id))
                db.commit()
            self.thread = threading.Thread(target=self._heartbeat, daemon=True)
            self.thread.start()
        except BaseException:
            self.close()
            raise

    def guard(self):
        if self.heartbeat_failed.is_set() or self.lock is None or self.lock.invalidated:
            raise RuntimeError('Worker database connection lost')
        if self.lock.scalar(text('SELECT pg_backend_pid()')) != self.pid:
            raise RuntimeError('Worker lock connection changed')
        self.lock.commit()
        with self.session() as db:
            tenant = db.get(Tenant, self.tenant_id)
            if tenant is None or not tenant.is_active:
                raise HTTPException(403, 'Worker tenant is inactive')

    def _heartbeat(self):
        while not self.stop_heartbeat.wait(5):
            try:
                with self.session() as db:
                    db.execute(update(LocalWorker).where(LocalWorker.id == self.id).values(heartbeat_at=now()))
                    db.commit()
            except Exception:
                self.heartbeat_failed.set()
                return

    def recover(self):
        # Only call while holding the exclusive tenant lock. Heartbeat age alone
        # is never evidence that another worker has stopped executing.
        self.guard()
        with self.session() as db:
            jobs = db.scalars(scoped(db, LocalJob).where(LocalJob.status == 'running').with_for_update()).all()
            for job in jobs:
                run = db.scalar(scoped(db, OrchestrationRun).where(OrchestrationRun.id == job.run_id)) if job.run_id else None
                if run and run.status != 'pending':
                    job.status, job.reason = run.status, run.decision_reason
                else:
                    job.status = 'interrupted'
                    job.reason = 'Worker stopped before completion was recorded; execution outcome may be unknown. Not replayed.'
                    if run:
                        events = db.scalars(scoped(db, ExecutionEvent).where(ExecutionEvent.run_id == run.id).order_by(ExecutionEvent.created_at, ExecutionEvent.id)).all()
                        db.info['execution'] = {'run_id':run.id, 'context_id':run.context_id, 'actor_id':run.actor_id,
                            'root':events[0].id if events else None, 'last':events[-1].id if events else None}
                        record(db, 'worker_interrupted', 'error', {'reason':job.reason, 'worker_id':str(job.worker_id)})
                        db.info.pop('execution', None)
                        run.status, run.decision_reason, run.completed_at = 'error', job.reason, now()
                        db.execute(update(OrchestrationRunEvent).where(OrchestrationRunEvent.run_id == run.id,
                            OrchestrationRunEvent.tenant_id == self.tenant_id, OrchestrationRunEvent.status == 'pending').values(
                                status='error', decision_reason=job.reason, completed_at=now()))
                job.completed_at = now()
            db.execute(update(LocalWorker).where(LocalWorker.tenant_id == self.tenant_id,
                LocalWorker.stopped_at == None).values(stopped_at=now()))
            db.commit()

    async def run_once(self):
        self.guard()
        with self.session() as db:
            job = db.scalar(scoped(db, LocalJob).where(LocalJob.status == 'queued').order_by(
                LocalJob.created_at, LocalJob.id).with_for_update(skip_locked=True).limit(1))
            if job is None:
                return False
            job.status, job.worker_id, job.started_at = 'running', self.id, now()
            db.commit()
            try:
                request, digest = load_task(job.task_key, self.tenant_id)
                if request.workflow_id != job.workflow_id or digest != job.task_hash:
                    raise HTTPException(409, 'Local task changed after submission; submit a new job')
                self.guard()
                job.run_id = uuid4()
                db.commit()
                await OrchestrationRunner(db, self.actor, self.provider).run(request, run_id=job.run_id, before_step=self.guard)
                job.status = 'success'
            except Exception as exc:
                db.rollback()
                # Preserve a terminal run if completion committed just before a
                # failure updating the job; otherwise report uncertainty later.
                if self.lock.invalidated or self.heartbeat_failed.is_set():
                    raise RuntimeError('Worker lost database connection') from None
                run = db.scalar(scoped(db, OrchestrationRun).where(OrchestrationRun.id == job.run_id)) if job.run_id else None
                if run and run.status != 'pending':
                    job.status, job.reason = run.status, run.decision_reason
                elif run:
                    raise RuntimeError('Run remains pending; restart worker to reconcile') from None
                else:
                    job.run_id = None
                    job.status = 'denied' if isinstance(exc, HTTPException) and exc.status_code == 403 else 'error'
                    job.reason = str(exc.detail)[:500] if isinstance(exc, HTTPException) else 'Local job failed before execution'
            job.completed_at = now()
            db.commit()
            return True

    async def serve(self):
        while True:
            if not await self.run_once():
                await asyncio.sleep(2)

    def close(self):
        self.stop_heartbeat.set()
        if self.thread:
            self.thread.join(timeout=6)
        try:
            with self.session() as db:
                db.execute(update(LocalWorker).where(LocalWorker.id == self.id).values(stopped_at=now()))
                db.commit()
        finally:
            if self.lock is not None:
                try:
                    if not self.lock.invalidated:
                        self.lock.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':self.lock_key})
                        self.lock.commit()
                finally:
                    self.lock.close()
                    self.lock = None
