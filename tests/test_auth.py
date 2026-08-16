import sqlite3

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


def register_user(client, email="asha@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha",
            "email": email,
            "password": "correct-horse-battery",
        },
    ).json()


def bearer(session):
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_registration_rejects_short_and_common_passwords(tmp_path):
    client, _ = auth_client(tmp_path)
    base = {"name": "Asha", "email": "asha@example.com"}

    short = client.post(
        "/api/v1/auth/register",
        json={**base, "password": "too-short"},
    )
    common = client.post(
        "/api/v1/auth/register",
        json={**base, "password": "passwordpassword"},
    )

    assert short.status_code == 422
    assert common.status_code == 422
    assert "less common" in common.json()["detail"]


def test_failed_logins_lock_the_account_and_success_resets_counter(tmp_path):
    client, database_path = auth_client(tmp_path)
    register_user(client)
    payload = {"email": "asha@example.com", "password": "incorrect-password"}

    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    locked = client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert locked.status_code == 401

    connection = get_connection(database_path)
    try:
        attempts, locked_until = connection.execute(
            "SELECT failed_login_attempts, locked_until FROM user_credentials"
        ).fetchone()
        assert attempts == 5
        assert locked_until is not None
        connection.execute(
            "UPDATE user_credentials SET locked_until = '2000-01-01 00:00:00'"
        )
        connection.commit()
    finally:
        connection.close()

    successful = client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert successful.status_code == 200
    connection = get_connection(database_path)
    try:
        attempts, last_login = connection.execute(
            "SELECT failed_login_attempts, last_login_at FROM user_credentials"
        ).fetchone()
    finally:
        connection.close()
    assert attempts == 0
    assert last_login is not None


def test_password_change_reauthenticates_and_revokes_old_sessions(tmp_path):
    client, _ = auth_client(tmp_path)
    registered = register_user(client)
    old_refresh = registered["refresh_token"]

    changed = client.patch(
        "/api/v1/auth/password",
        headers=bearer(registered),
        json={
            "current_password": "correct-horse-battery",
            "new_password": "a-new-strong-password",
        },
    )

    assert changed.status_code == 200
    replacement = changed.json()
    assert client.get("/api/v1/summary", headers=bearer(registered)).status_code == 401
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    ).status_code == 401
    assert client.get("/api/v1/summary", headers=bearer(replacement)).status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha@example.com",
            "password": "correct-horse-battery",
        },
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha@example.com",
            "password": "a-new-strong-password",
        },
    ).status_code == 200


def test_sessions_can_be_listed_and_revoked_by_their_owner(tmp_path):
    client, _ = auth_client(tmp_path)
    first = register_user(client)
    second = client.post(
        "/api/v1/auth/login",
        json={
            "email": "asha@example.com",
            "password": "correct-horse-battery",
        },
    ).json()
    sessions = client.get(
        "/api/v1/auth/sessions",
        headers=bearer(first),
    ).json()

    assert len(sessions) == 2
    current = next(session for session in sessions if session["current"])
    other = next(session for session in sessions if not session["current"])
    assert client.delete(
        f"/api/v1/auth/sessions/{other['id']}",
        headers=bearer(first),
    ).status_code == 204
    assert client.get("/api/v1/summary", headers=bearer(second)).status_code == 401
    assert client.get("/api/v1/summary", headers=bearer(first)).status_code == 200
    assert current["id"] != other["id"]


def test_logout_all_requires_password_and_revokes_every_session(tmp_path):
    client, _ = auth_client(tmp_path)
    registered = register_user(client)

    denied = client.post(
        "/api/v1/auth/logout-all",
        headers=bearer(registered),
        json={"password": "incorrect-password"},
    )
    revoked = client.post(
        "/api/v1/auth/logout-all",
        headers=bearer(registered),
        json={"password": "correct-horse-battery"},
    )

    assert denied.status_code == 403
    assert revoked.status_code == 204
    assert client.get("/api/v1/summary", headers=bearer(registered)).status_code == 401


def test_privacy_export_contains_user_data_without_authentication_secrets(tmp_path):
    client, _ = auth_client(tmp_path)
    registered = register_user(client)

    exported = client.post(
        "/api/v1/privacy/export",
        headers=bearer(registered),
        json={"password": "correct-horse-battery"},
    )

    assert exported.status_code == 200
    data = exported.json()
    assert data["profile"]["email"] == "asha@example.com"
    assert data["accounts"][0]["name"] == "Main account"
    assert len(data["categories"]) == 8
    serialized = exported.text.casefold()
    assert "password_hash" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert registered["access_token"].casefold() not in serialized


def test_account_deletion_removes_finance_auth_and_checkpoint_data(
    monkeypatch,
    tmp_path,
):
    checkpoint_path = tmp_path / "checkpoints.db"
    monkeypatch.setenv("FINANCE_CHECKPOINT_PATH", str(checkpoint_path))
    monkeypatch.delenv("FINANCE_CHECKPOINT_URL", raising=False)
    client, database_path = auth_client(tmp_path)
    registered = register_user(client)
    user_id = registered["user_id"]
    with sqlite3.connect(checkpoint_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS writes (
                thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO checkpoints VALUES (?, '', 'one')",
            (f"user-{user_id}:monthly",),
        )
        connection.execute(
            "INSERT INTO checkpoints VALUES ('user-999:keep', '', 'two')"
        )

    wrong_confirmation = client.request(
        "DELETE",
        "/api/v1/privacy/account",
        headers=bearer(registered),
        json={"password": "correct-horse-battery", "confirmation": "delete"},
    )
    deleted = client.request(
        "DELETE",
        "/api/v1/privacy/account",
        headers=bearer(registered),
        json={"password": "correct-horse-battery", "confirmation": "DELETE"},
    )

    assert wrong_confirmation.status_code == 422
    assert deleted.status_code == 204
    assert client.get("/api/v1/summary", headers=bearer(registered)).status_code == 401
    connection = get_connection(database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM users WHERE id = ?", (user_id,)
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM accounts WHERE user_id = ?", (user_id,)
        ).fetchone()[0] == 0
    finally:
        connection.close()
    with sqlite3.connect(checkpoint_path) as connection:
        threads = connection.execute(
            "SELECT thread_id FROM checkpoints ORDER BY thread_id"
        ).fetchall()
    assert threads == [("user-999:keep",)]
