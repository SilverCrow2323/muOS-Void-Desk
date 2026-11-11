from __future__ import annotations

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
SERVICE_DIR = Path(__file__).resolve().parent
DESK_DIR = APP_DIR / "desk"
for import_dir in (SERVICE_DIR, DESK_DIR):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

try:
    from const import RADIO_BUILTIN, RADIO_URL_MIGRATIONS
except Exception:
    RADIO_BUILTIN = []
    RADIO_URL_MIGRATIONS = {}

try:
    from mpvctl import MpvController
except Exception:
    MpvController = None

_APP_DIR = APP_DIR
_CONFIG_PATH = APP_DIR / "data" / "desk_config.json"
_PLAYER = None
_CURRENT = None

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | {".m3u", ".m3u8"}


def configure(app_dir: Path | str) -> None:
    global _APP_DIR, _CONFIG_PATH, _PLAYER
    _APP_DIR = Path(app_dir).resolve()
    _CONFIG_PATH = _APP_DIR / "data" / "desk_config.json"
    if MpvController is not None:
        _PLAYER = MpvController("/tmp/voiddesk-love-media-%d.sock" % os.getpid())


def _load_config() -> dict:
    try:
        value = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _save_config(config: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = _CONFIG_PATH.with_name(_CONFIG_PATH.name + ".media.tmp")
    encoded = json.dumps(config, ensure_ascii=False, indent=1)
    descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, _CONFIG_PATH)


def _station_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def _clean_station(station: dict) -> dict | None:
    if not isinstance(station, dict):
        return None
    url = station.get("url")
    name = str(station.get("name") or "")[:80].strip()
    if not isinstance(url, str) or not name:
        return None
    return {
        "id": _station_id(url),
        "name": name,
        "url": url,
        "tags": str(station.get("tags") or "")[:80],
        "country": str(station.get("country") or "")[:40],
        "category": str(station.get("category") or "all")[:24],
    }


def _catalog_sources(config: dict) -> tuple[list[dict], list[dict], list[dict]]:
    builtins = [entry for raw in RADIO_BUILTIN if (entry := _clean_station(raw))]
    raw_favorites = config.get("radio_favorites", [])
    raw_recent = config.get("radio_recent", [])
    if not isinstance(raw_favorites, list):
        raw_favorites = []
    if not isinstance(raw_recent, list):
        raw_recent = []
    favorites = [entry for raw in raw_favorites[:100]
                 if (entry := _clean_station(raw))]
    recent = [entry for raw in raw_recent[:30]
              if (entry := _clean_station(raw))]
    return builtins, favorites, recent


def list_stations(tab: str = "all") -> dict:
    if tab not in {"all", "italia", "tekno", "preferiti", "recenti"}:
        tab = "all"
    config = _load_config()
    builtins, favorites, recent = _catalog_sources(config)
    if tab == "italia":
        selected = [entry for entry in builtins if entry["category"] == "italia"]
    elif tab == "tekno":
        selected = [entry for entry in builtins if entry["category"] == "tekno"]
    elif tab == "preferiti":
        selected = favorites
    elif tab == "recenti":
        selected = recent
    else:
        selected = builtins
    favourite_ids = {entry["id"] for entry in favorites}
    stations = [{
        "id": entry["id"],
        "name": entry["name"],
        "tags": entry["tags"],
        "country": entry["country"],
        "category": entry["category"],
        "favorite": entry["id"] in favourite_ids,
    } for entry in selected[:100]]
    return {"ok": True, "tab": tab, "stations": stations, "count": len(stations)}


def _find_station(station_id: str) -> dict | None:
    config = _load_config()
    builtins, favorites, recent = _catalog_sources(config)
    for entry in builtins + favorites + recent:
        if entry["id"] == station_id:
            return entry
    return None


def toggle_favorite(station_id: str) -> dict:
    station = _find_station(station_id)
    if station is None:
        return {"ok": False, "error": "unknown radio station"}
    config = _load_config()
    raw_favorites = config.get("radio_favorites", [])
    if not isinstance(raw_favorites, list):
        raw_favorites = []
    favorites = [entry for raw in raw_favorites
                 if (entry := _clean_station(raw))]
    exists = any(entry["id"] == station_id for entry in favorites)
    if exists:
        favorites = [entry for entry in favorites if entry["id"] != station_id]
    else:
        favorites.append(station)
    config["radio_favorites"] = [
        {"name": entry["name"], "url": entry["url"], "tags": entry["tags"],
         "country": entry["country"], "category": entry["category"]}
        for entry in favorites[-100:]
    ]
    _save_config(config)
    return {"ok": True, "favorite": not exists, "station_id": station_id}


def play_radio(station_id: str) -> dict:
    global _CURRENT
    station = _find_station(station_id)
    if station is None:
        return {"ok": False, "error": "unknown radio station"}
    if _PLAYER is None:
        return {"ok": False, "error": "mpv controller is unavailable"}
    try:
        import iptv_module
        url = RADIO_URL_MIGRATIONS.get(station["url"], station["url"])
        safe_url = iptv_module.validate_feed_url(url)
    except Exception as exc:
        return {"ok": False, "error": "radio URL rejected: " + str(exc)[:120]}
    ok, error = _PLAYER.start(safe_url)
    if not ok:
        _CURRENT = None
        return {"ok": False, "error": str(error or "mpv could not start")[:160]}
    _CURRENT = {"kind": "radio", "id": station["id"], "name": station["name"]}
    config = _load_config()
    raw_recent = config.get("radio_recent", [])
    if not isinstance(raw_recent, list):
        raw_recent = []
    recent = [entry for raw in raw_recent
              if (entry := _clean_station(raw)) and entry["id"] != station["id"]]
    recent.insert(0, station)
    config["radio_recent"] = [
        {"name": entry["name"], "url": entry["url"], "tags": entry["tags"],
         "country": entry["country"], "category": entry["category"]}
        for entry in recent[:30]
    ]
    _save_config(config)
    return {"ok": True, "state": "playing", "name": station["name"]}


def play_file(path: str, name: str, video: bool = False) -> dict:
    global _CURRENT
    if _PLAYER is None:
        return {"ok": False, "error": "mpv controller is unavailable"}
    extra = ["--video=yes", "--fullscreen"] if video else []
    ok, error = _PLAYER.start(path, extra_args=extra)
    if not ok:
        _CURRENT = None
        return {"ok": False, "error": str(error or "mpv could not start")[:160]}
    _CURRENT = {"kind": "video" if video else "audio", "name": str(name)[:120]}
    return {"ok": True, "state": "playing", "name": _CURRENT["name"],
            "kind": _CURRENT["kind"]}


def stop() -> dict:
    global _CURRENT
    if _PLAYER is not None:
        _PLAYER.stop()
    _CURRENT = None
    return {"ok": True, "state": "idle"}


def status() -> dict:
    if _PLAYER is None:
        return {"ok": False, "error": "mpv controller is unavailable"}
    try:
        info = _PLAYER.status() if _PLAYER.is_running() else {"running": False}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}
    return {
        "ok": True,
        "playing": bool(info.get("running")),
        "current": dict(_CURRENT) if _CURRENT and info.get("running") else None,
        "icy_title": str(info.get("icy_title") or "")[:120],
        "paused": bool(info.get("pause")),
        "buffering": bool(info.get("paused_for_cache")),
        "volume": int(info.get("volume") or 0),
    }


atexit.register(stop)
