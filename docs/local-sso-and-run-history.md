# Southern Shade local sign-in and execution history

Southern Shade Technologies is the first installation organization. The app now
supports a local Keycloak OIDC provider, with authorization-code flow, PKCE,
validated ID tokens and explicit subject-to-role membership. No paid identity
provider or company domain is needed for this local setup.

## Start locally

From the repository root, with PostgreSQL running and the existing `.env` present:

```sh
.venv312/bin/pip install -r requirements.txt
.venv312/bin/python scripts/setup_local_sso.py
docker compose -f compose.sso.yml up -d
.venv312/bin/python scripts/run_backend.py
```

In a second terminal:

```sh
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 13000
```

Open http://127.0.0.1:13000 and choose **Sign in with Southern Shade SSO**.
The generated username/password are in `local-state/SSO_ACCESS.txt`. All generated
credentials and realm imports stay in the ignored `local-state` directory. The
provisioner reuses existing credentials on subsequent runs. Keycloak persists
its realm in a Docker volume and skips reimporting an existing realm.

The owner account is for local testing. Change its password in Keycloak when
adopting it for ongoing use; the smoke test uses the initially generated password.
The generated bootstrap administrator is separate from the R.A.E. owner.

```sh
.venv312/bin/python scripts/test_local_sso.py
```

This tests actual provider login and token validation, creates a harmless
verification workflow/run, rejects a replayed callback, and verifies logout.
It never prints credentials, authorization codes, or tokens.

## Identity boundaries

This release is **one installation for one organization**. Existing registry,
policy and audit tables still lack tenant isolation. Organization directory rows
do not establish a multi-customer security boundary. Do not onboard another
customer into this same database until every resource and authorization query
is tenant scoped.

`RAE_SSO_MEMBERS` maps provider subject IDs to server-owned names and roles.
Only explicitly listed subjects can sign in. Removing a member or deactivating
the installation tenant blocks their next request. Provider-side disabling alone
does not revoke an already issued R.A.E. session immediately; sessions last eight
hours. Logout revokes the R.A.E. session, but does not sign out the identity
provider. Session cookies are HttpOnly, with opaque random values whose hashes
are stored in PostgreSQL. OIDC tokens are not persisted. Cookie-authenticated
mutations require the configured frontend Origin.

The Keycloak container uses its development configuration and is bound to
loopback only. Production requires HTTPS, Secure cookies, hardened identity
hosting and operational backup procedures. Provider configuration is server-side
in `RAE_OIDC_ISSUER`, `RAE_OIDC_CLIENT_ID`, optional `RAE_OIDC_CLIENT_SECRET`,
`RAE_OIDC_REDIRECT_URI`, `RAE_FRONTEND_URL`, `RAE_SESSION_SECRET` and
`RAE_TENANT_KEY`. Changing providers also requires updating subject memberships.

## Execution history

The new **Orchestration runs** sidebar includes direct model calls. The list shows
workflow, status, start/completion times and planned step count. The detail view
shows attempted steps in order, timings, token counts and denial reasons. A
denial caused by a matching policy or emergency stop includes its ID.

`GET /api/orchestrations/runs` accepts `status`, `workflow_id`, `started_after`,
`started_before`, `limit` (1–100) and `offset`. Use timezone-qualified ISO timestamps.
`GET /api/orchestrations/runs/{run_id}` returns the run and ordered step timeline.
Existing viewer/operator/admin access applies installation-wide.

Run/step states are `pending`, `success`, `error`, `denied`. Start records commit
before work begins. A process crash may leave a run pending; this is not proof
that it remains active. Recovery/reconciliation and retries are future work.
Input/output references are opaque correlation labels, not retrievable stored
content. Prompts, model responses, and email contents are never stored in these
history tables. Old audit-only executions are not backfilled.

JSON telemetry includes server-generated request IDs, route templates, timings,
run/step IDs and outcomes. Request bodies, headers and query strings are omitted.
The local API launcher disables Uvicorn access logging so OIDC callback query
parameters are not written to access logs. Keep the same restriction in a proxy.
`X-Request-ID` correlates handled requests; execution failures also return `X-Run-ID`.

## Service credentials and limits

Legacy `RAE_API_KEYS` remains supported. `RAE_API_KEY_HASHES` alternatively maps
SHA-256 hashes of high-entropy service keys to identities. Each identity supports
`name`, `role`, optional timezone-qualified `expires_at`, and `revoked: true`.
Rotation means adding a new independently generated key and removing/revoking
the old identity; restart after changing environment configuration. Role scopes
remain admin/operator/viewer, with no workflow-specific service scopes yet.

`RAE_REQUESTS_PER_MINUTE` defaults to 120 authenticated requests per actor.
Exceeded limits return HTTP 429 with Retry-After. Buckets are bounded and shared
by keys using the same actor identity, but are local to each API process and
reset on restart. Distributed limits and unauthenticated ingress abuse protection
belong at the deployment gateway before a multi-worker production rollout.

Implementation references: [Authlib Starlette OIDC](https://docs.authlib.org/en/v1.5.0/client/starlette.html)
and [Keycloak containers](https://www.keycloak.org/server/containers).
