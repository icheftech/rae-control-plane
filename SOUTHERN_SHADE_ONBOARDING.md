# Southern Shade LLC – Tenant Onboarding (R.A.E.)

## AGENT INSTRUCTIONS - READ THIS FIRST

This is a **REAL-WORLD ENTERPRISE SYSTEM**, not coursework or a demo. You are building production-grade software for regulated industries (government, healthcare) that will handle PHI/PII data. Every component must be:

- **Production-ready**: Can handle heavy workloads
- **Compliant**: NIST AI RMF, HIPAA, FedRAMP, SOC 2 aligned
- **Secure**: Cryptographic audit trails, zero-trust architecture
- **Professional**: Enterprise-grade code quality and documentation

- CTO / Platform Owner: Leroy Brown
  - Responsibilities: R.A.E. technical owner, kill-switch authority, change governance
- CFO: Chelanda Smith-Brown
  - Responsibilities: Financial approvals, billing, spend controls
- AI Tech Leads: Chefel33 & Fredrick
  - Responsibilities: Agent design, prompts, model selection, tool integrations
- Business Owners: Leroy Brown, Chelanda Smith-Brown
  - Responsibilities: Approve new workflows and autonomy levels

---

## EXECUTIVE SUMMARY

### What is S.S.O.?

**Southern Shade Orchestrator (S.S.O.)** is a patent-pending platform that enables AI agents to operate across any cloud infrastructure while maintaining cryptographically verifiable audit trails and human control. It delivers "governed autonomy" for regulated industries.

**Simple explanation (for non-technical stakeholders):**
S.S.O. is a control system that lets AI helpers do work across different computer systems (like Amazon, Microsoft, Google clouds) while keeping humans in charge of important decisions and creating permanent records of everything that happens - like a security camera and supervisor combined into one.

### Business Model

S.S.O. is a **platform and service offering**, NOT a resale product. Revenue streams:

1. **Professional Services** - Custom implementation and integration
2. **Managed Services** - 24/7 monitoring, maintenance, optimization
3. **Platform Deployments** - Turnkey installations (cloud/hybrid/on-premises)
4. **Architecture & Governance** - Strategic oversight and compliance consulting

### Company Information

**Southern Shade LLC**
- **SAM.gov Registered Entity** (All procurement under southernshade.co)
- **Location**: Texas, United States
- **Contact**: contact@southernshade.com
- **Domains**: 
  - southernshade.co (SAM.gov registration)
  - southernshadellc.com (to be acquired and linked)

- Model provider: Free-tier, OpenAI-compatible API (configurable per environment).
- Default model: `general-governed-chat-v1` (placeholder; map to actual model ID in config).
- Agent pattern:
  - Stateless LLM calls via ModelProvider
  - Tools for:
    - Fetching solicitations
    - Reading internal capability docs
    - Creating draft artifacts (bids, emails, briefs)
  - Policy enforcement via R.A.E. gates before any external action (sending, submitting, deploying).

---

## TECHNICAL ARCHITECTURE DECISIONS (LOCKED)

### 1. First Workflow to Ship
**DECISION**: Production change management with human-in-the-loop approval

**Why**: This showcases S.S.O.'s core value proposition:
- Governed autonomy
- Human approval gates
- Full cryptographic audit trails
- Cross-cloud agent orchestration

**What it does**: An AI agent proposes a change (update record, approve transaction, deploy code), S.S.O. enforces human approval + cryptographic audit before committing.

### 2. Cloud Platform for Pilot
**DECISION**: AWS (Amazon Web Services)

**Why**:
- Mature agent backends (Bedrock, ECS/EKS, Lambda)
- Strong multi-account, private networking patterns
- HIPAA-eligible services
- Future GovCloud support
- Easy S.S.O. central control plane hosting (EKS)

### 3. Authentication
**DECISION**: Microsoft Entra ID (formerly Azure AD) as primary

**Why**:
- Enterprise buyers in regulated industries standardize on Microsoft
- Provides: SSO, conditional access, MFA, group/role-based access
- Fallback email/password can be added later

