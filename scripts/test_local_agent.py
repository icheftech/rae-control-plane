"""Run a real Ollama-backed demo through R.A.E.'s API, with durable audit records.

Uses an in-process API client and the local PostgreSQL database. It does not
change the running API's provider configuration or execute agent-proposed actions.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='qwen3.5:4b')
    args = parser.parse_args()
    values = dotenv_values(ROOT / '.env')
    for key, value in values.items():
        if value is not None:
            os.environ.setdefault(key, value)
    os.environ.setdefault('DATABASE_URL', 'postgresql://rae_user:' + values['POSTGRES_PASSWORD'] + '@127.0.0.1:55432/rae_control_plane')
    # Ollama requires no purchased key. This non-secret value satisfies the
    # gateway's configured-provider check; all inference stays on loopback.
    os.environ['LLM_BASE_URL'] = 'http://127.0.0.1:11434/v1'
    os.environ['LLM_API_KEY'] = 'ollama-local'
    os.environ['LLM_MODEL'] = args.model
    os.environ['LLM_TIMEOUT_SECONDS'] = '180'
    os.environ['LLM_REASONING_EFFORT'] = 'none'
    keys = json.loads(os.environ['RAE_API_KEYS'])
    admin_key = next(k for k, v in keys.items() if v['role'] == 'admin')
    agent_key = uuid4().hex
    keys[agent_key] = {'name': 'local-incident-demo-agent', 'role': 'operator'}
    os.environ['RAE_API_KEYS'] = json.dumps(keys)

    from fastapi.testclient import TestClient
    from app.main import app

    results = {'model': args.model, 'provider': 'Ollama on localhost', 'checks': []}
    with TestClient(app, headers={'Authorization': 'Bearer ' + admin_key}) as client:
        def call(method, path, body=None, expected=200, agent=False):
            response = client.request(method, path, json=body,
                headers={'Authorization': 'Bearer ' + (agent_key if agent else admin_key)})
            if response.status_code != expected:
                raise RuntimeError(f'{method} {path}: expected {expected}, got {response.status_code}: {response.text}')
            return response.json() if response.content else None

        workflow = call('POST', '/api/workflows', {
            'name': 'Local incident review demo ' + uuid4().hex[:8],
            'description': 'Synthetic incident triage with a local Ollama model; proposes actions only.',
            'version': '1.0.0', 'risk_level': 'low'}, expected=201)
        results['workflow_id'] = workflow['id']
        policy = stop = None
        try:
            request = {'workflow_id': workflow['id'], 'model': args.model,
                'messages': [{'role': 'user', 'content':
                    'You are a local incident review agent. Synthetic test: a staging API has a 5% error rate after a deployment. No customer data is involved. Propose one next investigation step in one short sentence. Do not execute any action.'}],
                'temperature': 0, 'max_tokens': 256}
            denied = call('POST', '/v1/chat/completions', request, expected=403, agent=True)
            results['checks'].append({'check':'default deny', 'result':'PASS', 'detail':denied['detail']})
            print('PASS: request denied before an allow policy exists', flush=True)
            policy = call('POST', '/api/control-policies', {
                'name':'Local demo model allow', 'workflow_id':workflow['id'],
                'policy_action':'allow', 'conditions':{'model':args.model}}, expected=201)
            print('Running the installed local model through R.A.E.…', flush=True)
            answer = call('POST','/v1/chat/completions',request,agent=True)
            if not answer.get('content', '').strip():
                raise RuntimeError('Model returned no visible answer; increase the generation budget for reasoning models.')
            results['response'] = answer['content']
            results['checks'].append({'check':'governed local inference','result':'PASS', 'event_id':answer['audit_metadata']['event_id']})
            print('PASS: local model replied: ' + answer['content'], flush=True)
            stop = call('POST','/api/kill-switches',{
                'name':'Local demo emergency stop','workflow_id':workflow['id'],
                'reason':'Verify that emergency controls override an allow policy'}, expected=201)
            call('POST',f"/api/kill-switches/{stop['id']}/activate",{'reason':'Local smoke test'})
            blocked = call('POST','/v1/chat/completions',request,expected=403,agent=True)
            if blocked['detail'] != 'Emergency stop is active':
                raise RuntimeError('Request was blocked for an unexpected reason')
            results['checks'].append({'check':'emergency stop','result':'PASS','detail':blocked['detail']})
            print('PASS: emergency stop blocked the next request', flush=True)
        finally:
            if stop:
                call('POST',f"/api/kill-switches/{stop['id']}/deactivate",{'reason':'Local smoke test finished'})
            if policy:
                call('DELETE',f"/api/control-policies/{policy['id']}",expected=204)
            call('DELETE',f"/api/workflows/{workflow['id']}",expected=204)
        verification = call('GET','/api/audit-events/verify')
        if not verification['valid']:
            raise RuntimeError('Audit chain verification failed')
        results['checks'].append({'check':'audit chain','result':'PASS',**verification})
        results['cleanup'] = 'Demo workflow and allow policy deactivated; emergency stop released. Audit records retained.'
    output = ROOT / 'local-agent-test-results.json'
    output.write_text(json.dumps(results, indent=2)+'\n')
    print('PASS: audit chain verified; demo controls cleaned up', flush=True)
    print('Results saved to local-agent-test-results.json', flush=True)


if __name__ == '__main__':
    main()
