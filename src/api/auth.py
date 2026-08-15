import json
import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

from src.security.validation import validate_positive_id


bearer_scheme = HTTPBearer(auto_error=False)


class TokenAuthenticator:
    """Map opaque bearer tokens to server-controlled user identities."""

    def __init__(self, token_users: dict[str, int] | None = None, auth_service=None):
        token_users = token_users or {}
        if not token_users and auth_service is None:
            raise ValueError("At least one API token must be configured.")

        validated = []
        for token, user_id in token_users.items():
            if not isinstance(token, str) or len(token) < 32:
                raise ValueError("API tokens must contain at least 32 characters.")
            validated.append((token, validate_positive_id(user_id, "user_id")))
        self._token_users = tuple(validated)
        self._auth_service = auth_service

    @classmethod
    def from_environment(cls, auth_service=None):
        load_dotenv()
        raw_tokens = os.getenv("FINANCE_API_TOKENS")
        if not raw_tokens:
            return cls({}, auth_service=auth_service)

        try:
            token_users = json.loads(raw_tokens)
        except json.JSONDecodeError as error:
            raise RuntimeError("FINANCE_API_TOKENS must contain valid JSON.") from error

        if not isinstance(token_users, dict):
            raise RuntimeError("FINANCE_API_TOKENS must contain a JSON object.")
        return cls(token_users, auth_service=auth_service)

    def authenticate(
        self,
        credentials: HTTPAuthorizationCredentials | None = Security(
            bearer_scheme
        ),
    ) -> int:
        if credentials is None or credentials.scheme.casefold() != "bearer":
            raise self._unauthorized()

        for token, user_id in self._token_users:
            if secrets.compare_digest(credentials.credentials, token):
                return user_id
        if self._auth_service is not None:
            user_id = self._auth_service.authenticate_access_token(
                credentials.credentials
            )
            if user_id is not None:
                return user_id
        raise self._unauthorized()

    @staticmethod
    def _unauthorized():
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
