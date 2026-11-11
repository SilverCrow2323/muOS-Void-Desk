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
import urllib.error
import urllib.request
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

# Supported muOS application roots. The service never accepts a caller-provided root.
MUOS_APP_ROOTS = (
    Path("/mnt/mmc/MUOS/application"),
    Path("/mnt/sdcard/MUOS/application"),
)

# Reuse the existing, already-battle-tested device probing code from the
# pygame engine instead of duplicating wifi/bt detection logic here.
sys.path.insert(0, str(APP_DIR / "desk"))
try:
    import sysinfo as deskinfo
except Exception:
    deskinfo = None

try:
    import syncthing as syncthing_discovery
    import syncthing_api
except Exception:
    syncthing_discovery = None
    syncthing_api = None

sys.path.insert(0, str(APP_DIR / "service"))
try:
    import tailscale_manager
except Exception:
    tailscale_manager = None

try:
    import iptv_module
    iptv_module.APP_DIR = APP_DIR
except Exception:
    iptv_module = None

try:
    import media_module
    media_module.configure(APP_DIR)
except Exception:
    media_module = None

MEDIA_ROOT_CANDIDATES = (
    (Path("/mnt/mmc"), "SD1"),
    (Path("/mnt/sdcard"), "SD2"),
    (DATA, "Void Desk Data"),
)
MEDIA_AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus",
}
MEDIA_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v",
}
MEDIA_EXTENSIONS = MEDIA_AUDIO_EXTENSIONS | MEDIA_VIDEO_EXTENSIONS | {".m3u", ".m3u8"}

_IPTV_CHANNELS = []
_IPTV_EPG = {}
_IPTV_ALLOWED_EPG_URLS = set()
_IPTV_DEFAULT_CONFIG = {
    "playlist_url": "https://iptv-org.github.io/iptv/countries/it.m3u",
    "epg_urls": [],
}

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

def h_gh_fetch_releases(args):
    """Return a bounded, public release summary for the Void Desk UI."""
    if IS_VISUAL_CAPTURE:
        return {
            "ok": True, "tag": None, "name": "Visual capture",
            "url": None, "releases": [], "status": "visual-fixture",
        }

    url = ("https://api.github.com/repos/"
           "SilverCrow2323/Void-Desk-Project/releases?per_page=5")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VoidDesk-Love/10.5",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "error": "GitHub release lookup failed: " + str(exc)[:120]}
    if not isinstance(payload, list):
        return {"ok": False, "error": "GitHub returned an unexpected release catalogue"}

    releases = []
    for item in payload[:5]:
        if not isinstance(item, dict) or item.get("draft"):
            continue
        releases.append({
            "tag": str(item.get("tag_name") or "")[:80],
            "name": str(item.get("name") or item.get("tag_name") or "Release")[:120],
            "url": str(item.get("html_url") or "")[:300],
            "published_at": str(item.get("published_at") or "")[:40],
            "prerelease": bool(item.get("prerelease")),
            "notes": str(item.get("body") or "")[:500],
        })

    latest = releases[0] if releases else None
    return {
        "ok": True,
        "tag": latest["tag"] if latest else None,
        "name": latest["name"] if latest else "No published releases",
        "url": latest["url"] if latest else None,
        "published_at": latest["published_at"] if latest else None,
        "releases": releases,
        "status": "available" if latest else "empty",
    }


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



