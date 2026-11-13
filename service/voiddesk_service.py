#!/usr/bin/env python3
"""
VoidDesk background service — reads .love_request.json,
writes .love_response.json. Minimal, no external deps.
Runs on both muOS (aarch64) and desktop x86_64.
"""
import errno
import fcntl
import ipaddress
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
import socket
import subprocess
import sys
import termios
import time
import traceback
import urllib.error
import urllib.parse
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
    from mpvctl import MpvController
except Exception:
    MpvController = None

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


# Void Radio: catalogue, favourites and playback use only station entries
# returned by Radio Browser; the LÖVE client never supplies a stream URL.
_RADIO_BROWSER = "https://de1.api.radio-browser.info/json/stations/search"
_RADIO_STATIONS = {}
_RADIO_PLAYER = None
_RADIO_FAVORITES_FILE = DATA / "radio_favorites.json"


def _radio_clean_station(item):
    if not isinstance(item, dict):
        return None
    station_id = str(item.get("stationuuid") or "")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", station_id):
        return None
    stream_url = str(item.get("url_resolved") or item.get("url") or "")
    try:
        parsed = urllib.parse.urlsplit(stream_url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password):
            return None
        if parsed.hostname.lower() in ("localhost", "localhost.localdomain"):
            return None
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            return None
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if not address.is_global:
                return None
        except ValueError:
            pass
    except ValueError:
        return None
    try:
        bitrate = max(0, min(100000, int(item.get("bitrate") or 0)))
    except (TypeError, ValueError):
        bitrate = 0
    return {
        "stationuuid": station_id,
        "name": str(item.get("name") or "Unknown station").strip()[:100] or "Unknown station",
        "url": stream_url[:1000],
        "country": str(item.get("country") or "")[:80],
        "language": str(item.get("language") or "")[:80],
        "tags": str(item.get("tags") or "")[:180],
        "codec": str(item.get("codec") or "")[:24],
        "bitrate": bitrate,
        "favicon": str(item.get("favicon") or "")[:300],
    }


def _radio_favorites_load():
    try:
        raw = json.loads(_RADIO_FAVORITES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    stations = []
    for item in raw[:200]:
        station = _radio_clean_station(item)
        if station:
            stations.append(station)
    return stations


def _radio_favorites_save(items):
    _RADIO_FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = _RADIO_FAVORITES_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(items[:200], ensure_ascii=False, indent=2),
                          encoding="utf-8")
    os.replace(temporary, _RADIO_FAVORITES_FILE)


