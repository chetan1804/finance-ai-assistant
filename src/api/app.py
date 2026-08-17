from datetime import date
import os
from pathlib import Path
import time
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from src.api.auth import TokenAuthenticator
from src.api.deployment_security import DeploymentSecuritySettings
from src.api.health import ProductionHealthChecker
from src.api.observability import Observability, request_id_from_header
from src.api.rate_limit import create_rate_limiter
from src.api.release import ReleaseMetadata
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    AccountResponse,
    AuthResponse,
    CategoryResponse,
    HealthResponse,
    ReadinessResponse,
    LoginRequest,
    LogoutRequest,
    DeleteAccountRequest,
    PasswordChangeRequest,
    PasswordConfirmation,
    PreferencesResponse,
    PreferencesUpdate,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
    SummaryResponse,
    TransactionCreate,
    TransactionCreated,
    TransactionResponse,
    VersionResponse,
    BudgetWrite,
    BudgetResponse,
    GoalWrite,
    GoalResponse,
    RecurringTransactionWrite,
    RecurringTransactionResponse,
    RecurringProcessRequest,
    RecurringProcessResponse,
    TransactionImportResponse,
    NotificationResponse,
    InvestmentWrite,
    InvestmentResponse,
    InvestmentContributionCreate,
    InvestmentContributionResponse,
    InvestmentProcessResponse,
    InvestmentValueUpdate,
    InvestmentSummaryResponse,
)
from src.database.db import initialize_database
from src.database.finance_service import FinanceService
from src.security.auth_service import (
    AuthenticationError,
    AuthService,
    ReauthenticationError,
    RegistrationError,
)
from src.services.transaction_import import (
    MAX_IMPORT_BYTES,
    parse_transaction_csv,
    transactions_to_csv,
)


MAX_REQUEST_BYTES = 64 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_UI_DIRECTORY = Path(__file__).resolve().parents[1] / "ui" / "static"


def get_ui_directory():
    configured = os.getenv("FINANCE_UI_DIST")
    return Path(configured).expanduser() if configured else LEGACY_UI_DIRECTORY


def _default_chat_handler(user_id, thread_id, question):
    from src.agents.finance_agent import chat

    return chat(user_id, thread_id, question)


