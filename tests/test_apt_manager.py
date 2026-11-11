import os
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
    script = tmp_path / "bin" / "vd_apt_manage.py"
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
    assert calls[0][0] == service.sys.executable
    assert calls[0][1].endswith("vd_apt_manage.py")
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
    script = tmp_path / "bin" / "vd_apt_manage.py"
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
    assert commands[0] == [service.sys.executable, str(script), "install", "htop", "ncdu"]


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



def load_manager_for_lock_tests():
    script = ROOT / "bin" / "vd_apt_manage.py"
    spec = importlib.util.spec_from_file_location("voiddesk_apt_lock_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_lock_manager(tmp_path, monkeypatch):
    manager = load_manager_for_lock_tests()
    data = tmp_path / "data"
    data.mkdir()
    image = data / "xfce.img"
    image.write_bytes(b"test image")
    (data / ".xfce_ready").write_text("ready")
    monkeypatch.setattr(manager, "DATA", data)
    monkeypatch.setattr(manager, "IMAGE", image)
    monkeypatch.setattr(manager, "MOUNT", data / "xfce_mnt")
    monkeypatch.setattr(manager, "LOCK", data / ".apt-manager.lock")
    mount_calls = []
    monkeypatch.setattr(manager.imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(
        manager.imgmount, "mount_img",
        lambda *_args: (mount_calls.append("mount") or True, "")
    )
    monkeypatch.setattr(manager.imgmount, "umount_tree", lambda *_args: True)
    return manager, data, mount_calls


def test_apt_manager_refuses_symlink_lock_without_touching_target(
        tmp_path, monkeypatch):
    manager, _data, mount_calls = prepare_lock_manager(tmp_path, monkeypatch)
    victim = tmp_path / "victim.txt"
    victim.write_text("must remain unchanged")
    manager.LOCK.symlink_to(victim)

    assert manager.main(["clean"]) == 1
    assert victim.read_text() == "must remain unchanged"
    assert mount_calls == []


def test_apt_manager_rejects_symlinked_data_directory(tmp_path, monkeypatch):
    manager, data, mount_calls = prepare_lock_manager(tmp_path, monkeypatch)
    linked_data = tmp_path / "data-link"
    linked_data.symlink_to(data, target_is_directory=True)
    monkeypatch.setattr(manager, "DATA", linked_data)
    monkeypatch.setattr(manager, "LOCK", linked_data / ".apt-manager.lock")

    assert manager.main(["clean"]) == 1
    assert mount_calls == []


def test_apt_manager_busy_lock_is_not_truncated(tmp_path, monkeypatch):
    import fcntl

    manager, _data, mount_calls = prepare_lock_manager(tmp_path, monkeypatch)
    manager.LOCK.write_text("existing lock metadata")
    with manager.LOCK.open("r+") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            assert manager.main(["clean"]) == 75
        finally:
            fcntl.flock(held.fileno(), fcntl.LOCK_UN)

    assert manager.LOCK.read_text() == "existing lock metadata"
    assert mount_calls == []


def test_apt_manager_lock_has_private_permissions(tmp_path, monkeypatch):
    manager, _data, _mount_calls = prepare_lock_manager(tmp_path, monkeypatch)
    lock = manager.open_lock_file()
    lock.close()

    assert manager.LOCK.stat().st_mode & 0o777 == 0o600


def test_apt_manager_rejects_hardlinked_lock(tmp_path, monkeypatch):
    manager, _data, mount_calls = prepare_lock_manager(tmp_path, monkeypatch)
    manager.LOCK.write_text("shared")
    second_name = tmp_path / "other-link"
    os.link(manager.LOCK, second_name)

    assert manager.main(["clean"]) == 1
    assert second_name.read_text() == "shared"
    assert mount_calls == []
