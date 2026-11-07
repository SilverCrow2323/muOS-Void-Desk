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

    def engine(self, key):
        """Frontend engine toggle (py | love). Writes to desk_config.json."""
        app = self.app
        if key == "A":
            cur = app.cfg.get("engine", "love")
            nxt = "py" if cur == "love" else "love"
            app.cfg["engine"] = nxt
            try:
                import json, os
                from desk.const import DATA
                with open(os.path.join(DATA, "desk_config.json"), "w") as f:
                    json.dump(app.cfg, f, indent=1)
            except Exception:
                pass
            try:
                app.notify("Engine: " + nxt.upper() + " (restart to apply)")
            except Exception:
                pass
        elif key == "B":
            app.pop_state()