def _muos_app_entries():
    """Discover direct-child muOS applications from the two supported SD roots."""
    entries = []
    current_app = APP_DIR.resolve()
    for root_index, root in enumerate(MUOS_APP_ROOTS, start=1):
        try:
            root_real = root.resolve(strict=True)
            if not root_real.is_dir():
                continue
            children = sorted(root_real.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue

        for child in children:
            try:
                if child.is_symlink() or not child.is_dir():
                    continue
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}", child.name):
                    continue
                app_dir = child.resolve(strict=True)
                if app_dir.parent != root_real or app_dir == current_app:
                    continue
                if child.name.lower().startswith("voiddesk"):
                    continue
                launcher = app_dir / "mux_launch.sh"
                if launcher.is_symlink() or not launcher.is_file():
                    continue
                if not os.access(str(launcher), os.X_OK):
                    continue

                help_text = ""
                try:
                    with launcher.open("r", encoding="utf-8", errors="replace") as handle:
                        for line in handle.read(800).splitlines():
                            if line.strip().upper().startswith("# HELP:"):
                                help_text = line.split(":", 1)[1].strip()[:80]
                                break
                except OSError:
                    pass

                entries.append({
                    "name": child.name,
                    "path": str(app_dir),
                    "sd": "SD%d" % root_index,
                    "help": help_text,
                })
            except OSError:
                continue
    return entries


def h_list_muos_apps(args):
    """List only launchable applications from the fixed SD1/SD2 muOS roots."""
    if IS_VISUAL_CAPTURE:
        return {
            "ok": True, "apps": [], "source": "visual capture fixture",
        }
    blocked = device_only("list_muos_apps")
    if blocked:
        return blocked
    apps = _muos_app_entries()
    return {
        "ok": True,
        "apps": apps,
        "source": "SD1 + SD2",
        "count": len(apps),
    }


def h_launch_muos_app(args):
    """Request a launcher hand-off for one app rediscovered from fixed roots."""
    blocked = device_only("launch_muos_app")
    if blocked:
        return blocked
    requested_path = args.get("path")
    if not isinstance(requested_path, str) or not requested_path:
        return {"ok": False, "error": "an application path from the scan is required"}

    match = next(
        (entry for entry in _muos_app_entries()
         if entry["path"] == requested_path),
        None,
    )
    if not match:
        return {"ok": False, "error": "application is no longer available or is outside supported roots"}

    marker = DATA / ".muos_app"
    if marker.exists():
        return {"ok": False, "error": "another application hand-off is already pending"}
    temporary = DATA / ".muos_app.tmp"
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            match["path"] + "\n" + match["name"] + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, marker)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": False, "error": "cannot queue application hand-off: " + str(exc)}

    return {
        "ok": True,
        "handoff": True,
        "name": match["name"],
        "note": "Returning to muOS launcher to start " + match["name"],
    }

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

def _iptv_config():
    """Read only the non-secret IPTV feed settings used by the LÖVE frontend."""
    path = DATA / "iptv_config.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    playlist_url = data.get("playlist_url")
    try:
        playlist_url = iptv_module.validate_feed_url(
            playlist_url, resolve=False
        ) if iptv_module is not None else None
    except ValueError:
        playlist_url = None
    if not playlist_url:
        playlist_url = _IPTV_DEFAULT_CONFIG["playlist_url"]

    epg_urls = []
    configured = data.get("epg_urls", [])
    if isinstance(configured, list) and iptv_module is not None:
        for candidate in configured[:8]:
            try:
                safe = iptv_module.validate_feed_url(candidate, resolve=False)
            except (TypeError, ValueError):
                continue
            if safe not in epg_urls:
                epg_urls.append(safe)

    return {"playlist_url": playlist_url, "epg_urls": epg_urls}


def h_iptv_get_config(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "config": dict(_IPTV_DEFAULT_CONFIG)}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    return {"ok": True, "config": _iptv_config()}


