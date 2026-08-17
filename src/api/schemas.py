from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    status: Literal["ok"]


class ReadinessResponse(StrictModel):
    status: Literal["ready", "unavailable"]
    checks: dict[str, Literal["ok", "unavailable"]]


class VersionResponse(StrictModel):
    version: str
    commit: str
    built_at: str


class RegisterRequest(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=15, max_length=128)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    account_name: str = Field(default="Main account", min_length=1, max_length=100)


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class LogoutRequest(StrictModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class PasswordConfirmation(StrictModel):
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=15, max_length=128)


class DeleteAccountRequest(StrictModel):
    password: str = Field(min_length=1, max_length=128)
    confirmation: Literal["DELETE"]


class SessionResponse(StrictModel):
    id: int
    created_at: datetime
    access_expires_at: datetime
    refresh_expires_at: datetime
    current: bool


class AuthResponse(StrictModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user_id: int
    name: str


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


class BudgetWrite(StrictModel):
    category_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    period: Literal["weekly", "monthly", "quarterly", "yearly", "custom"]
    start_date: date
    end_date: date


class BudgetResponse(BudgetWrite):
    id: int
    category: str
    spent: float
    remaining: float
    percent_used: float


class GoalWrite(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0, ge=0)
    target_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    status: Literal["active", "completed", "paused"] = "active"


class GoalResponse(GoalWrite):
    id: int
    remaining: float
    percent_complete: float


class RecurringTransactionWrite(StrictModel):
    account_id: int = Field(gt=0)
    category_id: int | None = Field(default=None, gt=0)
    transaction_type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval_count: int = Field(default=1, ge=1, le=365)
    next_date: date
    end_date: date | None = None
    merchant: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class RecurringTransactionResponse(RecurringTransactionWrite):
    id: int
    last_generated_date: date | None
    account: str
    category: str | None


class RecurringProcessRequest(StrictModel):
    through_date: date | None = None


class RecurringProcessResponse(StrictModel):
    generated_count: int
    transaction_ids: list[int]


class TransactionImportResponse(StrictModel):
    batch_id: int
    imported_count: int
    duplicate: bool
    transaction_ids: list[int] = Field(default_factory=list)


class NotificationResponse(StrictModel):
    id: int
    notification_type: Literal[
        "budget_warning",
        "budget_exceeded",
        "goal_completed",
        "recurring_generated",
        "import_completed",
    ]
    title: str
    message: str
    is_read: bool
    created_at: datetime
