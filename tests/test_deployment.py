from src.api.app import create_app
from src.api.auth import TokenAuthenticator
from src.api.rate_limit import InMemoryRateLimiter
from src.database.db import get_database_path, initialize_database
from src.database.finance_service import FinanceService
from scripts.bootstrap_user import bootstrap_user


def test_database_path_uses_deployment_data_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("FINANCE_DATABASE_PATH", raising=False)

    assert get_database_path() == tmp_path / "finance.db"


def test_explicit_database_path_takes_priority(monkeypatch, tmp_path):
    database_path = tmp_path / "custom" / "production.db"
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "ignored"))
    monkeypatch.setenv("FINANCE_DATABASE_PATH", str(database_path))

    assert get_database_path() == database_path


def test_bootstrap_user_is_idempotent_and_creates_usable_profile(tmp_path):
    database_path = tmp_path / "deployment.db"
    first_id = bootstrap_user(
        "Asha",
        "asha@example.com",
        database_path=database_path,
    )
    second_id = bootstrap_user(
        "Asha",
        "asha@example.com",
        database_path=database_path,
    )
    service = FinanceService(database_path)

    assert first_id == second_id
    assert len(service.get_accounts(first_id)) == 1
    assert len(service.get_categories(first_id)) == 8


def test_database_initialization_is_idempotent(tmp_path):
    database_path = tmp_path / "nested" / "finance.db"

    initialize_database(database_path)
    initialize_database(database_path)

    assert database_path.exists()


def test_api_factory_initializes_an_empty_deployment_database(tmp_path):
    database_path = tmp_path / "empty" / "finance.db"
    service = FinanceService(database_path)

    create_app(
        service=service,
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({"x" * 32: 1}),
        rate_limiter=InMemoryRateLimiter(requests=10),
    )

    assert database_path.exists()


def test_api_serves_configured_react_build(monkeypatch, tmp_path):
    react_dist = tmp_path / "dist"
    assets = react_dist / "assets"
    assets.mkdir(parents=True)
    (react_dist / "index.html").write_text(
        '<div id="root">React deployment</div>',
        encoding="utf-8",
    )
    (assets / "app.js").write_text("console.log('react')", encoding="utf-8")
    monkeypatch.setenv("FINANCE_UI_DIST", str(react_dist))

    application = create_app(
        service=FinanceService(tmp_path / "react.db"),
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({"x" * 32: 1}),
        rate_limiter=InMemoryRateLimiter(requests=10),
    )
    client = TestClient(application)

    page = client.get("/")
    script = client.get("/assets/app.js")

    assert page.status_code == 200
    assert "React deployment" in page.text
    assert script.status_code == 200
    assert "default-src 'self'" in page.headers["content-security-policy"]
from fastapi.testclient import TestClient
