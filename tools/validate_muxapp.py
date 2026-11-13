#!/usr/bin/env python3
"""Validate the VoidDesk handheld .muxapp archive layout."""
from __future__ import annotations

import argparse
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath


REQUIRED_FILES = (
    "Void-Desk/mux_launch.sh",
    "Void-Desk/voiddesk.py",
    "Void-Desk/love/main.lua",
    "Void-Desk/lib/love",
    "Void-Desk/lib/liblove-11.5.so",
    "Void-Desk/lib/libluajit-5.1.so.2",
)

AARCH64_MACHINE = 183
MIN_LOVE_RUNTIME_BYTES = 1024 * 1024


def _validate_aarch64_elf(data: bytes, label: str, errors: list[str]):
    if len(data) < 64 or data[:4] != b"\x7fELF":
        errors.append("%s is not a valid ELF executable/library" % label)
        return False
    if data[4] != 2 or data[5] != 1:
        errors.append("%s must be a 64-bit little-endian ELF" % label)
        return False
    machine = int.from_bytes(data[18:20], "little")
    if machine != AARCH64_MACHINE:
        errors.append("%s targets ELF machine %d, not AArch64" % (label, machine))
        return False
    return True



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
                if normalized == "Void-Desk/lib/love" and not (mode & 0o111):
                    errors.append("LÖVE launcher is not executable: %s" % normalized)
                if not info.is_dir():
                    files.add(normalized)

            if top_levels != {"Void-Desk"}:
                errors.append(
                    "archive must contain exactly one top-level directory "
                    "named Void-Desk/"
                )
            for required in REQUIRED_FILES:
                if required not in files:
                    errors.append("required file missing: %s" % required)

            runtime_paths = (
                "Void-Desk/lib/love",
                "Void-Desk/lib/liblove-11.5.so",
                "Void-Desk/lib/libluajit-5.1.so.2",
            )
            runtime_data = {}
            for runtime_path in runtime_paths:
                if runtime_path in files:
                    runtime_data[runtime_path] = package.read(runtime_path)

            loader_path = "Void-Desk/lib/love"
            love_path = "Void-Desk/lib/liblove-11.5.so"
            luajit_path = "Void-Desk/lib/libluajit-5.1.so.2"
            loader = runtime_data.get(loader_path)
            love_lib = runtime_data.get(love_path)
            luajit_lib = runtime_data.get(luajit_path)

            if loader is not None:
                if _validate_aarch64_elf(loader, "lib/love", errors):
                    for dependency in (b"liblove-11.5.so", b"libluajit-5.1.so.2"):
                        if dependency not in loader:
                            errors.append(
                                "lib/love does not declare expected runtime dependency: "
                                + dependency.decode("ascii")
                            )
            if love_lib is not None:
                _validate_aarch64_elf(love_lib, "lib/liblove-11.5.so", errors)
                if len(love_lib) < MIN_LOVE_RUNTIME_BYTES:
                    errors.append("lib/liblove-11.5.so is too small to be the LÖVE 11.5 runtime")
            if luajit_lib is not None:
                _validate_aarch64_elf(luajit_lib, "lib/libluajit-5.1.so.2", errors)
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
