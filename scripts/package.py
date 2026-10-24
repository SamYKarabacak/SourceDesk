"""Build a reproducible source distribution without local data or dependencies."""

import argparse
import hashlib
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import __version__  # noqa: E402

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "data",
    "releases",
    "test-results",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    ".codex",
}
EXCLUDE_FILES = {".env", ".coverage", ".DS_Store"}


def package(output: Path) -> Path:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = f"SourceDesk-v{__version__}"
    archive_path = output / f"{name}.zip"
    paths = []
    for directory, subdirs, files in os.walk(ROOT):
        subdirs[:] = sorted(
            d
            for d in subdirs
            if d not in EXCLUDE_DIRS
            and not (Path(directory) / d / "evidencelens.sqlite3").exists()
            and not (Path(directory) / d).is_symlink()
            and (Path(directory) / d).resolve() != output
        )
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.is_symlink() or filename in EXCLUDE_FILES:
                continue
            if filename.startswith(".env.") and filename != ".env.example":
                continue
            if path.suffix in {".pyc", ".log", ".sqlite3", ".db", ".zip"}:
                continue
            paths.append(path)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(paths):
            relative = path.relative_to(ROOT)
            info = zipfile.ZipInfo(f"{name}/{relative.as_posix()}", date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = path.read_bytes()
            if path.suffix == ".cmd":
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            archive.writestr(info, data)
    with archive_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive_path.with_suffix(".sha256").write_text(f"{digest}  {archive_path.name}\n")
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "releases")
    args = parser.parse_args()
    print(package(args.output))


if __name__ == "__main__":
    main()
