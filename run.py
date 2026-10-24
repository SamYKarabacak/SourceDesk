"""Set up SourceDesk's environment and start the local application."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parent


def port_number(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Use a port between 1 and 65535.")
    return number


def available_port(requested: int | None) -> int:
    for number in [requested] if requested else range(8000, 8011):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", number))
                return number
            except OSError:
                continue
    raise ValueError("The port is in use. Stop the other server or choose --port 8011.")


def prepare_environment() -> Path:
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Creating the local Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = ROOT / "requirements.txt"
    constraints = ROOT / "requirements-lock.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes() + constraints.read_bytes()).hexdigest()
    marker = environment / "sourcedesk-requirements.txt"
    expected = dict(
        line.strip().split("==", 1)
        for line in requirements.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    )
    # Check installed versions too, so interrupted or changed environments recover.
    ready = (
        subprocess.run(
            [
                str(python),
                "-c",
                "import fastapi, uvicorn, multipart, pypdf, httpx; "
                "import importlib.metadata as m, json, sys; "
                "sys.exit(0 if all(m.version(n) == v for n, v in json.loads(sys.argv[1]).items()) else 1)",
                json.dumps(expected),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )
    if not ready or not marker.is_file() or marker.read_text() != fingerprint:
        print(
            "Installing application dependencies. The first start needs internet access...",
            flush=True,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--only-binary=:all:",
                "-r",
                str(requirements),
                "-c",
                str(constraints),
            ],
            check=True,
        )
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        marker.write_text(fingerprint)
    return python


def wait_for_server(process: subprocess.Popen, url: str, timeout: float = 30) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError("The server stopped during startup. See the error above.")
        try:
            with opener.open(url + "/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.1)
    raise ValueError("The server did not become ready in time. See the terminal output above.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start SourceDesk on this computer.")
    parser.add_argument(
        "--port",
        type=port_number,
        help="Local port; defaults to the first free port from 8000 to 8010.",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Start without opening a browser tab."
    )
    parser.add_argument("--data-dir", type=Path, help="Folder for documents and saved research.")
    parser.add_argument(
        "--restore",
        type=Path,
        metavar="BACKUP.zip",
        help="Restore a backup into an empty --data-dir before starting.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Install dependencies and check the environment without starting.",
    )
    args = parser.parse_args(argv)
    if sys.version_info < (3, 12):  # noqa: UP036 -- Report unsupported launchers clearly.
        print("SourceDesk requires Python 3.12 or newer.", file=sys.stderr)
        return 1
    try:
        from backend import __version__

        if args.data_dir:
            os.environ["SOURCEDESK_DATA_DIR"] = str(args.data_dir.expanduser().resolve())
        from backend.config import Settings

        settings = Settings()
        if args.restore:
            from backend.backup import restore_backup

            restore_backup(args.restore.expanduser().resolve(), settings.data_dir)
            print(f"Workspace restored to {settings.data_dir}", flush=True)
        port = None if args.check else available_port(args.port)
        python = prepare_environment()
        if args.check:
            return subprocess.call([str(python), str(ROOT / "scripts" / "doctor.py")], cwd=ROOT)
        url = f"http://127.0.0.1:{port}"
        print(
            f"\nSourceDesk {__version__}\nWorkspace: {settings.data_dir}\nAddress: {url}\nKeep this window open. Press Ctrl+C to stop.\n",
            flush=True,
        )
        process = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
        )
        try:
            wait_for_server(process, url)
            if not args.no_browser:
                try:
                    webbrowser.open(url)
                except webbrowser.Error:
                    print(f"Open {url} in your browser.", flush=True)
            return process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    except KeyboardInterrupt:
        print("\nSourceDesk stopped.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"\nSourceDesk could not start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
