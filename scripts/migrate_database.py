import argparse
from pathlib import Path

from src.database.db import apply_migrations, migration_status


def backend_name(value):
    return "PostgreSQL" if value == "postgresql" else "SQLite"


def main():
    parser = argparse.ArgumentParser(
        description="Apply pending versioned database migrations."
    )
    parser.add_argument("--database-path", type=Path)
    parser.add_argument("--check", action="store_true", help="Exit nonzero when migrations are pending.")
    args = parser.parse_args()

    before = migration_status(args.database_path)
    if args.check:
        print(
            f"{backend_name(before['backend'])} database version "
            f"{before['current_version']} of "
            f"{before['latest_version']}; pending: {before['pending']}"
        )
        raise SystemExit(1 if before["pending"] else 0)

    applied = apply_migrations(args.database_path)
    after = migration_status(args.database_path)
    print(
        f"{backend_name(after['backend'])} database is at version "
        f"{after['current_version']} of "
        f"{after['latest_version']}. Applied: {applied or 'none'}"
    )


if __name__ == "__main__":
    main()
