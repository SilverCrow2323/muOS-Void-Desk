# -*- coding: utf-8 -*-
"""
Atomic writes for config/state: tmp + fsync + os.replace.
On a handheld the battery can die at any moment: with open(..., "w")
the file is truncated BEFORE writing, so a power cut = empty config.
Here the real file only changes once the write is complete (atomic rename).
"""
import json
import os
import shutil


def atomic_write_text(path, text, backup=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    if backup and os.path.exists(path):
        try:
            shutil.copy2(path, path + ".bak")
        except OSError:
            pass
    os.replace(tmp, path)


def atomic_write_json(path, obj, backup=False, **dump_kw):
    # serialize FIRST: if obj is not serializable the disk is never touched
    text = json.dumps(obj, **dump_kw)
    atomic_write_text(path, text, backup=backup)


def atomic_read_json(path, default=None):
    """Reads the JSON; if it is corrupt/missing tries path.bak, then default."""
    for p in (path, path + ".bak"):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, dict) and not isinstance(data, dict):
                continue
            return data
        except (OSError, ValueError):
            continue
    return default