def h_iptv_load_playlist(args):
    global _IPTV_CHANNELS, _IPTV_ALLOWED_EPG_URLS, _IPTV_EPG
    if IS_VISUAL_CAPTURE:
        _IPTV_CHANNELS = [
            {"name": "News Fixture", "url": "https://stream.example.test/news.m3u8",
             "tvg_id": "news.example.test", "tvg_name": "News Fixture",
             "logo": "", "group": "News", "index": 0},
            {"name": "Culture Fixture", "url": "https://stream.example.test/culture.m3u8",
             "tvg_id": "culture.example.test", "tvg_name": "Culture Fixture",
             "logo": "", "group": "Culture", "index": 1},
        ]
        _IPTV_ALLOWED_EPG_URLS = set()
        _IPTV_EPG = {}
        return {"ok": True, "channels": _IPTV_CHANNELS,
                "groups": ["News", "Culture"], "epg_urls": [], "count": 2}

    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    url = args.get("url")
    try:
        safe_url = iptv_module.validate_feed_url(url)
        playlist = iptv_module.fetch_text(safe_url, timeout=15)
        parsed = iptv_module.parse_m3u(playlist)
        _IPTV_CHANNELS = parsed["channels"]
        _IPTV_ALLOWED_EPG_URLS = set(_iptv_config()["epg_urls"])
        _IPTV_ALLOWED_EPG_URLS.update(parsed["epg_urls"])
        _IPTV_EPG = {}
        return {
            "ok": True,
            "channels": _IPTV_CHANNELS,
            "groups": parsed["groups"],
            "epg_urls": parsed["epg_urls"],
            "count": len(_IPTV_CHANNELS),
        }
    except Exception as exc:
        return {"ok": False, "error": "playlist load failed: " + str(exc)[:160]}


def h_iptv_load_epg(args):
    global _IPTV_EPG
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "channels_with_epg": 0, "programmes": 0}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}

    requested = args.get("urls", [])
    if not isinstance(requested, list):
        return {"ok": False, "error": "EPG URLs must be a list"}
    urls = []
    for candidate in requested[:8]:
        try:
            safe = iptv_module.validate_feed_url(candidate)
        except (TypeError, ValueError):
            continue
        if safe in _IPTV_ALLOWED_EPG_URLS and safe not in urls:
            urls.append(safe)

    if not urls:
        _IPTV_EPG = {}
        return {"ok": True, "channels_with_epg": 0, "programmes": 0}

    merged = {}
    total_programmes = 0
    errors = []
    for url in urls[:3]:
        try:
            payload = iptv_module.fetch_bytes(
                url, timeout=20, max_bytes=iptv_module.MAX_EPG_BYTES
            )
            parsed = iptv_module.parse_xmltv(payload)
            for key, programmes in parsed.items():
                remaining = max(0, 50000 - total_programmes)
                if remaining <= 0:
                    break
                selected = programmes[:remaining]
                merged.setdefault(key, []).extend(selected)
                total_programmes += len(selected)
        except Exception as exc:
            errors.append(str(exc)[:100])

    for programmes in merged.values():
        programmes.sort(key=lambda item: item["start"])
        del programmes[1000:]

    _IPTV_EPG = merged
    return {
        "ok": True,
        "channels_with_epg": len(merged),
        "programmes": total_programmes,
        "warnings": errors[:3],
    }


def h_iptv_epg_for(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "now": None, "next": None}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    channel = args.get("channel")
    if not isinstance(channel, dict):
        return {"ok": False, "error": "channel metadata is required"}
    requested_url = channel.get("url")
    if not any(item.get("url") == requested_url for item in _IPTV_CHANNELS):
        return {"ok": False, "error": "channel is not in the active playlist"}
    current, following = iptv_module.epg_now_next(_IPTV_EPG, channel)
    return {"ok": True, "now": current, "next": following}


def h_iptv_play(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "playback is disabled during visual capture"}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    url = args.get("url")
    channel = next(
        (item for item in _IPTV_CHANNELS if item.get("url") == url),
        None,
    )
    if channel is None:
        return {"ok": False, "error": "channel is not in the active playlist"}
    if not iptv_module.play(channel["url"], channel.get("name", "Live stream")):
        state = iptv_module.status()
        return {"ok": False, "error": state.get("error") or "mpv could not start"}
    return {"ok": True, "state": "playing",
            "channel": channel.get("name", "Live stream")}


def h_iptv_stop(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "state": "idle"}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    iptv_module.stop()
    return {"ok": True, "state": iptv_module.status()["state"]}


def h_iptv_status(args):
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    return {"ok": True, **iptv_module.status()}


