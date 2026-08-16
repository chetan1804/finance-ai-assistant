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
)
from src.database.db import initialize_database
from src.database.finance_service import FinanceService
from src.security.auth_service import (
    AuthenticationError,
    AuthService,
    ReauthenticationError,
    RegistrationError,
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

    application = FastAPI(
        title="Finance Assistant API",
        version="1.0.0",
        description="Authenticated access to personalized financial insights.",
        middleware=deployment_settings.middleware(),
        root_path=deployment_settings.root_path,
    )
    application.state.observability = observability
    application.state.deployment_settings = deployment_settings
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
