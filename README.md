# R.A.E. Control Plane

A local, single-installation AI governance prototype built with FastAPI, PostgreSQL, and Next.js.

## Working features

- Southern Shade local SSO and content-free orchestration timelines: [setup and boundaries](docs/local-sso-and-run-history.md).
- Structured request/step telemetry, per-actor local rate limits, and optional hashed service keys with expiry/revocation.

- Authenticated operator console with administrator, operator, and viewer API keys.
- Workflow registry and API-level capability/connector registration.
- Global and workflow-scoped policies and emergency stops.
- Model gateway: checks active stops and workflow registration, denies by default, requires a matching allow policy, and persists preflight and completion events.
- Change tracking with separate requester, reviewer, and approver identities.
- Transactional SHA-256 audit chain with serialized appends and integrity verification.

The console displays real database records, including empty and error states. No cloud deployment is configured.

## Local setup

Requires Python 3.11 or 3.12, Node 20.9+, and Docker Desktop.

1. Copy `.env.example` to `.env`; set a random database password and API keys. Do not commit credentials.
2. Run `docker compose up -d postgres` from this directory. PostgreSQL is bound to `127.0.0.1:55432`.
3. Create a virtual environment and install `requirements.txt`.
4. Run `python scripts/run_backend.py` with that environment. It applies migrations and serves the API at `http://127.0.0.1:18000`.
5. In `frontend`, run `npm ci`, then `API_URL=http://127.0.0.1:18000 npm run dev -- --hostname 127.0.0.1 --port 13000`.
6. Open `http://127.0.0.1:13000` and enter your configured API key.

For the prepared workspace, `.venv312` contains the installed Python dependencies and `LOCAL_ACCESS.txt` contains the generated local administrator key. Both are ignored by Git. The key is held only in browser memory.

For a containerized API, run `docker compose up --build -d` and set the frontend's `API_URL` to `http://127.0.0.1:8000`. The image applies migrations before starting. Redis and Celery have been removed from Compose because no worker implementation exists.

## API

Interactive documentation: `http://127.0.0.1:18000/api/docs`.
All data endpoints require `Authorization: Bearer <key>`. Health is public.

- `/api/me`
- `/api/workflows`
- `/api/capabilities`
- `/api/connectors`
- `/api/control-policies`
- `/api/kill-switches`
- `/api/change-requests`
- `/api/orchestrations/runs`
- `/api/audit-events` and `/api/audit-events/verify`
- `/api/tenants/` (current tenant administration; provisioning is installation-managed)
- `/v1/chat/completions`

Registry lists return arrays; request bodies use the model fields documented by OpenAPI. This replaces the disconnected `/api/v1/registry/*` frontend contract in the original archive.

### Model execution

