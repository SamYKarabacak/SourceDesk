import hashlib
import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from backend.backup import DATABASE_NAME, restore_backup
from backend.config import Settings
from backend.main import create_app
from tests.conftest import FakeOllama, upload


def test_workspace_backup_restores_documents_history_sources_and_vectors(client, tmp_path):
    document = upload(client, "Refunds are allowed for thirty days.").json()["document"]
    assert client.post("/api/index", json={}).status_code == 200
    saved = client.post("/api/ask", json={"query": "refund", "mode": "ai"}).json()
    original = client.get("/api/health").json()["storage"]
    backup = client.get("/api/workspace/backup")
    assert backup.status_code == 200
    assert backup.headers["content-type"] == "application/zip"
    path = tmp_path / "backup.zip"
    path.write_bytes(backup.content)
    destination = tmp_path / "restored"
    restore_backup(path, destination)
    config = Settings(data_dir=destination)
    model = FakeOllama(config)
    with TestClient(create_app(config, model)) as restored:
        assert restored.get("/api/health").json()["storage"] == original
        assert restored.get(f"/api/history/{saved['run_id']}").json() == saved
        assert (
            restored.get(saved["sources"][0]["url"]).json()["text"] == saved["sources"][0]["text"]
        )
        assert (
            restored.get(f"/api/documents/{document['id']}/download").text
            == "Refunds are allowed for thirty days."
        )
        assert restored.post("/api/search", json={"query": "refund"}).json()["sources"]
    assert model.embed_calls == model.generate_calls == 0


def test_empty_workspace_backup_can_be_restored(client, tmp_path):
    path = tmp_path / "empty.zip"
    path.write_bytes(client.get("/api/workspace/backup").content)
    destination = tmp_path / "empty"
    restore_backup(path, destination)
    assert (destination / DATABASE_NAME).is_file()
    assert (destination / "uploads").is_dir()


def test_restore_does_not_replace_existing_workspace(client, tmp_path):
    path = tmp_path / "backup.zip"
    path.write_bytes(client.get("/api/workspace/backup").content)
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "notes.txt"
    sentinel.write_text("Keep this file.")
    with pytest.raises(ValueError, match="empty data directory"):
        restore_backup(path, destination)
    assert sentinel.read_text() == "Keep this file."


def edited_backup(content, edit):
    with zipfile.ZipFile(BytesIO(content)) as source:
        files = {name: source.read(name) for name in source.namelist()}
    edit(files)
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


@pytest.mark.parametrize(
    "damage",
    [
        "path",
        "missing_document",
        "changed_document",
        "changed_database",
        "manifest",
        "foreign_database",
    ],
)
def test_damaged_or_unsafe_archives_leave_no_restored_data(client, tmp_path, damage):
    upload(client)
    content = client.get("/api/workspace/backup").content

    def corrupt(files):
        name = next(name for name in files if name.startswith("uploads/"))
        if damage == "path":
            files["../outside.txt"] = b"escape"
        elif damage == "missing_document":
            files.pop(name)
        elif damage == "changed_document":
            files[name] = b"Changed bytes"
        elif damage == "changed_database":
            files[DATABASE_NAME] = b"not the original database"
        elif damage == "manifest":
            files["manifest.json"] = b"[]"
        else:
            files[DATABASE_NAME] = b"not a database"
            manifest = json.loads(files["manifest.json"])
            manifest["database_sha256"] = hashlib.sha256(files[DATABASE_NAME]).hexdigest()
            files["manifest.json"] = json.dumps(manifest).encode()

    path = tmp_path / "broken.zip"
    path.write_bytes(edited_backup(content, corrupt))
    destination = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_backup(path, destination)
    assert not destination.exists()
    assert not (tmp_path / "outside.txt").exists()
    assert not list(tmp_path.glob(".sourcedesk-restore-*"))


def test_missing_original_makes_backup_fail_clearly(client, settings):
    doc = upload(client).json()["document"]
    (settings.upload_dir / f"{doc['id']}.txt").unlink()
    response = client.get("/api/workspace/backup")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "backup_file_missing"