### 4. Data Sensitivity
**DECISION**: Assume YES - touching PHI/PII in pilot

**Why**:
- Forces proper architecture from day one (encryption, RBAC, logging, data minimization)
- Avoids redesign later
- Can start with de-identified test data operationally, but contracts/controls are PHI/PII-grade

### 5. Technology Stack

**Backend**:
- Python 3.11+
- FastAPI (REST API)
- PostgreSQL 15+ (data persistence)
- Redis (caching, session management)
- SQLAlchemy (ORM)
- Alembic (database migrations)

**Frontend**:
- React with TypeScript
- Next.js framework
- Tailwind CSS
- shadcn/ui components

**Infrastructure**:
- AWS EKS (Kubernetes)
- Docker containers
- GitHub Actions (CI/CD)

**Blockchain/Audit**:
- SHA-256 hash-chained audit logs (immutable ledger)
- OpenTelemetry for observability (logs, traces, metrics)

---

## NIST AI RISK MANAGEMENT FRAMEWORK ALIGNMENT

S.S.O. implements all four NIST AI RMF functions as a closed loop:

### 1. GOVERN
**What**: Define policies, ownership, and decision authority

**S.S.O. Components**:
- `ControlPolicy` model - governance rules
- `PolicyPack` - signed, versioned policy bundles
- Risk tier definitions (LOW, MEDIUM, HIGH, CRITICAL)
- System registry - inventory of workflows, agents, tools, connectors

### 2. MAP
**What**: Identify context, capabilities, and risks

**S.S.O. Components**:
- `Workflow` model - AI agent task definitions
- `Capability` model - granular permissions (API calls, DB access, file ops)
- `Connector` model - external system integrations
- Risk level assignment per workflow

### 3. MEASURE
**What**: Test, assess, and track performance

**S.S.O. Components**:
- `AuditEvent` model - cryptographic event log (SHA-256 hash chain)
- `GateExecution` model - performance metrics per policy checkpoint
- OpenTelemetry traces - real-time observability
- Continuous monitoring dashboard

### 4. MANAGE
**What**: Operate, respond to incidents, maintain controls

**S.S.O. Components**:
- `EnforcementGate` model - policy checkpoints
- `KillSwitch` model - emergency stops (GLOBAL, WORKFLOW, CAPABILITY scopes)
- `BreakGlass` model - time-bounded emergency access
- `ChangeRequest` model - production change governance (FLAGSHIP)

---

## SECURITY & COMPLIANCE REQUIREMENTS

### OWASP LLM Top 10 Mitigations

**Excessive Agency** (LLM08):
- ✅ Agents can only PROPOSE actions, never execute directly
- ✅ Workflow engine + policy layer authorizes execution
- ✅ Non-bypassable rule - codify in architecture

**Insecure Plugin Design** (LLM07):
- ✅ Tool sandboxing - every capability call is scoped, authenticated, rate-limited
- ✅ Treat all tool inputs as hostile
- ✅ Least-privilege retrieval

**Sensitive Information Disclosure** (LLM06):
- ✅ Output redaction filters
- ✅ Data-loss guards
- ✅ Field-level encryption for PHI/PII

### Audit Trail Requirements

**Cryptographic Ledger**:
- SHA-256 hash chain (each event includes hash of previous event)
- Immutable append-only log
- Tamper-evident (chain breaks if any event modified)

**OpenTelemetry Integration**:
- Correlation IDs: `workflow_run_id`, `policy_version`, `approval_id`, `capability_id`, `connector_attempt`
- Emit audit event (ledger) AND ops signal (trace/log/metric) for every state transition
- Real-time operator correlation across services

### Operational Resilience

**Kill Switches** (Priority Implementation):
- Per-tenant toggles
- Per-workflow toggles
- Per-capability toggles
- Per-connector toggles
- Required fields: reason, owner, timestamp, scope
- Runtime enforcement: EVERY execution gate checks kill-switch state FIRST

