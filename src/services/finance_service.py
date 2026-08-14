from datetime import date

from src.database.db import get_connection


class FinanceService:

    def __init__(self, database_path="data/finance.db"):
        self.database_path = database_path

    def _connection(self):
        """
        Get a database connection.

        The actual connection management is handled
        by src.database.db.get_connection().
        """
        return get_connection()

    # =========================================================
    # BASIC FINANCE QUERIES
    # =========================================================

    def get_total_income(self, user_id: int) -> float:
        """
        Get total income for a specific user.
        """

        connection = self._connection()

        try:
            result = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE user_id = ?
                AND transaction_type = 'income'
                """,
                (user_id,)
            ).fetchone()

            return float(result[0])

        finally:
            connection.close()

    # =========================================================
    # TOTAL EXPENSES
    # =========================================================

    def get_total_expenses(self, user_id: int) -> float:
        """
        Get total expenses for a specific user.
        """

        connection = self._connection()

        try:
            result = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE user_id = ?
                AND transaction_type = 'expense'
                """,
                (user_id,)
            ).fetchone()

            return float(result[0])

        finally:
            connection.close()

    # =========================================================
    # SAVINGS
    # =========================================================

    def get_savings(self, user_id: int) -> float:
        """
        Calculate savings for a specific user.

        Savings = Income - Expenses
        """

        income = self.get_total_income(user_id)

        expenses = self.get_total_expenses(user_id)

        return income - expenses

    # =========================================================
    # CATEGORY EXPENSES
    # =========================================================

    def get_category_expenses(
        self,
        user_id: int,
        category: str
    ) -> float:
        """
        Get total expenses for a specific category
        and user.
        """

        connection = self._connection()

        try:
            result = connection.execute(
                """
                SELECT COALESCE(SUM(t.amount), 0)

                FROM transactions t

                JOIN categories c
                    ON t.category_id = c.id

                WHERE t.user_id = ?

                AND t.transaction_type = 'expense'

                AND LOWER(c.name) = LOWER(?)
                """,
                (
                    user_id,
                    category
                )
            ).fetchone()

            return float(result[0])

        finally:
            connection.close()

    # =========================================================
    # EXPENSES BY CATEGORY
    # =========================================================

    def get_expenses_by_category(
        self,
        user_id: int
    ):
        """
        Get all expense totals grouped by category
        for a specific user.
        """

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
                (user_id,)
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
        """
        Get the largest expense for a specific user.
        """

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
                (user_id,)
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
        """
        Get total expenses for a specific merchant
        and user.
        """

        connection = self._connection()

        try:
            result = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)

                FROM transactions

                WHERE user_id = ?

                AND transaction_type = 'expense'

                AND LOWER(merchant) LIKE LOWER(?)
                """,
                (
                    user_id,
                    f"%{merchant}%"
                )
            ).fetchone()

            return float(result[0])

        finally:
            connection.close()

    # =========================================================
    # TRANSACTION COUNT
    # =========================================================

    def get_transaction_count(
        self,
        user_id: int
    ) -> int:
        """
        Get total number of transactions
        for a specific user.
        """

        connection = self._connection()

        try:
            result = connection.execute(
                """
                SELECT COUNT(*)

                FROM transactions

                WHERE user_id = ?
                """,
                (user_id,)
            ).fetchone()

            return int(result[0])

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
        """
        Create a new user.
        """

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
        """
        Create an account for a specific user.
        """

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
        """
        Create a category for a specific user.
        """

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
        """
        Add a transaction for a specific user.
        """

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
            transaction_date = date.today().isoformat()

        connection = self._connection()

        try:
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

            # ---------------------------------------------
            # Update account balance
            # ---------------------------------------------

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
        """
        Get all transactions belonging to a specific user.
        """

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
                (user_id,)
            ).fetchall()

            return transactions

        finally:
            connection.close()