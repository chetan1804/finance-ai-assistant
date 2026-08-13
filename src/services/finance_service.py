from datetime import date

from src.database.db import get_connection


class FinanceService:

    def __init__(self, database_path="data/finance.db"):
        self.database_path = database_path

    def _connection(self):
        return get_connection()

    # =========================================================
    # BASIC FINANCE QUERIES
    # =========================================================

    def total_income(self):
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE transaction_type = 'income'
            """)

            return cursor.fetchone()[0]

        finally:
            connection.close()

    def total_expenses(self):
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE transaction_type = 'expense'
            """)

            return cursor.fetchone()[0]

        finally:
            connection.close()

    def total_savings(self):
        income = self.total_income()
        expenses = self.total_expenses()

        return income - expenses

    # =========================================================
    # CATEGORY EXPENSES
    # =========================================================

    def category_expenses(self, category: str) -> float:
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT COALESCE(SUM(t.amount), 0)
                FROM transactions t

                JOIN categories c
                    ON t.category_id = c.id

                WHERE t.transaction_type = 'expense'
                AND LOWER(c.name) = LOWER(?)
            """, (category,))

            result = cursor.fetchone()

            return result[0]

        finally:
            connection.close()

    # =========================================================
    # LARGEST EXPENSE
    # =========================================================

    def largest_expense(self):
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    t.amount,
                    t.merchant,
                    t.description,
                    t.transaction_date,
                    c.name AS category

                FROM transactions t

                LEFT JOIN categories c
                    ON t.category_id = c.id

                WHERE t.transaction_type = 'expense'

                ORDER BY
                    t.amount DESC,
                    t.transaction_date DESC

                LIMIT 1
            """)

            return cursor.fetchone()

        finally:
            connection.close()

    # =========================================================
    # MERCHANT EXPENSES
    # =========================================================

    def merchant_expenses(self, merchant):
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions

                WHERE transaction_type = 'expense'
                AND LOWER(merchant) LIKE LOWER(?)
            """, (f"%{merchant}%",))

            return cursor.fetchone()[0]

        finally:
            connection.close()

    # =========================================================
    # TRANSACTION COUNT
    # =========================================================

    def transaction_count(self):
        connection = self._connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM transactions
            """)

            return cursor.fetchone()[0]

        finally:
            connection.close()

    # =========================================================
    # CREATE USER
    # =========================================================

    def create_user(self, name, email, currency="INR"):
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
                "Transaction type must be income, expense or transfer."
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

            # Update account balance
            if transaction_type == "income":

                connection.execute(
                    """
                    UPDATE accounts
                    SET balance = balance + ?
                    WHERE id = ?
                    """,
                    (
                        amount,
                        account_id
                    )
                )

            elif transaction_type == "expense":

                connection.execute(
                    """
                    UPDATE accounts
                    SET balance = balance - ?
                    WHERE id = ?
                    """,
                    (
                        amount,
                        account_id
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

    def get_transactions(self, user_id):
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

                ORDER BY t.transaction_date DESC
                """,
                (user_id,)
            ).fetchall()

            return transactions

        finally:
            connection.close()

    # =========================================================
    # USER TOTAL INCOME
    # =========================================================

    def get_total_income(self, user_id):

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

            return result[0]

        finally:
            connection.close()

    # =========================================================
    # USER TOTAL EXPENSES
    # =========================================================

    def get_total_expenses(self, user_id):

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

            return result[0]

        finally:
            connection.close()

    # =========================================================
    # USER SAVINGS
    # =========================================================

    def get_savings(self, user_id):

        income = self.get_total_income(user_id)
        expenses = self.get_total_expenses(user_id)

        return income - expenses

    # =========================================================
    # EXPENSES BY CATEGORY
    # =========================================================

    def get_expenses_by_category(self, user_id):

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