**Break-Glass Access**:
- Strong authentication required
- Time-bounded privileges (auto-expire)
- Mandatory post-incident review
- Generates records in hash-chained registry log

**Continuous Monitoring**:
- Drift detection
- Anomaly detection
- Policy violations
- "Agent misbehavior" triggers → incident workflows

---

## DATABASE SCHEMA (Already Implemented)

### Phase 1: Registry Backbone (MAP)
```
workflows - AI agent workflows with risk levels
capabilities - Granular permissions 
connectors - External system integrations
```

### Phase 2: Controls (MANAGE)
```
control_policies - Governance rules
kill_switches - Emergency stops
break_glass - Time-bounded emergency access
```

### Phase 3: Enforcement Integration
```
audit_events - SHA-256 hash-chained immutable log
enforcement_gates - Policy checkpoints
gate_executions - Gate execution history with metrics
change_requests - FLAGSHIP: Production change workflow
```

**Status**: ✅ 13 files, 100% Python - COMPLETE

---

## IMPLEMENTATION PHASES

### PHASE 5: Identity Federation (IN PROGRESS)

#### 5.1 Microsoft Entra ID Integration

**What to build**:

1. **Backend OAuth2 Flow** (`backend/app/auth/entra.py`):
```python
# AGENT NOTE: Implement these endpoints
# - /auth/entra/login - Redirect to Microsoft login
# - /auth/entra/callback - Handle OAuth2 callback
# - /auth/entra/token - Exchange code for tokens
# - /auth/entra/refresh - Refresh access tokens
# - /auth/entra/logout - Clear session
```

2. **User Profile Sync** (`backend/app/auth/sync.py`):
```python
# AGENT NOTE: Sync these fields from Entra ID to local DB
# - email, name, groups, roles
# - Map Entra groups to S.S.O. permissions
# - Handle group membership changes
```

3. **Environment Variables** (`.env`):
```bash
# AGENT NOTE: Add these to .env.example and document
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-client-id  
ENTRA_CLIENT_SECRET=your-client-secret
ENTRA_REDIRECT_URI=http://localhost:8000/auth/entra/callback
```

#### 5.2 Fallback Email/Password Auth

**What to build** (`backend/app/auth/local.py`):
- Password hashing (bcrypt)
- Email verification flow
- Password reset flow
- Session management

**AGENT NOTE**: Entra ID is PRIMARY. Email/password is for:
- Demo environments
- Internal development
- Emergency access scenarios

### PHASE 6: Frontend Dashboard (NEXT PRIORITY)

**Tech Stack**: React + TypeScript + Next.js + Tailwind CSS

**Key Pages**:

1. **Login Page** (`/login`):
   - "Sign in with Microsoft" button (primary)
   - Email/password form (secondary)
   - Remember me option
   - Password reset link

2. **Dashboard** (`/dashboard`):
   - Workflow status cards
   - Pending approvals (high priority)
   - Recent audit events
   - System health metrics
   - Kill switch status indicators

3. **Workflows** (`/workflows`):
   - List all workflows (filterable by status, risk level)
   - Create new workflow
   - Edit workflow configuration
   - View workflow execution history

4. **Change Requests** (`/change-requests`):
   - Pending approvals list
   - Approve/reject interface
   - Change history
   - Risk assessment display
   - Audit trail viewer

5. **Audit Log** (`/audit`):
   - Searchable event log
   - Filter by: actor, resource, event type, date range
   - Hash chain verification status
   - Export to CSV/JSON

6. **Settings** (`/settings`):
   - User profile
   - Notification preferences
   - API keys management
   - Kill switches (emergency)

**AGENT NOTE**: Use shadcn/ui components for consistency. All pages must be responsive (mobile-first).

### PHASE 7: Flagship Workflow - Production Change Management

**What to build** (`backend/app/workflows/change_management.py`):

