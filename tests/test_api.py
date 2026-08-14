from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import TokenAuthenticator
from src.api.rate_limit import InMemoryRateLimiter
from src.database.db import initialize_database
from src.database.finance_service import FinanceService


USER_TOKEN = "user-one-token-000000000000000000"
OTHER_TOKEN = "user-two-token-000000000000000000"
AUTH_HEADERS = {"Authorization": f"Bearer {USER_TOKEN}"}


@pytest.fixture
def api_context(tmp_path):
    database_path = tmp_path / "api.db"
    initialize_database(database_path)
    service = FinanceService(database_path)
    user_id = service.create_user("Asha", "asha@example.com")
    other_user_id = service.create_user("Ravi", "ravi@example.com")
    account_id = service.create_account(user_id, "Bank", "savings")
    other_account_id = service.create_account(
        other_user_id,
        "Private Bank",
        "savings",
    )
    food_id = service.create_category(user_id, "Food", "expense")
    salary_id = service.add_transaction(
        user_id,
        account_id,
        food_id,
        "income",
        50000,
        "Salary",
        "2026-07-01",
    )
    grocery_id = service.add_transaction(
        user_id,
        account_id,
        food_id,
        "expense",
        2000,
        "Groceries",
        "2026-07-10",
    )
    private_transaction_id = service.add_transaction(
        other_user_id,
        other_account_id,
        None,
        "expense",
        9999,
        "Private expense",
        "2026-07-10",
    )

    chat_calls = []

    def fake_chat_handler(*, user_id, thread_id, question):
        chat_calls.append((user_id, thread_id, question))
        return {
            "messages": [
                SimpleNamespace(content="You spent ₹2,000.")
            ]
        }

    authenticator = TokenAuthenticator(
        {
            USER_TOKEN: user_id,
            OTHER_TOKEN: other_user_id,
        }
    )
    application = create_app(
        service=service,
        chat_handler=fake_chat_handler,
        authenticator=authenticator,
        rate_limiter=InMemoryRateLimiter(requests=100),
    )
    return {
        "client": TestClient(application),
        "service": service,
        "user_id": user_id,
        "other_user_id": other_user_id,
        "account_id": account_id,
        "other_account_id": other_account_id,
        "food_id": food_id,
        "salary_id": salary_id,
        "grocery_id": grocery_id,
        "private_transaction_id": private_transaction_id,
        "chat_calls": chat_calls,
    }


def test_health_is_public_and_has_security_headers(api_context):
    response = api_context["client"].get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_dashboard_and_static_assets_are_served_with_strict_csp(api_context):
    client = api_context["client"]
    page = client.get("/")
    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert page.status_code == 200
    assert "Welcome to Khata" in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert "unsafe-inline" not in page.headers["content-security-policy"]
    assert script.status_code == 200
    assert "sessionStorage" in script.text
    assert "localStorage" not in script.text
    assert styles.status_code == 200
    assert "--green" in styles.text


