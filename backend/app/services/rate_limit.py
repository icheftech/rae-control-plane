"""Bounded, per-process actor limiter for the local single-worker deployment."""
import os
from collections import OrderedDict
from threading import Lock
from time import monotonic
from fastapi import HTTPException

_buckets = OrderedDict()
_lock = Lock()


def limit_actor(actor):
    limit = int(os.getenv('RAE_REQUESTS_PER_MINUTE', '120'))
    now = monotonic()
    with _lock:
        key = str(actor.id)
        start, count = _buckets.get(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        if count >= limit:
            raise HTTPException(429, 'Request limit reached', headers={'Retry-After': str(max(1, int(60 - (now-start))))})
        _buckets[key] = (start, count+1)
        _buckets.move_to_end(key)
        while len(_buckets) > 10000:
            _buckets.popitem(last=False)
    return actor
