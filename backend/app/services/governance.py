"""Conservative preflight governance for LLM calls."""
from app.services.evidence import capture, evaluate_snapshot, record

def evaluate(db, workflow_id, model):
    snapshot = capture(db, workflow_id, model)
    allowed, reason = evaluate_snapshot(snapshot.content)
    record(db, 'authorization', 'success' if allowed else 'denied',
           {'allowed':allowed, 'reason':reason}, snapshot_id=snapshot.id)
    db.info['policy_snapshot_id'] = snapshot.id
    db.commit()
    return allowed, reason
