import calendar
from datetime import date, timedelta

from src.database.db import get_connection
from src.security.validation import (
    validate_currency,
    validate_date_range,
    validate_email,
    validate_finite_number,
    validate_iso_date,
    validate_money,
    validate_positive_id,
    validate_text,
)


VALID_TRANSACTION_TYPES = {"income", "expense", "transfer"}
VALID_CATEGORY_TYPES = {"income", "expense"}
VALID_BUDGET_PERIODS = {"weekly", "monthly", "quarterly", "yearly", "custom"}
VALID_GOAL_PRIORITIES = {"low", "medium", "high"}
VALID_GOAL_STATUSES = {"active", "completed", "paused"}
VALID_RECURRING_FREQUENCIES = {"daily", "weekly", "monthly", "yearly"}


def _advance_date(value, frequency, interval_count):
    current = date.fromisoformat(value)
    if frequency == "daily":
        return (current + timedelta(days=interval_count)).isoformat()
    if frequency == "weekly":
        return (current + timedelta(weeks=interval_count)).isoformat()

    months = interval_count if frequency == "monthly" else interval_count * 12
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


class FinanceService:

    def __init__(
        self,
        database_path=None
    ):
        self.database_path = database_path

    def _connection(self):
        return get_connection(self.database_path)

    # =========================================================
    # TOTAL INCOME
    # =========================================================

    def get_total_income(
        self,
        user_id: int,
        start_date=None,
        end_date=None,
    ) -> float:

        user_id = validate_positive_id(user_id, "user_id")
        start_date, end_date = validate_date_range(start_date, end_date)
        connection = self._connection()

        try:

            query = """
                SELECT COALESCE(SUM(amount), 0)

                FROM transactions

                WHERE user_id = ?

                AND transaction_type = 'income'
            """

            params = [
                user_id
            ]

            if start_date:

                query += """
                    AND transaction_date >= ?
                """

                params.append(
                    start_date
                )

            if end_date:

                query += """
                    AND transaction_date <= ?
                """

                params.append(
                    end_date
                )

            result = connection.execute(
                query,
                tuple(params)
            ).fetchone()

            return float(
                result[0]
            )

        finally:

            connection.close()

    # =========================================================
    # TOTAL EXPENSES
    # =========================================================

    def get_total_expenses(
        self,
        user_id: int,
        start_date=None,
        end_date=None,
    ) -> float:

        user_id = validate_positive_id(user_id, "user_id")
        start_date, end_date = validate_date_range(start_date, end_date)
        connection = self._connection()

        try:

            query = """
                SELECT COALESCE(SUM(amount), 0)

                FROM transactions

                WHERE user_id = ?

                AND transaction_type = 'expense'
            """

            params = [
                user_id
            ]

            if start_date:

                query += """
                    AND transaction_date >= ?
                """

                params.append(
                    start_date
                )

            if end_date:

                query += """
                    AND transaction_date <= ?
                """

                params.append(
                    end_date
                )

            result = connection.execute(
                query,
                tuple(params)
            ).fetchone()

            return float(
                result[0]
            )

        finally:

            connection.close()

    # =========================================================
    # SAVINGS
    # =========================================================

    def get_savings(
        self,
        user_id: int,
        start_date=None,
        end_date=None,
    ) -> float:

        income = self.get_total_income(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        expenses = self.get_total_expenses(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        return income - expenses

    # =========================================================
    # CATEGORY EXPENSES
    # =========================================================

    def get_category_expenses(
        self,
        user_id: int,
        category: str,
        start_date=None,
        end_date=None,
    ) -> float:

        user_id = validate_positive_id(user_id, "user_id")
        category = validate_text(category, "category", max_length=100)
        start_date, end_date = validate_date_range(start_date, end_date)
        connection = self._connection()

        try:

            query = """
                SELECT COALESCE(
                    SUM(t.amount),
                    0
                )

                FROM transactions t

                JOIN categories c
                    ON t.category_id = c.id

                WHERE t.user_id = ?

                AND t.transaction_type = 'expense'

                AND LOWER(c.name) = LOWER(?)
            """

            params = [
                user_id,
                category,
            ]

            if start_date:

                query += """
                    AND t.transaction_date >= ?
                """

                params.append(
                    start_date
                )

            if end_date:

                query += """
                    AND t.transaction_date <= ?
                """

                params.append(
                    end_date
                )

            result = connection.execute(
                query,
                tuple(params)
            ).fetchone()

            return float(
                result[0]
            )

        finally:

            connection.close()

    # =========================================================
    # EXPENSES BY CATEGORY
    # =========================================================

    def get_expenses_by_category(
        self,
        user_id: int
    ):

        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()

        try:

            results = connection.execute(
                """
                SELECT
                    c.name AS category,
                    SUM(t.amount) AS total

                FROM transactions t

                JOIN categories c
                    ON t.category_id = c.id

                WHERE t.user_id = ?

                AND t.transaction_type = 'expense'

                GROUP BY c.name

                ORDER BY total DESC
                """,
                (
                    user_id,
                )
            ).fetchall()

            return results

        finally:

            connection.close()

    # =========================================================
    # LARGEST EXPENSE
    # =========================================================

    def get_largest_expense(
        self,
        user_id: int
    ):

        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()

        try:

            result = connection.execute(
                """
                SELECT
                    amount,
                    merchant,
                    description,
                    transaction_date

                FROM transactions

                WHERE user_id = ?

                AND transaction_type = 'expense'

                ORDER BY amount DESC

                LIMIT 1
                """,
                (
                    user_id,
                )
            ).fetchone()

            return result

        finally:

            connection.close()

    # =========================================================
    # MERCHANT EXPENSES
    # =========================================================

    def get_merchant_expenses(
        self,
        user_id: int,
        merchant: str
    ) -> float:

        user_id = validate_positive_id(user_id, "user_id")
        merchant = validate_text(merchant, "merchant", max_length=255)
        connection = self._connection()

        try:

            result = connection.execute(
                """
                SELECT COALESCE(
                    SUM(amount),
                    0
                )

                FROM transactions

                WHERE user_id = ?

                AND transaction_type = 'expense'

                AND LOWER(merchant)
                    LIKE LOWER(?)
                """,
                (
                    user_id,
                    f"%{merchant}%"
                )
            ).fetchone()

            return float(
                result[0]
            )

        finally:

            connection.close()

    # =========================================================
    # TRANSACTION COUNT
    # =========================================================

    def get_transaction_count(
        self,
        user_id: int
    ) -> int:

        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()

        try:

            result = connection.execute(
                """
                SELECT COUNT(*)

                FROM transactions

                WHERE user_id = ?
                """,
                (
                    user_id,
                )
            ).fetchone()

            return int(
                result[0]
            )

        finally:

            connection.close()

    # =========================================================
    # CREATE USER
    # =========================================================

    def create_user(
        self,
        name,
        email,
        currency="INR"
    ):

        name = validate_text(name, "name", max_length=100)
        email = validate_email(email)
        currency = validate_currency(currency)
        connection = self._connection()

        try:

            cursor = connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    currency
                )

                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    currency
                )
            )

            connection.commit()

            return cursor.lastrowid

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # =========================================================
    # USER PREFERENCES
    # =========================================================

    def get_user_preferences(self, user_id: int) -> dict:
        """Return personalized display settings with user-level defaults."""
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()

        try:
            row = connection.execute(
                """
                SELECT
                    COALESCE(p.language, 'English'),
                    COALESCE(p.currency, u.currency, 'INR'),
                    p.monthly_income,
                    p.risk_preference,
                    COALESCE(p.notification_enabled, 1)
                FROM users u
                LEFT JOIN user_preferences p
                    ON p.user_id = u.id
                WHERE u.id = ?
                """,
                (user_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"User {user_id} does not exist.")

            return {
                "language": row[0],
                "currency": row[1],
                "monthly_income": row[2],
                "risk_preference": row[3],
                "notification_enabled": bool(row[4]),
            }
        finally:
            connection.close()

    def set_user_preferences(
        self,
        user_id: int,
        language="English",
        currency="INR",
        monthly_income=None,
        risk_preference=None,
        notification_enabled=True,
    ) -> dict:
        """Create or update the preferences used to personalize responses."""
        user_id = validate_positive_id(user_id, "user_id")
        language = validate_text(language, "language", max_length=50)
        currency = validate_currency(currency)
        monthly_income = validate_money(
            monthly_income,
            "monthly_income",
            allow_none=True,
        )
        risk_preference = validate_text(
            risk_preference,
            "risk_preference",
            max_length=50,
            required=False,
        )
        if not isinstance(notification_enabled, bool):
            raise ValueError("notification_enabled must be a boolean.")
        connection = self._connection()

        try:
            user = connection.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

            if user is None:
                raise ValueError(f"User {user_id} does not exist.")

            connection.execute(
                """
                INSERT INTO user_preferences (
                    user_id,
                    language,
                    currency,
                    monthly_income,
                    risk_preference,
                    notification_enabled
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    language = excluded.language,
                    currency = excluded.currency,
                    monthly_income = excluded.monthly_income,
                    risk_preference = excluded.risk_preference,
                    notification_enabled = excluded.notification_enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    language,
                    currency,
                    monthly_income,
                    risk_preference,
                    int(notification_enabled),
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return self.get_user_preferences(user_id)

    # =========================================================
    # CREATE ACCOUNT
    # =========================================================

    def create_account(
        self,
        user_id,
        name,
        account_type,
        institution=None,
        balance=0,
        currency="INR"
    ):

        user_id = validate_positive_id(user_id, "user_id")
        name = validate_text(name, "name", max_length=100)
        account_type = validate_text(
            account_type,
            "account_type",
            max_length=50,
        )
        institution = validate_text(
            institution,
            "institution",
            max_length=100,
            required=False,
        )
        balance = validate_finite_number(balance, "balance")
        currency = validate_currency(currency)
        connection = self._connection()

        try:

            cursor = connection.execute(
                """
                INSERT INTO accounts
                (
                    user_id,
                    name,
                    account_type,
                    institution,
                    balance,
                    currency
                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    account_type,
                    institution,
                    balance,
                    currency
                )
            )

            connection.commit()

            return cursor.lastrowid

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # =========================================================
    # CREATE CATEGORY
    # =========================================================

    def create_category(
        self,
        user_id,
        name,
        category_type,
        parent_id=None
    ):

        user_id = validate_positive_id(user_id, "user_id")
        name = validate_text(name, "name", max_length=100)
        category_type = validate_text(
            category_type,
            "category_type",
            max_length=20,
        ).casefold()
        if category_type not in VALID_CATEGORY_TYPES:
            raise ValueError("category_type must be income or expense.")
        if parent_id is not None:
            parent_id = validate_positive_id(parent_id, "parent_id")
        connection = self._connection()

        try:

            if parent_id is not None:
                parent = connection.execute(
                    """
                    SELECT 1
                    FROM categories
                    WHERE id = ?
                    AND (user_id = ? OR user_id IS NULL)
                    """,
                    (parent_id, user_id),
                ).fetchone()
                if parent is None:
                    raise ValueError(
                        "The parent category is not available to the selected user."
                    )

            cursor = connection.execute(
                """
                INSERT INTO categories
                (
                    user_id,
                    name,
                    category_type,
                    parent_id
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    category_type,
                    parent_id
                )
            )

            connection.commit()

            return cursor.lastrowid

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # =========================================================
    # ADD TRANSACTION
    # =========================================================

    def add_transaction(
        self,
        user_id,
        account_id,
        category_id,
        transaction_type,
        amount,
        description,
        transaction_date=None,
        merchant=None,
        notes=None
    ):

        user_id = validate_positive_id(user_id, "user_id")
        account_id = validate_positive_id(account_id, "account_id")
        if category_id is not None:
            category_id = validate_positive_id(category_id, "category_id")
        transaction_type = validate_text(
            transaction_type,
            "transaction_type",
            max_length=20,
        ).casefold()
        if transaction_type not in VALID_TRANSACTION_TYPES:
            raise ValueError(
                "transaction_type must be income, expense, or transfer."
            )
        amount = validate_money(amount)
        description = validate_text(
            description,
            "description",
            max_length=500,
            required=False,
        )
        merchant = validate_text(
            merchant,
            "merchant",
            max_length=255,
            required=False,
        )
        notes = validate_text(
            notes,
            "notes",
            max_length=1000,
            required=False,
            allow_newlines=True,
        )

        if transaction_date is None:

            transaction_date = (
                date.today().isoformat()
            )
        transaction_date = validate_iso_date(
            transaction_date,
            "transaction_date",
            allow_none=False,
        )

        connection = self._connection()

        try:

            account = connection.execute(
                "SELECT 1 FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id),
            ).fetchone()

            if account is None:
                raise ValueError(
                    "The account does not belong to the selected user."
                )

            if category_id is not None:
                category = connection.execute(
                    """
                    SELECT 1
                    FROM categories
                    WHERE id = ?
                    AND (user_id = ? OR user_id IS NULL)
                    """,
                    (category_id, user_id),
                ).fetchone()

                if category is None:
                    raise ValueError(
                        "The category is not available to the selected user."
                    )

            cursor = connection.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    account_id,
                    category_id,
                    transaction_type,
                    amount,
                    description,
                    transaction_date,
                    merchant,
                    notes
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    account_id,
                    category_id,
                    transaction_type,
                    amount,
                    description,
                    transaction_date,
                    merchant,
                    notes
                )
            )

            if transaction_type == "income":

                connection.execute(
                    """
                    UPDATE accounts

                    SET balance = balance + ?

                    WHERE id = ?

                    AND user_id = ?
                    """,
                    (
                        amount,
                        account_id,
                        user_id
                    )
                )

            elif transaction_type == "expense":

                connection.execute(
                    """
                    UPDATE accounts

                    SET balance = balance - ?

                    WHERE id = ?

                    AND user_id = ?
                    """,
                    (
                        amount,
                        account_id,
                        user_id
                    )
                )

            if transaction_type == "expense" and category_id is not None:
                self._check_budget_notifications(
                    connection, user_id, category_id, transaction_date
                )

            connection.commit()

            return cursor.lastrowid

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # =========================================================
    # GET TRANSACTIONS
    # =========================================================

    def get_transactions(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ):

        user_id = validate_positive_id(user_id, "user_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        connection = self._connection()

        try:

            transactions = connection.execute(
                """
                SELECT
                    t.id,
                    t.amount,
                    t.transaction_type,
                    t.description,
                    t.transaction_date,
                    t.merchant,
                    c.name AS category,
                    a.name AS account,
                    t.account_id,
                    t.category_id,
                    t.notes

                FROM transactions t

                LEFT JOIN categories c
                    ON t.category_id = c.id

                JOIN accounts a
                    ON t.account_id = a.id

                WHERE t.user_id = ?

                ORDER BY
                    t.transaction_date DESC,
                    t.id DESC

                LIMIT ? OFFSET ?
                """,
                (
                    user_id,
                    limit,
                    offset,
                )
            ).fetchall()

            return transactions

        finally:

            connection.close()

    def update_transaction(
        self,
        user_id,
        transaction_id,
        account_id,
        category_id,
        transaction_type,
        amount,
        description,
        transaction_date=None,
        merchant=None,
        notes=None,
    ):
        """Update a user-owned transaction and reconcile account balances."""
        user_id = validate_positive_id(user_id, "user_id")
        transaction_id = validate_positive_id(transaction_id, "transaction_id")
        account_id = validate_positive_id(account_id, "account_id")
        if category_id is not None:
            category_id = validate_positive_id(category_id, "category_id")
        transaction_type = validate_text(
            transaction_type,
            "transaction_type",
            max_length=20,
        ).casefold()
        if transaction_type not in VALID_TRANSACTION_TYPES:
            raise ValueError(
                "transaction_type must be income, expense, or transfer."
            )
        amount = validate_money(amount)
        description = validate_text(
            description,
            "description",
            max_length=500,
            required=False,
        )
        merchant = validate_text(
            merchant,
            "merchant",
            max_length=255,
            required=False,
        )
        notes = validate_text(
            notes,
            "notes",
            max_length=1000,
            required=False,
            allow_newlines=True,
        )
        if transaction_date is None:
            transaction_date = date.today().isoformat()
        transaction_date = validate_iso_date(
            transaction_date,
            "transaction_date",
            allow_none=False,
        )

        connection = self._connection()
        try:
            old = connection.execute(
                """
                SELECT account_id, transaction_type, amount
                FROM transactions
                WHERE id = ? AND user_id = ?
                """,
                (transaction_id, user_id),
            ).fetchone()
            if old is None:
                raise ValueError("Transaction not found.")

            account = connection.execute(
                "SELECT 1 FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id),
            ).fetchone()
            if account is None:
                raise ValueError(
                    "The account does not belong to the selected user."
                )

            if category_id is not None:
                category = connection.execute(
                    """
                    SELECT 1 FROM categories
                    WHERE id = ? AND (user_id = ? OR user_id IS NULL)
                    """,
                    (category_id, user_id),
                ).fetchone()
                if category is None:
                    raise ValueError(
                        "The category is not available to the selected user."
                    )

            old_account_id, old_type, old_amount = old
            if old_type == "income":
                connection.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (old_amount, old_account_id, user_id),
                )
            elif old_type == "expense":
                connection.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                    (old_amount, old_account_id, user_id),
                )

            connection.execute(
                """
                UPDATE transactions
                SET account_id = ?, category_id = ?, transaction_type = ?,
                    amount = ?, description = ?, transaction_date = ?,
                    merchant = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (
                    account_id,
                    category_id,
                    transaction_type,
                    amount,
                    description,
                    transaction_date,
                    merchant,
                    notes,
                    transaction_id,
                    user_id,
                ),
            )

            if transaction_type == "income":
                connection.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, user_id),
                )
            elif transaction_type == "expense":
                connection.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, user_id),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_transaction(self, user_id, transaction_id):
        """Delete a user-owned transaction and reverse its balance effect."""
        user_id = validate_positive_id(user_id, "user_id")
        transaction_id = validate_positive_id(transaction_id, "transaction_id")
        connection = self._connection()
        try:
            transaction = connection.execute(
                """
                SELECT account_id, transaction_type, amount
                FROM transactions
                WHERE id = ? AND user_id = ?
                """,
                (transaction_id, user_id),
            ).fetchone()
            if transaction is None:
                raise ValueError("Transaction not found.")

            account_id, transaction_type, amount = transaction
            if transaction_type == "income":
                connection.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, user_id),
                )
            elif transaction_type == "expense":
                connection.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, user_id),
                )

            connection.execute(
                "DELETE FROM transactions WHERE id = ? AND user_id = ?",
                (transaction_id, user_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_accounts(self, user_id: int):
        """Return active accounts belonging to a user."""
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()

        try:
            return connection.execute(
                """
                SELECT id, name, account_type, institution, balance, currency
                FROM accounts
                WHERE user_id = ?
                AND is_active = 1
                ORDER BY name, id
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def get_categories(self, user_id: int, category_type=None):
        """Return user-owned and shared categories, optionally by type."""
        user_id = validate_positive_id(user_id, "user_id")
        params = [user_id]
        query = """
            SELECT id, name, category_type, parent_id
            FROM categories
            WHERE (user_id = ? OR user_id IS NULL)
        """

        if category_type is not None:
            category_type = validate_text(
                category_type,
                "category_type",
                max_length=20,
            ).casefold()
            if category_type not in VALID_CATEGORY_TYPES:
                raise ValueError("category_type must be income or expense.")
            query += " AND category_type = ?"
            params.append(category_type)

        query += " ORDER BY name, id"
        connection = self._connection()
        try:
            return connection.execute(query, tuple(params)).fetchall()
        finally:
            connection.close()

    def create_budget(self, user_id, category_id, amount, period, start_date, end_date):
        user_id = validate_positive_id(user_id, "user_id")
        category_id = validate_positive_id(category_id, "category_id")
        amount = validate_money(amount)
        period = validate_text(period, "period", max_length=20).casefold()
        if period not in VALID_BUDGET_PERIODS:
            raise ValueError("period must be weekly, monthly, quarterly, yearly, or custom.")
        start_date, end_date = validate_date_range(start_date, end_date)
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required.")
        connection = self._connection()
        try:
            category = connection.execute(
                """
                SELECT 1 FROM categories
                WHERE id = ? AND category_type = 'expense'
                AND (user_id = ? OR user_id IS NULL)
                """,
                (category_id, user_id),
            ).fetchone()
            if category is None:
                raise ValueError("The expense category is not available to the selected user.")
            cursor = connection.execute(
                """
                INSERT INTO budgets
                    (user_id, category_id, amount, period, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, category_id, amount, period, start_date, end_date),
            )
            connection.commit()
            return cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_budgets(self, user_id):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            return connection.execute(
                """
                SELECT b.id, b.category_id, c.name, b.amount, b.period,
                       b.start_date, b.end_date,
                       COALESCE((
                           SELECT SUM(t.amount) FROM transactions t
                           WHERE t.user_id = b.user_id
                           AND t.category_id = b.category_id
                           AND t.transaction_type = 'expense'
                           AND t.transaction_date BETWEEN b.start_date AND b.end_date
                       ), 0) AS spent
                FROM budgets b
                JOIN categories c ON c.id = b.category_id
                WHERE b.user_id = ?
                ORDER BY b.end_date, b.id
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def update_budget(self, user_id, budget_id, category_id, amount, period, start_date, end_date):
        budget_id = validate_positive_id(budget_id, "budget_id")
        user_id = validate_positive_id(user_id, "user_id")
        category_id = validate_positive_id(category_id, "category_id")
        amount = validate_money(amount)
        period = validate_text(period, "period", max_length=20).casefold()
        if period not in VALID_BUDGET_PERIODS:
            raise ValueError("period must be weekly, monthly, quarterly, yearly, or custom.")
        start_date, end_date = validate_date_range(start_date, end_date)
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required.")
        connection = self._connection()
        try:
            category = connection.execute(
                """
                SELECT 1 FROM categories
                WHERE id = ? AND category_type = 'expense'
                AND (user_id = ? OR user_id IS NULL)
                """,
                (category_id, user_id),
            ).fetchone()
            if category is None:
                raise ValueError("The expense category is not available to the selected user.")
            cursor = connection.execute(
                """
                UPDATE budgets SET category_id = ?, amount = ?, period = ?,
                    start_date = ?, end_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (category_id, amount, period, start_date, end_date, budget_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Budget not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_budget(self, user_id, budget_id):
        user_id = validate_positive_id(user_id, "user_id")
        budget_id = validate_positive_id(budget_id, "budget_id")
        connection = self._connection()
        try:
            cursor = connection.execute(
                "DELETE FROM budgets WHERE id = ? AND user_id = ?",
                (budget_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Budget not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_goal(self, user_id, name, target_amount, current_amount=0, target_date=None, priority="medium", status="active"):
        user_id = validate_positive_id(user_id, "user_id")
        name = validate_text(name, "name", max_length=100)
        target_amount = validate_money(target_amount, "target_amount")
        current_amount = validate_finite_number(current_amount, "current_amount")
        if current_amount < 0:
            raise ValueError("current_amount must not be negative.")
        target_date = validate_iso_date(target_date, "target_date")
        priority = validate_text(priority, "priority", max_length=20).casefold()
        status = validate_text(status, "status", max_length=20).casefold()
        if priority not in VALID_GOAL_PRIORITIES:
            raise ValueError("priority must be low, medium, or high.")
        if status not in VALID_GOAL_STATUSES:
            raise ValueError("status must be active, completed, or paused.")
        if current_amount >= target_amount:
            status = "completed"
        connection = self._connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO financial_goals
                    (user_id, name, target_amount, current_amount, target_date, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, target_amount, current_amount, target_date, priority, status),
            )
            if status == "completed":
                self._add_notification(
                    connection, user_id, "goal_completed", "Savings goal completed",
                    f"You reached your {name} savings goal.",
                    f"goal:{cursor.lastrowid}:completed",
                )
            connection.commit()
            return cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_goals(self, user_id):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            return connection.execute(
                """
                SELECT id, name, target_amount, current_amount, target_date, priority, status
                FROM financial_goals WHERE user_id = ?
                ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
                         target_date, id
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def update_goal(self, user_id, goal_id, name, target_amount, current_amount, target_date=None, priority="medium", status="active"):
        user_id = validate_positive_id(user_id, "user_id")
        goal_id = validate_positive_id(goal_id, "goal_id")
        name = validate_text(name, "name", max_length=100)
        target_amount = validate_money(target_amount, "target_amount")
        current_amount = validate_finite_number(current_amount, "current_amount")
        if current_amount < 0:
            raise ValueError("current_amount must not be negative.")
        target_date = validate_iso_date(target_date, "target_date")
        priority = validate_text(priority, "priority", max_length=20).casefold()
        status = validate_text(status, "status", max_length=20).casefold()
        if priority not in VALID_GOAL_PRIORITIES or status not in VALID_GOAL_STATUSES:
            raise ValueError("Invalid goal priority or status.")
        if current_amount >= target_amount:
            status = "completed"
        connection = self._connection()
        try:
            cursor = connection.execute(
                """
                UPDATE financial_goals SET name = ?, target_amount = ?, current_amount = ?,
                    target_date = ?, priority = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (name, target_amount, current_amount, target_date, priority, status, goal_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Financial goal not found.")
            if status == "completed":
                self._add_notification(
                    connection, user_id, "goal_completed", "Savings goal completed",
                    f"You reached your {name} savings goal.",
                    f"goal:{goal_id}:completed",
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_goal(self, user_id, goal_id):
        user_id = validate_positive_id(user_id, "user_id")
        goal_id = validate_positive_id(goal_id, "goal_id")
        connection = self._connection()
        try:
            cursor = connection.execute(
                "DELETE FROM financial_goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Financial goal not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_recurring_transaction(self, user_id, account_id, category_id, transaction_type, amount, description, frequency, next_date, interval_count=1, end_date=None, merchant=None, notes=None):
        values = self._validate_recurring(
            user_id, account_id, category_id, transaction_type, amount, description,
            frequency, next_date, interval_count, end_date, merchant, notes,
        )
        connection = self._connection()
        try:
            self._validate_recurring_ownership(connection, *values[:4])
            cursor = connection.execute(
                """
                INSERT INTO recurring_transactions
                    (user_id, account_id, category_id, transaction_type, amount,
                     description, frequency, next_date, interval_count, end_date,
                     merchant, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.commit()
            return cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _validate_recurring(self, user_id, account_id, category_id, transaction_type, amount, description, frequency, next_date, interval_count, end_date, merchant, notes):
        user_id = validate_positive_id(user_id, "user_id")
        account_id = validate_positive_id(account_id, "account_id")
        if category_id is not None:
            category_id = validate_positive_id(category_id, "category_id")
        transaction_type = validate_text(transaction_type, "transaction_type", max_length=20).casefold()
        if transaction_type not in {"income", "expense"}:
            raise ValueError("Recurring transaction_type must be income or expense.")
        amount = validate_money(amount)
        description = validate_text(description, "description", max_length=500, required=False)
        frequency = validate_text(frequency, "frequency", max_length=20).casefold()
        if frequency not in VALID_RECURRING_FREQUENCIES:
            raise ValueError("frequency must be daily, weekly, monthly, or yearly.")
        if isinstance(interval_count, bool) or not isinstance(interval_count, int) or not 1 <= interval_count <= 365:
            raise ValueError("interval_count must be an integer between 1 and 365.")
        next_date, end_date = validate_date_range(next_date, end_date)
        if not next_date:
            raise ValueError("next_date is required.")
        merchant = validate_text(merchant, "merchant", max_length=255, required=False)
        notes = validate_text(notes, "notes", max_length=1000, required=False, allow_newlines=True)
        return (user_id, account_id, category_id, transaction_type, amount, description, frequency, next_date, interval_count, end_date, merchant, notes)

    @staticmethod
    def _validate_recurring_ownership(connection, user_id, account_id, category_id, transaction_type):
        if connection.execute(
            "SELECT 1 FROM accounts WHERE id = ? AND user_id = ? AND is_active = 1",
            (account_id, user_id),
        ).fetchone() is None:
            raise ValueError("The account does not belong to the selected user.")
        if category_id is not None and connection.execute(
            """
            SELECT 1 FROM categories WHERE id = ? AND category_type = ?
            AND (user_id = ? OR user_id IS NULL)
            """,
            (category_id, transaction_type, user_id),
        ).fetchone() is None:
            raise ValueError("The category is not available for this transaction type.")

    def get_recurring_transactions(self, user_id):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            return connection.execute(
                """
                SELECT r.id, r.account_id, r.category_id, r.transaction_type, r.amount,
                       r.description, r.frequency, r.interval_count, r.next_date,
                       r.end_date, r.is_active, r.last_generated_date, r.merchant,
                       r.notes, a.name, c.name
                FROM recurring_transactions r
                JOIN accounts a ON a.id = r.account_id
                LEFT JOIN categories c ON c.id = r.category_id
                WHERE r.user_id = ? ORDER BY r.is_active DESC, r.next_date, r.id
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

    def update_recurring_transaction(self, user_id, recurring_id, account_id, category_id, transaction_type, amount, description, frequency, next_date, interval_count=1, end_date=None, merchant=None, notes=None, is_active=True):
        recurring_id = validate_positive_id(recurring_id, "recurring_id")
        values = self._validate_recurring(
            user_id, account_id, category_id, transaction_type, amount, description,
            frequency, next_date, interval_count, end_date, merchant, notes,
        )
        connection = self._connection()
        try:
            self._validate_recurring_ownership(connection, *values[:4])
            cursor = connection.execute(
                """
                UPDATE recurring_transactions SET account_id = ?, category_id = ?,
                    transaction_type = ?, amount = ?, description = ?, frequency = ?,
                    next_date = ?, interval_count = ?, end_date = ?, merchant = ?, notes = ?,
                    is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (*values[1:], int(bool(is_active)), recurring_id, values[0]),
            )
            if cursor.rowcount != 1:
                raise ValueError("Recurring transaction not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_recurring_transaction(self, user_id, recurring_id):
        user_id = validate_positive_id(user_id, "user_id")
        recurring_id = validate_positive_id(recurring_id, "recurring_id")
        connection = self._connection()
        try:
            connection.execute(
                "UPDATE transactions SET recurring_transaction_id = NULL WHERE recurring_transaction_id = ? AND user_id = ?",
                (recurring_id, user_id),
            )
            cursor = connection.execute(
                "DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?",
                (recurring_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Recurring transaction not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def process_recurring_transactions(self, user_id, through_date=None):
        user_id = validate_positive_id(user_id, "user_id")
        through_date = validate_iso_date(
            through_date or date.today().isoformat(), "through_date", allow_none=False
        )
        connection = self._connection()
        generated = []
        try:
            if not hasattr(connection, "pool"):
                connection.execute("BEGIN IMMEDIATE")
            lock_clause = " FOR UPDATE" if hasattr(connection, "pool") else ""
            rows = connection.execute(
                """
                SELECT id, account_id, category_id, transaction_type, amount,
                       description, frequency, interval_count, next_date, end_date,
                       merchant, notes
                FROM recurring_transactions
                WHERE user_id = ? AND is_active = 1 AND next_date <= ?
                ORDER BY next_date, id
                """ + lock_clause,
                (user_id, through_date),
            ).fetchall()
            for row in rows:
                (recurring_id, account_id, category_id, transaction_type, amount,
                 description, frequency, interval_count, next_date, end_date,
                 merchant, notes) = row
                occurrence = str(next_date)
                end = str(end_date) if end_date else None
                processed = 0
                last_occurrence = None
                while occurrence <= through_date and (end is None or occurrence <= end):
                    last_occurrence = occurrence
                    exists = connection.execute(
                        """
                        SELECT 1 FROM transactions
                        WHERE recurring_transaction_id = ? AND scheduled_for = ?
                        """,
                        (recurring_id, occurrence),
                    ).fetchone()
                    if exists is None:
                        cursor = connection.execute(
                            """
                            INSERT INTO transactions
                                (user_id, account_id, category_id, transaction_type, amount,
                                 description, transaction_date, merchant, notes,
                                 recurring_transaction_id, scheduled_for)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (user_id, account_id, category_id, transaction_type, amount,
                             description, occurrence, merchant, notes, recurring_id, occurrence),
                        )
                        delta = amount if transaction_type == "income" else -amount
                        connection.execute(
                            "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                            (delta, account_id, user_id),
                        )
                        generated.append(cursor.lastrowid)
                        if transaction_type == "expense" and category_id is not None:
                            self._check_budget_notifications(
                                connection, user_id, category_id, occurrence
                            )
                    occurrence = _advance_date(occurrence, frequency, interval_count)
                    processed += 1
                    if processed >= 500:
                        raise ValueError("Recurring catch-up exceeds 500 occurrences.")
                active = int(not end or occurrence <= end)
                connection.execute(
                    """
                    UPDATE recurring_transactions
                    SET next_date = ?, last_generated_date = ?, is_active = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                    """,
                    (occurrence, last_occurrence, active, recurring_id, user_id),
                )
            if generated:
                self._add_notification(
                    connection, user_id, "recurring_generated",
                    "Scheduled transactions generated",
                    f"{len(generated)} due transaction(s) were added to your accounts.",
                )
            connection.commit()
            return generated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _notifications_enabled(connection, user_id):
        row = connection.execute(
            """
            SELECT COALESCE(notification_enabled, 1)
            FROM user_preferences WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return row is None or bool(row[0])

    def _add_notification(
        self, connection, user_id, notification_type, title, message, dedup_key=None
    ):
        if not self._notifications_enabled(connection, user_id):
            return
        connection.execute(
            """
            INSERT INTO notifications
                (user_id, notification_type, title, message, dedup_key)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, dedup_key) DO NOTHING
            """,
            (user_id, notification_type, title, message, dedup_key),
        )

    def _check_budget_notifications(self, connection, user_id, category_id, transaction_date):
        rows = connection.execute(
            """
            SELECT b.id, b.amount, c.name, COALESCE(SUM(t.amount), 0)
            FROM budgets b
            JOIN categories c ON c.id = b.category_id
            LEFT JOIN transactions t ON t.user_id = b.user_id
                AND t.category_id = b.category_id
                AND t.transaction_type = 'expense'
                AND t.transaction_date BETWEEN b.start_date AND b.end_date
            WHERE b.user_id = ? AND b.category_id = ?
                AND ? BETWEEN b.start_date AND b.end_date
            GROUP BY b.id, b.amount, c.name
            """,
            (user_id, category_id, transaction_date),
        ).fetchall()
        for budget_id, amount, category, spent in rows:
            ratio = float(spent) / float(amount)
            if ratio >= 1:
                self._add_notification(
                    connection, user_id, "budget_exceeded", "Budget limit reached",
                    f"Your {category} spending has reached or exceeded its budget.",
                    f"budget:{budget_id}:100",
                )
            elif ratio >= 0.8:
                self._add_notification(
                    connection, user_id, "budget_warning", "Budget is nearly used",
                    f"Your {category} spending has used at least 80% of its budget.",
                    f"budget:{budget_id}:80",
                )

    def import_transactions(self, user_id, account_id, rows, checksum, source_name):
        user_id = validate_positive_id(user_id, "user_id")
        account_id = validate_positive_id(account_id, "account_id")
        source_name = validate_text(source_name, "source_name", max_length=255)
        checksum = validate_text(checksum, "checksum", max_length=64)
        if not rows or len(rows) > 500:
            raise ValueError("An import must contain between 1 and 500 rows.")
        connection = self._connection()
        try:
            existing = connection.execute(
                "SELECT id, row_count FROM import_batches WHERE user_id = ? AND checksum = ?",
                (user_id, checksum),
            ).fetchone()
            if existing:
                return {"batch_id": existing[0], "imported_count": 0, "duplicate": True}
            if connection.execute(
                "SELECT 1 FROM accounts WHERE id = ? AND user_id = ? AND is_active = 1",
                (account_id, user_id),
            ).fetchone() is None:
                raise ValueError("The account does not belong to the selected user.")

            prepared = []
            for index, row in enumerate(rows, start=1):
                category_id = None
                category_name = row.get("category")
                if category_name:
                    category = connection.execute(
                        """
                        SELECT id FROM categories
                        WHERE LOWER(name) = LOWER(?) AND category_type = ?
                        AND (user_id = ? OR user_id IS NULL)
                        ORDER BY CASE WHEN user_id = ? THEN 0 ELSE 1 END, id
                        LIMIT 1
                        """,
                        (category_name, row["transaction_type"], user_id, user_id),
                    ).fetchone()
                    if category is None:
                        raise ValueError(
                            f"Import row {index}: category '{category_name}' is not available."
                        )
                    category_id = category[0]
                prepared.append((row, category_id))

            batch = connection.execute(
                """
                INSERT INTO import_batches (user_id, source_name, checksum, row_count)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, source_name, checksum, len(prepared)),
            )
            batch_id = batch.lastrowid
            transaction_ids = []
            for row, category_id in prepared:
                cursor = connection.execute(
                    """
                    INSERT INTO transactions
                        (user_id, account_id, category_id, transaction_type, amount,
                         description, transaction_date, merchant, notes, import_batch_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, account_id, category_id, row["transaction_type"],
                     row["amount"], row["description"], row["transaction_date"],
                     row["merchant"], row["notes"], batch_id),
                )
                transaction_ids.append(cursor.lastrowid)
                delta = row["amount"] if row["transaction_type"] == "income" else (
                    -row["amount"] if row["transaction_type"] == "expense" else 0
                )
                if delta:
                    connection.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                        (delta, account_id, user_id),
                    )
                if row["transaction_type"] == "expense" and category_id is not None:
                    self._check_budget_notifications(
                        connection, user_id, category_id, row["transaction_date"]
                    )
            self._add_notification(
                connection, user_id, "import_completed", "Transaction import completed",
                f"{len(transaction_ids)} transaction(s) were imported from {source_name}.",
                f"import:{batch_id}",
            )
            connection.commit()
            return {
                "batch_id": batch_id,
                "imported_count": len(transaction_ids),
                "duplicate": False,
                "transaction_ids": transaction_ids,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_notifications(self, user_id, limit=50, unread_only=False):
        user_id = validate_positive_id(user_id, "user_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100.")
        query = """
            SELECT id, notification_type, title, message, is_read, created_at
            FROM notifications WHERE user_id = ?
        """
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        connection = self._connection()
        try:
            return connection.execute(query, (user_id, limit)).fetchall()
        finally:
            connection.close()

    def mark_notification_read(self, user_id, notification_id):
        user_id = validate_positive_id(user_id, "user_id")
        notification_id = validate_positive_id(notification_id, "notification_id")
        connection = self._connection()
        try:
            cursor = connection.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                (notification_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Notification not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_all_notifications_read(self, user_id):
        user_id = validate_positive_id(user_id, "user_id")
        connection = self._connection()
        try:
            connection.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
                (user_id,),
            )
            connection.commit()
        finally:
            connection.close()

    def delete_notification(self, user_id, notification_id):
        user_id = validate_positive_id(user_id, "user_id")
        notification_id = validate_positive_id(notification_id, "notification_id")
        connection = self._connection()
        try:
            cursor = connection.execute(
                "DELETE FROM notifications WHERE id = ? AND user_id = ?",
                (notification_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Notification not found.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
