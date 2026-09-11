"""Live local worker proof: queue, heartbeat, SIGKILL, restart, no replay.

Uses a synthetic loopback model endpoint, never a paid model or private data.
Leaves an active harmless set_context demo definition for manual dashboard use.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def main():
    values=dotenv_values(ROOT/'.env')
    for key,value in values.items():
        if value is not None:
            os.environ.setdefault(key,value)
    os.environ.setdefault('DATABASE_URL','postgresql://rae_user:'+values['POSTGRES_PASSWORD']+'@127.0.0.1:55432/rae_control_plane')
    sys.path.insert(0,str(ROOT/'backend'))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.database import SessionLocal
    from app.db.models import LocalJob, LocalWorker
    key=next(k for k,v in json.loads(os.environ['RAE_API_KEYS']).items() if v['role']=='admin')
    received=threading.Event()
    release=threading.Event()
    class Stub(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            received.set()
            release.wait(30)
            result=json.dumps({'choices':[{'message':{'content':'Synthetic test result'}}],'usage':{}}).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(result)
            except (BrokenPipeError,ConnectionResetError):
                pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Stub)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    env={**os.environ,'LLM_BASE_URL':f'http://127.0.0.1:{server.server_port}/v1','LLM_API_KEY':'synthetic-local',
         'LLM_MODEL':'worker-recovery-test','LLM_TIMEOUT_SECONDS':'60'}
    state=ROOT/'local-state'
    state.mkdir(exist_ok=True,mode=0o700)
    children=[]
    log=(state/'worker-demo.log').open('w')
    def start():
        child=subprocess.Popen([sys.executable,str(ROOT/'scripts/run_local_worker.py'),'--once'],env=env,stdout=log,stderr=log)
        children.append(child)
        return child
    try:
        with TestClient(app,headers={'Authorization':'Bearer '+key}) as client:
            def call(method,path,body=None,expected=200):
                response=client.request(method,path,json=body)
                if response.status_code!=expected:
                    raise RuntimeError(f'{method} {path} failed: {response.status_code}')
                return response.json() if response.content else None
            tenant=call('GET','/api/me')['tenant_id']
            workflow=call('POST','/api/workflows',{'name':'Local worker recovery demo '+uuid4().hex[:8],'version':'1.0.0'},201)
            policy=call('POST','/api/control-policies',{'name':'Synthetic worker test','workflow_id':workflow['id'],
                'policy_action':'allow','conditions':{'model':'worker-recovery-test'}},201)
            task_dir=Path(os.getenv('RAE_LOCAL_TASKS_DIR',state/'worker-tasks'))/tenant
            task_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
            def install(task_key,steps):
                path=task_dir/(task_key+'.json')
                path.write_text(json.dumps({'workflow_id':workflow['id'],'steps':steps}))
                path.chmod(0o600)
            def enqueue(task_key):
                return call('POST','/api/local-jobs',{'workflow_id':workflow['id'],'task_key':task_key,'idempotency_key':str(uuid4())},202)
            try:
                install('local-worker-demo',[{'id':'check','type':'set_context','value':'Worker executed the synthetic demo','output_key':'result'}])
                success=enqueue('local-worker-demo')
                assert start().wait(timeout=25)==0
                assert call('GET','/api/local-jobs/'+success['id'])['status']=='success'
                print('PASS: queued job completed in a separate worker process',flush=True)
                install('worker-interruption-test',[{'id':'model','type':'llm_chat','output_key':'result',
                    'messages':[{'role':'user','content':'Synthetic worker restart test'}]}])
                pending=enqueue('worker-interruption-test')
                process=start()
                assert received.wait(20),'Worker never reached synthetic model'
                time.sleep(6)
                from uuid import UUID
                with SessionLocal() as db:
                    job=db.get(LocalJob,UUID(pending['id']))
                    worker=db.get(LocalWorker,job.worker_id)
                    assert worker.heartbeat_at>worker.started_at,'No worker heartbeat'
                process.kill()
                process.wait(timeout=10)
                release.set()
                assert start().wait(timeout=25)==0
                interrupted=call('GET','/api/local-jobs/'+pending['id'])
                assert interrupted['status']=='interrupted'
                evidence=call('GET','/api/orchestrations/runs/'+interrupted['run_id'])
                assert any(e['event_type']=='worker_interrupted' for e in evidence['events'])
                print('PASS: heartbeat recorded; SIGKILL detected on restart; job not replayed',flush=True)
                next_job=enqueue('local-worker-demo')
                assert start().wait(timeout=25)==0
                assert call('GET','/api/local-jobs/'+next_job['id'])['status']=='success'
                (state/'worker-demo-results.json').write_text(json.dumps({'workflow_id':workflow['id'],
                    'completed_job':success['id'],'interrupted_job':pending['id'],'post_restart_job':next_job['id'],
                    'task_key':'local-worker-demo','checks':'queue, heartbeat, SIGKILL recovery, no replay, new job success'},indent=2))
                print('PASS: a new job completed after recovery; results saved in local-state/worker-demo-results.json',flush=True)
            finally:
                call('DELETE','/api/control-policies/'+policy['id'],expected=204)
    finally:
        release.set()
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
        server.shutdown()
        log.close()


if __name__=='__main__':
    main()
