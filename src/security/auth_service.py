import hashlib
import secrets
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from src.database.db import INTEGRITY_ERRORS, get_connection
from src.security.validation import (
    validate_currency,
    validate_email,
    validate_positive_id,
    validate_text,
)


ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 30
MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15
MIN_PASSWORD_LENGTH = 15
COMMON_PASSWORDS = {
    "123456789012345",
    "adminadminadmin",
    "financeassistant",
    "letmeinletmein",
    "password123456",
    "passwordpassword",
    "qwertyqwerty123",
    "welcome1234567",
}
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


class ReauthenticationError(ValueError):
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
        return value.astimezone(timezone.utc).isoformat(sep=" ", timespec="seconds")

    @staticmethod
    def _password_input(password):
        if not isinstance(password, str):
            raise ValueError("password must be text.")
        if not password:
            raise ValueError("password must not be empty.")
        if len(password) > 128:
            raise ValueError("password must contain at most 128 characters.")
        return password

    @classmethod
    def _new_password(cls, password):
        password = cls._password_input(password)
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"password must contain at least {MIN_PASSWORD_LENGTH} characters."
            )
        if password.casefold() in COMMON_PASSWORDS:
            raise ValueError("Choose a less common password.")
        return password

    def _verify_user_password(self, connection, user_id, password):
        password = self._password_input(password)
        row = connection.execute(
            """
            SELECT u.name, c.password_hash
            FROM users u JOIN user_credentials c ON c.user_id = u.id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise ReauthenticationError("Password verification failed.")
        try:
            self.password_hasher.verify(row[1], password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            raise ReauthenticationError("Password verification failed.") from None
        return row

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
        password = self._new_password(password)
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
        except INTEGRITY_ERRORS as error:
            connection.rollback()
            raise RegistrationError("An account with this email already exists.") from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def login(self, email, password):
        email = validate_email(email)
        password = self._password_input(password)
        connection = self._connection()
        try:
            row = connection.execute(
                """
                SELECT u.id, u.name, c.password_hash,
                       c.failed_login_attempts,
                       CASE WHEN c.locked_until > CURRENT_TIMESTAMP
                            THEN 1 ELSE 0 END
                FROM users u JOIN user_credentials c ON c.user_id = u.id
                WHERE u.email = ?
                """,
                (email,),
            ).fetchone()
            if row is None and self._dummy_hash is None:
                self._dummy_hash = self.password_hasher.hash("not-a-real-password")
            password_hash = row[2] if row else self._dummy_hash
            verified = False
            try:
                self.password_hasher.verify(password_hash, password)
                verified = row is not None
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                verified = False
            if row is not None and not verified:
                attempts = row[3] + 1
                locked_until = (
                    self._timestamp(
                        datetime.now(timezone.utc)
                        + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
                    )
                    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS
                    else None
                )
                connection.execute(
                    """
                    UPDATE user_credentials
                    SET failed_login_attempts = ?, locked_until = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (attempts, locked_until, row[0]),
                )
                connection.commit()
            if row is None or not verified or row[4]:
                raise AuthenticationError("Invalid email or password.")
            if self.password_hasher.check_needs_rehash(password_hash):
                connection.execute(
                    "UPDATE user_credentials SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (self.password_hasher.hash(password), row[0]),
                )
            connection.execute(
                """
                UPDATE user_credentials
                SET failed_login_attempts = 0, locked_until = NULL,
                    last_login_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (row[0],),
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

    def list_sessions(self, user_id, current_access_token):
        user_id = validate_positive_id(user_id, "user_id")
        current_hash = self._token_hash(current_access_token)
        connection = self._connection()
        try:
            rows = connection.execute(
                """
                SELECT id, created_at, access_expires_at, refresh_expires_at,
                       CASE WHEN access_token_hash = ? THEN 1 ELSE 0 END
                FROM auth_sessions
                WHERE user_id = ? AND revoked_at IS NULL
                  AND refresh_expires_at > CURRENT_TIMESTAMP
                ORDER BY created_at DESC, id DESC
                """,
                (current_hash, user_id),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "created_at": row[1],
                    "access_expires_at": row[2],
                    "refresh_expires_at": row[3],
                    "current": bool(row[4]),
                }
                for row in rows
            ]
        finally:
            connection.close()

    def revoke_session(self, user_id, session_id):
        user_id = validate_positive_id(user_id, "user_id")
        session_id = validate_positive_id(session_id, "session_id")
        connection = self._connection()
        try:
            connection.execute(
                """
                UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND revoked_at IS NULL
                """,
                (session_id, user_id),
            )
            connection.commit()
        finally:
            connection.close()

    def revoke_all_sessions(self, user_id, password):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            self._verify_user_password(connection, user_id, password)
            connection.execute(
                """
                UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (user_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def change_password(self, user_id, current_password, new_password):
        user_id = validate_positive_id(user_id, "user_id")
        new_password = self._new_password(new_password)
        connection = self._connection()
        try:
            row = self._verify_user_password(connection, user_id, current_password)
            try:
                same_password = self.password_hasher.verify(row[1], new_password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                same_password = False
            if same_password:
                raise ValueError("New password must be different from the current password.")
            connection.execute(
                """
                UPDATE user_credentials
                SET password_hash = ?, failed_login_attempts = 0,
                    locked_until = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (self.password_hasher.hash(new_password), user_id),
            )
            connection.execute(
                """
                UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (user_id,),
            )
            session = self._create_session(connection, user_id)
            connection.commit()
            return {**session, "name": row[0]}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _json_value(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    @classmethod
    def _records(cls, rows, columns):
        return [
            {
                column: cls._json_value(value)
                for column, value in zip(columns, row)
            }
            for row in rows
        ]

    def export_user_data(self, user_id, password):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            self._verify_user_password(connection, user_id, password)
            profile = connection.execute(
                """
                SELECT id, name, email, currency, created_at, updated_at
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
            collections = {}
            queries = {
                "preferences": (
                    "SELECT language, currency, monthly_income, risk_preference, "
                    "notification_enabled, created_at, updated_at "
                    "FROM user_preferences WHERE user_id = ?",
                    ("language", "currency", "monthly_income", "risk_preference",
                     "notification_enabled", "created_at", "updated_at"),
                ),
                "accounts": (
                    "SELECT id, name, account_type, institution, balance, currency, "
                    "is_active, created_at, updated_at FROM accounts WHERE user_id = ? "
                    "ORDER BY id",
                    ("id", "name", "account_type", "institution", "balance", "currency",
                     "is_active", "created_at", "updated_at"),
                ),
                "categories": (
                    "SELECT id, name, category_type, parent_id, created_at "
                    "FROM categories WHERE user_id = ? ORDER BY id",
                    ("id", "name", "category_type", "parent_id", "created_at"),
                ),
                "transactions": (
                    "SELECT id, account_id, category_id, transaction_type, amount, "
                    "description, transaction_date, merchant, notes, recurring_transaction_id, "
                    "scheduled_for, import_batch_id, loan_type, created_at, updated_at "
                    "FROM transactions WHERE user_id = ? ORDER BY id",
                    ("id", "account_id", "category_id", "transaction_type", "amount",
                     "description", "transaction_date", "merchant", "notes",
                     "recurring_transaction_id", "scheduled_for",
                     "import_batch_id", "loan_type",
                     "created_at", "updated_at"),
                ),
                "import_batches": (
                    "SELECT id, source_name, checksum, row_count, created_at "
                    "FROM import_batches WHERE user_id = ? ORDER BY id",
                    ("id", "source_name", "checksum", "row_count", "created_at"),
                ),
                "notifications": (
                    "SELECT id, notification_type, title, message, is_read, created_at "
                    "FROM notifications WHERE user_id = ? ORDER BY id",
                    ("id", "notification_type", "title", "message", "is_read", "created_at"),
                ),
                "recurring_transactions": (
                    "SELECT id, account_id, category_id, transaction_type, amount, "
                    "description, merchant, notes, frequency, interval_count, next_date, "
                    "end_date, is_active, last_generated_date, schedule_kind, loan_type, "
                    "lender, created_at, updated_at "
                    "FROM recurring_transactions WHERE user_id = ? ORDER BY id",
                    ("id", "account_id", "category_id", "transaction_type", "amount",
                     "description", "merchant", "notes", "frequency", "interval_count",
                     "next_date", "end_date", "is_active", "last_generated_date",
                     "schedule_kind", "loan_type", "lender",
                     "created_at", "updated_at"),
                ),
                "investment_plans": (
                    "SELECT id, account_id, investment_type, name, provider, "
                    "contribution_amount, frequency, interval_count, next_date, "
                    "maturity_date, total_contributed, current_value, status, "
                    "last_contribution_date, notes, created_at, updated_at "
                    "FROM investment_plans WHERE user_id = ? ORDER BY id",
                    ("id", "account_id", "investment_type", "name", "provider",
                     "contribution_amount", "frequency", "interval_count", "next_date",
                     "maturity_date", "total_contributed", "current_value", "status",
                     "last_contribution_date", "notes", "created_at", "updated_at"),
                ),
                "investment_contributions": (
                    "SELECT id, investment_id, account_id, amount, contribution_date, "
                    "scheduled_for, notes, created_at FROM investment_contributions "
                    "WHERE user_id = ? ORDER BY id",
                    ("id", "investment_id", "account_id", "amount", "contribution_date",
                     "scheduled_for", "notes", "created_at"),
                ),
                "budgets": (
                    "SELECT id, category_id, amount, period, start_date, end_date, "
                    "created_at, updated_at FROM budgets WHERE user_id = ? ORDER BY id",
                    ("id", "category_id", "amount", "period", "start_date", "end_date",
                     "created_at", "updated_at"),
                ),
                "financial_goals": (
                    "SELECT id, name, target_amount, current_amount, target_date, priority, "
                    "status, created_at, updated_at FROM financial_goals "
                    "WHERE user_id = ? ORDER BY id",
                    ("id", "name", "target_amount", "current_amount", "target_date",
                     "priority", "status", "created_at", "updated_at"),
                ),
            }
            for name, (query, columns) in queries.items():
                rows = connection.execute(query, (user_id,)).fetchall()
                collections[name] = self._records(rows, columns)
            return {
                "export_version": 4,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "profile": self._records(
                    [profile],
                    ("id", "name", "email", "currency", "created_at", "updated_at"),
                )[0],
                **collections,
            }
        finally:
            connection.close()

    def delete_user_data(self, user_id, password):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            self._verify_user_password(connection, user_id, password)
        finally:
            connection.close()

        from src.agents.checkpoint import delete_user_checkpoints

        delete_user_checkpoints(user_id)
        connection = self._connection()
        try:
            for table in (
                "auth_sessions",
                "user_credentials",
                "notifications",
                "investment_contributions",
                "investment_plans",
                "transactions",
                "import_batches",
                "recurring_transactions",
                "budgets",
                "financial_goals",
                "user_preferences",
                "categories",
                "accounts",
            ):
                connection.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
