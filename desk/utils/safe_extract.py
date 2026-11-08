# -*- coding: utf-8 -*-
"""
Tar extraction with path traversal check (compatible with Python < 3.12).
Python's zipfile.extractall already sanitizes '..' and absolute paths; tarfile does not.
"""
import os
import tarfile


def _inside(base, target):
    return target == base or target.startswith(base + os.sep)


def safe_tar_extractall(tf, dest):
    dest_real = os.path.realpath(dest)
    safe = []
    for m in tf.getmembers():
        target = os.path.realpath(os.path.join(dest_real, m.name))
        if not _inside(dest_real, target):
            raise ValueError("unsafe archive (path traversal): %s" % m.name)
        if m.issym() or m.islnk():
            base = os.path.dirname(os.path.join(dest_real, m.name)) if m.issym() else dest_real
            lt = os.path.realpath(os.path.join(base, m.linkname))
            if not _inside(dest_real, lt):
                raise ValueError("unsafe archive (link outside target folder): %s" % m.name)
        if m.isdev():
            continue  # no device nodes from user archives
        safe.append(m)
    if hasattr(tarfile, "data_filter"):
        tf.extractall(dest, members=safe, filter="data")
    else:
        tf.extractall(dest, members=safe)
