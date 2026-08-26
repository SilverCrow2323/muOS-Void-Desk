# ============================================================================
#  VOID DESK — Hub Base Module
#  Base classes for hub mixins
# ============================================================================


class HubMixin:
    """Base mixin for hub modules. Provides common hub utilities."""

    def comp_action(self, key):
        """Void Installer action router."""
        import os
        app = self.app
        if key in ("install", "remove", "autostart"):
            if not os.path.exists(os.path.join(app.DATA, ".xfce_ready")):
                app.info_lines = [("sec", "info", app.t("need_xfce"))]
                app.push("info")
                return
            app.run_busy(app.t("mounting"), app.scan_status)
            app.build_rows()
            app.marked.clear()
            app.mode = key
            app.push("comp" if key != "autostart" else "autostart")
            if key == "autostart":
                app.auto_rows()
        elif key == "update":
            os.makedirs(app.DATA, exist_ok=True)
            with open(os.path.join(app.DATA, ".install_pkg"), "w") as f:
                f.write("update\n-\n")
            app.handoff(app.t("ho_update"))
            app.exit_code = app.EXIT_APT_UPDATE
            app.running = False
        elif key == "clean":
            app.info_lines = app.run_busy(app.t("cleaning"),
                                            app.apt_clean) or []
            app.scroll = 0
            app.push("info")
        elif key == "shell":
            app.open_real_terminal()


from desk.hubs.forge import ForgeHub
from desk.hubs.uplink import UplinkHub
from desk.hubs.media import MediaHub
from desk.hubs.workshop import WorkshopHub
from desk.hubs.toolbox import ToolboxHub
from desk.hubs.mapps import MappsHub
from desk.hubs.settings import SettingsHub
from desk.hubs.info import InfoHub
from desk.hubs.shutdown import ShutdownHub
from desk.hubs.controller import ControllerHub
from desk.hubs.games import GamesHub
from desk.hubs.develop import DevelopHub
from desk.hubs.community import CommunityHub
from desk.hubs.outerdesk import OuterdeskHub
from desk.hubs.legacy import LegacyHub
