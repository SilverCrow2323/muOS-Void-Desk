"""Integration tests for the legacy XFCE APT shell installer."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "vd_apt_install.sh"
MOUNT_HELPER = ROOT / "bin" / "vd_mount_common.sh"


def make_executable(path, body):
    path.write_text(body)
    path.chmod(0o755)
    return path


def make_harness(tmp_path, *, chroot_rc=0, cleanup_rc=0,
                 mount_fail_at=0, existing_root=False):
    app = tmp_path / "Void Desk"
    data = app / "data"
    bindir = app / "bin"
    fakebin = tmp_path / "fakebin"
    mountpoint = data / "xfce_mnt"
    (mountpoint / "etc").mkdir(parents=True)
    bindir.mkdir(parents=True)
    fakebin.mkdir()

    (data / ".xfce_ready").write_text("ready")
    (data / "xfce.img").write_bytes(b"fake ext4 image")
    (bindir / "vd_apt_install.sh").write_bytes(SCRIPT.read_bytes())
    (bindir / "vd_mount_common.sh").write_bytes(MOUNT_HELPER.read_bytes())

    mount_probe = make_executable(
        fakebin / "python3",
        """#!/bin/sh
printf '%s\\n' "$2" >> "$VD_PY_CALL_LOG"
case "$2" in
    *umount_tree*) exit "$VD_CLEANUP_RC" ;;
    *cleanup_stale*) exit "${VD_STALE_CLEANUP_RC:-0}" ;;
    *) exit "$VD_MOUNT_PROBE_RC" ;;
esac
""",
    )
    make_executable(
        fakebin / "mount",
        """#!/bin/sh
count=0
if [ -f "$VD_MOUNT_COUNT_FILE" ]; then
    read count < "$VD_MOUNT_COUNT_FILE"
fi
count=$((count + 1))
printf '%s\\n' "$count" > "$VD_MOUNT_COUNT_FILE"
if [ "$VD_MOUNT_FAIL_AT" -ne 0 ] &&
   [ "$count" -eq "$VD_MOUNT_FAIL_AT" ]; then
    echo "simulated mount failure" >&2
    exit 1
fi
exit 0
""",
    )
    make_executable(
        fakebin / "chroot",
        """#!/bin/sh
printf '%s\\n' "$*" >> "$VD_CHROOT_CALL_LOG"
echo "APT-STREAM-OUTPUT"
exit "$VD_CHROOT_RC"
""",
    )

    env = os.environ.copy()
    env.update({
        "PATH": str(fakebin) + os.pathsep + "/usr/bin:/bin",
        "APP_DIR": str(app),
        "PY3": str(mount_probe),
        "VD_MOUNT_PROBE_RC": "0" if existing_root else "1",
        "VD_CLEANUP_RC": str(cleanup_rc),
        "VD_STALE_CLEANUP_RC": "0",
        "VD_CHROOT_RC": str(chroot_rc),
        "VD_MOUNT_FAIL_AT": str(mount_fail_at),
        "VD_MOUNT_COUNT_FILE": str(tmp_path / "mount-count"),
        "VD_PY_CALL_LOG": str(tmp_path / "python-calls.log"),
        "VD_CHROOT_CALL_LOG": str(tmp_path / "chroot-calls.log"),
    })
    return app, data, mountpoint, env


def run_installer(tmp_path, **kwargs):
    app, data, mountpoint, env = make_harness(tmp_path, **kwargs)
    result = subprocess.run(
        [str(app / "bin" / "vd_apt_install.sh"), "htop"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, data, mountpoint, env


def test_apt_install_returns_apt_failure_instead_of_tee_status(tmp_path):
    result, data, _mountpoint, _env = run_installer(tmp_path, chroot_rc=42)

    assert result.returncode == 42
    assert "APT-STREAM-OUTPUT" in result.stdout
    assert "APT-STREAM-OUTPUT" in (data / "apt_install.log").read_text()


def test_apt_install_fails_when_owned_image_cleanup_fails(tmp_path):
    result, data, _mountpoint, _env = run_installer(
        tmp_path, chroot_rc=0, cleanup_rc=1
    )

    assert result.returncode == 1
    assert "cleanup failed" in result.stderr.lower()
    assert "exit: 1" in (data / "apt_install.log").read_text()


def test_apt_install_preserves_apt_failure_if_cleanup_also_fails(tmp_path):
    result, _data, _mountpoint, _env = run_installer(
        tmp_path, chroot_rc=42, cleanup_rc=1
    )

    assert result.returncode == 42
    assert "cleanup failed" in result.stderr.lower()


def test_apt_install_cleans_owned_image_after_bind_setup_failure(tmp_path):
    result, _data, _mountpoint, env = run_installer(
        tmp_path, mount_fail_at=2
    )

    assert result.returncode == 1
    assert not Path(env["VD_CHROOT_CALL_LOG"]).exists()
    python_calls = Path(env["VD_PY_CALL_LOG"]).read_text()
    assert "umount_tree" in python_calls


def test_apt_install_leaves_preexisting_desktop_root_mounted(tmp_path):
    result, _data, mountpoint, env = run_installer(
        tmp_path, existing_root=True
    )

    assert result.returncode == 0
    python_calls = Path(env["VD_PY_CALL_LOG"]).read_text()
    assert "umount_tree" not in python_calls
    assert Path(env["VD_CHROOT_CALL_LOG"]).exists()



def test_apt_install_releases_stale_loop_after_root_mount_failure(tmp_path):
    result, _data, _mountpoint, env = run_installer(
        tmp_path, mount_fail_at=1
    )

    assert result.returncode == 1
    assert not Path(env["VD_CHROOT_CALL_LOG"]).exists()
    python_calls = Path(env["VD_PY_CALL_LOG"]).read_text()
    assert "cleanup_stale" in python_calls
