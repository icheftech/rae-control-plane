"""Allowlisted JSON telemetry; never log bodies, credentials or query strings."""
import json
import logging
from contextvars import ContextVar
from time import monotonic
from uuid import uuid4

request_id = ContextVar('request_id', default=None)
logger = logging.getLogger('rae.telemetry')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.propagate = False


def emit(event, **fields):
    logger.info(json.dumps({'event': event, 'request_id': request_id.get(), **fields}))


class RequestTelemetry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        rid = str(uuid4())
        token = request_id.set(rid)
        start, status = monotonic(), 500

        async def traced_send(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                message['headers'] = [*message.get('headers', []), (b'x-request-id', rid.encode())]
            await send(message)
        try:
            await self.app(scope, receive, traced_send)
        finally:
            route = scope.get('route')
            emit('http_request', method=scope['method'], route=getattr(route, 'path', 'unmatched'),
                 status=status, duration_ms=round((monotonic() - start) * 1000, 2))
            request_id.reset(token)
