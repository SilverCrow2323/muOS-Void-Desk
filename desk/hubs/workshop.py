# ============================================================================
#  VOID DESK — WORKSHOP Hub
#  Stats, Diag, Monitor, Storage, Boost, CHD, Doppel, Clean, Logs, Backup
# ============================================================================

import shutil
import time

from desk.hubs import HubMixin


class WorkshopHub(HubMixin):
    """System maintenance and diagnostics."""

    def __init__(self, app):
        self.app = app

    def devcheck(self):
        """Device Check:Rt — pronto soccorso unificato (triage +
        diagnostica + memorie + pulizia) navigabile a reparti."""
        app = self.app
        app.devcheck_dept = 0
        app.devcheck_diag_mode = 0
        app._dc_sel_sel = 0
        app._dc_sel_cats = ["image", "envs", "sys", "net", "storage"]
        app._dc_net = None
        app._dc_rec = None
        app.push("devcheck")

    def stats(self):
        """Device statistics."""
        app = self.app
        app.info_title = "DEVICE STATS"
        app.info_lines = app.run_busy(app.t("checking"),
                                      app.void_stats) or []
        app.scroll = 0
        app.push("info")

    def diag(self):
        """Full diagnostic scan."""
        app = self.app

        def go():
            app.diag_scan_steps = app.diag_steps()
            app.diag_scan_idx = 0
            app.diag_scan_t0 = time.time()
            app.diag_scan_log = []
            app.diag_scan_results = [("sec", "gear", "VOID DIAG")]
            app.push("diagscan")
        app.confirm = (("Device pronto al setaccio.\n"
                       "Procedere?" if app.lang == "it"
                       else "Device ready for the sieve.\n"
                       "Proceed?"), go, "VOID DIAG", "gear",
                      None, "triage")
        app.push("confirm")

    def monitor(self):
        """System monitor (CPU, RAM, net, temp)."""
        app = self.app
        app.mon = {"cpu": [], "ram": [], "net": [], "tmp": [],
                   "last": None, "t": 0}
        app.mon_tab = 0
        app.push("monitor")

    def storage(self):
        """Storage analysis."""
        app = self.app
        app.info_title = ("SPAZIO ARCHIVIAZIONE" if app.lang == "it"
                          else "STORAGE")
        app.info_lines = app.run_busy(app.t("checking"),
                                      app.storage_lines) or []
        app.scroll = 0
        app.push("info")

    def boost(self):
        """System boost configuration."""
        app = self.app
        app.boost_sel = 0
        app.push("boostcfg")

    def chd(self):
        """Disc crusher / CHD converter."""
        from desk.main import NO_R, DIM
        app = self.app
        app.run_busy(app.t("checking"), app.scan_status)
        chdman_found = shutil.which("chdman") is not None
        if not chdman_found and not app.status.get("mame-tools (chdman)"):
            app.info_lines = [
                ("sec", "disk", "DISC CRUSHER"),
                ("kv", "", "chdman non è installato" if
                 app.lang == "it" else
                 "chdman is not installed", NO_R),
                ("kv", "", "Void Installer > STRUMENTI/CLI > "
                 "mame-tools" if app.lang == "it" else
                 "Void Installer > TOOLS/CLI > mame-tools", DIM)]
            app.scroll = 0
            app.push("info")
        else:
            app.chd_browse_open()

    def doppel(self):
        """Doppelganger duplicate finder."""
        self.app.doppel_open()

    def clean(self):
        """Package cache cleaning."""
        self.comp_action("clean")

    def logs(self):
        """Application logs viewer."""
        app = self.app
        app.sel_log = 1
        app.logs = app.build_logs()
        app.push("logs")

    def logdashboard(self):
        """Complete log control panel."""
        app = self.app
        app.push("logdashboard")

    def voiddecontext(self):
        """Generate a context pack of the entire application."""
        self.app.push("voiddecontext")

    def backup(self):
        """Backup management."""
        app = self.app
        app.bak_sel = 0
        app.push("backup")