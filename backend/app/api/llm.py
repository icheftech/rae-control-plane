"""Governed model gateway. Never persists prompt/response content."""
from typing import Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from app.api.schemas import Strict
from app.security import Actor, operator
from app.db.database import get_db
from app.services.model_provider import get_model_provider, ModelProvider
from app.services.governance import evaluate
from app.services.audit import append_event
router = APIRouter(prefix='/v1', tags=['llm'])
class Message(Strict):
    role: Literal['system','user','assistant']
    content: str = Field(min_length=1, max_length=32000)
class ChatCompletionRequest(Strict):
    messages: list[Message] = Field(min_length=1, max_length=100)
    workflow_id: UUID
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=8192)

@router.post('/chat/completions')
async def create_chat_completion(request: ChatCompletionRequest, actor: Actor=Depends(operator), db: Session=Depends(get_db), provider: ModelProvider=Depends(get_model_provider)):
    model = request.model or provider.default_model
    allowed, reason = evaluate(db, request.workflow_id, model)
    context = {'workflow_id': str(request.workflow_id), 'model':model, 'reason':reason}
    append_event(db, actor, 'LLM_ALLOWED' if allowed else 'LLM_BLOCKED', outcome='SUCCESS' if allowed else 'BLOCKED', context=context)
    db.commit()  # A durable preflight record is required before any external call.
    if not allowed: raise HTTPException(403, reason)
    if not provider.api_key: raise HTTPException(503, 'LLM provider key is not configured')
    try:
        result = await provider.generate_chat(messages=[m.model_dump() for m in request.messages], model=model, workflow_id=str(request.workflow_id), temperature=request.temperature, max_tokens=request.max_tokens)
    except Exception:
        append_event(db, actor, 'LLM_FAILED', outcome='ERROR', context=context)
        db.commit()
        raise HTTPException(502, 'Model provider request failed')
    event = append_event(db, actor, 'LLM_COMPLETED', context={**context, 'usage':result.get('usage',{})})
    db.commit()
    result['audit_metadata']['event_id'] = str(event.id)
    return result
