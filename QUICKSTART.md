# S.S.O. Control Plane - Quickstart Guide

**Get your language model running with S.S.O. in 5 minutes**

## Overview

This guide will help you:
1. Set up your local environment
2. Configure Groq (free tier) as your LLM provider
3. Start the S.S.O. backend
4. Test your first LLM call through the governance layer

## Prerequisites

- **Python 3.11+** (check with `python3 --version`)
- **PostgreSQL 15+** (or use Docker for simplified setup)
- **Git** (to clone the repo)
- **Groq API Key** (free tier - already set up in your account)

## Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/icheftech/sso-control-plane.git
cd sso-control-plane

# Install Python dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

Create a `.env` file in the root directory with your Groq API key:

```bash
# Copy the example file
cp .env.example .env
```

Now edit `.env` and add these LLM-specific settings at the bottom:

```bash
# ===================
# LLM Configuration (Groq - Free Tier)
# ===================
LLM_API_KEY=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
LLM_BASE_URL=https://api.groq.com/v1
LLM_DEFAULT_MODEL=llama-3.3-70b-versatile
```

**Note:** Replace the API key above with your actual Groq key from https://console.groq.com/keys

## Step 3: Set Up Database

### Option A: Docker (Easiest)

```bash
# Start PostgreSQL in Docker
docker-compose up -d postgres

# Wait 5 seconds for PostgreSQL to be ready
sleep 5
```

### Option B: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Create the database
createdb sso_control_plane

# Update .env with your local connection
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/sso_control_plane
```

## Step 4: Initialize Database

```bash
# Run from the backend directory
cd backend

# Initialize tables
python -c "from app.db.database import init_db; init_db()"
```

## Step 5: Start the Backend

```bash
# Still in backend/ directory
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🚀 S.S.O. Control Plane starting up...
✅ Database connection successful
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 6: Test Your Setup

### Test 1: Health Check

Open http://localhost:8000/health in your browser, or:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

### Test 2: API Documentation

Visit http://localhost:8000/api/docs to see the full Swagger UI with all endpoints.

### Test 3: Your First LLM Call

Make a chat completion request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is Southern Shade LLC?"}
    ],
    "tenant_id": "southern_shade_llc",
    "workflow_id": "test_workflow"
  }'
```

Expected response:
```json
{
  "content": "Southern Shade LLC is an infrastructure and AI automation consulting company...",
  "model": "llama-3.3-70b-versatile",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 45,
    "total_tokens": 60
  },
  "audit_metadata": {
    "tenant_id": "southern_shade_llc",
    "workflow_id": "test_workflow",
    "model": "llama-3.3-70b-versatile",
    "timestamp": "2026-01-03T07:00:00.123456"
  }
}
```

## What You Just Did

✅ **ModelProvider**: Your backend now has a unified interface to call Groq (or any OpenAI-compatible API)  
✅ **Governance Layer**: Every LLM call is tagged with `tenant_id` and `workflow_id` for audit trails  
✅ **Zero Cost**: You're using Groq's free tier (14.4k requests/day, ~1M tokens)  
✅ **Plug-and-Play**: The Southern Shade website and S.S.O. agents can now call `/v1/chat/completions`

## Next Steps

### For Southern Shade Website

In your website repo, add an API client:

```javascript
// website/lib/sso-client.ts
export async function askAssistant(question: string) {
  const response = await fetch('http://localhost:8000/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: 'You are a helpful assistant for Southern Shade LLC.' },
        { role: 'user', content: question }
      ],
      tenant_id: 'southern_shade_website',
      temperature: 0.7
    })
  });
  
  const data = await response.json();
  return data.content;
}
```

### For S.S.O. Agents

See `SOUTHERN_SHADE_ONBOARDING.md` for how to build:
- Sourcing & bidding agents
- Marketing & sales agents  
- Product development agents

All using the same `ModelProvider` interface you just tested.

## Troubleshooting

### "Database connection failed"

- Check PostgreSQL is running: `docker ps` or `pg_isready`
- Verify `DATABASE_URL` in `.env` matches your setup

### "LLM generation failed: 401 Unauthorized"

- Double-check your Groq API key in `.env`
- Make sure you copied it correctly from https://console.groq.com/keys

### "Port 8000 already in use"

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or use a different port
uvicorn app.main:app --reload --port 8001
```

## Cost Estimation

**Groq Free Tier:**
- 14,400 requests per day
- ~1,000,000 tokens per month
- Models: Llama 3.3 70B, Mixtral, Gemma 2

**When you'll need to pay:**
- Once you exceed free tier limits
- Typical cost: $0.50-$2.00 per million tokens (varies by model)
- For production at scale, consider dedicated hosting or enterprise contracts

## Security Notes

🔒 **Never commit `.env` to git** (it's in `.gitignore` already)  
🔒 **Rotate your API keys** regularly in production  
🔒 **Use environment-specific keys** (dev vs staging vs production)

---

**You're now running S.S.O. with a language model!** 🎉

For production deployment, see `AGENT_NOTES.md` for full governance setup.
