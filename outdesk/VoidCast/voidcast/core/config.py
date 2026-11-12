# outdesk/VoidCast/voidcast/core/config.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.config — configurazione persistente + percorsi
# SPDW Factory — universo ß approved.

import json
import os

# voidcast/core/config.py -> voidcast/ -> <app root>
PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(PKG_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
EPG_CACHE_DIR = os.path.join(CACHE_DIR, "epg")
PLAYLIST_DIR = os.path.join(DATA_DIR, "playlists")
REC_DIR = os.path.join(DATA_DIR, "recordings")
ADDON_DIR = os.path.join(PKG_DIR, "addons")
PRESETS_DIR = os.path.join(ROOT_DIR, "presets")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
CONFIG_DEFAULT_PATH = os.path.join(PRESETS_DIR, "config.default.json")
LOG_PATH = os.path.join(DATA_DIR, "voidcast.log")

for _d in (DATA_DIR, CACHE_DIR, EPG_CACHE_DIR, PLAYLIST_DIR, REC_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except OSError:
        pass

# First-run seed: this used to be mux_launch.sh's job (standalone
# install), copying presets/config.default.json -> data/config.json
# if the latter didn't exist yet. Now that VoidCast is launched
# directly by VoidDesk with no launcher script of its own, that one
# small step moved in here so it still happens.
if not os.path.exists(CONFIG_PATH) and os.path.exists(CONFIG_DEFAULT_PATH):
    try:
        import shutil as _shutil
        _shutil.copy(CONFIG_DEFAULT_PATH, CONFIG_PATH)
    except OSError:
        pass

APP_NAME = "VOIDCAST"
APP_VERSION = "1.0.0"
APP_TAGLINE = "SPDW IPTV SUITE // KYOMU BROADCAST NODE"

# Liste preset (GitHub, iptv-org — free, mondiali)
PRESET_PLAYLISTS = [
    ("iptv-org // MONDO (index)", "https://iptv-org.github.io/iptv/index.m3u"),
    ("iptv-org // ITALIA", "https://iptv-org.github.io/iptv/countries/it.m3u"),
    ("iptv-org // NEWS", "https://iptv-org.github.io/iptv/categories/news.m3u"),
    ("iptv-org // MUSICA", "https://iptv-org.github.io/iptv/categories/music.m3u"),
    ("iptv-org // FILM", "https://iptv-org.github.io/iptv/categories/movies.m3u"),
]

DEFAULTS = {
    "language": "en",
    "muos_profile": "auto",  # auto | andromeda | not_andromeda                # en | it
    "active_playlist": None,        # id playlist attiva
    "playlists": [],                # [{id, name, source(url|path), type:"url"/"file"}]
    "view_mode": "list",            # list | grid | guide
    "epg_manual_urls": [],          # URL EPG aggiunti a mano
    "epg_use_playlist_sources": True,
    "epg_max_age_hours": 12,
    "player_backend": "auto",       # auto | mpv | ffplay
    "player_cache_secs": 5,
    "user_agent": "VLC/3.0.20 LibVLC/3.0.20",
    "favorites": [],                # lista di url canale
    "last_group": "*",
    "show_logos": True,             # scarica/mostra i loghi tvg-logo (cache su disco)
    "button_map": {                 # joydev js1 indices verified on RG35XX H
        "0": "A", "1": "B", "2": "X", "3": "Y",
        "4": "L1", "5": "R1", "6": "L2", "7": "R2",
        "8": "SELECT", "9": "START", "10": "MENU", "11": "L3", "12": "R3",
    },
    "theme_accent": "crimson",
    "anim_intensity": 2,        # 0=off 1=subtle 2=normal 3=intense
    "rec_dir": "/mnt/mmc/MUOS/voidcast",   # registrazioni (SELECT in playback)      # crimson | cyan | amber
}


class Config(object):
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                stored = json.load(f)
            for k, v in stored.items():
                self.data[k] = v
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()

    # --- playlist helpers -------------------------------------------------
    def playlists(self):
        return self.data.get("playlists", [])

    def add_playlist(self, name, source, ptype):
        pid = "pl_%d" % (max([0] + [int(p["id"].split("_")[1]) for p in self.playlists()]) + 1)
        entry = {"id": pid, "name": name, "source": source, "type": ptype}
        self.data.setdefault("playlists", []).append(entry)
        if not self.data.get("active_playlist"):
            self.data["active_playlist"] = pid
        self.save()
        return entry

    def remove_playlist(self, pid):
        self.data["playlists"] = [p for p in self.playlists() if p["id"] != pid]
        if self.data.get("active_playlist") == pid:
            pls = self.playlists()
            self.data["active_playlist"] = pls[0]["id"] if pls else None
        self.save()

    def active_playlist(self):
        pid = self.data.get("active_playlist")
        for p in self.playlists():
            if p["id"] == pid:
                return p
        return None

    def toggle_favorite(self, url):
        favs = self.data.setdefault("favorites", [])
        if url in favs:
            favs.remove(url)
        else:
            favs.append(url)
        self.save()
        return url in favs
