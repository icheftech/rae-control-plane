# R.A.E. — Runtime Authority Engine

**Govern AI execution. Retain operational control. Choose your own technology.**

R.A.E. is an AI governance and orchestration platform from **Southern Shade Technologies**, built to address the operational control needs of enterprises and government agencies adopting AI. It brings workflow registration, execution policy, organizational ownership, change review, and execution evidence into a common control plane.

Our direction is a vendor-neutral platform that can support an organization's AI operations across their lifecycle—or integrate at a specific layer of an existing technology stack. Organizations should be able to expand their use of AI without surrendering control of their systems, operating procedures, or provider choices.

## The problem we solve

AI initiatives often introduce agents, models, and automation faster than organizations can establish consistent oversight. Different teams and vendors bring different execution paths, access assumptions, and records of activity. That fragmentation makes fundamental questions difficult to answer:

- Who authorized this workflow, and which organization owns it?
- What was the agent permitted to do at the moment it executed?
- Which policy allowed or denied a model call?
- Can an operator stop further execution when conditions change?
- What completed, what failed, and what remains uncertain after an interruption?
- Can the organization change model providers without rebuilding its governance process?

R.A.E. addresses these questions by placing explicit authority and traceable decisions in the execution path.

## One platform. Two adoption paths.

### Unified AI operations

The platform strategy is to support the full operational lifecycle of AI-enabled work: register workflows and integrations, establish ownership and policy, coordinate execution, review changes, and inspect outcomes through a shared interface.

This approach is intended for organizations seeking a common operating environment across teams and use cases. The current release establishes the registry, governance, sequential orchestration, local execution, and evidence foundations; broader enterprise integration and lifecycle management are being built on that foundation.

### Integration within an existing stack

Organizations can retain their existing applications and agent tooling and route supported model calls through R.A.E.'s governed gateway. They can also invoke its orchestration API or submit installed tasks to its local worker.

Adoption can begin with a defined workflow or model-execution boundary and expand over time. R.A.E. governs the work routed through those boundaries; connecting one layer does not automatically place unrelated systems under its control.

## Vendor-neutral by design

**No vendor lock-in is a core design objective.** Governance should belong to the organization rather than to a particular model vendor, cloud, or agent framework.

The current implementation provides a configurable OpenAI-compatible provider interface, including a tested local Ollama path. Applications integrate through HTTP APIs, and operational records persist in PostgreSQL. Local execution provides a foundation for customer-controlled deployments.

Vendor neutrality is an architectural commitment, not a claim of universal compatibility. Additional provider protocols, enterprise connectors, identity federation options, and deployment targets require implementation and validation. The current release does not require a purchased model-provider key when used with the supported local model configuration.

## Platform capabilities

| Capability | Operational purpose | Available today |
|---|---|---|
| Workflow registry | Establish an inventory of governed work | Workflow records, risk classification, versions, and capability/connector registration |
| Runtime governance | Make execution authority explicit | Default-deny model gateway, matching allow policies, denial reasons, and tenant/workflow-scoped emergency stops |
| Organizational ownership | Separate responsibility and access | Tenant-scoped resource queries, ownership constraints, administrator/operator/viewer roles, and local OIDC sign-in |
| Orchestration | Coordinate governed steps | Sequential context and model-call steps with policy evaluation before model execution |
| Durable local execution | Preserve jobs beyond a browser or API request | Persistent queue, worker ownership, heartbeats, duplicate-submission protection, and conservative restart recovery |
| Execution evidence | Explain what happened and why | Run timelines, actor/context identity, policy snapshots, causal events, and token-usage metadata |
| Change governance | Separate proposal, review, and approval | Change-request lifecycle with distinct requester, reviewer, and approver identities |
| Audit integrity | Support examination of operational records | Hash-linked audit events, integrity verification, and database protections on execution evidence |

## Enterprise and public-sector relevance

R.A.E.'s development priorities are shaped by operational needs that extend beyond model performance:

- **Accountability:** connect execution to an organization, actor, registered workflow, and recorded decision.
- **Controlled adoption:** introduce governed AI at a defined boundary while preserving existing investments.
- **Operational continuity:** distinguish completed work from interrupted or uncertain execution, without silently replaying unfinished jobs.
- **Reviewable evidence:** retain decision metadata without storing raw prompts and responses in run-history or audit records.
- **Customer choice:** support a path toward customer-controlled infrastructure and interchangeable model providers.

These capabilities support governance and assurance activities. They do not, by themselves, establish regulatory compliance, an agency authorization, or suitability for sensitive workloads.

## Release maturity and development direction

The repository contains a working implementation for **local evaluation and integration development**. Production deployment qualification remains ahead of the current release.

The next areas of development include enterprise identity and onboarding, broader connector and provider support, durable result handling, controlled scheduling and retries, finer-grained resource authorization, production operations, and externally anchored audit evidence.

Current boundaries are explicit: governance is a preflight check on supported execution paths; emergency stops do not cancel requests already sent to a provider. Protected resource scope currently identifies workflows. Privileged database administrators can alter database protections. Local worker recovery does not promise exactly-once external effects. Multi-provider enterprise SSO, production cloud deployment, and compliance certification are not delivered by this release.

## Evaluate and integrate

| Resource | Purpose |
|---|---|
| [Evaluation and operations guide](docs/operations-guide.md) | Setup, API contracts, model execution, validation, and reference workflows |
| [Identity and run history](docs/local-sso-and-run-history.md) | Local sign-in, service credentials, roles, and execution visibility |
| [Execution evidence](docs/execution-evidence.md) | Tenant ownership, policy snapshots, evidence protections, and their boundaries |
| [Durable local worker](docs/local-worker.md) | Task installation, queue submission, worker operation, and recovery |
| [CI pipeline](https://github.com/icheftech/rae-control-plane/actions/workflows/ci.yml) | Automated backend and frontend validation |

The implementation uses FastAPI, PostgreSQL, and Next.js. CI exercises real PostgreSQL migrations and backend tests with an 80% minimum application-coverage threshold, plus frontend type checking, linting, and production compilation.

**Southern Shade Technologies · R.A.E. Runtime Authority Engine**
