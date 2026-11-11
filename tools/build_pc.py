#!/usr/bin/env python3
"""Create a sanitized, portable Linux PC source bundle for Void Desk."""
from __future__ import annotations

import argparse
import hashlib
import io
import platform
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PREFIXES = (
    ".github/", "docs/", "tests/", "tools/", "wiki-source/", "data/",
    "external/rt-tailscale-m/",
)
EXCLUDED_NAMES = {".env", ".env.local", ".DS_Store", "Thumbs.db"}
README = """VOID DESK — LINUX PC BUNDLE

Requirements:
- Linux x86_64 or aarch64
- Python 3.10 or newer
- A working graphical session and SDL2 runtime libraries

Run:
  chmod +x launch-pc.sh
  ./launch-pc.sh

The launcher uses the existing voiddesk.py --py path. On first launch it creates
.venv_desktop and installs Pygame and psutil from PyPI. Internet access is needed
for that first dependency installation. You can also run:
  python3 voiddesk.py --help

This is a portable source bundle, not a statically linked binary or AppImage.
Handheld-only operations (muOS package management, framebuffer, XFCE image
mounting) are unavailable on a normal PC. LÖVE mode requires a system LÖVE
installation. Back up your configuration before replacing an existing copy.
"""


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        return False
    if any(part in EXCLUDED_NAMES for part in path.parts):
        return False
    if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    return True


def build_archive(output: str | Path, version: str) -> Path:
    output = Path(output)
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,40}", version):
        raise ValueError("version contains unsupported characters")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryFile() as source_tar:
        proc = subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=ROOT, stdout=source_tar, stderr=subprocess.PIPE, check=False,
        )
        if proc.returncode:
            raise RuntimeError(
                "git archive failed: " + proc.stderr.decode("utf-8", "replace")
            )
        source_tar.seek(0)
        digest = hashlib.sha256()
        with tarfile.open(fileobj=source_tar, mode="r:") as source:
            with tarfile.open(output, mode="w:gz", format=tarfile.PAX_FORMAT) as dest:
                for member in source:
                    if not _safe_member(member.name):
                        continue
                    if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                        raise RuntimeError("unsupported archive member: " + member.name)
                    stream = source.extractfile(member) if member.isfile() else None
                    member.name = "VoidDesk-PC/" + member.name
                    dest.addfile(member, stream)
                data_dir = tarfile.TarInfo("VoidDesk-PC/data/")
                data_dir.type = tarfile.DIRTYPE
                data_dir.mode = 0o755
                dest.addfile(data_dir)
                launch = ROOT / "packaging" / "pc" / "launch.sh"
                readme = tarfile.TarInfo("VoidDesk-PC/PC-README.txt")
                readme_data = README.replace("@VERSION@", version).encode("utf-8")
                readme.size = len(readme_data)
                readme.mode = 0o644
                dest.addfile(readme, io.BytesIO(readme_data))
                launch_data = launch.read_bytes()
                launch_info = tarfile.TarInfo("VoidDesk-PC/launch-pc.sh")
                launch_info.size = len(launch_data)
                launch_info.mode = 0o755
                dest.addfile(launch_info, io.BytesIO(launch_data))

    with output.open("rb") as package:
        for chunk in iter(lambda: package.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(
        digest.hexdigest() + "  " + output.name + "\n", encoding="ascii"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="dev")
    args = parser.parse_args()
    result = build_archive(args.output, args.version)
    print("[pc-build] created %s (%s, %s)" %
          (result, platform.system(), platform.machine()))
    print("[pc-build] sha256: %s" %
          hashlib.sha256(result.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
