import argparse
from pathlib import Path

from src.database.db import get_connection, initialize_database
from src.database.finance_service import FinanceService


DEFAULT_CATEGORIES = (
    ("Salary", "income"),
    ("Other income", "income"),
    ("Food", "expense"),
    ("Housing", "expense"),
    ("Transport", "expense"),
    ("Utilities", "expense"),
    ("Shopping", "expense"),
    ("Other expense", "expense"),
)


def bootstrap_user(
    name,
    email,
    currency="INR",
    account_name="Main account",
    database_path=None,
):
    """Create the first usable profile without duplicating existing data."""
    initialize_database(database_path)
    service = FinanceService(database_path)
    connection = get_connection(database_path)
    try:
        user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        connection.close()

    user_id = user[0] if user else service.create_user(name, email, currency)
    connection = get_connection(database_path)
    try:
        has_account = connection.execute(
            "SELECT 1 FROM accounts WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        existing_categories = {
            (row[0], row[1])
            for row in connection.execute(
                "SELECT name, category_type FROM categories WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        }
    finally:
        connection.close()

    if not has_account:
        service.create_account(
            user_id,
            account_name,
            "checking",
            currency=currency,
        )
    for category_name, category_type in DEFAULT_CATEGORIES:
        if (category_name, category_type) not in existing_categories:
            service.create_category(user_id, category_name, category_type)

    return user_id


def main():
    parser = argparse.ArgumentParser(
        description="Create an initial deployment user, account, and categories."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--currency", default="INR")
    parser.add_argument("--account-name", default="Main account")
    parser.add_argument("--database-path", type=Path)
    args = parser.parse_args()
    user_id = bootstrap_user(
        args.name,
        args.email,
        args.currency,
        args.account_name,
        args.database_path,
    )
    print(f"Deployment user ready. Configure a bearer token for user ID {user_id}.")


if __name__ == "__main__":
    main()
