# -*- coding: utf-8 -*-
# ============================================================================
#  VOID DESK — LEGACY Hub
#  Archivio, memoriale e chiusura del ciclo
# ============================================================================

import os
from desk.hubs import HubMixin


class LegacyHub(HubMixin):
    """Archivio e memoriale del progetto."""

    def __init__(self, app):
        self.app = app

    def archive(self):
        """Archivio delle versioni precedenti."""
        app = self.app
        archive_dir = os.path.join(app.DATA, "archive")
        try:
            os.makedirs(archive_dir, exist_ok=True)
        except OSError:
            pass
        app.fm_open(start_path=archive_dir)

    def memorial(self):
        """Memoriale: storia e crediti del progetto."""
        app = self.app
        app.info_title = "MEMORIALE" if app.lang == "it" else "MEMORIAL"
        lines = [
            ("sec", "info", "VOIDDESK \u2014 STORIA" if app.lang == "it" else "VOIDDESK \u2014 HISTORY"),
            ("kv", "", "v10.14 \u2014 Nexus: planetario 4 orbite, 15 nodi", app.accent),
            ("kv", "", "v10.0 \u2014 NEXUS: planetario 3D", app.accent),
            ("kv", "", "v9.0 \u2014 Net-Sphere: orbite e satelliti", app.accent),
            ("kv", "", "v8.0 \u2014 Chou Henka: boost e governor", app.accent),
            ("kv", "", "v7.0 \u2014 Media Vault: radio, IPTV, BGM", app.accent),
            ("kv", "", "v6.0 \u2014 UPLINK: rete, Bluetooth, hotspot", app.accent),
            ("kv", "", "v5.0 \u2014 FORGE: installer e updater", app.accent),
            ("kv", "", "v4.0 \u2014 Toolbox: calcolatrice, clock, note", app.accent),
            ("kv", "", "v3.0 \u2014 Workshop: diagnosi e monitor", app.accent),
            ("kv", "", "v2.0 \u2014 MuOS Apps: gestione applicazioni", app.accent),
            ("kv", "", "v1.0 \u2014 Prima release: desktop XFCE", app.accent),
            ("sec", "gear", "CREDITI" if app.lang == "it" else "CREDITS"),
            ("kv", "", "SPDW Factory \u2014 SilverCrow2323", app.accent),
            ("kv", "", "MuOS Team \u2014 MustardOS", app.accent),
            ("kv", "", "Community \u2014 tester e contributori", app.accent),
        ]
        app.info_lines = lines
        app.scroll = 0
        app.push("info")