```python
# AGENT NOTE: This is the FLAGSHIP workflow that showcases S.S.O. value

class ChangeManagementWorkflow:
    """
    High-risk production change with multi-stage approval.
    
    Flow:
    1. Agent proposes change (e.g., update database record)
    2. S.S.O. creates ChangeRequest
    3. Risk assessment (auto-calculated)
    4. Route to approver(s) based on risk level:
       - LOW: Auto-approve if policy allows
       - MEDIUM: Single approver
       - HIGH: Two approvers
       - CRITICAL: Three approvers + compliance officer
    5. Upon approval, execute change
    6. Log to cryptographic audit trail
    7. Notify stakeholders
    
    Security:
    - Every step generates audit event
    - Kill switch checked at EVERY gate
    - Break-glass path available (with mandatory review)
    - Full rollback capability
    """
```

**Database Flow**:
```
Agent → ChangeRequest (PENDING)
     → EnforcementGate (PRE_APPROVAL)
     → Approvals (based on risk level)
     → EnforcementGate (PRE_EXECUTION)
     → Execute change
     → EnforcementGate (POST_EXECUTION)
     → ChangeRequest (APPROVED/COMPLETED)
     → AuditEvent (hash-chained)
```

---

## SOUTHERN SHADE TENANT ONBOARDING

### Company Profile
```yaml
tenant_id: southern-shade-llc
name: Southern Shade LLC
industry: Government Contracting, Healthcare
sam_gov_registered: true
compliance_requirements:
  - NIST AI RMF
  - SOC 2
  - HIPAA (future)
  - FedRAMP (future)
domains:
  - southernshade.co
  - southernshadellc.com
```

### Users/Roles
```yaml
users:
  - name: Leroy
    role: CEO / System Owner
    permissions: [ADMIN, APPROVE_HIGH_RISK, BREAK_GLASS]
    
  - name: Chefel33
    role: CTO / Technical Lead
    permissions: [ADMIN, WORKFLOW_DEPLOY, POLICY_CREATE]
    
  - name: Fredrick (AI Agent)
    role: AI Assistant / Agent
    permissions: [WORKFLOW_PROPOSE, AUDIT_READ]
    note: "Can propose changes, cannot approve"
    
  - name: Chelanda
    role: Operations / Compliance
    permissions: [APPROVE_MEDIUM_RISK, AUDIT_REVIEW]
```

### Initial Workflows

**1. GovCon Intel Agent**
```yaml
workflow_key: govcon-intel-agent
name: Government Contracting Intelligence
description: Monitor SAM.gov, analyze opportunities, prepare bid materials
risk_level: MEDIUM
capabilities:
  - web_scraping (SAM.gov)
  - data_analysis
  - document_generation
  - email_notification
approval_required: true (for bid submissions)
```

**2. Production Change Management**
```yaml
workflow_key: prod-change-mgmt
name: Production Change Management
description: Governed production deployments with audit trail
risk_level: HIGH
capabilities:
  - code_deployment
  - database_migration
  - configuration_update
approval_required: true (2 approvers for HIGH risk)
```

**3. Marketing/Sales Automation**
```yaml
workflow_key: marketing-sales-automation
name: Marketing and Sales Automation
description: Content generation, lead scoring, outreach campaigns
risk_level: LOW
capabilities:
  - content_generation
  - email_sending
  - crm_integration
approval_required: false (auto-approve if within guardrails)
```

---

## DEVELOPMENT SETUP INSTRUCTIONS

### Prerequisites
```bash
# AGENT NOTE: Verify these are installed before proceeding
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for frontend)
- Docker & Docker Compose
- Git
```

### Clone Repository
```bash
git clone https://github.com/icheftech/sso-control-plane.git
cd sso-control-plane
```

### Backend Setup
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# AGENT NOTE: Edit .env with actual credentials

# Initialize database
alembic upgrade head

# Seed Southern Shade tenant
python -m app.db.seed_southern_shade

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# AGENT NOTE: Add NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

