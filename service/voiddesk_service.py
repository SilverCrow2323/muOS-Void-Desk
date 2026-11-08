#!/usr/bin/env python3
"""
VoidDesk background service — reads .love_request.json,
writes .love_response.json. Minimal, no external deps.
Runs on both muOS (aarch64) and desktop x86_64.
"""
import errno
import fcntl
import json
import os
import platform
import re
import pty
import select
import shlex
import struct
import signal
import shutil
import subprocess
import sys
import termios
import time
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA    = APP_DIR / "data"
REQ     = DATA / ".love_request.json"
PROCESSING = DATA / ".love_request.processing"
RESP    = DATA / ".love_response.json"
RESP_TMP = DATA / ".love_response.tmp"
CFG     = DATA / "desk_config.json"
DATA.mkdir(parents=True, exist_ok=True)

IS_DEVICE = platform.machine().lower() in ("aarch64", "armv7l", "arm64")
# Deterministic, privacy-safe values for the automated LÖVE screenshot pass.
# These values are only used when tools/capture_love_screenshots.py launches
# the service; normal device and desktop sessions keep real system probes.
IS_VISUAL_CAPTURE = os.environ.get("VOIDDESK_VISUAL_CAPTURE") == "1"

# Reuse the existing, already-battle-tested device probing code from the
# pygame engine instead of duplicating wifi/bt detection logic here.
sys.path.insert(0, str(APP_DIR / "desk"))
try:
    import sysinfo as deskinfo
except Exception:
    deskinfo = None

sys.path.insert(0, str(APP_DIR / "service"))
try:
    import tailscale_manager
except Exception:
    tailscale_manager = None

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
        if IS_VISUAL_CAPTURE:
            return {"ok": True, "info": {
                "os": "Linux visual capture",
                "machine": "CI",
                "hostname": "VISUAL-CAPTURE",
                "is_device": False,
                "ip": "—",
                "disk_free_gb": 0.0,
            }}
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

# ── system / network / media status ─────────────────────────
# These were referenced in HANDLERS below but never defined: the whole
# service crashed with a NameError at import time before it could even
# start its main loop, so EVERY bridge.call from the LÖVE frontend
# (including xfce_install) always hit the 10s client-side timeout,
# because no service was ever actually running to answer it.

def _cpu_pct():
    try:
        load1 = os.getloadavg()[0]
        ncpu = os.cpu_count() or 1
        return max(0, min(100, round(load1 / ncpu * 100)))
    except Exception:
        return 0

def _ram_info():
    try:
        vals = {}
        with open("/proc/meminfo") as f:
            for ln in f:
                k, _, v = ln.partition(":")
                if k in ("MemTotal", "MemAvailable"):
                    vals[k] = int(v.strip().split()[0])  # kB
        total_kb = vals.get("MemTotal", 0)
        avail_kb = vals.get("MemAvailable", total_kb)
        used_kb = max(0, total_kb - avail_kb)
        pct = round(used_kb / total_kb * 100) if total_kb else 0
        return {"used_mb": used_kb // 1024, "total_mb": total_kb // 1024,
                "pct": pct}
    except Exception:
        return {"used_mb": 0, "total_mb": 0, "pct": 0}

def _disk_info():
    out = []
    seen = set()
    mounts = ["/"]
    for extra in ("/mnt/mmc", "/mnt/sdcard"):
        if os.path.isdir(extra):
            mounts.append(extra)
    for mount in mounts:
        try:
            du = shutil.disk_usage(mount)
            if du.total in seen:
                continue
            seen.add(du.total)
            pct = round(du.used / du.total * 100) if du.total else 0
            out.append({"mount": mount,
                        "free_gb": round(du.free / 1e9, 1), "pct": pct})
        except Exception:
            continue
    return out

def _uptime_s():
    try:
        return float(open("/proc/uptime").read().split()[0])
    except Exception:
        return 0

def _temp_c():
    for p in ("/sys/class/thermal/thermal_zone0/temp",):
        try:
            v = int(open(p).read().strip())
            return round(v / 1000.0, 1) if v > 1000 else float(v)
        except Exception:
            continue
    return None

