# ============================================================================
#  VOID DESK — AUTOPSIA
#  Strumento di diagnosi completa del sistema
# ============================================================================

import os
import time
import subprocess
import psutil

class Autopsia:
    """Diagnostica completa del sistema."""

    def __init__(self, app):
        self.app = app
        self.results = []

    def run_all(self):
        """Esegue tutti i controlli di diagnostica."""
        self.results = []
        self._check_system()
        self._check_memory()
        self._check_storage()
        self._check_network()
        self._check_outerdesk()
        self._check_audio()
        self._check_display()
        return self.results

    def _check_system(self):
        self.results.append(("sec", "info", "SISTEMA"))
        try:
            un = os.uname()
            self.results.append(("kv", "KERNEL", "%s %s" % (un.sysname, un.release), (96, 225, 120)))
        except Exception:
            self.results.append(("kv", "KERNEL", "N/D", (238, 62, 58)))
        try:
            up = int(float(open("/proc/uptime").read().split()[0]))
            self.results.append(("kv", "UPTIME", "%dh %02dm" % (up // 3600, (up % 3600) // 60), (96, 225, 120)))
        except Exception:
            self.results.append(("kv", "UPTIME", "N/D", (238, 62, 58)))
        try:
            for p in ("/opt/muos/config/system/version", "/opt/muos/config/version.txt"):
                if os.path.exists(p):
                    ver = open(p).read().strip().splitlines()[0]
                    self.results.append(("kv", "muOS", ver, (96, 225, 120)))
                    break
        except Exception:
            pass

    def _check_memory(self):
        self.results.append(("sec", "task", "MEMORIA"))
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            tot = avail = 0
            for ln in lines:
                if ln.startswith("MemTotal:"):
                    tot = int(ln.split()[1])
                elif ln.startswith("MemAvailable:"):
                    avail = int(ln.split()[1])
            if tot:
                used = tot - avail
                pct = used * 100 // tot
                col = (238, 62, 58) if pct > 85 else (96, 225, 120)
                self.results.append(("kv", "RAM", "%d MB / %d MB (%d%%)" % (used // 1024, tot // 1024, pct), col))
        except Exception:
            self.results.append(("kv", "RAM", "N/D", (238, 62, 58)))

    def _check_storage(self):
        self.results.append(("sec", "disk", "ARCHIVIAZIONE"))
        for lbl, p in (("SD1 (mmc)", "/mnt/mmc"), ("SD2 (sdcard)", "/mnt/sdcard")):
            try:
                st = os.statvfs(p)
                free = st.f_bavail * st.f_frsize
                total = st.f_blocks * st.f_frsize
                pct = 100 - (free * 100 // total) if total else 0
                col = (238, 62, 58) if pct > 92 else (96, 225, 120)
                self.results.append(("kv", lbl.upper(), "%s liberi / %s (%d%%)" % (self._human(free), self._human(total), pct), col))
            except Exception:
                self.results.append(("kv", lbl.upper(), "N/D", (238, 62, 58)))
        img = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "xfce.img")
        if os.path.exists(img):
            self.results.append(("kv", "IMMAGINE XFCE", self._human(os.path.getsize(img)), (96, 225, 120)))

    def _check_network(self):
        self.results.append(("sec", "wifi", "RETE"))
        try:
            ssid = ""
            try:
                out = subprocess.check_output(["iwgetid", "-r"], stderr=subprocess.DEVNULL, text=True).strip()
                ssid = out or ""
            except Exception:
                pass
            conn = bool(ssid)
            self.results.append(("kv", "WIFI", ssid or "non connesso", (96, 225, 120) if conn else (148, 150, 152)))
        except Exception:
            self.results.append(("kv", "WIFI", "N/D", (238, 62, 58)))

    def _check_outerdesk(self):
        self.results.append(("sec", "gear", "OUTER-DESK"))
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from outdesk.outdeskintro import OUTERDESK_APPS
            n = len(OUTERDESK_APPS)
            self.results.append(("kv", "APP REGISTRATE", str(n), (96, 225, 120)))
            for app in OUTERDESK_APPS:
                script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), app.get("script", ""))
                exists = os.path.exists(script)
                col = (96, 225, 120) if exists else (238, 62, 58)
                self.results.append(("kv", "  %s" % app["key"], "OK" if exists else "MANCANTE", col))
        except Exception as e:
            self.results.append(("kv", "OUTER-DESK", "errore: %s" % str(e), (238, 62, 58)))

    def _check_audio(self):
        self.results.append(("sec", "speaker", "AUDIO"))
        try:
            import pygame
            pygame.mixer.init()
            self.results.append(("kv", "MIXER", "attivo", (96, 225, 120)))
        except Exception:
            self.results.append(("kv", "MIXER", "non disponibile", (238, 62, 58)))

    def _check_display(self):
        self.results.append(("sec", "monitor", "DISPLAY"))
        try:
            with open("/sys/class/graphics/fb0/virtual_size") as f:
                size = f.read().strip()
            self.results.append(("kv", "RISOLUZIONE", size, (96, 225, 120)))
        except Exception:
            self.results.append(("kv", "DISPLAY", "N/D", (238, 62, 58)))

    def _human(self, n):
        for u in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or u == "TB":
                return "%d%s" % (n, u) if u == "B" else "%.1f%s" % (n, u)
            n /= 1024.0
        return "%dB" % n


def get_results_for_display(results, lang="it"):
    """Converte i risultati di Autopsia in righe per la schermata info."""
    lines = [("sec", "gear", "AUTOPSIA")]
    for r in results:
        if r[0] == "sec":
            lines.append(("sec", r[1], r[2].upper()))
        elif r[0] == "kv":
            lines.append(("kv", r[1], r[2], r[3] if len(r) > 3 else (148, 150, 152)))
    return lines
