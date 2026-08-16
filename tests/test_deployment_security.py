import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import TokenAuthenticator
from src.api.deployment_security import DeploymentSecuritySettings
from src.api.rate_limit import InMemoryRateLimiter
from src.database.finance_service import FinanceService


def settings(**overrides):
    values = {
        "environment": "development",
        "allowed_hosts": ("testserver",),
        "cors_origins": (),
        "https_redirect": False,
        "hsts_seconds": 0,
        "root_path": "",
    }
    values.update(overrides)
    return DeploymentSecuritySettings(**values)


def secured_app(tmp_path, deployment_settings):
    return create_app(
        service=FinanceService(tmp_path / "deployment-security.db"),
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({"x" * 32: 1}),
        rate_limiter=InMemoryRateLimiter(requests=100),
        auth_rate_limiter=InMemoryRateLimiter(requests=100),
        deployment_settings=deployment_settings,
    )


def test_production_requires_explicit_allowed_hosts(monkeypatch):
    monkeypatch.setenv("FINANCE_ENVIRONMENT", "production")
    monkeypatch.delenv("FINANCE_ALLOWED_HOSTS", raising=False)

    with pytest.raises(RuntimeError, match="required in production"):
        DeploymentSecuritySettings.from_environment()


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("FINANCE_ENVIRONMENT", "prodction")

    with pytest.raises(RuntimeError, match="development, test, or production"):
        DeploymentSecuritySettings.from_environment()


def test_production_rejects_wildcard_hosts(monkeypatch):
    monkeypatch.setenv("FINANCE_ENVIRONMENT", "production")
    monkeypatch.setenv("FINANCE_ALLOWED_HOSTS", "*")
    monkeypatch.delenv("FINANCE_CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError, match=r"cannot use \*"):
        DeploymentSecuritySettings.from_environment()


def test_cors_origins_must_be_explicit_origins(monkeypatch):
    monkeypatch.setenv("FINANCE_ENVIRONMENT", "development")
    monkeypatch.delenv("FINANCE_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("FINANCE_CORS_ORIGINS", "https://app.example.com/path")

    with pytest.raises(RuntimeError, match="invalid origin"):
        DeploymentSecuritySettings.from_environment()


def test_untrusted_host_is_rejected(tmp_path):
    application = secured_app(
        tmp_path,
        settings(allowed_hosts=("finance.example.com",)),
    )

    response = TestClient(
        application,
        base_url="http://untrusted.example.com",
    ).get("/health")

    assert response.status_code == 400


def test_cors_allows_only_configured_frontend_origin(tmp_path):
    application = secured_app(
        tmp_path,
        settings(
            allowed_hosts=("api.example.com",),
            cors_origins=("https://app.example.com",),
        ),
    )
    client = TestClient(application, base_url="http://api.example.com")

    allowed = client.options(
        "/api/v1/summary",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    rejected = client.get(
        "/health",
        headers={"Origin": "https://untrusted.example.com"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    assert "access-control-allow-origin" not in rejected.headers


def test_https_redirect_and_hsts_are_enabled_for_secure_production(tmp_path):
    deployment_settings = settings(
        environment="production",
        allowed_hosts=("finance.example.com",),
        https_redirect=True,
        hsts_seconds=31536000,
    )
    application = secured_app(tmp_path, deployment_settings)

    redirect = TestClient(
        application,
        base_url="http://finance.example.com",
        follow_redirects=False,
    ).get("/health")
    secure = TestClient(
        application,
        base_url="https://finance.example.com",
    ).get("/health")

    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://finance.example.com/health"
    assert secure.status_code == 200
    assert secure.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )
