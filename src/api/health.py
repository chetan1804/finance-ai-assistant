from src.agents.checkpoint import checkpoint_storage_is_ready
from src.database.db import database_is_ready


class ProductionHealthChecker:
    def __init__(self, database_path=None, rate_limiters=()):
        self.database_path = database_path
        self.rate_limiters = tuple(rate_limiters)

    @staticmethod
    def _status(check):
        try:
            return "ok" if check() else "unavailable"
        except Exception:
            return "unavailable"

    def check(self):
        checks = {
            "database": self._status(
                lambda: database_is_ready(self.database_path)
            ),
            "checkpoints": self._status(checkpoint_storage_is_ready),
            "rate_limiter": self._status(
                lambda: all(
                    limiter.is_ready()
                    for limiter in self.rate_limiters
                )
            ),
        }
        return {
            "status": (
                "ready"
                if all(value == "ok" for value in checks.values())
                else "unavailable"
            ),
            "checks": checks,
        }
