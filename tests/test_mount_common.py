"""Tests for the shared shell mount-state probe."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "bin" / "vd_mount_common.sh"


def run_probe(tmp_path, *, result=0, path="/mnt/Void Desk/xfce_mnt",
              python_available=True):
    capture = tmp_path / "argv.txt"
    env = os.environ.copy()
    env.update({
        "APP_DIR": str(ROOT),
        "MOUNT_PATH": path,
        "VD_MOUNT_RESULT": str(result),
        "VD_ARG_CAPTURE": str(capture),
    })

    if python_available:
        fake_python = tmp_path / "python3"
        fake_python.write_text(
            """#!/bin/sh
printf '%s\\n' "$#" "$3" > "$VD_ARG_CAPTURE"
case "$VD_MOUNT_RESULT" in
    0) printf 'mounted\\n' ;;
    1) printf 'unmounted\\n' ;;
    *) exit "$VD_MOUNT_RESULT" ;;
esac
"""
        )
        fake_python.chmod(0o755)
        env["PY3"] = str(fake_python)
    else:
        env["PY3"] = ""
        env["PATH"] = "/nonexistent"

    script = (
        '. "$HELPER_PATH"\n'
        'vd_mount_present "$APP_DIR" "$MOUNT_PATH"\n'
    )
    env["HELPER_PATH"] = str(HELPER)
    return subprocess.run(
        ["/bin/sh", "-c", script],
        env=env, capture_output=True, text=True, check=False,
    ), capture


def test_shared_mount_probe_preserves_mounted_status(tmp_path):
    result, _capture = run_probe(tmp_path, result=0)
    assert result.returncode == 0


def test_shared_mount_probe_preserves_unmounted_status(tmp_path):
    result, _capture = run_probe(tmp_path, result=1)
    assert result.returncode == 1


def test_shared_mount_probe_returns_unknown_on_parser_error(tmp_path):
    result, _capture = run_probe(tmp_path, result=2)
    assert result.returncode == 2
    assert "refusing to change mount state" in result.stderr


def test_shared_mount_probe_returns_unknown_without_python(tmp_path):
    result, _capture = run_probe(tmp_path, python_available=False)
    assert result.returncode == 2
    assert "mount state is unknown" in result.stderr


def test_shared_mount_probe_passes_path_with_spaces_as_one_argument(tmp_path):
    mount_path = "/mnt/Void Desk/xfce mount"
    result, capture = run_probe(tmp_path, result=0, path=mount_path)

    assert result.returncode == 0
    assert capture.read_text().splitlines() == ["3", mount_path]


def test_shared_mount_probe_returns_unknown_when_imgmount_import_raises(tmp_path):
    app = tmp_path / "broken-app"
    desk = app / "desk"
    desk.mkdir(parents=True)
    (desk / "imgmount.py").write_text(
        "raise RuntimeError('simulated imgmount import failure')\n"
    )
    env = os.environ.copy()
    env.update({
        "APP_DIR": str(app),
        "MOUNT_PATH": "/mnt/Void Desk/xfce_mnt",
        "PY3": sys.executable,
        "PYTHONPATH": str(desk) + os.pathsep + env.get("PYTHONPATH", ""),
        "HELPER_PATH": str(HELPER),
    })
    script = (
        '. "$HELPER_PATH"\n'
        'vd_mount_present "$APP_DIR" "$MOUNT_PATH"\n'
    )

    result = subprocess.run(
        ["/bin/sh", "-c", script],
        env=env, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 2
    assert "state check failed" in result.stderr
    assert "simulated imgmount import failure" in result.stderr


def run_ensure(tmp_path, *, result, mount_rc=0):
    app = tmp_path / "ensure-app"
    app.mkdir()
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    python = fakebin / "python3"
    python.write_text(
        """#!/bin/sh
case "$VD_MOUNT_RESULT" in
    0) printf 'mounted\\n' ;;
    1) printf 'unmounted\\n' ;;
    *) exit "$VD_MOUNT_RESULT" ;;
esac
"""
    )
    python.chmod(0o755)
    mount = fakebin / "fake-mount"
    mount.write_text(
        """#!/bin/sh
echo called > "$VD_MOUNT_CALLED"
exit "$VD_MOUNT_RC"
"""
    )
    mount.chmod(0o755)
    called = tmp_path / "mount-called"
    env = os.environ.copy()
    env.update({
        "APP_DIR": str(app),
        "PY3": str(python),
        "VD_MOUNT_RESULT": str(result),
        "VD_MOUNT_RC": str(mount_rc),
        "VD_MOUNT_CALLED": str(called),
        "HELPER_PATH": str(HELPER),
    })
    script = (
        '. "$HELPER_PATH"\n'
        'vd_mount_ensure "$APP_DIR" "/mnt/Void Desk/xfce_mnt" fake-mount --target "/mnt/Void Desk/xfce_mnt"\n'
    )
    env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(
        ["/bin/sh", "-c", script],
        env=env, capture_output=True, text=True, check=False,
    )
    return completed, called


def test_mount_ensure_does_not_mount_when_already_mounted(tmp_path):
    result, called = run_ensure(tmp_path, result=0)
    assert result.returncode == 0
    assert not called.exists()


def test_mount_ensure_mounts_only_when_confirmed_unmounted(tmp_path):
    result, called = run_ensure(tmp_path, result=1)
    assert result.returncode == 0
    assert called.read_text().strip() == "called"


def test_mount_ensure_refuses_to_mount_when_state_is_unknown(tmp_path):
    result, called = run_ensure(tmp_path, result=2)
    assert result.returncode == 2
    assert not called.exists()


def test_mount_ensure_propagates_mount_command_failure(tmp_path):
    result, called = run_ensure(tmp_path, result=1, mount_rc=32)
    assert result.returncode == 32
    assert called.read_text().strip() == "called"
