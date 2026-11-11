#!/usr/bin/env python3
"""Run one validated IPTV stream after the handheld frontend releases the display."""
from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR / "service"))

try:
    import iptv_module
except Exception as exc:
    print("IPTV player unavailable: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

iptv_module.APP_DIR = APP_DIR


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: vd_media_player.py REQUEST.json", file=sys.stderr)
        return 2
    request_path = Path(argv[1])
    try:
        if request_path.is_symlink() or not request_path.is_file():
            raise ValueError("media request is not a regular file")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("media request must be a JSON object")
        url = iptv_module.validate_url(request.get("url"), stream=True)
        name = str(request.get("name") or "IPTV stream")[:120]
    except (OSError, ValueError, TypeError) as exc:
        print("Invalid media request: " + str(exc), file=sys.stderr)
        return 1

    if not iptv_module.play(url, name):
        status = iptv_module.status()
        print("MPV launch failed: " + str(status.get("error") or "unknown error"),
              file=sys.stderr)
        return 1

    process = iptv_module._mpv_proc
    if process is None:
        print("MPV process was not created", file=sys.stderr)
        return 1
    try:
        return process.wait()
    except KeyboardInterrupt:
        iptv_module.stop()
        return 130
    finally:
        iptv_module.stop()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
