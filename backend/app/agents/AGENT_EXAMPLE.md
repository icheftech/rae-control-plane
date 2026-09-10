# R.A.E. Agent Implementation Guide

Example implementation showing how to build an R.A.E. workflow agent that uses the ModelProvider.

## Overview

R.A.E. agents are Python classes that:
1. Call the ModelProvider (via `/v1/chat/completions` or direct service import)
2. Tag all LLM calls with `tenant_id` and `workflow_id` for audit trails
3. Check kill-switches and control policies before executing
4. Emit audit events to R.A.E. tables

## Example: Sourcing Agent (Simplified)

```python
from app.services.model_provider import get_model_provider

class SourcingAgent:
    def __init__(self, tenant_id: str = "southern_shade_llc"):
        self.tenant_id = tenant_id
        self.workflow_id = "sourcing_bidding_agents"
        self.model_provider = get_model_provider()
    
    async def analyze_solicitation(self, solicitation_text: str) -> dict:
        """Analyze a solicitation and draft a bid outline."""
        
        # Step 1: Build system prompt based on Southern Shade capabilities
        system_prompt = """
You are a sourcing agent for Southern Shade LLC, an AI & infrastructure consulting firm.
Analyze the solicitation and determine:
1. Relevance score (0-100)
2. Key requirements
3. Draft bid outline
4. Risk factors
"""
        
        # Step 2: Call ModelProvider with governance metadata
        result = await self.model_provider.generate_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Solicitation:\n{solicitation_text}"}
            ],
            model="gpt-4",  # or env-configured model
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            temperature=0.3,  # Lower for factual analysis
        )
        
        # Step 3: Parse response and emit to R.A.E. audit
        return {
            "analysis": result["content"],
            "model_used": result["model"],
            "tokens": result["usage"],
            "audit": result["audit_metadata"],
        }
```

## Integration Points

### 1. Workflow Registration
Register your agent's workflow in the `workflows` table:
```sql
INSERT INTO workflows (tenant_id, name, description, status)
VALUES (
  'southern_shade_llc',
  'sourcing_bidding_agents',
  'Scan portals for matching solicitations and draft bids',
  'active'
);
```

### 2. Control Policies
Define policies that gate agent actions:
```sql
INSERT INTO control_policies (name, rule_logic, action)
VALUES (
  'require_human_review_for_bids',
  'workflow_id == "sourcing_bidding_agents"',
  'REVIEW'
);
```

### 3. Audit Trail
Every `ModelProvider.generate_chat()` call automatically emits:
- `tenant_id` and `workflow_id` in the response
- Token usage for cost tracking
- Timestamp for compliance

## Running the Agent

```python
# In a FastAPI endpoint or async script
import asyncio
from app.agents.sourcing_agent import SourcingAgent

async def main():
    agent = SourcingAgent(tenant_id="southern_shade_llc")
    
    solicitation = """
    RFP: AI-powered infrastructure management system
    Agency: City of Houston
    Budget: $500k
    Deadline: Jan 15, 2026
    """
    
    result = await agent.analyze_solicitation(solicitation)
    print(result["analysis"])
    print(f"Used {result['tokens']['total_tokens']} tokens")

if __name__ == "__main__":
    asyncio.run(main())
```

## Environment Setup

```bash
# .env
LLM_API_KEY=your_groq_or_openai_key
LLM_BASE_URL=https://api.groq.com/openai/v1  # or OpenAI
DATABASE_URL=postgresql://user:pass@localhost/rae
```

## Next Steps

1. **Add Tools**: Extend `generate_chat()` with `tools` parameter for function calling
2. **Gate Execution**: Check kill-switches before LLM calls
3. **Persist Results**: Store agent outputs in R.A.E. tables for review
4. **Web UI**: Build a dashboard to monitor agent runs and audit trails

See `SOUTHERN_SHADE_ONBOARDING.md` for the full workflow definitions.