def h_system_status(args):
    try:
        if IS_VISUAL_CAPTURE:
            return {"ok": True, "system": {
                "cpu": 12,
                "ram": {"used_mb": 256, "total_mb": 1024, "pct": 25},
                "disk": [{"mount": "/", "free_gb": 12.0, "pct": 50}],
                "uptime_s": 3600,
                "temp_c": None,
                "kernel": "visual-capture",
                "xfce_installed": False,
            }}
        return {"ok": True, "system": {
            "cpu": _cpu_pct(),
            "ram": _ram_info(),
            "disk": _disk_info(),
            "uptime_s": _uptime_s(),
            "temp_c": _temp_c(),
            "kernel": platform.release(),
            "xfce_installed": (DATA / ".xfce_ready").exists(),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _gateway_ip():
    try:
        with open("/proc/net/route") as f:
            for ln in f.readlines()[1:]:
                p = ln.split()
                if len(p) >= 3 and p[1] == "00000000":
                    h = p[2]
                    return ".".join(str(int(h[i:i + 2], 16))
                                   for i in (6, 4, 2, 0))
    except Exception:
        pass
    return ""

def h_network_status(args):
    try:
        if IS_VISUAL_CAPTURE:
            return {"ok": True, "network": {
                "wifi": {"connected": False, "ssid": "OFFLINE",
                         "signal": 0, "ip": "—"},
                "bt": {"on": False, "count": 0},
                "hotspot": {"on": False, "ssid": "—"},
                "info": {"hostname": "VISUAL-CAPTURE", "gateway": "—"},
            }}
        if deskinfo is not None:
            connected, ssid, lvl, _iface, ip = deskinfo.wifi_status()
            bt_on = deskinfo.bt_status()
        else:
            connected, ssid, lvl, ip, bt_on = False, None, None, None, None
        signal_pct = {0: 20, 1: 45, 2: 70, 3: 95}.get(lvl, 0) \
            if lvl is not None else 0
        hs_marker = DATA / ".hotspot_active"
        hotspot_on = hs_marker.exists()
        hotspot_ssid = ""
        if hotspot_on:
            try:
                hotspot_ssid = hs_marker.read_text().strip()
            except Exception:
                pass
        return {"ok": True, "network": {
            "wifi": {"connected": bool(connected), "ssid": ssid or "—",
                     "signal": signal_pct, "ip": ip or "—"},
            "bt": {"on": bool(bt_on), "count": 0},
            "hotspot": {"on": hotspot_on, "ssid": hotspot_ssid or "—"},
            "info": {"hostname": platform.node(),
                     "gateway": _gateway_ip() or "—"},
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _external_tool_target(tool):
    """Resolve a registry launcher without permitting arbitrary path escape."""
    launcher = str(tool.get("launcher") or "")
    kind = tool.get("launcher_type")
    if kind == "portable-voidcast" and launcher == "../VoidCast":
        target = (APP_DIR.parent / "VoidCast").resolve()
        if target.parent == APP_DIR.parent.resolve():
            return target
        return None
    target = (APP_DIR / launcher).resolve()
    try:
        target.relative_to(APP_DIR.resolve())
    except ValueError:
        return None
    return target


def h_list_external(args):
    registry_path = APP_DIR / "external" / "tools.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "error": "cannot read external tools: " + str(exc)}
    tools = []
    for tool in registry.get("tools", []):
        if not isinstance(tool, dict):
            continue
        target = _external_tool_target(tool)
        kind = tool.get("launcher_type")
        if target is None:
            exists = False
        elif kind == "love":
            exists = target.is_file() or (
                target.is_dir() and (target / "main.lua").is_file()
            )
        elif kind == "sh":
            exists = target.is_file()
        elif kind == "portable-voidcast":
            exists = target.is_dir() and (
                (target / "mux_launch.sh").is_file()
                or (target / "voidcast.py").is_file()
            )
        else:
            exists = False
        tools.append({
            "id": str(tool.get("id") or ""),
            "name": str(tool.get("name") or "External tool"),
            "desc": str(tool.get("desc") or ""),
            "hub": str(tool.get("hub") or "system"),
            "native_engine": str(tool.get("native_engine") or ""),
            "launcher_type": str(kind or ""),
            "icon": str(tool.get("icon") or "gear"),
            "exists": exists,
        })
    return {"ok": True, "tools": tools}


def h_launch_external(args):
    tool_id = str(args.get("id") or "")
    return h_job_start({
        "tool_id": tool_id,
        "name": "External: " + tool_id,
        "hub": "external",
    })


def h_toolbox_stats(args):
    """Read-only counts for the LÖVE Toolbox dashboard."""
    notes_dir = DATA / "notes"
    texts_dir = DATA / "Texts"
    text_exts = {
        ".txt", ".md", ".log", ".cfg", ".ini", ".json", ".csv",
        ".yml", ".yaml", ".sh", ".conf", ".xml",
    }

    def count_files(directory, allowed=None):
        try:
            with os.scandir(directory) as entries:
                return sum(
                    1 for entry in entries
                    if entry.is_file(follow_symlinks=False)
                    and (allowed is None or
                         Path(entry.name).suffix.lower() in allowed)
                )
        except OSError:
            return 0

    return {
        "ok": True,
        "notes_count": count_files(notes_dir, {".txt"}),
        "text_files": count_files(texts_dir, text_exts),
    }


def h_calendar_events(args):
    """Return month-scoped events in the shape expected by LÖVE Calendar."""
    try:
        year = int(args.get("year"))
        month = int(args.get("month"))
        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid calendar year or month"}

    path = DATA / "calendar.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw = []
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": "cannot read calendar: " + str(exc)}

    if not isinstance(raw, list):
        return {"ok": False, "error": "calendar data must be a list"}

    from datetime import date
    events = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            event_date = date(
                int(item["y"]), int(item["mo"]), int(item["d"])
            )
            hour = max(0, min(23, int(item.get("h", 0))))
            minute = max(0, min(59, int(item.get("mi", 0))))
            importance = max(0, min(2, int(item.get("imp", 0))))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if event_date.year != year or event_date.month != month:
            continue
        key = event_date.strftime("%Y-%m-%d")
        events.setdefault(key, []).append({
            "title": str(item.get("t") or "Untitled event")[:160],
            "category": "personal",
            "hour": hour,
            "minute": minute,
            "importance": importance,
        })

    for day_events in events.values():
        day_events.sort(key=lambda event: (event["hour"], event["minute"]))
    return {"ok": True, "events": events}


# One interactive PTY is shared by the LÖVE terminal scene.
_SHELL_MASTER = None
_SHELL_PROC = None


def h_shell_start(args):
    global _SHELL_MASTER, _SHELL_PROC
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "interactive shell disabled during visual capture"}
    if _SHELL_PROC is not None and _SHELL_PROC.poll() is None:
        return {"ok": True, "already_running": True}
    if _SHELL_MASTER is not None:
        try:
            os.close(_SHELL_MASTER)
        except OSError:
            pass
        _SHELL_MASTER = None
    master = slave = None
    try:
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ,
                    struct.pack("HHHH", 24, 80, 0, 0))
        shell = os.environ.get("SHELL") or "/bin/sh"
        if not os.path.isfile(shell):
            shell = "/bin/sh"
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        process = subprocess.Popen(
            [shell], stdin=slave, stdout=slave, stderr=slave,
            cwd=str(APP_DIR), env=env, close_fds=True,
            start_new_session=True,
        )
        os.close(slave)
        slave = None
        flags = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        _SHELL_MASTER = master
        _SHELL_PROC = process
        return {"ok": True, "pid": process.pid}
    except (OSError, ValueError) as exc:
        for fd in (master, slave):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        return {"ok": False, "error": "cannot start shell: " + str(exc)}


def h_shell_poll(args):
    if _SHELL_MASTER is None or _SHELL_PROC is None:
        return {"ok": False, "error": "shell is not running"}
    chunks = []
    total = 0
    try:
        readable, _, _ = select.select([_SHELL_MASTER], [], [], 0)
        if readable:
            while total < 32768:
                try:
                    chunk = os.read(_SHELL_MASTER, min(8192, 32768 - total))
                except BlockingIOError:
                    break
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": "shell poll failed: " + str(exc)}
    return {
        "ok": True,
        "output": b"".join(chunks).decode("utf-8", errors="replace"),
        "running": _SHELL_PROC.poll() is None,
    }


def h_shell_send(args):
    if _SHELL_MASTER is None or _SHELL_PROC is None:
        return {"ok": False, "error": "shell is not running"}
    if _SHELL_PROC.poll() is not None:
        return {"ok": False, "error": "shell process has exited"}
    payload = str(args.get("text") or "")[:8192].encode(
        "utf-8", errors="replace"
    )
    try:
        sent = os.write(_SHELL_MASTER, payload)
        return {"ok": True, "bytes_written": sent}
    except OSError as exc:
        return {"ok": False, "error": "shell write failed: " + str(exc)}


def h_shell_kill(args):
    global _SHELL_MASTER, _SHELL_PROC
    process = _SHELL_PROC
    if process is not None and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (AttributeError, ProcessLookupError, PermissionError, OSError):
            try:
                process.terminate()
            except OSError:
                pass
    if _SHELL_MASTER is not None:
        try:
            os.close(_SHELL_MASTER)
        except OSError:
            pass
    _SHELL_MASTER = None
    _SHELL_PROC = None
    return {"ok": True}


# Background jobs are process-local: a service restart clears the live
# process table, while each job's log remains available under data/.
_JOBS = {}
_JOB_SEQ = 0
_ALLOWED_JOB_PACKAGES = {"htop", "ncdu", "ffmpeg", "curl"}
_APT_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,127}$")
_APT_ACTIONS = {"update", "upgrade", "clean", "install", "remove"}
_APT_CATALOG_MODES = {"search", "installed", "info"}


def _valid_apt_packages(values):
    return (isinstance(values, list) and 1 <= len(values) <= 20
            and all(isinstance(value, str) and _APT_PACKAGE_RE.fullmatch(value)
                    for value in values))


def h_apt_catalog(args):
    """Read package metadata from the Debian/Ubuntu XFCE chroot, never host APT."""
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "mode": str(args.get("mode") or "search"),
                "packages": [], "note": "visual capture fixture"}
    mode = str(args.get("mode") or "search")
    if mode not in _APT_CATALOG_MODES:
        return {"ok": False, "error": "unsupported catalog mode"}
    script = APP_DIR / "bin" / "vd_apt_manage.py"
    if not script.is_file():
        return {"ok": False, "error": "APT manager is missing"}
    command = [sys.executable, str(script), "catalog", mode]
    if mode == "search":
        query = str(args.get("query") or "").strip()[:80]
        if not query or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 +_.-]*", query):
            return {"ok": False, "error": "search query contains unsupported characters"}
        command.append(query)
    elif mode == "info":
        packages = args.get("packages")
        if not _valid_apt_packages(packages):
            return {"ok": False, "error": "one to twenty valid package names are required"}
        command.extend(packages)
    elif args.get("packages"):
        return {"ok": False, "error": "installed mode takes no package arguments"}
    try:
        result = subprocess.run(command, cwd=str(APP_DIR), capture_output=True,
                                text=True, timeout=35, check=False)
        output = (result.stdout or "")[-24000:]
        if result.returncode:
            return {"ok": False, "error": (result.stderr or output or
                    "APT catalog query failed")[-600:]}
        packages = []
        for line in output.splitlines():
            if mode == "search":
                name, sep, description = line.partition(" - ")
                if sep and _APT_PACKAGE_RE.fullmatch(name.strip()):
                    packages.append({"name": name.strip(),
                                     "description": description.strip()[:240]})
            elif mode == "installed":
                name, sep, version = line.partition("\t")
                if sep and _APT_PACKAGE_RE.fullmatch(name.strip().split(":", 1)[0]):
                    packages.append({"name": name.strip(), "version": version.strip()})
        return {"ok": True, "mode": mode, "packages": packages[:100],
                "details": output if mode == "info" else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "APT catalog query timed out"}
    except OSError as exc:
        return {"ok": False, "error": "cannot run APT catalog: " + str(exc)}




