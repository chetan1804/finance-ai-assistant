import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from redis import Redis
from redis.exceptions import ConnectionError

from src.api.rate_limit import RedisRateLimiter


class FakeRedis:
    def __init__(self, results=None, error=None):
        self.results = list(results or [])
        self.error = error

    def eval(self, *_args):
        if self.error:
            raise self.error
        return self.results.pop(0)

    def ping(self):
        if self.error:
            raise self.error
        return True


def test_redis_rate_limiter_returns_retry_after():
    limiter = RedisRateLimiter(
        FakeRedis(results=[(1, 60000), (2, 59500)]),
        requests=1,
        window_seconds=60,
    )

    limiter.check("user-1")
    with pytest.raises(HTTPException) as error:
        limiter.check("user-1")

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}


def test_redis_failure_closes_rate_limit_boundary():
    limiter = RedisRateLimiter(FakeRedis(error=ConnectionError()))

    assert limiter.is_ready() is False
    with pytest.raises(HTTPException) as error:
        limiter.check("user-1")

    assert error.value.status_code == 503


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="TEST_REDIS_URL is required for Redis integration testing.",
)
def test_redis_rate_limit_is_shared_between_instances():
    client = Redis.from_url(os.environ["TEST_REDIS_URL"])
    namespace = f"integration-{uuid4().hex}"
    first = RedisRateLimiter(client, requests=2, namespace=namespace)
    second = RedisRateLimiter(client, requests=2, namespace=namespace)

    first.check("shared-user")
    second.check("shared-user")
    with pytest.raises(HTTPException) as error:
        first.check("shared-user")

    client.close()
    assert error.value.status_code == 429
