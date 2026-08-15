import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    """Small single-process sliding-window limiter for the local API."""

    def __init__(self, requests=60, window_seconds=60):
        if requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit values must be positive.")
        self.requests = requests
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, identity):
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            events = self._events[identity]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.requests:
                retry_after = max(1, int(events[0] + self.window_seconds - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded.",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)
