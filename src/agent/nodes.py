from langchain_core.messages import SystemMessage

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


# ============================================================
# TOOLS
# ============================================================

TOOLS = [
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
]


# ============================================================
# LLM
# ============================================================

llm = get_llm().bind_tools(
    TOOLS
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_MESSAGE = """
You are a personal finance assistant.

You help users understand their financial transactions.

Rules:

1. All monetary values are in Indian Rupees (INR).

2. Use ₹ when displaying money.

3. Never invent financial numbers.

4. If the question requires financial data,
   use the appropriate finance tool.

5. Trust the database tool result.

6. Do not guess financial values.

7. Keep answers simple and concise.

Examples:

8000 -> ₹8,000

25000 -> ₹25,000

125000 -> ₹1,25,000
"""


# ============================================================
# LLM NODE
# ============================================================

def call_llm(state):

    messages = state["messages"]

    messages_with_system = [
        SystemMessage(
            content=SYSTEM_MESSAGE
        )
    ] + messages

    response = llm.invoke(
        messages_with_system
    )

    return {
        "messages": [response]
    }