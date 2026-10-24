import socket
import subprocess
import sys

import pytest

import run


def test_launcher_help_does_not_install_or_start_anything(monkeypatch):
    monkeypatch.setattr(run, "prepare_environment", lambda: pytest.fail("Unexpected installation"))
    with pytest.raises(SystemExit) as result:
        run.main(["--help"])
    assert result.value.code == 0


def test_explicit_busy_port_is_rejected():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with pytest.raises(ValueError, match="port is in use"):
            run.available_port(server.getsockname()[1])


def test_default_port_skips_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        try:
            server.bind(("127.0.0.1", 8000))
            server.listen()
        except OSError:
            pass  # An existing server already occupies the default port.
        selected = run.available_port(None)
    assert 8001 <= selected <= 8010


@pytest.mark.parametrize("value", ["0", "-1", "65536", "abc"])
def test_invalid_ports_are_rejected(value):
    with pytest.raises(SystemExit) as result:
        run.main(["--port", value])
    assert result.value.code == 2


def test_failed_restore_does_not_install_dependencies(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "prepare_environment", lambda: pytest.fail("Unexpected installation"))
    assert (
        run.main(["--restore", str(tmp_path / "missing.zip"), "--data-dir", str(tmp_path / "new")])
        == 1
    )
    assert not (tmp_path / "new").exists()


def test_startup_failure_is_detected_without_waiting():
    child = subprocess.Popen([sys.executable, "-c", "raise SystemExit(1)"])
    child.wait()
    with pytest.raises(ValueError, match="stopped during startup"):
        run.wait_for_server(child, "http://127.0.0.1:1")
