from langchain_core.tools import tool

from src.services.finance_service import FinanceService


finance_service = FinanceService()


@tool
def get_total_income() -> float:
    """
    Get the total income recorded
    in the finance database.
    """

    return finance_service.total_income()


@tool
def get_total_expenses() -> float:
    """
    Get the total expenses recorded
    in the finance database.
    """

    return finance_service.total_expenses()


@tool
def get_total_savings() -> float:
    """
    Calculate total savings as income
    minus expenses.
    """

    return finance_service.total_savings()


@tool
def get_category_expenses(
    category: str
) -> float:
    """
    Get total expenses for a specific
    financial category.

    Examples:
    Food
    Transport
    Shopping
    Bills
    Entertainment
    """

    return finance_service.category_expenses(
        category
    )


@tool
def get_largest_expense():
    """
    Get the largest expense transaction.
    """

    return finance_service.largest_expense()


@tool
def get_merchant_expenses(
    merchant: str
) -> float:
    """
    Get total expenses for a specific merchant.
    """

    return finance_service.merchant_expenses(
        merchant
    )


@tool
def get_transaction_count() -> int:
    """
    Get the total number of transactions.
    """

    return finance_service.transaction_count()