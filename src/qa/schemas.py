from typing import Literal, Optional

from pydantic import BaseModel, Field


class FinancialQuery(BaseModel):

    intent: Literal[
        "total_income",
        "total_expenses",
        "total_savings",
        "category_expenses",
        "largest_expense",
        "merchant_expenses",
        "transaction_count"
    ] = Field(
        description="The financial question intent"
    )

    category: Optional[str] = Field(
        default=None,
        description="Expense category if applicable"
    )

    merchant: Optional[str] = Field(
        default=None,
        description="Merchant if applicable"
    )