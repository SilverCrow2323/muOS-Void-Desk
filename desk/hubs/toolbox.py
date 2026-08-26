# ============================================================================
#  VOID DESK — TOOLBOX Hub
#  Calculator, Clock, Calendar, Notes, File Manager, FTP, Sync, Shell,
#  Python REPL, Editor, RSS, Weather
# ============================================================================

import sys
import time

from desk.hubs import HubMixin


class ToolboxHub(HubMixin):
    """Productivity tools hub."""

    def __init__(self, app):
        self.app = app

    def shell(self):
        """RT:Shell terminal emulator."""
        self.app.rtsh_open()

    def clockmain(self):
        """Clock widget."""
        app = self.app
        try:
            app.play_clock_gaze(entering=True)
        except Exception as e:
            sys.stderr.write(
                "bootanim clock non riuscita: %s\n" % e)
        app.push("clock")

    def calc(self):
        """Calculator."""
        app = self.app
        app.calc_expr = ""
        app.calc_sel = 0
        try:
            app.play_calc_lid(opening=True)
        except Exception as e:
            sys.stderr.write(
                "bootanim calc non riuscita: %s\n" % e)
        app.push("calc")

    def cal(self):
        """Calendar."""
        app = self.app
        app.evs = app.cal_load()
        lt = time.localtime()
        app.cal_cur = [lt.tm_year, lt.tm_mon, lt.tm_mday]
        app.cal_view = "month"
        app.ev_sel = 0
        app.push("cal")

    def notes(self):
        """Notes management."""
        app = self.app
        app.notes = app.notes_refresh()
        app.note_sel = 0
        app.push("notes")

    def rss(self):
        """RSS reader."""
        app = self.app
        try:
            app.play_rss_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim rss non riuscita: %s\n" % e)
        app.rss_sel = 0
        app.push("rss")
        if not app.rss_items and app.rss_enabled_feeds():
            app.run_busy(app.t("rss_upd"), app.rss_refresh)

    def weather(self):
        """Weather forecast."""
        app = self.app
        try:
            app.play_weather_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim meteo non riuscita: %s\n" % e)
        app.wx_sel = 0
        app.push("weather")
        cities = app.cfg.get("weather_cities") or []
        if cities and not app.wx_data:
            app.run_busy(app.t("wx_updating"), app.wx_refresh_all)

    def pyrepl(self):
        """Python REPL."""
        from desk.main import PYSCRIPTS_DIR
        app = self.app
        app.py_ns = {}
        app.py_out = ["Python %s // host muOS" %
                      sys.version.split()[0], ">>> "]
        try:
            app.play_python_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim python non riuscita: %s\n" % e)

        def run_and_open(p):
            app.py_runfile(p)
            app.push("pyrepl")
        app.fm_open(start_path=PYSCRIPTS_DIR,
                    ext_filter={".py"}, pick=run_and_open)

    def fileman(self):
        """File manager."""
        app = self.app
        try:
            app.play_files_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim files non riuscita: %s\n" % e)
        app.fm_open()

    def ftp(self):
        """FTP client."""
        app = self.app
        try:
            app.play_ftp_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim ftp non riuscita: %s\n" % e)
        app.ftp_prof_sel = 0
        app.push("ftpprof")

    def editor(self):
        """VOID TEXT editor."""
        from desk.main import TEXTS_DIR, TEXT_EXTS
        app = self.app
        try:
            app.play_editor_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim editor non riuscita: %s\n" % e)
        app.fm_open(start_path=TEXTS_DIR, ext_filter=TEXT_EXTS)

    def sync(self):
        """File sync / rsync."""
        app = self.app
        try:
            app.play_sync_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim sync non riuscita: %s\n" % e)
        app.sync_open()

    def tsgui(self):
        """Tailnet GUI - also accessible from toolbox."""
        app = self.app
        try:
            app.play_ts_intro()
        except Exception as e:
            sys.stderr.write(
                "bootanim tailscale non riuscita: %s\n" % e)
        app.ts_open()

    def tool_open(self, key):
        """Open a CLI tool package."""
        from desk.main import TOOL_PKGS
        app = self.app
        label, pkgs = TOOL_PKGS[key]
        app.tool_open(key)
