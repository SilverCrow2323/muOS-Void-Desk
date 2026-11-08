import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_apt_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    pid = 987654322

    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15


def test_apt_catalog_search_runs_only_chroot_manager(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    script = tmp_path / "bin" / "vd_apt_manage.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n")
    calls = []

    class Result:
        returncode = 0
        stdout = "htop - interactive process viewer\ncurl - transfer tool\n"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    result = service.h_apt_catalog({"mode": "search", "query": "htop"})
    assert result["ok"] is True
    assert result["packages"] == [
        {"name": "htop", "description": "interactive process viewer"},
        {"name": "curl", "description": "transfer tool"},
    ]
    assert calls[0][0] == "sh"
    assert calls[0][1].endswith("vd_apt_manage.sh")
    assert calls[0][2:] == ["catalog", "search", "htop"]


def test_apt_catalog_rejects_unsafe_search_before_execution(monkeypatch):
    service = load_service()
    monkeypatch.setattr(service.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("must not execute")
                        ))
    result = service.h_apt_catalog({"mode": "search", "query": "htop; reboot"})
    assert result["ok"] is False
    assert "unsupported characters" in result["error"]


def test_apt_job_accepts_valid_package_list(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    monkeypatch.setattr(service, "_JOBS", {})
    monkeypatch.setattr(service, "_JOB_SEQ", 0)
    script = tmp_path / "bin" / "vd_apt_manage.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n")
    process = FakeProcess()
    commands = []
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda command, **kwargs: (commands.append(command) or process))

    result = service.h_job_start({
        "apt_action": "install", "packages": ["htop", "ncdu"],
        "name": "Install selected packages", "hub": "forge",
    })
    assert result["ok"] is True
    assert commands[0] == ["sh", str(script), "install", "htop", "ncdu"]


def test_apt_job_rejects_shell_metacharacters_and_unknown_actions(monkeypatch):
    service = load_service()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("must not execute")
                        ))
    bad_package = service.h_job_start({
        "apt_action": "install", "packages": ["htop;reboot"]
    })
    bad_action = service.h_job_start({"apt_action": "dist-upgrade"})
    assert bad_package["ok"] is False
    assert bad_action["ok"] is False
