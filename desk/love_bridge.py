# -*- coding: utf-8 -*-
"""Bridge between Python (logic) and LÖVE (graphics) on muOS Andromeda.
On x86_64 desktop, falls back to existing Pygame scenes."""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
LOVE_DIR = APP_DIR / "love"
LOVE_BIN = APP_DIR / "lib" / "love"
LIB_DIR = APP_DIR / "lib"
DATA_DIR = APP_DIR / "data"
REQ = DATA_DIR / ".love_request.json"
RESP = DATA_DIR / ".love_response.json"


def love_available() -> bool:
    """True only on ARM device where lib/love exists and is executable."""
    if platform.machine() not in ("aarch64", "arm64", "armv7l"):
        return False
    return LOVE_BIN.is_file() and os.access(LOVE_BIN, os.X_OK)


def run_scene(scene_name: str, args: dict | None = None,
              timeout: float = 120.0) -> dict:
    """Run a LÖVE scene. Returns the JSON response or {'fallback': True}
    if LÖVE is not available (desktop x86_64)."""
    if not love_available():
        return {"fallback": True}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"scene": scene_name, "args": args or {}}
    REQ.write_text(json.dumps(payload), encoding="utf-8")
    if RESP.exists():
        RESP.unlink()

    env = os.environ.copy()
    # Andromeda: bind-mounted path, never hardcode /mnt/mmc
    env["LD_LIBRARY_PATH"] = f"{LIB_DIR}:{env.get('LD_LIBRARY_PATH', '')}"
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    env.pop("SDL_VIDEODRIVER", None)

    try:
        proc = subprocess.run(
            [str(LOVE_BIN), str(LOVE_DIR)],
            cwd=str(APP_DIR),
            env=env,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except OSError as e:
        return {"ok": False, "error": str(e)}

    if RESP.exists():
        try:
            return json.loads(RESP.read_text(encoding="utf-8"))
        except Exception as e:
            return {"ok": False, "error": f"bad response: {e}"}
    return {"ok": False, "error": f"love rc={proc.returncode}"}
