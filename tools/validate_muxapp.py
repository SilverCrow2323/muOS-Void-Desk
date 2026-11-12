#!/usr/bin/env python3
"""Validate the VoidDesk handheld .muxapp archive layout."""
from __future__ import annotations

import argparse
import io
import stat
import tarfile
import sys
import zipfile
from pathlib import Path, PurePosixPath


REQUIRED_FILES = (
    "Void-Desk/mux_launch.sh",
    "Void-Desk/voiddesk.py",
    "Void-Desk/desk/main.py",
    "Void-Desk/love/main.lua",
    "Void-Desk/bin/bootstrap_lite.py",
    "Void-Desk/bin/xfce_launch.sh",
    "Void-Desk/service/voiddesk_service.py",
    "Void-Desk/lib/love",
    "Void-Desk/lib/libluajit-5.1.so.2",
    "Void-Desk/lib/glyph_install.sh",
    "Void-Desk/resources/voiddesk.png",
    "Void-Desk/assets/runtime_archives/pygame.tar.gz",
    "Void-Desk/assets/runtime_archives/pygame.libs.tar.gz",
    "Void-Desk/assets/runtime_archives/pygame-2.6.1.data.tar.gz",
    "Void-Desk/assets/runtime_archives/pygame-2.6.1.dist-info.tar.gz",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/ts",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/watchdog",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py",
)

EXECUTABLE_FILES = (
    "Void-Desk/mux_launch.sh",
    "Void-Desk/bin/xfce_launch.sh",
    "Void-Desk/lib/love",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/ts",
    "Void-Desk/external/rt-tailscale-m/app/RtTailscale/watchdog",
)


def validate_pygame_runtime_archives(package: zipfile.ZipFile, files: set[str]) -> list[str]:
    """Inspect the offline Pygame tar payload without extracting it to disk."""
    prefix = "Void-Desk/assets/runtime_archives/"
    archive_names = {
        "pygame.tar.gz": prefix + "pygame.tar.gz",
        "pygame.libs.tar.gz": prefix + "pygame.libs.tar.gz",
        "pygame-2.6.1.data.tar.gz": prefix + "pygame-2.6.1.data.tar.gz",
        "pygame-2.6.1.dist-info.tar.gz": prefix + "pygame-2.6.1.dist-info.tar.gz",
    }
    errors: list[str] = []
    extracted: dict[str, set[str]] = {}
    wheel_text = ""

    for label, member_path in archive_names.items():
        if member_path not in files:
            continue
        try:
            payload = package.read(member_path)
            if not payload:
                raise ValueError("archive is empty")
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
                members = archive.getmembers()
                if not members:
                    raise ValueError("tar archive is empty")
                names: set[str] = set()
                for member in members:
                    name = member.name
                    relative = PurePosixPath(name)
                    if (not name or "\\" in name or relative.is_absolute()
                            or ".." in relative.parts or not relative.parts):
                        raise ValueError("unsafe tar path: %r" % name)
                    if not (member.isfile() or member.isdir()):
                        raise ValueError("unsupported tar member type: %r" % name)
                    names.add(str(relative))
                extracted[label] = names
                if label == "pygame-2.6.1.dist-info.tar.gz":
                    wheel_member = next(
                        (m for m in members if m.name.endswith("/WHEEL") or m.name == "WHEEL"),
                        None,
                    )
                    if wheel_member is None:
                        raise ValueError("WHEEL metadata is missing")
                    stream = archive.extractfile(wheel_member)
                    if stream is None:
                        raise ValueError("WHEEL metadata cannot be read")
                    wheel_text = stream.read().decode("utf-8")
        except (OSError, tarfile.TarError, UnicodeDecodeError, ValueError) as exc:
            errors.append("invalid bundled Pygame archive %s: %s" % (label, exc))

    pygame_names = extracted.get("pygame.tar.gz", set())
    for required in (
        "pygame/__init__.py",
        "pygame/base.cpython-311-aarch64-linux-gnu.so",
    ):
        if required not in pygame_names:
            errors.append("bundled Pygame source archive missing: %s" % required)

    libs_names = extracted.get("pygame.libs.tar.gz", set())
    if not any(
        name.startswith("pygame.libs/libSDL2-") and ".so.0" in name
        for name in libs_names
    ):
        errors.append("bundled Pygame SDL2 ARM64 libraries missing")

    data_names = extracted.get("pygame-2.6.1.data.tar.gz", set())
    if not any(name.startswith("pygame-2.6.1.data/") for name in data_names):
        errors.append("bundled Pygame data archive has an unexpected layout")

    if wheel_text and not (
        "Tag: cp311-cp311-manylinux_2_17_aarch64" in wheel_text
        and "Tag: cp311-cp311-manylinux2014_aarch64" in wheel_text
    ):
        errors.append("bundled Pygame wheel metadata is not CPython 3.11/aarch64")

    return errors


