import base64
from pathlib import Path

import pytest
import yaml

from scripts.deploy_lightsail_instance import load_environment
from scripts.prepare_lightsail_instance_env import prepare_values, validate_host
from scripts.provision_lightsail_instance import (
    cloud_init_script,
    ensure_key_pair,
    select_ubuntu_blueprint,
    select_usd12_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def test_lightsail_compose_keeps_data_services_private_and_persistent():
    compose = yaml.safe_load(
        (ROOT / "compose.lightsail.yaml").read_text(encoding="utf-8")
    )
    services = compose["services"]

    assert "ports" not in services["postgres"]
    assert "ports" not in services["redis"]
    assert services["postgres"]["volumes"] == [
        "postgres-data:/var/lib/postgresql/data"
    ]
    assert services["redis"]["volumes"] == ["redis-data:/data"]
    assert services["caddy"]["ports"] == ["80:80", "443:443"]
    assert services["arthnivo"]["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert services["arthnivo"]["depends_on"]["redis"]["condition"] == (
        "service_healthy"
    )
    assert compose["networks"]["backend"]["internal"] is True


def test_lightsail_secrets_are_excluded_from_git_and_docker():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "lightsail.env" in gitignore
    assert "lightsail.env" in dockerignore
    assert ".lightsail" in gitignore
    assert ".lightsail" in dockerignore


def test_instance_environment_generates_internal_service_credentials():
    values = prepare_values(
        {"GROQ_API_KEY": "new-provider-key"},
        "203.0.113.10",
        https=False,
    )

    assert values["POSTGRES_USER"] == "arthnivo"
    assert values["POSTGRES_DB"] == "arthnivo"
    assert len(values["POSTGRES_PASSWORD"]) == 48
    assert len(values["REDIS_PASSWORD"]) == 48
    assert values["ARTHNIVO_SITE_ADDRESS"] == ":80"
    assert values["FINANCE_ALLOWED_HOSTS"] == "203.0.113.10"
    assert values["FINANCE_HTTPS_REDIRECT"] == "false"


def test_instance_environment_enables_caddy_https_for_a_domain():
    values = prepare_values(
        {"GROQ_API_KEY": "new-provider-key"},
        "app.example.com",
        https=True,
    )

    assert values["ARTHNIVO_SITE_ADDRESS"] == "app.example.com"
    assert values["FINANCE_HTTPS_REDIRECT"] == "true"


@pytest.mark.parametrize(
    "host",
    ("https://example.com", "example.com/path", "example", "bad host.example"),
)
def test_instance_environment_rejects_invalid_hosts(host):
    with pytest.raises(RuntimeError):
        validate_host(host)


def test_deployment_environment_requires_every_compose_secret(tmp_path):
    env_file = tmp_path / "lightsail.env"
    env_file.write_text("GROQ_API_KEY=new-key\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="POSTGRES_USER"):
        load_environment(env_file)


def test_instance_selection_uses_latest_ubuntu_and_usd12_bundle():
    blueprint = select_ubuntu_blueprint(
        [
            {
                "blueprintId": "ubuntu_22_04",
                "name": "Ubuntu",
                "version": "22.04 LTS",
                "isActive": True,
            },
            {
                "blueprintId": "ubuntu_24_04",
                "name": "Ubuntu",
                "version": "24.04 LTS",
                "isActive": True,
            },
        ]
    )
    bundle = select_usd12_bundle(
        [
            {"bundleId": "micro", "price": 7, "ramSizeInGb": 1, "isActive": True},
            {"bundleId": "small", "price": 12, "ramSizeInGb": 2, "isActive": True},
        ]
    )

    assert blueprint["blueprintId"] == "ubuntu_24_04"
    assert bundle["bundleId"] == "small"


def test_key_pair_accepts_unpadded_base64(monkeypatch, tmp_path):
    private_key = b"-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n"
    encoded = base64.b64encode(private_key).decode("ascii").rstrip("=")

    def fake_aws_json(arguments, region):
        if arguments == ["get-key-pairs"]:
            return {"keyPairs": []}
        return {"privateKeyBase64": encoded}

    monkeypatch.setattr(
        "scripts.provision_lightsail_instance.aws_json",
        fake_aws_json,
    )
    key_path = tmp_path / "key.pem"

    ensure_key_pair("test-key", key_path, "ap-south-1")

    assert key_path.read_bytes() == private_key


def test_key_pair_accepts_pem_decoded_by_aws_cli(monkeypatch, tmp_path):
    private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n"

    def fake_aws_json(arguments, region):
        if arguments == ["get-key-pairs"]:
            return {"keyPairs": []}
        return {"privateKeyBase64": private_key}

    monkeypatch.setattr(
        "scripts.provision_lightsail_instance.aws_json",
        fake_aws_json,
    )
    key_path = tmp_path / "key.pem"

    ensure_key_pair("test-key", key_path, "ap-south-1")

    assert key_path.read_text(encoding="ascii") == private_key


def test_cloud_init_script_is_compatible_when_lightsail_uses_sh():
    script = cloud_init_script()

    assert "set -eux\n" in script
    assert "pipefail" not in script


def test_container_healthcheck_uses_the_configured_trusted_host():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "os.getenv('FINANCE_ALLOWED_HOSTS', 'localhost')" in dockerfile
    assert "headers={'Host':host" in dockerfile
