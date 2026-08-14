from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    status: Literal["ok"]


class ChatRequest(StrictModel):
    thread_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(StrictModel):
    thread_id: str
    answer: str


class SummaryResponse(StrictModel):
    currency: str
    start_date: date | None
    end_date: date | None
    income: float
    expenses: float
    savings: float


class PreferencesResponse(StrictModel):
    language: str
    currency: str
    monthly_income: float | None
    risk_preference: str | None
    notification_enabled: bool


class PreferencesUpdate(StrictModel):
    language: str | None = Field(default=None, min_length=1, max_length=50)
    currency: str | None = Field(default=None, min_length=3, max_length=16)
    monthly_income: float | None = Field(default=None, gt=0)
    risk_preference: str | None = Field(default=None, max_length=50)
    notification_enabled: bool | None = None


class TransactionCreate(StrictModel):
    account_id: int = Field(gt=0)
    category_id: int | None = Field(default=None, gt=0)
    transaction_type: Literal["income", "expense", "transfer"]
    amount: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date | None = None
    merchant: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class TransactionCreated(StrictModel):
    id: int


class TransactionResponse(StrictModel):
    id: int
    account_id: int
    category_id: int | None
    amount: float
    transaction_type: str
    description: str | None
    transaction_date: date
    merchant: str | None
    notes: str | None
    category: str | None
    account: str


class AccountResponse(StrictModel):
    id: int
    name: str
    account_type: str
    institution: str | None
    balance: float
    currency: str


class CategoryResponse(StrictModel):
    id: int
    name: str
    category_type: Literal["income", "expense"]
    parent_id: int | None
