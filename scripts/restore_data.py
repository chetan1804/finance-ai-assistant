import argparse
from pathlib import Path

from src.operations.backups import restore_backup


def main():
    parser = argparse.ArgumentParser(
        description="Verify and restore a database backup archive."
    )
    parser.add_argument("backup_directory", type=Path)
    parser.add_argument("--finance-path", type=Path)
    parser.add_argument("--checkpoint-path", type=Path)
    parser.add_argument("--finance-url")
    parser.add_argument("--checkpoint-url")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing SQLite file or non-empty PostgreSQL database.",
    )
    args = parser.parse_args()
    if args.finance_path and args.finance_url:
        parser.error("Use only one of --finance-path and --finance-url.")
    if args.checkpoint_path and args.checkpoint_url:
        parser.error("Use only one of --checkpoint-path and --checkpoint-url.")

    roles = restore_backup(
        args.backup_directory,
        finance_path=args.finance_path,
        checkpoint_path=args.checkpoint_path,
        finance_url=args.finance_url,
        checkpoint_url=args.checkpoint_url,
        force=args.force,
    )
    print(f"Restored and verified storage roles: {', '.join(roles)}")


if __name__ == "__main__":
    main()
