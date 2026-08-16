import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


LOCAL_HOSTS = ("127.0.0.1", "localhost", "testserver")


def _csv_setting(name, default=()):
    value = os.getenv(name)
    if value is None:
        return tuple(default)
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise RuntimeError(f"{name} must contain at least one value.")
    return values


def _boolean_setting(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.casefold()
    if normalized not in {"true", "false"}:
        raise RuntimeError(f"{name} must be true or false.")
    return normalized == "true"


def _integer_setting(name, default):
    value = os.getenv(name)
    try:
        parsed = int(value) if value is not None else default
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer.") from error
    if parsed < 0:
        raise RuntimeError(f"{name} must not be negative.")
    return parsed


def _validate_hosts(hosts, production):
    for host in hosts:
        if host == "*":
            if production:
                raise RuntimeError("FINANCE_ALLOWED_HOSTS cannot use * in production.")
            continue
        if (
            "://" in host
            or any(character in host for character in "/@?#")
            or any(character.isspace() for character in host)
        ):
            raise RuntimeError("FINANCE_ALLOWED_HOSTS contains an invalid host.")


def _validate_origins(origins):
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("FINANCE_CORS_ORIGINS contains an invalid origin.")


@dataclass(frozen=True)
class DeploymentSecuritySettings:
    environment: str
    allowed_hosts: tuple[str, ...]
    cors_origins: tuple[str, ...]
    https_redirect: bool
    hsts_seconds: int
    root_path: str

    @classmethod
    def from_environment(cls):
        environment = os.getenv("FINANCE_ENVIRONMENT", "development").casefold()
        if environment not in {"development", "test", "production"}:
            raise RuntimeError(
                "FINANCE_ENVIRONMENT must be development, test, or production."
            )
        production = environment == "production"
        configured_hosts = os.getenv("FINANCE_ALLOWED_HOSTS")
        if production and configured_hosts is None:
            raise RuntimeError("FINANCE_ALLOWED_HOSTS is required in production.")
        allowed_hosts = _csv_setting("FINANCE_ALLOWED_HOSTS", LOCAL_HOSTS)
        cors_origins = _csv_setting("FINANCE_CORS_ORIGINS") if os.getenv(
            "FINANCE_CORS_ORIGINS"
        ) is not None else ()
        https_redirect = _boolean_setting("FINANCE_HTTPS_REDIRECT", production)
        hsts_seconds = _integer_setting(
            "FINANCE_HSTS_SECONDS",
            31536000 if production else 0,
        )
        root_path = os.getenv("FINANCE_ROOT_PATH", "")
        if root_path and (not root_path.startswith("/") or root_path.endswith("/")):
            raise RuntimeError(
                "FINANCE_ROOT_PATH must start with / and must not end with /."
            )
        _validate_hosts(allowed_hosts, production)
        _validate_origins(cors_origins)
        return cls(
            environment=environment,
            allowed_hosts=allowed_hosts,
            cors_origins=cors_origins,
            https_redirect=https_redirect,
            hsts_seconds=hsts_seconds,
            root_path=root_path,
        )

    def middleware(self):
        middleware = [
            Middleware(
                TrustedHostMiddleware,
                allowed_hosts=list(self.allowed_hosts),
                www_redirect=False,
            )
        ]
        if self.https_redirect:
            middleware.append(Middleware(HTTPSRedirectMiddleware))
        if self.cors_origins:
            middleware.insert(
                0,
                Middleware(
                    CORSMiddleware,
                    allow_origins=list(self.cors_origins),
                    allow_credentials=False,
                    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
                    expose_headers=["X-Request-ID"],
                    max_age=600,
                ),
            )
        return middleware
