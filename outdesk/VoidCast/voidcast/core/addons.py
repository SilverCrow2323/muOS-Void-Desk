# outdesk/VoidCast/voidcast/core/addons.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.addons — sistema addon/tools
#
# Un addon è una cartella in voidcast/addons/<nome>/ con:
#   addon.json  -> {"name": "...", "desc": "...", "entry": "addon.py"}
#   addon.py    -> deve esporre register(api) -> lista di azioni:
#                  [{"label": str, "action": callable(api), "context": "menu"|"channel"}]
#
# L'API passata agli addon (AddonAPI) espone lo stato dell'app in modo
# controllato: config, canale corrente, EPG, notifiche toast, directory dati.
# Questo è lo spiraglio per PVR, registrazione, catch-up, telemetria, ecc.

import importlib.util
import json
import os
import traceback

from . import config as C
from . import i18n


class AddonAPI(object):
    """Superficie stabile esposta agli addon. Non rompere il contratto."""

    def __init__(self, app):
        self._app = app
        self.config = app.cfg
        self.data_dir = C.DATA_DIR
        self.recordings_dir = C.REC_DIR

    @property
    def current_channel(self):
        return getattr(self._app, "current_channel", None)

    @property
    def playlist(self):
        return getattr(self._app, "playlist", None)

    @property
    def epg(self):
        return getattr(self._app, "epg", None)

    def toast(self, msg, ok=True):
        self._app.toast(msg, ok)

    def t(self, key, *args):
        return i18n.t(key, *args)

    @property
    def language(self):
        return i18n.get_lang()

    def open_screen(self, name):
        screens = getattr(self._app, "screens", {}) or {}
        factory = screens.get(name)
        if factory is None:
            return False
        try:
            self._app.push(factory())
            return True
        except Exception:
            return False

    def log(self, msg):
        try:
            with open(C.LOG_PATH, "a", encoding="utf-8") as f:
                f.write("[addon] %s\n" % msg)
        except OSError:
            pass


class AddonManager(object):
    def __init__(self, app):
        self.app = app
        self.api = AddonAPI(app)
        self.addons = []        # [{"meta":..., "actions":[...]}]
        self.errors = []

    def discover(self):
        self.addons, self.errors = [], []
        base = C.ADDON_DIR
        if not os.path.isdir(base):
            return
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            meta_path = os.path.join(folder, "addon.json")
            if not os.path.isfile(meta_path):
                continue
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                entry = os.path.join(folder, meta.get("entry", "addon.py"))
                spec = importlib.util.spec_from_file_location(
                    "voidcast_addon_" + name, entry)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                actions = mod.register(self.api) or []
                self.addons.append({"meta": meta, "actions": actions})
            except Exception:  # noqa: BLE001
                self.errors.append((name, traceback.format_exc(limit=2)))

    def menu_actions(self):
        out = []
        for a in self.addons:
            for act in a["actions"]:
                if act.get("context", "menu") == "menu":
                    out.append((a["meta"].get("name", "?"), act))
        return out

    def channel_actions(self):
        out = []
        for a in self.addons:
            for act in a["actions"]:
                if act.get("context") == "channel":
                    out.append((a["meta"].get("name", "?"), act))
        return out
