"""Runtime regression tests for the XFCE APT image manager."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_manager():
    script = ROOT / "bin" / "vd_apt_manage.py"
    spec = importlib.util.spec_from_file_location("vd_apt_manager_runtime_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_manager(tmp_path, monkeypatch, *, apt_returncode=0,
                    mount_failure_at=None, cleanup_ok=True):
    manager = load_manager()
    data = tmp_path / "data"
    data.mkdir()
    image = data / "xfce.img"
    image.write_bytes(b"fake image")
    (data / ".xfce_ready").write_text("ready")
    mountpoint = data / "xfce_mnt"
    monkeypatch.setattr(manager, "APP", tmp_path)
    monkeypatch.setattr(manager, "DATA", data)
    monkeypatch.setattr(manager, "IMAGE", image)
    monkeypatch.setattr(manager, "MOUNT", mountpoint)
    monkeypatch.setattr(manager, "LOCK", data / ".apt-manager.lock")

    monkeypatch.setattr(manager.imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(manager.imgmount, "mount_img", lambda *_args: (True, ""))
    cleanup_calls = []
    monkeypatch.setattr(
        manager.imgmount, "umount_tree",
        lambda *args: (cleanup_calls.append(args) or cleanup_ok),
    )

    run_calls = []

    class Result:
        def __init__(self, code=0, stdout="", stderr=""):
            self.returncode = code
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):
        run_calls.append(command)
        if command[0] == "chroot":
            return Result(apt_returncode)
        if command[0] == "mount" and mount_failure_at == len(run_calls):
            return Result(1, stderr="simulated bind mount failure")
        return Result()

    monkeypatch.setattr(manager.subprocess, "run", fake_run)
    return manager, run_calls, cleanup_calls


def test_apt_manager_fails_when_cleanup_leaves_image_mounted(
        tmp_path, monkeypatch, capsys):
    manager, calls, cleanup_calls = prepare_manager(
        tmp_path, monkeypatch, cleanup_ok=False
    )

    assert manager.main(["clean"]) == 1
    assert cleanup_calls
    assert any(command[0] == "chroot" for command in calls)
    assert "cannot safely finish APT operation" in capsys.readouterr().err


def test_apt_manager_preserves_apt_error_when_cleanup_also_fails(
        tmp_path, monkeypatch, capsys):
    manager, calls, cleanup_calls = prepare_manager(
        tmp_path, monkeypatch, apt_returncode=100, cleanup_ok=False
    )

    assert manager.main(["clean"]) == 100
    assert cleanup_calls
    assert any(command[0] == "chroot" for command in calls)
    assert "cannot safely finish APT operation" in capsys.readouterr().err


def test_apt_manager_cleans_partial_mounts_after_bind_failure(
        tmp_path, monkeypatch, capsys):
    manager, calls, cleanup_calls = prepare_manager(
        tmp_path, monkeypatch, mount_failure_at=2, cleanup_ok=True
    )

    assert manager.main(["clean"]) == 1
    assert cleanup_calls
    assert not any(command[0] == "chroot" for command in calls)
    assert "simulated bind mount failure" in capsys.readouterr().err


def test_apt_manager_returns_success_only_after_verified_cleanup(
        tmp_path, monkeypatch):
    manager, calls, cleanup_calls = prepare_manager(
        tmp_path, monkeypatch, cleanup_ok=True
    )

    assert manager.main(["clean"]) == 0
    assert cleanup_calls
    assert any(command[0] == "chroot" for command in calls)
