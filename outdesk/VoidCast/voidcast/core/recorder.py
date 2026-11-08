# outdesk/VoidCast/voidcast/core/recorder.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.recorder — shared PVR (ffmpeg stream-copy).
import os
import shutil
import signal
import subprocess
import time

_proc = None
_current = ""
_last_file = ""

def is_active():
    return _proc is not None and _proc.poll() is None

def current():
    return _current if is_active() else ""

def last_file():
    return _last_file

def start(url, name, rec_dir, ua=""):
    global _proc, _current, _last_file
    if is_active():
        return False, "already recording"
    ff = shutil.which("ffmpeg")
    if not ff:
        return False, "ffmpeg not found"
    try:
        os.makedirs(rec_dir, exist_ok=True)
    except OSError:
        pass
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:40]
    out = os.path.join(rec_dir, "%s_%s.ts"
                       % (safe, time.strftime("%Y%m%d_%H%M%S")))
    cmd = [ff, "-hide_banner", "-loglevel", "error",
           "-user_agent", ua, "-i", url,
           "-c", "copy", "-f", "mpegts", out]
    try:
        _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        _current = name
        _last_file = out
        return True, out
    except OSError as e:
        return False, str(e)

def stop():
    global _proc, _current
    if not is_active():
        _proc = None
        return False
    name = _current
    try:
        _proc.send_signal(signal.SIGINT)
        _proc.wait(timeout=8)
    except Exception:
        _proc.kill()
    _proc = None
    _current = ""
    return name
