from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException

_BUCKETS: dict[str, Deque[float]] = defaultdict(deque)


def enforce_rate_limit(*, key: str, max_requests: int, window_seconds: int) -> None:
    now = time.time()
    q = _BUCKETS[key]
    cutoff = now - window_seconds
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests. Please retry later.")
    q.append(now)
