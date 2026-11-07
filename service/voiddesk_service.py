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
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        return {"ok": True, "info": {
            "os":       platform.system(),
            "machine":  platform.machine(),
            "hostname": platform.node(),
            "is_device": IS_DEVICE,
            "ip":       local_ip,
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

def _tail_log(path, n=12):
    try:
        with open(path, "rb") as f:
            data = f.read()[-4000:].decode("utf-8", "replace")
        lines = [ln for ln in data.splitlines() if ln.strip()]
        return " | ".join(lines[-n:])
    except Exception:
        return ""

def h_xfce_launch(args):
    """Launch XFCE on PC inside Xephyr. Returns detailed error on failure."""
    if IS_DEVICE:
        return {"ok": True, "note": "device: launch via VoidDesk chroot (Sprint 2)"}

    import shutil, subprocess, time, os
    if not shutil.which("startxfce4"):
        return {"ok": False, "error": "XFCE not installed — use Install XFCE Desktop first"}
    if not shutil.which("Xephyr"):
        return {"ok": False, "error": "Xephyr missing — install: sudo apt install xserver-xephyr"}
    if not shutil.which("dbus-run-session") and not shutil.which("dbus-launch"):
        return {"ok": False, "error": "dbus-run-session missing — install: sudo apt install dbus"}

    # Kill stale Xephyr on :99
    subprocess.run(["pkill", "-f", "Xephyr :99"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(0.5)

    log_path = APP_DIR / "data" / "xfce_pc.log"
    try:
        log_file = open(log_path, "wb")
    except OSError as e:
        return {"ok": False, "error": f"cannot write log: {e}"}

    # ── 1) Launch Xephyr ──
    try:
        xephyr = subprocess.Popen(
            ["Xephyr", ":99",
             "-screen", "1280x720",
             "-ac", "-br", "-noreset",
             "-title", "VoidDesk XFCE (PC)"],
            stdout=log_file, stderr=log_file,
            preexec_fn=os.setsid)
    except Exception as e:
        log_file.close()
        return {"ok": False, "error": f"Xephyr failed to start: {e}"}
    _XFCE_PROCS.append(("xephyr", xephyr))

    # ── 2) Wait for X11 socket ──
    sock = "/tmp/.X11-unix/X99"
    ready = False
    for _ in range(60):  # 6s max
        if os.path.exists(sock):
            ready = True
            break
        if xephyr.poll() is not None:
            log_file.close()
            return {"ok": False,
                    "error": "Xephyr exited: " + _tail_log(log_path, 8)}
        time.sleep(0.1)
    if not ready:
        try: xephyr.terminate()
        except Exception: pass
        log_file.close()
        return {"ok": False,
                "error": "Xephyr socket /tmp/.X11-unix/X99 never appeared (maybe :99 busy)"}

    time.sleep(0.4)  # let X settle

    # ── 3) Launch XFCE with dbus session ──
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    # Remove our pygame-specific vars that might confuse GTK
    for k in ("SDL_VIDEODRIVER", "VOIDDESK_PC", "VOIDDESK_APP_DIR"):
        env.pop(k, None)

    cmd = ["dbus-run-session", "--", "startxfce4"]
    if not shutil.which("dbus-run-session"):
        # fallback to dbus-launch shim
        cmd = ["dbus-launch", "startxfce4"]

    try:
        xfce = subprocess.Popen(
            cmd, env=env,
            stdout=log_file, stderr=log_file,
            preexec_fn=os.setsid)
    except Exception as e:
        log_file.close()
        try: xephyr.terminate()
        except Exception: pass
        return {"ok": False, "error": f"startxfce4 failed: {e}"}
    _XFCE_PROCS.append(("xfce", xfce))

    # ── 4) Wait for xfce4-panel to appear (or fail) ──
    for _ in range(100):  # 10s
        if xfce.poll() is not None:
            log_file.close()
            return {"ok": False,
                    "error": "XFCE exited immediately — log: " + _tail_log(log_path, 12)}
        r = subprocess.run(["pgrep", "-f", "xfce4-panel"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        if r.returncode == 0:
            log_file.close()
            return {"ok": True,
                    "note": "XFCE running in the 'VoidDesk XFCE (PC)' window",
                    "xfce_pid": xfce.pid,
                    "xephyr_pid": xephyr.pid,
                    "log": str(log_path)}
        time.sleep(0.1)

    log_file.close()
    return {"ok": True,
            "note": "XFCE running (panel not detected yet — may be slow to start)",
            "xfce_pid": xfce.pid,
            "xephyr_pid": xephyr.pid,
            "log": str(log_path)}


def h_session_list(args):
    import shutil
    xfce_inst = (shutil.which("startxfce4") is not None) if not IS_DEVICE else True
    return {"ok": True, "sessions": [
        {"id": "xfce",  "name": "XFCE",  "installed": xfce_inst},
        {"id": "icewm", "name": "IceWM", "installed": False},
        {"id": "lxde",  "name": "LXDE",  "installed": False},
    ]}

def h_session_launch(args):
    sid = args.get("id", "xfce")
    if sid == "xfce":
        return h_xfce_launch(args)
    return {"ok": False, "error": f"{sid} not yet supported on this platform"}

def h_wifi_scan(args):
    if not IS_DEVICE:
        return {"ok": False, "reason": "device-only", "networks": []}
    import subprocess
    try:
        out = subprocess.check_output(["iwlist", "wlan0", "scan"],
                                       stderr=subprocess.DEVNULL,
                                       text=True, timeout=15)
        nets, cur = [], {}
        for line in out.splitlines():
            line = line.strip()
            if "ESSID:" in line:
                cur["ssid"] = line.split(":", 1)[1].strip().strip('"')
                nets.append(cur); cur = {}
            elif "Signal level=" in line:
                try: cur["signal"] = line.split("=")[1].split(" ")[0]
                except Exception: pass
        return {"ok": True, "networks": nets}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "networks": []}

def h_bt_scan(args):
    import shutil, subprocess
    if not shutil.which("bluetoothctl"):
        return {"ok": False, "reason": "no bluetoothctl", "devices": []}
    try:
        out = subprocess.check_output(["bluetoothctl", "devices"],
                                       stderr=subprocess.DEVNULL,
                                       text=True, timeout=10)
        devs = []
        for line in out.splitlines():
            parts = line.split(" ", 2)
            if len(parts) >= 3 and parts[0] == "Device":
                devs.append({"mac": parts[1], "name": parts[2]})
        return {"ok": True, "devices": devs}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "devices": []}


HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "session_list": h_session_list,
    "session_launch": h_session_launch,
    "wifi_scan": h_wifi_scan,
    "bt_scan": h_bt_scan,

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
