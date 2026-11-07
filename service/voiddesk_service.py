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

# ── IPTV module import ──
try:
    import iptv_module
    iptv_module.APP_DIR = APP_DIR
except ImportError:
    iptv_module = None

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
    """Launch XFCE on PC inside Xephyr. Robust against slow first start."""
    if IS_DEVICE:
        return {"ok": True, "note": "device: launch via chroot (Sprint 2)"}

    import shutil, subprocess, time, os
    if not shutil.which("startxfce4"):
        return {"ok": False, "error": "XFCE not installed — use Install XFCE Desktop first"}
    if not shutil.which("Xephyr"):
        return {"ok": False, "error": "Xephyr missing — sudo apt install xserver-xephyr"}
    if not shutil.which("dbus-run-session") and not shutil.which("dbus-launch"):
        return {"ok": False, "error": "dbus missing — sudo apt install dbus dbus-x11"}

    # Kill stale Xephyr :99
    subprocess.run(["pkill", "-f", "Xephyr :99"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(0.6)

    log_path = APP_DIR / "data" / "xfce_pc.log"
    try:
        log_file = open(log_path, "wb")
    except OSError as e:
        return {"ok": False, "error": f"cannot write log: {e}"}

    # ── 1) Start Xephyr ──
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
        return {"ok": False, "error": f"Xephyr failed: {e}"}
    _XFCE_PROCS.append(("xephyr", xephyr))

    # ── 2) Wait for X11 socket (up to 15s) ──
    sock = "/tmp/.X11-unix/X99"
    ready = False
    for _ in range(150):
        if os.path.exists(sock):
            ready = True
            break
        if xephyr.poll() is not None:
            log_file.close()
            return {"ok": False, "error": "Xephyr exited: " + _tail_log(log_path, 8)}
        time.sleep(0.1)
    if not ready:
        try: xephyr.terminate()
        except: pass
        log_file.close()
        return {"ok": False, "error": "X11 socket :99 never appeared (is :99 busy?)"}

    time.sleep(0.6)

    # ── 3) Launch XFCE with dbus session ──
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    for k in ("SDL_VIDEODRIVER", "VOIDDESK_PC", "VOIDDESK_APP_DIR"):
        env.pop(k, None)

    if shutil.which("dbus-run-session"):
        cmd = ["dbus-run-session", "--", "startxfce4"]
    elif shutil.which("dbus-launch"):
        cmd = ["dbus-launch", "startxfce4"]
    else:
        cmd = ["xfce4-session"]

    try:
        xfce = subprocess.Popen(cmd, env=env,
                                stdout=log_file, stderr=log_file,
                                preexec_fn=os.setsid)
    except Exception as e:
        log_file.close()
        try: xephyr.terminate()
        except: pass
        return {"ok": False, "error": f"launch failed: {e}"}
    _XFCE_PROCS.append(("xfce", xfce))

    # ── 4) Detect xfce4-session process (fast, not panel) ──
    for _ in range(300):  # 30s
        if xfce.poll() is not None:
            log_file.close()
            return {"ok": False,
                    "error": "XFCE exited — log: " + _tail_log(log_path, 12)}
        r = subprocess.run(["pgrep", "-x", "xfce4-session"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        if r.returncode == 0:
            log_file.close()
            return {"ok": True,
                    "note": "XFCE running in the Xephyr window",
                    "xfce_pid": xfce.pid,
                    "xephyr_pid": xephyr.pid,
                    "log": str(log_path)}
        time.sleep(0.1)

    # Process still alive but session not detected → accept it
    if xfce.poll() is None:
        log_file.close()
        return {"ok": True,
                "note": "XFCE process running (session warmup in progress)",
                "xfce_pid": xfce.pid,
                "xephyr_pid": xephyr.pid,
                "log": str(log_path)}

    log_file.close()
    return {"ok": False, "error": "XFCE never started — log: " + _tail_log(log_path, 12)}


def _muos_app_roots():
    import os
    env = os.environ.get("VD_MUOS_APP_ROOTS",
                          "/mnt/mmc/MUOS/application:/mnt/sdcard/MUOS/application")
    return [p for p in env.split(":") if os.path.isdir(p)]

def _scan_muos_apps():
    import os
    apps = []
    srcs = []
    for root in _muos_app_roots():
        srcs.append(root)
        try:
            for name in sorted(os.listdir(root)):
                full = os.path.join(root, name)
                if not os.path.isdir(full):
                    continue
                # App must have a mux_launch.sh or similar
                has_launcher = False
                for fn in ("mux_launch.sh", "launch.sh", "run.sh", "start.sh"):
                    if os.path.isfile(os.path.join(full, fn)):
                        has_launcher = True
                        break
                if has_launcher:
                    apps.append({
                        "name": name,
                        "path": full,
                        "source": root,
                    })
        except OSError:
            continue
    return apps, ":".join(srcs) if srcs else "(no MUOS/application dirs found)"

def h_list_muos_apps(args):
    apps, src = _scan_muos_apps()
    if not apps and not IS_DEVICE:
        return {"ok": False,
                "error": "device-only: no muOS application folder on PC",
                "apps": [],
                "source": "/mnt/mmc/MUOS/application (device only)",
                "reason": "device-only"}
    return {"ok": True, "apps": apps, "source": src}

def h_launch_muos_app(args):
    if not IS_DEVICE:
        return {"ok": False, "reason": "device-only",
                "error": "launching muOS apps requires the handheld"}
    import subprocess, os
    path = args.get("path", "")
    name = args.get("name", "app")
    if not os.path.isdir(path):
        return {"ok": False, "error": f"invalid path: {path}"}
    launcher = None
    for fn in ("mux_launch.sh", "launch.sh", "run.sh", "start.sh"):
        c = os.path.join(path, fn)
        if os.path.isfile(c):
            launcher = c
            break
    if not launcher:
        return {"ok": False, "error": "no launcher found"}
    try:
        subprocess.Popen(["sh", launcher], cwd=path,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return {"ok": True, "note": f"launched {name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def h_toolbox_stats(args):
    import os, glob
    data_dir = APP_DIR / "data"
    notes_count = 0
    texts_count = 0
    try:
        notes_dir = data_dir / "notes"
        if notes_dir.is_dir():
            notes_count = sum(1 for _ in notes_dir.iterdir()
                              if _.suffix == ".txt")
    except Exception:
        pass
    try:
        texts_dir = data_dir / "Texts"
        if texts_dir.is_dir():
            texts_count = sum(1 for _ in texts_dir.iterdir()
                              if _.is_file())
    except Exception:
        pass
    apps, _ = _scan_muos_apps()
    return {"ok": True,
            "notes_count": notes_count,
            "text_files": texts_count,
            "apps_count": len(apps)}


# ── IPTV handlers ──────────────────────────────────────────────────
_iptv_cache = {"playlist": None, "playlist_url": None,
               "epg": None, "epg_urls": []}

def h_iptv_load_playlist(args):
    if iptv_module is None:
        return {"ok": False, "error": "iptv module not available"}
    url = args.get("url", "").strip()
    if not url:
        return {"ok": False, "error": "no URL provided"}
    try:
        text = iptv_module.fetch_text(url)
        data = iptv_module.parse_m3u(text)
        _iptv_cache["playlist"] = data
        _iptv_cache["playlist_url"] = url
        return {"ok": True,
                "channels": data["channels"],
                "groups": data["groups"],
                "epg_urls": data["epg_urls"],
                "count": len(data["channels"])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def h_iptv_load_epg(args):
    if iptv_module is None:
        return {"ok": False, "error": "iptv module not available"}
    urls = args.get("urls", [])
    if not urls and _iptv_cache.get("playlist"):
        urls = _iptv_cache["playlist"].get("epg_urls", [])
    if not urls:
        return {"ok": False, "error": "no EPG URLs"}
    merged = {}
    errors = []
    for u in urls:
        try:
            data = iptv_module.fetch_bytes(u)
            parsed = iptv_module.parse_xmltv(data)
            for k, progs in parsed.items():
                merged.setdefault(k, []).extend(progs)
            # limit total to avoid memory blowup
            if sum(len(v) for v in merged.values()) > 8000:
                break
        except Exception as e:
            errors.append({"url": u, "error": str(e)[:120]})
    for progs in merged.values():
        progs.sort(key=lambda p: p["start"])
    _iptv_cache["epg"] = merged
    _iptv_cache["epg_urls"] = urls
    return {"ok": True, "loaded": len(urls) - len(errors),
            "errors": errors, "channels_with_epg": len(merged)}

def h_iptv_epg_for(args):
    if iptv_module is None or not _iptv_cache.get("epg"):
        return {"ok": True, "now": None, "next": None}
    channel = args.get("channel", {})
    cur, nxt = iptv_module.epg_now_next(_iptv_cache["epg"], channel)
    return {"ok": True, "now": cur, "next": nxt}

def h_iptv_play(args):
    if iptv_module is None:
        return {"ok": False, "error": "iptv module not available"}
    url = args.get("url", "")
    name = args.get("name", "stream")
    ok = iptv_module.play(url, name)
    return {"ok": ok, "state": iptv_module.status()["state"],
            "error": iptv_module.status().get("error", "")}

def h_iptv_stop(args):
    if iptv_module is None:
        return {"ok": False, "error": "iptv module not available"}
    iptv_module.stop()
    return {"ok": True}

def h_iptv_status(args):
    if iptv_module is None:
        return {"ok": True, "state": "idle", "channel": None}
    return {"ok": True, **iptv_module.status()}

def h_iptv_get_config(args):
    cfg_path = APP_DIR / "data" / "iptv_config.json"
    default = {
        "playlist_url": "https://iptv-org.github.io/iptv/countries/it.m3u",
        "epg_urls": [],
        "last_channel_url": "",
    }
    try:
        with open(cfg_path) as f:
            data = json.load(f)
            for k, v in default.items(): data.setdefault(k, v)
            return {"ok": True, "config": data}
    except Exception:
        return {"ok": True, "config": default}

def h_iptv_save_config(args):
    cfg_path = APP_DIR / "data" / "iptv_config.json"
    cfg = args.get("config", {})
    try:
        with open(cfg_path, "w") as f:
            json.dump(cfg, f, indent=1)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "network_status": h_network_status,
    "iptv_load_playlist": h_iptv_load_playlist,
    "iptv_load_epg": h_iptv_load_epg,
    "iptv_epg_for": h_iptv_epg_for,
    "iptv_play": h_iptv_play,
    "iptv_stop": h_iptv_stop,
    "iptv_status": h_iptv_status,
    "iptv_get_config": h_iptv_get_config,
    "iptv_save_config": h_iptv_save_config,

    "system_status": h_system_status,
    "media_status": h_media_status,
    "hotspot_toggle": h_hotspot_toggle,

    "session_list": h_session_list,
    "list_muos_apps": h_list_muos_apps,
    "launch_muos_app": h_launch_muos_app,
    "toolbox_stats":   h_toolbox_stats,

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