### Docker Compose (Full Stack)
```bash
# AGENT NOTE: This starts backend, frontend, PostgreSQL, Redis
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

## SEED DATA SCRIPT

**File**: `backend/app/db/seed_southern_shade.py`

```python
# AGENT NOTE: Create this file with the following structure

from app.db.database import SessionLocal
from app.db.models import (
    Workflow, WorkflowStatus, WorkflowRiskLevel,
    Capability, CapabilityType,
    Connector, ConnectorType,
    ControlPolicy, PolicyType,
    KillSwitch, KillSwitchScope, KillSwitchStatus,
    User, UserRole
)

def seed_southern_shade():
    """
    Seed database with Southern Shade LLC tenant data.
    
    This creates:
    - Users (Leroy, Chefel33, Fredrick, Chelanda)
    - Workflows (GovCon Intel, Change Mgmt, Marketing)
    - Capabilities (per workflow)
    - Connectors (SAM.gov, AWS, Email, CRM)
    - Control Policies (approval rules)
    - Kill Switches (emergency controls)
    """
    db = SessionLocal()
    
    try:
        # 1. Create users
        users = create_users(db)
        
        # 2. Create workflows
        workflows = create_workflows(db)
        
        # 3. Create capabilities
        capabilities = create_capabilities(db, workflows)
        
        # 4. Create connectors
        connectors = create_connectors(db)
        
        # 5. Create control policies
        policies = create_control_policies(db, workflows)
        
        # 6. Create kill switches
        kill_switches = create_kill_switches(db, workflows)
        
        db.commit()
        print("✅ Southern Shade tenant seeded successfully")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()

def create_users(db):
    """Create Southern Shade users"""
    # AGENT NOTE: Implement user creation
    pass

def create_workflows(db):
    """Create initial workflows"""
    # AGENT NOTE: Implement workflow creation
    pass

# ... (continue with other creation functions)

if __name__ == "__main__":
    seed_southern_shade()
```

---

## API ENDPOINTS TO IMPLEMENT

### Authentication
```
POST   /auth/entra/login      - Redirect to Microsoft login
GET    /auth/entra/callback   - OAuth2 callback
POST   /auth/entra/refresh    - Refresh token
POST   /auth/logout           - Clear session
POST   /auth/register         - Email/password registration (fallback)
POST   /auth/login            - Email/password login (fallback)
```

### Workflows
```
GET    /workflows             - List all workflows
POST   /workflows             - Create new workflow
GET    /workflows/{id}        - Get workflow details
PUT    /workflows/{id}        - Update workflow
DELETE /workflows/{id}        - Delete workflow (soft delete)
POST   /workflows/{id}/execute - Execute workflow
GET    /workflows/{id}/history - Get execution history
```

### Change Requests (FLAGSHIP)
```
GET    /change-requests                - List pending changes
POST   /change-requests                - Create change request
GET    /change-requests/{id}           - Get change details
PUT    /change-requests/{id}/approve   - Approve change
PUT    /change-requests/{id}/reject    - Reject change
GET    /change-requests/{id}/audit     - Get audit trail for change
```

### Audit Log
```
GET    /audit                 - List audit events (paginated, filterable)
GET    /audit/{id}            - Get specific audit event
POST   /audit/verify          - Verify hash chain integrity
GET    /audit/export          - Export audit log (CSV/JSON)
```

### Kill Switches
```
GET    /kill-switches         - List all kill switches
POST   /kill-switches         - Create kill switch
PUT    /kill-switches/{id}/activate   - Activate kill switch
PUT    /kill-switches/{id}/deactivate - Deactivate kill switch
GET    /kill-switches/status  - Get global system status
```

### Capabilities
```
GET    /capabilities          - List capabilities
POST   /capabilities          - Create capability
GET    /capabilities/{id}     - Get capability details
PUT    /capabilities/{id}     - Update capability
```

### Connectors
```
GET    /connectors            - List connectors
POST   /connectors            - Create connector
GET    /connectors/{id}       - Get connector details
PUT    /connectors/{id}       - Update connector
POST   /connectors/{id}/test  - Test connector connection
```

---

## TESTING REQUIREMENTS

### Unit Tests
```bash
# AGENT NOTE: Use pytest for all tests
pytest tests/unit/

