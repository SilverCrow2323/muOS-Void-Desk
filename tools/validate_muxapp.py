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
    "Void-Desk/desk/main.py",
    "Void-Desk/love/main.lua",
    "Void-Desk/bin/bootstrap_lite.py",
    "Void-Desk/bin/xfce_launch.sh",
    "Void-Desk/service/voiddesk_service.py",
    "Void-Desk/lib/love",
    "Void-Desk/lib/libluajit-5.1.so.2",
    "Void-Desk/lib/glyph_install.sh",
    "Void-Desk/resources/voiddesk.png",
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
                        label = (
                            "muOS launcher"
                            if normalized == "Void-Desk/mux_launch.sh"
                            else "Rt:Tailscale-M entrypoint"
                        )
                        errors.append("%s is not executable: %s" % (label, normalized))

            if top_levels != {"Void-Desk"}:
                errors.append(
                    "archive must contain exactly one top-level directory "
                    "named Void-Desk/"
                )
            for required in REQUIRED_FILES:
                if required not in files:
                    errors.append("required file missing: %s" % required)

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
