#!/usr/bin/env python3
"""Build a muOS .muxapp with one Void-Desk/ root and pinned Tailscale service."""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIRS = (
    "assets", "bin", "desk", "external", "lib", "love", "outdesk",
    "resources", "service", "voidcast_addons",
)
APP_FILES = (
    "BUILDCHECK.py", "LICENSE", "README.md", "THIRD-PARTY.md",
    "mux_launch.sh", "voiddesk.py", "voiddesk.sh",
)
SKIP_DIRS = {
    ".git", ".github", ".pytest_cache", ".ruff_cache", "__pycache__",
    ".venv", ".venv_desktop", "node_modules", "tests", "docs",
    "wiki-source", "tools", "dist", "runtime", "data", ".cache",
}
SKIP_FILES = {".DS_Store", "Thumbs.db", ".git", ".gitmodules"}


def _copy_tree(source: Path, destination: Path, *, skip_dirs=()):
    source = Path(source)
    if not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    blocked = set(skip_dirs)
    for current, dirs, files in os.walk(source, topdown=True, followlinks=False):
        current_path = Path(current)
        relative = current_path.relative_to(source)
        kept = []
        for name in sorted(dirs):
            path = current_path / name
            if name in SKIP_DIRS or name in blocked:
                continue
            if path.is_symlink():
                raise RuntimeError(f"symbolic link is not packageable: {path}")
            kept.append(name)
        dirs[:] = kept
        target_dir = destination / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in sorted(files):
            if name in SKIP_FILES or name.endswith((".pyc", ".pyo")):
                continue
            path = current_path / name
            if path.is_symlink():
                raise RuntimeError(f"symbolic link is not packageable: {path}")
            if not path.is_file():
                continue
            target = target_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _copy_tailscale_service(repo_root: Path, package_root: Path):
    upstream = repo_root / "external" / "rt-tailscale-m"
    source = upstream / "app" / "RtTailscale"
    required = (
        source / "rt",
        source / "ts",
        source / "watchdog",
        source / "VERSION",
        source / "panel" / "server.py",
        source / "panel" / "index.html",
        upstream / "LICENSE",
        upstream / "THIRD-PARTY.md",
    )
    missing = [str(path.relative_to(repo_root)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(
            "pinned Rt:Tailscale-M submodule is not ready; missing "
            + ", ".join(missing)
            + ". Run: git submodule update --init --recursive"
        )

    target = package_root / "external" / "rt-tailscale-m" / "app" / "RtTailscale"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("rt", "ts", "watchdog", "VERSION"):
        shutil.copy2(source / name, target / name)
    _copy_tree(source / "panel", target / "panel")
    shutil.copy2(upstream / "LICENSE", target / "LICENSE")
    shutil.copy2(upstream / "THIRD-PARTY.md", target / "THIRD-PARTY.md")
    # The upstream manager creates config, bin, state and taildrop at first use.
    for name in ("config", "bin", "state", "taildrop"):
        (target / name).mkdir(exist_ok=True)


def _zip_datetime():
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800"))
    epoch = max(epoch, 315532800)
    return datetime.fromtimestamp(epoch, tz=timezone.utc).timetuple()[:6]


def build_archive(repo_root: Path, output: Path):
    repo_root = Path(repo_root).resolve()
    output = Path(output).resolve()
    required_main = ("mux_launch.sh", "voiddesk.py", "love/main.lua")
    missing = [name for name in required_main if not (repo_root / name).is_file()]
    if missing:
        raise RuntimeError("project root is incomplete: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="voiddesk-muxapp-") as temp:
        package_root = Path(temp) / "Void-Desk"
        package_root.mkdir()
        for name in APP_DIRS:
            source = repo_root / name
            if not source.exists():
                continue
            if name == "external":
                _copy_tree(source, package_root / name,
                           skip_dirs={"rt-tailscale-m"})
            else:
                _copy_tree(source, package_root / name)
        for name in APP_FILES:
            source = repo_root / name
            if source.is_file():
                if source.is_symlink():
                    raise RuntimeError(f"symbolic link is not packageable: {source}")
                shutil.copy2(source, package_root / name)

        _copy_tailscale_service(repo_root, package_root)

        output.parent.mkdir(parents=True, exist_ok=True)
        timestamp = _zip_datetime()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=7) as archive:
            for path in sorted(package_root.rglob("*")):
                if path.is_symlink():
                    raise RuntimeError(f"symbolic link is not packageable: {path}")
                if not path.is_file():
                    continue
                relative = path.relative_to(package_root.parent).as_posix()
                info = zipfile.ZipInfo(relative, date_time=timestamp)
                mode = stat.S_IMODE(path.stat().st_mode)
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_muxapp import validate_archive

    errors = validate_archive(output)
    if errors:
        output.unlink(missing_ok=True)
        raise RuntimeError("built archive failed validation: " + "; ".join(errors))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "dist" / "Void-Desk-10.5.4.muxapp",
        help="output .muxapp path (default: dist/Void-Desk-10.5.4.muxapp)",
    )
    args = parser.parse_args()
    try:
        output = build_archive(ROOT, args.output)
    except (OSError, RuntimeError) as exc:
        print("[muxapp] ERROR: " + str(exc), file=sys.stderr)
        return 1
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"[muxapp] OK: {output} ({size_mb:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
