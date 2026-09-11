import asyncio
import json
from uuid import UUID, uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.db.models import LocalJob, Workflow, OrchestrationRun, ExecutionEvent, ControlPolicy
from app.db.models.tenant import Tenant
from app.security import Actor
from app.db.models.control_policy import PolicyAction
from app.services.local_tasks import load_task
from app.services.local_worker import LocalWorkerProcess
from app.services.run_history import RunHistory


def install(root, tenant_id, workflow_id, steps=None):
    path = root / str(tenant_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / 'test.json').write_text(json.dumps({'workflow_id':str(workflow_id), 'steps':steps or [
        {'id':'hello', 'type':'set_context', 'value':'private test content', 'output_key':'result'}]}))
    return load_task('test', tenant_id)[1]


def test_submission_idempotency_and_tenant_scope(client, test_db, tmp_path, monkeypatch):
    monkeypatch.setenv('RAE_LOCAL_TASKS_DIR', str(tmp_path))
    tenant_id = UUID(client.get('/api/me').json()['tenant_id'])
    workflow = client.post('/api/workflows', json={'name':'queued', 'version':'1'}).json()
    install(tmp_path, tenant_id, workflow['id'])
    body = {'workflow_id':workflow['id'], 'task_key':'test', 'idempotency_key':str(uuid4())}
    first = client.post('/api/local-jobs', json=body)
    assert first.status_code == 202, first.text
    assert client.post('/api/local-jobs', json=body).json()['id'] == first.json()['id']
    assert 'private test content' not in first.text
    assert len(client.get('/api/local-jobs').json()) == 1
    assert client.post('/api/local-jobs', json=body, headers={'Authorization':'Bearer viewer-key'}).status_code == 403
    assert client.get('/api/local-jobs/workers').json() == []
    assert client.get('/api/local-jobs/'+first.json()['id']).status_code == 200
    changed = dict(body, task_key='../test')
    assert client.post('/api/local-jobs', json=changed).status_code == 422
    install(tmp_path, tenant_id, workflow['id'], [{'id':'changed','type':'set_context','output_key':'x'}])
    assert client.post('/api/local-jobs', json=body).status_code == 409
    foreign = Tenant(tenant_key=str(uuid4()), tenant_name='Other', created_by='tests')
    test_db.add(foreign)
    test_db.commit()
    monkeypatch.setenv('RAE_API_KEYS', json.dumps({'foreign':{'name':'other','role':'admin','tenant_key':foreign.tenant_key}}))
    headers={'Authorization':'Bearer foreign'}
    assert client.get('/api/local-jobs', headers=headers).json() == []
    assert client.get('/api/local-jobs/'+first.json()['id'], headers=headers).status_code == 404
    assert client.post('/api/local-jobs', json=body, headers=headers).status_code == 404


@pytest.fixture
def worker_setup(test_engine, tmp_path, monkeypatch):
    # Real committed sessions are essential to test advisory locks and recovery.
    # Each test owns a unique tenant; the temporary database is discarded afterward.
    monkeypatch.setenv('RAE_LOCAL_TASKS_DIR', str(tmp_path))
    sessions = sessionmaker(bind=test_engine)
    with sessions() as db:
        tenant = Tenant(tenant_key=str(uuid4()), tenant_name='Worker test', created_by='test')
        db.add(tenant)
        db.flush()
        tenant_id = tenant.id
        workflow = Workflow(tenant_id=tenant_id, name='worker-test', version='1')
        db.add(workflow)
        db.commit()
        workflow_id = workflow.id
    provider=AsyncMock()
    provider.default_model='test-model'
    provider.api_key='local-test'
    provider.generate_chat.return_value={'content':'private response', 'usage':{}}
    def enqueue(steps=None):
        digest=install(tmp_path, tenant_id, workflow_id, steps)
        with sessions() as db:
            job=LocalJob(tenant_id=tenant_id,workflow_id=workflow_id,requested_by=uuid4(),
                         idempotency_key=uuid4(),task_key='test',task_hash=digest)
            db.add(job)
            db.commit()
            return job.id
    return sessions, tenant_id, workflow_id, provider, enqueue


