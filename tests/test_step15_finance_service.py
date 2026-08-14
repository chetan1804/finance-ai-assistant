import pytest

from src.database.db import initialize_database
from src.database.finance_service import FinanceService


@pytest.fixture
def personalized_service(tmp_path):
    database_path = tmp_path / "finance.db"
    initialize_database(database_path)
    service = FinanceService(database_path)

    user_id = service.create_user("Asha", "asha@example.com", "INR")
    other_user_id = service.create_user("Ravi", "ravi@example.com", "USD")
    account_id = service.create_account(user_id, "Bank", "savings")
    other_account_id = service.create_account(
        other_user_id,
        "Other Bank",
        "savings",
    )
    food_id = service.create_category(user_id, "Food", "expense")

    service.add_transaction(
        user_id,
        account_id,
        food_id,
        "income",
        50000,
        "Salary",
        "2026-07-01",
    )
    service.add_transaction(
        user_id,
        account_id,
        food_id,
        "expense",
        1200,
        "Groceries",
        "2026-07-10",
    )
    service.add_transaction(
        user_id,
        account_id,
        food_id,
        "expense",
        800,
        "Dinner",
        "2026-08-02",
    )
    service.add_transaction(
        other_user_id,
        other_account_id,
        None,
        "expense",
        9999,
        "Other user expense",
        "2026-07-10",
    )

    return service, user_id, other_user_id, account_id, other_account_id


def test_queries_are_scoped_by_user_and_date(personalized_service):
    service, user_id, _, _, _ = personalized_service

    assert service.get_total_income(user_id) == 50000
    assert service.get_total_expenses(user_id) == 2000
    assert service.get_total_expenses(
        user_id,
        start_date="2026-07-01",
        end_date="2026-07-31",
    ) == 1200
    assert service.get_category_expenses(
        user_id,
        "food",
        start_date="2026-07-01",
        end_date="2026-07-31",
    ) == 1200


def test_preferences_have_defaults_and_can_be_updated(personalized_service):
    service, user_id, _, _, _ = personalized_service

    assert service.get_user_preferences(user_id)["currency"] == "INR"

    preferences = service.set_user_preferences(
        user_id,
        language="Marathi",
        currency="INR",
        monthly_income=50000,
        risk_preference="moderate",
        notification_enabled=False,
    )

    assert preferences["language"] == "Marathi"
    assert preferences["monthly_income"] == 50000
    assert preferences["risk_preference"] == "moderate"
    assert preferences["notification_enabled"] is False


def test_transaction_rejects_another_users_account(personalized_service):
    service, user_id, _, _, other_account_id = personalized_service

    with pytest.raises(ValueError, match="does not belong"):
        service.add_transaction(
            user_id,
            other_account_id,
            None,
            "expense",
            100,
            "Invalid transaction",
            "2026-08-03",
        )
