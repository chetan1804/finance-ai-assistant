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


def test_request_id_is_returned_and_untrusted_values_are_replaced(api_context):
    client = api_context["client"]
    accepted = client.get("/health", headers={"X-Request-ID": "request-123"})
    replaced = client.get("/health", headers={"X-Request-ID": "unsafe request"})

    assert accepted.headers["x-request-id"] == "request-123"
    assert replaced.headers["x-request-id"] != "unsafe request"
    assert len(replaced.headers["x-request-id"]) == 32


def test_metrics_use_route_templates_and_include_readiness(api_context):
    client = api_context["client"]
    client.get("/ready")
    client.delete(
        "/api/v1/transactions/999999",
        headers=AUTH_HEADERS,
    )

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "finance_http_requests_total" in metrics.text
    assert 'route="/api/v1/transactions/{transaction_id}"' in metrics.text
    assert 'dependency="database"} 1.0' in metrics.text
    assert 'route="/api/v1/transactions/999999"' not in metrics.text


def test_readiness_reports_dependency_status(api_context):
    response = api_context["client"].get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "checkpoints": "ok",
            "rate_limiter": "ok",
        },
    }


def test_readiness_returns_503_when_a_dependency_is_unavailable(tmp_path):
    class UnavailableHealthChecker:
        @staticmethod
        def check():
            return {
                "status": "unavailable",
                "checks": {
                    "database": "ok",
                    "checkpoints": "ok",
                    "rate_limiter": "unavailable",
                },
            }

    application = create_app(
        service=FinanceService(tmp_path / "readiness.db"),
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({USER_TOKEN: 1}),
        rate_limiter=InMemoryRateLimiter(requests=100),
        health_checker=UnavailableHealthChecker(),
    )
    response = TestClient(application).get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_unhandled_errors_return_generic_response_with_request_id(tmp_path):
    application = create_app(
        service=FinanceService(tmp_path / "errors.db"),
        chat_handler=lambda **_kwargs: None,
        authenticator=TokenAuthenticator({USER_TOKEN: 1}),
        rate_limiter=InMemoryRateLimiter(requests=100),
    )

    @application.get("/test-unhandled-error")
    def unhandled_error():
        raise RuntimeError("internal database detail")

    response = TestClient(
        application,
        raise_server_exceptions=False,
    ).get(
        "/test-unhandled-error",
        headers={"X-Request-ID": "failure-123"},
    )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "failure-123"
    assert response.json() == {
        "detail": "Internal server error.",
        "request_id": "failure-123",
    }
    assert "internal database detail" not in response.text


def test_dashboard_and_static_assets_are_served_with_strict_csp(api_context):
    client = api_context["client"]
    page = client.get("/")
    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert page.status_code == 200
    assert "Welcome to ArthNivo" in page.text or 'id="root"' in page.text
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


