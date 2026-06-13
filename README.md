# R.A.E. Control Plane

**Runtime Authority Engine — Enterprise AI Governance Platform**

> R.A.E. is Southern Shade Technologies' flagship AI governance platform: a control plane and Chief Orchestrator system that governs how AI agents operate inside enterprise and federal environments. Agents propose actions only — execution is gated by registry, policy, kill-switch, and audit layers.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Overview

The **R.A.E. (Runtime Authority Engine) Control Plane** is an enterprise-grade governance platform for AI agent systems, designed for regulated industries requiring PHI/PII-grade compliance. R.A.E. operates on two layers: the **control plane** (a structured registry of AI agents, policy controls, enforcement rules, a compliance engine, and identity federation) and the **Chief Orchestrator** (a conversational AI command layer atop the control plane whose own actions appear in the audit chain as a distinct actor type — the governance system is itself governed).

R.A.E. is built on four core tenets: **visibility** (every agent action is logged and traceable), **control** (policies constrain any registered agent in real time), **compliance** (evidence is generated automatically for regulatory frameworks), and **federation** (identity and authority span organizational and agency boundaries without sacrificing auditability).

### Key Features

- **🔒 Enterprise Security**: PHI/PII-grade data handling with cryptographic audit chains
- **📋 Compliance-First**: NIST AI RMF, SOC 2, HIPAA, and ISO 27001 alignment
- **🚨 Emergency Controls**: Kill switches and time-bounded break-glass procedures
- **✅ Change Management**: Multi-stage approval workflows for production changes
- **📊 Audit Trail**: Immutable hash-chained audit logs (SHA-256)
- **🎯 Policy Enforcement**: Real-time control policy evaluation at enforcement gates

---

## 📊 Project Status

**Current Phase:** Phase 5 - Identity Federation (In Progress)

**Completed Phases:**
- ✅ Phase 1: Registry Backbone (NIST AI RMF MAP)
- ✅ Phase 2: Controls Framework (NIST AI RMF MANAGE)
- ✅ Phase 3: Language Model Integration (NIST AI RMF MAP)
- ✅ Phase 4: Compliance Engine (NIST AI RMF GOVERN)

**Upcoming Phases:**
- ⏳ Phase 5: Identity Federation (Q1 2026)
- 📋 Phase 6: AI Model Governance (Q2 2026)
- 📋 Phase 7: Advanced Threat Detection (Q2 2026)
- 📋 Phase 8: Multi-Cloud Integration (Q3 2026)
- 📋 Phase 9: Production Hardening (Q3 2026)

📄 **[View Complete Development Roadmap](PHASES.md)**

---

## 📚 Architecture

### System Components

```
R.A.E. Control Plane
├── Phase 1: Registry Backbone (MAP)
│   ├── Workflows - AI agent task definitions
│   ├── Capabilities - Granular permission system
│   └── Connectors - External system integrations
├── Phase 2: Controls (MANAGE)
│   ├── Control Policies - Governance rules
│   ├── Kill Switches - Emergency stop mechanisms
│   └── Break Glass - Time-bounded emergency access
└── Phase 3: Enforcement Integration
    ├── Audit Events - Cryptographic audit trail
    ├── Enforcement Gates - Policy evaluation checkpoints
    └── Change Requests - Production change governance (FLAGSHIP)
```

### Database Schema

**Phase 1: Registry Backbone** - NIST AI RMF MAP Phase
- `workflows` - AI agent workflows with risk levels and lifecycle management
- `capabilities` - Granular permissions (API calls, database access, file operations)
- `connectors` - External integrations (Slack, JIRA, databases, cloud providers)

**Phase 2: Controls** - NIST AI RMF MANAGE Phase
- `control_policies` - Governance policies (human review, rate limits, data restrictions)
- `kill_switches` - Emergency stops (GLOBAL, WORKFLOW, CAPABILITY scopes)
- `break_glass` - Time-bounded emergency access with mandatory post-incident review

**Phase 3: Enforcement** - Integration & Audit
- `audit_events` - SHA-256 hash-chained immutable audit log
- `enforcement_gates` - Policy checkpoints (PRE_EXECUTION, POST_EXECUTION, etc.)
- `gate_executions` - Gate execution history with performance metrics
- `change_requests` - 🚀 **FLAGSHIP**: Governed production change workflow

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- pip or poetry for dependency management

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/icheftech/rae-control-plane.git
cd rae-control-plane
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure database**
```bash
# Set environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/rae_control_plane"

# Create database
createdb rae_control_plane
```

4. **Initialize database tables**
```python
from app.db.database import init_db
init_db()
```

### Database Configuration

The system uses PostgreSQL with SQLAlchemy ORM:

- **Connection Pool**: 10 base connections, 20 overflow
- **Pool Pre-Ping**: Automatic connection health checks
- **Statement Timeout**: 30 seconds (prevents runaway queries)
- **Pool Recycle**: 1-hour connection lifecycle

---

## 📖 Usage Examples

### Working with Models

