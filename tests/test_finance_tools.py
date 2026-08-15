import pytest

import src.tools.finance_tools as finance_tools_module
from src.database.db import initialize_database
from src.database.finance_service import FinanceService
from src.tools.finance_tools import (
    get_category_expenses,
    get_total_expenses,
    get_total_income,
    get_total_savings,
)


@pytest.fixture(autouse=True)
def isolated_finance_tools(tmp_path, monkeypatch):
    database_path = tmp_path / "finance-tools.db"
    initialize_database(database_path)
    service = FinanceService(database_path)
    service.create_user("First User", "first@example.com")
    user_id = service.create_user("Tool User", "tools@example.com")
    account_id = service.create_account(user_id, "Bank", "checking")
    food_id = service.create_category(user_id, "Food", "expense")
    service.add_transaction(
        user_id,
        account_id,
        None,
        "income",
        5000,
        "Salary",
        "2026-08-01",
    )
    service.add_transaction(
        user_id,
        account_id,
        food_id,
        "expense",
        1200,
        "Groceries",
        "2026-08-02",
    )
    assert user_id == finance_tools_module.CURRENT_USER_ID
    monkeypatch.setattr(finance_tools_module, "finance_service", service)


def test_total_income():

    result = get_total_income.invoke({})

    assert result == 5000


def test_total_expenses():

    result = get_total_expenses.invoke({})

    assert result == 1200


def test_total_savings():

    result = get_total_savings.invoke({})

    assert result == 3800


def test_category_expenses():

    result = get_category_expenses.invoke({
        "category": "Food"
    })

    assert result == 1200
