import httpx
import pytest
from app.services.model_provider import ModelProvider


@pytest.mark.asyncio
async def test_local_provider_settings(monkeypatch):
    monkeypatch.setenv('LLM_REASONING_EFFORT', 'none')
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS', '180')
    provider = ModelProvider(api_key='local-test', base_url='http://127.0.0.1:11434/v1')
    assert provider.client.timeout.read == 180
    await provider.close()

    def respond(request):
        import json
        payload = json.loads(request.content)
        assert str(request.url) == 'http://127.0.0.1:11434/v1/chat/completions'
        assert payload['reasoning_effort'] == 'none'
        assert payload['max_tokens'] == 256
        return httpx.Response(200, json={'choices':[{'message':{'content':'Investigate logs'}}], 'usage':{}})

    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        result = await provider.generate_chat([{'role':'user','content':'Synthetic incident'}], model='local', max_tokens=256)
        assert result['content'] == 'Investigate logs'
    finally:
        await provider.close()
