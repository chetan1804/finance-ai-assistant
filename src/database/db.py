import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import IntegrityError as PostgresIntegrityError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = Path(__file__).with_name("migrations")
POSTGRES_MIGRATIONS_PATH = Path(__file__).with_name("postgres_migrations")
MIGRATION_PATTERN = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
INTEGRITY_ERRORS = (sqlite3.IntegrityError, PostgresIntegrityError)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str


def get_data_directory():
    """Resolve the writable application-data directory at runtime."""
    configured = os.getenv("FINANCE_DATA_DIR")
    return Path(configured).expanduser() if configured else PROJECT_ROOT / "data"


def get_database_path():
    """Resolve the finance database path from deployment configuration."""
    configured = os.getenv("FINANCE_DATABASE_PATH")
    return (
        Path(configured).expanduser()
        if configured
        else get_data_directory() / "finance.db"
    )


def get_database_url():
    value = os.getenv("FINANCE_DATABASE_URL")
    if value and not value.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("FINANCE_DATABASE_URL must use PostgreSQL.")
    return value


def _postgres_query(query):
    """Convert qmark bindings without touching quoted SQL text."""
    result = []
    quote = None
    index = 0
    while index < len(query):
        character = query[index]
        if quote:
            result.append(character)
            if character == quote:
                if index + 1 < len(query) and query[index + 1] == quote:
                    result.append(query[index + 1])
                    index += 1
                else:
                    quote = None
        elif character in ("'", '"'):
            quote = character
            result.append(character)
        elif character == "?":
            result.append("%s")
        else:
            result.append(character)
        index += 1
    return "".join(result)


class PostgresCursorAdapter:
    def __init__(self, connection, cursor):
        self.connection = connection
        self.cursor = cursor

    @property
    def lastrowid(self):
        row = self.connection.execute("SELECT LASTVAL()").fetchone()
        return row[0]

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)


class PostgresConnectionAdapter:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        cursor = self.connection.execute(_postgres_query(query), params)
        return PostgresCursorAdapter(self.connection, cursor)

    def executemany(self, query, params):
        cursor = self.connection.cursor()
        cursor.executemany(_postgres_query(query), params)
        return PostgresCursorAdapter(self.connection, cursor)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_connection(database_path=None):
    """Return a configured SQLite or PostgreSQL-compatible connection."""
    database_url = None if database_path is not None else get_database_url()
    if database_url:
        return PostgresConnectionAdapter(psycopg.connect(database_url))
    path = Path(database_path) if database_path else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def discover_migrations(migrations_path=None):
    directory = Path(migrations_path) if migrations_path else MIGRATIONS_PATH
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_PATTERN.fullmatch(path.name)
        if match is None:
            raise RuntimeError(f"Invalid migration filename: {path.name}")
        sql = path.read_text(encoding="utf-8")
        migrations.append(Migration(
            version=int(match.group(1)),
            name=match.group(2),
            sql=sql,
            checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        ))
    versions = [migration.version for migration in migrations]
    if not migrations or versions != list(range(1, len(migrations) + 1)):
        raise RuntimeError("Database migrations must be sequential and start at 001.")
    return migrations


def _apply_postgres_migrations(database_url, migrations_path=None):
    migrations = discover_migrations(migrations_path or POSTGRES_MIGRATIONS_PATH)
    newly_applied = []
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (61420260815,))
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied = {
                row[0]: (row[1], row[2])
                for row in connection.execute(
                    "SELECT version, name, checksum FROM schema_migrations"
                ).fetchall()
            }
            for migration in migrations:
                existing = applied.get(migration.version)
                if existing:
                    if existing != (migration.name, migration.checksum):
                        raise RuntimeError(
                            f"Applied migration {migration.version:03d} was modified."
                        )
                    continue
                connection.execute(migration.sql)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum)
                    VALUES (%s, %s, %s)
                    """,
                    (migration.version, migration.name, migration.checksum),
                )
                newly_applied.append(migration.version)
    return newly_applied


def apply_migrations(database_path=None, migrations_path=None):
    """Apply immutable migrations for the selected backend and verify checksums."""
    database_url = None if database_path is not None else get_database_url()
    if database_url:
        return _apply_postgres_migrations(database_url, migrations_path)
    connection = get_connection(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
        applied = {
            row[0]: (row[1], row[2])
            for row in connection.execute(
                "SELECT version, name, checksum FROM schema_migrations"
            ).fetchall()
        }
        newly_applied = []
        for migration in discover_migrations(migrations_path):
            existing = applied.get(migration.version)
            if existing:
                if existing != (migration.name, migration.checksum):
                    raise RuntimeError(
                        f"Applied migration {migration.version:03d} was modified."
                    )
                continue
            name = migration.name.replace("'", "''")
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{migration.sql}\n"
                "INSERT INTO schema_migrations (version, name, checksum) "
                f"VALUES ({migration.version}, '{name}', '{migration.checksum}');\n"
                "COMMIT;"
            )
            try:
                connection.executescript(script)
            except Exception:
                if connection.in_transaction:
                    connection.rollback()
                raise
            newly_applied.append(migration.version)
        return newly_applied
    finally:
        connection.close()


def migration_status(database_path=None, migrations_path=None):
    database_url = None if database_path is not None else get_database_url()
    if database_url:
        migrations = discover_migrations(migrations_path or POSTGRES_MIGRATIONS_PATH)
        with psycopg.connect(database_url) as connection:
            exists = connection.execute("SELECT to_regclass('schema_migrations')").fetchone()[0]
            applied = set()
            if exists:
                applied = {
                    row[0]
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations"
                    ).fetchall()
                }
        return {
            "backend": "postgresql",
            "current_version": max(applied, default=0),
            "latest_version": migrations[-1].version,
            "pending": [m.version for m in migrations if m.version not in applied],
        }
    migrations = discover_migrations(migrations_path)
    connection = get_connection(database_path)
    try:
        exists = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_migrations'
            """
        ).fetchone()
        applied = set()
        if exists:
            applied = {
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
        return {
            "backend": "sqlite",
            "current_version": max(applied, default=0),
            "latest_version": migrations[-1].version,
            "pending": [m.version for m in migrations if m.version not in applied],
        }
    finally:
        connection.close()


def initialize_database(database_path=None):
    """Bring the selected database to the latest schema version."""
    return apply_migrations(database_path)
