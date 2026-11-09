"""Discovery helpers for the Syncthing service shipped with MustardOS.

MustardOS Andromeda exposes its optional Syncthing service on port 7070.
VoidDesk must attach to that service instead of starting a second daemon.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_MUOS_URL = "http://127.0.0.1:7070"


def config_candidates(storage_roots=None, app_roots=None, home=None,
                      data_dir=None):
    if storage_roots is None:
        storage_roots = os.environ.get(
            "VD_MUOS_STORAGE_ROOTS",
            "/mnt/mmc/MUOS:/mnt/sdcard/MUOS").split(":")
    if app_roots is None:
        app_roots = os.environ.get(
            "VD_MUOS_ROOTS",
            "/mnt/mmc/MUOS/application:/mnt/sdcard/MUOS/application"
        ).split(":")
    home = Path(home or Path.home())
    paths = [
        home / ".local/state/syncthing/config.xml",
        home / ".config/syncthing/config.xml",
    ]
    for root in storage_roots:
        if root:
            paths.append(Path(root) / "syncthing/config.xml")
    for root in app_roots:
        if root:
            # Older community packages kept their config beside the app.
            paths.append(Path(root).parent / "syncthing/config.xml")
    if data_dir:
        paths.extend([
            Path(data_dir) / "xfce_mnt/root/.local/state/syncthing/config.xml",
            Path(data_dir) / "xfce_mnt/root/.config/syncthing/config.xml",
        ])
    # Preserve order while removing duplicate paths.
    return list(dict.fromkeys(paths))


def _local_address(address, default_port=7070):
    address = (address or "").strip()
    if not address:
        return "127.0.0.1:%d" % default_port
    if address.startswith(":"):
        return "127.0.0.1" + address
    if address in ("0.0.0.0", "[::]", "::"):
        return "127.0.0.1:%d" % default_port
    if address.startswith("0.0.0.0:"):
        return "127.0.0.1:" + address.rsplit(":", 1)[1]
    return address


def read_connection(config_path, default_port=7070):
    path = Path(config_path)
    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError, ValueError):
        return None
    gui = root.find("gui")
    if gui is None:
        return None
    key = (gui.findtext("apikey") or "").strip()
    address = _local_address(gui.findtext("address"), default_port)
    if not key:
        api_file = path.parent / "api.txt"
        try:
            key = api_file.read_text(encoding="utf-8").strip()
        except OSError:
            return None
    if not key:
        return None
    # Syncthing's GUI address is normally host:port, not a URL.
    if "://" not in address:
        address = "http://" + address
    parsed = urlsplit(address)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return {
        "url": address.rstrip("/"),
        "key": key,
        "home": str(path.parent),
        "config": str(path),
    }


def discover_connection(storage_roots=None, app_roots=None, home=None,
                        data_dir=None, default_port=7070):
    for path in config_candidates(storage_roots, app_roots, home, data_dir):
        if not path.is_file():
            continue
        connection = read_connection(path, default_port)
        if connection:
            return connection
    return None


def is_muos_host():
    return Path("/opt/muos/script/var/func.sh").is_file()