def create_app(
    *,
    service=None,
    chat_handler=None,
    authenticator=None,
    auth_service=None,
    rate_limiter=None,
    auth_rate_limiter=None,
    health_checker=None,
    observability=None,
    deployment_settings=None,
    release_metadata=None,
):
    """Create the API with injectable dependencies for deterministic tests."""
    load_dotenv()
    service = service or FinanceService()
    initialize_database(service.database_path)
    auth_service = auth_service or AuthService(service.database_path)
    ui_directory = get_ui_directory()
    if not (ui_directory / "index.html").is_file():
        raise RuntimeError(f"Frontend build not found at {ui_directory}.")
    chat_handler = chat_handler or _default_chat_handler
    authenticator = authenticator or TokenAuthenticator.from_environment(auth_service)
    rate_limiter = rate_limiter or create_rate_limiter(namespace="api")
    auth_rate_limiter = auth_rate_limiter or create_rate_limiter(
        requests=10,
        window_seconds=60,
        namespace="auth",
    )
    health_checker = health_checker or ProductionHealthChecker(
        database_path=service.database_path,
        rate_limiters=(rate_limiter, auth_rate_limiter),
    )
    observability = observability or Observability()
    deployment_settings = (
        deployment_settings or DeploymentSecuritySettings.from_environment()
    )
    release_metadata = release_metadata or ReleaseMetadata.from_environment()

    application = FastAPI(
        title="ArthNivo API",
        version=release_metadata.version,
        description="Authenticated access to personalized financial insights.",
        middleware=deployment_settings.middleware(),
        root_path=deployment_settings.root_path,
    )
    application.state.observability = observability
    application.state.deployment_settings = deployment_settings
    application.state.release_metadata = release_metadata
    application.mount(
        "/static",
        StaticFiles(directory=LEGACY_UI_DIRECTORY),
        name="static",
    )
    if (ui_directory / "assets").is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=ui_directory / "assets"),
            name="react-assets",
        )

    def apply_security_response_headers(request, response):
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if deployment_settings.hsts_seconds and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={deployment_settings.hsts_seconds}; includeSubDomains"
            )
        if (
            request.url.path == "/"
            or request.url.path.startswith("/static/")
            or request.url.path.startswith("/assets/")
        ):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; "
                "font-src 'self'; object-src 'none'; base-uri 'none'; "
                "frame-ancestors 'none'"
            )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        request.state.request_id = request_id_from_header(
            request.headers.get("x-request-id")
        )
        started_at = time.perf_counter()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > MAX_REQUEST_BYTES
            except ValueError:
                too_large = True
            if too_large:
                response = JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "Request body is too large."},
                )
                apply_security_response_headers(request, response)
                observability.record_request(
                    request,
                    response.status_code,
                    started_at,
                )
                return response

        try:
            response = await call_next(request)
        except Exception as error:
            observability.logger.error(
                "unhandled_request_error",
                extra={
                    "request_id": request.state.request_id,
                    "error_type": type(error).__name__,
                },
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error.",
                    "request_id": request.state.request_id,
                },
            )
        apply_security_response_headers(request, response)
        observability.record_request(request, response.status_code, started_at)
        return response

    @application.exception_handler(ValueError)
    async def value_error_handler(_request: Request, error: ValueError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(error)},
        )

    @application.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        _request: Request,
        error: AuthenticationError,
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(error)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @application.exception_handler(RegistrationError)
    async def registration_error_handler(
        _request: Request,
        error: RegistrationError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(error)},
        )

    @application.exception_handler(ReauthenticationError)
    async def reauthentication_error_handler(
        _request: Request,
        error: ReauthenticationError,
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(error)},
        )

    def current_user(
        user_id: int = Depends(authenticator.authenticate),
    ) -> int:
        rate_limiter.check(user_id)
        return user_id

    def auth_request_limit(request: Request):
        host = request.client.host if request.client else "unknown"
        auth_rate_limiter.check(f"auth:{host}")

    @application.get("/health", response_model=HealthResponse)
    def health():
        return {"status": "ok"}

    @application.get("/version", response_model=VersionResponse)
    def version():
        return release_metadata.response()

    @application.get("/ready", response_model=ReadinessResponse)
    def readiness(response: Response):
        result = health_checker.check()
        observability.record_readiness(result["checks"])
        if result["status"] != "ready":
            observability.logger.warning(
                "dependency_readiness_failed",
                extra={"checks": result["checks"]},
            )
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return result

    @application.get("/metrics", include_in_schema=False)
    def metrics():
        payload, content_type = observability.metrics_payload()
        return Response(content=payload, media_type=content_type)

    @application.post(
        "/api/v1/auth/register",
        response_model=AuthResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(auth_request_limit)],
    )
    def register(payload: RegisterRequest):
        return auth_service.register(
            payload.name,
            payload.email,
            payload.password,
            payload.currency,
            payload.account_name,
        )

    @application.post(
        "/api/v1/auth/login",
        response_model=AuthResponse,
        dependencies=[Depends(auth_request_limit)],
    )
    def login(payload: LoginRequest):
        return auth_service.login(payload.email, payload.password)

    @application.post(
        "/api/v1/auth/refresh",
        response_model=AuthResponse,
        dependencies=[Depends(auth_request_limit)],
    )
    def refresh(payload: RefreshRequest):
        return auth_service.refresh(payload.refresh_token)

    @application.post(
        "/api/v1/auth/logout",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def logout(
        payload: LogoutRequest,
        user_id: int = Depends(current_user),
    ):
        auth_service.logout(user_id, payload.refresh_token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.patch(
        "/api/v1/auth/password",
        response_model=AuthResponse,
    )
    def change_password(
        payload: PasswordChangeRequest,
        user_id: int = Depends(current_user),
    ):
        return auth_service.change_password(
            user_id,
            payload.current_password,
            payload.new_password,
        )

    @application.get(
        "/api/v1/auth/sessions",
        response_model=list[SessionResponse],
    )
    def sessions(
        request: Request,
        user_id: int = Depends(current_user),
    ):
        authorization = request.headers.get("authorization", "")
        access_token = authorization.partition(" ")[2]
        return auth_service.list_sessions(user_id, access_token)

    @application.delete(
        "/api/v1/auth/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def revoke_session(
        session_id: int,
        user_id: int = Depends(current_user),
    ):
        auth_service.revoke_session(user_id, session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/api/v1/auth/logout-all",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def logout_all(
        payload: PasswordConfirmation,
        user_id: int = Depends(current_user),
    ):
        auth_service.revoke_all_sessions(user_id, payload.password)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post("/api/v1/privacy/export")
    def export_personal_data(
        payload: PasswordConfirmation,
        user_id: int = Depends(current_user),
    ):
        return auth_service.export_user_data(user_id, payload.password)

    @application.post("/api/v1/export/transactions")
    def export_transactions_csv(
        payload: PasswordConfirmation,
        user_id: int = Depends(current_user),
    ):
        exported = auth_service.export_user_data(user_id, payload.password)
        accounts_by_id = {
            item["id"]: item["name"] for item in exported["accounts"]
        }
        categories_by_id = {
            item["id"]: item["name"] for item in exported["categories"]
        }
        transactions = [
            {
                **item,
                "account": accounts_by_id.get(item["account_id"], ""),
                "category": categories_by_id.get(item["category_id"], ""),
            }
            for item in exported["transactions"]
        ]
        return Response(
            content=transactions_to_csv(transactions),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="arthnivo-transactions-{date.today().isoformat()}.csv"'
                )
            },
        )

    @application.post(
        "/api/v1/import/transactions",
        response_model=TransactionImportResponse,
    )
    async def import_transactions_csv(
        request: Request,
        account_id: int = Query(gt=0),
        source_name: str = Query(default="transactions.csv", min_length=1, max_length=255),
        user_id: int = Depends(current_user),
    ):
        content_type = request.headers.get("content-type", "").partition(";")[0].strip()
        if content_type not in {"text/csv", "application/csv", "text/plain"}:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": "Import content type must be text/csv."},
            )
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_IMPORT_BYTES:
                raise ValueError("The CSV file must not exceed 64 KB.")
        rows, checksum = parse_transaction_csv(bytes(content))
        return service.import_transactions(
            user_id, account_id, rows, checksum, source_name
        )

    @application.delete(
        "/api/v1/privacy/account",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_account(
        payload: DeleteAccountRequest,
        user_id: int = Depends(current_user),
    ):
        auth_service.delete_user_data(user_id, payload.password)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(ui_directory / "index.html")

    if (ui_directory / "favicon.svg").is_file():
        @application.get("/favicon.svg", include_in_schema=False)
        def favicon():
            return FileResponse(
                ui_directory / "favicon.svg",
                media_type="image/svg+xml",
            )

    @application.get(
        "/api/v1/accounts",
        response_model=list[AccountResponse],
    )
    def accounts(user_id: int = Depends(current_user)):
        return [
            {
                "id": row[0],
                "name": row[1],
                "account_type": row[2],
                "institution": row[3],
                "balance": row[4],
                "currency": row[5],
            }
            for row in service.get_accounts(user_id)
        ]

    @application.get(
        "/api/v1/categories",
        response_model=list[CategoryResponse],
    )
    def categories(
        category_type: Literal["income", "expense"] | None = None,
        user_id: int = Depends(current_user),
    ):
        return [
            {
                "id": row[0],
                "name": row[1],
                "category_type": row[2],
                "parent_id": row[3],
            }
            for row in service.get_categories(user_id, category_type)
        ]

    @application.get(
        "/api/v1/summary",
        response_model=SummaryResponse,
    )
    def summary(
        start_date: date | None = None,
        end_date: date | None = None,
        user_id: int = Depends(current_user),
    ):
        start = start_date.isoformat() if start_date else None
        end = end_date.isoformat() if end_date else None
        preferences = service.get_user_preferences(user_id)
        return {
            "currency": preferences["currency"],
            "start_date": start_date,
            "end_date": end_date,
            "income": service.get_total_income(user_id, start, end),
            "expenses": service.get_total_expenses(user_id, start, end),
            "savings": service.get_savings(user_id, start, end),
        }

    @application.get(
        "/api/v1/transactions",
        response_model=list[TransactionResponse],
    )
    def transactions(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user_id: int = Depends(current_user),
    ):
        rows = service.get_transactions(user_id, limit=limit, offset=offset)
        return [
            {
                "id": row[0],
                "amount": row[1],
                "transaction_type": row[2],
                "description": row[3],
                "transaction_date": row[4],
                "merchant": row[5],
                "category": row[6],
                "account": row[7],
                "account_id": row[8],
                "category_id": row[9],
                "notes": row[10],
            }
            for row in rows
        ]

    @application.post(
        "/api/v1/transactions",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_transaction(
        payload: TransactionCreate,
        user_id: int = Depends(current_user),
    ):
        transaction_id = service.add_transaction(
            user_id=user_id,
            account_id=payload.account_id,
            category_id=payload.category_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            description=payload.description,
            transaction_date=(
                payload.transaction_date.isoformat()
                if payload.transaction_date
                else None
            ),
            merchant=payload.merchant,
            notes=payload.notes,
        )
        return {"id": transaction_id}

    @application.put(
        "/api/v1/transactions/{transaction_id}",
        response_model=TransactionCreated,
    )
    def update_transaction(
        transaction_id: int,
        payload: TransactionCreate,
        user_id: int = Depends(current_user),
    ):
        service.update_transaction(
            user_id=user_id,
            transaction_id=transaction_id,
            account_id=payload.account_id,
            category_id=payload.category_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            description=payload.description,
            transaction_date=(
                payload.transaction_date.isoformat()
                if payload.transaction_date
                else None
            ),
            merchant=payload.merchant,
            notes=payload.notes,
        )
        return {"id": transaction_id}

    @application.delete(
        "/api/v1/transactions/{transaction_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_transaction(
        transaction_id: int,
        user_id: int = Depends(current_user),
    ):
        service.delete_transaction(user_id, transaction_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/api/v1/budgets", response_model=list[BudgetResponse])
    def budgets(user_id: int = Depends(current_user)):
        results = []
        for row in service.get_budgets(user_id):
            amount = float(row[3])
            spent = float(row[7])
            results.append({
                "id": row[0], "category_id": row[1], "category": row[2],
                "amount": amount, "period": row[4], "start_date": row[5],
                "end_date": row[6], "spent": spent,
                "remaining": max(amount - spent, 0),
                "percent_used": min(spent / amount * 100, 100),
            })
        return results

    @application.post(
        "/api/v1/budgets",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_budget(payload: BudgetWrite, user_id: int = Depends(current_user)):
        budget_id = service.create_budget(
            user_id, payload.category_id, payload.amount, payload.period,
            payload.start_date.isoformat(), payload.end_date.isoformat(),
        )
        return {"id": budget_id}

    @application.put("/api/v1/budgets/{budget_id}", response_model=TransactionCreated)
    def update_budget(budget_id: int, payload: BudgetWrite, user_id: int = Depends(current_user)):
        service.update_budget(
            user_id, budget_id, payload.category_id, payload.amount, payload.period,
            payload.start_date.isoformat(), payload.end_date.isoformat(),
        )
        return {"id": budget_id}

    @application.delete("/api/v1/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_budget(budget_id: int, user_id: int = Depends(current_user)):
        service.delete_budget(user_id, budget_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/api/v1/goals", response_model=list[GoalResponse])
    def goals(user_id: int = Depends(current_user)):
        results = []
        for row in service.get_goals(user_id):
            target = float(row[2])
            current = float(row[3])
            results.append({
                "id": row[0], "name": row[1], "target_amount": target,
                "current_amount": current, "target_date": row[4],
                "priority": row[5], "status": row[6],
                "remaining": max(target - current, 0),
                "percent_complete": min(current / target * 100, 100),
            })
        return results

    @application.post(
        "/api/v1/goals",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_goal(payload: GoalWrite, user_id: int = Depends(current_user)):
        goal_id = service.create_goal(
            user_id, payload.name, payload.target_amount, payload.current_amount,
            payload.target_date.isoformat() if payload.target_date else None,
            payload.priority, payload.status,
        )
        return {"id": goal_id}

    @application.put("/api/v1/goals/{goal_id}", response_model=TransactionCreated)
    def update_goal(goal_id: int, payload: GoalWrite, user_id: int = Depends(current_user)):
        service.update_goal(
            user_id, goal_id, payload.name, payload.target_amount,
            payload.current_amount,
            payload.target_date.isoformat() if payload.target_date else None,
            payload.priority, payload.status,
        )
        return {"id": goal_id}

    @application.delete("/api/v1/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_goal(goal_id: int, user_id: int = Depends(current_user)):
        service.delete_goal(user_id, goal_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get(
        "/api/v1/recurring-transactions",
        response_model=list[RecurringTransactionResponse],
    )
    def recurring_transactions(user_id: int = Depends(current_user)):
        return [
            {
                "id": row[0], "account_id": row[1], "category_id": row[2],
                "transaction_type": row[3], "amount": float(row[4]),
                "description": row[5], "frequency": row[6],
                "interval_count": row[7], "next_date": row[8],
                "end_date": row[9], "is_active": bool(row[10]),
                "last_generated_date": row[11], "merchant": row[12],
                "notes": row[13], "account": row[14], "category": row[15],
                "schedule_kind": row[16], "loan_type": row[17], "lender": row[18],
            }
            for row in service.get_recurring_transactions(user_id)
        ]

    @application.post(
        "/api/v1/recurring-transactions/process",
        response_model=RecurringProcessResponse,
    )
    def process_recurring(payload: RecurringProcessRequest, user_id: int = Depends(current_user)):
        transaction_ids = service.process_recurring_transactions(
            user_id,
            payload.through_date.isoformat() if payload.through_date else None,
        )
        return {"generated_count": len(transaction_ids), "transaction_ids": transaction_ids}

    @application.post(
        "/api/v1/recurring-transactions",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_recurring(payload: RecurringTransactionWrite, user_id: int = Depends(current_user)):
        recurring_id = service.create_recurring_transaction(
            user_id, payload.account_id, payload.category_id,
            payload.transaction_type, payload.amount, payload.description,
            payload.frequency, payload.next_date.isoformat(), payload.interval_count,
            payload.end_date.isoformat() if payload.end_date else None,
            payload.merchant, payload.notes,
            payload.schedule_kind, payload.loan_type, payload.lender,
        )
        return {"id": recurring_id}

    @application.put(
        "/api/v1/recurring-transactions/{recurring_id}",
        response_model=TransactionCreated,
    )
    def update_recurring(recurring_id: int, payload: RecurringTransactionWrite, user_id: int = Depends(current_user)):
        service.update_recurring_transaction(
            user_id, recurring_id, payload.account_id, payload.category_id,
            payload.transaction_type, payload.amount, payload.description,
            payload.frequency, payload.next_date.isoformat(), payload.interval_count,
            payload.end_date.isoformat() if payload.end_date else None,
            payload.merchant, payload.notes, payload.is_active,
            payload.schedule_kind, payload.loan_type, payload.lender,
        )
        return {"id": recurring_id}

    @application.delete(
        "/api/v1/recurring-transactions/{recurring_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_recurring(recurring_id: int, user_id: int = Depends(current_user)):
        service.delete_recurring_transaction(user_id, recurring_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get(
        "/api/v1/investments/summary",
        response_model=InvestmentSummaryResponse,
    )
    def investment_summary(user_id: int = Depends(current_user)):
        return service.get_investment_summary(user_id)

    @application.post(
        "/api/v1/investments/process",
        response_model=InvestmentProcessResponse,
    )
    def process_investments(
        payload: RecurringProcessRequest,
        user_id: int = Depends(current_user),
    ):
        contribution_ids = service.process_investments(
            user_id,
            payload.through_date.isoformat() if payload.through_date else None,
        )
        return {
            "generated_count": len(contribution_ids),
            "contribution_ids": contribution_ids,
        }

    @application.get(
        "/api/v1/investments",
        response_model=list[InvestmentResponse],
    )
    def investments(user_id: int = Depends(current_user)):
        return [
            {
                "id": row[0], "account_id": row[1], "investment_type": row[2],
                "name": row[3], "provider": row[4],
                "contribution_amount": float(row[5]), "frequency": row[6],
                "interval_count": row[7], "next_date": row[8],
                "maturity_date": row[9], "total_contributed": float(row[10]),
                "current_value": float(row[11]), "status": row[12],
                "last_contribution_date": row[13], "notes": row[14],
                "account": row[15], "gain_loss": float(row[11]) - float(row[10]),
            }
            for row in service.get_investments(user_id)
        ]

    @application.post(
        "/api/v1/investments",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_investment(
        payload: InvestmentWrite,
        user_id: int = Depends(current_user),
    ):
        investment_id = service.create_investment(
            user_id, payload.account_id, payload.investment_type, payload.name,
            payload.provider, payload.contribution_amount, payload.frequency,
            payload.next_date.isoformat(), payload.interval_count,
            payload.maturity_date.isoformat() if payload.maturity_date else None,
            payload.current_value, payload.status, payload.notes,
        )
        return {"id": investment_id}

    @application.put(
        "/api/v1/investments/{investment_id}",
        response_model=TransactionCreated,
    )
    def update_investment(
        investment_id: int,
        payload: InvestmentWrite,
        user_id: int = Depends(current_user),
    ):
        service.update_investment(
            user_id, investment_id, payload.account_id, payload.investment_type,
            payload.name, payload.provider, payload.contribution_amount,
            payload.frequency, payload.next_date.isoformat(), payload.interval_count,
            payload.maturity_date.isoformat() if payload.maturity_date else None,
            payload.current_value, payload.status, payload.notes,
        )
        return {"id": investment_id}

    @application.delete(
        "/api/v1/investments/{investment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_investment(
        investment_id: int,
        user_id: int = Depends(current_user),
    ):
        service.delete_investment(user_id, investment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get(
        "/api/v1/investments/{investment_id}/contributions",
        response_model=list[InvestmentContributionResponse],
    )
    def investment_contributions(
        investment_id: int,
        user_id: int = Depends(current_user),
    ):
        return [
            {
                "id": row[0], "amount": float(row[1]),
                "contribution_date": row[2], "scheduled_for": row[3],
                "notes": row[4],
            }
            for row in service.get_investment_contributions(user_id, investment_id)
        ]

    @application.post(
        "/api/v1/investments/{investment_id}/contributions",
        response_model=TransactionCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def add_investment_contribution(
        investment_id: int,
        payload: InvestmentContributionCreate,
        user_id: int = Depends(current_user),
    ):
        contribution_id = service.add_investment_contribution(
            user_id, investment_id, payload.amount,
            payload.contribution_date.isoformat() if payload.contribution_date else None,
            payload.notes,
        )
        return {"id": contribution_id}

    @application.put(
        "/api/v1/investments/{investment_id}/value",
        response_model=TransactionCreated,
    )
    def update_investment_value(
        investment_id: int,
        payload: InvestmentValueUpdate,
        user_id: int = Depends(current_user),
    ):
        service.update_investment_value(
            user_id, investment_id, payload.current_value
        )
        return {"id": investment_id}

    @application.get(
        "/api/v1/notifications",
        response_model=list[NotificationResponse],
    )
    def notifications(
        limit: int = Query(default=50, ge=1, le=100),
        unread_only: bool = False,
        user_id: int = Depends(current_user),
    ):
        return [
            {
                "id": row[0], "notification_type": row[1], "title": row[2],
                "message": row[3], "is_read": bool(row[4]), "created_at": row[5],
            }
            for row in service.get_notifications(user_id, limit, unread_only)
        ]

    @application.patch(
        "/api/v1/notifications/{notification_id}/read",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def mark_notification_read(
        notification_id: int,
        user_id: int = Depends(current_user),
    ):
        service.mark_notification_read(user_id, notification_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/api/v1/notifications/read-all",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def mark_all_notifications_read(user_id: int = Depends(current_user)):
        service.mark_all_notifications_read(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.delete(
        "/api/v1/notifications/{notification_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_notification(
        notification_id: int,
        user_id: int = Depends(current_user),
    ):
        service.delete_notification(user_id, notification_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get(
        "/api/v1/preferences",
        response_model=PreferencesResponse,
    )
    def get_preferences(user_id: int = Depends(current_user)):
        return service.get_user_preferences(user_id)

    @application.put(
        "/api/v1/preferences",
        response_model=PreferencesResponse,
    )
    def update_preferences(
        payload: PreferencesUpdate,
        user_id: int = Depends(current_user),
    ):
        preferences = service.get_user_preferences(user_id)
        updates = payload.model_dump(exclude_unset=True)
        for required_field in (
            "language",
            "currency",
            "notification_enabled",
        ):
            if updates.get(required_field) is None:
                updates.pop(required_field, None)
        preferences.update(updates)
        return service.set_user_preferences(user_id, **preferences)

    @application.post(
        "/api/v1/chat",
        response_model=ChatResponse,
    )
    def personalized_chat(
        payload: ChatRequest,
        user_id: int = Depends(current_user),
    ):
        result = chat_handler(
            user_id=user_id,
            thread_id=payload.thread_id,
            question=payload.question,
        )
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("The finance agent returned no response.")
        return {
            "thread_id": payload.thread_id,
            "answer": messages[-1].content,
        }

    return application
