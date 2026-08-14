from langchain_core.tools import tool

from src.services.finance_service import FinanceService


# =========================================================
# CURRENT APPLICATION USER
# =========================================================

CURRENT_USER_ID = 2


# =========================================================
# FINANCE SERVICE
# =========================================================

finance_service = FinanceService()


# =========================================================
# TOTAL INCOME
# =========================================================

@tool
def get_total_income() -> float:
    """
    Get the total income for the current user.
    """

    return finance_service.get_total_income(
        CURRENT_USER_ID
    )


# =========================================================
# TOTAL EXPENSES
# =========================================================

@tool
def get_total_expenses() -> float:
    """
    Get the total expenses for the current user.
    """

    return finance_service.get_total_expenses(
        CURRENT_USER_ID
    )


# =========================================================
# TOTAL SAVINGS
# =========================================================

@tool
def get_total_savings() -> float:
    """
    Get the total savings for the current user.
    """

    return finance_service.get_savings(
        CURRENT_USER_ID
    )


# =========================================================
# CATEGORY EXPENSES
# =========================================================

@tool
def get_category_expenses(
    category: str
) -> float:
    """
    Get expenses for a specific category
    for the current user.
    """

    return finance_service.get_category_expenses(
        CURRENT_USER_ID,
        category
    )


# =========================================================
# LARGEST EXPENSE
# =========================================================

@tool
def get_largest_expense():
    """
    Get the largest expense for the current user.
    """

    return finance_service.get_largest_expense(
        CURRENT_USER_ID
    )


# =========================================================
# MERCHANT EXPENSES
# =========================================================

@tool
def get_merchant_expenses(
    merchant: str
) -> float:
    """
    Get expenses for a specific merchant
    for the current user.
    """

    return finance_service.get_merchant_expenses(
        CURRENT_USER_ID,
        merchant
    )


# =========================================================
# TRANSACTION COUNT
# =========================================================

@tool
def get_transaction_count() -> int:
    """
    Get the transaction count for the current user.
    """

    return finance_service.get_transaction_count(
        CURRENT_USER_ID
    )