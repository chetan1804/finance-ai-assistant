import json
from io import StringIO
from types import SimpleNamespace

from prometheus_client import CollectorRegistry

from src.api.observability import (
    Observability,
    configure_application_logger,
    request_id_from_header,
)


def test_request_id_accepts_safe_values_and_replaces_untrusted_values():
    assert request_id_from_header("request-123") == "request-123"

    generated = request_id_from_header("unsafe request\nheader")
    assert len(generated) == 32
    assert generated.isalnum()


def test_structured_request_log_contains_only_operational_metadata(monkeypatch):
    stream = StringIO()
    monkeypatch.setenv("FINANCE_LOG_FORMAT", "json")
    logger = configure_application_logger(stream=stream)
    observability = Observability(logger=logger, registry=CollectorRegistry())
    request = SimpleNamespace(
        method="POST",
        state=SimpleNamespace(request_id="request-123"),
        scope={"route": SimpleNamespace(path="/api/v1/transactions")},
    )

    observability.record_request(request, 201, 0)
    record = json.loads(stream.getvalue())

    assert record["message"] == "http_request_completed"
    assert record["request_id"] == "request-123"
    assert record["route"] == "/api/v1/transactions"
    assert "body" not in record
    assert "token" not in record