```python
from app.db.database import SessionLocal
from app.db.models import Workflow, ControlPolicy, ChangeRequest
from app.db.models import WorkflowStatus, ChangeType, ChangeRiskLevel

# Create a database session
db = SessionLocal()

try:
    # Create a new workflow
    workflow = Workflow(
        workflow_key="acme_invoice_processor",
        name="ACME Invoice Processing",
        description="Automated invoice processing with ML extraction",
        risk_level=WorkflowRiskLevel.MEDIUM,
        status=WorkflowStatus.DRAFT
    )
    db.add(workflow)
    db.commit()
    
    # Create a change request for production deployment
    change_request = ChangeRequest(
        change_key="CHG-2025-001",
        change_type=ChangeType.WORKFLOW_DEPLOYMENT,
        risk_level=ChangeRiskLevel.HIGH,
        title="Deploy ACME Invoice Processor to Production",
        description="Initial production deployment",
        rationale="Business requirement to automate invoice processing",
        requested_by=user_id,
        requested_by_email="[email protected]",
        workflow_id=workflow.id
    )
    db.add(change_request)
    db.commit()
    
finally:
    db.close()
```

### Audit Trail

```python
from app.db.models import AuditEvent

# Create audit event
audit_event = AuditEvent.create_event(
    event_type="WORKFLOW_CREATED",
    action="Created new workflow: ACME Invoice Processor",
    actor_id=user_id,
    actor_type="USER",
    outcome="SUCCESS",
    context={
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request_id
    },
    resource_type="WORKFLOW",
    resource_id=workflow.id,
    previous_hash=last_event.event_hash if last_event else None
)
db.add(audit_event)
db.commit()

# Verify audit chain integrity
is_valid = audit_event.verify_chain(previous_event=last_event)
```

---

## 🏗️ Project Status

### ✅ Completed

- **Phase 1**: Registry Backbone - 4 models (workflow, capability, connector, base)
- **Phase 2**: Controls - 3 models (control_policy, kill_switch, break_glass)
- **Phase 3**: Enforcement - 4 models (audit_event, enforcement_gate, change_request, __init__)
- **Phase 4**: Database configuration and session management

**Total**: 13 files, 100% Python

### 🔄 In Progress

- FastAPI REST API endpoints
- Alembic database migrations
- Seed data for demonstrations
- Unit and integration tests

### 📅 Roadmap

- **Q1 2026**: API development and testing
- **Q2 2026**: Frontend dashboard (React/Next.js)
- **Q3 2026**: Production pilot with enterprise customer
- **Q4 2026**: Public launch

---

## 🎖️ Federal Readiness

R.A.E. is designed as the governance wrapper that makes autonomous AI deployable at scale in federal contexts, including CFIC/ARCYBER "AI Effects at the Edge" missions. It answers the evaluator's hardest questions:

- **Can you prove this agent did what you said it did?** Yes — cryptographic hash-chained audit log, signed per event.
- **Can you shut it down mid-mission?** Yes — kill switches at GLOBAL, WORKFLOW, and CAPABILITY scope, enforced before any policy check.
- **Can you prove policy compliance without manual review?** Yes — the compliance engine generates evidence automatically against NIST AI RMF, SOC 2, HIPAA, and ISO 27001.

---

## 🔒 Compliance & Security

### Framework Alignment

**NIST AI Risk Management Framework (AI RMF)**
- **GOVERN-1.3**: Risk tolerance and decision authority (ChangeRequest)
- **MAP-2.1**: Capability registration and discovery
- **MANAGE-1.1**: Risk-based decision making
- **MANAGE-2.1**: Risk management processes (EnforcementGate)
- **MANAGE-3.2**: Audit trail maintenance (AuditEvent)
- **MANAGE-4.1**: Incident response (KillSwitch, BreakGlass)

**SOC 2 Compliance**
- CC6.1: Logical access controls (ControlPolicy)
- CC7.2: System monitoring and logging (AuditEvent)
- CC8.1: Change management (ChangeRequest)

**HIPAA Compliance**
- §164.308(a)(8): Evaluation of changes (ChangeRequest)
- §164.312(b): Audit controls (AuditEvent)

**ISO 27001**
- A.9.4.1: Information access restriction (EnforcementGate)
- A.12.1.2: Change management (ChangeRequest)
- A.12.4.1: Event logging (AuditEvent)

### Security Features

- **Cryptographic Audit Chain**: SHA-256 hash-chained events prevent tampering
- **Immutable Logs**: Append-only audit events
- **Time-Bounded Access**: Break-glass procedures expire automatically
- **Multi-Stage Approvals**: Risk-based approval requirements
- **Kill Switch Priority**: Emergency stops evaluated FIRST before any policy

---

## 🤝 Contributing

This is a proprietary platform by **Southern Shade Technologies (SST)**. For partnership inquiries:

- **Email**: [email protected]
- **Website**: [southernshade.com](https://southernshade.com)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🏢 About Southern Shade Technologies

**Southern Shade Technologies (SST)** provides enterprise AI governance solutions for regulated industries. Our platform enables organizations to deploy AI agents safely and compliantly while maintaining full audit trails and policy enforcement.

Southern Shade Technologies is the operating brand of Southern Shade LLC (Texas, USA).

### Contact

- **Company**: Southern Shade Technologies (SST)
- **Location**: Texas, USA
- **Focus**: Enterprise AI Governance & Compliance

---

**Built with ❤️ for Enterprise AI Safety**