def test_worker_claim_completion_lock_and_changed_task(test_engine, worker_setup):
    sessions, tenant, workflow, provider, enqueue = worker_setup
    job_id=enqueue()
    worker=LocalWorkerProcess(test_engine,sessions,tenant,provider)
    worker.start()
    try:
        second=LocalWorkerProcess(test_engine,sessions,tenant,provider)
        with pytest.raises(RuntimeError, match='already owns'):
            second.start()
        assert asyncio.run(worker.run_once())
        assert not asyncio.run(worker.run_once())
        with sessions() as db:
            job=db.get(LocalJob,job_id)
            assert job.status=='success'
            assert db.get(OrchestrationRun,job.run_id).status=='success'
            assert len(db.scalars(select(OrchestrationRun).where(OrchestrationRun.id==job.run_id)).all())==1
        changed_id=enqueue()
        enqueue([{'id':'modified','type':'set_context','output_key':'result'}])
        assert asyncio.run(worker.run_once())
        with sessions() as db:
            assert db.get(LocalJob,changed_id).status=='error'
            assert db.get(LocalJob,changed_id).run_id is None
    finally:
        worker.close()


def test_recovery_never_replays_and_preserves_completed_runs(test_engine, worker_setup):
    sessions, tenant, workflow, provider, enqueue = worker_setup
    pending, completed=enqueue(),enqueue()
    old=LocalWorkerProcess(test_engine,sessions,tenant,provider)
    old.start()
    with old.session() as db:
        for job_id in (pending,completed):
            job=db.get(LocalJob,job_id)
            job.status='running'
            job.worker_id=old.id
            job.run_id=uuid4()
            db.commit()
            history=RunHistory(db,old.actor,workflow,1,run_id=job.run_id)
            history.__enter__()
            if job_id==completed:
                history.__exit__(None,None,None)
    old.close()
    restarted=LocalWorkerProcess(test_engine,sessions,tenant,provider)
    restarted.start()
    try:
        with sessions() as db:
            interrupted=db.get(LocalJob,pending)
            assert interrupted.status=='interrupted'
            assert 'Not replayed' in interrupted.reason
            assert db.get(OrchestrationRun,interrupted.run_id).status=='error'
            assert db.scalar(select(ExecutionEvent).where(ExecutionEvent.run_id==interrupted.run_id,
                ExecutionEvent.event_type=='worker_interrupted')) is not None
            assert db.get(LocalJob,completed).status=='success'
        assert not asyncio.run(restarted.run_once())
        provider.generate_chat.assert_not_called()
    finally:
        restarted.close()


def test_worker_rechecks_model_policy(test_engine, worker_setup):
    sessions, tenant, workflow, provider, enqueue = worker_setup
    steps=[{'id':'model','type':'llm_chat','output_key':'result','messages':[{'role':'user','content':'hello'}]}]
    denied=enqueue(steps)
    worker=LocalWorkerProcess(test_engine,sessions,tenant,provider)
    worker.start()
    try:
        asyncio.run(worker.run_once())
        with sessions() as db:
            assert db.get(LocalJob,denied).status=='denied'
            db.add(ControlPolicy(tenant_id=tenant,workflow_id=workflow,policy_key=str(uuid4()),created_by=str(uuid4()),last_modified_by=str(uuid4()),name='allow',policy_action=PolicyAction.ALLOW,conditions={'model':'test-model'}))
            db.commit()
        allowed=enqueue(steps)
        asyncio.run(worker.run_once())
        with sessions() as db:
            assert db.get(LocalJob,allowed).status=='success'
        provider.generate_chat.assert_awaited_once()
    finally:
        worker.close()
