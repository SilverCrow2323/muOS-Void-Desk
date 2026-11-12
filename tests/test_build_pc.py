from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_pc", ROOT / "tools" / "build_pc.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_pc_bundle_excludes_device_state_and_secrets(tmp_path, monkeypatch):
    builder = load_builder()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "desk").mkdir()
    (repo / "data").mkdir()
    (repo / "tests").mkdir()
    (repo / "packaging" / "pc").mkdir(parents=True)
    (repo / "desk" / "main.py").write_text("print('Void Desk')\n")
    (repo / "voiddesk.py").write_text("print('launcher')\n")
    (repo / "data" / "desk_config.json").write_text(
        '{"termid_id":"private-device-id"}\n'
    )
    (repo / ".env").write_text("API_TOKEN=never-package\n")
    (repo / "tests" / "test_private.py").write_text("pass\n")
    (repo / "packaging" / "pc" / "launch.sh").write_text(
        "#!/bin/sh\nexec python3 voiddesk.py --py\n"
    )

    git(repo, "init", "-q")
    git(repo, "config", "user.email", "ci@example.invalid")
    git(repo, "config", "user.name", "CI")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")
    monkeypatch.setattr(builder, "ROOT", repo)

    output = tmp_path / "dist" / "Void-Desk-PC-test.tar.gz"
    builder.build_archive(output, "test")

    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
        assert "VoidDesk-PC/voiddesk.py" in names
        assert "VoidDesk-PC/desk/main.py" in names
        assert "VoidDesk-PC/PC-README.txt" in names
        pc_readme = archive.extractfile("VoidDesk-PC/PC-README.txt").read().decode("utf-8")
        assert "$HOME/VoidDesk-PC/" in pc_readme
        assert "VoidDesk-PC/launch-pc.sh" in names
        assert "VoidDesk-PC/data" in names
        assert "VoidDesk-PC/data/desk_config.json" not in names
        assert "VoidDesk-PC/.env" not in names
        assert "VoidDesk-PC/tests/test_private.py" not in names
        launch = archive.getmember("VoidDesk-PC/launch-pc.sh")
        assert launch.mode & 0o111

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    assert checksum.read_text(encoding="ascii").startswith(digest + "  ")


def test_pc_bundle_rejects_unsafe_version(tmp_path, monkeypatch):
    builder = load_builder()
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    try:
        builder.build_archive(tmp_path / "bad.tar.gz", "../escape")
    except ValueError as exc:
        assert "unsupported characters" in str(exc)
    else:
        raise AssertionError("unsafe version labels must be rejected")
