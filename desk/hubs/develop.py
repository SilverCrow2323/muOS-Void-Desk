# -*- coding: utf-8 -*-
# ============================================================================
#  VOID DESK — DEVELOP Hub
#  Strumenti per sviluppatori: REPL, editor, build
# ============================================================================

import os
from desk.hubs import HubMixin


class DevelopHub(HubMixin):
    """Strumenti di sviluppo per muOS."""

    def __init__(self, app):
        self.app = app

    def repl(self):
        """Python REPL interattivo."""
        app = self.app
        app.py_ns = {}
        app.py_out = ["Python %s // host muOS" % __import__("sys").version.split()[0], ">>> "]
        app.push("pyrepl")

    def editor(self):
        """Editor di testo (VOID EDIT)."""
        app = self.app
        from desk.main import TEXTS_DIR, TEXT_EXTS
        try:
            app.play_editor_intro()
        except Exception as e:
            __import__("sys").stderr.write("bootanim editor non riuscita: %s\n" % e)
        app.fm_open(start_path=TEXTS_DIR, ext_filter=TEXT_EXTS)

    def builder(self):
        """Strumenti di build (compilazione pacchetti)."""
        app = self.app
        app.info_title = "BUILD TOOLS" if app.lang == "en" else "STRUMENTI DI BUILD"
        lines = [
            ("sec", "gear", "PACCHETTI DISPONIBILI" if app.lang == "it" else "AVAILABLE PACKAGES"),
            ("kv", "", "\u2022 muxapp-builder \u2014 crea .muxapp da cartelle", app.accent),
            ("kv", "", "\u2022 muxthm-builder \u2014 crea temi .muxthm", app.accent),
            ("kv", "", "\u2022 banim-pack \u2014 animazioni di boot .banim", app.accent),
            ("kv", "", "\u2022 chdman \u2014 converti immagini CD in CHD", app.accent),
            ("kv", "", "\u2022 ffmpeg \u2014 conversione audio/video", app.accent),
        ]
        app.info_lines = lines
        app.scroll = 0
        app.push("info")
