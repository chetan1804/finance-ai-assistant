import os
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


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


def get_connection(database_path=None):
    """Return a new SQLite connection with foreign keys enabled."""
    path = Path(database_path) if database_path else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(database_path=None):
    """Create every application table in the selected database."""
    connection = get_connection(database_path)

    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
