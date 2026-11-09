# -*- coding: utf-8 -*-
"""Portable, testable helpers for VOID BaseStation.

This module intentionally has no Tk or Paramiko import so the security and
backup primitives can be tested on headless build workers.
"""
from __future__ import print_function

import hashlib
import hmac
import json
import os
import posixpath
import secrets
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def generate_auth_token():
    """Create a high-entropy token suitable for the BaseStation LAN daemon."""
    return secrets.token_urlsafe(32)


def token_matches(expected, supplied):
    """Constant-time token comparison. Empty tokens never authenticate."""
    if not isinstance(expected, str) or not expected:
        return False
    if not isinstance(supplied, str) or not supplied:
        return False
    try:
        return hmac.compare_digest(expected.encode("utf-8"),
                                   supplied.encode("utf-8"))
    except (UnicodeError, TypeError):
        return False


def atomic_write_json(path, payload, mode=0o600):
    """Persist JSON atomically and restrict the resulting file permissions."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp",
                                     dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(temp_name, mode)
        except OSError:
            pass
        os.replace(temp_name, str(path))
        return path
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _safe_component(value):
    value = str(value or "").strip()
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in value)
    cleaned = cleaned.strip("._")
    return cleaned[:64] or "backup"


def _safe_relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    normalized = posixpath.normpath(value)
    if normalized in ("", ".") or normalized.startswith("/") or normalized == ".." or normalized.startswith("../"):
        return None
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return normalized


def _remote_join(root, relative):
    root = posixpath.normpath(str(root))
    relative = _safe_relative_path(relative)
    if not root.startswith("/") or not relative:
        raise ValueError("remote backup paths must be absolute and relative paths must be safe")
    target = posixpath.normpath(posixpath.join(root, relative))
    if not target.startswith(root.rstrip("/") + "/"):
        raise ValueError("remote path escapes selected backup root")
    return target


def create_remote_backup(sftp, roots, archive_path, metadata=None,
                         progress_callback=None, chunk_size=256 * 1024):
    """Create a verified ZIP snapshot of selected remote folders via SFTP.

    sftp is an already-authenticated Paramiko SFTP client. roots is an
    iterable of dictionaries containing name and absolute path. Symlinks and
    non-regular special files are skipped rather than followed. The output is
    replaced atomically only after the complete ZIP is closed.
    """
    roots = list(roots or [])
    if not roots:
        raise ValueError("at least one remote folder is required")
    for root in roots:
        if not isinstance(root, dict) or not root.get("name") or not root.get("path"):
            raise ValueError("each backup root needs a name and path")
        if not str(root["path"]).startswith("/"):
            raise ValueError("remote backup roots must be absolute paths")

    destination = Path(archive_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".partial",
                                     dir=str(destination.parent))
    os.close(fd)
    manifest = {
        "format": "void-basestation-backup",
        "format_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "metadata": metadata or {},
        "roots": [],
        "files": [],
        "skipped": [],
    }

    try:
        work = []
        seen_roots = set()
        for root in roots:
            label = _safe_component(root["name"])
            if label in seen_roots:
                raise ValueError("backup root labels must be unique")
            seen_roots.add(label)
            remote_root = posixpath.normpath(str(root["path"]))
            if remote_root == "/" or not remote_root.startswith("/"):
                raise ValueError("refusing to back up filesystem root or relative path")
            root_record = {"name": label, "remote_path": remote_root,
                           "files": 0, "bytes": 0}
            manifest["roots"].append(root_record)
            stack = [(remote_root, "")]
            while stack:
                directory, prefix = stack.pop()
                for entry in sftp.listdir_attr(directory):
                    name = getattr(entry, "filename", "")
                    if not name or name in (".", "..") or "/" in name or "\\" in name:
                        manifest["skipped"].append({
                            "root": label, "path": str(name), "reason": "unsafe name"})
                        continue
                    relative = _safe_relative_path(
                        posixpath.join(prefix, name) if prefix else name)
                    if not relative:
                        manifest["skipped"].append({
                            "root": label, "path": str(name), "reason": "unsafe path"})
                        continue
                    remote_path = _remote_join(remote_root, relative)
                    mode = int(getattr(entry, "st_mode", 0) or 0)
                    if stat.S_ISLNK(mode):
                        manifest["skipped"].append({
                            "root": label, "path": relative, "reason": "symbolic link"})
                    elif stat.S_ISDIR(mode):
                        stack.append((remote_path, relative))
                    elif mode == 0 or stat.S_ISREG(mode):
                        work.append((label, root_record, relative, remote_path,
                                     int(getattr(entry, "st_size", 0) or 0),
                                     int(getattr(entry, "st_mtime", 0) or 0)))
                    else:
                        manifest["skipped"].append({
                            "root": label, "path": relative, "reason": "special file"})

        total = len(work)
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for index, item in enumerate(work, 1):
                label, root_record, relative, remote_path, size, mtime = item
                archive_name = "VOID-BaseStation-Backup/files/{}/{}".format(label, relative)
                info = zipfile.ZipInfo(archive_name,
                    date_time=datetime.now().timetuple()[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                digest = hashlib.sha256()
                copied = 0
                with sftp.open(remote_path, "rb") as source:
                    with archive.open(info, "w") as target:
                        while True:
                            chunk = source.read(chunk_size)
                            if not chunk:
                                break
                            target.write(chunk)
                            digest.update(chunk)
                            copied += len(chunk)
                file_record = {
                    "root": label, "path": relative, "archive_path": archive_name,
                    "size_bytes": copied, "remote_mtime": mtime,
                    "sha256": digest.hexdigest(),
                }
                manifest["files"].append(file_record)
                root_record["files"] += 1
                root_record["bytes"] += copied
                if progress_callback:
                    progress_callback(relative, index, total)

            archive.writestr(
                "VOID-BaseStation-Backup/manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))
        os.replace(temp_name, str(destination))
        return manifest
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
