"""Tests for the shared shell mount-state probe."""

import os
import shutil
import subprocess
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
            "#!/bin/sh\n"
            "printf '%s\\n' \"$#\" \"$3\" > \"$VD_ARG_CAPTURE\"\n"
            "case \"$VD_MOUNT_RESULT\" in\n"
            "    0) printf 'mounted\\n' ;;\n"
            "    1) printf 'unmounted\\n' ;;\n"
            "    *) exit \"$VD_MOUNT_RESULT\" ;;\n"
            "esac\n"
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


def test_shared_mount_probe_fails_closed_when_imgmount_import_fails(tmp_path):
    app_dir = tmp_path / "app"
    desk = app_dir / "desk"
    desk.mkdir(parents=True)
    (desk / "imgmount.py").write_text(
        'raise RuntimeError("simulated parser import failure")\n',
        encoding="utf-8",
    )
    python = shutil.which("python3")
    if not python:
        return

    env = os.environ.copy()
    env.update({
        "APP_DIR": str(app_dir),
        "PY3": python,
        "HELPER_PATH": str(HELPER),
        "MOUNT_PATH": "/mnt/xfce_mnt",
    })
    result = subprocess.run(
        [
            "/bin/sh", "-c",
            '. "$HELPER_PATH"\nvd_mount_present "$APP_DIR" "$MOUNT_PATH"\n',
        ],
        env=env, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0
    assert "refusing to stack another mount" in result.stderr