def _media_root_entries():
    roots = []
    for root, label in MEDIA_ROOT_CANDIDATES:
        try:
            real = root.resolve(strict=True)
            if real.is_dir() and not any(item["path"] == str(real) for item in roots):
                roots.append({"id": label.lower().replace(" ", "-"),
                              "label": label, "path": str(real)})
        except OSError:
            continue
    return roots


def _media_resolve_path(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError("a valid media path is required")
    candidate = Path(value)
    if not candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError("media path must be absolute and cannot traverse parents")

    for root in _media_root_entries():
        base = Path(root["path"])
        try:
            relative = candidate.relative_to(base)
        except ValueError:
            continue

        current = base
        for part in relative.parts:
            if part in ("", "."):
                continue
            current = current / part
            if current.is_symlink():
                raise ValueError("symbolic links are not allowed in the media browser")

        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ValueError("media path does not exist") from exc
        if resolved == base or base in resolved.parents:
            return resolved, root
    raise ValueError("media path is outside SD1, SD2 and Void Desk Data")


def h_media_roots(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "roots": [
            {"id": "sd1", "label": "SD1", "path": "fixture://sd1"},
            {"id": "sd2", "label": "SD2", "path": "fixture://sd2"},
            {"id": "data", "label": "Void Desk Data", "path": "fixture://data"},
        ]}
    return {"ok": True, "roots": _media_root_entries()}


def h_media_list(args):
    requested = args.get("path")
    if IS_VISUAL_CAPTURE:
        samples = {
            "fixture://sd1": [
                {"name": "MUSIC", "type": "dir", "path": "fixture://sd1/MUSIC", "size": 0},
                {"name": "VIDEO", "type": "dir", "path": "fixture://sd1/VIDEO", "size": 0},
            ],
            "fixture://sd1/MUSIC": [
                {"name": "Ambient Session.ogg", "type": "audio", "path": "fixture://track/audio", "size": 7340032},
            ],
            "fixture://sd1/VIDEO": [
                {"name": "Void Trailer.mp4", "type": "video", "path": "fixture://track/video", "size": 73400320},
            ],
            "fixture://sd2": [],
            "fixture://data": [],
        }
        if requested not in samples:
            return {"ok": False, "error": "fixture media path is unavailable"}
        return {"ok": True, "path": requested, "entries": samples[requested]}

    try:
        current, root = _media_resolve_path(requested)
        if not current.is_dir():
            return {"ok": False, "error": "selected media path is not a folder"}
        entries = []
        for child in sorted(current.iterdir(), key=lambda item: item.name.casefold()):
            if child.name.startswith(".") or child.is_symlink():
                continue
            try:
                real = child.resolve(strict=True)
                if real.parent != current:
                    continue
                if child.is_dir():
                    entries.append({
                        "name": child.name[:160], "type": "dir",
                        "path": str(real), "size": 0,
                    })
                elif child.is_file() and child.suffix.lower() in MEDIA_EXTENSIONS:
                    suffix = child.suffix.lower()
                    media_type = (
                        "audio" if suffix in MEDIA_AUDIO_EXTENSIONS else
                        "video" if suffix in MEDIA_VIDEO_EXTENSIONS else "playlist"
                    )
                    entries.append({
                        "name": child.name[:160], "type": media_type,
                        "path": str(real), "size": child.stat().st_size,
                    })
            except OSError:
                continue
            if len(entries) >= 200:
                break
        return {"ok": True, "path": str(current), "root": root["label"],
                "entries": entries}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)[:160]}


def h_media_play_file(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "media playback is disabled during visual capture"}
    if media_module is None:
        return {"ok": False, "error": "media playback service unavailable"}
    try:
        path, _root = _media_resolve_path(args.get("path"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)[:160]}
    if not path.is_file():
        return {"ok": False, "error": "selected media item is not a file"}
    suffix = path.suffix.lower()
    if suffix not in MEDIA_AUDIO_EXTENSIONS | MEDIA_VIDEO_EXTENSIONS:
        return {"ok": False, "error": "selected file type is not playable"}
    return media_module.play_file(
        str(path), path.name, video=suffix in MEDIA_VIDEO_EXTENSIONS
    )


