# ============================================================================
#  VOID DESK — INFO Hub
#  About, Manual, Guide, Manifesto, Update
# ============================================================================

import time

from desk.hubs import HubMixin


class InfoHub(HubMixin):
    """Information and system update hub."""

    def __init__(self, app):
        self.app = app

    def about(self):
        """Show about screen."""
        app = self.app
        app.info_title = ("INFO PROGETTO" if app.lang == "it"
                          else "PROJECT INFO")
        app.info_lines = app.about_lines()
        app.scroll = 0
        app.push("info")

    def manual(self):
        """Show technical manual."""
        app = self.app
        app.man_sel = 0
        app.push("manual")

    def guide(self):
        """Show controls guide."""
        app = self.app
        app.info_title = ("GUIDA CONTROLLI" if app.lang == "it"
                          else "CONTROLS GUIDE")
        app.info_lines = app.guide_lines()
        app.scroll = 0
        app.push("info")

    def manifesto(self):
        """Show project manifesto."""
        app = self.app
        app.scroll = 0
        app.push("manifesto")

    def voidupdate(self):
        """Void system update check."""
        app = self.app
        if app.update_data is None:
            app.update_checking = True
            app.update_data = app.run_busy(
                app.t("checking"), app.gh_fetch_releases)
            app.update_checking = False
        app.updmenu_sel = 0
        app.updmenu_scroll = 0
        app.push("voidupdate")

    def cursedev(self):
        """Activate CURSEDEV secret screen."""
        from desk.main import CURSEDEV_CATEGORIES
        app = self.app
        app.cursedev_secret_glitch_phase = 1
        app.cursedev_secret_glitch_t0 = time.time()
        app._cursedev_notif_sent = False
        app.cursedev_menu_sel = 0
        app.cursedev_category_sel = 0
        app.cursedev_submenu_active = False
        app.cursedev_menu_items = CURSEDEV_CATEGORIES
        app.cursedev_category_keys = list(CURSEDEV_CATEGORIES.keys())
        app.push("cursedevsecret")
        try:
            app.play("rerezero2")
        except Exception:
            pass
