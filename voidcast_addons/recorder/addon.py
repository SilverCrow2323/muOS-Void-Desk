# -*- coding: utf-8 -*-
# VOIDCAST addon // PVR Recorder v1.1
# Records the current channel stream to SD with ffmpeg stream-copy (no
# transcoding: the H700's CPU says thanks).
#
# Demonstrates the addon contract: register(api) -> list of actions.
#   context "channel" -> shows in the channel action menu (START)
#   context "menu"    -> shows in TOOLS / ADDONS

import os
import shutil
import signal
import subprocess
import time

_proc = None
_current = ""


def _ffmpeg():
    return shutil.which("ffmpeg")


def _start(api):
    global _proc, _current
    ch = api.current_channel
    if ch is None:
        api.toast("No channel selected", ok=False)
        return
    if _proc is not None and _proc.poll() is None:
        api.toast("Recording already active: " + _current, ok=False)
        return
    ff = _ffmpeg()
    if not ff:
        api.toast("ffmpeg not found on system", ok=False)
        return
    safe = "".join(c if c.isalnum() or c in "-_" else "_"
                  for c in ch.name)[:40]
    out = os.path.join(api.recordings_dir,
                       "%s_%s.ts" % (safe, time.strftime("%Y%m%d_%H%M%S")))
    ua = api.config.get("user_agent", "")
    cmd = [ff, "-hide_banner", "-loglevel", "error",
          "-user_agent", ua, "-i", ch.url,
          "-c", "copy", "-f", "mpegts", out]
    try:
        _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        _current = ch.name
        api.log("REC start: %s -> %s" % (ch.name, out))
        api.toast("REC: " + ch.name)
    except OSError as e:
        api.toast("ffmpeg failed: %s" % e, ok=False)


def _stop(api):
    global _proc
    if _proc is None or _proc.poll() is not None:
        api.toast("No recording active", ok=False)
        _proc = None
        return
    try:
        _proc.send_signal(signal.SIGINT)
        _proc.wait(timeout=8)
    except Exception:  # noqa: BLE001
        _proc.kill()
    _proc = None
    api.log("REC stop: %s" % _current)
    api.toast("Recording saved: " + _current)


def _status(api):
    if _proc is not None and _proc.poll() is None:
        api.toast("REC in progress: " + _current)
    else:
        if os.path.isdir(api.recordings_dir):
            n = len([f for f in os.listdir(api.recordings_dir)
                    if f.endswith(".ts")])
        else:
            n = 0
        api.toast("No active REC - %d file(s) in recordings/" % n)


def register(api):
    return [
        {"label": "Record this channel", "action": _start,
        "context": "channel"},
        {"label": "Stop recording", "action": _stop, "context": "menu"},
        {"label": "Recording status", "action": _status, "context": "menu"},
    ]
