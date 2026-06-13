# 🔒 R.A.E. CONTROL PLANE — AGENT IMPLEMENTATION NOTES

**Read this entire document before writing any code.**
This system is a **real-world enterprise platform**, not a demo, tutorial, or class project.

## 0. Mission Context

You are implementing the **R.A.E. (Runtime Authority Engine)** control plane for **Southern Shade Technologies (SST)**.

R.A.E. is a **governed autonomy platform** designed for:
- Regulated enterprises
- Government, healthcare, finance
- Environments handling PHI/PII
- High-risk automated changes

The platform **does NOT allow agents to execute actions directly**.
Agents may **propose actions only**.
All execution is gated by **registry, policy, kill-switch, and audit layers**.

## 1. Architectural Non-Negotiables

### Control Philosophy (DO NOT VIOLATE)
- **Prevent bad actions at runtime**
- **Produce cryptographic evidence that prevention occurred**
- **Everything is enforceable, versioned, and auditable**
- **No silent failures**
- **No bypass paths**

### What This Is NOT
- ❌ Not a microservice explosion
- ❌ Not event sourcing for fun
- ❌ Not "best effort" security
- ❌ Not agent-trust based
- ❌ Not "admin can do anything"

Admins **cannot** bypass HARD_STOP kill switches.

## 2. Golden Path

The **first and only flagship workflow** for this phase is:

> **Production Change Management (Golden Path)**

Examples:
- Prod config update
- System-of-record update
- IAM permission change
- Deployment flag toggle

```
workflow_key = "PROD_CHANGE_GOLDEN_PATH"
```

## 3. Implementation Order (IMPORTANT)

You MUST implement in this order:

### Phase 1 — Registry Backbone (MAP)
1. Registry models
2. Registry migrations
3. Registry APIs (read/write)
4. Registry change log (hash-chained)
5. Registry gates (NO execution yet)
6. Seed Golden Path data

### Phase 2 — Controls (MANAGE)
7. Kill switch models
8. Kill switch APIs
9. Break-glass models
10. Break-glass APIs
11. Runtime enforcement (kill switch FIRST)
12. Mandatory post-incident review linkage

### Phase 3 — Enforcement Integration
13. Wire gates into `capability_executor`
14. HARD_STOP vs DEGRADE behavior
15. Audit events for every deny

### Phase 4 — Proof
16. Smoke test script that demonstrates:
    - Kill switch creation
    - Denied execution
    - Audit evidence produced

## 4. File Structure (STRICT)

```
backend/
  app/
    api/v1/
      routes_registry.py
      routes_controls.py
    controls/
      service.py
    core/
      oidc_entra.py  # stub allowed for local dev ONLY
      rbac.py
    db/
      models_registry.py
      models_controls.py
      migrations/
        versions/
          0001_registry_init.py
          0003_controls.py
    orchestration/
      capability_executor.py
      audit_chain.py
    registry/
      change_log.py
      gates.py
      seed_golden_path.py
    scripts/
      smoke_controls.py
    main.py
```

## 5. Kill Switches — Critical Safety Brake

### Kill Switch Scope
Kill switches MUST support:
- TENANT
- WORKFLOW
- CAPABILITY
- CONNECTOR

### Kill Switch Effects
Two effects only:
- `HARD_STOP` → execution denied, cannot be bypassed
- `DEGRADE` → execution suppressed / read-only

Default = HARD_STOP.

### Enforcement Rule (NON-NEGOTIABLE)
Kill switches are checked **BEFORE**:
- Registry checks
- Policy checks
- Approvals
- Execution

Order:
```
Kill Switch → Registry → Policy → Approval → Execution
```

## 6. Break-Glass (Emergency Access)

Every break-glass grant MUST:
- Be time-bounded (minutes, not days)
- Have a reason
- Be scoped (workflow/capability/connector/system)
- Generate a registry change event
- Require post-incident review

## 7. Audit & Evidence Rules

### Registry Change Log
All registry and control actions must:
- Include `prev_hash`
- Compute `event_hash`
- Be append-only

### Capability Execution Audit
On any deny (kill switch or registry):
- Emit audit event
- Include reason
- Include scope
- Include workflow_key, capability, connector

## 8. Acceptance Criteria

The implementation is **NOT ACCEPTED** unless all are true:
- `alembic upgrade head` succeeds
- FastAPI app starts without errors
- Kill switch hard-stops execution
- Break-glass expires automatically
- Registry change log is hash-chained
- Smoke test demonstrates enforcement

## 9. Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2
- **Database**: PostgreSQL 16 (RDS)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Task Queue**: Celery + Redis
- **Auth**: Microsoft Entra ID (OIDC)
- **Cloud**: AWS (ECS Fargate pilot)

## 10. Final Warning

Do **not**:
- Invent shortcuts
- Loosen security "for now"
- Bypass kill switches
- Skip audit events
- Refactor without instruction

This system is designed to pass:
- Security review
- Compliance audit  
- Procurement evaluation

Build it like it will be attacked — because it will.
