# -*- coding: utf-8 -*-
# ============================================================================
#  VOID DESK — OUTERDESK Hub
#  App standalone e strumenti portatili
# ============================================================================

from desk.hubs import HubMixin


class OuterdeskHub(HubMixin):
    """Outer-Desk: app standalone e strumenti portatili."""

    def __init__(self, app):
        self.app = app

    def apps(self):
        """Lista app Outer-Desk."""
        app = self.app
        app.od_sel = 0
        app.od_scroll = 0
        app.od_deps_cache = {}
        app.push("outerdesk")