def h_radio_search(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": True, "stations": [], "count": 0, "source": "visual capture"}
    name = str(args.get("name") or "").strip()[:80]
    country = str(args.get("country") or "").strip()[:80]
    tag = str(args.get("tag") or "").strip()[:60]
    try:
        limit = max(1, min(50, int(args.get("limit", 30))))
    except (TypeError, ValueError):
        limit = 30
    query = {"limit": limit, "hidebroken": "true",
             "order": "clickcount", "reverse": "true"}
    if name:
        query["name"] = name
    if country:
        query["country"] = country
    if tag:
        query["tag"] = tag
    url = _RADIO_BROWSER + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url, headers={"User-Agent": "VoidDesk-Radio/1.0",
                      "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "error": "Radio Browser unavailable: " + str(exc)[:120]}
    if not isinstance(payload, list):
        return {"ok": False, "error": "Radio Browser returned an invalid catalogue"}
    stations = []
    for item in payload:
        station = _radio_clean_station(item)
        if station:
            _RADIO_STATIONS[station["stationuuid"]] = station
            stations.append(station)
    return {"ok": True, "stations": stations, "count": len(stations),
            "source": "Radio Browser"}


def h_radio_favorites(args):
    stations = _radio_favorites_load()
    for station in stations:
        _RADIO_STATIONS[station["stationuuid"]] = station
    return {"ok": True, "stations": stations, "count": len(stations)}


def h_radio_favorite_toggle(args):
    station_id = str(args.get("stationuuid") or "")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", station_id):
        return {"ok": False, "error": "invalid station id"}
    stations = _radio_favorites_load()
    if any(item["stationuuid"] == station_id for item in stations):
        stations = [item for item in stations if item["stationuuid"] != station_id]
        _radio_favorites_save(stations)
        return {"ok": True, "favorite": False, "count": len(stations)}
    station = _RADIO_STATIONS.get(station_id)
    if station is None:
        return {"ok": False, "error": "station must be loaded from the catalogue first"}
    stations.append(station)
    _radio_favorites_save(stations)
    return {"ok": True, "favorite": True, "count": len(stations)}


def _radio_player():
    global _RADIO_PLAYER
    if MpvController is None:
        return None
    if _RADIO_PLAYER is None:
        _RADIO_PLAYER = MpvController(
            sock_path="/tmp/voiddesk_radio_%d.sock" % os.getpid())
    return _RADIO_PLAYER


def h_radio_play(args):
    station_id = str(args.get("stationuuid") or "")
    station = _RADIO_STATIONS.get(station_id)
    if station is None:
        station = next((item for item in _radio_favorites_load()
                        if item["stationuuid"] == station_id), None)
    if station is None:
        return {"ok": False, "error": "station not found; refresh the catalogue"}
    player = _radio_player()
    if player is None:
        return {"ok": False, "error": "MPV controller is unavailable"}
    try:
        ok, error = player.start(station["url"])
    except Exception as exc:
        player.stop()
        return {"ok": False, "error": "MPV launch failed: " + str(exc)[:120]}
    if not ok:
        player.stop()
        return {"ok": False, "error": str(error or "stream could not be started")[:140]}
    return {"ok": True, "playing": station["name"], "stationuuid": station_id}


def h_radio_action(args):
    action = str(args.get("action") or "")
    player = _radio_player()
    if player is None:
        return {"ok": False, "error": "MPV controller is unavailable"}
    if action == "stop":
        player.stop()
        return {"ok": True, "running": False}
    if not player.is_running():
        return {"ok": False, "error": "no radio stream is running"}
    if action == "toggle_pause":
        paused = player.toggle_pause()
        return {"ok": True, "pause": bool(paused)}
    if action == "volume":
        try:
            volume = max(0, min(100, int(args.get("value"))))
        except (TypeError, ValueError):
            return {"ok": False, "error": "volume must be between 0 and 100"}
        player.set_volume(volume)
        return {"ok": True, "volume": volume}
    return {"ok": False, "error": "unsupported radio action"}


def h_radio_status(args):
    player = _radio_player()
    if player is None:
        return {"ok": False, "error": "MPV controller is unavailable"}
    try:
        return {"ok": True, "status": player.status()}
    except Exception as exc:
        return {"ok": False, "error": "cannot read radio status: " + str(exc)[:100]}


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


def _notes_name(candidate):
    if not isinstance(candidate, str):
        return None
    value = candidate.strip()
    if not value or len(value) > 64 or "/" in value or "\\" in value or "\x00" in value:
        return None
    if not value.lower().endswith(".txt"):
        value += ".txt"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}\.txt", value):
        return None
    return value


def h_notes_list(args):
    notes_dir = DATA / "notes"
    try:
        notes_dir.mkdir(parents=True, exist_ok=True)
        items = []
        for path in notes_dir.iterdir():
            if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".txt":
                continue
            try:
                stat = path.stat()
                preview = path.read_text(encoding="utf-8", errors="replace")[:120]
                items.append({
                    "name": path.name,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "preview": preview.replace("\n", " ").strip(),
                })
            except OSError:
                continue
        items.sort(key=lambda item: item["modified"], reverse=True)
        return {"ok": True, "notes": items[:100], "count": min(len(items), 100)}
    except OSError as exc:
        return {"ok": False, "error": "cannot list notes: " + str(exc)[:120]}


def h_notes_read(args):
    name = _notes_name(args.get("name"))
    if not name:
        return {"ok": False, "error": "invalid note name"}
    target = DATA / "notes" / name
    if target.is_symlink() or not target.is_file():
        return {"ok": False, "error": "note does not exist"}
    try:
        if target.stat().st_size > 32768:
            return {"ok": False, "error": "note is larger than the 32 KB editor limit"}
        return {"ok": True, "name": name,
                "content": target.read_text(encoding="utf-8", errors="replace")}
    except OSError as exc:
        return {"ok": False, "error": "cannot read note: " + str(exc)[:120]}


def h_notes_save(args):
    name = _notes_name(args.get("name"))
    content = args.get("content")
    if not name:
        return {"ok": False, "error": "invalid note name"}
    if not isinstance(content, str):
        return {"ok": False, "error": "note content must be text"}
    if len(content.encode("utf-8")) > 32768:
        return {"ok": False, "error": "note exceeds the 32 KB limit"}
    notes_dir = DATA / "notes"
    target = notes_dir / name
    temporary = notes_dir / ("." + name + ".tmp")
    try:
        notes_dir.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() or temporary.is_symlink():
            return {"ok": False, "error": "linked note files are not allowed"}
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return {"ok": True, "name": name, "size": target.stat().st_size}
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": False, "error": "cannot save note: " + str(exc)[:120]}


def h_notes_delete(args):
    name = _notes_name(args.get("name"))
    if not name:
        return {"ok": False, "error": "invalid note name"}
    target = DATA / "notes" / name
    if target.is_symlink() or not target.is_file():
        return {"ok": False, "error": "note does not exist"}
    try:
        target.unlink()
        return {"ok": True, "name": name}
    except OSError as exc:
        return {"ok": False, "error": "cannot delete note: " + str(exc)[:120]}


def _read_content_cache(name, max_bytes=512 * 1024):
    if name not in ("rss_cache.json", "weather_cache.json"):
        return {"ok": False, "error": "unknown content cache"}
    path = DATA / name
    if path.is_symlink() or not path.is_file():
        return {"ok": True, "cached": False}
    try:
        if path.stat().st_size > max_bytes:
            return {"ok": False, "error": "cached content exceeds its size limit"}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return {"ok": False, "error": "cached content is malformed"}
        payload["cached"] = True
        return payload
    except (OSError, ValueError, TypeError):
        return {"ok": False, "error": "cannot read cached content"}


def h_rss_cache(args):
    return _read_content_cache("rss_cache.json")


def h_weather_cache(args):
    return _read_content_cache("weather_cache.json")


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
    state_path = job.get("progress_file")
    if state_path:
        try:
            state = json.loads(Path(state_path).read_text(encoding="utf-8"))
            if isinstance(state, dict):
                for field in ("progress", "phase", "message", "detail",
                              "animation", "severity", "indeterminate"):
                    if field in state:
                        job[field] = state[field]
                if state.get("status") == "failed":
                    job["severity"] = "error"
        except (OSError, ValueError, TypeError):
            pass

    process = job.get("process")
    if job["status"] == "running" and process is not None:
        code = process.poll()
        if code is not None:
            job["status"] = "done" if code == 0 else "error"
            job["progress"] = 100 if code == 0 else job.get("progress", 0)
            job["severity"] = "success" if code == 0 else "error"
            job["exit_code"] = code
            lock_path = job.get("lock_path")
            if lock_path:
                try:
                    Path(lock_path).unlink(missing_ok=True)
                except OSError:
                    pass
    return job


def _job_public(job):
    _job_refresh(job)
    return {
        "id": job["id"],
        "name": job["name"],
        "hub": job["hub"],
        "status": job["status"],
        "started": job["started"],
        "progress": job.get("progress", 0),
        "phase": job.get("phase", ""),
        "message": job.get("message", ""),
        "detail": job.get("detail", ""),
        "description": job.get("description", "Void Desk is performing this operation."),
        "reason": job.get("reason", "This step is required to complete the selected action."),
        "icon": job.get("icon", "tool"),
        "animation": job.get("animation", "loading"),
        "severity": job.get("severity", "info"),
        "indeterminate": job.get("indeterminate", False),
        "can_background": job.get("can_background", True),
        "color": job.get("color", [0.45, 0.72, 0.95]),
    }


def h_job_start(args):
    """Start only allowlisted package jobs or registered external tools."""
    global _JOB_SEQ
    command = None
    cwd = APP_DIR
    progress_file = None
    cmd_text = args.get("cmd")
    tool_id = args.get("tool_id")
    service_task = args.get("service_task")

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
    elif service_task == "tailscale_start":
        script = APP_DIR / "service" / "tailscale_job.py"
        if not script.is_file():
            return {"ok": False, "error": "Tailscale service job is missing"}
        command = [sys.executable, str(script)]
    elif service_task == "xfce_bootstrap":
        if not IS_DEVICE:
            return {"ok": False, "error": "XFCE handheld bootstrap is available only on muOS devices"}
        script = APP_DIR / "bin" / "xfce_bootstrap.py"
        if not script.is_file():
            return {"ok": False, "error": "XFCE bootstrap script is missing"}
        progress_file = DATA / ".xfce_bootstrap_state.json"
        command = [sys.executable, str(script)]
    elif service_task == "rss_refresh":
        category = str(args.get("category") or "all").lower()
        language = str(args.get("language") or "all").lower()
        if category not in ("all", "news", "tech", "linux", "gaming", "retro", "anime"):
            return {"ok": False, "error": "unsupported RSS category"}
        if language not in ("all", "en", "it"):
            return {"ok": False, "error": "unsupported RSS language"}
        script = APP_DIR / "service" / "content_refresh.py"
        if not script.is_file():
            return {"ok": False, "error": "content refresh worker is missing"}
        progress_file = DATA / ".rss_refresh_state.json"
        command = [sys.executable, str(script), "rss", category, language]
    elif service_task == "weather_refresh":
        city = " ".join(str(args.get("city") or "").split())
        if not city or len(city) > 80 or any(ord(ch) < 32 for ch in city):
            return {"ok": False, "error": "enter a city name up to 80 characters"}
        script = APP_DIR / "service" / "content_refresh.py"
        if not script.is_file():
            return {"ok": False, "error": "content refresh worker is missing"}
        progress_file = DATA / ".weather_refresh_state.json"
        command = [sys.executable, str(script), "weather", city]
    elif service_task == "env_install":
        env_id = str(args.get("id") or "")
        if env_id not in ("icewm", "lxde"):
            return {"ok": False, "error": "unsupported desktop environment"}
        script = APP_DIR / "bin" / "env_install.py"
        if not script.is_file():
            return {"ok": False, "error": "environment installer is missing"}
        progress_file = DATA / (".%s_install_state.json" % env_id)
        command = [sys.executable, str(script), env_id]
    elif service_task == "desktop_maintenance":
        action = str(args.get("action") or "")
        env_id = str(args.get("id") or "")
        if action not in ("uninstall", "updates") or env_id not in ENV_MARKERS:
            return {"ok": False, "error": "unsupported desktop maintenance operation"}
        if action == "uninstall" and not (DATA / ENV_MARKERS[env_id]).exists():
            return {"ok": False, "error": "desktop environment is not installed"}
        if action == "updates" and not (DATA / ENV_MARKERS[env_id]).exists():
            return {"ok": False, "error": "install this desktop before checking for updates"}
        script = APP_DIR / "bin" / "desktop_env_maintenance.py"
        if not script.is_file():
            return {"ok": False, "error": "desktop maintenance helper is missing"}
        progress_file = DATA / (".%s_%s_state.json" % (env_id, action))
        command = [sys.executable, str(script), action, env_id]
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

    if service_task in ("rss_refresh", "weather_refresh"):
        requested_name = name
        for existing in _JOBS.values():
            _job_refresh(existing)
            if existing.get("name") == requested_name and existing.get("status") in ("running", "starting"):
                return {"ok": True, "job": _job_public(existing), "already": True}

    if progress_file is not None:
        try:
            progress_file.unlink(missing_ok=True)
        except OSError:
            pass

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
        "phase": "Preparing",
        "message": "Starting operation...",
        "detail": "",
        "description": str(args.get("description") or "Void Desk is performing this operation.")[:240],
        "reason": str(args.get("reason") or "This step is required to complete the selected action.")[:240],
        "icon": str(args.get("icon") or "tool")[:32],
        "animation": str(args.get("animation") or "loading")[:24],
        "severity": "info",
        "indeterminate": progress_file is not None,
        "can_background": args.get("can_background", True) is not False,
        "process": process,
        "log_path": log_path,
        "progress_file": progress_file,
        "color": args.get("color") or [0.45, 0.72, 0.95],
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


# Local media browser: fixed roots, no caller-supplied root and no symlink traversal.
MEDIA_ROOTS = (Path("/mnt/mmc"), Path("/mnt/sdcard"))
MEDIA_AUDIO_EXTS = {".mp3", ".ogg", ".oga", ".opus", ".flac", ".wav", ".m4a", ".aac"}
MEDIA_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v"}
_MEDIA_PLAYER_PROC = None
_MEDIA_NOW_PLAYING = ""
_MEDIA_PLAYER_SOCKET = Path(os.environ.get("TMPDIR") or "/tmp") / ("voiddesk-mpv-%s.sock" % os.getpid())


def _media_resolve(candidate):
    if not isinstance(candidate, str) or not candidate or "\x00" in candidate:
        return None
    raw = Path(candidate)
    if not raw.is_absolute() or ".." in raw.parts:
        return None
    for configured_root in MEDIA_ROOTS:
        try:
            root = configured_root.resolve(strict=True)
            relative = raw.relative_to(root)
            current = root
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("symlink paths are not allowed")
            target = raw.resolve(strict=True)
            target.relative_to(root)
            if target.exists():
                return target
        except (OSError, ValueError, RuntimeError):
            continue
    return None


def h_media_list(args):
    requested = args.get("path")
    if requested in (None, ""):
        roots = []
        for configured_root in MEDIA_ROOTS:
            try:
                root = configured_root.resolve(strict=True)
                if root.is_dir():
                    roots.append({"name": root.name or str(root), "path": str(root),
                                  "is_dir": True, "size": 0})
            except OSError:
                continue
        return {"ok": True, "path": "", "items": roots, "root": True}
    directory = _media_resolve(requested)
    if directory is None or not directory.is_dir():
        return {"ok": False, "error": "directory is unavailable or outside media roots"}
    items = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        items.append({"name": entry.name[:160], "path": entry.path,
                                      "is_dir": True, "size": 0})
                    elif entry.is_file(follow_symlinks=False):
                        suffix = Path(entry.name).suffix.lower()
                        if suffix in MEDIA_AUDIO_EXTS or suffix in MEDIA_VIDEO_EXTS:
                            items.append({"name": entry.name[:160], "path": entry.path,
                                          "is_dir": False, "size": entry.stat(
                                              follow_symlinks=False).st_size})
                except OSError:
                    continue
    except OSError as exc:
        return {"ok": False, "error": "cannot read media directory: " + str(exc)[:100]}
    items.sort(key=lambda item: (not item["is_dir"], item["name"].casefold()))
    return {"ok": True, "path": str(directory), "items": items[:200], "root": False}


def _media_ipc(command):
    """Send one bounded command to the local MPV Unix socket."""
    if not _MEDIA_PLAYER_SOCKET.exists() or _MEDIA_PLAYER_SOCKET.is_symlink():
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.6)
            client.connect(str(_MEDIA_PLAYER_SOCKET))
            payload = json.dumps({"command": command, "request_id": 1}) + "\n"
            client.sendall(payload.encode("utf-8"))
            response = client.recv(4096).decode("utf-8", "replace").splitlines()
        for line in response:
            try:
                parsed = json.loads(line)
                if parsed.get("request_id") == 1:
                    return parsed
            except (ValueError, TypeError):
                continue
    except (OSError, ValueError):
        return None
    return None


