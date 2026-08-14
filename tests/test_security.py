import math

import pytest

from src.database.db import initialize_database
from src.database.finance_service import FinanceService
from src.security.validation import validate_chat_request


@pytest.fixture
def secure_service(tmp_path):
    database_path = tmp_path / "security.db"
    initialize_database(database_path)
    service = FinanceService(database_path)

    user_id = service.create_user("Asha", "ASHA@example.com")
    other_user_id = service.create_user("Ravi", "ravi@example.com")
    account_id = service.create_account(user_id, "Bank", "savings")
    other_account_id = service.create_account(
        other_user_id,
        "Other Bank",
        "savings",
    )
    category_id = service.create_category(user_id, "Food", "expense")
    other_category_id = service.create_category(
        other_user_id,
        "Private",
        "expense",
    )
    return {
        "service": service,
        "user_id": user_id,
        "other_user_id": other_user_id,
        "account_id": account_id,
        "other_account_id": other_account_id,
        "category_id": category_id,
        "other_category_id": other_category_id,
    }


@pytest.mark.parametrize("amount", [math.nan, math.inf, -math.inf, -1, 0])
def test_unsafe_transaction_amounts_are_rejected(secure_service, amount):
    service = secure_service["service"]

    with pytest.raises(ValueError, match="finite number greater than zero"):
        service.add_transaction(
            secure_service["user_id"],
            secure_service["account_id"],
            secure_service["category_id"],
            "expense",
            amount,
            "Unsafe amount",
            "2026-08-01",
        )


def test_cross_user_parent_category_is_rejected(secure_service):
    service = secure_service["service"]

    with pytest.raises(ValueError, match="parent category"):
        service.create_category(
            secure_service["user_id"],
            "Child",
            "expense",
            parent_id=secure_service["other_category_id"],
        )


def test_query_dates_are_strict_and_ordered(secure_service):
    service = secure_service["service"]

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        service.get_total_expenses(
            secure_service["user_id"],
            start_date="2026-01-01' OR 1=1 --",
        )

    with pytest.raises(ValueError, match="must not be after"):
        service.get_total_expenses(
            secure_service["user_id"],
            start_date="2026-08-31",
            end_date="2026-08-01",
        )


def test_parameterized_category_query_does_not_execute_sql(secure_service):
    service = secure_service["service"]
    injection = "Food'); DROP TABLE users; --"

    assert service.get_category_expenses(
        secure_service["user_id"],
        injection,
    ) == 0
    assert service.get_user_preferences(secure_service["user_id"])


@pytest.mark.parametrize(
    ("user_id", "thread_id", "question", "error"),
    [
        (True, "thread-1", "Show expenses", "positive integer"),
        (1, "../other-user", "Show expenses", "thread_id"),
        (1, "thread-1", "hello\x00world", "unsupported characters"),
        (1, "thread-1", "x" * 2001, "at most 2000"),
    ],
)
def test_chat_boundary_rejects_unsafe_input(
    user_id,
    thread_id,
    question,
    error,
):
    with pytest.raises(ValueError, match=error):
        validate_chat_request(user_id, thread_id, question)


def test_chat_boundary_normalizes_safe_input():
    assert validate_chat_request(
        1,
        "monthly-review",
        "  How much did I spend?  ",
    ) == (1, "monthly-review", "How much did I spend?")


def test_profile_fields_are_validated(secure_service):
    service = secure_service["service"]

    with pytest.raises(ValueError, match="three-letter ISO code"):
        service.set_user_preferences(
            secure_service["user_id"],
            currency="INR<script>",
        )

    with pytest.raises(ValueError, match="boolean"):
        service.set_user_preferences(
            secure_service["user_id"],
            notification_enabled=1,
        )
