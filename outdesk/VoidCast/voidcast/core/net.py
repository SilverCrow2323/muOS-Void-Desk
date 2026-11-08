# outdesk/VoidCast/voidcast/core/net.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.net — download utility (UA custom, gzip, cache su disco)

import gzip
import hashlib
import io
import os
import ssl
import time
import urllib.request


def _opener(user_agent):
    ctx = ssl.create_default_context()
    # su firmware embedded i CA bundle a volte sono vecchi: non moriamo per questo
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    handler = urllib.request.HTTPSHandler(context=ctx)
    op = urllib.request.build_opener(handler)
    op.addheaders = [("User-Agent", user_agent or "Mozilla/5.0"),
                     ("Accept-Encoding", "gzip")]
    return op


def fetch_bytes(url, user_agent=None, timeout=25):
    """Scarica bytes. Decomprime gzip automaticamente (header o magic bytes)."""
    op = _opener(user_agent)
    with op.open(url, timeout=timeout) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass
    return raw


def fetch_text(url, user_agent=None, timeout=25):
    raw = fetch_bytes(url, user_agent, timeout)
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def cached_fetch(url, cache_dir, max_age_hours, user_agent=None):
    """Ritorna (bytes, from_cache). Cache su file keyed su hash URL."""
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(cache_dir, key + ".bin")
    max_age = max_age_hours * 3600
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age:
        with open(path, "rb") as f:
            return f.read(), True
    data = fetch_bytes(url, user_agent)
    try:
        with open(path, "wb") as f:
            f.write(data)
    except OSError:
        pass
    return data, False
