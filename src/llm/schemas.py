from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field


class TransactionExtraction(BaseModel):

    amount: float = Field(
        description="Transaction amount"
    )

    type: Literal[
        "income",
        "expense",
        "transfer"
    ] = Field(
        description="Transaction type"
    )

    merchant: str = Field(
        description="Merchant or source of transaction"
    )

    description: str = Field(
        description="Short transaction description"
    )

    category: str = Field(
        description="Financial category"
    )

    date: Date = Field(
        description="Transaction date"
    )