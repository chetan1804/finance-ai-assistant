import logging
import os
import re
import sys
import time
from uuid import uuid4

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pythonjsonlogger.json import JsonFormatter


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def configure_application_logger(stream=None):
    logger = logging.getLogger("arthnivo")
    level_name = os.getenv("FINANCE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise RuntimeError("FINANCE_LOG_LEVEL must be a valid logging level.")

    handler = logging.StreamHandler(stream or sys.stdout)
    if os.getenv("FINANCE_LOG_FORMAT", "json").casefold() == "json":
        formatter = JsonFormatter(
            [
                "timestamp",
                "levelname",
                "name",
                "message",
                "request_id",
                "method",
                "route",
                "status_code",
                "duration_ms",
                "checks",
                "error_type",
                "ai_stage",
                "exc_info",
            ],
            timestamp=True,
            static_fields={
                "service": "arthnivo",
                "environment": os.getenv("FINANCE_ENVIRONMENT", "development"),
            },
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def request_id_from_header(value):
    return value if value and REQUEST_ID_PATTERN.fullmatch(value) else uuid4().hex


class Observability:
    def __init__(self, logger=None, registry=None):
        self.logger = logger or configure_application_logger()
        self.registry = registry or CollectorRegistry()
        self.requests = Counter(
            "finance_http_requests_total",
            "HTTP requests processed by the finance API.",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.duration = Histogram(
            "finance_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ("method", "route"),
            registry=self.registry,
        )
        self.readiness = Gauge(
            "finance_dependency_ready",
            "Whether a production dependency is currently ready.",
            ("dependency",),
            registry=self.registry,
        )

    @staticmethod
    def route_name(request):
        route = request.scope.get("route")
        return getattr(route, "path", None) or "unmatched"

    def record_request(self, request, status_code, started_at):
        route = self.route_name(request)
        duration = max(0.0, time.perf_counter() - started_at)
        method = request.method
        status_value = str(status_code)
        self.requests.labels(method, route, status_value).inc()
        self.duration.labels(method, route).observe(duration)
        self.logger.info(
            "http_request_completed",
            extra={
                "request_id": request.state.request_id,
                "method": method,
                "route": route,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )

    def record_readiness(self, checks):
        for dependency, dependency_status in checks.items():
            self.readiness.labels(dependency).set(
                1 if dependency_status == "ok" else 0
            )

    def metrics_payload(self):
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
