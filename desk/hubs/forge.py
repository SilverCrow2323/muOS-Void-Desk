# ============================================================================
#  VOID DESK — FORGE Hub
#  Installer, Autostart, Update, VoidUpdate, CLI Tools
# ============================================================================

from desk.hubs import HubMixin


class ForgeHub(HubMixin):
    """Installation, system update, and CLI tools management."""

    def __init__(self, app):
        self.app = app

    def installer(self):
        """Open the component installer."""
        self.comp_action("install")

    def autostart(self):
        """Manage autostart applications."""
        self.comp_action("autostart")

    def update(self):
        """System update via environment detail."""
        from desk.main import ENVS
        self.app.envdet_env = ENVS[0][0]
        self.app.envdet_sel = 0
        self.app.push("envdetail")

    def vdupdate(self):
        """Void system update via update server."""
        if self.app.update_data is None:
            self.app.update_checking = True
            self.app.update_data = self.app.run_busy(
                self.app.t("checking"), self.app.gh_fetch_releases)
            self.app.update_checking = False
        self.app.push("voidupdate")

    def clitools(self):
        """CLI tools hub management."""
        self.app.run_busy(self.app.t("checking"), self.app.scan_status)
        self.app.clihub_sel = 0
        self.app.push("clihub")