def validate_archive(archive: str | Path) -> list[str]:
    """Return validation errors; an empty list means the package is valid."""
    path = Path(archive)
    errors: list[str] = []
    if not path.is_file():
        return ["archive does not exist or is not a regular file"]

    try:
        with zipfile.ZipFile(path) as package:
            infos = package.infolist()
            if not infos:
                return ["archive is empty"]

            seen: set[str] = set()
            files: set[str] = set()
            top_levels: set[str] = set()

            for info in infos:
                name = info.filename
                if not name or "\\" in name:
                    errors.append("invalid archive member path: %r" % name)
                    continue
                member = PurePosixPath(name)
                if member.is_absolute() or ".." in member.parts:
                    errors.append("unsafe archive member path: %s" % name)
                    continue
                normalized = str(member)
                if normalized in seen:
                    errors.append("duplicate archive member: %s" % normalized)
                    continue
                seen.add(normalized)

                if not member.parts:
                    errors.append("empty archive member path")
                    continue
                top_levels.add(member.parts[0])
                if member.parts[0] != "Void-Desk":
                    errors.append(
                        "unexpected top-level entry: %s (only Void-Desk/ is allowed)"
                        % member.parts[0]
                    )
                if len(member.parts) == 1 and not info.is_dir():
                    errors.append("top-level files are not allowed: %s" % name)

                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    errors.append("symbolic links are not allowed: %s" % name)
                if not info.is_dir():
                    files.add(normalized)
                    if normalized in EXECUTABLE_FILES and not (mode & 0o111):
                        if normalized == "Void-Desk/mux_launch.sh":
                            label = "muOS launcher"
                        elif normalized.startswith(
                            "Void-Desk/external/rt-tailscale-m/"
                        ):
                            label = "Rt:Tailscale-M entrypoint"
                        else:
                            label = "runtime entrypoint"
                        errors.append("%s is not executable: %s" % (label, normalized))

            if top_levels != {"Void-Desk"}:
                errors.append(
                    "archive must contain exactly one top-level directory "
                    "named Void-Desk/"
                )
            for required in REQUIRED_FILES:
                if required not in files:
                    errors.append("required file missing: %s" % required)

            errors.extend(validate_pygame_runtime_archives(package, files))

            config_name = "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf"
            if config_name in files:
                try:
                    config = package.read(config_name).decode("utf-8")
                    required_settings = (
                        "PANEL=0", "PANEL_BIND=127.0.0.1", "WATCHDOG=1",
                        "TAILDROP=1", "TS_MODE=auto", "WIFI_WAIT=120",
                    )
                    for setting in required_settings:
                        if setting not in config.splitlines():
                            errors.append("Rt:Tailscale-M config missing setting: %s" % setting)
                    if "\\n" in config:
                        errors.append("Rt:Tailscale-M config contains literal escaped newlines")
                except (UnicodeDecodeError, KeyError) as exc:
                    errors.append("cannot read Rt:Tailscale-M config: %s" % exc)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        errors.append("cannot read archive: %s" % exc)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="path to the .muxapp ZIP archive")
    args = parser.parse_args()

    errors = validate_archive(args.archive)
    if errors:
        for error in errors:
            print("[muxapp] ERROR: " + error, file=sys.stderr)
        return 1

    with zipfile.ZipFile(args.archive) as package:
        files = sum(not item.is_dir() for item in package.infolist())
    print("[muxapp] OK: one Void-Desk/ root, %d files, required launchers present"
          % files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
