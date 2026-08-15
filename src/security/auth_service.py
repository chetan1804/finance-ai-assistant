import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from src.database.db import get_connection
from src.security.validation import validate_currency, validate_email, validate_text


ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 30
DEFAULT_CATEGORIES = (
    ("Salary", "income"), ("Other income", "income"),
    ("Food", "expense"), ("Housing", "expense"),
    ("Transport", "expense"), ("Utilities", "expense"),
    ("Shopping", "expense"), ("Other expense", "expense"),
)


class AuthenticationError(ValueError):
    pass


class RegistrationError(ValueError):
    pass


class AuthService:
    def __init__(self, database_path=None, password_hasher=None):
        self.database_path = database_path
        self.password_hasher = password_hasher or PasswordHasher()
        self._dummy_hash = None

    def _connection(self):
        return get_connection(self.database_path)

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _timestamp(value):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _password(password):
        if not isinstance(password, str):
            raise ValueError("password must be text.")
        if len(password) < 12:
            raise ValueError("password must contain at least 12 characters.")
        if len(password) > 128:
            raise ValueError("password must contain at most 128 characters.")
        return password

    def _create_session(self, connection, user_id):
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        connection.execute(
            """
            INSERT INTO auth_sessions
            (user_id, access_token_hash, refresh_token_hash,
             access_expires_at, refresh_expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                self._token_hash(access_token),
                self._token_hash(refresh_token),
                self._timestamp(now + timedelta(minutes=ACCESS_TOKEN_MINUTES)),
                self._timestamp(now + timedelta(days=REFRESH_TOKEN_DAYS)),
            ),
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_MINUTES * 60,
            "user_id": user_id,
        }

    def register(self, name, email, password, currency="INR", account_name="Main account"):
        name = validate_text(name, "name", max_length=100)
        email = validate_email(email)
        password = self._password(password)
        currency = validate_currency(currency)
        account_name = validate_text(account_name, "account_name", max_length=100)
        password_hash = self.password_hasher.hash(password)
        connection = self._connection()
        try:
            cursor = connection.execute(
                "INSERT INTO users (name, email, currency) VALUES (?, ?, ?)",
                (name, email, currency),
            )
            user_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO user_credentials (user_id, password_hash) VALUES (?, ?)",
                (user_id, password_hash),
            )
            connection.execute(
                """
                INSERT INTO accounts (user_id, name, account_type, currency)
                VALUES (?, ?, 'checking', ?)
                """,
                (user_id, account_name, currency),
            )
            connection.executemany(
                "INSERT INTO categories (user_id, name, category_type) VALUES (?, ?, ?)",
                ((user_id, category, category_type) for category, category_type in DEFAULT_CATEGORIES),
            )
            session = self._create_session(connection, user_id)
            connection.commit()
            return {**session, "name": name}
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise RegistrationError("An account with this email already exists.") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def login(self, email, password):
        email = validate_email(email)
        password = self._password(password)
        connection = self._connection()
        try:
            row = connection.execute(
                """
                SELECT u.id, u.name, c.password_hash
                FROM users u JOIN user_credentials c ON c.user_id = u.id
                WHERE u.email = ?
                """,
                (email,),
            ).fetchone()
            if row is None and self._dummy_hash is None:
                self._dummy_hash = self.password_hasher.hash("not-a-real-password")
            password_hash = row[2] if row else self._dummy_hash
            try:
                self.password_hasher.verify(password_hash, password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                raise AuthenticationError("Invalid email or password.") from None
            if row is None:
                raise AuthenticationError("Invalid email or password.")
            if self.password_hasher.check_needs_rehash(password_hash):
                connection.execute(
                    "UPDATE user_credentials SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (self.password_hasher.hash(password), row[0]),
                )
            session = self._create_session(connection, row[0])
            connection.commit()
            return {**session, "name": row[1]}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def authenticate_access_token(self, token):
        if not isinstance(token, str) or len(token) < 32:
            return None
        connection = self._connection()
        try:
            row = connection.execute(
                """
                SELECT user_id FROM auth_sessions
                WHERE access_token_hash = ? AND revoked_at IS NULL
                  AND access_expires_at > CURRENT_TIMESTAMP
                """,
                (self._token_hash(token),),
            ).fetchone()
            return row[0] if row else None
        finally:
            connection.close()

    def refresh(self, refresh_token):
        refresh_token = validate_text(refresh_token, "refresh_token", max_length=256)
        connection = self._connection()
        try:
            row = connection.execute(
                """
                SELECT s.id, s.user_id, u.name FROM auth_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ? AND s.revoked_at IS NULL
                  AND s.refresh_expires_at > CURRENT_TIMESTAMP
                """,
                (self._token_hash(refresh_token),),
            ).fetchone()
            if row is None:
                raise AuthenticationError("Invalid or expired refresh token.")
            connection.execute(
                "UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row[0],),
            )
            session = self._create_session(connection, row[1])
            connection.commit()
            return {**session, "name": row[2]}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def logout(self, user_id, refresh_token):
        connection = self._connection()
        try:
            connection.execute(
                """
                UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND refresh_token_hash = ? AND revoked_at IS NULL
                """,
                (user_id, self._token_hash(refresh_token)),
            )
            connection.commit()
        finally:
            connection.close()
