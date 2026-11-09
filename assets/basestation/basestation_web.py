# -*- coding: utf-8 -*-
"""Safe read-only helpers for the SPDW Hub PC browser dashboard."""
from __future__ import print_function

import json
import os
from datetime import datetime
from pathlib import Path

from basestation_core import safe_device_id


def list_received_files(incoming_dir, limit=1000):
    """List regular non-symlink files from the per-device inbox."""
    root = Path(incoming_dir)
    root.mkdir(parents=True, exist_ok=True)
    files = []
    for device_dir in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if device_dir.is_symlink() or not device_dir.is_dir():
            continue
        device_id = safe_device_id(device_dir.name)
        for entry in sorted(device_dir.iterdir(), key=lambda item: item.name.lower()):
            if entry.is_symlink() or not entry.is_file():
                continue
            info = entry.stat(follow_symlinks=False)
            files.append({
                "device": device_id,
                "name": entry.name,
                "size": int(info.st_size),
                "mtime": datetime.fromtimestamp(
                    info.st_mtime).astimezone().isoformat(timespec="seconds"),
            })
            if len(files) >= max(1, int(limit)):
                return files
    return files


def resolve_received_file(incoming_dir, device_id, filename):
    """Resolve one inbox file and reject traversal and symlink escapes."""
    root = Path(incoming_dir).resolve()
    safe_id = safe_device_id(device_id)
    name = str(filename or "")
    if (not name or name in (".", "..") or os.path.basename(name) != name
            or "/" in name or "\\" in name or name != safe_device_id(name)):
        raise ValueError("invalid file name")
    device_root = root / safe_id
    if device_root.is_symlink():
        raise ValueError("symbolic device directory is not allowed")
    device_root = device_root.resolve(strict=True)
    try:
        device_root.relative_to(root)
    except ValueError:
        raise ValueError("device directory escapes received-files root")
    target = root / safe_id / name
    if target.is_symlink():
        raise ValueError("symbolic links are not downloadable")
    target = target.resolve(strict=True)
    try:
        target.relative_to(device_root)
    except ValueError:
        raise ValueError("file escapes device received-files directory")
    if not target.is_file():
        raise FileNotFoundError(name)
    return target


def load_service_registry(source_file):
    """Read the shared registry from the source tree or PC bundle."""
    source = Path(source_file).resolve()
    candidates = (
        source.parent / "services.json",
        source.parents[2] / "service" / "spdw_hub" / "services.json",
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        with candidate.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError("service registry root must be an object")
        return data
    raise FileNotFoundError("SPDW service registry is not bundled")