Configure `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. Register a workflow and create an allow policy for its intended model. Send a `workflow_id` and `messages` to `/v1/chat/completions`. There is no unauthenticated execution mode.

Conditions use exact equality on `model`, `workflow_id`, and `operation` (`chat_completion`). All standard conditions must match; any matching auto-deny condition blocks. Any applicable deny, review, or degrade policy overrides allow. All active stop modes block new model calls. No policies means no execution. Prompt and response text are not stored in the audit trail.

### Orchestration

`POST /api/orchestrations/runs` executes a registered workflow as ordered steps. The first runtime supports:

- `set_context`: copies a literal value or input value into the run context.
- `llm_chat`: renders message templates from context, checks policies and kill switches, calls the configured OpenAI-compatible model provider, and records redacted audit events.

Example request:

```json
{
  "workflow_id": "00000000-0000-0000-0000-000000000000",
  "inputs": { "goal": "check personal Gmail safely" },
  "steps": [
    { "id": "capture_goal", "type": "set_context", "input_key": "goal", "output_key": "task" },
    {
      "id": "plan",
      "type": "llm_chat",
      "output_key": "plan",
      "messages": [{ "role": "user", "content": "Plan this workflow: {{task}}" }]
    }
  ]
}
```

Audit records include run ids, step ids, model names, decisions, and token usage. Prompt and response content stay out of the audit trail.

### Change review

Draft → under review → pending approval → approved. Review and approval require distinct administrators, separate from the requester. Configure multiple independently held keys to exercise the full flow. This tracks decisions; it does not deploy changes or execute rollback procedures.

## Validation

The optional [durable local worker](docs/local-worker.md) adds a persistent job
queue, worker heartbeats and conservative restart recovery. Use **Orchestration
runs → Local worker jobs** to submit installed local tasks and inspect outcomes.

From `backend`, with the virtual environment active and Docker running:

```sh
python -m pytest
```

Tests create a temporary PostgreSQL container, apply real Alembic migrations, and isolate each test with a savepoint. The required 80% coverage threshold is retained.

From `frontend`:

```sh
npm run lint
npm run type-check
npm run build
```

## Scope and limitations

This is a local prototype, not a compliance certification. Registry resources, policies, emergency stops, change requests, audit queries and runs now enforce tenant ownership in API queries. Database constraints reject cross-tenant links between existing owned resources. Southern Shade Technologies owns the migrated installation data. Local Keycloak sign-in remains configured for this installation tenant; customer enrollment and multiple SSO providers are not implemented.

Audit events are append-only through the API and hash-linked, but database administrators can alter records or rewrite the chain. External anchoring, database-level immutable retention, and tamper alerts remain future work. The execution gate is a preflight check, not continuous enforcement of a request already sent to a provider.

New runs record immutable execution identity, causal events and the policy inputs evaluated at each model decision. Database triggers reject updates/deletes to this evidence, but privileged database administrators can remove those protections. Resource scope currently identifies the workflow, not individual files, patients or email messages. See [execution evidence](docs/execution-evidence.md) for precise guarantees and limitations.

Keep this build local. Production identity hosting, secret management, dependency hardening, distributed rate limiting and operational monitoring remain work. Break-glass execution, automatic rollback and in-flight model cancellation are not implemented. Connector config must contain non-secret values or secret references, never credentials.

Earlier roadmap, strategy, and handoff documents describe planned or historical behavior; this README documents the implemented v0.2 surface.

## Test the installed local model

With Ollama running and `qwen3.5:4b` installed, run:

```sh
.venv312/bin/python scripts/test_local_agent.py
```

This small demo agent submits a synthetic incident for investigation advice. It exercises the actual R.A.E. API handlers against local PostgreSQL, using an in-process client and Ollama on loopback. No paid provider key is needed and no proposed action is executed.

The script verifies default denial, permits one workflow/model combination, obtains a real model response, activates a workflow-scoped emergency stop, checks that another request is denied, and verifies the audit chain. It releases the stop and deactivates its demo workflow/policy afterward. Audit records remain visible in the console; the result is saved in `local-agent-test-results.json`.

This does not reconfigure the running server or govern other agents automatically. An external agent must route its calls through R.A.E.'s model gateway or orchestration endpoint to be governed.

The local demo sets `LLM_TIMEOUT_SECONDS=180` and `LLM_REASONING_EFFORT=none` for its process only. The normal provider timeout remains 60 seconds. Reasoning control follows [Ollama’s OpenAI compatibility documentation](https://docs.ollama.com/api/openai-compatibility).

## Gmail read-only workflow

This local workflow reads Gmail message headers and short snippets, asks the
locally installed model for a triage summary through R.A.E., and prints the
result. It cannot send, delete, archive, label, download attachments, or act on
text within messages. The Gmail API client uses the narrow
`gmail.readonly` scope and saves the OAuth token only under `local-state/`,
which is ignored by Git.

### One-time Google setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project
   such as `RAE Local Gmail` and enable **Gmail API**.
2. Under **Google Auth platform**, configure the consent screen as **External**.
   Keep the app in testing and add your own Gmail address as a test user.
3. Under **Data Access**, add only the Gmail read-only scope.
4. Under **Clients**, create an OAuth client of type **Desktop app** and download
   its JSON credential. This desktop client has no browser redirect URI to add.
5. Create `local-state/` in this project and save that downloaded file as
   `local-state/gmail-oauth-client.json`. Do not send or commit it.

Google's current [Gmail Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
uses this same Desktop OAuth flow and read-only scope.

### Provision and run

First set the local provider variables in `.env` and restart the API:

```sh
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=ollama-local
LLM_MODEL=qwen3.5:4b
LLM_TIMEOUT_SECONDS=180
LLM_REASONING_EFFORT=none
```

Install the added requirements, run `scripts/provision_gmail_readonly_workflow.py`
once, copy its four printed `RAE_*` values into `.env`, and restart the API again.
Then run:

```sh
.venv312/bin/python scripts/gmail_readonly_agent.py
```

The first run opens Google's consent page. Sign in only to the personal Gmail
account you want to authorize and approve the read-only scope. Future runs reuse
the local refresh token. Use `--query` and `--max-messages` to narrow the Gmail
search, for example `--query 'is:unread newer_than:2d' --max-messages 5`.
