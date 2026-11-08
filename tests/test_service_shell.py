import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_shell_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeShellProcess:
    pid = 987654322

    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15


def test_shell_pty_start_poll_send_and_stop(monkeypatch, tmp_path):
    service = load_service()
    process = FakeShellProcess()
    written = []
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "_SHELL_MASTER", None)
    monkeypatch.setattr(service, "_SHELL_PROC", None)
    monkeypatch.setattr(service.pty, "openpty", lambda: (11, 12))
    monkeypatch.setattr(service.fcntl, "ioctl", lambda *args: 0)
    monkeypatch.setattr(service.fcntl, "fcntl", lambda *args: 0)
    monkeypatch.setattr(service.os, "close", lambda _fd: None)
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process)
    monkeypatch.setattr(service.select, "select",
                        lambda *args: ([11], [], []))
    read_once = {"done": False}

    def fake_read(_fd, _size):
        if not read_once["done"]:
            read_once["done"] = True
            return b"hello\r\n"
        raise BlockingIOError()

    monkeypatch.setattr(service.os, "read", fake_read)
    monkeypatch.setattr(
        service.os, "write",
        lambda _fd, payload: written.append(payload) or len(payload),
    )
    monkeypatch.setattr(
        service.os, "killpg",
        lambda *_args: (_ for _ in ()).throw(ProcessLookupError()),
    )

    started = service.h_shell_start({})
    assert started["ok"] is True
    assert started["pid"] == process.pid

    polled = service.h_shell_poll({})
    assert polled == {"ok": True, "output": "hello\r\n", "running": True}

    sent = service.h_shell_send({"text": "echo hello\n"})
    assert sent["ok"] is True
    assert written == [b"echo hello\n"]

    stopped = service.h_shell_kill({})
    assert stopped == {"ok": True}
    assert process.terminated is True
    assert service._SHELL_MASTER is None
    assert service._SHELL_PROC is None


def test_shell_poll_and_send_require_running_session(monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "_SHELL_MASTER", None)
    monkeypatch.setattr(service, "_SHELL_PROC", None)
    assert service.h_shell_poll({})["ok"] is False
    assert service.h_shell_send({"text": "pwd"})["ok"] is False
