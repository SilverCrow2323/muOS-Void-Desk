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



def test_desktop_environment_operations_use_supervised_allowlisted_jobs(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    monkeypatch.setattr(service, "IS_DEVICE", True)
    monkeypatch.setattr(service, "_JOBS", {})
    monkeypatch.setattr(service, "_JOB_SEQ", 0)
    scripts = tmp_path / "bin"
    scripts.mkdir()
    (scripts / "xfce_bootstrap.py").write_text("print('bootstrap')\n")
    (scripts / "env_install.py").write_text("print('install')\n")
    (scripts / "desktop_env_maintenance.py").write_text("print('maintenance')\n")
    (tmp_path / "service").mkdir()
    process = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process)

    xfce = service.h_xfce_install({})
    assert xfce["ok"] is True
    assert xfce["job"]["name"] == "Install XFCE"
    assert xfce["job"]["status"] == "running"
    assert (tmp_path / "data" / ".xfce_install_running").read_text() == str(process.pid)
    assert xfce["job"]["progress"] == 0

    process2 = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process2)
    (tmp_path / "data" / ".xfce_ready").write_text("xfce ok\n")
    icewm = service.h_env_install({"id": "icewm"})
    assert icewm["ok"] is True
    assert icewm["job"]["name"] == "Install IceWM"
    assert icewm["job"]["animation"] == "install"

    process3 = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process3)
    (tmp_path / "data" / ".icewm_ready").write_text("icewm ok\n")
    removal = service.h_env_uninstall({"id": "icewm"})
    assert removal["ok"] is True
    assert removal["job"]["name"] == "Remove IceWM"
    assert "isolated" in removal["job"]["reason"].lower()

    process4 = FakeProcess()
    monkeypatch.setattr(service.subprocess, "Popen",
                        lambda *args, **kwargs: process4)
    update = service.h_env_update_check({"id": "xfce"})
    assert update["ok"] is True
    assert update["job"]["name"] == "Check updates for XFCE"
    assert update["job"]["animation"] == "verify"

    assert service.h_env_uninstall({"id": "../../etc"})["ok"] is False
    assert service.h_env_update_check({"id": "unknown"})["ok"] is False
