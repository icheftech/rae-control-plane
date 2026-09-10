# Tenant ownership and execution evidence

The September 10 slice connects the console to tenant-scoped execution evidence.
The navy/cyan dashboard uses real workflow counts, health, risk classifications
and recent runs. Decorative globe, layer illustration and card curves are not
operational telemetry.

## Ownership

Authentication binds each request to an active tenant before resource queries.
Cross-tenant reads and mutations return 404; relationship creation requires
ownership. Policies and global emergency stops apply only within their tenant.
Actor identifiers include the tenant. Legacy change-request actor IDs remain
recognized for separation of duties. Database composite foreign keys reinforce
ownership between existing registry/run resources; this is not PostgreSQL RLS.

Migration `20260910_ownership` assigns preexisting resources to Southern Shade.
It preserves original audit hash values. Tenant administrators manage their own
organization only and cannot provision another tenant or change its key.

## What a run records

Each new run gets a server-generated immutable context containing tenant, actor,
workflow and protected resource scope. Scope currently contains only the workflow.
It does not establish file, patient, inbox or document-level authorization.

Each model authorization captures applicable active policies, stops and workflow
state in one PostgreSQL statement snapshot. The decision evaluates this exact
stored content. A version and SHA-256 digest identify the decision inputs.
Later changes do not rewrite earlier snapshots. Sequential steps can therefore
use different snapshots if policy changes between steps.

Events record run/step starts, authorization and completion outcomes, including
errors and denials. Parent and cause IDs connect these events. The console run
detail shows the context, causal events and expandable policy snapshots.
`set_context` records its fixed runtime authorization rule without a model-policy
snapshot. Raw prompts, responses and email contents are not stored as execution
evidence; administrators must keep policy configuration free of sensitive text.

Database triggers reject updates/deletes to contexts, snapshots and events, and
changes to a run's identity. Privileged database administrators can remove these
triggers. External audit anchoring and immutable external retention are absent.
The legacy audit chain remains global; its verify endpoint checks that chain but
returns only the current tenant's event count and no foreign event details.

## Limits

Older runs show no fabricated context or policy snapshot. Runtime execution
remains sequential; this slice does not implement retries, branching, workers,
crash reconciliation or in-flight cancellation. A crash can leave a pending run.
Authorization is preflight, not continuous enforcement. These tests do not amount
to a production security audit or customer-ready SSO provisioning.

## Verification

`backend/tests/test_execution_boundaries.py` exercises two-tenant isolation,
same-name actor/workflow separation, foreign-tenant stops, snapshot preservation,
causal references and database evidence immutability. The full backend suite
uses migrated temporary PostgreSQL databases.

`scripts/test_local_agent.py` exercises default denial, a real local Ollama
response, emergency-stop denial and audit verification. It cleans up demo
controls while retaining run history. `scripts/verify_dashboard.cjs` uses
Playwright and installed Chrome for local SSO, filtering, timeline and mobile
layout checks; generated credentials and screenshots remain in `local-state`.
