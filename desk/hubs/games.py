# -*- coding: utf-8 -*-
# ============================================================================
#  VOID DESK — GAMES Hub
#  PortMaster, giochi nativi, collezioni
# ============================================================================

import os
from desk.hubs import HubMixin


class GamesHub(HubMixin):
    """Gestione giochi e porting per muOS."""

    def __init__(self, app):
        self.app = app

    def portmaster(self):
        """Avvia PortMaster (già presente in muOS)."""
        app = self.app
        pm_paths = [
            "/mnt/mmc/MUOS/PortMaster/PortMaster.sh",
            "/mnt/sdcard/MUOS/PortMaster/PortMaster.sh",
            "/opt/muos/PortMaster/PortMaster.sh",
        ]
        pm = None
        for p in pm_paths:
            if os.path.exists(p):
                pm = p
                break
        if not pm:
            app.notify("PortMaster", "non trovato nel sistema", "warning")
            return
        app.handoff("AVVIO PORTMASTER..." if app.lang == "it" else "STARTING PORTMASTER...")
        app.exit_code = 0
        app.running = False

    def native(self):
        """Giochi nativi .muxapp."""
        app = self.app
        game_roots = [
            "/mnt/mmc/MUOS/application",
            "/mnt/sdcard/MUOS/application",
            "/mnt/mmc/ROMS/PORTS",
            "/mnt/sdcard/ROMS/PORTS",
        ]
        start_path = "/mnt/mmc/MUOS/application"
        if os.path.isdir(start_path):
            app.fm_open(start_path=start_path)

    def collections(self):
        """Collezioni di giochi (raccolte tematiche)."""
        app = self.app
        app.info_title = "COLLEZIONI" if app.lang == "it" else "COLLECTIONS"
        collections = [
            ("Retro Classics", "NES, SNES, Genesis"),
            ("Handheld Heroes", "Game Boy, GBA, PSP"),
            ("Arcade Legends", "MAME, CPS, Neo Geo"),
            ("PC Ports", "PortMaster, ScummVM"),
            ("Homebrew", "Giochi indie e homebrew"),
        ]
        lines = [("sec", "folder", "COLLEZIONI DISPONIBILI" if app.lang == "it" else "AVAILABLE COLLECTIONS")]
        for name, desc in collections:
            lines.append(("kv", "", f"{name} \u2014 {desc}", app.accent))
        app.info_lines = lines
        app.scroll = 0
        app.push("info")
