# -*- coding: utf-8 -*-
# ============================================================================
#  VOID DESK — COMMUNITY Hub
#  Forum, wiki, condivisione
# ============================================================================

import os
from desk.hubs import HubMixin


class CommunityHub(HubMixin):
    """Punto di accesso alla community muOS."""

    def __init__(self, app):
        self.app = app

    def forum(self):
        """Apri il forum muOS nel browser (se disponibile)."""
        app = self.app
        url = "https://community.muos.dev"
        browser = None
        for b in ["netsurf-gtk", "firefox", "chromium", "falkon"]:
            if __import__("shutil").which(b):
                browser = b
                break
        if browser:
            try:
                __import__("subprocess").Popen([browser, url])
                app.notify("Forum", "aperto nel browser", "success")
            except Exception as e:
                app.notify("Forum", str(e)[:60], "warning")
        else:
            app.info_title = "FORUM" if app.lang == "en" else "FORUM"
            app.info_lines = [
                ("sec", "globe", "COMMUNITY FORUM"),
                ("kv", "", "Apri il link sul PC o sul telefono:", app.accent),
                ("kv", "", url, app.accent),
                ("kv", "", "Oppure installa un browser (NetSurf) da FORGE.", app.accent),
            ]
            app.scroll = 0
            app.push("info")

    def wiki(self):
        """Wiki muOS."""
        app = self.app
        url = "https://muos.dev"
        browser = None
        for b in ["netsurf-gtk", "firefox", "chromium", "falkon"]:
            if __import__("shutil").which(b):
                browser = b
                break
        if browser:
            try:
                __import__("subprocess").Popen([browser, url])
                app.notify("Wiki", "aperta nel browser", "success")
            except Exception as e:
                app.notify("Wiki", str(e)[:60], "warning")
        else:
            app.info_title = "WIKI" if app.lang == "en" else "WIKI"
            app.info_lines = [
                ("sec", "book", "MUOS WIKI"),
                ("kv", "", "https://muos.dev", app.accent),
                ("kv", "", "Documentazione ufficiale, guide e FAQ.", app.accent),
            ]
            app.scroll = 0
            app.push("info")

    def share(self):
        """Condivisione file e risorse."""
        app = self.app
        shared = os.path.join(app.DATA, "shared")
        try:
            os.makedirs(shared, exist_ok=True)
        except OSError:
            pass
        app.fm_open(start_path=shared)
