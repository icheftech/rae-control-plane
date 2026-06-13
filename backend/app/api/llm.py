"""LLM API Router - Chat completions endpoint for R.A.E.

Exposes POST /v1/chat/completions for internal agents and external clients
(like the Southern Shade website) to call the ModelProvider.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.model_provider import get_model_provider, ModelProvider


router = APIRouter(prefix="/v1", tags=["llm"])


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tenant_id: Optional[str] = None
    workflow_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ChatCompletionResponse(BaseModel):
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    model: str
    usage: Dict[str, Any]
    audit_metadata: Dict[str, Any]


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    provider: ModelProvider = Depends(get_model_provider),
):
    """
    Generate a chat completion using the configured LLM provider.

    - Accepts OpenAI-compatible message format
    - Injects tenant_id and workflow_id for R.A.E. audit trails
    - Returns content, tool calls, usage stats, and audit metadata
    """
    try:
        # Convert pydantic models to dicts for ModelProvider
        messages_dict = [msg.dict() for msg in request.messages]

        result = await provider.generate_chat(
            messages=messages_dict,
            model=request.model,
            tools=request.tools,
            tenant_id=request.tenant_id,
            workflow_id=request.workflow_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatCompletionResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {str(e)}"
        )