def h_media_play(args):
    global _MEDIA_PLAYER_PROC, _MEDIA_NOW_PLAYING
    target = _media_resolve(args.get("path"))
    if target is None or not target.is_file():
        return {"ok": False, "error": "media file is unavailable or outside media roots"}
    if target.suffix.lower() not in MEDIA_AUDIO_EXTS | MEDIA_VIDEO_EXTS:
        return {"ok": False, "error": "unsupported media file type"}
    player = shutil.which("mpv")
    if not player:
        return {"ok": False, "error": "mpv is not installed"}
    h_media_stop({})
    try:
        if _MEDIA_PLAYER_SOCKET.is_symlink():
            return {"ok": False, "error": "refusing a linked MPV control socket"}
        _MEDIA_PLAYER_SOCKET.unlink(missing_ok=True)
        video = target.suffix.lower() in MEDIA_VIDEO_EXTS
        player_args = [player, "--no-terminal",
                       "--input-ipc-server=" + str(_MEDIA_PLAYER_SOCKET)]
        player_args.append("--force-window=yes" if video else "--no-video")
        player_args.append(str(target))
        _MEDIA_PLAYER_PROC = subprocess.Popen(
            player_args, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        _MEDIA_NOW_PLAYING = target.name
        return {"ok": True, "playing": _MEDIA_NOW_PLAYING,
                "pid": _MEDIA_PLAYER_PROC.pid}
    except OSError as exc:
        _MEDIA_PLAYER_PROC = None
        _MEDIA_NOW_PLAYING = ""
        return {"ok": False, "error": "cannot start mpv: " + str(exc)[:120]}


def h_media_action(args):
    action = str(args.get("action") or "")
    if action == "stop":
        return h_media_stop({})
    if _MEDIA_PLAYER_PROC is None or _MEDIA_PLAYER_PROC.poll() is not None:
        return {"ok": False, "error": "no local media is playing"}
    if action == "toggle_pause":
        response = _media_ipc(["cycle", "pause"])
        if not response or response.get("error") != "success":
            return {"ok": False, "error": "MPV pause control is unavailable"}
        status = _media_ipc(["get_property", "pause"])
        paused = status.get("data") if status and status.get("error") == "success" else None
        return {"ok": True, "action": action, "data": paused}
    if action == "volume":
        try:
            value = max(0, min(100, int(args.get("value"))))
        except (TypeError, ValueError):
            return {"ok": False, "error": "volume must be between 0 and 100"}
        response = _media_ipc(["set_property", "volume", value])
        if not response or response.get("error") != "success":
            return {"ok": False, "error": "MPV volume control is unavailable"}
        return {"ok": True, "volume": value}
    return {"ok": False, "error": "unsupported media action"}


def h_media_stop(args):
    global _MEDIA_PLAYER_PROC, _MEDIA_NOW_PLAYING
    process = _MEDIA_PLAYER_PROC
    if process is not None and process.poll() is None:
        # Ask MPV to exit cleanly first; terminate is the bounded fallback.
        _media_ipc(["quit"])
        try:
            process.wait(timeout=2)
        except Exception:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except OSError:
                    pass
    _MEDIA_PLAYER_PROC = None
    _MEDIA_NOW_PLAYING = ""
    try:
        _MEDIA_PLAYER_SOCKET.unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True}


