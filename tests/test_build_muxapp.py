import hashlib
import importlib.util
import io
import tarfile
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


def tar_gz_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def add_runtime_archives(root: Path):
    base = root / "assets" / "runtime_archives"
    base.mkdir(parents=True, exist_ok=True)
    archives = {
        "pygame.tar.gz": {
            "pygame/__init__.py": b"from . import base\\n",
            "pygame/base.cpython-311-aarch64-linux-gnu.so": b"ELF fixture",
        },
        "pygame.libs.tar.gz": {
            "pygame.libs/libSDL2-test.so.0": b"ELF SDL fixture",
        },
        "pygame-2.6.1.data.tar.gz": {
            "pygame-2.6.1.data/headers/include/pgcompat.h": b"/* fixture */\\n",
        },
        "pygame-2.6.1.dist-info.tar.gz": {
            "pygame-2.6.1.dist-info/WHEEL": (
                b"Wheel-Version: 1.0\\n"
                b"Root-Is-Purelib: false\\n"
                b"Tag: cp311-cp311-manylinux_2_17_aarch64\\n"
                b"Tag: cp311-cp311-manylinux2014_aarch64\\n"
            ),
            "pygame-2.6.1.dist-info/METADATA": b"Name: pygame\\nVersion: 2.6.1\\n",
        },
    }
    for name, members in archives.items():
        (base / name).write_bytes(tar_gz_bytes(members))


def make_project(root: Path):
    add_runtime_archives(root)
    for path in ("mux_launch.sh", "voiddesk.py", "desk/main.py", "love/main.lua",
                 "bin/launcher.sh", "bin/bootstrap_lite.py", "bin/xfce_launch.sh",
                 "service/voiddesk_service.py", "lib/love",
                 "lib/libluajit-5.1.so.2", "lib/glyph_install.sh",
                 "resources/voiddesk.png", "external/tools.json", "LICENSE",
                 "README.md", "THIRD-PARTY.md"):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test fixture\n")

    upstream = root / "external" / "rt-tailscale-m"
    app = upstream / "app" / "RtTailscale"
    (app / "panel").mkdir(parents=True)
    for name in ("rt", "ts", "watchdog", "VERSION"):
        (app / name).write_text("fixture\n")
    (app / "panel" / "server.py").write_text("fixture\n")
    (app / "panel" / "index.html").write_text("fixture\n")
    (upstream / "LICENSE").write_text("MIT\n")
    (upstream / "THIRD-PARTY.md").write_text("notices\n")


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
    make_project(project)
    (project / ".env").write_text("API_KEY=must-not-ship\n")
    (project / "data").mkdir()
    (project / "data" / "user-config.json").write_text("{\"private\": true}")
    output = tmp_path / "dist" / "Void-Desk.muxapp"

    result = builder.build_archive(project, output)

    assert result == output
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    sidecar = output.with_suffix(output.suffix + ".sha256")
    assert sidecar.read_text(encoding="ascii").startswith(expected_hash + "  ")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        launcher_info = archive.getinfo("Void-Desk/mux_launch.sh")
        launcher_mode = (launcher_info.external_attr >> 16) & 0o777
        service_modes = {
            name: (archive.getinfo(
                "Void-Desk/external/rt-tailscale-m/app/RtTailscale/" + name
            ).external_attr >> 16) & 0o777
            for name in ("rt", "ts", "watchdog")
        }
        love_mode = (archive.getinfo("Void-Desk/lib/love").external_attr >> 16) & 0o777
        xfce_mode = (archive.getinfo(
            "Void-Desk/bin/xfce_launch.sh"
        ).external_attr >> 16) & 0o777
        tailscale_config = archive.read(
            "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf"
        ).decode("utf-8")
    assert names
    assert all(name.startswith("Void-Desk/") for name in names)
    assert "Void-Desk/mux_launch.sh" in names
    assert "Void-Desk/desk/main.py" in names
    assert "Void-Desk/bin/bootstrap_lite.py" in names
    assert "Void-Desk/service/voiddesk_service.py" in names
    assert "Void-Desk/lib/libluajit-5.1.so.2" in names
    assert "Void-Desk/resources/voiddesk.png" in names
    for archive_name in (
        "pygame.tar.gz", "pygame.libs.tar.gz",
        "pygame-2.6.1.data.tar.gz", "pygame-2.6.1.dist-info.tar.gz",
    ):
        assert "Void-Desk/assets/runtime_archives/" + archive_name in names
    assert "Void-Desk/love/main.lua" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf" in names
    assert "PANEL=0" in tailscale_config
    assert "PANEL_BIND=127.0.0.1" in tailscale_config
    assert tailscale_config.splitlines()[0] == "PANEL=0"
    assert r"\n" not in tailscale_config
    assert launcher_mode & 0o111 == 0o111
    assert love_mode & 0o111 == 0o111
    assert xfce_mode & 0o111 == 0o111
    assert all(mode & 0o111 == 0o111 for mode in service_modes.values())
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
