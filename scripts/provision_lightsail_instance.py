"""Provision the single USD 12/month Lightsail instance for ArthNivo."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_DIRECTORY = ROOT / ".lightsail"
INSTANCE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,253}[A-Za-z0-9]$")


def run(command: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout or ""


def aws_json(arguments: list[str], region: str) -> dict:
    output = run(
        ["aws", "lightsail", *arguments, "--region", region, "--output", "json"],
        capture=True,
    )
    return json.loads(output or "{}")


def secure_json_file(value: dict) -> Path:
    descriptor, filename = tempfile.mkstemp(prefix="arthnivo-lightsail-", suffix=".json")
    path = Path(filename)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream)
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers) or (0,)


def select_ubuntu_blueprint(blueprints: list[dict]) -> dict:
    ubuntu = [
        blueprint
        for blueprint in blueprints
        if blueprint.get("isActive")
        and "ubuntu" in (
            f"{blueprint.get('blueprintId', '')} {blueprint.get('name', '')}"
        ).lower()
        and "server" in blueprint.get("type", "os").lower()
    ]
    if not ubuntu:
        ubuntu = [
            blueprint
            for blueprint in blueprints
            if blueprint.get("isActive")
            and "ubuntu" in blueprint.get("blueprintId", "").lower()
        ]
    if not ubuntu:
        raise RuntimeError("No active Ubuntu blueprint is available in this region.")
    return max(
        ubuntu,
        key=lambda item: version_tuple(
            f"{item.get('version', '')} {item.get('blueprintId', '')}"
        ),
    )


def select_usd12_bundle(bundles: list[dict]) -> dict:
    matches = [
        bundle
        for bundle in bundles
        if bundle.get("isActive")
        and float(bundle.get("price", -1)) == 12.0
        and float(bundle.get("ramSizeInGb", 0)) >= 2.0
    ]
    if not matches:
        raise RuntimeError(
            "The USD 12 Lightsail Linux bundle is not available in this region."
        )
    return min(matches, key=lambda item: float(item.get("ramSizeInGb", 0)))


def cloud_init_script() -> str:
    return """#!/bin/bash