def test_budget_reports_category_spending_and_supports_update(api_context):
    client = api_context["client"]
    created = client.post(
        "/api/v1/budgets",
        headers=AUTH_HEADERS,
        json={
            "category_id": api_context["food_id"],
            "amount": 5000,
            "period": "monthly",
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )
    budget_id = created.json()["id"]
    listed = client.get("/api/v1/budgets", headers=AUTH_HEADERS)

    assert created.status_code == 201
    assert listed.json()[0]["spent"] == 2000
    assert listed.json()[0]["remaining"] == 3000
    assert listed.json()[0]["percent_used"] == 40

    updated = client.put(
        f"/api/v1/budgets/{budget_id}",
        headers=AUTH_HEADERS,
        json={
            "category_id": api_context["food_id"],
            "amount": 4000,
            "period": "monthly",
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )
    assert updated.json() == {"id": budget_id}
    assert client.get("/api/v1/budgets", headers=AUTH_HEADERS).json()[0]["percent_used"] == 50


def test_financial_goals_are_user_scoped_and_report_progress(api_context):
    client = api_context["client"]
    created = client.post(
        "/api/v1/goals",
        headers=AUTH_HEADERS,
        json={
            "name": "Emergency fund",
            "target_amount": 100000,
            "current_amount": 25000,
            "target_date": "2027-08-01",
            "priority": "high",
            "status": "active",
        },
    )
    goals = client.get("/api/v1/goals", headers=AUTH_HEADERS)
    other_goals = client.get(
        "/api/v1/goals",
        headers={"Authorization": f"Bearer {OTHER_TOKEN}"},
    )

    assert created.status_code == 201
    assert goals.json()[0]["remaining"] == 75000
    assert goals.json()[0]["percent_complete"] == 25
    assert other_goals.json() == []


def test_recurring_processing_is_repeatable_and_updates_balance(api_context):
    client = api_context["client"]
    created = client.post(
        "/api/v1/recurring-transactions",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["account_id"],
            "category_id": api_context["food_id"],
            "transaction_type": "expense",
            "amount": 100,
            "description": "Subscription",
            "frequency": "monthly",
            "interval_count": 1,
            "next_date": "2026-06-30",
            "end_date": "2026-08-31",
            "is_active": True,
        },
    )
    first = client.post(
        "/api/v1/recurring-transactions/process",
        headers=AUTH_HEADERS,
        json={"through_date": "2026-08-31"},
    )
    second = client.post(
        "/api/v1/recurring-transactions/process",
        headers=AUTH_HEADERS,
        json={"through_date": "2026-08-31"},
    )
    schedules = client.get(
        "/api/v1/recurring-transactions",
        headers=AUTH_HEADERS,
    )
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS)

    assert created.status_code == 201
    assert first.json()["generated_count"] == 3
    assert second.json()["generated_count"] == 0
    assert schedules.json()[0]["is_active"] is False
    assert schedules.json()[0]["last_generated_date"] == "2026-08-30"
    assert accounts.json()[0]["balance"] == 47700


def test_loan_emi_schedule_generates_an_expense_with_loan_metadata(api_context):
    client = api_context["client"]
    created = client.post(
        "/api/v1/recurring-transactions",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["account_id"],
            "category_id": None,
            "transaction_type": "expense",
            "amount": 5000,
            "description": "Home loan payment",
            "frequency": "monthly",
            "next_date": "2026-08-15",
            "schedule_kind": "loan_emi",
            "loan_type": "home",
            "lender": "Example Bank",
        },
    )
    generated = client.post(
        "/api/v1/recurring-transactions/process",
        headers=AUTH_HEADERS,
        json={"through_date": "2026-08-31"},
    )
    schedules = client.get(
        "/api/v1/recurring-transactions", headers=AUTH_HEADERS
    ).json()
    summary = client.get("/api/v1/summary", headers=AUTH_HEADERS).json()
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS).json()

    assert created.status_code == 201
    assert generated.json()["generated_count"] == 1
    assert schedules[0]["schedule_kind"] == "loan_emi"
    assert schedules[0]["loan_type"] == "home"
    assert schedules[0]["category"] == "Loan EMI"
    assert summary["expenses"] == 7000
    assert accounts[0]["balance"] == 43000
    deleted = client.delete(
        f"/api/v1/recurring-transactions/{schedules[0]['id']}",
        headers=AUTH_HEADERS,
    )
    assert deleted.status_code == 204
    assert api_context["service"].get_total_loan_emi(
        api_context["user_id"], loan_type="home"
    ) == 5000


