import hashlib
import importlib.util
import io
from pathlib import Path
import zipfile
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    script = ROOT / "tools" / "build_muxapp.py"
    spec = importlib.util.spec_from_file_location("voiddesk_muxapp_builder_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def elf64_aarch64(payload=b""):
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4], header[5], header[6] = 2, 1, 1
    header[18:20] = (183).to_bytes(2, "little")
    return bytes(header) + payload


def make_project(root: Path):
    for relative in (
        "mux_launch.sh", "voiddesk.py", "love/main.lua",
        "bin/launcher.sh", "service/voiddesk_service.py",
        "external/tools.json", "LICENSE", "README.md", "THIRD-PARTY.md",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test fixture\n", encoding="utf-8")

    lib = root / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    loader = lib / "love"
    loader.write_bytes(elf64_aarch64(b"liblove-11.5.so\0libluajit-5.1.so.2\0"))
    loader.chmod(0o755)
    (lib / "libluajit-5.1.so.2").write_bytes(elf64_aarch64())
    love_runtime = elf64_aarch64(b"\0" * (1024 * 1024))
    (lib / "liblove-11.5.so").write_bytes(love_runtime)

    upstream = root / "external" / "rt-tailscale-m"
    app = upstream / "app" / "RtTailscale"
    (app / "panel").mkdir(parents=True)
    for name in ("rt", "ts", "watchdog", "VERSION"):
        (app / name).write_text("fixture\n", encoding="utf-8")
    (app / "panel" / "server.py").write_text("fixture\n", encoding="utf-8")
    (app / "panel" / "index.html").write_text("fixture\n", encoding="utf-8")
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (upstream / "THIRD-PARTY.md").write_text("notices\n", encoding="utf-8")
    return love_runtime


def test_builder_emits_only_void_desk_root_and_bundles_rt_service(tmp_path, monkeypatch):
    builder = load_builder()
    monkeypatch.setattr(
        builder.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=builder.TAILSCALE_COMMIT, stderr=""
        ),
    )
    project = tmp_path / "project"
    project.mkdir()
    runtime_bytes = make_project(project)
    monkeypatch.setattr(builder, "LOVE_RUNTIME_BLOB_SHA", builder.git_blob_sha(runtime_bytes))
    (project / ".env").write_text("API_KEY=must-not-ship\n", encoding="utf-8")
    (project / "data").mkdir()
    (project / "data" / "user-config.json").write_text(
        '{"private": true}', encoding="utf-8"
    )
    output = tmp_path / "dist" / "Void-Desk.muxapp"

    result = builder.build_archive(project, output)

    assert result == output
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    sidecar = output.with_suffix(output.suffix + ".sha256")
    assert sidecar.read_text(encoding="ascii").startswith(expected_hash + "  ")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        tailscale_config = archive.read(
            "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf"
        ).decode("utf-8")
        packaged_runtime = archive.read("Void-Desk/lib/liblove-11.5.so")
        loader_mode = (archive.getinfo("Void-Desk/lib/love").external_attr >> 16) & 0o777
    assert names
    assert all(name.startswith("Void-Desk/") for name in names)
    assert "Void-Desk/mux_launch.sh" in names
    assert "Void-Desk/love/main.lua" in names
    assert packaged_runtime == runtime_bytes
    assert loader_mode & 0o111
    assert "Void-Desk/lib/libluajit-5.1.so.2" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf" in names
    assert "PANEL=0" in tailscale_config
    assert "PANEL_BIND=127.0.0.1" in tailscale_config
    assert not any(name.startswith("Void-Desk/tests/") for name in names)
    assert "Void-Desk/.env" not in names
    assert "Void-Desk/data/user-config.json" not in names


def test_builder_fails_if_pinned_submodule_is_not_initialized(tmp_path):
    builder = load_builder()
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / "external" / "rt-tailscale-m" / "app" / "RtTailscale" / "rt").unlink()

    try:
        builder.build_archive(project, tmp_path / "bad.muxapp")
    except RuntimeError as exc:
        assert "git submodule update --init --recursive" in str(exc)
    else:
        raise AssertionError("builder must refuse a package without Rt:Tailscale-M")


def test_builder_fetches_pinned_runtime_when_missing(tmp_path, monkeypatch):
    builder = load_builder()
    package_root = tmp_path / "package" / "Void-Desk"
    lib = package_root / "lib"
    lib.mkdir(parents=True)
    loader = lib / "love"
    loader.write_bytes(elf64_aarch64(b"liblove-11.5.so\0libluajit-5.1.so.2\0"))
    loader.chmod(0o755)
    (lib / "libluajit-5.1.so.2").write_bytes(elf64_aarch64())

    payload = elf64_aarch64(b"\0" * (1024 * 1024))
    monkeypatch.setattr(builder, "LOVE_RUNTIME_BLOB_SHA", builder.git_blob_sha(payload))
    monkeypatch.setattr(
        builder, "LOVE_RUNTIME_SOURCE_URL", "https://example.invalid/liblove-11.5.so"
    )
    monkeypatch.setattr(
        builder.urllib.request, "urlopen",
        lambda *args, **kwargs: io.BytesIO(payload),
    )

    builder._ensure_love_runtime(package_root)
    downloaded = lib / "liblove-11.5.so"
    assert downloaded.read_bytes() == payload
    assert downloaded.stat().st_mode & 0o111


def test_builder_rejects_unpinned_love_runtime(tmp_path, monkeypatch):
    builder = load_builder()
    package_root = tmp_path / "package" / "Void-Desk"
    lib = package_root / "lib"
    lib.mkdir(parents=True)
    loader = lib / "love"
    loader.write_bytes(elf64_aarch64(b"liblove-11.5.so\0libluajit-5.1.so.2\0"))
    loader.chmod(0o755)
    (lib / "libluajit-5.1.so.2").write_bytes(elf64_aarch64())
    (lib / "liblove-11.5.so").write_bytes(elf64_aarch64(b"wrong binary"))
    monkeypatch.setattr(builder, "LOVE_RUNTIME_BLOB_SHA", "0" * 40)

    try:
        builder._ensure_love_runtime(package_root)
    except RuntimeError as exc:
        assert "not the pinned H700 LÖVE 11.5 build" in str(exc)
    else:
        raise AssertionError("builder must refuse an unpinned LÖVE runtime")
