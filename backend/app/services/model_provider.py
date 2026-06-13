"""ModelProvider - Unified LLM interface for R.A.E.

Provides a single interface for calling language models with:
- Multi-provider support (OpenAI-compatible APIs, local models, etc.)
- Tenant and workflow context injection
- Audit event emission
- Policy enforcement hooks
"""

import os
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime


class ModelProvider:
    """Wraps LLM API calls with R.A.E. governance."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-3.5-turbo",
    ):
        """
        Initialize the ModelProvider.

        Args:
            api_key: API key for the LLM provider (falls back to env var)
            base_url: Base URL for OpenAI-compatible API (defaults to OpenAI)
            default_model: Default model ID to use if not specified in requests
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
        self.default_model = default_model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tenant_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion with governance metadata.

        Args:
            messages: OpenAI-format message list [{"role": "user", "content": "..."}]
            model: Model ID (defaults to instance default_model)
            tools: Optional tool/function definitions for function calling
            tenant_id: Tenant making the request (for audit)
            workflow_id: Workflow making the request (for audit)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Dict with 'content', 'model', 'usage', 'audit_metadata'
        """
        model = model or self.default_model

        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        # Call the LLM API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()

        # Extract assistant message
        assistant_message = result["choices"][0]["message"]
        content = assistant_message.get("content", "")
        tool_calls = assistant_message.get("tool_calls")

        # Build audit metadata
        audit_metadata = {
            "tenant_id": tenant_id,
            "workflow_id": workflow_id,
            "model": model,
            "timestamp": datetime.utcnow().isoformat(),
            "usage": result.get("usage", {}),
        }

        return {
            "content": content,
            "tool_calls": tool_calls,
            "model": model,
            "usage": result.get("usage", {}),
            "audit_metadata": audit_metadata,
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance for FastAPI dependency injection
_provider_instance: Optional[ModelProvider] = None


def get_model_provider() -> ModelProvider:
    """Get or create the global ModelProvider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = ModelProvider()
    return _provider_instance
