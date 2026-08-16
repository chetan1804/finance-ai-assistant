import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg

from src.agents.checkpoint import get_checkpoint_database, get_checkpoint_url
from src.database.db import get_data_directory, get_database_path, get_database_url


MANIFEST_VERSION = 1


class BackupError(RuntimeError):
    """Raised when a backup cannot be created, verified, or restored safely."""


def get_backup_directory():
    configured = os.getenv("FINANCE_BACKUP_DIR")
    return (
        Path(configured).expanduser()
        if configured
        else get_data_directory() / "backups"
    )


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command, tool_name, *, sensitive_values=()):
    if shutil.which(command[0]) is None:
        raise BackupError(f"{tool_name} is required but was not found on PATH.")
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "unknown error").strip()
        for value in sensitive_values:
            detail = detail.replace(value, "[REDACTED]")
        raise BackupError(f"{tool_name} failed: {detail}") from None


def _sqlite_backup(source_path, destination_path):
    source_path = Path(source_path)
    if not source_path.is_file():
        raise BackupError(f"SQLite database does not exist: {source_path}")
    with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
        with sqlite3.connect(destination_path) as destination:
            source.backup(destination)


def _postgres_backup(database_url, destination_path):
    _run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            f"--file={destination_path}",
            database_url,
        ],
        "pg_dump",
        sensitive_values=(database_url,),
    )


def _configured_sources():
    finance_url = get_database_url()
    checkpoint_url = get_checkpoint_url()
    sources = []
    if finance_url:
        sources.append(("postgresql", finance_url, "finance"))
    else:
        sources.append(("sqlite", str(get_database_path()), "finance"))
    if checkpoint_url:
        sources.append(("postgresql", checkpoint_url, "checkpoints"))
    else:
        checkpoint_path = get_checkpoint_database()
        if checkpoint_path.exists():
            sources.append(("sqlite", str(checkpoint_path), "checkpoints"))

    grouped = []
    for backend, location, role in sources:
        match = next(
            (
                source
                for source in grouped
                if source["backend"] == backend and source["location"] == location
            ),
            None,
        )
        if match:
            match["roles"].append(role)
        else:
            grouped.append({"backend": backend, "location": location, "roles": [role]})
    return grouped


def create_backup(output_directory=None):
    """Back up all configured persistent databases into a verified archive."""
    root = Path(output_directory) if output_directory else get_backup_directory()
    root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".backup-", dir=root))
    artifacts = []
    try:
        for source in _configured_sources():
            label = "-".join(source["roles"])
            extension = "sqlite3" if source["backend"] == "sqlite" else "dump"
            filename = f"{label}.{extension}"
            destination = temporary / filename
            if source["backend"] == "sqlite":
                _sqlite_backup(source["location"], destination)
            else:
                _postgres_backup(source["location"], destination)
            artifacts.append(
                {
                    "backend": source["backend"],
                    "roles": source["roles"],
                    "filename": filename,
                    "size_bytes": destination.stat().st_size,
                    "sha256": _sha256(destination),
                }
            )

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": artifacts,
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        verify_backup(temporary)
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = root / f"{name}-{uuid4().hex[:8]}"
        temporary.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _load_manifest(backup_directory):
    directory = Path(backup_directory).resolve()
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BackupError(f"Invalid backup manifest: {error}") from None
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise BackupError("Unsupported backup manifest version.")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BackupError("Backup manifest does not contain artifacts.")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise BackupError("Backup manifest contains an invalid artifact.")
        if artifact.get("backend") not in {"sqlite", "postgresql"}:
            raise BackupError("Backup manifest contains an unsupported backend.")
        roles = artifact.get("roles")
        if (
            not isinstance(roles, list)
            or not roles
            or not set(roles).issubset({"finance", "checkpoints"})
        ):
            raise BackupError("Backup manifest contains invalid storage roles.")
        if not isinstance(artifact.get("size_bytes"), int):
            raise BackupError("Backup manifest contains an invalid artifact size.")
        checksum = artifact.get("sha256")
        if not isinstance(checksum, str) or len(checksum) != 64:
            raise BackupError("Backup manifest contains an invalid checksum.")
    return directory, manifest


