from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import TokenAuthenticator
from src.api.rate_limit import InMemoryRateLimiter
from src.api.release import ReleaseMetadata
from src.database.finance_service import FinanceService


def test_release_metadata_uses_safe_environment_values(monkeypatch):
    monkeypatch.setenv("FINANCE_RELEASE_VERSION", "v2.4.1")
    monkeypatch.setenv("FINANCE_COMMIT_SHA", "abc123def456")
    monkeypatch.setenv("FINANCE_BUILD_DATE", "2026-08-16T08:30:00Z")

    assert ReleaseMetadata.from_environment().response() == {
        "version": "v2.4.1",
        "commit": "abc123def456",
        "built_at": "2026-08-16T08:30:00Z",
    }


def test_release_metadata_rejects_unsafe_values(monkeypatch):
    monkeypatch.setenv("FINANCE_RELEASE_VERSION", "<script>alert(1)</script>")
    monkeypatch.setenv("FINANCE_COMMIT_SHA", "commit with spaces")

    metadata = ReleaseMetadata.from_environment()

    assert metadata.version == "development"
    assert metadata.commit == "unknown"


def test_version_endpoint_reports_deployed_artifact(tmp_path):
    metadata = ReleaseMetadata(
        version="v2.4.1",
        commit="abc123def456",
        built_at="2026-08-16T08:30:00Z",
    )
    application = create_app(
        service=FinanceService(tmp_path / "release.db"),
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({"x" * 32: 1}),
        rate_limiter=InMemoryRateLimiter(requests=10),
        release_metadata=metadata,
    )

    response = TestClient(application).get("/version")

    assert response.status_code == 200
    assert response.json() == metadata.response()
    assert application.version == "v2.4.1"
