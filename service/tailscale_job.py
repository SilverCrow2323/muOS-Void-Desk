#!/usr/bin/env python3
"""Background install/start task for the bundled Rt:Tailscale-M service."""
from pathlib import Path
import os
import sys

import tailscale_manager

APP_DIR = Path(__file__).resolve().parents[1]
LOCK = APP_DIR / "data" / ".tailscale_setup.pid"


def claim():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(str(os.getpid()))
            return True
        except FileExistsError:
            try:
                pid = int(LOCK.read_text(encoding="ascii").strip())
                os.kill(pid, 0)
                command = Path(f"/proc/{pid}/cmdline").read_bytes()
                if b"tailscale_job.py" in command:
                    print("Tailscale setup is already running")
                    return False
            except (OSError, ValueError):
                pass
            LOCK.unlink(missing_ok=True)
    return False


def main():
    if not claim():
        return 0
    try:
        result = tailscale_manager.action(APP_DIR, "start")
        output = result.get("output", "")
        error = result.get("error", "")
        if output:
            print(output)
        if error:
            print(error, file=sys.stderr)
        return 0 if result.get("ok") else 1
    finally:
        try:
            if LOCK.read_text(encoding="ascii").strip() == str(os.getpid()):
                LOCK.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
