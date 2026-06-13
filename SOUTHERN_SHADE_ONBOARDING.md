# Southern Shade LLC – Tenant Onboarding (R.A.E.)

## 1. Organization profile

- Legal name: Southern Shade LLC  
- Sector: Infrastructure, AI & automation consulting  
- Primary use-cases:
  - AI-assisted sourcing and bidding for public works
  - Marketing and sales automation
  - New product / solution development
- Data sensitivity: High (potential PHI/PII and regulated infrastructure data)

## 2. Roles and people

- CTO / Platform Owner: Leroy Brown
  - Responsibilities: R.A.E. technical owner, kill-switch authority, change governance
- CFO: Chelanda Smith-Brown
  - Responsibilities: Financial approvals, billing, spend controls
- AI Tech Leads: Chefel33 & Fredrick
  - Responsibilities: Agent design, prompts, model selection, tool integrations
- Business Owners: Leroy Brown, Chelanda Smith-Brown
  - Responsibilities: Approve new workflows and autonomy levels

## 3. Initial workflows

### 3.1 Sourcing & Bidding Agents

- Purpose: Scan portals (Beacon, SAM.gov, etc.) for matching solicitations, draft bid outlines.
- Inputs: Solicitation feeds, internal capabilities library, pricing rules.
- Outputs: 
  - Opportunity summaries
  - Draft bid outlines
  - Risk/fit assessment
- Autonomy level: Draft-only, human review required for submission.

### 3.2 Marketing & Sales Agents

- Purpose: Draft outreach emails, website copy, social content, case studies.
- Inputs: Southern Shade positioning, service catalog, brand voice.
- Outputs:
  - Email drafts
  - Landing page copy
  - Campaign concepts
- Autonomy level: Draft-only; publishing requires human approval.

### 3.3 New Product Development Agents

- Purpose: Help design new AI/automation offerings for Southern Shade and clients.
- Inputs: Client problems, existing solutions, market research.
- Outputs:
  - Solution briefs
  - Architecture outlines
  - Experiment backlogs
- Autonomy level: Advisory; cannot touch production infra directly.

## 4. Governance, policies, and gates

- Tenant risk class: High-governance, PHI/PII-capable, default-deny.
- Required controls for all workflows:
  - Identity: All actions tied to a verified human or agent identity.
  - Audit: Every model/agent call must emit an audit event with tenant_id, workflow_id, and tool usage.
  - Change management: Any production change requires a change_request and approval gate.
- Kill-switch policy:
  - Leroy (CTO) can disable any workflow or agent fleet immediately.
  - Break-glass events must log:
    - Who triggered
    - Reason
    - Scope (which workflows/agents)
    - Automatic follow-up review task

## 5. Language model & agent layer (v1)

- Model provider: Free-tier, OpenAI-compatible API (configurable per environment).
- Default model: `general-governed-chat-v1` (placeholder; map to actual model ID in config).
- Agent pattern:
  - Stateless LLM calls via ModelProvider
  - Tools for:
    - Fetching solicitations
    - Reading internal capability docs
    - Creating draft artifacts (bids, emails, briefs)
  - Policy enforcement via R.A.E. gates before any external action (sending, submitting, deploying).

## 6. Tenant configuration (example JSON)

```json
{
  "tenant_id": "southern_shade_llc",
  "name": "Southern Shade LLC",
  "sector": "infrastructure_ai_automation",
  "risk_tier": "high_governance",
  "default_model": "general-governed-chat-v1",
  "owners": ["leroy_brown"],
  "financial_contacts": ["chelanda_smith_brown"],
  "ai_tech_leads": ["chefel33", "fredrick"],
  "workflows": [
    "sourcing_bidding_agents",
    "marketing_sales_agents",
    "new_product_development_agents"
  ]
}
