from src.llm.llm_client import get_llm

from src.tools.finance_tools import (
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
)


TOOLS = [
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
]


def get_tool_enabled_llm():

    llm = get_llm()

    return llm.bind_tools(
        TOOLS
    )