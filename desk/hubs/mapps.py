# ============================================================================
#  VOID DESK — MAPPS Hub
#  Application Discovery, Governor, Glyph Manager
# ============================================================================

from desk.hubs import HubMixin


class MappsHub(HubMixin):
    """muOS applications management."""

    def __init__(self, app):
        self.app = app

    def app_discovery(self, key):
        """Browse and launch muOS applications."""
        app = self.app
        if key == "A":
            app.scan_muos()
            app.push("mapps")
        elif key == "B":
            app.pop_state()

    def governor(self, key):
        """CPU governor management."""
        app = self.app
        if key == "A":
            app.push("governor")
        elif key == "B":
            app.pop_state()

    def glyph_manager(self, key):
        """Glyph icon management."""
        app = self.app
        if key == "A":
            app.push("glyphs")
        elif key == "B":
            app.pop_state()
