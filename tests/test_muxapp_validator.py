import importlib.util
import io
import stat
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE_MEMBERS = {
    "Void-Desk/mux_launch.sh",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/ts",
    "Void-Desk/bin/xfce_launch.sh",
    "Void-Desk/lib/love",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/watchdog",
}


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
            info = zipfile.ZipInfo(name)
            mode = 0o755 if name in EXECUTABLE_MEMBERS else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, payload)


def tar_gz_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def runtime_archives():
    return {
        "Void-Desk/assets/runtime_archives/pygame.tar.gz": tar_gz_bytes({
            "pygame/__init__.py": b"from . import base\\n",
            "pygame/base.cpython-311-aarch64-linux-gnu.so": b"ELF fixture",
        }),
        "Void-Desk/assets/runtime_archives/pygame.libs.tar.gz": tar_gz_bytes({
            "pygame.libs/libSDL2-test.so.0": b"ELF SDL fixture",
        }),
        "Void-Desk/assets/runtime_archives/pygame-2.6.1.data.tar.gz": tar_gz_bytes({
            "pygame-2.6.1.data/headers/include/pgcompat.h": b"/* fixture */\\n",
        }),
        "Void-Desk/assets/runtime_archives/pygame-2.6.1.dist-info.tar.gz": tar_gz_bytes({
            "pygame-2.6.1.dist-info/WHEEL": (
                b"Wheel-Version: 1.0\\nRoot-Is-Purelib: false\\n"
                b"Tag: cp311-cp311-manylinux_2_17_aarch64\\n"
                b"Tag: cp311-cp311-manylinux2014_aarch64\\n"
            ),
            "pygame-2.6.1.dist-info/METADATA": b"Name: pygame\\nVersion: 2.6.1\\n",
        }),
    }


def valid_members():
    return {
        "Void-Desk/mux_launch.sh": b"#!/bin/sh\n",
        "Void-Desk/voiddesk.py": b"print('VoidDesk')\n",
        "Void-Desk/desk/main.py": b"# pygame entrypoint fixture\n",
        "Void-Desk/love/main.lua": b"function love.load() end\n",
        "Void-Desk/bin/bootstrap_lite.py": b"# bootstrap fixture\n",
        "Void-Desk/bin/xfce_launch.sh": b"#!/bin/sh\n",
        "Void-Desk/service/voiddesk_service.py": b"# service fixture\n",
        "Void-Desk/lib/love": b"fake-love-binary",
        "Void-Desk/lib/libluajit-5.1.so.2": b"fake-luajit-library",
        "Void-Desk/lib/glyph_install.sh": b"# glyph fixture\n",
        "Void-Desk/resources/voiddesk.png": b"png-fixture",
        **runtime_archives(),
        "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt": b"#!/bin/sh\n",
        "Void-Desk/external/rt-tailscale-m/app/RtTailscale/ts": b"#!/bin/sh\n",
        "Void-Desk/external/rt-tailscale-m/app/RtTailscale/watchdog": b"#!/bin/sh\n",
        "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf": (
            b"PANEL=0\nPANEL_BIND=127.0.0.1\nWATCHDOG=1\n"
            b"TAILDROP=1\nTS_MODE=auto\nWIFI_WAIT=120\n"
        ),
        "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py": (
            b"# Rt:Tailscale-M panel fixture\n"
        ),
    }


def test_muxapp_accepts_single_void_desk_root(tmp_path):
    archive = tmp_path / "valid.muxapp"
    make_archive(archive, valid_members())
    assert load_validator().validate_archive(archive) == []


def test_muxapp_rejects_non_executable_muos_launcher(tmp_path):
    archive = tmp_path / "non-executable.muxapp"
    members = valid_members()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, payload in members.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            package.writestr(info, payload)
    errors = load_validator().validate_archive(archive)
    assert any("muOS launcher is not executable" in error for error in errors)
    assert sum("Rt:Tailscale-M entrypoint is not executable" in error
               for error in errors) == 3
    assert any("bin/xfce_launch.sh" in error and "not executable" in error
               for error in errors)
    assert any("lib/love" in error and "not executable" in error
               for error in errors)


def test_muxapp_rejects_invalid_offline_pygame_wheel_tag(tmp_path):
    archive = tmp_path / "wrong-abi.muxapp"
    members = valid_members()
    members["Void-Desk/assets/runtime_archives/pygame-2.6.1.dist-info.tar.gz"] = (
        tar_gz_bytes({
            "pygame-2.6.1.dist-info/WHEEL": (
                b"Tag: cp310-cp310-manylinux2014_aarch64\\n"
            )
        })
    )
    make_archive(archive, members)
    errors = load_validator().validate_archive(archive)
    assert any("not CPython 3.11/aarch64" in error for error in errors)


def test_muxapp_rejects_missing_offline_pygame_binary(tmp_path):
    archive = tmp_path / "missing-pygame-base.muxapp"
    members = valid_members()
    members["Void-Desk/assets/runtime_archives/pygame.tar.gz"] = tar_gz_bytes({
        "pygame/__init__.py": b"# incomplete wheel\\n",
    })
    make_archive(archive, members)
    errors = load_validator().validate_archive(archive)
    assert any("pygame/base.cpython-311-aarch64-linux-gnu.so" in error
               for error in errors)


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
