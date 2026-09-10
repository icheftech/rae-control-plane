"""Provision one local, read-only Gmail agent workflow through R.A.E.'s API.

Run once with an administrator key. It creates a separate operator identity for
the agent, one workflow, and a model-specific allow policy. It writes only local
configuration, all ignored by Git.
"""
import json
import os
import secrets
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "local-state"


def main() -> None:
    values = dotenv_values(ROOT / ".env")
    admin_keys = json.loads(values.get("RAE_API_KEYS") or "{}")
    admin_key = next((key for key, identity in admin_keys.items() if identity.get("role") == "admin"), None)
    if not admin_key:
        raise SystemExit("Add at least one admin identity to RAE_API_KEYS in .env first.")
    api_url = values.get("RAE_API_URL", "http://127.0.0.1:18000")
    model = values.get("RAE_GMAIL_MODEL", "qwen3.5:4b")
    agent_key = secrets.token_urlsafe(32)
    admin_keys[agent_key] = {"name": "gmail-readonly-agent", "role": "operator"}
    headers = {"Authorization": "Bearer " + admin_key}
    with httpx.Client(base_url=api_url, headers=headers, timeout=30) as client:
        workflow = client.post("/api/workflows", json={
            "name": "Gmail read-only triage", "version": "1.0.0", "risk_level": "medium",
            "description": "Reads selected Gmail message metadata; produces local summaries and never changes mail.",
        })
        workflow.raise_for_status()
        workflow_id = workflow.json()["id"]
        policy = client.post("/api/control-policies", json={
            "name": "Allow local Gmail triage model", "workflow_id": workflow_id,
            "policy_action": "allow", "conditions": {"model": model},
        })
        policy.raise_for_status()
    STATE.mkdir(parents=True, exist_ok=True)
    config = {
        "RAE_API_URL": api_url, "RAE_GMAIL_AGENT_KEY": agent_key,
        "RAE_GMAIL_WORKFLOW_ID": workflow_id, "RAE_GMAIL_MODEL": model,
        "policy_id": policy.json()["id"],
    }
    target = STATE / "gmail-agent-config.json"
    target.write_text(json.dumps(config, indent=2) + "\n")
    target.chmod(0o600)
    # The active R.A.E. process reads this identity at startup. Persist it before
    # asking the user to restart so the agent cannot borrow the administrator key.
    set_key(ROOT / ".env", "RAE_API_KEYS", json.dumps(admin_keys, separators=(",", ":")))
    print("Workflow provisioned. Copy these values into .env, then restart the R.A.E. API:")
    for key in ("RAE_API_URL", "RAE_GMAIL_AGENT_KEY", "RAE_GMAIL_WORKFLOW_ID", "RAE_GMAIL_MODEL"):
        print(f"{key}={config[key]}")
    print(f"Local configuration saved to {target}")


if __name__ == "__main__":
    main()
