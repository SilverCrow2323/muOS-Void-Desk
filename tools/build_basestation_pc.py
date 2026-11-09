#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a reproducible standalone VOID BaseStation PC companion archive."""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets" / "basestation"
REQUIRED_FILES = (
    "basestation.py",
    "basestation_core.py",
    "basestation_web.py",
    "pc_hub.html",
    "requirements.txt",
    "README.md",
    "run_basestation.sh",
)
ZIP_EPOCH = (2024, 1, 1, 0, 0, 0)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_archive(source_dir, output_path, version="4.0.0"):
    source_dir = Path(source_dir)
    output_path = Path(output_path)
    if not version or any(ch not in "0123456789.-" for ch in version):
        raise ValueError("version must contain only digits, dots and hyphens")

    def source_for(name):
        candidate = source_dir / name
        if candidate.is_file():
            return candidate
        # Include an exact project or companion license only when supplied;
        # never invent license terms for this archive.
        if name == "LICENSE" and (ROOT / "LICENSE").is_file():
            return ROOT / "LICENSE"
        return candidate

    missing = [name for name in REQUIRED_FILES if not source_for(name).is_file()]
    registry_source = ROOT / "service" / "spdw_hub" / "services.json"
    if missing:
        raise RuntimeError("BaseStation PC source is incomplete: " + ", ".join(missing))
    if not registry_source.is_file():
        raise RuntimeError("SPDW service registry is missing: {}".format(registry_source))
    package_files = REQUIRED_FILES + (("LICENSE",) if source_for("LICENSE").is_file() else ())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    root_name = "VOID-BaseStation-{}".format(version)
    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED,
        compresslevel=9, allowZip64=True
    ) as archive:
        for name in package_files:
            source = source_for(name)
            data = source.read_bytes()
            info = zipfile.ZipInfo(
                "{}/{}".format(root_name, name), date_time=ZIP_EPOCH)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if name == "run_basestation.sh" else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)

        # Keep the single source-of-truth registry in the PC companion bundle
        # beside basestation.py so the web dashboard can render service policy.
        data = registry_source.read_bytes()
        info = zipfile.ZipInfo("{}/services.json".format(root_name),
                               date_time=ZIP_EPOCH)
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.flag_bits |= 0x800
        archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                         compresslevel=9)

    checksum = sha256_file(output_path)
    sidecar = output_path.with_name(output_path.name + ".sha256")
    sidecar.write_text("{}  {}\n".format(checksum, output_path.name),
                       encoding="ascii")
    return output_path, sidecar, checksum


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the standalone VOID BaseStation PC companion ZIP.")
    parser.add_argument("--output", required=True, help="destination ZIP path")
    parser.add_argument("--version", default="4.0.0",
                        help="BaseStation version (default: 4.0.0)")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR),
                        help="BaseStation source directory")
    args = parser.parse_args(argv)
    archive, checksum_file, checksum = build_archive(
        args.source_dir, args.output, args.version)
    print("Built: {}".format(archive))
    print("SHA-256: {}".format(checksum))
    print("Checksum file: {}".format(checksum_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
