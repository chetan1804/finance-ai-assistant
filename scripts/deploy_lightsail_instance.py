"""Upload and deploy ArthNivo to an existing Lightsail instance."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY = ROOT / ".lightsail" / "arthnivo-deploy.pem"
REQUIRED_SETTINGS = (
    "GROQ_API_KEY",
    "POSTGRES_USER",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "ARTHNIVO_SITE_ADDRESS",
    "FINANCE_ALLOWED_HOSTS",
    "FINANCE_HTTPS_REDIRECT",
)


def load_environment(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"Deployment environment file not found: {path}")
    values = {
        key: str(value)
        for key, value in dotenv_values(path).items()
        if value is not None and str(value).strip()
    }
    missing = [name for name in REQUIRED_SETTINGS if not values.get(name)]
    if missing:
        raise RuntimeError(
            "Prepare lightsail.env before deployment. Missing: " + ", ".join(missing)
        )
    return values


def run(command: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout or ""


def ssh_base(key: Path, user: str, host: str) -> list[str]:
    return [
        "ssh",
        "-i",
        str(key),
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
    ]


def smoke_test(url: str) -> None:
    for path in ("/health", "/ready", "/version"):
        endpoint = url.rstrip("/") + path
        try:
            with urllib.request.urlopen(endpoint, timeout=20) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"{endpoint} returned HTTP {response.status}.")
        except urllib.error.URLError as error:
            raise RuntimeError(f"Verification failed for {endpoint}: {error}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy ArthNivo to one Lightsail instance."
    )
    parser.add_argument("--host", required=True, help="Instance static IPv4 address.")
    parser.add_argument("--user", default="ubuntu")
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--env-file", type=Path, default=ROOT / "lightsail.env")
    parser.add_argument("--public-url", help="Defaults to HTTP static IP.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.key.is_file():
        raise RuntimeError(f"SSH private key not found: {args.key}")
    os.chmod(args.key, 0o600)
    load_environment(args.env_file)
    for command in ("ssh", "scp", "rsync"):
        if not shutil.which(command):
            raise RuntimeError(f"Required deployment command is missing: {command}")

    ssh = ssh_base(args.key, args.user, args.host)
    print("Waiting for Lightsail cloud initialization...")
    run([*ssh, "sudo cloud-init status --wait || true"])
    print("Ensuring Docker Compose and deployment tools are installed...")
    run(
        [
            *ssh,
            (
                "if ! command -v docker >/dev/null 2>&1 || "
                "! sudo docker compose version >/dev/null 2>&1 || "
                "! command -v rsync >/dev/null 2>&1; then "
                "sudo apt-get update && "
                "sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "
                "docker.io docker-compose-v2 rsync; "
                "fi; "
                "sudo systemctl enable --now docker; "
                "sudo usermod -aG docker ubuntu; "
                "sudo mkdir -p /opt/arthnivo; "
                "sudo chown ubuntu:ubuntu /opt/arthnivo"
            ),
        ]
    )

    rsync_shell = (
        f"ssh -i {args.key} -o StrictHostKeyChecking=accept-new"
    )
    print("Uploading application files without local secrets or data...")
    run(
        [
            "rsync",
            "-az",
            "--exclude=.git",
            "--exclude=.venv",
            "--exclude=.lightsail",
            "--exclude=.env",
            "--exclude=lightsail.env",
            "--exclude=frontend/node_modules",
            "--exclude=frontend/dist",
            "--exclude=data",
            "--exclude=backups",
            "-e",
            rsync_shell,
            f"{ROOT}/",
            f"{args.user}@{args.host}:/opt/arthnivo/",
        ]
    )
    run(
        [
            "scp",
            "-i",
            str(args.key),
            "-o",
            "StrictHostKeyChecking=accept-new",
            str(args.env_file),
            f"{args.user}@{args.host}:/opt/arthnivo/lightsail.env",
        ]
    )
    revision = run(["git", "rev-parse", "--short=12", "HEAD"], capture=True).strip()
    built_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    remote_command = (
        "cd /opt/arthnivo && chmod 600 lightsail.env && "
        f"FINANCE_RELEASE_VERSION={revision} FINANCE_COMMIT_SHA={revision} "
        f"FINANCE_BUILD_DATE={built_at} "
        "docker compose --env-file lightsail.env -f compose.lightsail.yaml "
        "up --detach --build --remove-orphans"
    )
    print("Building and starting ArthNivo, PostgreSQL, Redis, and Caddy...")
    run([*ssh, remote_command])
    run(
        [
            *ssh,
            "cd /opt/arthnivo && docker compose --env-file lightsail.env "
            "-f compose.lightsail.yaml ps",
        ]
    )
    public_url = args.public_url or f"http://{args.host}"
    smoke_test(public_url)
    print(f"ArthNivo is live at {public_url}")


if __name__ == "__main__":
    main()
