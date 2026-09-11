# Durable local worker

The local worker executes installed orchestration definitions independently of
HTTP requests. Closing the browser does not cancel a submitted job. PostgreSQL
stores job metadata; task inputs remain in local files. Outputs are currently
discarded after execution and are not downloadable from the queue.

## Start

Run `scripts/run_backend.py` with the repository virtual environment to apply
migrations and start the API. In a separate terminal at the repository root:

```sh
.venv312/bin/python scripts/run_local_worker.py
```

This loads `.env` and uses its provider configuration. To explicitly use Ollama:

```sh
LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_API_KEY=ollama-local LLM_MODEL=qwen3.5:4b .venv312/bin/python scripts/run_local_worker.py
```

The model must already be installed. No model is needed for a `set_context` task.
`--once` performs recovery, processes at most one queued job, then exits. The
default stays connected and polls every two seconds. Ctrl+C stops the process;
this is a manually started worker, not a login service or scheduled task.

## Install a task

An installation administrator writes a JSON orchestration request under:

```text
local-state/worker-tasks/<tenant UUID>/<task-key>.json
```

Use the tenant UUID from `/api/me`. The API and worker must share the same task
directory; `RAE_LOCAL_TASKS_DIR` can override its root. Keep the directory private
(0700), files private (0600), and out of version control. These files contain
operational inputs and must not contain credentials. The worker supports the
existing `set_context` and `llm_chat` steps; it cannot execute shell commands.

```json
{
  "workflow_id": "REPLACE_WITH_ACTIVE_WORKFLOW_UUID",
  "steps": [
    {"id": "check", "type": "set_context", "value": "Hello from the local worker", "output_key": "result"}
  ]
}
```

In **Orchestration runs → Local worker jobs**, select the workflow and enter the
installed task key. API clients submit `POST /api/local-jobs` with `workflow_id`,
`task_key` and a fresh UUID `idempotency_key`. Reuse that key when retrying the
same submission after a network failure; changing the submission while reusing
the key returns 409. A successful submission returns 202 with its durable job ID.
Tenant operators/admins submit jobs; viewers can inspect their tenant's jobs.

Only task references and SHA-256 hashes enter the queue, not prompts or responses.
Definitions are limited to 256 KiB. A changed definition is rejected at execution;
install the desired version and submit a new job. There is no task-upload API.

## Execution and recovery

One worker per tenant holds a PostgreSQL session advisory lock on a dedicated
connection. Claims commit before execution. Heartbeats update every five seconds;
the UI labels them offline after 30 seconds without a heartbeat. Heartbeat age
alone never permits takeover. A replacement worker must acquire the lock first.

Jobs progress from `queued` to `running`, then `success`, `denied`, `error`, or
`interrupted`. A restart reconciles the previous worker's running jobs: a durable
terminal run is preserved; an incomplete run is marked error with an explicit
`worker_interrupted` evidence event and an interrupted job status. If the worker
died before creating a run, the interrupted job has no run evidence link.

No interrupted job is automatically replayed. An external model request might
have completed even if the worker lost its response. The database lock prevents
concurrent workers during normal operation; it does not promise exactly-once
external effects across network partitions. A lost lock/heartbeat connection
stops new steps, but cannot retract an already sent provider request.

Jobs execute as the installation's `local-worker` service actor. The submitting
actor is retained separately in job metadata and a `LOCAL_JOB_QUEUED` audit event.
This is durable delegation: logging out or rotating the submitting key does not
cancel queued work. Tenant activity is rechecked before execution and each step.
Model calls re-evaluate current policies and emergency stops through the existing
governance path. The worker has local database access and must run under the
trusted installation account.

Scheduling, cancellation controls, automatic retries, remote workers, result
storage and Gmail job integration are later milestones. The Mac, PostgreSQL and
worker must be running; the configured model must be available for model steps.

## Verification

```sh
.venv312/bin/python scripts/test_local_worker.py
```

This creates synthetic local tasks, completes one in a separate process, blocks
a synthetic localhost model response, verifies a heartbeat, kills that worker,
restarts it, proves no replay, and completes a new job. It releases its temporary
allow policy. Demo history and a harmless `local-worker-demo` task remain for
dashboard use. Results and logs stay in ignored `local-state/`.

Run the test before starting a persistent worker for the same tenant: a second
worker is deliberately refused. The test never calls a paid model or reads email.