def _job_refresh(job):
    process = job.get("process")
    if job["status"] == "running" and process is not None:
        code = process.poll()
        if code is not None:
            job["status"] = "done" if code == 0 else "error"
            job["progress"] = 100 if code == 0 else 0
            job["exit_code"] = code
    return job


def _job_public(job):
    _job_refresh(job)
    return {
        "id": job["id"],
        "name": job["name"],
        "hub": job["hub"],
        "status": job["status"],
        "started": job["started"],
        "progress": job["progress"],
        "color": [0.45, 0.72, 0.95],
    }


def h_job_start(args):
    """Start only allowlisted package jobs or registered external tools."""
    global _JOB_SEQ
    command = None
    cwd = APP_DIR
    cmd_text = args.get("cmd")
    tool_id = args.get("tool_id")

    apt_action = args.get("apt_action")
    if apt_action is not None:
        action = str(apt_action)
        if action not in _APT_ACTIONS:
            return {"ok": False, "error": "APT action is not allowlisted"}
        packages = args.get("packages", [])
        if action in ("install", "remove"):
            if not _valid_apt_packages(packages):
                return {"ok": False, "error": "one to twenty valid package names are required"}
        elif packages:
            return {"ok": False, "error": "this APT action takes no package arguments"}
        script = APP_DIR / "bin" / "vd_apt_manage.py"
        if not script.is_file():
            return {"ok": False, "error": "APT manager is missing"}
        command = [sys.executable, str(script), action] + list(packages)
    elif cmd_text:
        try:
            tokens = shlex.split(str(cmd_text))
        except ValueError as exc:
            return {"ok": False, "error": "invalid command: " + str(exc)}
        if (len(tokens) != 3 or tokens[:2] !=
                ["sh", "bin/vd_apt_install.sh"] or
                tokens[2] not in _ALLOWED_JOB_PACKAGES):
            return {"ok": False, "error": "command is not allowlisted"}
        script = APP_DIR / "bin" / "vd_apt_install.sh"
        if not script.is_file():
            return {"ok": False, "error": "package installer is missing"}
        command = ["sh", str(script), tokens[2]]
    elif args.get("service_task") == "tailscale_start":
        script = APP_DIR / "service" / "tailscale_job.py"
        if not script.is_file():
            return {"ok": False, "error": "Tailscale service job is missing"}
        command = [sys.executable, str(script)]
    elif tool_id:
        try:
            registry = json.loads(
                (APP_DIR / "external" / "tools.json").read_text(
                    encoding="utf-8"
                )
            )
            tool = next(
                (item for item in registry.get("tools", [])
                 if item.get("id") == str(tool_id)),
                None,
            )
        except (OSError, ValueError, TypeError) as exc:
            return {"ok": False, "error": "cannot read external tools: " + str(exc)}
        if not tool:
            return {"ok": False, "error": "unknown external tool"}
        launcher_type = tool.get("launcher_type")
        launcher = tool.get("launcher", "")
        if launcher_type == "portable-voidcast":
            if launcher != "../VoidCast":
                return {"ok": False, "error": "external tool path is not allowlisted"}
            target = (APP_DIR.parent / "VoidCast").resolve()
            if target.parent != APP_DIR.parent.resolve() or not target.is_dir():
                return {"ok": False, "error": "VoidCast is not installed"}
            shell_launcher = target / "mux_launch.sh"
            python_launcher = target / "voidcast.py"
            if shell_launcher.is_file():
                command = ["sh", str(shell_launcher)]
            elif python_launcher.is_file():
                command = [sys.executable, str(python_launcher)]
            else:
                return {"ok": False, "error": "VoidCast launcher is missing"}
            cwd = target
        else:
            target = (APP_DIR / launcher).resolve()
            try:
                target.relative_to(APP_DIR.resolve())
            except ValueError:
                return {"ok": False, "error": "external tool path escapes app directory"}
            if launcher_type == "love":
                if not target.is_file() and not (
                    target.is_dir() and (target / "main.lua").is_file()
                ):
                    return {"ok": False, "error": "external tool is not installed"}
                love_bin = APP_DIR / "lib" / "love"
                love_exec = str(love_bin) if love_bin.is_file() else shutil.which("love")
                if not love_exec:
                    return {"ok": False, "error": "LÖVE runtime is not installed"}
                command = [love_exec, str(target)]
                cwd = target if target.is_dir() else target.parent
            elif launcher_type == "sh":
                if not target.is_file():
                    return {"ok": False, "error": "external launcher is not installed"}
                command = ["sh", str(target)]
                cwd = target.parent
            else:
                return {"ok": False, "error": "unsupported external launcher type"}
    else:
        return {"ok": False, "error": "job requires cmd or tool_id"}

    _JOB_SEQ += 1
    job_id = str(_JOB_SEQ)
    name = str(args.get("name") or tool_id or "Background job")[:80]
    hub = str(args.get("hub") or "system")[:32]
    log_path = DATA / ("love_job_%s.log" % job_id)
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                command, cwd=str(cwd), stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as exc:
        return {"ok": False, "error": "cannot start job: " + str(exc)}

    job = {
        "id": job_id,
        "name": name,
        "hub": hub,
        "status": "running",
        "started": time.time(),
        "progress": 0,
        "process": process,
        "log_path": log_path,
    }
    _JOBS[job_id] = job
    return {"ok": True, "job": _job_public(job)}


