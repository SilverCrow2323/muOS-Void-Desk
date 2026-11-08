# outdesk/VoidCast/voidcast/addons/recplayer/addon.py
# -*- coding: utf-8 -*-
# VOIDCAST addon // Recordings Player
def _open(api):
    api.open_screen("recordings")

def register(api):
    return [
        {"label": api.t("rec.label_play"), "action": _open,
         "context": "menu"},
    ]