def test_investment_contributions_debit_cash_without_inflating_expenses(api_context):
    client = api_context["client"]
    created = client.post(
        "/api/v1/investments",
        headers=AUTH_HEADERS,
        json={
            "account_id": api_context["account_id"],
            "investment_type": "mutual_fund_sip",
            "name": "Index SIP",
            "provider": "Example AMC",
            "contribution_amount": 1000,
            "frequency": "monthly",
            "next_date": "2026-07-15",
            "status": "active",
        },
    )
    investment_id = created.json()["id"]
    processed = client.post(
        "/api/v1/investments/process",
        headers=AUTH_HEADERS,
        json={"through_date": "2026-08-15"},
    )
    client.put(
        f"/api/v1/investments/{investment_id}/value",
        headers=AUTH_HEADERS,
        json={"current_value": 2500},
    )
    manual = client.post(
        f"/api/v1/investments/{investment_id}/contributions",
        headers=AUTH_HEADERS,
        json={"amount": 500, "contribution_date": "2026-08-16"},
    )
    investments = client.get("/api/v1/investments", headers=AUTH_HEADERS).json()
    investment_summary = client.get(
        "/api/v1/investments/summary", headers=AUTH_HEADERS
    ).json()
    finance_summary = client.get("/api/v1/summary", headers=AUTH_HEADERS).json()
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS).json()
    contributions = client.get(
        f"/api/v1/investments/{investment_id}/contributions",
        headers=AUTH_HEADERS,
    ).json()

    assert created.status_code == 201
    assert processed.json()["generated_count"] == 2
    assert len(processed.json()["contribution_ids"]) == 2
    assert manual.status_code == 201
    assert investments[0]["total_contributed"] == 2500
    assert investment_summary["total_contributed"] == 2500
    assert investment_summary["current_value"] == 3000
    assert investment_summary["gain_loss"] == 500
    assert finance_summary["expenses"] == 2000
    assert accounts[0]["balance"] == 45500
    assert len(contributions) == 3


def test_csv_import_is_atomic_duplicate_safe_and_creates_notifications(api_context):
    client = api_context["client"]
    client.post(
        "/api/v1/budgets",
        headers=AUTH_HEADERS,
        json={
            "category_id": api_context["food_id"], "amount": 2500,
            "period": "monthly", "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )
    content = (
        "transaction_date,transaction_type,amount,description,merchant,category,notes\n"
        "2026-07-12,income,1000,Refund,Market,,Returned item\n"
        "2026-07-13,expense,600,Dinner,Cafe,Food,Team meal\n"
    )
    path = (
        f"/api/v1/import/transactions?account_id={api_context['account_id']}"
        "&source_name=bank.csv"
    )
    imported = client.post(
        path, headers={**AUTH_HEADERS, "Content-Type": "text/csv"}, content=content
    )
    duplicate = client.post(
        path, headers={**AUTH_HEADERS, "Content-Type": "text/csv"}, content=content
    )
    notifications = client.get("/api/v1/notifications", headers=AUTH_HEADERS)
    accounts = client.get("/api/v1/accounts", headers=AUTH_HEADERS)

    assert imported.status_code == 200
    assert imported.json()["imported_count"] == 2
    assert imported.json()["duplicate"] is False
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["imported_count"] == 0
    assert accounts.json()[0]["balance"] == 48400
    assert {item["notification_type"] for item in notifications.json()} == {
        "budget_exceeded", "import_completed"
    }

    notification_id = notifications.json()[0]["id"]
    assert client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=AUTH_HEADERS
    ).status_code == 204
    assert client.get(
        "/api/v1/notifications?unread_only=true", headers=AUTH_HEADERS
    ).json() == [
        item for item in notifications.json()[1:] if not item["is_read"]
    ]


def test_invalid_csv_import_does_not_save_partial_rows(api_context):
    client = api_context["client"]
    before = client.get("/api/v1/transactions", headers=AUTH_HEADERS).json()
    content = (
        "date,type,amount,description\n"
        "2026-07-12,income,1000,Valid\n"
        "not-a-date,expense,500,Invalid\n"
    )
    response = client.post(
        f"/api/v1/import/transactions?account_id={api_context['account_id']}",
        headers={**AUTH_HEADERS, "Content-Type": "text/csv"},
        content=content,
    )
    after = client.get("/api/v1/transactions", headers=AUTH_HEADERS).json()

    assert response.status_code == 422
    assert "CSV row 3" in response.json()["detail"]
    assert after == before


def test_notification_preference_suppresses_new_notifications(api_context):
    client = api_context["client"]
    client.put(
        "/api/v1/preferences",
        headers=AUTH_HEADERS,
        json={"notification_enabled": False},
    )
    created = client.post(
        "/api/v1/goals",
        headers=AUTH_HEADERS,
        json={
            "name": "Already funded",
            "target_amount": 1000,
            "current_amount": 1000,
            "priority": "medium",
            "status": "active",
        },
    )

    assert created.status_code == 201
    assert client.get("/api/v1/notifications", headers=AUTH_HEADERS).json() == []


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
