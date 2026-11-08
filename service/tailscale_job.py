#!/usr/bin/env python3
"""Background install/start task for the bundled Rt:Tailscale-M service."""
from pathlib import Path
import sys

import tailscale_manager

APP_DIR = Path(__file__).resolve().parents[1]


def main():
    result = tailscale_manager.action(APP_DIR, "start")
    output = result.get("output", "")
    error = result.get("error", "")
    if output:
        print(output)
    if error:
        print(error, file=sys.stderr)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
