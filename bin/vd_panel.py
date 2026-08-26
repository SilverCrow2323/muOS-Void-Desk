# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // vd_panel — pannello LIVE (START+SELECT durante XFCE).
#  Sfondo: lo schermo XFCE congelato e oscurato. Sopra: la finestra LIVE.
#  Gira FUORI da X: funziona anche a desktop bloccato.
# ============================================================================
import json
import os
import signal
import subprocess
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP_DIR, "data")
sys.path.insert(0, os.path.join(APP_DIR, "desk"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame          # noqa: E402
import evinput         # noqa: E402
import fbdisplay       # noqa: E402
import icons           # noqa: E402
import imgmount        # noqa: E402
import sysinfo         # noqa: E402

W, H = 640, 480
# --- palette LIVE: piu' fredda del menu principale (che e' ambra su nero)
WIN_BG = (20, 23, 36)
WIN_HEAD = (30, 35, 56)
WIN_EDGE = (72, 84, 120)
SEL = (44, 52, 82)
FG = (234, 236, 244)
DIM = (156, 162, 182)
FAINT = (104, 110, 132)
OK_G = (86, 224, 132)
WARN_Y = (250, 196, 70)
NO_R = (240, 86, 86)
LIVE_R = (255, 70, 70)
ACCENTS = {"ambra": (255, 176, 46), "cremisi": (231, 54, 84),
           "ciano": (74, 206, 224), "verde": (112, 224, 122),
           "acciaio": (208, 214, 210)}
# tinta identitaria dell'ambiente attivo (in linea col selettore del menu)
ENV_SECONDARY = {
    "ambra":   {"icewm": (74, 206, 224),  "lxde": (112, 224, 122)},
    "cremisi": {"icewm": (255, 176, 46),  "lxde": (74, 206, 224)},
    "ciano":   {"icewm": (231, 54, 84),   "lxde": (255, 176, 46)},
    "verde":   {"icewm": (74, 206, 224),  "lxde": (255, 176, 46)},
    "acciaio": {"icewm": (110, 195, 250), "lxde": (255, 176, 46)},
}
ENV_NAMES = {"xfce": "XFCE", "icewm": "IceWM", "lxde": "LXDE",
            "cli": "CLI Terminal"}
ENV_GLYPHS = {
 "xfce": [0x07E0, 0x1FF8, 0x3FFC, 0x7FFE, 0x7FFE, 0xFFFF, 0xF3CF, 0xF3CF,
          0xFFFF, 0xFFFF, 0x7FFE, 0x799E, 0x3FFC, 0x1FF8, 0x07E0, 0x0000],
 "icewm": [0x03F0, 0x07E0, 0x0FC0, 0x1F80, 0x3FF8, 0x7FF0, 0x07E0, 0x0FC0,
           0x1F80, 0x3F00, 0x7E00, 0x7C00, 0x3800, 0x1800, 0x1000, 0x0000],
 "lxde": [0x0000, 0xC000, 0xF000, 0x7C00, 0x3F00, 0x1FC0, 0x0FF0, 0x07FC,
          0x07FF, 0x0FF0, 0x1F80, 0x3E00, 0x7800, 0xE000, 0x8000, 0x0000],
}
FONT_PATH = os.path.join(APP_DIR, "assets", "DejaVuSans.ttf")

WIN = pygame.Rect(28, 26, W - 56, H - 52)

TR = {
 "it": {"back": "Torna a XFCE", "back_s": "riprende la sessione",
        "diag": "Diagnosi sistema", "diag_s": "periferiche, rete, audio, XFCE",
        "fix": "Risoluzione problemi", "fix_s": "riparazioni rapide",
        "vol": "Volume", "vol_s": "SX/DX regola",
        "bri": "Luminosita'", "bri_s": "SX/DX regola",
        "kbd": "Tastiera virtuale", "kbd_s": "mostra/nascondi la tastiera",
        "task": "Task manager", "task_s": "processi, A termina",
        "restart": "Riavvia XFCE", "restart_s": "chiude e riapre la sessione",
        "close": "Chiudi XFCE", "close_s": "torna a muOS",
        "sel": "scegli", "adj": "regola", "ok": "conferma", "back_b": "torna",
        "kill": "termina", "run": "esegui",
        "t_diag": "DIAGNOSI SISTEMA", "t_fix": "RISOLUZIONE PROBLEMI",
        "t_task": "TASK MANAGER", "killed": "terminato: %s",
        "checking": "controllo in corso...", "working": "eseguo...",
        "all_ok": "tutto in ordine", "probs": "%d problemi rilevati",
        "conn_lbl": "connesso", "d_wifi": "WiFi", "d_ip": "Indirizzo IP",
        "d_noconn": "non connesso", "d_missing": "assente"},
 "en": {"back": "Back to XFCE", "back_s": "resume the session where it was",
        "diag": "System check", "diag_s": "devices, network, audio, XFCE",
        "fix": "Troubleshooting", "fix_s": "one-tap repairs",
        "vol": "Volume", "vol_s": "LEFT/RIGHT to adjust",
        "bri": "Brightness", "bri_s": "LEFT/RIGHT to adjust",
        "kbd": "On-screen keyboard", "kbd_s": "show or hide the keyboard",
        "task": "Task manager", "task_s": "running processes, A to kill",
        "restart": "Restart XFCE", "restart_s": "close and reopen the session",
        "close": "Close XFCE", "close_s": "back to muOS",
        "sel": "select", "adj": "adjust", "ok": "confirm", "back_b": "back",
        "kill": "kill", "run": "run",
        "t_diag": "SYSTEM CHECK", "t_fix": "TROUBLESHOOTING",
        "t_task": "TASK MANAGER", "killed": "killed: %s",
        "checking": "checking...", "working": "working...",
        "all_ok": "everything looks fine", "probs": "%d issues found",
        "conn_lbl": "connected", "d_wifi": "Wi-Fi", "d_ip": "IP address",
        "d_noconn": "not connected", "d_missing": "missing"},
}


def font(sz):
    try:
        return pygame.font.Font(FONT_PATH, sz)
    except Exception:
        return pygame.font.Font(None, sz)


def read(p, d=""):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return d


def run_out(cmd, t=4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=t).stdout
    except Exception:
        return ""


def have(b):
    return any(os.access(os.path.join(d, b), os.X_OK)
               for d in os.environ.get("PATH", "").split(":"))


def mounted(p):
    try:
        return (" %s " % os.path.abspath(p)) in open("/proc/mounts").read()
    except OSError:
        return False


def pids_of(*names):
    out = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        c = read("/proc/%s/comm" % pid)
        st = read("/proc/%s/stat" % pid)
        if ") Z" in st:
            continue        # zombie: esiste ma non gira
        if any(c == n or c.startswith(n) for n in names):
            out.append(int(pid))
    return out


# ------------------------------------------------------------ periferiche --
batt = sysinfo.battery
get_bri = sysinfo.brightness
set_bri = sysinfo.set_brightness
get_vol = sysinfo.volume
set_vol = sysinfo.set_volume
bt_on = sysinfo.bt_status


def wifi_info():
    conn, ssid, lvl, _if, _ip = sysinfo.wifi_status()
    return (ssid or ("connesso" if conn else None)), (lvl if conn else None)


def ip_addr():
    return sysinfo.wifi_status()[4]


def mem_free_mb():
    try:
        for ln in open("/proc/meminfo"):
            if ln.startswith("MemAvailable:"):
                return int(ln.split()[1]) // 1024
    except OSError:
        pass
    return None


def swap_mb():
    try:
        lines = open("/proc/swaps").read().splitlines()[1:]
        return sum(int(l.split()[2]) // 1024 for l in lines if l.split())
    except (OSError, ValueError, IndexError):
        return 0


CORE_TASKS = [
    ("Xorg", ("Xorg", "X"), None),
    ("matchbox-window-manager", ("matchbox-window-manager",),
     ["matchbox-window-manager", "-use_titlebar", "no"]),
    ("matchbox-keyboard", ("matchbox-keybo", "matchbox-keyboard"), None),
    ("qjoypad", ("qjoypad",), ["qjoypad", "--notray", "Default"]),
]


def task_list(n=12):
    rows = []
    me = os.getpid()
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == me:
            continue
        c = read("/proc/%s/comm" % pid)
        if not c:
            continue
        rss = 0
        try:
            for ln in open("/proc/%s/status" % pid):
                if ln.startswith("VmRSS:"):
                    rss = int(ln.split()[1])
                    break
        except OSError:
            continue
        rows.append((rss, int(pid), c))
    rows.sort(reverse=True)
    return rows[:n]


class Panel(object):
    def __init__(self, mnt=""):
        self.mnt = mnt
        cfg = {}
        try:
            cfg = json.load(open(os.path.join(DATA, "desk_config.json")))
        except Exception:
            pass
        self.lang = cfg.get("lang", "it")
        theme = cfg.get("theme", "ambra")
        self.accent = ACCENTS.get(theme, ACCENTS["ambra"])
        self.env = "xfce"
        try:
            e = open(os.path.join(mnt, "tmp/.vd_env")).read().strip()
            if e in ENV_NAMES:
                self.env = e
        except OSError:
            pass
        self.envname = ENV_NAMES[self.env]
        if self.env != "xfce":
            self.accent = ENV_SECONDARY.get(theme, ENV_SECONDARY["ambra"]
                                            ).get(self.env, self.accent)
        pygame.display.init()
        pygame.font.init()
        self.surface = pygame.display.set_mode((W, H))
        # 1) catturo lo schermo XFCE PRIMA di prendere il framebuffer
        self.bg = fbdisplay.grab()
        if self.bg is not None:
            if self.bg.get_size() != (W, H):
                self.bg = pygame.transform.smoothscale(self.bg, (W, H))
            dark = pygame.Surface((W, H))
            dark.fill((0, 0, 0))
            dark.set_alpha(165)
            self.bg.blit(dark, (0, 0))
        fbdisplay.attach(self.surface)
        self.f_big = font(24)
        self.f_med = font(18)
        self.f_small = font(14)
        self.f_tiny = font(12)
        self.sel = 0
        self.stack = ["menu"]
        self.sub_sel = 0
        self.note = ""
        self.diag = []
        self.result = "resume"
        self.running = True
        self.vol = get_vol()
        self.bri = get_bri()
        self.vol_osd_until = 0.0
        self._dpad = 0.0
        self._st = ({}, 0.0)

    def t(self, k):
        return TR.get(self.lang, TR["it"]).get(k, k)

    # ------------------------------------------------------------- chrome
    def status(self):
        now = time.time()
        if now - self._st[1] > 6:
            b, chg = sysinfo.battery()
            conn, ssid, lvl, iface, ip = sysinfo.wifi_status()
            self._st = ({"batt": b, "chg": chg,
                         "ssid": ssid or (self.t("conn_lbl") if conn else None),
                         "wifi": lvl if conn else None, "conn": conn,
                         "ip": ip, "bt": sysinfo.bt_status(),
                         "vol": sysinfo.volume()}, now)
        return self._st[0]

    def text(self, s, pos, f, col, maxw=None):
        if maxw:
            while s and f.size(s)[0] > maxw:
                s = s[:-1]
        self.surface.blit(f.render(s, True, col), pos)

    def window(self, title):
        """Sfondo XFCE oscurato + cornice della finestra LIVE."""
        if self.bg is not None:
            self.surface.blit(self.bg, (0, 0))
        else:
            self.surface.fill((8, 9, 14))
        sh = pygame.Surface((WIN.w, WIN.h))
        sh.fill((0, 0, 0))
        sh.set_alpha(120)
        self.surface.blit(sh, (WIN.x + 5, WIN.y + 6))
        pygame.draw.rect(self.surface, WIN_BG, WIN, border_radius=9)
        pygame.draw.rect(self.surface, WIN_EDGE, WIN, 2, border_radius=9)
        head = pygame.Rect(WIN.x + 2, WIN.y + 2, WIN.w - 4, 40)
        pygame.draw.rect(self.surface, WIN_HEAD, head,
                         border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(self.surface, self.accent, (WIN.x + 2, WIN.y + 42),
                         (WIN.right - 2, WIN.y + 42), 2)
        # badge LIVE + titolo
        pygame.draw.circle(self.surface, LIVE_R, (WIN.x + 20, WIN.y + 22), 5)
        self.text("LIVE", (WIN.x + 32, WIN.y + 13), self.f_small, LIVE_R)
        self.text("Void-", (WIN.x + 74, WIN.y + 10), self.f_big, FG)
        bw = self.f_big.size("Void-")[0]
        self.text("DESK", (WIN.x + 74 + bw, WIN.y + 10), self.f_big,
                  self.accent)
        self.text(title, (WIN.x + 218, WIN.y + 18), self.f_tiny, DIM,
                  maxw=WIN.w - 218 - 130)
        # indicatori console
        st = self.status()
        x = WIN.right - 12
        txt = time.strftime("%H:%M")
        tw = self.f_tiny.size(txt)[0]
        x -= tw
        self.text(txt, (x, WIN.y + 16), self.f_tiny, DIM)
        if st["batt"] is not None:
            b = "%d%%" % st["batt"]
            bw = self.f_tiny.size(b)[0]
            x -= bw + 6
            self.text(b, (x, WIN.y + 16), self.f_tiny,
                      NO_R if st["batt"] <= 20 else DIM)
            x -= 24
            icons.battery_icon(self.surface, x, WIN.y + 10, 18, st["batt"],
                               st["chg"], OK_G, NO_R, DIM)
        x -= 24
        icons.volume_icon(self.surface, x, WIN.y + 12, 18, st["vol"],
                          self.accent, FAINT)
        if st["bt"] is not None:
            x -= 22
            icons.bt_icon(self.surface, x, WIN.y + 12, 18, st["bt"],
                          self.accent, FAINT)
        x -= 22
        icons.wifi_icon(self.surface, x, WIN.y + 12, 18, st["wifi"],
                        self.accent, FAINT)
        if st["ip"]:
            iw = self.f_tiny.size(st["ip"])[0]
            x -= iw + 6
            self.text(st["ip"], (x, WIN.y + 16), self.f_tiny, DIM)
        elif st["ssid"]:
            sw = self.f_tiny.size(st["ssid"])[0]
            x -= sw + 6
            self.text(st["ssid"], (x, WIN.y + 16), self.f_tiny, DIM)

    def wfooter(self, hints):
        y = WIN.bottom - 26
        pygame.draw.line(self.surface, WIN_EDGE, (WIN.x + 2, y - 4),
                         (WIN.right - 2, y - 4), 1)
        x = WIN.x + 14
        for k, lab in hints:
            self.text(k, (x, y), self.f_tiny, self.accent)
            x += self.f_tiny.size(k)[0] + 4
            self.text(lab, (x, y), self.f_tiny, DIM)
            x += self.f_tiny.size(lab)[0] + 14

    def bar(self, x, y, w, pct):
        pygame.draw.rect(self.surface, (12, 14, 22), (x, y, w, 10),
                         border_radius=3)
        pygame.draw.rect(self.surface, self.accent,
                         (x, y, max(2, w * pct // 100), 10), border_radius=3)

    # -------------------------------------------------------------- voci
    def items(self):
        if self.env == "cli":
            it_ = (self.lang == "it")
            return [
                ("resume", "start", "Riprendi" if it_ else "Resume",
                 "torna al terminale" if it_ else "back to the "
                 "terminal"),
                ("launch_clitools", "terminal",
                 "Lancia CLI Tools" if it_ else "Launch CLI Tools",
                 "chiudi e avvia un altro tool" if it_ else "close "
                 "and launch another tool"),
                ("core_tasks", "task", "Core Tasks",
                 "processi necessari, tutti attivi?" if it_ else
                 "required processes, all running?"),
                ("cli_troubleshoot", "monitor",
                 "CLI Troubleshooting",
                 "diagnosi per questo ambiente" if it_ else
                 "diagnostics for this environment"),
                ("kbd_settings", "keyboard",
                 "Keyboard settings" if it_ else "Keyboard settings",
                 "dimensione, layout" if it_ else "size, layout"),
                ("restart", "start",
                 "Restart CLI Tool" if it_ else "Restart CLI Tool",
                 "riavvia il tool corrente" if it_ else "restart the "
                 "current tool"),
                ("close", "info",
                 "Termina CLI Terminal" if it_ else "Close CLI "
                 "Terminal", "torna a CLI Arsenal" if it_ else
                 "back to CLI Arsenal"),
            ]
        it = [("back", "start", self.t("back").replace("XFCE",
                                                        self.envname),
               self.t("back_s")),
              ("diag", "monitor", self.t("diag"),
               self.t("diag_s").replace("XFCE", self.envname)),
              ("fix", "gear", self.t("fix"), self.t("fix_s"))]
        if self.vol is not None:
            it.append(("vol", "speaker", self.t("vol"), self.t("vol_s")))
        if self.bri is not None:
            it.append(("bri", "image", self.t("bri"), self.t("bri_s")))
        it += [("kbd", "keyboard", self.t("kbd"), self.t("kbd_s")),
               ("task", "task", self.t("task"), self.t("task_s")),
               ("restart", "start",
                self.t("restart").replace("XFCE", self.envname),
                self.t("restart_s")),
               ("close", "info",
                self.t("close").replace("XFCE", self.envname),
                self.t("close_s"))]
        return it

    # ---------------------------------------------------------- diagnosi
    def chroot_pids(self, *names):
        """Processi del chroot (condividono /proc con l'host)."""
        return pids_of(*names)

    def run_diag(self):
        it = (self.lang == "it")

        def L(i, e):
            return i if it else e

        d = []
        st = self.status()
        d.append(("Xorg", bool(pids_of("Xorg", "X")),
                  L("server grafico", "graphics server"), "xorg"))
        if self.env != "cli":
            d.append((L("Window manager", "Window manager"),
                      bool(self.chroot_pids(
                          {"xfce": "xfwm4", "icewm": "icewm",
                           "lxde": "openbox"}[self.env])),
                      {"xfce": "xfwm4", "icewm": "icewm",
                       "lxde": "openbox"}[self.env], "window"))
            d.append((L("Pannello XFCE", "XFCE panel"),
                      bool(self.chroot_pids(
                          {"xfce": "xfce4-panel", "icewm": "icewm",
                           "lxde": "lxpanel"}[self.env])),
                      {"xfce": "xfce4-panel", "icewm": "icewm-tray",
                       "lxde": "lxpanel"}[self.env], "panel"))
        d.append(("QJoyPad", bool(self.chroot_pids("qjoypad")),
                  L("controller -> mouse", "controller -> mouse"),
                  "gamepad"))
        d.append((L("Tastiera (matchbox)", "Keyboard (matchbox)"),
                  bool(self.chroot_pids("matchbox-keybo",
                                        "matchbox-keyboard")),
                  L("tastiera virtuale", "on-screen keyboard"), "keyboard"))
        for lbl_i, lbl_e, sub, ic in (
                ("Audio (/dev/snd)", "Audio (/dev/snd)", "/dev/snd",
                 "speaker"),
                ("Input (/dev/input)", "Input (/dev/input)", "/dev/input",
                 "gamepad"),
                ("Memoria cond. (/dev/shm)", "Shared mem (/dev/shm)",
                 "/dev/shm", "task"),
                ("D-Bus di sistema", "System D-Bus", "/run/dbus", "dbus")):
            ok = (mounted(os.path.join(self.mnt, sub.lstrip("/")))
                  if self.mnt else False)
            d.append((L(lbl_i, lbl_e), ok,
                      L("montato nel chroot", "mounted in the chroot") if ok
                      else L("NON montato: usa Risoluzione problemi",
                             "NOT mounted: use Troubleshooting"), ic))
        cards = read("/proc/asound/cards", "")
        d.append((L("Schede audio", "Sound cards"), bool(cards.strip()),
                  cards.splitlines()[0][:38] if cards.strip()
                  else L("nessuna", "none"), "mixer"))
        vol = st["vol"]
        d.append((L("Volume", "Volume"), vol is None or vol > 0,
                  "%d%%" % vol if vol is not None else L("n/d", "n/a"),
                  "speaker"))
        d.append((self.t("d_wifi"), bool(st.get("conn")),
                  st["ssid"] or self.t("d_noconn"), "wifi"))
        d.append((self.t("d_ip"), bool(st["ip"]),
                  st["ip"] or self.t("d_missing"), "net"))
        inet = subprocess.call(["curl", "-sI", "--max-time", "6",
                                "https://ports.ubuntu.com"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL) == 0
        d.append(("Internet", inet, "ports.ubuntu.com", "globe"))
        d.append(("Bluetooth", bool(st["bt"]),
                  L("n/d", "n/a") if st["bt"] is None else
                  (L("adattatore attivo", "adapter on")
                   if st["bt"] else L("spento", "off")), "bt"))
        mf = mem_free_mb()
        sw = swap_mb()
        d.append((L("Memoria libera", "Free memory"), (mf or 0) > 120,
                  "%s MB" % (mf if mf is not None else "?"), "task"))
        d.append(("Swap", sw > 0, "%d MB" % sw if sw else
                  L("assente: consigliato (RAM 1GB)",
                    "missing: recommended (1GB RAM)"), "disk"))
        img = os.path.join(DATA, "xfce.img")
        dev = imgmount.loop_of(img)
        d.append((L("Immagine XFCE", "XFCE image"), True,
                  (L("montata su %s", "mounted on %s") % dev) if dev
                  else L("non montata", "not mounted"), "disk"))
        try:
            s_ = os.statvfs(DATA)
            free_gb = s_.f_bavail * s_.f_frsize / 1e9
            d.append((L("Spazio su SD1", "SD1 free space"), free_gb > 0.3,
                      L("%.1f GB liberi", "%.1f GB free") % free_gb, "disk"))
        except OSError:
            pass
        self.diag = d
        return d

    # ------------------------------------------------- riparazioni rapide
    def session_cmd(self, cmd, wait=False):
        dbus = read(os.path.join(self.mnt, "tmp/.vd_dbus"))
        full = ["chroot", self.mnt, "/usr/bin/env", "DISPLAY=:0",
                "HOME=/root", "PATH=/usr/sbin:/usr/bin:/sbin:/bin"]
        if dbus:
            full.append("DBUS_SESSION_BUS_ADDRESS=" + dbus)
        try:
            if wait:
                return subprocess.call(full + cmd, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=25)
            subprocess.Popen(full + cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return 0

    def cli_trouble_actions(self):
        it = (self.lang == "it")
        return [
            ("ctrlc", "terminal", "Ctrl+C",
             "interrompi il comando in corso" if it else
             "interrupt the running command"),
            ("refresh", "monitor", "Refresh schermo" if it else
             "Refresh screen", "se rimangono artefatti visivi" if it
             else "if visual artifacts remain"),
        ]

    def fixes(self):
        it = (self.lang == "it")
        if it:
            return [
                ("panel", "panel", "Riavvia pannello XFCE",
                 "se la barra e' sparita"),
                ("wm", "window", "Riavvia window manager",
                 "se le finestre non hanno cornice"),
                ("qjp", "gamepad", "Riavvia controller",
                 "se stick e tasti non rispondono"),
                ("audio", "speaker", "Ripara audio",
                 "riattiva mixer e PulseAudio all'80%"),
                ("kbd", "keyboard", "Riavvia tastiera virtuale",
                 "se matchbox non compare"),
                ("mounts", "disk", "Rimonta periferiche",
                 "audio, input, dbus nel chroot"),
                ("swap", "disk", "Attiva swap 512MB",
                 "piu' respiro con 1GB di RAM"),
                ("mem", "task", "Libera memoria",
                 "svuota le cache del kernel"),
                ("loop", "disk", "Libera immagine XFCE",
                 "se l'installazione dice 'mount fallito'"),
                ("fitwin", "window", "Adatta finestra allo schermo",
                 "riporta dentro le finestre giganti"),
                ("killwin", "window", "Chiudi finestra attiva",
                 "se un programma e' bloccato"),
            ]
        return [
            ("panel", "panel", "Restart XFCE panel",
             "if the taskbar disappeared"),
            ("wm", "window", "Restart window manager",
             "if windows lost their borders"),
            ("qjp", "gamepad", "Restart controller",
             "if sticks and buttons stop working"),
            ("audio", "speaker", "Repair audio",
             "unmute mixer and restart PulseAudio"),
            ("kbd", "keyboard", "Restart on-screen keyboard",
             "if matchbox will not show up"),
            ("mounts", "disk", "Remount devices",
             "audio, input and dbus inside the chroot"),
            ("swap", "disk", "Enable 512MB swap",
             "more headroom with only 1GB of RAM"),
            ("mem", "task", "Free memory",
             "drop kernel caches"),
            ("loop", "disk", "Release XFCE image",
             "if installing says 'mount failed'"),
            ("fitwin", "window", "Fit window to screen",
             "pull oversized windows back in"),
            ("killwin", "window", "Kill active window",
             "if an app is frozen"),
        ]

    def apply_fix(self, key):
        it = (self.lang == "it")
        if key == "panel":
            cmd = {"xfce": ["xfce4-panel", "-r"],
                   "icewm": ["sh", "-c", "kill -HUP $(pidof icewm)"],
                   "lxde": ["lxpanelctl", "restart"]}[self.env]
            self.session_cmd(cmd)
            return ("pannello riavviato" if it else "panel restarted")
        if key == "wm":
            cmd = {"xfce": ["xfwm4", "--replace", "--daemon"],
                   "icewm": ["sh", "-c", "kill -HUP $(pidof icewm)"],
                   "lxde": ["openbox", "--restart"]}[self.env]
            self.session_cmd(cmd)
            return ("window manager riavviato" if it
                    else "window manager restarted")
        if key == "qjp":
            for p in pids_of("qjoypad"):
                try:
                    os.kill(p, signal.SIGKILL)
                except OSError:
                    pass
            prof = read(os.path.join(DATA, ".qjoypad_profile"), "sinistro")
            src = os.path.join(DATA, "qjoypad_custom.lyt") \
                if prof == "custom" else os.path.join(
                    APP_DIR, "assets", "xfce", "qjoypad_%s.lyt" % prof)
            try:
                dst = os.path.join(self.mnt, "root/.qjoypad3/Default.lyt")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(src, "rb") as a, open(dst, "wb") as b:
                    b.write(a.read())
            except OSError:
                pass
            self.session_cmd(["qjoypad", "--notray", "Default"])
            return (("controller riavviato (profilo %s)" if it
                     else "controller restarted (%s profile)") % prof)
        if key == "audio":
            for ctl in ("Master", "PCM", "Speaker", "Headphone"):
                subprocess.call(["amixer", "-q", "sset", ctl, "80%", "unmute"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
            self.session_cmd(["pulseaudio", "-k"], wait=True)
            self.session_cmd(["pulseaudio", "--start", "--exit-idle-time=-1"])
            self.vol = get_vol()
            return ("audio riattivato all'80%" if it
                    else "audio unmuted at 80%")
        if key == "kbd":
            for p_ in pids_of("matchbox-keybo", "matchbox-keyboard"):
                try:
                    os.kill(p_, signal.SIGKILL)
                except OSError:
                    pass
            # parte quando X riprende: senza demone, appare direttamente
            self.session_cmd(["matchbox-keyboard"])
            return ("tastiera riavviata" if self.lang == "it"
                    else "keyboard restarted")
        if key == "mounts":
            n = 0
            for sub in ("/dev/snd", "/dev/shm", "/dev/input", "/dev/pts",
                        "/run/dbus", "/run/udev"):
                if not os.path.exists(sub):
                    continue
                dst = os.path.join(self.mnt, sub.lstrip("/"))
                if mounted(dst):
                    continue
                os.makedirs(dst, exist_ok=True)
                if subprocess.call(["mount", "-o", "bind", sub, dst],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL) == 0:
                    n += 1
            return (("rimontate %d periferiche" if it
                     else "remounted %d devices") % n)
        if key == "swap":
            if swap_mb() > 0:
                return (("swap gia' attivo (%d MB)" if it
                         else "swap already on (%d MB)") % swap_mb())
            sf = os.path.join(self.mnt, "swapfile") if self.mnt else \
                os.path.join(DATA, "swapfile")
            try:
                if not os.path.exists(sf):
                    subprocess.call(["dd", "if=/dev/zero", "of=" + sf,
                                     "bs=1M", "count=512"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                    os.chmod(sf, 0o600)
                    subprocess.call(["mkswap", sf], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                rc = subprocess.call(["swapon", sf],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                if rc == 0:
                    return ("swap 512MB attivo" if it else "512MB swap on")
                return ("swapon fallito (kernel senza swap?)" if it
                        else "swapon failed (no swap support?)")
            except Exception as e:
                return ("errore swap: %s" if it else "swap error: %s") % e
        if key == "mem":
            before = mem_free_mb() or 0
            subprocess.call(["sync"])
            try:
                with open("/proc/sys/vm/drop_caches", "w") as f:
                    f.write("3\n")
            except OSError:
                return ("impossibile svuotare le cache" if it
                        else "cannot drop caches")
            after = mem_free_mb() or 0
            return (("liberati %d MB (ora %d MB)" if it
                     else "freed %d MB (now %d MB)")
                    % (max(0, after - before), after))
        if key == "loop":
            img = os.path.join(DATA, "xfce.img")
            mnt = os.path.join(DATA, "xfce_mnt")
            n = len(imgmount.submounts(mnt))
            imgmount.umount_tree(mnt, img)
            imgmount.cleanup_stale(img)
            free = imgmount.loop_of(img) is None
            return ("liberati %d mount, loop %s" %
                    (n, "libero" if free else "ancora occupato")
                    if self.lang == "it" else
                    "released %d mounts, loop %s"
                    % (n, "free" if free else "still busy"))
        if key == "fitwin":
            self.session_cmd(["sh", "-c",
                              "xdotool getactivewindow windowmove 0 0 "
                              "windowsize 636 442"])
            return ("finestra adattata a 640x480" if it
                    else "window fitted to 640x480")
        if key == "killwin":
            self.session_cmd(["sh", "-c",
                              "xdotool windowkill $(xdotool getactivewindow)"])
            return ("finestra chiusa" if it else "window closed")
        return ""

    # ------------------------------------------------------------- input
    def on_button(self, b):
        top = self.stack[-1]
        if top == "menu":
            items = self.items()
            key = items[self.sel][0]
            if b == "UP":
                self.sel = (self.sel - 1) % len(items)
            elif b == "DOWN":
                self.sel = (self.sel + 1) % len(items)
            elif b in ("LEFT", "RIGHT"):
                d = 5 if b == "RIGHT" else -5
                if key == "vol" and self.vol is not None:
                    self.vol = max(0, min(100, self.vol + d))
                    set_vol(self.vol)
                    self.vol_osd_until = time.time() + 1.4
                elif key == "bri" and self.bri is not None:
                    self.bri = max(5, min(100, self.bri + d))
                    set_bri(self.bri)
            elif b == "B":
                self.running = False
            elif b == "A":
                if key == "back":
                    self.running = False
                elif key == "kbd":
                    # MAI toccare un client X mentre Xorg e' SIGSTOPpato:
                    # il toggle lo fa vd_hotkey DOPO il SIGCONT.
                    self.result = "kbd"
                    self.running = False
                elif key == "ctrlc":
                    # stesso motivo di "kbd": mai toccare X qui dentro,
                    # lo fa vd_hotkey dopo aver ripreso Xorg
                    self.result = "ctrlc"
                    self.running = False
                elif key == "launch_clitools":
                    self.stack.append("launch_clitools")
                elif key == "core_tasks":
                    self.sub_sel = 0
                    self.stack.append("core_tasks")
                elif key == "cli_troubleshoot":
                    self.sub_sel = 0
                    self.stack.append("cli_troubleshoot")
                elif key == "kbd_settings":
                    self.sub_sel = 0
                    self.stack.append("kbd_settings")
                elif key == "resume":
                    self.running = False
                elif key == "diag":
                    self.note = self.t("checking")
                    self.stack.append("diag")
                    self.sub_sel = 0
                    self.render()
                    self.run_diag()
                    self.note = ""
                elif key == "fix":
                    self.sub_sel = 0
                    self.note = ""
                    self.stack.append("fix")
                elif key == "task":
                    self.sub_sel = 0
                    self.stack.append("task")
                elif key in ("restart", "close"):
                    self.result = key
                    self.running = False
        elif top == "diag":
            if b == "UP":
                self.sub_sel = max(0, self.sub_sel - 1)
            elif b == "DOWN":
                self.sub_sel = min(max(0, len(self.diag) - 9),
                                   self.sub_sel + 1)
            elif b == "A":
                self.note = self.t("checking")
                self.render()
                self.run_diag()
                self.note = ""
            elif b == "B":
                self.stack.pop()
        elif top == "fix":
            fx = self.fixes()
            if b == "UP":
                self.sub_sel = (self.sub_sel - 1) % len(fx)
            elif b == "DOWN":
                self.sub_sel = (self.sub_sel + 1) % len(fx)
            elif b == "A":
                self.note = self.t("working")
                self.render()
                self.note = self.apply_fix(fx[self.sub_sel][0])
            elif b == "B":
                self.stack.pop()
        elif top == "task":
            rows = task_list()
            if b == "UP":
                self.sub_sel = max(0, self.sub_sel - 1)
            elif b == "DOWN":
                self.sub_sel = min(len(rows) - 1, self.sub_sel + 1)
            elif b == "B":
                self.stack.pop()
            elif b == "A" and rows:
                _r, pid, comm = rows[min(self.sub_sel, len(rows) - 1)]
                try:
                    os.kill(pid, signal.SIGKILL)
                    self.note = self.t("killed") % comm
                except OSError as e:
                    self.note = str(e)
        elif top == "launch_clitools":
            if b == "B":
                self.stack.pop()
            elif b == "A":
                self.result = "launch_clitools"
                self.running = False
        elif top == "core_tasks":
            n = len(CORE_TASKS)
            if b == "UP":
                self.sub_sel = (self.sub_sel - 1) % n
            elif b == "DOWN":
                self.sub_sel = (self.sub_sel + 1) % n
            elif b == "B":
                self.stack.pop()
            elif b == "A":
                name, comms, launch = CORE_TASKS[self.sub_sel]
                running = bool(pids_of(*comms))
                if running:
                    self.note = (("gia' attivo" if self.lang == "it"
                                 else "already running"))
                elif name == "matchbox-keyboard":
                    self.result = "kbd"
                    self.running = False
                elif launch:
                    self.result = "start:" + name
                    self.running = False
                else:
                    self.note = ("non riavviabile da qui" if
                                 self.lang == "it" else "can't be "
                                 "restarted from here")
        elif top == "cli_troubleshoot":
            actions = self.cli_trouble_actions()
            n = len(actions)
            if b == "UP":
                self.sub_sel = (self.sub_sel - 1) % n
            elif b == "DOWN":
                self.sub_sel = (self.sub_sel + 1) % n
            elif b == "B":
                self.stack.pop()
            elif b == "A":
                key = actions[self.sub_sel][0]
                if key == "ctrlc":
                    self.result = "ctrlc"
                    self.running = False
                elif key == "refresh":
                    self.result = "refresh"
                    self.running = False
        elif top == "kbd_settings":
            if b == "B":
                self.stack.pop()
            elif b == "A":
                try:
                    cfgp = os.path.join(os.path.dirname(self.mnt),
                                        "desk_config.json")
                    cfgd = json.load(open(cfgp))
                except Exception:
                    cfgd = {}
                sizes = [170, 230, 300]
                cur = cfgd.get("kbd_h", 230)
                nxt = sizes[(sizes.index(cur) + 1) % len(sizes)
                           if cur in sizes else 1]
                cfgd["kbd_h"] = nxt
                try:
                    json.dump(cfgd, open(cfgp, "w"))
                except Exception:
                    pass
                self.note = (("dimensione: %dpx (attiva alla "
                             "prossima apertura)" % nxt) if
                             self.lang == "it" else
                             ("size: %dpx (applies next time it "
                             "opens)" % nxt))

    # ------------------------------------------------------------ render
    def render(self):
        top = self.stack[-1]
        if top == "menu":
            self.window(self.envname)
            gm = ENV_GLYPHS.get(self.env)
            if gm:
                for ry in range(16):
                    bits = gm[ry]
                    for rx in range(16):
                        if bits & (1 << (15 - rx)):
                            pygame.draw.rect(
                                self.surface, self.accent,
                                (WIN.right - 52 + rx * 2,
                                 WIN.y + 12 + ry * 2, 1, 1))
            items = self.items()
            per = 8
            first = max(0, min(self.sel - per // 2, len(items) - per))
            first = max(0, first)
            y = WIN.y + 52
            for i in range(first, min(first + per, len(items))):
                key, ic, label, sub = items[i]
                if i == self.sel:
                    pygame.draw.rect(self.surface, SEL,
                                     (WIN.x + 8, y, WIN.w - 16, 38),
                                     border_radius=5)
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.x + 8, y, 3, 38))
                icons.draw(self.surface, ic, WIN.x + 20, y + 8, 22,
                           self.accent if i == self.sel else DIM)
                self.text(label, (WIN.x + 52, y + 3), self.f_med,
                          FG if i == self.sel else DIM)
                self.text(sub, (WIN.x + 52, y + 21), self.f_tiny, FAINT,
                          maxw=WIN.w - 250)
                if key == "vol" and self.vol is not None:
                    self.bar(WIN.right - 165, y + 14, 110, self.vol)
                    self.text("%d%%" % self.vol, (WIN.right - 48, y + 10),
                              self.f_small, self.accent)
                elif key == "bri" and self.bri is not None:
                    self.bar(WIN.right - 165, y + 14, 110, self.bri)
                    self.text("%d%%" % self.bri, (WIN.right - 48, y + 10),
                              self.f_small, self.accent)
                y += 40
            if first > 0:
                self.text("^", (WIN.right - 26, WIN.y + 48), self.f_small,
                          self.accent)
            if first + per < len(items):
                self.text("v", (WIN.right - 26, WIN.y + WIN.h - 60),
                          self.f_small, self.accent)
            self.wfooter([("SU/GIU", self.t("sel")), ("SX/DX", self.t("adj")),
                          ("A", self.t("ok")), ("B", self.t("back_b"))])
        elif top == "diag":
            self.window(self.t("t_diag"))
            if self.note:
                self.text(self.note, (WIN.x + 20, WIN.y + 60), self.f_med,
                          DIM)
            else:
                bad = sum(1 for d in self.diag if not d[1])
                msg = (self.t("all_ok") if not bad
                       else self.t("probs") % bad)
                self.text(msg, (WIN.x + 20, WIN.y + 50), self.f_small,
                          OK_G if not bad else WARN_Y)
                y = WIN.y + 70
                for lbl, ok, det, ic in self.diag[self.sub_sel:
                                                  self.sub_sel + 9]:
                    icons.draw(self.surface, ic, WIN.x + 18, y + 2, 18,
                               DIM)
                    self.text(lbl, (WIN.x + 44, y), self.f_small,
                              FG, maxw=190)
                    self.text(det, (WIN.x + 240, y + 1), self.f_tiny,
                              OK_G if ok else NO_R, maxw=WIN.w - 300)
                    cx = WIN.right - 30
                    if ok:
                        pygame.draw.lines(self.surface, OK_G, False,
                                          [(cx, y + 9), (cx + 4, y + 14),
                                           (cx + 12, y + 2)], 3)
                    else:
                        pygame.draw.line(self.surface, NO_R, (cx, y + 2),
                                         (cx + 11, y + 13), 3)
                        pygame.draw.line(self.surface, NO_R, (cx + 11, y + 2),
                                         (cx, y + 13), 3)
                    y += 22
            self.wfooter([("A", "aggiorna"), ("SU/GIU", "scorri"),
                          ("B", self.t("back_b"))])
        elif top == "fix":
            self.window(self.t("t_fix"))
            fx = self.fixes()
            y = WIN.y + 50
            for i, (key, ic, label, sub) in enumerate(fx):
                if i == self.sub_sel:
                    pygame.draw.rect(self.surface, SEL,
                                     (WIN.x + 8, y, WIN.w - 16, 34),
                                     border_radius=5)
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.x + 8, y, 3, 34))
                icons.draw(self.surface, ic, WIN.x + 20, y + 7, 20,
                           self.accent if i == self.sub_sel else DIM)
                self.text(label, (WIN.x + 50, y + 2), self.f_small,
                          FG if i == self.sub_sel else DIM)
                self.text(sub, (WIN.x + 50, y + 18), self.f_tiny, FAINT,
                          maxw=WIN.w - 80)
                y += 36
            if self.note:
                pygame.draw.rect(self.surface, (16, 30, 24),
                                 (WIN.x + 8, WIN.bottom - 52, WIN.w - 16, 22),
                                 border_radius=4)
                self.text("→ " + self.note, (WIN.x + 16, WIN.bottom - 50),
                          self.f_tiny, OK_G, maxw=WIN.w - 40)
            self.wfooter([("A", self.t("run")), ("B", self.t("back_b"))])
        elif top == "task":
            self.window(self.t("t_task"))
            rows = task_list()
            y = WIN.y + 52
            for i, (rss, pid, comm) in enumerate(rows):
                if i == self.sub_sel:
                    pygame.draw.rect(self.surface, SEL,
                                     (WIN.x + 8, y, WIN.w - 16, 24),
                                     border_radius=4)
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.x + 8, y, 3, 24))
                self.text(comm[:24], (WIN.x + 20, y + 3), self.f_small,
                          FG if i == self.sub_sel else DIM)
                self.text("pid %-6d" % pid, (WIN.x + 250, y + 4),
                          self.f_tiny, FAINT)
                self.text("%4d MB" % (rss // 1024), (WIN.x + 350, y + 4),
                          self.f_tiny, DIM)
                if rows[0][0]:
                    w = 90 * rss // max(1, rows[0][0])
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.right - 110, y + 8, max(1, w), 7),
                                     border_radius=2)
                y += 26
            if self.note:
                self.text(self.note, (WIN.x + 16, WIN.bottom - 50),
                          self.f_tiny, OK_G)
            self.wfooter([("A", self.t("kill")), ("B", self.t("back_b"))])
        elif top == "launch_clitools":
            it = (self.lang == "it")
            self.window("Launch CLI Tools" if not it else
                       "Lancia CLI Tools")
            active = None
            try:
                active = open(os.path.join(
                    self.mnt, "tmp/vd_xterm_cmd")).read().strip()
            except OSError:
                pass
            y = WIN.y + 70
            if active:
                self.text(("in esecuzione ora:" if it else
                          "currently running:"), (WIN.x + 24, y),
                          self.f_small, FAINT)
                y += 24
                self.text(active, (WIN.x + 24, y), self.f_med,
                          self.accent, maxw=WIN.w - 48)
                y += 40
            self.text(("Chiudere e passare a CLI Arsenal per "
                      "sceglierne un altro?" if it else
                      "Close it and go to CLI Arsenal to pick "
                      "another?"), (WIN.x + 24, y), self.f_small, FG,
                      maxw=WIN.w - 48)
            self.wfooter([("A", "conferma" if it else "confirm"),
                         ("B", self.t("back_b"))])
        elif top == "core_tasks":
            it = (self.lang == "it")
            self.window("Core Tasks")
            y = WIN.y + 52
            for i, (name, comms, launch) in enumerate(CORE_TASKS):
                running = bool(pids_of(*comms))
                if i == self.sub_sel:
                    pygame.draw.rect(self.surface, SEL,
                                     (WIN.x + 8, y, WIN.w - 16, 36),
                                     border_radius=5)
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.x + 8, y, 3, 36))
                led = OK_G if running else NO_R
                pygame.draw.circle(self.surface, led,
                                   (WIN.x + 26, y + 18), 6)
                self.text(name, (WIN.x + 46, y + 5), self.f_med,
                          FG if i == self.sub_sel else DIM)
                if running:
                    stxt = "attivo" if it else "running"
                    scol = OK_G
                else:
                    can_start = launch or name == "matchbox-keyboard"
                    if can_start:
                        stxt = ("spento -- premi A per avviarlo" if it
                                else "off -- press A to start it")
                    else:
                        stxt = "spento" if it else "off"
                    scol = FAINT
                self.text(stxt, (WIN.x + 46, y + 22), self.f_tiny, scol)
                y += 42
            if self.note:
                self.text(self.note, (WIN.x + 16, WIN.bottom - 50),
                          self.f_tiny, OK_G)
            self.wfooter([("A", "avvia" if it else "start"),
                         ("B", self.t("back_b"))])
        elif top == "cli_troubleshoot":
            self.window("CLI Troubleshooting")
            actions = self.cli_trouble_actions()
            y = WIN.y + 52
            for i, (key, ic, label, sub) in enumerate(actions):
                if i == self.sub_sel:
                    pygame.draw.rect(self.surface, SEL,
                                     (WIN.x + 8, y, WIN.w - 16, 38),
                                     border_radius=5)
                    pygame.draw.rect(self.surface, self.accent,
                                     (WIN.x + 8, y, 3, 38))
                icons.draw(self.surface, ic, WIN.x + 20, y + 8, 22,
                          self.accent if i == self.sub_sel else DIM)
                self.text(label, (WIN.x + 52, y + 3), self.f_med,
                          FG if i == self.sub_sel else DIM)
                self.text(sub, (WIN.x + 52, y + 21), self.f_tiny, FAINT,
                          maxw=WIN.w - 90)
                y += 40
            if self.note:
                self.text(self.note, (WIN.x + 16, WIN.bottom - 50),
                          self.f_tiny, OK_G)
            self.wfooter([("A", self.t("ok")), ("B", self.t("back_b"))])
        elif top == "kbd_settings":
            it = (self.lang == "it")
            self.window("Keyboard settings")
            try:
                cfgd = json.load(open(os.path.join(
                    os.path.dirname(self.mnt), "desk_config.json")))
            except Exception:
                cfgd = {}
            cur = cfgd.get("kbd_h", 230)
            y = WIN.y + 60
            self.text("Dimensione" if it else "Size", (WIN.x + 24, y),
                      self.f_med, FG)
            y += 30
            for sz, lab in ((170, "piccola" if it else "small"),
                            (230, "media" if it else "medium"),
                            (300, "grande" if it else "large")):
                sel = (sz == cur)
                col = self.accent if sel else WIN_EDGE
                pygame.draw.rect(self.surface, col,
                                 (WIN.x + 24, y, 140, 34), 2 if sel
                                 else 1, border_radius=6)
                self.text("%s (%dpx)" % (lab, sz), (WIN.x + 34, y + 8),
                          self.f_small, FG if sel else DIM)
                y += 42
            self.text("A: cicla piccola/media/grande" if it else
                      "A: cycle small/medium/large",
                      (WIN.x + 24, y + 6), self.f_tiny, FAINT)
            if self.note:
                self.text(self.note, (WIN.x + 16, WIN.bottom - 50),
                          self.f_tiny, OK_G)
            self.wfooter([("A", "cambia" if it else "change"),
                         ("B", self.t("back_b"))])
        if time.time() < self.vol_osd_until and self.vol is not None:
            self.draw_vol_osd()
        pygame.display.flip()

    def draw_vol_osd(self):
        """Finestrella verticale del volume, a sinistra: compare al
        variare del volume (o quando scende a zero, cioe' muto) e
        sparisce da sola dopo un attimo."""
        bx, by, bw, bh = 14, WIN.centery - 90, 34, 180
        pygame.draw.rect(self.surface, (10, 11, 15), (bx, by, bw, bh),
                         border_radius=10)
        pygame.draw.rect(self.surface, self.accent, (bx, by, bw, bh), 2,
                         border_radius=10)
        pad = 6
        fh = bh - pad * 2
        lvl = max(0, min(100, self.vol))
        filled = int(fh * lvl / 100.0)
        muted = lvl == 0
        col = (200, 60, 56) if muted else self.accent
        pygame.draw.rect(self.surface, (26, 28, 34),
                         (bx + pad, by + pad, bw - pad * 2, fh),
                         border_radius=4)
        if filled > 0:
            pygame.draw.rect(self.surface, col,
                             (bx + pad, by + pad + (fh - filled),
                              bw - pad * 2, filled), border_radius=4)
        icons.volume_icon(self.surface, bx + bw // 2 - 9, by - 30, 18,
                          0 if muted else lvl, col, (90, 92, 98))
        pct = "MUTE" if muted else "%d%%" % lvl
        pw = self.f_tiny.size(pct)[0]
        self.text(pct, (bx + bw // 2 - pw // 2, by + bh + 8),
                  self.f_tiny, col)

    # --------------------------------------------------------- animazione
    def animate_open(self):
        base = pygame.Surface((W, H))
        if self.bg is not None:
            base.blit(self.bg, (0, 0))
        else:
            base.fill((8, 9, 14))
        self.render()
        win_img = self.surface.subsurface(WIN).copy()
        for i in range(1, 7):
            k = i / 6.0
            self.surface.blit(base, (0, 0))
            w = max(2, int(WIN.w * (0.72 + 0.28 * k)))
            h = max(2, int(WIN.h * (0.72 + 0.28 * k)))
            img = pygame.transform.smoothscale(win_img, (w, h))
            img.set_alpha(int(255 * k))
            self.surface.blit(img, (WIN.centerx - w // 2,
                                    WIN.centery - h // 2))
            pygame.display.flip()
            time.sleep(0.012)

    def run_panel(self):
        self.animate_open()
        while self.running:
            for b in evinput.poll():
                if b != "MENU":
                    self.on_button(b)
            hx, hy = evinput.hat()
            now = time.time()
            if (hx or hy) and now - self._dpad > 0.16:
                self._dpad = now
                if hy > 0:
                    self.on_button("UP")
                elif hy < 0:
                    self.on_button("DOWN")
                if hx < 0:
                    self.on_button("LEFT")
                elif hx > 0:
                    self.on_button("RIGHT")
            self.render()
            time.sleep(0.03)
        fbdisplay.detach()
        pygame.display.quit()
        return self.result
