#!/usr/bin/env python3
"""
VoidDesk background service — reads .love_request.json,
writes .love_response.json. Minimal, no external deps.
Runs on both muOS (aarch64) and desktop x86_64.
"""
import json
import os
import platform
import shutil
import sys
import time
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA    = APP_DIR / "data"
REQ     = DATA / ".love_request.json"
RESP    = DATA / ".love_response.json"
CFG     = DATA / "desk_config.json"
DATA.mkdir(parents=True, exist_ok=True)

IS_DEVICE = platform.machine().lower() in ("aarch64", "armv7l", "arm64")

def log(msg):
    print(f"[service] {msg}", file=sys.stderr, flush=True)

# ── handlers ─────────────────────────────────────────────
def h_ping(args):
    return {"ok": True, "pong": True, "device": IS_DEVICE,
            "machine": platform.machine()}

def h_get_config(args):
    try:
        return {"ok": True, "config": json.loads(CFG.read_text())}
    except Exception:
        return {"ok": True, "config": {}}

def h_set_config(args):
    try:
        CFG.write_text(json.dumps(args.get("config", {}), indent=1))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_system_info(args):
    try:
        du = shutil.disk_usage("/")
        return {"ok": True, "info": {
            "os":       platform.system(),
            "machine":  platform.machine(),
            "hostname": platform.node(),
            "is_device": IS_DEVICE,
            "disk_free_gb": round(du.free / 1e9, 1),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_list_files(args):
    path = args.get("path", "/")
    try:
        items = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            try:
                items.append({
                    "name": name,
                    "is_dir": os.path.isdir(full),
                    "size": os.path.getsize(full) if os.path.isfile(full) else 0,
                })
            except OSError:
                continue
        return {"ok": True, "items": items[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def device_only(cmd):
    if not IS_DEVICE:
        return {"ok": False, "reason": "device-only", "command": cmd}
    return None

def h_xfce_install(args):
    """Install XFCE:
       - on device: deferred (arm64 chroot via device bootstrap)
       - on PC: apt install xfce4 + Xephyr via pkexec (GUI prompt)."""
    if IS_DEVICE:
        return {"ok": True, "note": "device: install via VoidDesk chroot (Sprint 2)"}
    import shutil, subprocess
    if shutil.which("startxfce4"):
        return {"ok": True, "already": True, "note": "XFCE already installed"}
    try:
        r = subprocess.run(
            ["pkexec", "apt-get", "install", "-y", "--no-install-recommends",
             "xfce4", "xfce4-terminal", "xserver-xephyr"],
            capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            return {"ok": True, "note": "XFCE installed on PC"}
        return {"ok": False, "error": (r.stderr or r.stdout)[-300:] or "apt failed"}
    except FileNotFoundError:
        return {"ok": False, "error": "pkexec missing — install polkit (sudo apt install pkexec)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "install timed out (>15 min)"}

# Track XFCE/Xephyr subprocesses so we can clean up on exit
import atexit
_XFCE_PROCS = []
def _kill_xfce_procs():
    for name, proc in _XFCE_PROCS:
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass
atexit.register(_kill_xfce_procs)

def h_xfce_launch(args):
    """Launch XFCE:
       - on device: deferred (real chroot)
       - on PC: run XFCE inside Xephyr (nested X server in a window)."""
    if IS_DEVICE:
        return {"ok": True, "note": "device: launch via VoidDesk chroot (Sprint 2)"}
    import shutil, subprocess, time
    if not shutil.which("startxfce4"):
        return {"ok": False, "error": "XFCE not installed — run Install XFCE Desktop first"}
    if not shutil.which("Xephyr"):
        return {"ok": False, "error": "Xephyr missing — install: sudo apt install xserver-xephyr"}
    try:
        # Kill any stale Xephyr :99 from a previous run
        subprocess.run(["pkill", "-f", "Xephyr :99"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        time.sleep(0.4)
        xephyr = subprocess.Popen(
            ["Xephyr", ":99", "-screen", "800x600",
             "-title", "VoidDesk XFCE (PC)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid)
        _XFCE_PROCS.append(("xephyr", xephyr))
        time.sleep(1.6)  # give Xephyr time to initialize
        env = os.environ.copy()
        env["DISPLAY"] = ":99"
        xfce = subprocess.Popen(
            ["startxfce4"], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid)
        _XFCE_PROCS.append(("xfce", xfce))
        return {"ok": True,
                "note": "XFCE running in the 'VoidDesk XFCE (PC)' window",
                "xfce_pid": xfce.pid,
                "xephyr_pid": xephyr.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_apt_update(args):
    r = device_only("apt_update")
    if r: return r
    return {"ok": True, "note": "implementation deferred to Sprint 2"}

HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "list_files": h_list_files,
    "xfce_install": h_xfce_install,
    "xfce_launch": h_xfce_launch,
    "apt_update": h_apt_update,
}

# ── main loop ────────────────────────────────────────────
def main():
    log(f"started  machine={platform.machine()}  device={IS_DEVICE}")
    log(f"req={REQ}  resp={RESP}")
    last_mtime = 0
    while True:
        try:
            if not REQ.exists():
                time.sleep(0.05)
                continue
            mtime = REQ.stat().st_mtime
            if mtime == last_mtime:
                time.sleep(0.05)
                continue
            last_mtime = mtime
            req = json.loads(REQ.read_text())
            cmd  = req.get("cmd", "")
            args = req.get("args", {})
            rid  = req.get("id", 0)
            fn = HANDLERS.get(cmd)
            try:
                resp = fn(args) if fn else {"ok": False, "error": f"unknown cmd: {cmd}"}
            except Exception:
                resp = {"ok": False, "error": traceback.format_exc(limit=3)}
            resp["id"] = rid
            RESP.write_text(json.dumps(resp))
        except Exception as e:
            log(f"loop error: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
