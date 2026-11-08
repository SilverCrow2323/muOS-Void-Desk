import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_jobs_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    pid = 987654321

    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15


def test_job_service_tracks_allowlisted_package_job(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    monkeypatch.setattr(service, "_JOBS", {})
    monkeypatch.setattr(service, "_JOB_SEQ", 0)
    installer = tmp_path / "bin" / "vd_apt_install.sh"
    installer.parent.mkdir()
    installer.write_text("#!/bin/sh\nexit 0\n")
    process = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process)

    started = service.h_job_start({
        "cmd": "sh bin/vd_apt_install.sh htop",
        "name": "apt: htop",
        "hub": "forge",
    })
    assert started["ok"] is True
    job_id = started["job"]["id"]
    assert started["job"]["status"] == "running"

    log_path = tmp_path / "data" / ("love_job_%s.log" % job_id)
    log_path.write_text("Installing htop\nDone\n")
    assert service.h_job_log({"job_id": job_id})["lines"] == [
        "Installing htop", "Done"
    ]
    assert service.h_job_list({})["jobs"][0]["status"] == "running"

    process.returncode = 0
    finished = service.h_job_list({})["jobs"][0]
    assert finished["status"] == "done"
    assert finished["progress"] == 100


def test_job_service_rejects_arbitrary_commands(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError("Popen must not run")
                        ))
    result = service.h_job_start({"cmd": "sh -c 'rm -rf /'"})
    assert result["ok"] is False
    assert "allowlisted" in result["error"]


def test_job_service_cancel_terminates_running_job(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    monkeypatch.setattr(service, "_JOBS", {})
    monkeypatch.setattr(service, "_JOB_SEQ", 0)
    installer = tmp_path / "bin" / "vd_apt_install.sh"
    installer.parent.mkdir()
    installer.write_text("#!/bin/sh\nexit 0\n")
    process = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process)
    started = service.h_job_start({"cmd": "sh bin/vd_apt_install.sh curl"})
    result = service.h_job_cancel({"job_id": started["job"]["id"]})
    assert result == {"ok": True, "status": "cancelled"}
    assert process.terminated is True
