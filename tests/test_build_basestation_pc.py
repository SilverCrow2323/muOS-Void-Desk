import hashlib
import json
import importlib.util
import os
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools" / "build_basestation_pc.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_basestation_pc_test", BUILDER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_source(root):
    root.mkdir(parents=True, exist_ok=True)
    for name in ("basestation.py", "basestation_core.py", "basestation_web.py",
                 "pc_hub.html", "requirements.txt", "README.md",
                 "run_basestation.sh", "LICENSE"):
        (root / name).write_text("# {}\\n".format(name), encoding="utf-8")


def test_pc_companion_archive_has_expected_root_and_executable_launcher(tmp_path):
    builder = load_builder()
    source = tmp_path / "source"
    make_source(source)
    output = tmp_path / "VOID-BaseStation-4.0.0.zip"

    archive, sidecar, checksum = builder.build_archive(source, output)

    assert archive.is_file()
    assert sidecar.is_file()
    assert sidecar.read_text(encoding="ascii").split()[0] == checksum
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        assert all(name.startswith("VOID-BaseStation-4.0.0/") for name in names)
        assert "VOID-BaseStation-4.0.0/basestation.py" in names
        assert "VOID-BaseStation-4.0.0/basestation_core.py" in names
        assert "VOID-BaseStation-4.0.0/pc_hub.html" in names
        assert "VOID-BaseStation-4.0.0/services.json" in names
        assert "VOID-BaseStation-4.0.0/basestation_web.py" in names
        registry = json.loads(package.read("VOID-BaseStation-4.0.0/services.json"))
        assert registry["schema"] == "spdw-service-registry"
        launcher = package.getinfo("VOID-BaseStation-4.0.0/run_basestation.sh")
        assert stat.S_IMODE(launcher.external_attr >> 16) == 0o755


def test_pc_companion_build_is_reproducible(tmp_path):
    builder = load_builder()
    source = tmp_path / "source"
    make_source(source)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    builder.build_archive(source, first)
    builder.build_archive(source, second)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()


def test_pc_companion_builder_rejects_incomplete_source(tmp_path):
    builder = load_builder()
    source = tmp_path / "source"
    source.mkdir()
    (source / "basestation.py").write_text("pass\\n", encoding="utf-8")

    try:
        builder.build_archive(source, tmp_path / "bad.zip")
    except RuntimeError as exc:
        assert "basestation_core.py" in str(exc)
    else:
        raise AssertionError("incomplete PC companion must not be packaged")
