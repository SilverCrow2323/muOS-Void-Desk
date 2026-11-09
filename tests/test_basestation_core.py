import hashlib
import importlib.util
import json
import os
import stat
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "assets" / "basestation" / "basestation_core.py"


def load_core():
    spec = importlib.util.spec_from_file_location("basestation_core_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSFTP:
    def __init__(self):
        self.entries = {
            "/remote/saves": [
                SimpleNamespace(filename="slot1.sav", st_mode=stat.S_IFREG | 0o600,
                                st_size=5, st_mtime=100),
                SimpleNamespace(filename="nested", st_mode=stat.S_IFDIR | 0o755,
                                st_size=0, st_mtime=100),
                SimpleNamespace(filename="escape", st_mode=stat.S_IFLNK | 0o777,
                                st_size=0, st_mtime=100),
            ],
            "/remote/saves/nested": [
                SimpleNamespace(filename="slot2.state", st_mode=stat.S_IFREG | 0o600,
                                st_size=6, st_mtime=101),
            ],
        }
        self.files = {
            "/remote/saves/slot1.sav": b"SAVE1",
            "/remote/saves/nested/slot2.state": b"STATE2",
        }

    def listdir_attr(self, path):
        return self.entries[path]

    def open(self, path, mode):
        assert mode == "rb"
        return BytesIO(self.files[path])


def test_auth_tokens_are_random_and_empty_tokens_never_authenticate():
    core = load_core()
    first = core.generate_auth_token()
    second = core.generate_auth_token()

    assert len(first) >= 40
    assert first != second
    assert core.token_matches(first, first)
    assert not core.token_matches(first, "")
    assert not core.token_matches("", first)
    assert not core.token_matches(first, first + "x")


def test_atomic_json_write_restricts_permissions(tmp_path):
    core = load_core()
    target = tmp_path / "private" / "daemon.json"

    core.atomic_write_json(target, {"token": "secret"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"token": "secret"}
    if os.name == "posix":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(target.parent.glob("*.tmp"))


def test_remote_backup_writes_manifest_checksums_and_skips_symlinks(tmp_path):
    core = load_core()
    archive_path = tmp_path / "backup.zip"
    progress = []

    manifest = core.create_remote_backup(
        FakeSFTP(),
        [{"name": "Saves", "path": "/remote/saves"}],
        archive_path,
        metadata={"device_name": "Test Console"},
        progress_callback=lambda name, done, total: progress.append((name, done, total)),
        chunk_size=2,
    )

    assert archive_path.is_file()
    assert len(manifest["files"]) == 2
    assert len(manifest["skipped"]) == 1
    assert manifest["skipped"][0]["reason"] == "symbolic link"
    assert progress[-1][1:] == (2, 2)
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert "VOID-BaseStation-Backup/files/Saves/slot1.sav" in names
        assert "VOID-BaseStation-Backup/files/Saves/nested/slot2.state" in names
        assert not any("escape" in name for name in names)
        saved = json.loads(archive.read(
            "VOID-BaseStation-Backup/manifest.json").decode("utf-8"))
        assert saved["metadata"]["device_name"] == "Test Console"
        records = {item["path"]: item for item in saved["files"]}
        assert records["slot1.sav"]["sha256"] == hashlib.sha256(b"SAVE1").hexdigest()
        assert records["nested/slot2.state"]["sha256"] == hashlib.sha256(b"STATE2").hexdigest()


def test_remote_backup_rejects_unsafe_roots_before_creating_archive(tmp_path):
    core = load_core()
    archive_path = tmp_path / "unsafe.zip"

    try:
        core.create_remote_backup(FakeSFTP(), [{"name": "Root", "path": "/"}],
                                  archive_path)
    except ValueError as exc:
        assert "filesystem root" in str(exc)
    else:
        raise AssertionError("filesystem root must never be archived")
    assert not archive_path.exists()


def test_remote_backup_removes_partial_archive_on_transfer_error(tmp_path):
    core = load_core()

    class BrokenSFTP(FakeSFTP):
        def open(self, path, mode):
            raise OSError("network interrupted")

    archive_path = tmp_path / "broken.zip"
    try:
        core.create_remote_backup(
            BrokenSFTP(), [{"name": "Saves", "path": "/remote/saves"}],
            archive_path)
    except OSError:
        pass
    else:
        raise AssertionError("transfer error must propagate")
    assert not archive_path.exists()
    assert not list(tmp_path.glob("*.partial"))

def test_listener_snapshot_prefers_ss_and_returns_raw_socket_inventory(monkeypatch):
    core = load_core()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout="tcp LISTEN 0 128 0.0.0.0:8765 0.0.0.0:* users:((\"python\",pid=10,fd=3))\\n",
            stderr="",
        )

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    result = core.collect_listener_snapshot()

    assert calls == [["ss", "-lntup"]]
    assert result["tool"] == "ss"
    assert "8765" in result["stdout"]


def test_listener_snapshot_falls_back_to_netstat(monkeypatch):
    core = load_core()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0] == "ss":
            raise FileNotFoundError("ss not installed")
        return SimpleNamespace(returncode=0, stdout="tcp 0 0 0.0.0.0:22 LISTEN\\n", stderr="")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    result = core.collect_listener_snapshot()

    assert calls == [["ss", "-lntup"], ["netstat", "-lntup"]]
    assert result["tool"] == "netstat"
    assert "0.0.0.0:22" in result["stdout"]


def test_listener_snapshot_reports_missing_tools_without_raising(monkeypatch):
    core = load_core()
    monkeypatch.setattr(
        core.subprocess, "run",
        lambda command, **kwargs: (_ for _ in ()).throw(FileNotFoundError(command[0])),
    )

    result = core.collect_listener_snapshot()

    assert result["tool"] is None
    assert "ss not installed" in result["stderr"]
    assert "netstat not installed" in result["stderr"]