def h_media_status(args):
    try:
        if IS_VISUAL_CAPTURE:
            return {"ok": True, "media": {
                "volume": 40, "now_playing": None, "paused": False,
                "library_count": 0, "recordings": 0,
            }}
        playing = None
        paused = False
        player_volume = None
        if _MEDIA_PLAYER_PROC is not None and _MEDIA_PLAYER_PROC.poll() is None:
            playing = _MEDIA_NOW_PLAYING or "Media"
            pause_response = _media_ipc(["get_property", "pause"])
            volume_response = _media_ipc(["get_property", "volume"])
            if pause_response and pause_response.get("error") == "success":
                paused = bool(pause_response.get("data"))
            if volume_response and volume_response.get("error") == "success":
                try:
                    player_volume = int(volume_response.get("data"))
                except (TypeError, ValueError):
                    player_volume = None
        vol = player_volume
        if vol is None:
            vol = deskinfo.volume() if deskinfo is not None else None
        return {"ok": True, "media": {
            "volume": vol if vol is not None else 0,
            "now_playing": playing,
            "paused": paused,
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


def h_iptv_action(args):
    if IS_VISUAL_CAPTURE:
        return {"ok": False, "error": "playback controls are disabled during visual capture"}
    if iptv_module is None:
        return {"ok": False, "error": "IPTV service module unavailable"}
    action = str(args.get("action") or "")
    try:
        return iptv_module.action(action, args.get("value"))
    except Exception as exc:
        return {"ok": False, "error": "IPTV control failed: " + str(exc)[:120]}


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
    """Install an allowlisted additional desktop inside the XFCE image."""
    env_id = args.get("id")
    if env_id not in ("icewm", "lxde"):
        return {"ok": False, "error": "unknown desktop environment"}
    blocked = device_only("env_install")
    if blocked:
        return blocked
    if not (DATA / ".xfce_ready").exists():
        return {"ok": False, "error": "Install XFCE before adding another desktop"}
    marker = DATA / ENV_MARKERS[env_id]
    if marker.exists():
        return {"ok": True, "already": True, "note": ENV_NAMES[env_id] + " is already installed"}
    lock = DATA / (".%s_install_running" % env_id)
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            os.kill(pid, 0)
            for job in _JOBS.values():
                process = job.get("process")
                if process is not None and process.pid == pid:
                    return {"ok": True, "job": _job_public(job), "already": True}
            return {"ok": False, "error": "An existing desktop installation is still running"}
        except (ValueError, ProcessLookupError, PermissionError, OSError):
            try:
                lock.unlink()
            except OSError:
                pass
    result = h_job_start({
        "service_task": "env_install",
        "id": env_id,
        "name": "Install " + ENV_NAMES[env_id],
        "hub": "start-session",
        "description": "Install " + ENV_NAMES[env_id] + " into the existing XFCE image.",
        "reason": "Additional window managers share the XFCE root filesystem and require XFCE to be installed first.",
        "icon": "desktop",
        "animation": "install",
        "can_background": True,
    })
    if not result.get("ok"):
        return result
    job = _JOBS.get(str(result["job"]["id"]))
    if job and job.get("process"):
        try:
            lock.write_text(str(job["process"].pid), encoding="utf-8")
            job["lock_path"] = lock
        except OSError as exc:
            try:
                os.killpg(job["process"].pid, signal.SIGTERM)
            except OSError:
                pass
            return {"ok": False, "error": "Cannot create operation lock: " + str(exc)}
    return result

def _start_desktop_maintenance(env_id, action):
    if env_id not in ENV_MARKERS or action not in ("uninstall", "updates"):
        return {"ok": False, "error": "unsupported desktop maintenance operation"}
    blocked = device_only("desktop_maintenance")
    if blocked:
        return blocked
    marker = DATA / ENV_MARKERS[env_id]
    if not marker.exists():
        return {"ok": False, "error": ENV_NAMES[env_id] + " is not installed"}
    name = ("Remove " if action == "uninstall" else "Check updates for ") + ENV_NAMES[env_id]
    for existing in _JOBS.values():
        _job_refresh(existing)
        if existing.get("name") == name and existing.get("status") in ("running", "starting"):
            return {"ok": True, "job": _job_public(existing), "already": True}
    description = ("Remove the selected desktop environment." if action == "uninstall"
                   else "Refresh package indexes and simulate available updates without installing them.")
    reason = ("XFCE removal deletes the shared desktop image, including IceWM and LXDE if installed."
              if action == "uninstall" and env_id == "xfce"
              else "This operation is limited to the selected environment inside the isolated Ubuntu image.")
    result = h_job_start({
        "service_task": "desktop_maintenance",
        "action": action,
        "id": env_id,
        "name": name,
        "hub": "start-session",
        "description": description,
        "reason": reason,
        "icon": "desktop",
        "animation": "verify" if action == "updates" else "extract",
        "can_background": True,
    })
    return result


def h_env_uninstall(args):
    env_id = str(args.get("id") or "")
    if env_id not in ENV_MARKERS:
        return {"ok": False, "error": "unknown desktop environment"}
    return _start_desktop_maintenance(env_id, "uninstall")


def h_env_update_check(args):
    env_id = str(args.get("id") or "")
    if env_id not in ENV_MARKERS:
        return {"ok": False, "error": "unknown desktop environment"}
    return _start_desktop_maintenance(env_id, "updates")

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
    """Start the isolated XFCE bootstrap as a supervised LÖVE operation."""
    lock = DATA / ".xfce_install_running"
    if IS_DEVICE:
        ready_marker = DATA / ".xfce_ready"
        desktop_image = DATA / "xfce.img"
        if ready_marker.exists():
            try:
                if desktop_image.is_file() and desktop_image.stat().st_size > 3_000_000_000:
                    return {"ok": True, "already": True, "note": "XFCE is already installed"}
            except OSError:
                pass
            try:
                ready_marker.unlink()
            except OSError:
                pass
        if lock.exists():
            try:
                pid = int(lock.read_text().strip())
                os.kill(pid, 0)
                for job in _JOBS.values():
                    process = job.get("process")
                    if process is not None and process.pid == pid:
                        return {"ok": True, "job": _job_public(job), "already": True}
                return {"ok": False, "error": "An existing XFCE operation is still running; restart Void Desk before starting another."}
            except (ValueError, ProcessLookupError, PermissionError, OSError):
                try:
                    lock.unlink()
                except OSError:
                    pass
        result = h_job_start({
            "service_task": "xfce_bootstrap",
            "name": "Install XFCE",
            "hub": "start-session",
            "description": "Prepare the isolated Ubuntu 24.04 / XFCE desktop image.",
            "reason": "XFCE requires at least 5 GB free for a fresh image (1 GB when reusing an existing image), a working network and about 10–20 minutes.",
            "icon": "desktop",
            "animation": "extract",
            "can_background": True,
        })
        if not result.get("ok"):
            return result
        job = _JOBS.get(str(result["job"]["id"]))
        if job and job.get("process"):
            try:
                lock.write_text(str(job["process"].pid), encoding="utf-8")
                job["lock_path"] = lock
            except OSError as exc:
                try:
                    os.killpg(job["process"].pid, signal.SIGTERM)
                except OSError:
                    pass
                return {"ok": False, "error": "Cannot create XFCE operation lock: " + str(exc)}
        return result
    if shutil.which("startxfce4"):
        return {"ok": True, "already": True, "note": "XFCE is already installed"}
    try:
        log_path = DATA / "xfce_pc_install.log"
        with open(log_path, "ab") as lf:
            subprocess.Popen(
                ["pkexec", "apt-get", "install", "-y", "--no-install-recommends",
                 "xfce4", "xfce4-terminal", "xserver-xephyr"],
                stdout=lf, stderr=lf, start_new_session=True)
        return {"ok": True, "note": "PC XFCE installation started"}
    except FileNotFoundError:
        return {"ok": False, "error": "pkexec is missing; install polkit on the PC"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

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
    "media_list": h_media_list,
    "media_play": h_media_play,
    "media_stop": h_media_stop,
    "media_action": h_media_action,
    "radio_search": h_radio_search,
    "radio_favorites": h_radio_favorites,
    "radio_favorite_toggle": h_radio_favorite_toggle,
    "radio_play": h_radio_play,
    "radio_action": h_radio_action,
    "radio_status": h_radio_status,
    "iptv_get_config": h_iptv_get_config,
    "iptv_load_playlist": h_iptv_load_playlist,
    "iptv_load_epg": h_iptv_load_epg,
    "iptv_epg_for": h_iptv_epg_for,
    "iptv_play": h_iptv_play,
    "iptv_action": h_iptv_action,
    "iptv_stop": h_iptv_stop,
    "iptv_status": h_iptv_status,
    "list_external": h_list_external,
    "launch_external": h_launch_external,
    "toolbox_stats": h_toolbox_stats,
    "rss_cache": h_rss_cache,
    "weather_cache": h_weather_cache,
    "notes_list": h_notes_list,
    "notes_read": h_notes_read,
    "notes_save": h_notes_save,
    "notes_delete": h_notes_delete,
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
    "env_uninstall": h_env_uninstall,
    "env_update_check": h_env_update_check,
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
