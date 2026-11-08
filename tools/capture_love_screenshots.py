#!/usr/bin/env python3
"""Capture every LÖVE scene under a real LÖVE runtime (optionally headless).

Run from any directory:
    python3 tools/capture_love_screenshots.py
    python3 tools/capture_love_screenshots.py --love-bin /path/to/love

Requires LÖVE 11.5. If no desktop display is available, xvfb-run is required.
The script writes local PNGs and metadata under data/visual-captures/ and
refreshes the asset/screenshot catalogue. Captures are intentionally ignored
by Git until they have been reviewed for private information.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "data" / "visual-captures"
MANIFEST = CAPTURE_DIR / "love-batch-manifest.json"


def find_love(value: str | None) -> str | None:
    if value:
        candidate = Path(value).expanduser()
        if candidate.exists():
            return str(candidate.resolve())
        return shutil.which(value)
    return shutil.which("love")


def command_for(love_bin: str, game_dir: Path, use_xvfb: bool) -> list[str]:
    command = [love_bin, str(game_dir)]
    if use_xvfb:
        xvfb = shutil.which("xvfb-run")
        if not xvfb:
            raise RuntimeError("xvfb-run is required when DISPLAY is not set")
        command = [xvfb, "-a", *command]
    return command


def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def read_manifest(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--love-bin", help="LÖVE 11.5 binary; defaults to PATH lookup")
    parser.add_argument("--timeout", type=int, default=240,
                        help="maximum runtime in seconds (default: 240)")
    parser.add_argument("--settle", type=float, default=0.85,
                        help="seconds to let each scene settle before capture")
    parser.add_argument("--no-service", action="store_true",
                        help="do not start the Python companion service")
    parser.add_argument("--no-xvfb", action="store_true",
                        help="use the existing display instead of xvfb-run")
    parser.add_argument("--no-catalog", action="store_true",
                        help="do not regenerate asset and screenshot reports")
    args = parser.parse_args()

    love_bin = find_love(args.love_bin)
    if not love_bin:
        print("ERROR: LÖVE was not found. Install LÖVE 11.5 or pass --love-bin.",
              file=sys.stderr)
        return 2
    if args.timeout <= 0 or args.settle < 0:
        print("ERROR: timeout must be positive and settle cannot be negative.",
              file=sys.stderr)
        return 2

    use_xvfb = not args.no_xvfb and not os.environ.get("DISPLAY")
    if use_xvfb and not shutil.which("xvfb-run"):
        print("ERROR: no DISPLAY is set and xvfb-run is unavailable.",
              file=sys.stderr)
        return 2

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update({
        "VOIDDESK_APP_DIR": str(ROOT),
        "VOIDDESK_CAPTURE_ALL": "1",
        "VOIDDESK_CAPTURE_SETTLE": str(args.settle),
        "VOIDDESK_FULLSCREEN": "0",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_AUDIODRIVER": "dummy",
    })

    xdg_data = CAPTURE_DIR / "love-xdg-data"
    xdg_data.mkdir(parents=True, exist_ok=True)
    env["XDG_DATA_HOME"] = str(xdg_data)

    service = None
    service_log_handle = None
    love_log = CAPTURE_DIR / "love-batch-run.log"
    service_log = CAPTURE_DIR / "love-batch-service.log"

    try:
        if not args.no_service:
            service_log_handle = service_log.open("wb")
            service = subprocess.Popen(
                [sys.executable, str(ROOT / "service" / "voiddesk_service.py")],
                cwd=ROOT,
                env=env,
                stdout=service_log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            time.sleep(0.35)
            if service.poll() is not None:
                raise RuntimeError(
                    "the Python service exited before capture; see "
                    + str(service_log)
                )

        command = command_for(love_bin, ROOT / "love", use_xvfb)
        print("Starting LÖVE scene capture:")
        print("  " + " ".join(command))
        print("Output: " + str(CAPTURE_DIR))

        with love_log.open("wb") as log_handle:
            try:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                print("ERROR: capture timed out; see " + str(love_log),
                      file=sys.stderr)
                return 1

        manifest = read_manifest(MANIFEST)
        if manifest is None:
            print("ERROR: LÖVE did not produce a batch manifest; see "
                  + str(love_log), file=sys.stderr)
            return 1

        captured = manifest.get("captured", [])
        failed = manifest.get("failed", [])
        requested = int(manifest.get("requested", 0))
        print("Captured %d/%d LÖVE screens; %d failed." %
              (len(captured), requested, len(failed)))
        for entry in failed:
            print("  FAILED %-20s %s" %
                  (entry.get("screen", "?"), entry.get("error", "")))
        if completed.returncode != 0:
            print("ERROR: LÖVE exited with code %d; see %s" %
                  (completed.returncode, love_log), file=sys.stderr)
            return 1

        if not args.no_catalog:
            inventory = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "visual_capture.py")],
                cwd=ROOT,
                check=False,
            )
            if inventory.returncode:
                return inventory.returncode

        print("Manifest: " + str(MANIFEST))
        print("Run log: " + str(love_log))
        return 1 if failed or len(captured) != requested else 0

    except (OSError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    finally:
        stop_process(service)
        if service_log_handle is not None:
            service_log_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