def _artifact_path(directory, filename):
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise BackupError("Backup manifest contains an unsafe artifact path.")
    path = (directory / filename).resolve()
    if path.parent != directory:
        raise BackupError("Backup artifact escapes its directory.")
    return path


def verify_backup(backup_directory):
    """Validate artifact checksums and database/archive integrity."""
    directory, manifest = _load_manifest(backup_directory)
    for artifact in manifest["artifacts"]:
        path = _artifact_path(directory, artifact.get("filename"))
        if not path.is_file():
            raise BackupError(f"Backup artifact is missing: {path.name}")
        if path.stat().st_size != artifact.get("size_bytes"):
            raise BackupError(f"Backup artifact size mismatch: {path.name}")
        if _sha256(path) != artifact.get("sha256"):
            raise BackupError(f"Backup artifact checksum mismatch: {path.name}")
        backend = artifact.get("backend")
        if backend == "sqlite":
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
                result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise BackupError(f"SQLite integrity check failed: {path.name}")
        elif backend == "postgresql":
            _run(["pg_restore", "--list", str(path)], "pg_restore")
        else:
            raise BackupError(f"Unsupported backup backend: {backend}")
    return manifest


def _postgres_has_objects(database_url):
    query = """
        SELECT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
        )
    """
    with psycopg.connect(database_url) as connection:
        return connection.execute(query).fetchone()[0]


def _restore_sqlite(source, target, force):
    target = Path(target).expanduser()
    if target.exists() and not force:
        raise BackupError(f"Restore target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.restore-{uuid4().hex}")
    try:
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as backup:
            with sqlite3.connect(temporary) as destination:
                backup.backup(destination)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _restore_postgres(source, target_url, force):
    if _postgres_has_objects(target_url) and not force:
        raise BackupError(
            "PostgreSQL restore target is not empty; use --force to replace it."
        )
    command = [
        "pg_restore",
        "--exit-on-error",
        "--no-owner",
        "--no-privileges",
        f"--dbname={target_url}",
    ]
    if force:
        command.extend(["--clean", "--if-exists"])
    command.append(str(source))
    _run(command, "pg_restore", sensitive_values=(target_url,))


def restore_backup(
    backup_directory,
    *,
    finance_path=None,
    checkpoint_path=None,
    finance_url=None,
    checkpoint_url=None,
    force=False,
):
    """Verify and restore a backup to explicit or configured destinations."""
    manifest = verify_backup(backup_directory)
    directory = Path(backup_directory).resolve()
    targets = {
        "finance": finance_url or (get_database_url() if finance_path is None else None),
        "checkpoints": checkpoint_url,
    }
    paths = {
        "finance": Path(finance_path) if finance_path else get_database_path(),
        "checkpoints": (
            Path(checkpoint_path) if checkpoint_path else get_checkpoint_database()
        ),
    }
    if targets["checkpoints"] is None and checkpoint_path is None:
        targets["checkpoints"] = get_checkpoint_url()

    restored = set()
    for artifact in manifest["artifacts"]:
        source = _artifact_path(directory, artifact["filename"])
        backend = artifact["backend"]
        artifact_targets = [
            targets[role] if backend == "postgresql" else paths[role]
            for role in artifact["roles"]
        ]
        if len({str(target) for target in artifact_targets}) > 1:
            raise BackupError(
                "A shared database backup must be restored to one shared destination."
            )
        for role in artifact["roles"]:
            target = targets[role] if backend == "postgresql" else paths[role]
            key = (backend, str(target))
            if key in restored:
                continue
            if backend == "sqlite":
                _restore_sqlite(source, target, force)
            else:
                if not target:
                    raise BackupError(f"A PostgreSQL target URL is required for {role}.")
                _restore_postgres(source, target, force)
            restored.add(key)
    return sorted(role for artifact in manifest["artifacts"] for role in artifact["roles"])
