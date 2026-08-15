from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import TokenAuthenticator
from src.api.rate_limit import InMemoryRateLimiter
from src.database.db import get_connection, initialize_database
from src.database.finance_service import FinanceService
from src.security.auth_service import AuthService


def auth_client(tmp_path):
    database_path = tmp_path / "auth.db"
    initialize_database(database_path)
    service = FinanceService(database_path)
    auth_service = AuthService(
        database_path,
        PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1),
    )
    application = create_app(
        service=service,
        auth_service=auth_service,
        authenticator=TokenAuthenticator({}, auth_service=auth_service),
        chat_handler=lambda **_kwargs: None,
        rate_limiter=InMemoryRateLimiter(requests=100),
        auth_rate_limiter=InMemoryRateLimiter(requests=100),
    )
    return TestClient(application), database_path


def test_registration_creates_onboarded_user_and_hashed_credentials(tmp_path):
    client, database_path = auth_client(tmp_path)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha",
            "email": "ASHA@example.com",
            "password": "correct-horse-battery",
            "currency": "INR",
            "account_name": "Salary account",
        },
    )

    assert response.status_code == 201
    tokens = response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/v1/summary", headers=headers).status_code == 200
    assert client.get("/api/v1/accounts", headers=headers).json()[0]["name"] == "Salary account"
    assert len(client.get("/api/v1/categories", headers=headers).json()) == 8

    connection = get_connection(database_path)
    try:
        password_hash = connection.execute(
            "SELECT password_hash FROM user_credentials"
        ).fetchone()[0]
        session = connection.execute(
            "SELECT access_token_hash, refresh_token_hash FROM auth_sessions"
        ).fetchone()
    finally:
        connection.close()
    assert password_hash.startswith("$argon2id$")
    assert "correct-horse-battery" not in password_hash
    assert tokens["access_token"] not in session
    assert tokens["refresh_token"] not in session


def test_login_rejects_invalid_credentials_without_revealing_email(tmp_path):
    client, _ = auth_client(tmp_path)
    registration = {
        "name": "Asha",
        "email": "asha@example.com",
        "password": "correct-horse-battery",
    }
    client.post("/api/v1/auth/register", json=registration)

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": registration["email"], "password": "incorrect-password"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "incorrect-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_refresh_rotates_tokens_and_logout_revokes_session(tmp_path):
    client, _ = auth_client(tmp_path)
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha",
            "email": "asha@example.com",
            "password": "correct-horse-battery",
        },
    ).json()
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert refreshed.status_code == 200
    replacement = refreshed.json()
    assert replacement["access_token"] != registered["access_token"]
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    ).status_code == 401

    headers = {"Authorization": f"Bearer {replacement['access_token']}"}
    assert client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": replacement["refresh_token"]},
    ).status_code == 204
    assert client.get("/api/v1/summary", headers=headers).status_code == 401


def test_duplicate_registration_is_rejected(tmp_path):
    client, _ = auth_client(tmp_path)
    payload = {
        "name": "Asha",
        "email": "asha@example.com",
        "password": "correct-horse-battery",
    }

    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