def h_media_stop(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "state": "idle"}
    if media_module is None:
        return {"ok": False, "error": "media playback service unavailable"}
    return media_module.stop()


def h_media_playback_status(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "playing": False, "current": None,
                "icy_title": "", "paused": False, "buffering": False, "volume": 0}
    if media_module is None:
        return {"ok": False, "error": "media playback service unavailable"}
    return media_module.status()


def h_radio_list(args):
    tab = str(args.get("tab") or "all")
    if IS_VISUAL_CAPTURE:
        stations = [
            {"id": "fixture-radio-01", "name": "Void Signal Radio",
             "tags": "ambient · electronic", "country": "US",
             "category": "all", "favorite": True},
            {"id": "fixture-radio-02", "name": "Italia Broadcast",
             "tags": "news · talk", "country": "IT",
             "category": "italia", "favorite": False},
        ]
        return {"ok": True, "tab": tab, "stations": stations, "count": len(stations)}
    if media_module is None:
        return {"ok": False, "error": "radio service unavailable"}
    return media_module.list_stations(tab)


def h_radio_toggle_favorite(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "radio changes are disabled during visual capture"}
    if media_module is None:
        return {"ok": False, "error": "radio service unavailable"}
    return media_module.toggle_favorite(str(args.get("station_id") or ""))


def h_radio_play(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "radio playback is disabled during visual capture"}
    if media_module is None:
        return {"ok": False, "error": "radio service unavailable"}
    return media_module.play_radio(str(args.get("station_id") or ""))


def h_radio_stop(args):
    return h_media_stop(args)


def h_radio_status(args):
    return h_media_playback_status(args)


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


def _syncthing_rest(url, key, path, method="GET", payload=None):
    import urllib.request
    headers = {"X-API-Key": key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    elif method != "GET":
        data = b""
    request = urllib.request.Request(
        url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=2) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def _syncthing_connection():
    if syncthing_discovery is None:
        return None
    return syncthing_discovery.discover_connection(data_dir=DATA)


def h_syncthing_status(args):
    """Read-only status for the existing muOS Syncthing Web Service."""
    if IS_VISUAL_CAPTURE:
        return {
            "ok": True, "available": True, "state": "Running",
            "url": "http://127.0.0.1:7070", "id": "VOIDDESK-SYNC-CI",
            "connected": 1,
            "folders": [
                {"id": "roms", "label": "ROMs", "path": "/mnt/mmc/ROMS",
                 "pct": 84, "paused": False},
                {"id": "saves", "label": "Save files", "path": "/mnt/mmc/SAVES",
                 "pct": 100, "paused": True},
            ],
            "devices": [
                {"id": "VOIDDESK-DESKTOP-CI", "name": "Desktop PC",
                 "connected": True, "paused": False,
                 "address": "192.168.1.20:22000"},
            ],
        }
    connection = _syncthing_connection()
    if not connection:
        return {
            "ok": True, "available": False, "state": "Not configured",
            "message": "Enable Syncthing in muOS: Configuration > Connectivity > Web Services",
            "folders": [], "devices": [], "connected": 0,
        }
    try:
        url, key = connection["url"], connection["key"]
        system = _syncthing_rest(url, key, "/rest/system/status")
        config = _syncthing_rest(url, key, "/rest/config")
        connections = _syncthing_rest(
            url, key, "/rest/system/connections").get("connections", {})
        from urllib.parse import quote
        folders = []
        for folder in config.get("folders", [])[:8]:
            folder_id = str(folder.get("id") or "")
            pct = -1
            if folder_id:
                try:
                    completion = _syncthing_rest(
                        url, key, "/rest/db/completion?folder=" +
                        quote(folder_id, safe=""))
                    pct = int(completion.get("completion", 0))
                except Exception:
                    pass
            folders.append({
                "id": folder_id,
                "label": folder.get("label") or folder_id,
                "path": folder.get("path", ""),
                "pct": pct,
                "paused": bool(folder.get("paused")),
            })
        devices = []
        for device in config.get("devices", []):
            device_id = str(device.get("deviceID") or "")
            link = connections.get(device_id, {})
            devices.append({
                "id": device_id,
                "name": device.get("name") or device_id[:12],
                "connected": bool(link.get("connected")),
                "paused": bool(link.get("paused")),
                "address": link.get("address", ""),
            })
        return {
            "ok": True, "available": True,
            "state": "Running", "url": connection["url"],
            "id": str(system.get("myID") or "?")[:18],
            "connected": sum(1 for device in devices if device["connected"]),
            "folders": folders, "devices": devices,
        }
    except Exception as exc:
        return {
            "ok": True, "available": False, "state": "Unavailable",
            "message": "Syncthing API unavailable: " + str(exc)[:120],
            "folders": [], "devices": [], "connected": 0,
        }


def h_syncthing_action(args):
    """Perform only allowlisted operations on configured folders/devices."""
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "Syncthing actions are disabled in visual capture"}
    if syncthing_api is None:
        return {"ok": False, "error": "Syncthing adapter unavailable"}
    connection = _syncthing_connection()
    if not connection:
        return {"ok": False, "error": "muOS Syncthing Web Service is not enabled"}
    action = str(args.get("action") or "")
    folder_id = str(args.get("folder") or "")
    device_id = str(args.get("device") or "")
    try:
        config = _syncthing_rest(
            connection["url"], connection["key"], "/rest/config")
        if action in ("toggle_folder", "pause_folder", "resume_folder",
                      "scan", "override"):
            if not folder_id or not any(
                str(item.get("id") or "") == folder_id
                for item in config.get("folders", [])
            ):
                return {"ok": False, "error": "unknown Syncthing folder"}
        elif action in ("toggle_device", "pause_device", "resume_device"):
            if not device_id or not any(
                str(item.get("deviceID") or "") == device_id
                for item in config.get("devices", [])
            ):
                return {"ok": False, "error": "unknown Syncthing device"}
        else:
            return {"ok": False, "error": "unsupported Syncthing action"}
        return syncthing_api.perform_action(
            _syncthing_rest, connection["url"], connection["key"], action,
            folder=folder_id, device=device_id,
        )
    except Exception as exc:
        return {"ok": False, "error": "Syncthing action failed: " + str(exc)[:120]}


