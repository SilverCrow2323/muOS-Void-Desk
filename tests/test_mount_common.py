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

    script = """\
. "$HELPER_PATH"
vd_mount_present "$APP_DIR" "$MOUNT_PATH"
"""
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


def test_shared_mount_probe_fails_closed_on_parser_error(tmp_path):
    result, _capture = run_probe(tmp_path, result=2)
    assert result.returncode == 0
    assert "refusing to stack another mount" in result.stderr


def test_shared_mount_probe_fails_closed_without_python(tmp_path):
    result, _capture = run_probe(tmp_path, python_available=False)
    assert result.returncode == 0
    assert "python3 unavailable" in result.stderr


def test_shared_mount_probe_passes_path_with_spaces_as_one_argument(tmp_path):
    mount_path = "/mnt/Void Desk/xfce mount"
    result, capture = run_probe(tmp_path, result=0, path=mount_path)

    assert result.returncode == 0
    assert capture.read_text().splitlines() == ["3", mount_path]


def test_shared_mount_probe_fails_closed_when_imgmount_import_raises(tmp_path):
    app = tmp_path / "broken-app"
    desk = app / "desk"
    desk.mkdir(parents=True)
    (desk / "imgmount.py").write_text(
        "raise RuntimeError('simulated imgmount import failure')"
    )
    env = os.environ.copy()
    env.update({
        "APP_DIR": str(app),
        "MOUNT_PATH": "/mnt/Void Desk/xfce_mnt",
        "PY3": sys.executable,
        "HELPER_PATH": str(HELPER),
    })
    script = """\
. "$HELPER_PATH"
vd_mount_present "$APP_DIR" "$MOUNT_PATH"
"""

    result = subprocess.run(
        ["/bin/sh", "-c", script],
        env=env, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0
    assert "state check failed" in result.stderr
    assert "simulated imgmount import failure" in result.stderr
