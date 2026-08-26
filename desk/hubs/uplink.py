# ============================================================================
#  VOID DESK — UPLINK Hub
#  Network: WiFi, Hotspot, Bluetooth, PC up, BaseStation, Syncthing,
#  Tailscale, FTPiercer, Network Probe, Device Remapper, Wired Controller
# ============================================================================

import os
import sys

from desk.hubs import HubMixin


class UplinkHub(HubMixin):
    """Network and connectivity management."""

    def __init__(self, app):
        self.app = app

    def wifi(self):
        """WiFi network management."""
        app = self.app
        app.wm_sel = 0
        app.wm_nets = app.run_busy(
            app.t("wm_scan"),
            app.wm_scan,
            steps=[
                "scanning networks...",
                "parsing results...",
                "building list...",
            ],
            accent=(74, 206, 224),
            icon="wifi") or []
        app.push("wifimgr")

    def hotspot(self):
        """Hotspot management."""
        self.app.push("hotmgr")

    def bt(self):
        """Bluetooth management."""
        app = self.app
        app.bt_sel = 0
        app.bt_devs = app.run_busy("bluetooth...",
                                   lambda: app.bt_list(False)) or []
        app.push("btmgr")

    def pcup(self):
        """PC uplink client management."""
        app = self.app
        if not app.pc_servers:
            app.pc_scanning = True
            app.run_busy(app.t("checking"), app.pcup_scan)
            app.pc_scanning = False
        app.pc_srv_sel = 0
        app.push("pcupsrv")

    def basestation(self):
        """BaseStation web server."""
        self.app.push("bstationsend")

    def sync(self):
        """File sync / rsync."""
        app = self.app
        try:
            app.play_sync_intro()
        except Exception as e:
            sys.stderr.write("bootanim sync non riuscita: %s\n" % e)
        app.sync_open()

    def tsgui(self):
        """Tailnet GUI management."""
        app = self.app
        try:
            app.play_ts_intro()
        except Exception as e:
            sys.stderr.write("bootanim tailnet non riuscita: %s\n" % e)
        app.ts_open()

    def ftp(self):
        """FTP client."""
        app = self.app
        try:
            app.play_ftp_intro()
        except Exception as e:
            sys.stderr.write("bootanim ftp non riuscita: %s\n" % e)
        app.ftp_prof_sel = 0
        app.push("ftpprof")

    def netdiag(self):
        """Network probe diagnostics."""
        from desk.main import net_test
        app = self.app
        st = app.status_snapshot()
        ip = app.own_ip() or "non disponibile"
        internet = app.run_busy(app.t("checking"), net_test,
                                accent=(74, 206, 224),
                                icon="globe")
        base = "attivo" if app.bstation_srv is not None else "fermo"
        app.netprobe_data = {
            "ip": ip,
            "internet": internet,
            "base": base,
            "st": st,
        }
        app.info_title = "NETWORK PROBE"
        app.scroll = 0
        app.push("netprobe")

    def deviceremapper(self):
        """Device key mapping."""
        self.app.controller_hub.map()

    def wiredcontroller(self):
        """External controller management."""
        self.app.controller_hub.devices()
