"""Prepare ignored secrets for the single-instance Lightsail deployment."""

from __future__ import annotations

import argparse
import ipaddress
import os
import secrets
import string
from pathlib import Path

from dotenv import dotenv_values, set_key


ROOT = Path(__file__).resolve().parents[1]
SAFE_SECRET_ALPHABET = string.ascii_letters + string.digits


def validate_host(value: str) -> str:
    host = value.strip().lower()
    if not host or "://" in host or any(char in host for char in "/@?#"):
        raise RuntimeError("Host must not contain a scheme, port, path, or credentials.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        labels = host.split(".")
        if len(labels) < 2 or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not all(char.isalnum() or char == "-" for char in label)
            for label in labels
        ):
            raise RuntimeError("Host must be a valid IP address or DNS hostname.")
    return host


def generated_secret(length: int = 48) -> str:
    return "".join(secrets.choice(SAFE_SECRET_ALPHABET) for _ in range(length))


def prepare_values(existing: dict[str, str], host: str, https: bool) -> dict[str, str]:
    groq_key = existing.get("GROQ_API_KEY", "").strip()
    if not groq_key or groq_key.startswith("replace-with"):
        raise RuntimeError("Set a newly rotated GROQ_API_KEY in lightsail.env first.")
    public_host = validate_host(host)
    return {
        "GROQ_API_KEY": groq_key,
        "POSTGRES_USER": "arthnivo",
        "POSTGRES_DB": "arthnivo",
        "POSTGRES_PASSWORD": existing.get("POSTGRES_PASSWORD")
        or generated_secret(),
        "REDIS_PASSWORD": existing.get("REDIS_PASSWORD") or generated_secret(),
        "ARTHNIVO_SITE_ADDRESS": public_host if https else ":80",
        "FINANCE_ALLOWED_HOSTS": public_host,
        "FINANCE_HTTPS_REDIRECT": "true" if https else "false",
    }


def write_values(path: Path, values: dict[str, str]) -> None:
    path.touch(mode=0o600, exist_ok=True)
    os.chmod(path, 0o600)
    for key, value in values.items():
        set_key(str(path), key, value, quote_mode="always")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate PostgreSQL and Redis secrets for Lightsail."
    )
    parser.add_argument("--host", required=True, help="Static IP or configured domain.")
    parser.add_argument("--https", action="store_true", help="Enable domain-based HTTPS.")
    parser.add_argument("--env-file", type=Path, default=ROOT / "lightsail.env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    existing = (
        {
            key: str(value)
            for key, value in dotenv_values(args.env_file).items()
            if value is not None
        }
        if args.env_file.exists()
        else {}
    )
    values = prepare_values(existing, args.host, args.https)
    write_values(args.env_file, values)
    print(
        f"Prepared {args.env_file} for {'HTTPS' if args.https else 'HTTP'} "
        "without printing secrets."
    )


if __name__ == "__main__":
    main()
