import hashlib
import zipfile

from scripts import package as distribution


def test_package_is_reproducible_and_excludes_workspaces_and_secrets(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    for name in [
        "README.md",
        "run.py",
        "Start-SourceDesk.cmd",
        ".env.example",
        ".env",
        ".env.personal",
        "data/private.txt",
        "custom-workspace/evidencelens.sqlite3",
        "custom-workspace/uploads/private.txt",
        ".venv/token.txt",
        "node_modules/token.txt",
    ]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("line one\nline two\n")
    monkeypatch.setattr(distribution, "ROOT", source)
    first = distribution.package(tmp_path / "first")
    second = distribution.package(tmp_path / "second")
    assert (
        hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    )
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        names = {name.split("/", 1)[1] for name in archive.namelist()}
        assert names == {"README.md", "run.py", "Start-SourceDesk.cmd", ".env.example"}
        launcher = next(name for name in archive.namelist() if name.endswith(".cmd"))
        assert archive.read(launcher) == b"line one\r\nline two\r\n"
