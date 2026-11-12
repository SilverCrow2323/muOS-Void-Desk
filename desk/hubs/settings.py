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
        """Frontend engine selection; LÖVE remains opt-in when packaged."""
        app = self.app
        if key == "A":
            import json
            import os
            from desk.const import DATA

            current = app.cfg.get("engine", "py")
            next_engine = "py" if current == "love" else "love"
            if os.environ.get("VOIDDESK_PLATFORM") == "muos":
                app_dir = os.environ.get("VOIDDESK_APP_DIR", "")
                love_runtime = os.path.join(app_dir, "lib", "liblove-11.5.so")
                if next_engine == "love" and not os.path.isfile(love_runtime):
                    app.notify("LÖVE runtime is not included in this muOS build")
                    return

            app.cfg["engine"] = next_engine
            try:
                config_path = os.path.join(str(DATA), "desk_config.json")
                temporary = config_path + ".tmp"
                with open(temporary, "w", encoding="utf-8") as stream:
                    json.dump(app.cfg, stream, indent=1)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, config_path)
            except OSError as exc:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                app.notify("Cannot save engine setting: " + str(exc))
                return
            app.notify("Engine: " + next_engine.upper() + " (restart to apply)")
        elif key == "B":
            app.pop_state()