def h_job_list(args):
    jobs = [_job_public(job) for job in _JOBS.values()]
    jobs.sort(key=lambda job: job["started"], reverse=True)
    return {"ok": True, "jobs": jobs}


def h_job_cancel(args):
    job = _JOBS.get(str(args.get("job_id", "")))
    if not job:
        return {"ok": False, "error": "unknown job"}
    _job_refresh(job)
    if job["status"] != "running":
        return {"ok": True, "status": job["status"]}
    process = job.get("process")
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (AttributeError, ProcessLookupError, PermissionError, OSError):
            try:
                process.terminate()
            except OSError:
                pass
    job["status"] = "cancelled"
    return {"ok": True, "status": "cancelled"}


def h_job_log(args):
    job = _JOBS.get(str(args.get("job_id", "")))
    if not job:
        return {"ok": False, "error": "unknown job"}
    try:
        lines = job["log_path"].read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()[-160:]
    except OSError:
        lines = []
    return {"ok": True, "lines": lines}


def h_media_status(args):
    try:
        if IS_VISUAL_CAPTURE:
            return {"ok": True, "media": {
                "volume": 40,
                "now_playing": None,
                "library_count": 0,
                "recordings": 0,
            }}
        vol = deskinfo.volume() if deskinfo is not None else None
        return {"ok": True, "media": {
            "volume": vol if vol is not None else 0,
            "now_playing": None,
            "library_count": 0,
            "recordings": 0,
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_hotspot_toggle(args):
    dcheck = device_only("hotspot_toggle")
    if dcheck:
        return dcheck
    active = (DATA / ".hotspot_active").exists()
    script = APP_DIR / "bin" / \
        ("vd_hotspot_stop.sh" if active else "vd_hotspot_start.sh")
    try:
        r = subprocess.run(["sh", str(script)], capture_output=True,
                           text=True, timeout=20)
        now_on = (DATA / ".hotspot_active").exists()
        if r.returncode == 0:
            return {"ok": True, "state": "on" if now_on else "off"}
        return {"ok": False,
                "error": (r.stderr or r.stdout or "hotspot script failed")[-300:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "hotspot script timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_wifi_scan(args):
    if not IS_DEVICE:
        return {"ok": True, "networks": []}
    nets, seen = [], set()
    try:
        if shutil.which("nmcli"):
            r = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev",
                 "wifi", "list"], capture_output=True, text=True, timeout=15)
            for ln in r.stdout.splitlines():
                p = ln.split(":")
                if p and p[0] and p[0] not in seen:
                    seen.add(p[0])
                    nets.append({
                        "ssid": p[0],
                        "signal": int(p[1]) if len(p) > 1 and p[1].isdigit() else 0,
                        "secure": bool(p[2]) if len(p) > 2 else True})
        elif shutil.which("iwlist") and deskinfo is not None:
            ifs = deskinfo.wireless_ifaces() or ["wlan0"]
            r = subprocess.run(["iwlist", ifs[0], "scan"],
                               capture_output=True, text=True, timeout=15)
            for ln in r.stdout.splitlines():
                ln = ln.strip()
                if ln.startswith("ESSID:"):
                    ssid = ln.split(":", 1)[1].strip('"')
                    if ssid and ssid not in seen:
                        seen.add(ssid)
                        nets.append({"ssid": ssid, "signal": 0, "secure": True})
        else:
            return {"ok": False, "error": "no nmcli/iwlist available"}
        return {"ok": True, "networks": nets}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "scan timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_bt_scan(args):
    if not IS_DEVICE:
        return {"ok": True, "devices": []}
    if not shutil.which("bluetoothctl"):
        return {"ok": False, "error": "bluetoothctl not found"}
    devs = []
    try:
        try:
            subprocess.run(["bluetoothctl", "scan", "on"],
                           capture_output=True, text=True, timeout=2.5)
        except subprocess.TimeoutExpired:
            pass  # expected: "scan on" blocks until stopped
        subprocess.run(["bluetoothctl", "scan", "off"],
                       capture_output=True, text=True, timeout=3)
        r = subprocess.run(["bluetoothctl", "devices"],
                           capture_output=True, text=True, timeout=3)
        for ln in r.stdout.splitlines():
            p = ln.split(" ", 2)
            if len(p) == 3 and p[0] == "Device":
                devs.append({"mac": p[1], "name": p[2]})
        return {"ok": True, "devices": devs}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# bin/xfce_launch.sh is the ONE shared launcher for all three desktop
# environments already — it reads "desk_env" from desk_config.json and
# falls back to xfce if the chosen one isn't actually installed in the
# chroot (see its DESKENV case block). So "adding" icewm/lxde support
# here is: report their own install markers, and on launch write
# desk_env + drop the SAME pending-session hand-off xfce already uses
# (xfce_launch.sh itself decides what to start from desk_env).
ENV_MARKERS = {
    "xfce": ".xfce_ready",
    "icewm": ".icewm_ready",
    "lxde": ".lxde_ready",
}
ENV_NAMES = {"xfce": "XFCE", "icewm": "IceWM", "lxde": "LXDE"}

def h_session_list(args):
    try:
        return {"ok": True, "sessions": [
            {"id": eid, "name": ENV_NAMES[eid],
             "installed": (DATA / marker).exists()}
            for eid, marker in ENV_MARKERS.items()
        ]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_session_launch(args):
    sess_id = args.get("id")
    if sess_id not in ENV_MARKERS:
        return {"ok": False, "error": f"unknown session: {sess_id}"}
    if not (DATA / ENV_MARKERS[sess_id]).exists():
        return {"ok": False, "error": f"{ENV_NAMES[sess_id]} not installed"}
    if IS_DEVICE:
        # The service process can't itself hand over the framebuffer/X
        # session — it's a background helper, not the thing holding the
        # screen. The actual hand-off has to happen at the level that
        # DOES own the screen: mux_launch.sh, which starts the LÖVE
        # process in the first place. So instead of trying (and failing)
        # to take the display from here, write which environment was
        # picked, drop a "pending session" marker and ask LÖVE to quit
        # cleanly; mux_launch.sh notices the marker after LÖVE exits,
        # runs bin/xfce_launch.sh to completion (full screen, no
        # conflict with LÖVE since LÖVE is gone by then — that one
        # script starts whichever env desk_env says), and relaunches
        # the engine afterwards. See mux_launch.sh for the other half.
        try:
            cfg = {}
            if CFG.exists():
                try:
                    cfg = json.loads(CFG.read_text())
                except Exception:
                    cfg = {}
            cfg["desk_env"] = sess_id
            CFG.write_text(json.dumps(cfg, indent=1))
            (DATA / ".pending_session").write_text(sess_id)
            return {"ok": True, "handoff": True,
                    "note": f"handing off to {ENV_NAMES[sess_id]} — VoidDesk "
                            "will restart automatically when you log out"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if sess_id != "xfce":
        return {"ok": False, "error": "PC path only supports XFCE for now"}
    return h_xfce_launch(args)

def h_env_install(args):
    """Install icewm or lxde into the existing XFCE chroot (device only —
    there's no PC-side equivalent, those run XFCE itself via apt/Xephyr)."""
    env_id = args.get("id")
    if env_id not in ("icewm", "lxde"):
        return {"ok": False, "error": f"unknown env: {env_id}"}
    dcheck = device_only("env_install")
    if dcheck:
        return dcheck
    if not (DATA / ".xfce_ready").exists():
        return {"ok": False, "error": "install XFCE first — this adds onto it"}
    marker = DATA / ENV_MARKERS[env_id]
    if marker.exists():
        return {"ok": True, "already": True,
                "note": f"{ENV_NAMES[env_id]} already installed"}
    lock = DATA / f".{env_id}_install_running"
    if lock.exists():
        try:
            os.kill(int(lock.read_text().strip()), 0)
            return {"ok": True, "note": "install already running in background"}
        except Exception:
            try: lock.unlink()
            except OSError: pass
    try:
        log_path = DATA / f"{env_id}_install.log"
        with open(log_path, "ab") as lf:
            proc = subprocess.Popen(
                [sys.executable, str(APP_DIR / "bin" / "env_install.py"), env_id],
                stdout=lf, stderr=lf, start_new_session=True)
        lock.write_text(str(proc.pid))
        return {"ok": True,
                "note": f"installing {ENV_NAMES[env_id]} in background — "
                        f"progress in data/{env_id}_install.log"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_voidcast_launch(args):
    """Launch the bundled VoidCast IPTV app (outdesk/VoidCast). Same
    quit-and-handoff trick as session_launch, minus the install check —
    it ships inside VoidDesk itself, no separate chroot/package needed."""
    dcheck = device_only("voidcast_launch")
    if dcheck:
        return dcheck
    script = APP_DIR / "outdesk" / "VoidCast" / "voidcast" / "main.py"
    if not script.exists():
        return {"ok": False, "error": "outdesk/VoidCast/voidcast/main.py missing"}
    try:
        (DATA / ".pending_session").write_text("voidcast")
        return {"ok": True, "handoff": True,
                "note": "handing off to VoidCast — VoidDesk will restart "
                        "automatically when you quit it"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_apt_update(args):
    if IS_DEVICE:
        if not (DATA / ".xfce_ready").exists():
            return {"ok": False, "error": "XFCE not installed"}
        try:
            log_path = DATA / "apt_update.log"
            with open(log_path, "ab") as lf:
                subprocess.Popen(
                    [sys.executable, str(APP_DIR / "bin" / "xfce_update.py")],
                    stdout=lf, stderr=lf, start_new_session=True)
            return {"ok": True, "note": "update started in background — "
                                        "see data/apt_update.log"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    try:
        r = subprocess.run(["pkexec", "apt-get", "update"],
                           capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            return {"ok": True, "note": "apt cache updated"}
        return {"ok": False, "error": (r.stderr or r.stdout)[-300:]}
    except subprocess.TimeoutExpired:
        return {"ok": True, "note": "update still running in background"}
    except FileNotFoundError:
        return {"ok": False, "error": "pkexec missing"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def h_xfce_install(args):
    """Install XFCE:
       - on device: kicks off bin/xfce_bootstrap.py in the background
         (a real 10-20 min install needing network + ~5GB free) instead
         of the previous stub that always reported fake success without
         installing anything.
       - on PC: apt install xfce4 + Xephyr via pkexec (GUI prompt),
         also backgrounded so a long install can't block the whole
         service (and therefore every other status query) for minutes."""
    lock = DATA / ".xfce_install_running"
    if IS_DEVICE:
        if (DATA / ".xfce_ready").exists():
            return {"ok": True, "already": True, "note": "XFCE already installed"}
        if lock.exists():
            try:
                os.kill(int(lock.read_text().strip()), 0)
                return {"ok": True, "note": "install already running in background"}
            except Exception:
                try: lock.unlink()
                except OSError: pass
        try:
            log_path = DATA / "xfce_bootstrap.log"
            with open(log_path, "ab") as lf:
                proc = subprocess.Popen(
                    [sys.executable, str(APP_DIR / "bin" / "xfce_bootstrap.py")],
                    stdout=lf, stderr=lf, start_new_session=True)
            lock.write_text(str(proc.pid))
            return {"ok": True,
                    "note": "install started in background (10-20 min) — "
                            "progress in data/xfce_bootstrap.log"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if shutil.which("startxfce4"):
        return {"ok": True, "already": True, "note": "XFCE already installed"}
    try:
        log_path = DATA / "xfce_pc_install.log"
        with open(log_path, "ab") as lf:
            subprocess.Popen(
                ["pkexec", "apt-get", "install", "-y", "--no-install-recommends",
                 "xfce4", "xfce4-terminal", "xserver-xephyr"],
                stdout=lf, stderr=lf, start_new_session=True)
        return {"ok": True, "note": "install started in background — "
                                    "check data/xfce_pc_install.log"}
    except FileNotFoundError:
        return {"ok": False, "error": "pkexec missing — install polkit (sudo apt install pkexec)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

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
        # bin/xfce_launch.sh takes over the console's framebuffer/X for a
        # full session hand-off (like mux_launch.sh choosing py vs love),
        # which is not something a background JSON bridge call can do
        # safely. Previously this silently reported fake success instead.
        return {"ok": False,
                "error": "device session hand-off not wired yet (needs "
                         "mux_launch.sh integration, see bin/xfce_launch.sh)"}

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


def h_tailscale_status(args):
    """Read-only status from the bundled Rt:Tailscale-M service manager."""
    if IS_VISUAL_CAPTURE:
        return {
            "ok": True, "installed": True, "available": True,
            "backend": "Running", "daemon": True, "panel": False,
            "watchdog": True, "taildrop_enabled": True, "autostart": True,
            "version": "3.0.6", "tailscale_version": "1.80.0",
            "auth_url": "https://login.tailscale.com/a/voiddesk-visual-fixture",
            "tailnet": "visual-fixture.ts.net",
            "self": {"name": "voiddesk-handheld", "ips": ["100.64.0.10"],
                     "online": True, "user": "fixture@example.test"},
            "peers": [
                {"name": "desktop-pc", "ip": "100.64.0.20",
                 "online": True, "exit_node": True, "using": False,
                 "os": "linux", "user": "fixture@example.test"},
                {"name": "home-server", "ip": "100.64.0.30",
                 "online": False, "exit_node": False, "using": False,
                 "os": "linux", "user": "fixture@example.test"},
            ],
            "taildrop": [{"name": "save-backup.zip", "size": 4096,
                          "mtime": 0}],
            "urls": [],
        }
    if tailscale_manager is None:
        return {"ok": False, "error": "Tailscale service adapter unavailable"}
    return tailscale_manager.status(APP_DIR)


def h_tailscale_action(args):
    """Allowlisted operations delegated to Rt:Tailscale-M's own manager."""
    if tailscale_manager is None:
        return {"ok": False, "error": "Tailscale service adapter unavailable"}
    action = str(args.get("action") or "")
    value = str(args.get("value") or "")
    if action == "start":
        return h_job_start({
            "service_task": "tailscale_start",
            "name": "Rt:Tailscale-M setup and start",
            "hub": "uplink",
        })
    return tailscale_manager.action(APP_DIR, action, value)


HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "network_status": h_network_status,
    "system_status": h_system_status,
    "shell_start": h_shell_start,
    "shell_poll": h_shell_poll,
    "shell_send": h_shell_send,
    "shell_kill": h_shell_kill,
    "apt_catalog": h_apt_catalog,
    "job_start": h_job_start,
    "job_list": h_job_list,
    "job_cancel": h_job_cancel,
    "job_log": h_job_log,
    "media_status": h_media_status,
    "list_external": h_list_external,
    "launch_external": h_launch_external,
    "toolbox_stats": h_toolbox_stats,
    "calendar_events": h_calendar_events,
    "hotspot_toggle": h_hotspot_toggle,
    "tailscale_status": h_tailscale_status,
    "tailscale_action": h_tailscale_action,

    "session_list": h_session_list,
    "session_launch": h_session_launch,
    "wifi_scan": h_wifi_scan,
    "bt_scan": h_bt_scan,

    "list_files": h_list_files,
    "xfce_install": h_xfce_install,
    "xfce_launch": h_xfce_launch,
    "apt_update": h_apt_update,
    "env_install": h_env_install,
    "voidcast_launch": h_voidcast_launch,
}

# ── main loop ────────────────────────────────────────────
def main():
    log(f"started  machine={platform.machine()}  device={IS_DEVICE}")
    log(f"req={REQ}  resp={RESP}")
    # A previous service process may have been interrupted mid-request.
    # Its claim file is no longer owned by a live worker.
    try:
        PROCESSING.unlink(missing_ok=True)
    except OSError as e:
        log(f"cannot clear stale processing file: {e}")

    while True:
        try:
            # Claim the request with an atomic rename. Unlike mtime polling,
            # this works on FAT/exFAT volumes where timestamps have coarse
            # resolution and two quick requests can share the same mtime.
            try:
                REQ.replace(PROCESSING)
            except FileNotFoundError:
                time.sleep(0.05)
                continue

            try:
                req = json.loads(PROCESSING.read_text())
                if not isinstance(req, dict):
                    raise ValueError("request must be a JSON object")
                cmd = req.get("cmd", "")
                args = req.get("args", {})
                rid = req.get("id", 0)
                if not isinstance(args, dict):
                    args = {}
                fn = HANDLERS.get(cmd)
                try:
                    resp = fn(args) if fn else {
                        "ok": False, "error": f"unknown cmd: {cmd}"
                    }
                except Exception:
                    resp = {
                        "ok": False,
                        "error": traceback.format_exc(limit=3),
                    }
                if not isinstance(resp, dict):
                    resp = {"ok": False, "error": "handler returned invalid response"}
                resp["id"] = rid
            except Exception:
                resp = {
                    "ok": False,
                    "error": traceback.format_exc(limit=3),
                    "id": 0,
                }

            # Publish a complete response atomically; the LÖVE side never
            # observes a partially written JSON document.
            RESP_TMP.write_text(json.dumps(resp))
            RESP_TMP.replace(RESP)
        except OSError as e:
            log(f"request loop error: {e}")
            time.sleep(0.1)
        except Exception as e:
            log(f"loop error: {e}")
            time.sleep(0.1)
        finally:
            try:
                PROCESSING.unlink(missing_ok=True)
            except OSError:
                pass

if __name__ == "__main__":
    main()
