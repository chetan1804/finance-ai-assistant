import atexit
import hashlib
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError


RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('PTTL', KEYS[1])
return {current, ttl}
"""
_REDIS_CLIENTS = {}
_REDIS_CLIENTS_LOCK = threading.Lock()


def get_redis_url():
    value = os.getenv("FINANCE_REDIS_URL")
    if value and not value.startswith(("redis://", "rediss://")):
        raise RuntimeError("FINANCE_REDIS_URL must use Redis.")
    return value


def get_redis_client(redis_url=None):
    redis_url = redis_url or get_redis_url()
    if not redis_url:
        return None
    with _REDIS_CLIENTS_LOCK:
        client = _REDIS_CLIENTS.get(redis_url)
        if client is None:
            client = Redis.from_url(
                redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            _REDIS_CLIENTS[redis_url] = client
    return client


def close_redis_clients():
    with _REDIS_CLIENTS_LOCK:
        clients = list(_REDIS_CLIENTS.values())
        _REDIS_CLIENTS.clear()
    for client in clients:
        client.close()


atexit.register(close_redis_clients)


class InMemoryRateLimiter:
    """Small single-process sliding-window limiter for the local API."""

    def __init__(self, requests=60, window_seconds=60):
        if requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit values must be positive.")
        self.requests = requests
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = threading.Lock()
        self.backend = "memory"

    def is_ready(self):
        return True

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


class RedisRateLimiter:
    """Atomic fixed-window limiter shared by all application replicas."""

    def __init__(
        self,
        client,
        requests=60,
        window_seconds=60,
        namespace="api",
    ):
        if requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit values must be positive.")
        self.client = client
        self.requests = requests
        self.window_seconds = window_seconds
        self.namespace = namespace
        self.backend = "redis"

    def _key(self, identity):
        digest = hashlib.sha256(str(identity).encode("utf-8")).hexdigest()
        return f"finance:rate-limit:{self.namespace}:{digest}"

    def is_ready(self):
        try:
            return bool(self.client.ping())
        except RedisError:
            return False

    def check(self, identity):
        try:
            current, ttl_ms = self.client.eval(
                RATE_LIMIT_SCRIPT,
                1,
                self._key(identity),
                self.window_seconds * 1000,
            )
        except RedisError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting is temporarily unavailable.",
            ) from None
        if current > self.requests:
            retry_after = max(1, (max(ttl_ms, 0) + 999) // 1000)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
                headers={"Retry-After": str(retry_after)},
            )


def create_rate_limiter(
    *,
    requests=60,
    window_seconds=60,
    namespace="api",
    redis_client=None,
):
    client = redis_client or get_redis_client()
    if client is None:
        return InMemoryRateLimiter(requests, window_seconds)
    return RedisRateLimiter(
        client,
        requests=requests,
        window_seconds=window_seconds,
        namespace=namespace,
    )