def test_protected_endpoint_requires_a_valid_bearer_token(api_context):
    client = api_context["client"]

    missing = client.get("/api/v1/summary")
    invalid = client.get(
        "/api/v1/summary",
        headers={"Authorization": f"Bearer {'x' * 32}"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"


def test_summary_identity_comes_from_the_token(api_context):
    client = api_context["client"]

    user_summary = client.get("/api/v1/summary", headers=AUTH_HEADERS)
    other_summary = client.get(
        "/api/v1/summary",
        headers={"Authorization": f"Bearer {OTHER_TOKEN}"},
    )

    assert user_summary.status_code == 200
    assert user_summary.json()["expenses"] == 2000
    assert user_summary.json()["savings"] == 48000
    assert other_summary.json()["expenses"] == 9999


def test_account_and_category_options_are_user_scoped(api_context):
    client = api_context["client"]
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS)
    categories = client.get(
        "/api/v1/categories?category_type=expense",
        headers=AUTH_HEADERS,
    )

    assert accounts.status_code == 200
    assert [account["name"] for account in accounts.json()] == ["Bank"]
    assert categories.status_code == 200
    assert [category["name"] for category in categories.json()] == ["Food"]


def test_summary_rejects_reversed_dates(api_context):
    response = api_context["client"].get(
        "/api/v1/summary?start_date=2026-08-31&end_date=2026-08-01",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "must not be after" in response.json()["detail"]


def test_transaction_creation_and_pagination(api_context):
    client = api_context["client"]
    response = client.post(
        "/api/v1/transactions",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["account_id"],
            "category_id": api_context["food_id"],
            "transaction_type": "expense",
            "amount": 500,
            "description": "Lunch",
            "transaction_date": "2026-07-11",
        },
    )
    listed = client.get(
        "/api/v1/transactions?limit=1&offset=0",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    assert response.json()["id"] > 0
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["description"] == "Lunch"


def test_transaction_rejects_another_users_account(api_context):
    response = api_context["client"].post(
        "/api/v1/transactions",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["other_account_id"],
            "transaction_type": "expense",
            "amount": 500,
            "description": "Unauthorized",
        },
    )

    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


def test_transaction_update_reconciles_balance_and_returns_edit_fields(api_context):
    client = api_context["client"]
    transaction_id = api_context["grocery_id"]
    response = client.put(
        f"/api/v1/transactions/{transaction_id}",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["account_id"],
            "category_id": None,
            "transaction_type": "income",
            "amount": 3000,
            "description": "Refund",
            "transaction_date": "2026-07-12",
            "merchant": "Market",
            "notes": "Corrected entry",
        },
    )
    listed = client.get("/api/v1/transactions", headers=AUTH_HEADERS)
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS)
    summary = client.get("/api/v1/summary", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"id": transaction_id}
    updated = next(item for item in listed.json() if item["id"] == transaction_id)
    assert updated["transaction_type"] == "income"
    assert updated["account_id"] == api_context["account_id"]
    assert updated["category_id"] is None
    assert updated["notes"] == "Corrected entry"
    assert accounts.json()[0]["balance"] == 53000
    assert summary.json()["income"] == 53000
    assert summary.json()["expenses"] == 0


def test_transaction_delete_reverses_balance_and_is_user_scoped(api_context):
    client = api_context["client"]
    deleted = client.delete(
        f"/api/v1/transactions/{api_context['grocery_id']}",
        headers=AUTH_HEADERS,
    )
    forbidden = client.delete(
        f"/api/v1/transactions/{api_context['private_transaction_id']}",
        headers=AUTH_HEADERS,
    )
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS)
    listed = client.get("/api/v1/transactions", headers=AUTH_HEADERS)

    assert deleted.status_code == 204
    assert forbidden.status_code == 422
    assert "not found" in forbidden.json()["detail"].lower()
    assert accounts.json()[0]["balance"] == 50000
    assert all(
        item["id"] != api_context["grocery_id"]
        for item in listed.json()
    )


def test_preferences_can_be_read_and_updated(api_context):
    client = api_context["client"]
    response = client.put(
        "/api/v1/preferences",
        headers=AUTH_HEADERS,
        json={
            "language": "Marathi",
            "risk_preference": "moderate",
            "notification_enabled": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["language"] == "Marathi"
    assert response.json()["risk_preference"] == "moderate"
    assert response.json()["notification_enabled"] is False


def test_chat_uses_authenticated_user_and_forbids_body_user_id(api_context):
    client = api_context["client"]
    response = client.post(
        "/api/v1/chat",
        headers=AUTH_HEADERS,
        json={"thread_id": "monthly", "question": "What did I spend?"},
    )
    injected_identity = client.post(
        "/api/v1/chat",
        headers=AUTH_HEADERS,
        json={
            "thread_id": "monthly",
            "question": "What did I spend?",
            "user_id": api_context["other_user_id"],
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "You spent ₹2,000."
    assert api_context["chat_calls"] == [
        (api_context["user_id"], "monthly", "What did I spend?")
    ]
    assert injected_identity.status_code == 422


def test_rate_limit_is_enforced(api_context):
    application = create_app(
        service=api_context["service"],
        chat_handler=lambda **_: None,
        authenticator=TokenAuthenticator(
            {USER_TOKEN: api_context["user_id"]}
        ),
        rate_limiter=InMemoryRateLimiter(requests=1, window_seconds=60),
    )
    client = TestClient(application)

    assert client.get("/api/v1/preferences", headers=AUTH_HEADERS).status_code == 200
    limited = client.get("/api/v1/preferences", headers=AUTH_HEADERS)

    assert limited.status_code == 429
    assert limited.headers["retry-after"]


def test_oversized_request_is_rejected(api_context):
    response = api_context["client"].post(
        "/api/v1/chat",
        headers=AUTH_HEADERS,
        json={"thread_id": "large", "question": "x" * 70000},
    )

    assert response.status_code == 413