# Coverage report
pytest --cov=app tests/
```

**Required Test Coverage**:
- Models: 90%+
- API endpoints: 80%+
- Auth flows: 95%+
- Audit chain: 100% (critical security component)

### Integration Tests
```bash
pytest tests/integration/

# AGENT NOTE: These test:
# - Database operations
# - API endpoint flows
# - Auth integration
# - Audit chain integrity
```

### End-to-End Tests
```bash
# AGENT NOTE: Use Playwright or Cypress for frontend E2E
npm run test:e2e

# Critical flows to test:
# - Login flow (Entra ID + fallback)
# - Change request creation → approval → execution
# - Kill switch activation
# - Audit log verification
```

---

## DEPLOYMENT CHECKLIST

### Pre-Production
- [ ] All tests passing (unit, integration, E2E)
- [ ] Security audit completed
- [ ] Performance testing (load test with k6 or Locust)
- [ ] Dependency vulnerability scan (Safety, Snyk)
- [ ] Documentation complete (API docs, deployment guide)
- [ ] Backup/restore procedures tested
- [ ] Disaster recovery plan documented

### Production Environment Variables
```bash
# AGENT NOTE: Never commit these to Git
DATABASE_URL=postgresql://user:pass@prod-db:5432/sso
REDIS_URL=redis://prod-redis:6379
SECRET_KEY=<strong-random-key>
ENTRA_TENANT_ID=<your-tenant>
ENTRA_CLIENT_ID=<your-client>
ENTRA_CLIENT_SECRET=<your-secret>
AWS_REGION=us-east-1
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### AWS EKS Deployment
```bash
# AGENT NOTE: Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## NEXT STEPS FOR AGENT

### Immediate Actions (Week 1)

1. **Complete Entra ID Integration**
   - Create `backend/app/auth/entra.py`
   - Implement OAuth2 flow
   - Test with real Microsoft tenant
   - Document setup process

2. **Create Seed Script**
   - Implement `backend/app/db/seed_southern_shade.py`
   - Add all Southern Shade workflows
   - Create test users
   - Run and verify

3. **Build Core API Endpoints**
   - Workflows CRUD
   - Change Requests (FLAGSHIP)
   - Kill Switches
   - Audit Log

### Week 2: Frontend + Testing

4. **Build Frontend Dashboard**
   - Login page (Entra ID + fallback)
   - Dashboard with metrics
   - Change request approval UI
   - Audit log viewer

5. **Write Tests**
   - Unit tests for all models
   - Integration tests for API
   - E2E tests for critical flows

### Week 3: Polish + Pilot Prep

6. **Security Hardening**
   - Input validation
   - Rate limiting
   - CORS configuration
   - Security headers

7. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - Deployment guide
   - User manual
   - Admin guide

8. **Pilot Preparation**
   - Demo environment setup
   - Sample workflows configured
   - Training materials
   - Sales deck

---

## SUCCESS CRITERIA

**By End of Week 3, we must have**:

✅ Working authentication (Entra ID primary)
✅ Change Request workflow (create → approve → execute → audit)
✅ Kill switch functionality (can emergency-stop workflows)
✅ Audit log with hash chain verification
✅ Basic frontend dashboard
✅ API documentation
✅ Deployment to AWS EKS
✅ Demo environment for client presentations

**Ready to offer to first enterprise client** with confidence that the system can handle:
- PHI/PII data securely
- Regulatory compliance requirements
- Production workloads
- 24/7 availability

---

## CONTACT & SUPPORT

For questions during development:
- Technical Lead: Chefel33
- Business Owner: Leroy
- AI Assistant: Fredrick

GitHub Repository: https://github.com/icheftech/sso-control-plane

---

**END OF ONBOARDING DOCUMENT**

*This document is a living artifact and should be updated as the system evolves.*
