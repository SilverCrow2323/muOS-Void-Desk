#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Background worker for RSS and weather refreshes launched by Void Desk."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA = APP_DIR / "data"
sys.path.insert(0, str(APP_DIR / "service"))

from content_tools import refresh_rss, refresh_weather  # noqa: E402


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("rss", "weather"):
        print("usage: content_refresh.py rss [category] [language] | weather CITY", file=sys.stderr)
        return 2
    kind = argv[1]
    if kind == "rss":
        category = argv[2] if len(argv) > 2 else "all"
        language = argv[3] if len(argv) > 3 else "all"
        progress_path = DATA / ".rss_refresh_state.json"
        cache_path = DATA / "rss_cache.json"
        action = lambda progress: refresh_rss(category, language, progress)
    else:
        city = " ".join(argv[2:]).strip()
        if not city:
            print("weather refresh requires a city name", file=sys.stderr)
            return 2
        progress_path = DATA / ".weather_refresh_state.json"
        cache_path = DATA / "weather_cache.json"
        action = lambda progress: refresh_weather(city, progress)

    def progress(percent, phase, message, detail=""):
        atomic_json(progress_path, {
            "progress": max(0, min(100, int(percent))),
            "phase": str(phase)[:48],
            "message": str(message)[:180],
            "detail": str(detail)[:240],
            "animation": "download" if phase in ("FETCHING", "GEOCODING", "FORECAST") else "verify",
            "indeterminate": False,
            "severity": "info",
        })
        print("[%s] %s%% %s — %s" % (kind.upper(), percent, phase, message), flush=True)

    try:
        payload = action(progress)
        atomic_json(cache_path, payload)
        progress_path.unlink(missing_ok=True)
        print("[%s] cache updated" % kind.upper(), flush=True)
        return 0
    except Exception as exc:
        progress_path.unlink(missing_ok=True)
        print("[%s] refresh failed: %s" % (kind.upper(), str(exc)[:240]), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