HANDLERS = {
    "ping": h_ping,
    "get_config": h_get_config,
    "set_config": h_set_config,
    "system_info": h_system_info,
    "gh_fetch_releases": h_gh_fetch_releases,
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
    "media_roots": h_media_roots,
    "media_list": h_media_list,
    "media_play_file": h_media_play_file,
    "media_stop": h_media_stop,
    "media_playback_status": h_media_playback_status,
    "radio_list": h_radio_list,
    "radio_toggle_favorite": h_radio_toggle_favorite,
    "radio_play": h_radio_play,
    "radio_stop": h_radio_stop,
    "radio_status": h_radio_status,
    "iptv_get_config": h_iptv_get_config,
    "iptv_load_playlist": h_iptv_load_playlist,
    "iptv_load_epg": h_iptv_load_epg,
    "iptv_epg_for": h_iptv_epg_for,
    "iptv_play": h_iptv_play,
    "iptv_stop": h_iptv_stop,
    "iptv_status": h_iptv_status,
    "list_external": h_list_external,
    "launch_external": h_launch_external,
    "toolbox_stats": h_toolbox_stats,
    "calendar_events": h_calendar_events,
    "hotspot_toggle": h_hotspot_toggle,
    "tailscale_status": h_tailscale_status,
    "tailscale_action": h_tailscale_action,
    "syncthing_status": h_syncthing_status,
    "syncthing_action": h_syncthing_action,

    "session_list": h_session_list,
    "session_launch": h_session_launch,
    "wifi_scan": h_wifi_scan,
    "bt_scan": h_bt_scan,
    "list_muos_apps": h_list_muos_apps,
    "launch_muos_app": h_launch_muos_app,

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
