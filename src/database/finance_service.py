from datetime import date

from src.database.db import get_connection


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

        connection = self._connection()

        try:

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

        if amount <= 0:

            raise ValueError(
                "Amount must be greater than zero."
            )

        if transaction_type not in [
            "income",
            "expense",
            "transfer"
        ]:

            raise ValueError(
                "Transaction type must be "
                "income, expense or transfer."
            )

        if transaction_date is None:

            transaction_date = (
                date.today().isoformat()
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
        user_id: int
    ):

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
                    a.name AS account

                FROM transactions t

                LEFT JOIN categories c
                    ON t.category_id = c.id

                JOIN accounts a
                    ON t.account_id = a.id

                WHERE t.user_id = ?

                ORDER BY
                    t.transaction_date DESC,
                    t.id DESC
                """,
                (
                    user_id,
                )
            ).fetchall()

            return transactions

        finally:

            connection.close()
