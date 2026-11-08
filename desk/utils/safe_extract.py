# -*- coding: utf-8 -*-
"""
Archive extraction helpers.

Tar extraction includes a path traversal check for Python versions before 3.12.
ZIP extraction validates every member before writing, including ZIP metadata
that can describe symbolic links or special files.
"""
import os
import stat
import tarfile


def _inside(base, target):
    return target == base or target.startswith(base + os.sep)


def safe_tar_extractall(tf, dest):
    dest_real = os.path.realpath(dest)
    safe = []
    for member in tf.getmembers():
        target = os.path.realpath(os.path.join(dest_real, member.name))
        if not _inside(dest_real, target):
            raise ValueError("unsafe archive (path traversal): %s" % member.name)
        if member.issym() or member.islnk():
            base = (os.path.dirname(os.path.join(dest_real, member.name))
                    if member.issym() else dest_real)
            link_target = os.path.realpath(os.path.join(base, member.linkname))
            if not _inside(dest_real, link_target):
                raise ValueError(
                    "unsafe archive (link outside target folder): %s" % member.name
                )
        if member.isdev():
            continue
        safe.append(member)

    if hasattr(tarfile, "data_filter"):
        tf.extractall(dest, members=safe, filter="data")
    else:
        tf.extractall(dest, members=safe)


def safe_zip_extractall(zf, dest, max_total_size=256 * 1024 * 1024):
    """Extract a ZIP after rejecting traversal, links, special files and bombs."""
    dest_real = os.path.realpath(dest)
    safe_members = []
    seen = set()
    total_size = 0

    for info in zf.infolist():
        raw_name = info.filename
        if not raw_name or "\x00" in raw_name:
            raise ValueError("unsafe archive (empty or NUL path)")

        normalized = raw_name.replace("\\", "/")
        if normalized.startswith("/") or (
                len(normalized) >= 2 and normalized[1] == ":"):
            raise ValueError("unsafe archive (absolute path): %s" % raw_name)

        parts = normalized.split("/")
        if any(part == ".." for part in parts):
            raise ValueError("unsafe archive (path traversal): %s" % raw_name)

        clean_parts = [part for part in parts if part not in ("", ".")]
        if not clean_parts:
            raise ValueError("unsafe archive (empty path): %s" % raw_name)
        clean_name = "/".join(clean_parts)
        if clean_name in seen:
            raise ValueError("unsafe archive (duplicate path): %s" % raw_name)
        seen.add(clean_name)

        target = os.path.realpath(os.path.join(dest_real, *clean_parts))
        try:
            inside = os.path.commonpath((dest_real, target)) == dest_real
        except ValueError:
            inside = False
        if not inside:
            raise ValueError("unsafe archive (path traversal): %s" % raw_name)

        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if stat.S_ISLNK(mode) or file_type not in (
                0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError("unsafe archive (special file): %s" % raw_name)

        if info.file_size < 0:
            raise ValueError("unsafe archive (invalid file size): %s" % raw_name)
        total_size += info.file_size
        if total_size > max_total_size:
            raise ValueError("unsafe archive (expanded size limit exceeded)")

        safe_members.append(info)

    os.makedirs(dest_real, exist_ok=True)
    zf.extractall(dest_real, members=safe_members)
