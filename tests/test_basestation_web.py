import importlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "assets" / "basestation"


def load_web_helpers():
    path = str(MODULE_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
    sys.modules.pop("basestation_web", None)
    return importlib.import_module("basestation_web")


def test_list_received_files_only_reports_regular_files(tmp_path):
    web = load_web_helpers()
    incoming = tmp_path / "incoming"
    device = incoming / "handheld-01"
    device.mkdir(parents=True)
    (device / "screenshot.png").write_bytes(b"PNG")
    (device / "notes.txt").write_text("hello", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (device / "escape.txt").symlink_to(outside)
    (incoming / "device-link").symlink_to(outside)

    files = web.list_received_files(incoming)

    names = {item["name"] for item in files}
    assert names == {"screenshot.png", "notes.txt"}
    assert all(item["device"] == "handheld-01" for item in files)
    assert all(item["size"] > 0 for item in files)


def test_resolve_received_file_rejects_traversal_and_symlinks(tmp_path):
    web = load_web_helpers()
    incoming = tmp_path / "incoming"
    device = incoming / "handheld-01"
    device.mkdir(parents=True)
    (device / "safe.txt").write_text("safe", encoding="utf-8")
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    (device / "outside.txt").symlink_to(outside)

    assert web.resolve_received_file(
        incoming, "handheld-01", "safe.txt").read_text(encoding="utf-8") == "safe"

    for name in ("../private.txt", "outside.txt", "subdir/file.txt", ""):
        try:
            web.resolve_received_file(incoming, "handheld-01", name)
        except (ValueError, FileNotFoundError):
            pass
        else:
            raise AssertionError("unsafe inbox path was accepted: {}".format(name))


def test_resolve_received_file_rejects_symlinked_device_directory(tmp_path):
    web = load_web_helpers()
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (incoming / "handheld-link").symlink_to(outside, target_is_directory=True)

    try:
        web.resolve_received_file(incoming, "handheld-link", "secret.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("symlinked device directory was accepted")


def test_load_service_registry_prefers_bundle_sidecar(tmp_path):
    web = load_web_helpers()
    companion = tmp_path / "basestation.py"
    companion.write_text("# test", encoding="utf-8")
    registry = {
        "schema": "spdw-service-registry",
        "version": 1,
        "services": [],
    }
    (tmp_path / "services.json").write_text(
        json.dumps(registry), encoding="utf-8")

    assert web.load_service_registry(companion) == registry


def test_load_service_registry_reports_missing_file(tmp_path):
    web = load_web_helpers()
    companion = tmp_path / "basestation.py"
    companion.write_text("# test", encoding="utf-8")

    try:
        web.load_service_registry(companion)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing service registry should be reported")
