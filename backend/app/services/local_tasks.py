"""Load only installer-owned, bounded task definitions; never expose their content."""
import hashlib
import os
import re
from pathlib import Path
from fastapi import HTTPException
from app.services.orchestration import OrchestrationRunRequest


def load_task(key, tenant_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', key):
        raise HTTPException(422, 'Invalid local task key')
    root = Path(os.getenv('RAE_LOCAL_TASKS_DIR', Path(__file__).resolve().parents[3] / 'local-state' / 'worker-tasks'))
    # Tenant subdirectories prevent another tenant selecting a private definition.
    path = root / str(tenant_id) / (key + '.json')
    try:
        if path.is_symlink() or path.stat().st_size > 262144:
            raise ValueError()
        content = path.read_bytes()
        if len(content) > 262144:
            raise ValueError()
        request = OrchestrationRunRequest.model_validate_json(content)
    except (OSError, ValueError):
        raise HTTPException(422, 'Local task is missing or invalid')
    return request, hashlib.sha256(content).hexdigest()
