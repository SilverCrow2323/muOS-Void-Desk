import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    script = ROOT / "tools" / "validate_muxapp.py"
    spec = importlib.util.spec_from_file_location("validate_muxapp", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_archive(path: Path, members: dict[str, bytes]):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


def valid_members():
    return {
        "Void-Desk/mux_launch.sh": b"#!/bin/sh\n",
        "Void-Desk/voiddesk.py": b"print('VoidDesk')\n",
        "Void-Desk/love/main.lua": b"function love.load() end\n",
    }


def test_muxapp_accepts_single_void_desk_root(tmp_path):
    archive = tmp_path / "valid.muxapp"
    make_archive(archive, valid_members())
    assert load_validator().validate_archive(archive) == []


def test_muxapp_rejects_extra_top_level_directory(tmp_path):
    archive = tmp_path / "invalid.muxapp"
    members = valid_members()
    members["application/README.txt"] = b"wrong root"
    errors = load_validator().validate_archive(
        make_archive(archive, members) or archive
    )
    assert any("unexpected top-level entry: application" in e for e in errors)


def test_muxapp_rejects_missing_launcher_and_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.muxapp"
    members = valid_members()
    del members["Void-Desk/mux_launch.sh"]
    members["Void-Desk/../outside.txt"] = b"unsafe"
    make_archive(archive, members)
    errors = load_validator().validate_archive(archive)
    assert any("unsafe archive member path" in e for e in errors)
    assert any("required file missing: Void-Desk/mux_launch.sh" in e for e in errors)
