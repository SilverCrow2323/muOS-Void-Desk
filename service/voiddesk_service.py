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


# ── External tools ────────────────────────────────────────────────
_EXTERNAL_PROCS = []

def _load_external_tools():
    import json as _j
    path = APP_DIR / "external" / "tools.json"
    try:
        return _j.loads(path.read_text())
    except Exception:
        return {"tools": []}

def _resolve_path(rel):
    """Resolve a path relative to APP_DIR."""
    from pathlib import Path as _P
    base = APP_DIR
    if rel.startswith("../"):
        base = base.parent
        rel = rel[3:]
    return (base / rel).resolve()

def h_list_external(args):
    data = _load_external_tools()
    out = []
    for t in data.get("tools", []):
        p = _resolve_path(t.get("path", ""))
        exists = p.is_dir() or p.is_file()
        # resolve launcher
        launcher = t.get("launcher", "")
        if launcher:
            lp = _resolve_path(launcher)
            launcher_exists = lp.is_file()
        else:
            launcher_exists = exists
        out.append({**t, "exists": exists,
                    "launcher_exists": launcher_exists,
                    "resolved_path": str(p)})
    return {"ok": True, "tools": out}

def h_launch_external(args):
    """Launch a tool by id. Logs everything to data/external_launch.log."""
    import subprocess, os as _os, shutil, time
    from datetime import datetime
    tid = args.get("id", "")
    data = _load_external_tools()
    tool = None
    for t in data.get("tools", []):
        if t.get("id") == tid:
            tool = t
            break
    if not tool:
        return {"ok": False, "error": f"unknown tool: {tid}"}

    lpath = _resolve_external_path(tool.get("launcher", ""))
    if not lpath.exists():
        return {"ok": False,
                "error": f"not installed: {lpath}",
                "hint": "run: cd external && git clone <repo>"}

    ltype = tool.get("launcher_type", "sh")
    log_path = APP_DIR / "data" / "external_launch.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = dict(_os.environ)
    env.pop("SDL_VIDEODRIVER", None)

    try:
        if ltype == "sh":
            cmd = ["sh", str(lpath)]
            cwd = str(lpath.parent)
        elif ltype == "love":
            love_bin = None
            for cand in (str(APP_DIR / "lib" / "love"),
                         "/usr/bin/love",
                         shutil.which("love") or ""):
                if cand and Path(cand).is_file() and _os.access(cand, _os.X_OK):
                    love_bin = cand
                    break
            if not love_bin:
                return {"ok": False,
                        "error": "LOVE binary not found",
                        "hint": "sudo apt install love (PC) "
                                "or ensure lib/love is executable (device)"}
            env["LD_LIBRARY_PATH"] = str(APP_DIR / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
            env["VOIDDESK_APP_DIR"] = str(APP_DIR)
            cmd = [love_bin, str(lpath)]
            cwd = str(lpath.parent)
        elif ltype == "python":
            cmd = ["python3", str(lpath)]
            cwd = str(lpath.parent)
        else:
            return {"ok": False, "error": f"unknown launcher_type: {ltype}"}

        # Log headers
        try:
            with open(log_path, "a") as lf:
                sep = "=" * 60
                now_iso = datetime.now().isoformat()
                lf.write("\n" + sep + "\n")
                lf.write("[" + now_iso + "] Launch: " + tid + "\n")
                lf.write("cmd: " + " ".join(cmd) + "\n")
                lf.write("cwd: " + cwd + "\n")
                lf.write("DISPLAY: " + str(env.get("DISPLAY", "(none)")) + "\n")
        except OSError:
            pass

        # Spawn with log redirection
        with open(log_path, "ab") as logf:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=logf, stderr=logf,
                                    start_new_session=True)
        _EXTERNAL_PROCS.append((tid, proc, str(log_path)))

        # Wait 1.5s to detect fast crash
        time.sleep(1.5)
        if proc.poll() is not None:
            # Died fast - read log tail
            tail = ""
            try:
                with open(log_path) as f:
                    tail = f.read()[-600:]
            except OSError:
                pass
            return {"ok": False,
                    "error": f"exited in 1.5s (code {proc.returncode})",
                    "log_tail": tail,
                    "log_file": str(log_path),
                    "cmd": " ".join(cmd),
                    "cwd": cwd}

        return {"ok": True,
                "note": f"launched {tool.get('name', tid)}",
                "pid": proc.pid,
                "log_file": str(log_path),
                "cmd": " ".join(cmd)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def h_external_status(args):
    out = []
    for entry in _EXTERNAL_PROCS[:]:
        tid = entry[0]
        proc = entry[1]
        log_path = entry[2] if len(entry) > 2 else None
        alive = proc.poll() is None
        info = {"id": tid, "pid": proc.pid, "alive": alive}
        if not alive:
            info["exit_code"] = proc.returncode
            if log_path:
                try:
                    with open(log_path) as f:
                        info["log_tail"] = f.read()[-400:]
                except OSError:
                    pass
            _EXTERNAL_PROCS.remove(entry)
        out.append(info)
    return {"ok": True, "running": out}


# ── Job manager ────────────────────────────────────────────────────
_JOBS = {}

try:
    import threading as _threading
except Exception:
    _threading = None

_JOB_COLORS = [
    [0.90, 0.31, 0.75], [0.94, 0.35, 0.24], [0.31, 0.80, 1.00],
    [0.37, 0.82, 0.55], [0.69, 0.43, 0.94], [0.59, 0.63, 0.71],
]

def _next_job_color():
    return _JOB_COLORS[len(_JOBS) % len(_JOB_COLORS)]

def _add_job_log(job_id, line):
    j = _JOBS.get(job_id)
    if not j:
        return
    j["log"].append(line)
    if len(j["log"]) > 200:
        j["log"] = j["log"][-200:]

def h_job_start(args):
    import subprocess, os as _os, shutil, time as _time
    tool_id = args.get("tool_id", "")
    cmd_str = args.get("cmd", "")
    name    = args.get("name", tool_id or cmd_str or "job")
    hub     = args.get("hub", "toolbox")
    job_id = "job_%d" % int(_time.time() * 1000)

    if tool_id:
        data = _load_external_tools()
        tool = None
        for t in data.get("tools", []):
            if t.get("id") == tool_id:
                tool = t; break
        if not tool:
            return {"ok": False, "error": "unknown tool: " + tool_id}
        lpath = _resolve_external_path(tool.get("launcher", ""))
        if not lpath.exists():
            return {"ok": False, "error": "not installed: " + str(lpath)}
        ltype = tool.get("launcher_type", "sh")
        env = dict(_os.environ); env.pop("SDL_VIDEODRIVER", None)
        if ltype == "sh":
            cmd = ["sh", str(lpath)]; cwd = str(lpath.parent)
        elif ltype == "love":
            love_bin = None
            for cand in (str(APP_DIR / "lib" / "love"), "/usr/bin/love",
                         shutil.which("love") or ""):
                if cand and Path(cand).is_file() and _os.access(cand, _os.X_OK):
                    love_bin = cand; break
            if not love_bin:
                return {"ok": False, "error": "LOVE binary not found"}
            env["LD_LIBRARY_PATH"] = str(APP_DIR / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
            env["VOIDDESK_APP_DIR"] = str(APP_DIR)
            cmd = [love_bin, str(lpath)]; cwd = str(lpath.parent)
        elif ltype == "python":
            cmd = ["python3", str(lpath)]; cwd = str(lpath.parent)
        else:
            return {"ok": False, "error": "unknown launcher_type: " + ltype}
        name = tool.get("name", tool_id)
        hub = tool.get("hub", hub)
        color = tool.get("color") or _next_job_color()
    elif cmd_str:
        cmd = ["sh", "-c", cmd_str]; cwd = str(APP_DIR)
        env = dict(_os.environ); color = _next_job_color()
    else:
        return {"ok": False, "error": "no tool_id or cmd"}

    _JOBS[job_id] = {"id": job_id, "name": name, "hub": hub, "color": color,
                     "status": "starting", "progress": 0, "log": [],
                     "pid": None, "proc": None,
                     "started": _time.time(), "ended": None, "exit_code": None}
    _add_job_log(job_id, "$ " + " ".join(cmd))

    def _runner():
        import re as _re
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    start_new_session=True, text=True, bufsize=1)
            _JOBS[job_id]["proc"] = proc
            _JOBS[job_id]["pid"] = proc.pid
            _JOBS[job_id]["status"] = "running"
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                _add_job_log(job_id, line.rstrip()[:200])
                m = _re.search(r"(\d{1,3})%", line)
                if m:
                    _JOBS[job_id]["progress"] = min(99, int(m.group(1)))
                else:
                    m2 = _re.search(r"\((\d+)/(\d+)\)", line)
                    if m2:
                        cur, tot = int(m2.group(1)), int(m2.group(2))
                        if tot > 0:
                            _JOBS[job_id]["progress"] = min(99, int(100 * cur / tot))
            proc.wait()
            _JOBS[job_id]["exit_code"] = proc.returncode
            if proc.returncode == 0:
                _JOBS[job_id]["status"] = "done"
                _JOBS[job_id]["progress"] = 100
                _add_job_log(job_id, "[done] exit 0")
            else:
                _JOBS[job_id]["status"] = "error"
                _add_job_log(job_id, "[error] exit %d" % proc.returncode)
            _JOBS[job_id]["ended"] = _time.time()
        except Exception as e:
            _JOBS[job_id]["status"] = "error"
            _add_job_log(job_id, "[fatal] " + str(e))
            _JOBS[job_id]["ended"] = _time.time()

    if _threading:
        t = _threading.Thread(target=_runner, daemon=True)
        t.start()
    else:
        _runner()

    return {"ok": True, "job_id": job_id, "name": name, "color": color}

def h_job_list(args):
    import time as _time
    now = _time.time()
    expired = []
    for jid, j in list(_JOBS.items()):
        if j.get("ended") and (now - j["ended"]) > 300:
            expired.append(jid)
    for jid in expired:
        _JOBS.pop(jid, None)
    out = []
    for jid, j in _JOBS.items():
        out.append({"id": jid, "name": j["name"], "hub": j["hub"],
                    "color": j["color"], "status": j["status"],
                    "progress": j["progress"], "pid": j.get("pid"),
                    "started": j["started"], "ended": j.get("ended"),
                    "exit_code": j.get("exit_code")})
    out.sort(key=lambda x: x["started"], reverse=True)
    return {"ok": True, "jobs": out}

def h_job_log(args):
    jid = args.get("job_id", "")
    j = _JOBS.get(jid)
    if not j:
        return {"ok": False, "error": "unknown job"}
    return {"ok": True, "lines": list(j["log"]), "status": j["status"],
            "progress": j["progress"], "name": j["name"], "color": j["color"]}

def h_job_cancel(args):
    jid = args.get("job_id", "")
    j = _JOBS.get(jid)
    if not j:
        return {"ok": False, "error": "unknown job"}
    proc = j.get("proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate(); proc.wait(timeout=3)
        except Exception:
            try: proc.kill()
            except Exception: pass
        j["status"] = "cancelled"
        _add_job_log(jid, "[cancelled]")
        return {"ok": True}
    return {"ok": False, "error": "job not running"}

HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "network_status": h_network_status,
    "list_external": h_list_external,
    "launch_external": h_launch_external,
    "external_status": h_external_status,

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
    "job_start": h_job_start,
    "job_list": h_job_list,
    "job_log": h_job_log,
    "job_cancel": h_job_cancel,

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