set -eux
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 rsync
systemctl enable --now docker
usermod -aG docker ubuntu
mkdir -p /opt/arthnivo
chown ubuntu:ubuntu /opt/arthnivo
"""


def get_instance(name: str, region: str) -> dict | None:
    result = aws_json(["get-instances"], region)
    return next(
        (item for item in result.get("instances", []) if item.get("name") == name),
        None,
    )


def wait_for_instance(name: str, region: str, timeout_seconds: int = 900) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_state = "unknown"
    while time.monotonic() < deadline:
        instance = get_instance(name, region)
        if instance:
            last_state = (instance.get("state") or {}).get("name", "unknown")
            if last_state == "running":
                return instance
        time.sleep(10)
    raise RuntimeError(
        f"Timed out waiting for the instance; last state was {last_state}."
    )


def ensure_key_pair(key_name: str, key_path: Path, region: str) -> None:
    if key_path.exists():
        os.chmod(key_path, 0o600)
        return
    existing = aws_json(["get-key-pairs"], region).get("keyPairs", [])
    if any(item.get("name") == key_name for item in existing):
        raise RuntimeError(
            f"AWS key pair {key_name} exists but {key_path} is missing. "
            "Use another key name; private keys cannot be downloaded again."
        )
    created = aws_json(["create-key-pair", "--key-pair-name", key_name], region)
    encoded = created.get("privateKeyBase64")
    if not encoded:
        raise RuntimeError("Lightsail did not return the new private SSH key.")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = encoded.strip()
    if normalized.startswith("-----BEGIN "):
        private_key = f"{normalized}\n".encode("ascii")
    else:
        normalized += "=" * (-len(normalized) % 4)
        private_key = base64.b64decode(normalized, validate=True)
    key_path.write_bytes(private_key)
    os.chmod(key_path, 0o600)


def ensure_static_ip(instance_name: str, static_ip_name: str, region: str) -> str:
    addresses = aws_json(["get-static-ips"], region).get("staticIps", [])
    static_ip = next(
        (item for item in addresses if item.get("name") == static_ip_name),
        None,
    )
    if static_ip is None:
        aws_json(["allocate-static-ip", "--static-ip-name", static_ip_name], region)
    elif static_ip.get("isAttached"):
        if static_ip.get("attachedTo") != instance_name:
            raise RuntimeError(
                f"Static IP {static_ip_name} is attached to another instance."
            )
        return static_ip["ipAddress"]
    if not static_ip or not static_ip.get("isAttached"):
        aws_json(
            [
                "attach-static-ip",
                "--static-ip-name",
                static_ip_name,
                "--instance-name",
                instance_name,
            ],
            region,
        )
    addresses = aws_json(["get-static-ips"], region).get("staticIps", [])
    static_ip = next(
        (item for item in addresses if item.get("name") == static_ip_name),
        None,
    )
    if not static_ip or not static_ip.get("ipAddress"):
        raise RuntimeError("Lightsail did not return the attached static IP.")
    return static_ip["ipAddress"]


def set_instance_firewall(
    instance_name: str,
    region: str,
    ssh_cidr: str,
) -> None:
    port_infos = [
        {
            "fromPort": 22,
            "toPort": 22,
            "protocol": "tcp",
            "cidrs": [ssh_cidr],
        },
        {"fromPort": 80, "toPort": 80, "protocol": "tcp"},
        {"fromPort": 443, "toPort": 443, "protocol": "tcp"},
    ]
    document = secure_json_file(port_infos)
    try:
        aws_json(
            [
                "put-instance-public-ports",
                "--instance-name",
                instance_name,
                "--port-infos",
                f"file://{document}",
            ],
            region,
        )
    finally:
        document.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one USD 12 Lightsail instance for ArthNivo."
    )
    parser.add_argument("--profile", help="Optional named AWS CLI profile.")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--availability-zone", default="ap-south-1a")
    parser.add_argument("--instance", default="arthnivo")
    parser.add_argument("--key-name", default="arthnivo-deploy")
    parser.add_argument("--static-ip-name", default="arthnivo-ip")
    parser.add_argument(
        "--ssh-cidr",
        required=True,
        help="Your public IPv4 address in CIDR form, such as 203.0.113.10/32.",
    )
    parser.add_argument(
        "--confirm-monthly-charge",
        required=True,
        choices=("USD12",),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.profile:
        os.environ["AWS_PROFILE"] = args.profile
    if not shutil.which("aws"):
        raise RuntimeError("Install AWS CLI version 2 before provisioning Lightsail.")
    if not INSTANCE_NAME_PATTERN.fullmatch(args.instance):
        raise RuntimeError("Invalid Lightsail instance name.")

    key_path = STATE_DIRECTORY / f"{args.key_name}.pem"
    ensure_key_pair(args.key_name, key_path, args.region)
    instance = get_instance(args.instance, args.region)
    if instance is None:
        blueprints = aws_json(["get-blueprints"], args.region).get("blueprints", [])
        bundles = aws_json(["get-bundles"], args.region).get("bundles", [])
        blueprint = select_ubuntu_blueprint(blueprints)
        bundle = select_usd12_bundle(bundles)
        request = {
            "instanceNames": [args.instance],
            "availabilityZone": args.availability_zone,
            "blueprintId": blueprint["blueprintId"],
            "bundleId": bundle["bundleId"],
            "userData": cloud_init_script(),
            "keyPairName": args.key_name,
            "tags": [{"key": "application", "value": "ArthNivo"}],
        }
        document = secure_json_file(request)
        try:
            print(
                f"Creating {args.instance} with {bundle['bundleId']} "
                "(USD12/month)..."
            )
            aws_json(
                ["create-instances", "--cli-input-json", f"file://{document}"],
                args.region,
            )
        finally:
            document.unlink(missing_ok=True)
        instance = wait_for_instance(args.instance, args.region)

    static_ip = ensure_static_ip(args.instance, args.static_ip_name, args.region)
    set_instance_firewall(args.instance, args.region, args.ssh_cidr)
    print(f"Lightsail instance is running at {static_ip}")
    print(f"SSH key: {key_path}")


if __name__ == "__main__":
    main()
