import sqlite3
from pathlib import Path


# ============================================================
# DATABASE PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "data" / "finance.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    """
    Create a NEW SQLite connection.

    A new connection is returned every time this function
    is called. This prevents connections from being shared
    between threads.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH)
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    try:

        connection.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                currency TEXT DEFAULT 'INR'
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                institution TEXT,
                balance REAL DEFAULT 0,
                currency TEXT DEFAULT 'INR',

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                category_type TEXT NOT NULL,
                parent_id INTEGER,

                FOREIGN KEY (user_id)
                    REFERENCES users(id),

                FOREIGN KEY (parent_id)
                    REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                category_id INTEGER,

                transaction_type TEXT NOT NULL,

                amount REAL NOT NULL,

                description TEXT,

                transaction_date TEXT NOT NULL,

                merchant TEXT,

                notes TEXT,

                FOREIGN KEY (user_id)
                    REFERENCES users(id),

                FOREIGN KEY (account_id)
                    REFERENCES accounts(id),

                FOREIGN KEY (category_id)
                    REFERENCES categories(id)
            );
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()