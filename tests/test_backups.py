import json
import os
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from src.database.db import initialize_database
from src.operations.backups import (
    BackupError,
    create_backup,
    restore_backup,
    verify_backup,
)


def _configure_sqlite(monkeypatch, tmp_path):
    finance = tmp_path / "source" / "finance.db"
    checkpoints = tmp_path / "source" / "checkpoints.db"
    monkeypatch.delenv("FINANCE_DATABASE_URL", raising=False)
    monkeypatch.delenv("FINANCE_CHECKPOINT_URL", raising=False)
    monkeypatch.setenv("FINANCE_DATABASE_PATH", str(finance))
    monkeypatch.setenv("FINANCE_CHECKPOINT_PATH", str(checkpoints))
    initialize_database(finance)
    with sqlite3.connect(finance) as connection:
        connection.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Backup User", "backup@example.com"),
        )
    checkpoints.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(checkpoints) as connection:
        connection.execute("CREATE TABLE checkpoints (thread_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO checkpoints VALUES ('conversation-1')")
    return finance, checkpoints


def test_sqlite_backup_is_verified_and_restorable(monkeypatch, tmp_path):
    _configure_sqlite(monkeypatch, tmp_path)

    backup = create_backup(tmp_path / "backups")
    manifest = verify_backup(backup)
    manifest_text = (backup / "manifest.json").read_text(encoding="utf-8")

    assert {tuple(item["roles"]) for item in manifest["artifacts"]} == {
        ("finance",),
        ("checkpoints",),
    }
    assert "FINANCE_DATABASE" not in manifest_text
    assert "backup@example.com" not in manifest_text

    finance_restore = tmp_path / "restore" / "finance.db"
    checkpoint_restore = tmp_path / "restore" / "checkpoints.db"
    restored = restore_backup(
        backup,
        finance_path=finance_restore,
        checkpoint_path=checkpoint_restore,
    )

    assert restored == ["checkpoints", "finance"]
    with sqlite3.connect(finance_restore) as connection:
        name = connection.execute("SELECT name FROM users").fetchone()[0]
        assert name == "Backup User"
    with sqlite3.connect(checkpoint_restore) as connection:
        thread_id = connection.execute(
            "SELECT thread_id FROM checkpoints"
        ).fetchone()[0]
        assert thread_id == "conversation-1"


def test_restore_refuses_to_replace_existing_sqlite_database(monkeypatch, tmp_path):
    _configure_sqlite(monkeypatch, tmp_path)
    backup = create_backup(tmp_path / "backups")
    target = tmp_path / "existing.db"
    target.write_bytes(b"keep me")

    with pytest.raises(BackupError, match="already exists"):
        restore_backup(
            backup,
            finance_path=target,
            checkpoint_path=tmp_path / "restored-checkpoints.db",
        )

    assert target.read_bytes() == b"keep me"


def test_backup_checksum_detects_corruption(monkeypatch, tmp_path):
    _configure_sqlite(monkeypatch, tmp_path)
    backup = create_backup(tmp_path / "backups")
    artifact = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))[
        "artifacts"
    ][0]
    with (backup / artifact["filename"]).open("ab") as stream:
        stream.write(b"corruption")

    with pytest.raises(BackupError, match="size mismatch"):
        verify_backup(backup)


def test_backup_rejects_unsafe_manifest_path(monkeypatch, tmp_path):
    _configure_sqlite(monkeypatch, tmp_path)
    backup = create_backup(tmp_path / "backups")
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["filename"] = "../finance.db"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BackupError, match="unsafe artifact path"):
        verify_backup(backup)


POSTGRES_BACKUP_AVAILABLE = bool(
    os.getenv("TEST_POSTGRES_URL")
    and shutil.which("pg_dump")
    and shutil.which("pg_restore")
)


@pytest.mark.skipif(
    not POSTGRES_BACKUP_AVAILABLE,
    reason="TEST_POSTGRES_URL, pg_dump, and pg_restore are required.",
)
def test_postgres_backup_can_be_restored_to_an_empty_database(monkeypatch, tmp_path):
    source_url = os.environ["TEST_POSTGRES_URL"]
    target_name = f"finance_restore_{uuid4().hex}"
    connection_info = conninfo_to_dict(source_url)
    admin_url = make_conninfo(**{**connection_info, "dbname": "postgres"})
    target_url = make_conninfo(**{**connection_info, "dbname": target_name})
    monkeypatch.setenv("FINANCE_DATABASE_URL", source_url)
    monkeypatch.delenv("FINANCE_CHECKPOINT_URL", raising=False)
    monkeypatch.delenv("FINANCE_CHECKPOINT_PATH", raising=False)
    initialize_database()

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_name)))
    try:
        backup = create_backup(tmp_path / "backups")
        manifest = verify_backup(backup)
        assert manifest["artifacts"][0]["roles"] == ["finance", "checkpoints"]

        restore_backup(backup, finance_url=target_url, checkpoint_url=target_url)
        with psycopg.connect(target_url) as connection:
            migration_count = connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            assert migration_count == 7
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (target_name,),
            )
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(target_name)
                )
            )
