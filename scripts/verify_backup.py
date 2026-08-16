import argparse
from pathlib import Path

from src.operations.backups import verify_backup


def main():
    parser = argparse.ArgumentParser(description="Verify a database backup archive.")
    parser.add_argument("backup_directory", type=Path)
    args = parser.parse_args()

    manifest = verify_backup(args.backup_directory)
    names = ", ".join(artifact["filename"] for artifact in manifest["artifacts"])
    print(f"Backup is valid: {names}")


if __name__ == "__main__":
    main()
