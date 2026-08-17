import sqlite3
from pathlib import Path

import pytest

from src.database.db import apply_migrations, migration_status


SCHEMA_SNAPSHOT = Path(__file__).resolve().parents[1] / "src" / "database" / "schema.sql"


def test_migrations_apply_in_order_and_are_idempotent(tmp_path):
    database_path = tmp_path / "finance.db"

    assert apply_migrations(database_path) == [1, 2, 3, 4]
    assert apply_migrations(database_path) == []
    assert migration_status(database_path) == {
        "backend": "sqlite",
        "current_version": 4,
        "latest_version": 4,
        "pending": [],
    }

    connection = sqlite3.connect(database_path)
    try:
        versions = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
    finally:
        connection.close()
    assert versions == [
        (1, "core_schema"),
        (2, "auth_sessions"),
        (3, "account_security"),
        (4, "recurring_transactions"),
    ]


def test_modified_applied_migration_is_rejected(tmp_path):
    database_path = tmp_path / "finance.db"
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "001_example.sql"
    migration.write_text("CREATE TABLE example (id INTEGER);", encoding="utf-8")
    apply_migrations(database_path, migrations)
    migration.write_text("CREATE TABLE changed (id INTEGER);", encoding="utf-8")

    with pytest.raises(RuntimeError, match="was modified"):
        apply_migrations(database_path, migrations)


def test_failed_migration_is_not_recorded(tmp_path):
    database_path = tmp_path / "finance.db"
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_broken.sql").write_text(
        "CREATE TABLE partial (id INTEGER); THIS IS NOT SQL;",
        encoding="utf-8",
    )

    with pytest.raises(sqlite3.OperationalError):
        apply_migrations(database_path, migrations)

    connection = sqlite3.connect(database_path)
    try:
        recorded = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        partial = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'partial'"
        ).fetchone()
    finally:
        connection.close()
    assert recorded == 0
    assert partial is None


def test_non_sequential_migrations_are_rejected(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "002_second.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(RuntimeError, match="sequential"):
        apply_migrations(tmp_path / "finance.db", migrations)


def test_existing_unversioned_database_is_preserved(tmp_path):
    database_path = tmp_path / "existing.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(SCHEMA_SNAPSHOT.read_text(encoding="utf-8"))
        user_id = connection.execute(
            "INSERT INTO users (name, email) VALUES ('Asha', 'asha@example.com')"
        ).lastrowid
        account_id = connection.execute(
            """
            INSERT INTO accounts (user_id, name, account_type, balance)
            VALUES (?, 'Bank', 'checking', 4800)
            """,
            (user_id,),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO transactions
            (user_id, account_id, transaction_type, amount, description, transaction_date)
            VALUES (?, ?, 'expense', 200, 'Groceries', '2026-08-15')
            """,
            (user_id, account_id),
        )
        connection.commit()
    finally:
        connection.close()

    assert apply_migrations(database_path) == [1, 2, 3, 4]

    connection = sqlite3.connect(database_path)
    try:
        transaction = connection.execute(
            "SELECT description, amount FROM transactions"
        ).fetchone()
        balance = connection.execute("SELECT balance FROM accounts").fetchone()[0]
    finally:
        connection.close()
    assert transaction == ("Groceries", 200.0)
    assert balance == 4800.0
