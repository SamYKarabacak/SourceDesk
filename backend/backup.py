"""Portable workspace snapshots. Restore only into a new, empty directory."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from backend import APP_ID, __version__
from backend.errors import AppError

if TYPE_CHECKING:
    from backend.storage import Store

MAX_BACKUP_BYTES = 1024 * 1024 * 1024
DATABASE_NAME = "evidencelens.sqlite3"
UPLOAD_NAME = re.compile(r"^uploads/[a-f0-9]{32}\.(pdf|txt|md)$")


def create_backup(store: "Store") -> Path:
    """Freeze metadata and files under the same writer lock, including WAL data."""
    handle, name = tempfile.mkstemp(
        prefix=f"SourceDesk-backup-{datetime.now(UTC):%Y-%m-%d}-", suffix=".zip"
    )
    os.close(handle)
    archive_path = Path(name)
    try:
        with store.lock, tempfile.TemporaryDirectory(prefix="sourcedesk-snapshot-") as staging:
            snapshot = Path(staging) / DATABASE_NAME
            with closing(store.connect()) as source, closing(sqlite3.connect(snapshot)) as dest:
                source.backup(dest)
                documents = dest.execute("SELECT id, kind, sha256 FROM documents").fetchall()
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, DATABASE_NAME)
                for doc_id, kind, digest in documents:
                    original = store.settings.upload_dir / f"{doc_id}.{kind}"
                    if not original.is_file():
                        raise AppError(
                            "backup_file_missing",
                            "An original file is missing. Check your workspace folder before backing up.",
                            409,
                        )
                    with original.open("rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                            raise AppError(
                                "backup_file_damaged",
                                "An original file has changed on disk. Check your workspace folder before backing up.",
                                409,
                            )
                    archive.write(original, f"uploads/{doc_id}.{kind}")
                with snapshot.open("rb") as stream:
                    database_digest = hashlib.file_digest(stream, "sha256").hexdigest()
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "application": APP_ID,
                            "version": __version__,
                            "format": 1,
                            "created_at": datetime.now(UTC).isoformat(),
                            "database_sha256": database_digest,
                            "documents": len(documents),
                        },
                        indent=2,
                    ),
                )
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise


def restore_backup(archive_path: Path, destination: Path) -> None:
    """Validate in a sibling staging directory, then move the completed workspace."""
    destination = destination.expanduser().resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Restore needs an empty data directory. Use --data-dir with a new folder.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sourcedesk-restore-", dir=destination.parent) as name:
        staging = Path(name)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                entries = archive.infolist()
                names = [item.filename for item in entries]
                if len(names) != len(set(names)) or len(names) > 10000:
                    raise ValueError("The backup contains duplicate files or too many entries.")
                if sum(item.file_size for item in entries) > MAX_BACKUP_BYTES:
                    raise ValueError("The uncompressed backup exceeds the 1 GB restore limit.")
                expected = {"manifest.json", DATABASE_NAME}
                if not expected.issubset(names) or any(
                    item not in expected and not UPLOAD_NAME.fullmatch(item) for item in names
                ):
                    raise ValueError("The backup contains unexpected files.")
                if archive.getinfo("manifest.json").file_size > 65536:
                    raise ValueError("The backup manifest is too large.")
                manifest = json.loads(archive.read("manifest.json"))
                if (
                    not isinstance(manifest, dict)
                    or manifest.get("application") != APP_ID
                    or manifest.get("format") != 1
                ):
                    raise ValueError("This is not a supported SourceDesk backup.")
                for item in names:
                    if item == "manifest.json":
                        continue
                    target = staging / item
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                database = staging / DATABASE_NAME
                with database.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != manifest.get(
                        "database_sha256"
                    ):
                        raise ValueError("The backup database checksum does not match.")
                with closing(
                    sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
                ) as conn:
                    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise ValueError("The backup database is damaged.")
                    if conn.execute("PRAGMA user_version").fetchone()[0] not in {1, 2}:
                        raise ValueError("The backup requires a different application version.")
                    if conn.execute("PRAGMA foreign_key_check").fetchone():
                        raise ValueError("The backup contains broken document references.")
                    docs = conn.execute("SELECT id, kind, sha256 FROM documents").fetchall()
                if manifest.get("documents") != len(docs):
                    raise ValueError("The backup document count does not match.")
                for doc_id, kind, digest in docs:
                    filename = f"uploads/{doc_id}.{kind}"
                    if not UPLOAD_NAME.fullmatch(filename) or filename not in names:
                        raise ValueError("A document is missing from this backup.")
                    with (staging / filename).open("rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                            raise ValueError("A document checksum does not match.")
                if set(names) != expected | {
                    f"uploads/{doc_id}.{kind}" for doc_id, kind, _ in docs
                }:
                    raise ValueError("The backup contains unreferenced files.")
            (staging / "uploads").mkdir(exist_ok=True)
            # Recheck after validation in case another process started using this path.
            if destination.exists():
                destination.rmdir()
            staging.rename(destination)
        except (
            OSError,
            zipfile.BadZipFile,
            RuntimeError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
            sqlite3.DatabaseError,
        ) as exc:
            raise ValueError(f"Could not restore this backup: {exc}") from exc
