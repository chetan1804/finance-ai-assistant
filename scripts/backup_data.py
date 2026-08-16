import argparse
from pathlib import Path

from src.operations.backups import create_backup


def main():
    parser = argparse.ArgumentParser(
        description="Create and verify a backup of configured persistent storage."
    )
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()

    backup = create_backup(args.output_directory)
    print(f"Verified backup created at {backup}")


if __name__ == "__main__":
    main()
