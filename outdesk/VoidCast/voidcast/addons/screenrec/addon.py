# outdesk/VoidCast/voidcast/addons/screenrec/addon.py
# -*- coding: utf-8 -*-
# VOIDCAST addon // Screen Recorder v2
# Records the current channel, whether foreground or background playback.
from core import recorder, i18n

def _start(api):
    ch = api.current_channel
    if ch is None:
        bg = getattr(api._app, "bgplay", None)
        if bg and bg.active and bg.channel:
            ch = bg.channel
    if ch is None:
        api.toast(api.t("rec.no_channel"), ok=False)
        return
    ok, msg = recorder.start(ch.url, ch.name, api.recordings_dir,
                             api.config.get("user_agent", ""))
    if ok:
        api.toast(api.t("rec.start_toast", ch.name))
        api.log("REC: " + msg)
    else:
        api.toast(api.t("rec.ffmpeg_ko", msg), ok=False)

def _stop(api):
    name = recorder.stop()
    if name:
        api.toast(api.t("rec.stopped", name))
    else:
        api.toast(api.t("rec.no_active"), ok=False)

def _status(api):
    if recorder.is_active():
        api.toast(api.t("rec.in_progress", recorder.current()))
        return
    import os
    d = api.recordings_dir
    n = len([f for f in os.listdir(d) if f.endswith(".ts")]) if os.path.isdir(d) else 0
    api.toast(api.t("rec.none_status", n))

def _open_recordings(api):
    api.open_screen("recordings")

def register(api):
    return [
        {"label": api.t("rec.label_start"), "action": _start,
         "context": "menu"},
        {"label": api.t("rec.label_stop"), "action": _stop,
         "context": "menu"},
        {"label": api.t("rec.label_status"), "action": _status,
         "context": "menu"},
        {"label": api.t("rec.label_open"), "action": _open_recordings,
         "context": "menu"},
    ]
