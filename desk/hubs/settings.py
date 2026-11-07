# ============================================================================
#  VOID DESK — SETTINGS Hub
#  Theme, Font, Effects, Language, Controller, Status Bar, Boot Animation
# ============================================================================

from desk.hubs import HubMixin


class SettingsHub(HubMixin):
    """Settings management hub."""

    def __init__(self, app):
        self.app = app

    def theme(self, key):
        """Theme selection."""
        app = self.app
        if key == "A":
            app.push("themeset")
        elif key == "B":
            app.pop_state()

    def font(self, key):
        """Font and text scaling settings."""
        app = self.app
        if key == "A":
            app.push("fontset")
        elif key == "B":
            app.pop_state()

    def vfx(self, key):
        """Visual effects settings."""
        app = self.app
        if key == "A":
            app.push("vfxset")
        elif key == "B":
            app.pop_state()

    def language(self, key):
        """Language selection."""
        app = self.app
        if key == "A":
            app.push("langset")
        elif key == "B":
            app.pop_state()

    def controller(self, key):
        """Controller settings."""
        app = self.app
        if key == "A":
            app.push("ctrlset")
        elif key == "B":
            app.pop_state()

    def status_bar(self, key):
        """Status bar configuration."""
        app = self.app
        if key == "A":
            app.push("statusbarset")
        elif key == "B":
            app.pop_state()

    def boot_anim(self, key):
        """Boot animation settings."""
        app = self.app
        if key == "A":
            app.push("boottomb")
        elif key == "B":
            app.pop_state()
