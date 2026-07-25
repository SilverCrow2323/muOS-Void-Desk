# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK v8.5 — pannello di controllo della suite Void per muOS
#  Estetica SPDW FACTORY: cyberpunk manga grezzo, megastruttura alla BLAME!
# ============================================================================
import math
import os
import calendar as calmod
import datetime as dtmod
import ftplib
import random
import re
import subprocess
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame          # noqa: E402
import evinput         # noqa: E402
import fbdisplay       # noqa: E402
import icons           # noqa: E402
import imgmount        # noqa: E402
import intro           # noqa: E402
import jsmap           # noqa: E402
import shell           # noqa: E402
import sysinfo         # noqa: E402

W, H = 640, 480
BG = (7, 8, 11)            # nero megastruttura
PANEL = (18, 20, 26)       # lastra scura
LINE = (34, 38, 47)        # nervature della struttura
INK = (2, 2, 4)            # china: piu' nero del fondo
STEEL = (78, 86, 98)       # acciaio strutturale: mai un accento, sempre struttura
STEEL_HI = (128, 138, 150) # riflesso freddo sull'acciaio, per il bevel
GRN = (60, 255, 110)        # fosforo verde: terminale retro, mondo a parte
DGRN = (20, 90, 45)
CLI_ACCENTS = {
    "verde":  ((60, 255, 110), (20, 90, 45)),
    "ambra":  ((255, 190, 60), (95, 70, 20)),
    "ciano":  ((80, 220, 255), (25, 82, 96)),
    "bianco": ((228, 228, 222), (86, 86, 82)),
}
FG = (233, 233, 226)       # bianco osso
DIM = (148, 150, 152)
FAINT = (100, 103, 110)
OK_G = (96, 225, 120)      # spunta: verde acceso
NO_R = (238, 62, 58)       # croce: rosso sangue
UNK = (110, 112, 120)
ACCENTS = {
    "ambra":   (255, 176, 46),
    "cremisi": (231, 54, 84),
    "ciano":   (74, 206, 224),
    "verde":   (112, 224, 122),
    "acciaio": (208, 214, 210),
}


def theme_secondary(accent):
    """Seconda tinta del tema, derivata dall'accento (mai scelta a
    mano): piu' scura e mezza desaturata verso il grigio. Serve per i
    dettagli decorativi di sfondo (cavi, ingranaggi) -- mai per
    selezione o azione, quello resta sempre il vero accento."""
    r, g, b = accent
    gray = (r + g + b) / 3.0
    r2 = r * 0.5 + gray * 0.5
    g2 = g * 0.5 + gray * 0.5
    b2 = b * 0.5 + gray * 0.5
    return (int(r2 * 0.5), int(g2 * 0.5), int(b2 * 0.5))


# colore identitario di ogni ambiente nel selettore START SESSION:
# xfce = accento del tema; gli altri due cambiano combinazione col tema.
ENV_SECONDARY = {
    "ambra":   {"icewm": (74, 206, 224),  "lxde": (112, 224, 122)},
    "cremisi": {"icewm": (255, 176, 46),  "lxde": (74, 206, 224)},
    "ciano":   {"icewm": (231, 54, 84),   "lxde": (255, 176, 46)},
    "verde":   {"icewm": (74, 206, 224),  "lxde": (255, 176, 46)},
    "acciaio": {"icewm": (110, 195, 250), "lxde": (255, 176, 46)},
}
# maschere 16x16 dei marchi ambiente (bit alto = colonna sinistra)
ENV_GLYPHS = {
 "xfce": [0x07E0, 0x1FF8, 0x3FFC, 0x7FFE, 0x7FFE, 0xFFFF, 0xF3CF, 0xF3CF,
          0xFFFF, 0xFFFF, 0x7FFE, 0x799E, 0x3FFC, 0x1FF8, 0x07E0, 0x0000],
 "icewm": [0x03F0, 0x07E0, 0x0FC0, 0x1F80, 0x3FF8, 0x7FF0, 0x07E0, 0x0FC0,
           0x1F80, 0x3F00, 0x7E00, 0x7C00, 0x3800, 0x1800, 0x1000, 0x0000],
 "lxde": [0x0000, 0xC000, 0xF000, 0x7C00, 0x3F00, 0x1FC0, 0x0FF0, 0x07FC,
          0x07FF, 0x0FF0, 0x1F80, 0x3E00, 0x7800, 0xE000, 0x8000, 0x0000],
}
MUOS_APP_ROOTS = os.environ.get(
    "VD_MUOS_ROOTS",
    "/mnt/mmc/MUOS/application:/mnt/sdcard/MUOS/application").split(":")
MUOS_TASK_ROOTS = os.environ.get(
    "VD_MUOS_TASK_ROOTS",
    "/mnt/mmc/MUOS/Task:/mnt/sdcard/MUOS/Task").split(":")

# --------------------------------------------------------------------------
# v6.0: architettura a sezioni. Ogni hub e' dati puri: un solo gestore.
# kind: push=apre stato, act=azione, cycle=valore ciclico, info=schermata info
# --------------------------------------------------------------------------
HUBS = {
 "forge": ("forge", "h_forge", [
    ("installer", "pkg",     "f_inst",  "f_inst_s",  "act"),
    ("autostart", "start",   "f_auto",  "f_auto_s",  "act"),
    ("update",    "download","f_upd",   "f_upd_s",   "act"),
    ("vdupdate",  "forge",   "f_vdupd", "f_vdupd_s", "push"),
    ("clitools",  "terminal","f_cli",   "f_cli_s",   "push"),
 ]),
 "workshop": ("workshop", "h_work", [
    ("stats",   "task",    "w_stats", "w_stats_s", "act"),
    ("diag",    "gear",    "w_diag",  "w_diag_s",  "act"),
    ("monitor", "task",    "t_mon",   "t_mon_s",   "push"),
    ("storage", "storage", "w_sto",   "w_sto_s",   "act"),
    ("boost",   "gauge",   "w_boost", "w_boost_s", "push"),
    ("clean",   "trash",   "w_clean", "w_clean_s", "act"),
    ("logs",    "doc",     "w_logs",  "w_logs_s",  "push"),
    ("backup",  "archive", "w_bak",   "w_bak_s",   "push"),
 ]),
 "uplink": ("uplink", "h_up", [
    ("wifi",    "wifi",    "u_wifi",  "u_wifi_s",  "push"),
    ("hotspot", "uplink",  "u_hot",   "u_hot_s",   "push"),
    ("bt",      "bt",      "u_bt",    "u_bt_s",    "push"),
    ("dlang",   "lang",    "u_dlang", "u_dlang_s", "cycle"),
    ("kbdmb",   "keyboard","u_kmb",   "u_kmb_s",   "cycle"),
    ("kbdx",    "keyboard","u_kx",    "u_kx_s",    "cycle"),
    ("ctrl",    "gamepad", "u_ctrl",  "u_ctrl_s",  "cycle"),
    ("map",     "gamepad", "u_map",   "u_map_s",   "push"),
 ]),
 "toolbox": ("toolbox", "h_tool", [
    ("calc",    "calc",    "t_calc",  "t_calc_s",  "push"),
    ("clockmain", "clock", "t_clock", "t_clock_s", "push"),
    ("cal",     "clock",   "t_cal",   "t_cal_s",   "push"),
    ("notes",   "text",    "t_note",  "t_note_s",  "push"),
    ("fileman", "folder",  "t_fm",    "t_fm_s",    "act"),
    ("ftp",     "download","t_ftp",   "t_ftp_s",   "act"),
    ("sync",    "remote",  "t_sync",  "t_sync_s",  "act"),
    ("tsgui",   "uplink",  "t_tsg",   "t_tsg_s",   "act"),
    ("shell",   "terminal","t_sh",    "t_sh_s",    "act"),
    ("pyrepl",  "terminal","t_py",    "t_py_s",    "push"),
    ("editor",  "text",    "t_ed",    "t_ed_s",    "act"),
    ("rss",     "globe",   "t_rss",   "t_rss_s",   "push"),
    ("weather", "w_partly","t_wx",    "t_wx_s",    "push"),
 ]),
 "infohub": ("book", "h_info", [
    ("about",   "info",    "i_about", "i_about_s", "act"),
    ("manual",  "book",    "i_man",   "i_man_s",   "push"),
    ("guide",   "gamepad", "i_guide", "i_guide_s", "act"),
    ("manifesto", "terminal", "i_manifesto", "i_manifesto_s", "act"),
 ]),
}
CYCLES = {
    "dlang": ("desk_lang", ["system", "en_US", "it_IT", "de_DE",
                            "fr_FR", "es_ES", "pt_BR"]),
    "kbdmb": ("kbd_mb", ["default", "it", "de", "fr", "es", "gb"]),
    "kbdx":  ("kbd_x", ["us", "it", "de", "fr", "es", "gb"]),
    "ctrl":  ("controller", ["sinistro", "classico", "custom"]),
    "fscale": ("font_scale", ["piccolo", "normale", "grande",
                              "molto grande"]),
}
FONT_SCALES = {"piccolo": 0.85, "normale": 1.0, "grande": 1.15,
              "molto grande": 1.3}
GOVS = ["default", "performance", "ondemand", "powersave"]
OSK_PAGES = [
    ["qwertyuiop", "asdfghjkl-", "zxcvbnm_.,", "1234567890"],
    ["QWERTYUIOP", "ASDFGHJKL-", "ZXCVBNM_.,", "1234567890"],
    ["1234567890", "!@#$%^&*()", "+-*/=<>[]{", "}:;'\"~`|\\ "],
]

CLOCK_LAYOUTS = ["classic", "minimal", "segmented", "analog", "skeleton",
                 "pilot"]
HOME_STYLES = ["blame", "hud", "terminal", "orbit", "nexus"]
VERSION = "9.63"
GITHUB_REPO = "SilverCrow2323/muOS-Void-Desk"
# gruppi tematici del Rt:Toolbox: (titolo IT, titolo EN, icona sezione,
# quante voci ci stanno, stile del widget) -- l'ordine deve combaciare
# con l'ordine delle voci in HUBS["toolbox"]
TOOLBOX_GROUPS = [
    ("PRODUTTIVITA'", "PRODUCTIVITY", "calc", 4, "grid2"),
    ("RETE E FILE", "NETWORK & FILES", "folder", 4, "row4"),
    ("SVILUPPO", "DEVELOPMENT", "terminal", 3, "row3"),
    ("INFORMAZIONE", "INFORMATION", "globe", 2, "row2"),
]
MAPP_VIEWS = ["list", "grid", "compact", "detailed"]
ALARM_SOUNDS = ["classic", "digital", "gentle"]

CALC_KEYS = [
    ["7", "8", "9", "/", "sin", "cos"],
    ["4", "5", "6", "*", "tan", "log"],
    ["1", "2", "3", "-", "ln", "sqrt"],
    ["0", ".", "(", ")", "+", "^"],
    ["pi", "e", "ans", "C", "<", "="],
]
MANUAL = [
    ("intro", "info"), ("sessions", "start"), ("forge", "forge"),
    ("mapps", "window"), ("workshop", "workshop"), ("uplink", "uplink"),
    ("toolbox", "toolbox"), ("live", "panel"), ("trouble", "gear"),
]
PROTECTED = ("portmaster", "retroarch", "ppsspp", "scummvm", "drastic",
             "pico8", "pico-8")
TZS = ["UTC", "Europe/Rome", "Europe/Paris", "Europe/Berlin",
       "Europe/Madrid", "Europe/London", "Europe/Lisbon", "Europe/Athens",
       "Europe/Moscow", "America/New_York", "America/Chicago",
       "America/Denver", "America/Los_Angeles", "America/Sao_Paulo",
       "America/Mexico_City", "America/Argentina/Buenos_Aires",
       "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Hong_Kong",
       "Asia/Singapore", "Asia/Kolkata", "Asia/Dubai", "Asia/Jerusalem",
       "Australia/Sydney", "Australia/Perth", "Pacific/Auckland",
       "Africa/Cairo", "Africa/Johannesburg"]
WM_IFACE = os.environ.get("VD_WM_IFACE", "wlan0")
WPA = os.environ.get("VD_WPA", "wpa_cli -i " + WM_IFACE).split()
SYS_WPA_CONF = os.environ.get("VD_WPA_CONF", "/etc/wpa_supplicant.conf")
BTCTL = os.environ.get("VD_BTCTL", "bluetoothctl").split()
BT_UART = os.environ.get("VD_BT_UART", "/dev/ttyS1")
BT_BAUD = os.environ.get("VD_BT_BAUD", "115200")
BT_HCIATTACH = os.environ.get("VD_RTKHCIATTACH", "rtk_hciattach")
BT_MODULE = os.environ.get("VD_BT_MODULE", "rtl_btlpm")
BTD_BIN = os.environ.get("VD_BTD_BIN",
                         "/usr/libexec/bluetooth/bluetoothd")

def comp_color(c):
    """Complementare del tema, alzato se troppo scuro su fondo nero."""
    r, g, b = 255 - c[0], 255 - c[1], 255 - c[2]
    if r + g + b < 250:
        r, g, b = min(255, r + 90), min(255, g + 90), min(255, b + 90)
    return (r, g, b)


TS_BIN = os.environ.get("VD_TS_BIN", "/opt/muos/bin/tailscale")
TS_SOCK = os.environ.get("VD_TS_SOCK", "/run/tailscale/tailscaled.sock")
TS_BLUE = (74, 111, 227)
TS_GRAY = (196, 200, 208)

WMO_CODES = {
    0: ("w_sunny", "sereno", "clear"),
    1: ("w_sunny", "poco nuvoloso", "mostly clear"),
    2: ("w_partly", "parziale nuvolosita'", "partly cloudy"),
    3: ("w_cloudy", "coperto", "overcast"),
    45: ("w_fog", "nebbia", "fog"),
    48: ("w_fog", "nebbia", "fog"),
    51: ("w_rain", "pioviggine", "drizzle"),
    53: ("w_rain", "pioviggine", "drizzle"),
    55: ("w_rain", "pioviggine", "drizzle"),
    56: ("w_rain", "pioviggine gelata", "freezing drizzle"),
    57: ("w_rain", "pioviggine gelata", "freezing drizzle"),
    61: ("w_rain", "pioggia debole", "light rain"),
    63: ("w_rain", "pioggia", "rain"),
    65: ("w_rain", "pioggia forte", "heavy rain"),
    66: ("w_rain", "pioggia gelata", "freezing rain"),
    67: ("w_rain", "pioggia gelata", "freezing rain"),
    71: ("w_snow", "neve debole", "light snow"),
    73: ("w_snow", "neve", "snow"),
    75: ("w_snow", "neve forte", "heavy snow"),
    77: ("w_snow", "granelli di neve", "snow grains"),
    80: ("w_rain", "rovesci", "showers"),
    81: ("w_rain", "rovesci", "showers"),
    82: ("w_rain", "rovesci violenti", "violent showers"),
    85: ("w_snow", "rovesci di neve", "snow showers"),
    86: ("w_snow", "rovesci di neve", "snow showers"),
    95: ("w_storm", "temporale", "thunderstorm"),
    96: ("w_storm", "temporale con grandine", "thunderstorm w/hail"),
    99: ("w_storm", "temporale con grandine", "thunderstorm w/hail"),
}
WX_SEGMENTS = ["09", "15", "21"]

RSS_CATS = {
    "news":    ("globe",    (196, 200, 208)),
    "tech":    ("gear",     (74, 206, 224)),
    "linux":   ("terminal", (255, 176, 46)),
    "gaming":  ("gamepad",  (112, 224, 122)),
    "retro":   ("monitor",  (231, 84, 191)),
    "anime":   ("film",     (255, 105, 135)),
    "general": ("text",     (148, 150, 152)),
}
# libreria curata: (nome, url, lingua, categoria) - "generale" e' riservata
# ai feed che l'utente aggiunge da DATA/rss_custom.json
RSS_FEEDS = [
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml",
     "en", "news"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml",
     "en", "news"),
    ("TechCrunch", "https://techcrunch.com/feed/", "en", "tech"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index",
     "en", "tech"),
    ("The Verge", "https://www.theverge.com/rss/index.xml",
     "en", "tech"),
    ("Phoronix", "https://www.phoronix.com/rss.php", "en", "linux"),
    ("It's FOSS", "https://itsfoss.com/feed/", "en", "linux"),
    ("OMG Ubuntu", "https://www.omgubuntu.co.uk/feed", "en", "linux"),
    ("IGN", "https://feeds.ign.com/ign/games-all", "en", "gaming"),
    ("PC Gamer", "https://www.pcgamer.com/rss/", "en", "gaming"),
    ("Time Extension", "https://www.timeextension.com/feed",
     "en", "retro"),
    ("RetroRGB", "https://www.retrorgb.com/feed", "en", "retro"),
    ("Anime News Network",
     "https://www.animenewsnetwork.com/all/rss.xml", "en", "anime"),
    ("Crunchyroll News", "https://www.crunchyroll.com/newsrss",
     "en", "anime"),
    ("ANSA", "https://www.ansa.it/sito/ansait_rss.xml", "it", "news"),
    ("Il Post", "https://www.ilpost.it/feed/", "it", "news"),
    ("HDblog", "https://www.hdblog.it/rss/hdblog.xml", "it", "tech"),
    ("Punto Informatico", "https://www.punto-informatico.it/feed/",
     "it", "tech"),
    ("Multiplayer.it", "https://www.multiplayer.it/feed/",
     "it", "gaming"),
    ("AnimeClick", "https://www.animeclick.it/rss", "it", "anime"),
]

TOOL_PKGS = {
    "fileman": ("Thunar (file manager)", "thunar thunar-volman"),
    "ftp": ("FileZilla (FTP)", "filezilla"),
    "editor": ("Mousepad (editor)", "mousepad"),
    "sync": ("Syncthing", "syncthing"),
}

ENV_CODENAME = {"xfce": "CORE", "icewm": "TURBO", "lxde": "LIGHT"}

ENVS = [
    ("xfce",  "DESKTOP XFCE",  "startxfce4"),
    ("icewm", "ICEWM // TURBO", "icewm"),
    ("lxde",  "LXDE // LIGHT",  "lxde-core lxterminal"),
]


def sel_tint(accent):
    """Fondo della riga selezionata: nero tinto con l'accento."""
    return tuple(min(255, BG[i] + accent[i] // 7) for i in range(3))

DATA = os.path.join(APP_DIR, "data")
LOG = os.path.join(DATA, "voiddesk.log")
FONT_PATH = os.path.join(APP_DIR, "assets", "DejaVuSans.ttf")

EXIT_XFCE_LAUNCH = 11
EXIT_XFCE_INSTALL = 12
EXIT_PKG_INSTALL = 13
EXIT_PKG_REMOVE = 14
EXIT_APT_UPDATE = 15
EXIT_MUOS_APP = 16
EXIT_XTERM = 17

# ---------------------------------------------------------------------------
# Catalogo componenti: categorie -> voci
#   (nome, pacchetti apt, descrizione, percorsi-prova nel chroot)
# ---------------------------------------------------------------------------
CATEGORIES = [
 ("BASE / DRIVER", [
  ("Server X (Xorg)", "xserver-xorg-core", "il server grafico",
   "usr/bin/Xorg", "xorg"),
  ("Driver video fbdev", "xserver-xorg-video-fbdev", "uscita su framebuffer",
   "usr/lib/xorg/modules/drivers/fbdev_drv.so", "driver"),
  ("Driver input evdev", "xserver-xorg-input-evdev", "tasti e stick",
   "usr/lib/xorg/modules/input/evdev_drv.so", "gamepad"),
  ("startx / xinit", "xinit", "avvio della sessione", "usr/bin/startx",
   "start"),
  ("Utility X11", "x11-xserver-utils x11-utils", "xset, xrefresh, xdpyinfo",
   "usr/bin/xset", "gear"),
  ("D-Bus", "dbus dbus-x11", "comunicazione tra applicazioni",
   "usr/bin/dbus-daemon", "dbus"),
  ("Font DejaVu", "fonts-dejavu-core", "font di sistema",
   "usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "font"),
  ("Certificati CA", "ca-certificates", "connessioni https",
   "usr/sbin/update-ca-certificates", "cert"),
 ]),
 ("DESKTOP XFCE", [
  ("Sessione XFCE", "xfce4-session", "gestore di sessione",
   "usr/bin/startxfce4", "start"),
  ("Window manager", "xfwm4", "cornici e finestre", "usr/bin/xfwm4",
   "window"),
  ("Pannello", "xfce4-panel", "barra applicazioni", "usr/bin/xfce4-panel",
   "panel"),
  ("Scrivania", "xfdesktop4", "sfondo e icone", "usr/bin/xfdesktop",
   "desktop"),
  ("Impostazioni XFCE", "xfce4-settings", "aspetto, tastiera, mouse",
   "usr/bin/xfce4-settings-manager", "gear"),
  ("File manager", "thunar", "Thunar", "usr/bin/thunar", "folder"),
  ("Terminale", "xfce4-terminal", "terminale grafico",
   "usr/bin/xfce4-terminal", "terminal"),
  ("Task manager", "xfce4-taskmanager", "processi e memoria",
   "usr/bin/xfce4-taskmanager", "task"),
  ("Screenshot", "xfce4-screenshooter", "catture schermo",
   "usr/bin/xfce4-screenshooter", "camera"),
  ("Blocco note", "mousepad", "editor di testo", "usr/bin/mousepad", "text"),
 ]),
 ("AMBIENTI DESKTOP", [
  ("IceWM", "icewm",
   "window manager turbo: ~10MB di RAM", "usr/bin/icewm-session",
   "desktop"),
  ("LXDE", "lxde-core lxterminal",
   "desktop completo leggero (openbox+pcmanfm)", "usr/bin/startlxde",
   "desktop"),
 ]),
 ("INPUT / TASTIERA", [
  ("QJoyPad", "qjoypad", "gamepad -> mouse e tasti", "usr/bin/qjoypad",
   "gamepad"),
  ("Tastiera matchbox", "matchbox-keyboard",
   "tastiera virtuale (MENU la apre)", "usr/bin/matchbox-keyboard",
   "keyboard"),
  ("xdotool", "xdotool", "automazione finestre", "usr/bin/xdotool", "mouse"),
  ("Zenity", "zenity", "finestre di dialogo", "usr/bin/zenity", "dialog"),
 ]),
 ("PERIFERICHE", [
  ("Audio ALSA", "alsa-utils", "amixer, alsamixer, aplay", "usr/bin/amixer",
   "speaker"),
  ("PulseAudio + mixer", "pulseaudio pavucontrol",
   "server audio e mixer grafico", "usr/bin/pulseaudio", "mixer"),
  ("Bluetooth", "bluez blueman", "bluetoothctl + gestore grafico",
   "usr/bin/bluetoothctl", "bt"),
  ("WiFi (wpa_gui)", "wpagui", "reti wifi dal desktop", "usr/bin/wpa_gui",
   "wifi"),
  ("Dischi e USB", "gvfs gvfs-backends udisks2 thunar-volman",
   "automount chiavette in Thunar",
   "usr/lib/udisks2/udisksd|usr/libexec/udisks2/udisksd", "disk"),
  ("Hotspot (hostapd+dnsmasq)", "hostapd dnsmasq",
   "motore per UPLINK > Hotspot", "usr/sbin/hostapd usr/sbin/dnsmasq",
   "uplink"),
  ("Utility rete", "iproute2 iputils-ping wireless-tools",
   "ip, ping, iwconfig", "usr/bin/ping", "net"),
  ("NetworkManager", "network-manager network-manager-gnome",
   "gestione reti (puo' litigare con muOS)", "usr/sbin/NetworkManager",
   "wifi"),
 ]),
 ("BROWSER / RETE", [
  ("NetSurf", "netsurf-gtk", "browser leggerissimo (~20MB)",
   "usr/bin/netsurf-gtk", "globe"),
  ("Falkon", "falkon", "browser Qt completo (~350MB)", "usr/bin/falkon",
   "globe"),
  ("Dillo", "dillo", "browser minimale, velocissimo", "usr/bin/dillo",
   "globe"),
  ("Transmission", "transmission-gtk", "client torrent",
   "usr/bin/transmission-gtk", "download"),
  ("FileZilla", "filezilla", "trasferimento FTP/SFTP", "usr/bin/filezilla",
   "net"),
  ("Remmina", "remmina", "desktop remoto RDP/VNC", "usr/bin/remmina",
   "remote"),
 ]),
 ("MULTIMEDIA", [
  ("mpv", "mpv", "player video", "usr/bin/mpv", "video"),
  ("Audacious", "audacious", "player musicale leggero", "usr/bin/audacious",
   "music"),
  ("Ristretto", "ristretto", "visualizzatore immagini", "usr/bin/ristretto",
   "image"),
  ("Codec ffmpeg", "ffmpeg", "conversione e codec", "usr/bin/ffmpeg",
   "film"),
 ]),
 ("GRAFICA / UFFICIO", [
  ("mtPaint", "mtpaint", "disegno e ritocco leggero", "usr/bin/mtpaint",
   "paint"),
  ("GIMP", "gimp", "fotoritocco completo (PESANTE)", "usr/bin/gimp", "paint"),
  ("AbiWord", "abiword", "videoscrittura", "usr/bin/abiword", "doc"),
  ("Gnumeric", "gnumeric", "fogli di calcolo", "usr/bin/gnumeric", "sheet"),
  ("Lettore PDF", "xpdf", "visualizzatore PDF", "usr/bin/xpdf", "pdf"),
  ("Galculator", "galculator", "calcolatrice", "usr/bin/galculator", "calc"),
 ]),
 ("RETE / SVILUPPO", [
  ("Syncthing", "syncthing", "sincronizza file (muOS ne ha uno suo)",
   "usr/bin/syncthing", "download"),
  ("Tailscale", "!curl -fsSL https://tailscale.com/install.sh | sh",
   "VPN personale (script ufficiale)", "usr/bin/tailscale", "net"),
  ("Barrier", "barrier", "mouse e tastiera dal PC via rete",
   "usr/bin/barrier", "mouse"),
  ("KDE Connect", "kdeconnect", "telefono <-> desktop (PESANTE)",
   "usr/bin/kdeconnect-app", "remote"),
  ("Server SSH", "openssh-server",
   "entra nel desktop dal PC (porta 22)", "usr/sbin/sshd", "net"),
  ("Client SSH", "openssh-client", "ssh, scp verso altri PC",
   "usr/bin/ssh", "net"),
  ("VNC (x11vnc)", "x11vnc", "vedi il desktop dal PC", "usr/bin/x11vnc",
   "remote"),
  ("ADB", "adb", "android debug bridge", "usr/bin/adb", "disk"),
  ("Python 3 completo", "python3-full python3-pip python3-venv",
   "interprete, pip, venv", "usr/bin/pip3", "python"),
  ("Compilatore C/C++", "build-essential", "gcc, make (PESANTE)",
   "usr/bin/gcc", "gear"),
  ("rsync", "rsync", "sincronizza cartelle", "usr/bin/rsync", "download"),
  ("tmux", "tmux", "sessioni terminale persistenti", "usr/bin/tmux",
   "terminal"),
  ("Samba client", "cifs-utils smbclient", "cartelle di rete Windows",
   "usr/bin/smbclient", "folder"),
  ("nmap", "nmap", "scansione rete e porte", "usr/bin/nmap", "net"),
  ("traceroute", "traceroute", "traccia il percorso di rete",
   "usr/bin/traceroute", "net"),
  ("dig / nslookup", "dnsutils", "diagnostica DNS", "usr/bin/dig",
   "globe"),
  ("iperf3", "iperf3", "misura la banda tra due host", "usr/bin/iperf3",
   "net"),
 ]),
 ("STRUMENTI / CLI", [
  ("Xarchiver", "xarchiver", "archivi zip/tar/7z", "usr/bin/xarchiver",
   "archive"),
  ("Supporto archivi", "zip unzip p7zip-full", "zip, 7z da terminale",
   "usr/bin/7z", "archive"),
  ("htop", "htop", "monitor processi da terminale", "usr/bin/htop",
   "monitor"),
  ("Midnight Commander", "mc", "file manager da terminale", "usr/bin/mc",
   "folder"),
  ("Git", "git", "controllo versione", "usr/bin/git", "git"),
  ("nano", "nano", "editor da terminale", "usr/bin/nano", "edit"),
  ("wget / curl", "wget curl", "download da terminale", "usr/bin/wget",
   "download"),
  ("Info sistema", "neofetch lshw", "neofetch, lshw", "usr/bin/neofetch",
   "info"),
  ("ncdu", "ncdu", "spazio disco interattivo", "usr/bin/ncdu", "storage"),
  ("tree", "tree", "elenco cartelle ad albero", "usr/bin/tree", "folder"),
  ("fzf", "fzf", "ricerca fuzzy da terminale", "usr/bin/fzf", "terminal"),
  ("jq", "jq", "elaborazione JSON", "usr/bin/jq", "text"),
  ("iotop", "iotop", "monitor I/O disco", "usr/sbin/iotop", "monitor"),
  ("duf", "duf", "spazio disco, colonne leggibili", "usr/bin/duf",
   "storage"),
  ("lsof", "lsof", "quali processi tengono aperto cosa", "usr/bin/lsof",
   "terminal"),
  ("psmisc", "psmisc", "killall, fuser, pstree", "usr/bin/killall",
   "task"),
  ("sqlite3", "sqlite3", "database leggero da riga di comando",
   "usr/bin/sqlite3", "storage"),
  ("bc", "bc", "calcolatrice da script/terminale", "usr/bin/bc", "calc"),
  ("ImageMagick", "imagemagick", "converti/ritaglia immagini da CLI",
   "usr/bin/convert", "paint"),
  ("yt-dlp", "yt-dlp", "scarica video/audio da riga di comando",
   "usr/bin/yt-dlp", "download"),
  ("xterm", "xterm", "terminale X vero -- serve ai CLI tools "
   "interattivi e al Terminal", "usr/bin/xterm", "terminal"),
  ("matchbox-window-manager", "matchbox-window-manager",
   "porta le finestre a schermo intero -- senza, xterm resta piccolo "
   "in un angolo", "usr/bin/matchbox-window-manager", "window"),
 ]),
 ("DIVERTIMENTO CLI", [
  ("cmatrix", "cmatrix", "la pioggia di Matrix nel terminale",
   "usr/bin/cmatrix", "terminal"),
  ("nyancat", "nyancat", "il gatto arcobaleno, in ASCII",
   "usr/games/nyancat|usr/bin/nyancat", "image"),
  ("sl", "sl", "un treno a vapore attraversa il terminale",
   "usr/games/sl|usr/bin/sl", "monitor"),
  ("cowsay", "cowsay", "una mucca (o altro) che dice quello che vuoi",
   "usr/games/cowsay|usr/bin/cowsay", "text"),
  ("lolcat", "lolcat", "colora l'output di qualsiasi comando",
   "usr/bin/lolcat|usr/games/lolcat", "paint"),
  ("fortune", "fortune-mod", "citazioni casuali a ogni avvio terminale",
   "usr/games/fortune|usr/bin/fortune", "book"),
  ("figlet", "figlet", "scritte enormi in ASCII art", "usr/bin/figlet",
   "text"),
  ("nsnake", "nsnake", "il serpente del Nokia, in terminale",
   "usr/games/nsnake|usr/bin/nsnake", "gamepad"),
  ("moon-buggy", "moon-buggy", "salta i crateri sulla luna",
   "usr/games/moon-buggy|usr/bin/moon-buggy", "gamepad"),
  ("bastet", "bastet", "Tetris, ma ti da sempre il pezzo peggiore",
   "usr/games/bastet|usr/bin/bastet", "gamepad"),
  ("pacman4console", "pacman4console", "Pac-Man in ASCII",
   "usr/games/pacman4console|usr/bin/pacman4console", "gamepad"),
  ("ninvaders", "ninvaders", "Space Invaders da terminale",
   "usr/games/ninvaders|usr/bin/ninvaders", "gamepad"),
 ]),
]

# ---------------------------------------------------------------------------
# Avvio al boot: SOLO vere applicazioni. Sessione, driver, input e servizi
# (startxfce4, Xorg, qjoypad, matchbox, dbus, pulseaudio, bluetooth...)
# partono gia' da soli: metterli qui li fa partire DOPPI e sfascia il
# desktop (era il bug "le app non si avviano piu'", terminale incluso).
# ---------------------------------------------------------------------------
FEATURE_DEPS = {
    "hotspot": ["Hotspot (hostapd+dnsmasq)"],
    "real_terminal": ["xterm", "matchbox-window-manager",
                      "Tastiera matchbox"],
}
# (nome, voce-catalogo-per-lo-stato (None = script, non apt), comando
# da lanciare in terminale, descrizione IT, descrizione EN)
CLI_TOOLS = [
    ("cmatrix", "cmatrix", "cmatrix",
     "la pioggia di Matrix nel terminale",
     "The Matrix digital rain in your terminal", "monitor", []),
    ("nyancat", "nyancat", "nyancat",
     "il gatto arcobaleno, in ASCII", "the rainbow cat, in ASCII",
     "image", []),
    ("sl", "sl", "sl", "un treno a vapore attraversa il terminale",
     "a steam train crosses your terminal", "monitor", []),
    ("cowsay", "cowsay", "cowsay 'SPDW Factory saluta!'",
     "una mucca che dice quello che vuoi",
     "a cow saying whatever you want", "text", []),
    ("fortune", "fortune", "fortune",
     "citazione casuale", "a random quote", "book", []),
    ("figlet", "figlet", "figlet SPDW",
     "scritte enormi in ASCII art", "huge ASCII art text banners",
     "text", []),
    ("ani-cli", None, "ani-cli",
     "anime in streaming da terminale (script GitHub, non apt)",
     "stream anime from the terminal (GitHub script, not apt)",
     "film", ["mpv", "curl", "fzf"]),
    ("nsnake", "nsnake", "nsnake", "il serpente del Nokia, in terminale",
     "the classic Nokia snake, in your terminal", "gamepad", []),
    ("moon-buggy", "moon-buggy", "moon-buggy",
     "salta i crateri sulla luna", "jump craters on the moon",
     "gamepad", []),
    ("bastet", "bastet", "bastet",
     "Tetris, ma ti da sempre il pezzo peggiore",
     "Tetris, but it always gives you the worst piece", "gamepad", []),
    ("pacman4console", "pacman4console", "pacman4console",
     "Pac-Man in ASCII", "Pac-Man in ASCII", "gamepad", []),
    ("ninvaders", "ninvaders", "ninvaders",
     "Space Invaders da terminale", "Space Invaders in your terminal",
     "gamepad", []),
    ("mc", "Midnight Commander", "mc",
     "file manager da terminale, due pannelli",
     "terminal file manager, dual pane", "folder", []),
    ("nano", "nano", "nano", "editor di testo da terminale",
     "terminal text editor", "edit", []),
]
ANI_CLI_URL = ("https://raw.githubusercontent.com/pystardust/"
              "ani-cli/master/ani-cli")
for _tname, _tcat, _tcmd, _tdit, _tden, _tic, _tdeps in CLI_TOOLS:
    if _tcat:
        FEATURE_DEPS["clitool_" + _tname] = [_tcat]

CAT_ICONS = {
    "BASE / DRIVER": "gear", "DESKTOP XFCE": "desktop",
    "AMBIENTI DESKTOP": "window", "INPUT / TASTIERA": "gamepad",
    "PERIFERICHE": "disk", "BROWSER / RETE": "globe",
    "MULTIMEDIA": "video", "GRAFICA / UFFICIO": "paint",
    "RETE / SVILUPPO": "net", "STRUMENTI / CLI": "terminal",
    "DIVERTIMENTO CLI": "film",
}
CAT_NAMES_EN = {
    "BASE / DRIVER": "BASE / DRIVERS", "DESKTOP XFCE": "XFCE DESKTOP",
    "AMBIENTI DESKTOP": "DESKTOP ENVIRONMENTS",
    "INPUT / TASTIERA": "INPUT / KEYBOARD", "PERIFERICHE": "PERIPHERALS",
    "BROWSER / RETE": "BROWSER / NETWORK", "MULTIMEDIA": "MULTIMEDIA",
    "GRAFICA / UFFICIO": "GRAPHICS / OFFICE",
    "RETE / SVILUPPO": "NETWORK / DEV", "STRUMENTI / CLI": "CLI TOOLS",
    "DIVERTIMENTO CLI": "CLI FUN",
}
# nome/descrizione italiani -> (nome, descrizione) inglesi. Il nome
# resta identico quando e' gia' un nome proprio (Git, GIMP, htop...).
PKG_TR_EN = {
 "Server X (Xorg)": ("Server X (Xorg)", "the graphics server"),
 "Driver video fbdev": ("fbdev video driver", "framebuffer output"),
 "Driver input evdev": ("evdev input driver", "keys and sticks"),
 "startx / xinit": ("startx / xinit", "session startup"),
 "Utility X11": ("X11 utilities", "xset, xrefresh, xdpyinfo"),
 "D-Bus": ("D-Bus", "inter-app communication"),
 "Font DejaVu": ("DejaVu font", "system font"),
 "Certificati CA": ("CA certificates", "https connections"),
 "Sessione XFCE": ("XFCE session", "session manager"),
 "Window manager": ("Window manager", "frames and windows"),
 "Pannello": ("Panel", "application bar"),
 "Scrivania": ("Desktop", "wallpaper and icons"),
 "Impostazioni XFCE": ("XFCE settings", "look, keyboard, mouse"),
 "File manager": ("File manager", "Thunar"),
 "Terminale": ("Terminal", "graphical terminal"),
 "Task manager": ("Task manager", "processes and memory"),
 "Screenshot": ("Screenshot", "screen capture"),
 "Blocco note": ("Text editor", "Mousepad"),
 "IceWM": ("IceWM", "turbo window manager: ~10MB RAM"),
 "LXDE": ("LXDE", "full light desktop (openbox+pcmanfm)"),
 "QJoyPad": ("QJoyPad", "gamepad -> mouse and keys"),
 "Tastiera matchbox": ("Matchbox keyboard",
                       "on-screen keyboard (MENU opens it)"),
 "xdotool": ("xdotool", "window automation"),
 "Zenity": ("Zenity", "dialog windows"),
 "Audio ALSA": ("ALSA audio", "amixer, alsamixer, aplay"),
 "PulseAudio + mixer": ("PulseAudio + mixer",
                        "audio server and graphical mixer"),
 "Bluetooth": ("Bluetooth", "bluetoothctl + graphical manager"),
 "WiFi (wpa_gui)": ("WiFi (wpa_gui)", "wifi networks from the desktop"),
 "Dischi e USB": ("Disks and USB", "automount USB sticks in Thunar"),
 "Hotspot (hostapd+dnsmasq)": ("Hotspot (hostapd+dnsmasq)",
                               "engine for UPLINK > Hotspot"),
 "Utility rete": ("Network utilities", "ip, ping, iwconfig"),
 "NetworkManager": ("NetworkManager",
                    "network management (may clash with muOS)"),
 "NetSurf": ("NetSurf", "ultra-light browser (~20MB)"),
 "Falkon": ("Falkon", "full Qt browser (~350MB)"),
 "Dillo": ("Dillo", "minimal, very fast browser"),
 "Transmission": ("Transmission", "torrent client"),
 "FileZilla": ("FileZilla", "FTP/SFTP transfer"),
 "Remmina": ("Remmina", "RDP/VNC remote desktop"),
 "mpv": ("mpv", "video player"),
 "Audacious": ("Audacious", "light music player"),
 "Ristretto": ("Ristretto", "image viewer"),
 "Codec ffmpeg": ("ffmpeg codecs", "conversion and codecs"),
 "mtPaint": ("mtPaint", "light drawing and touch-up"),
 "GIMP": ("GIMP", "full photo editing (HEAVY)"),
 "AbiWord": ("AbiWord", "word processor"),
 "Gnumeric": ("Gnumeric", "spreadsheets"),
 "Lettore PDF": ("PDF reader", "PDF viewer"),
 "Galculator": ("Galculator", "calculator"),
 "Syncthing": ("Syncthing", "file sync (muOS has its own)"),
 "Tailscale": ("Tailscale", "personal VPN (official script)"),
 "Barrier": ("Barrier", "mouse and keyboard from your PC, over LAN"),
 "KDE Connect": ("KDE Connect", "phone <-> desktop (HEAVY)"),
 "Server SSH": ("SSH server", "get into the desktop from your PC "
               "(port 22)"),
 "Client SSH": ("SSH client", "ssh, scp to other PCs"),
 "VNC (x11vnc)": ("VNC (x11vnc)", "see the desktop from your PC"),
 "ADB": ("ADB", "android debug bridge"),
 "Python 3 completo": ("Full Python 3", "interpreter, pip, venv"),
 "Compilatore C/C++": ("C/C++ compiler", "gcc, make (HEAVY)"),
 "rsync": ("rsync", "sync folders"),
 "tmux": ("tmux", "persistent terminal sessions"),
 "Samba client": ("Samba client", "Windows network folders"),
 "Xarchiver": ("Xarchiver", "zip/tar/7z archives"),
 "Supporto archivi": ("Archive support", "zip, 7z from the terminal"),
 "htop": ("htop", "terminal process monitor"),
 "Midnight Commander": ("Midnight Commander", "terminal file manager"),
 "Git": ("Git", "version control"),
 "nano": ("nano", "terminal editor"),
 "wget / curl": ("wget / curl", "terminal downloads"),
 "Info sistema": ("System info", "neofetch, lshw"),
 "ncdu": ("ncdu", "interactive disk usage"),
 "tree": ("tree", "tree-style folder listing"),
 "fzf": ("fzf", "terminal fuzzy finder"),
 "jq": ("jq", "JSON processor"),
 "iotop": ("iotop", "disk I/O monitor"),
 "nmap": ("nmap", "network and port scanning"),
 "traceroute": ("traceroute", "trace the network path"),
 "dig / nslookup": ("dig / nslookup", "DNS diagnostics"),
 "iperf3": ("iperf3", "measure bandwidth between two hosts"),
 "duf": ("duf", "disk space, readable columns"),
 "lsof": ("lsof", "which processes hold what open"),
 "psmisc": ("psmisc", "killall, fuser, pstree"),
 "sqlite3": ("sqlite3", "lightweight command-line database"),
 "bc": ("bc", "calculator for scripts/terminal"),
 "ImageMagick": ("ImageMagick", "convert/crop images from the CLI"),
 "yt-dlp": ("yt-dlp", "download video/audio from the command line"),
 "xterm": ("xterm", "real X terminal -- needed for interactive CLI "
           "tools and the Terminal entry"),
 "matchbox-window-manager": ("matchbox-window-manager", "makes windows "
                            "go fullscreen -- without it xterm stays "
                            "small in a corner"),
 "cmatrix": ("cmatrix", "The Matrix digital rain in your terminal"),
 "nyancat": ("nyancat", "the rainbow cat, in ASCII"),
 "sl": ("sl", "a steam train crosses your terminal"),
 "cowsay": ("cowsay", "a cow (or other) saying whatever you want"),
 "lolcat": ("lolcat", "rainbow-colours the output of any command"),
 "fortune": ("fortune", "random quotes on every terminal launch"),
 "figlet": ("figlet", "huge ASCII art text banners"),
 "nsnake": ("nsnake", "the classic Nokia snake, in your terminal"),
 "moon-buggy": ("moon-buggy", "jump craters on the moon"),
 "bastet": ("bastet", "Tetris, but it always gives you the worst "
           "piece"),
 "pacman4console": ("pacman4console", "Pac-Man in ASCII"),
 "ninvaders": ("ninvaders", "Space Invaders in your terminal"),
}

AUTOSTART_OK = {
    "File manager", "Terminale", "Task manager", "Blocco note",
    "NetSurf", "Falkon", "Dillo", "Transmission", "FileZilla", "Remmina",
    "Audacious", "Ristretto",
    "mtPaint", "GIMP", "AbiWord", "Gnumeric", "Lettore PDF", "Galculator",
    "Syncthing", "Barrier", "KDE Connect", "Server SSH", "VNC (x11vnc)",
    "Xarchiver",
}
AUTOSTART_EXEC = {i[3].split()[0].split("/")[-1]
                  for _c, items in CATEGORIES for i in items
                  if i[0] in AUTOSTART_OK}

# I numeri "Button N" di QJoyPad dipendono dal driver joydev del kernel:
# li calcoliamo leggendo il pad, non tirando a indovinare (jsmap).
KNOWN_NAMES = {304: "A", 305: "B", 306: "Y", 307: "X", 308: "L1",
               309: "R1", 310: "SELECT", 311: "START", 312: "MENU",
               314: "L2", 315: "R2"}
EXTRA_NAMES = ["L3", "R3"]
# tasti volume: sono KEY_ non BTN_, quindi QJoyPad non li vede mai.
# Restano usabili solo dalle funzioni gestite da VoidDesk (es. tastiera).
VOLUME_KEYS = {114: "VOL-", 115: "VOL+"}

PAD_PATH, PAD_KEYS = jsmap.find_pad()
EV2QJ = jsmap.ev_to_qj(PAD_KEYS) if PAD_KEYS else {}


def _build_names():
    out = dict(VOLUME_KEYS)
    for c in sorted(PAD_KEYS or ()):
        if 256 <= c <= 319:
            out[c] = KNOWN_NAMES.get(c)
    extra = [c for c in sorted(PAD_KEYS or ())
             if 256 <= c <= 319 and c not in KNOWN_NAMES]
    for i, c in enumerate(extra):
        out[c] = EXTRA_NAMES[i] if i < len(EXTRA_NAMES) else "B%d" % c
    return {k: v for k, v in out.items() if v}


EV2NAME = _build_names() or dict(KNOWN_NAMES)
NAME2EV = {v: k for k, v in EV2NAME.items()}


def ev_of(name):
    return NAME2EV.get(name)


# funzioni rimappabili: chiave -> (etichetta it, etichetta en, icona,
#                                  azione QJoyPad, default [evdev])
FUNCS_DEF = [
    ("click_l", "Click sinistro", "Left click", "mouse", "mouse 1",
     ["A", "L3"]),
    ("click_r", "Click destro", "Right click", "mouse", "mouse 3",
     ["X", "R3"]),
    ("click_m", "Click centrale", "Middle click", "mouse", "mouse 2", ["Y"]),
    ("wheel_up", "Rotella su", "Wheel up", "mouse", "mouse 4", ["R1"]),
    ("wheel_dn", "Rotella giu'", "Wheel down", "mouse", "mouse 5", ["L1"]),
    ("back", "Indietro", "Back", "globe", "key 166", ["B"]),
    ("enter", "Invio", "Enter", "keyboard", "key 36", ["START"]),
    ("esc", "Esc", "Esc", "keyboard", "key 9", ["SELECT"]),
    ("kbd", "Mostra/nascondi tastiera", "Toggle keyboard", "keyboard",
     "__kbd__", ["MENU"]),
]
# risolvo i nomi in codici evdev realmente presenti sul pad
FUNCS = [(k, it, en, ic, act,
          [ev_of(n) for n in names if ev_of(n) is not None])
         for k, it, en, ic, act, names in FUNCS_DEF]
FUNC_BY_KEY = {f[0]: f for f in FUNCS}


def default_map():
    return {f[0]: list(f[5]) for f in FUNCS}


def write_custom_layout(cfg, path):
    """Genera il .lyt di QJoyPad dalla mappatura personalizzata."""
    m = cfg.get("map") or default_map()
    stick = cfg.get("mouse_stick", "sinistro")
    out = ["# QJoyPad 4.3 Layout File", "# VOIDDESK - mappatura utente",
           "Joystick 1 {"]
    if stick == "sinistro":
        out += ["\tAxis 1: gradient, maxSpeed 3, mouse+h",
                "\tAxis 2: gradient, maxSpeed 3, mouse+v",
                "\tAxis 3: gradient, +key 114, -key 113",
                "\tAxis 4: gradient, +key 117, -key 112"]
    else:
        out += ["\tAxis 3: gradient, maxSpeed 3, mouse+h",
                "\tAxis 4: gradient, maxSpeed 3, mouse+v",
                "\tAxis 1: gradient, +key 114, -key 113",
                "\tAxis 2: gradient, +key 117, -key 112"]
    out += ["\tAxis 5: +key 114, -key 113", "\tAxis 6: +key 116, -key 111"]
    learned = cfg.get("qj_map", {})
    for key, evs in m.items():
        f = FUNC_BY_KEY.get(key)
        if not f or f[4] == "__kbd__":      # la tastiera la gestisce il watcher
            continue
        for ev in evs:
            qj = learned.get(str(ev)) or EV2QJ.get(int(ev))
            if qj:
                out.append("\tButton %d: %s" % (qj, f[4]))
    out.append("}")
    try:
        with open(path, "w") as fh:
            fh.write("\n".join(out) + "\n")
        return True
    except OSError:
        return False


# traduzioni di categorie, descrizioni del catalogo e valori ricorrenti
CAT_EN = {
    "AMBIENTI DESKTOP": "DESKTOP ENVIRONMENTS",
    "BASE / DRIVER": "BASE / DRIVERS", "DESKTOP XFCE": "XFCE DESKTOP",
    "INPUT / TASTIERA": "INPUT / KEYBOARD", "PERIFERICHE": "DEVICES",
    "BROWSER / RETE": "BROWSER / NETWORK", "MULTIMEDIA": "MULTIMEDIA",
    "GRAFICA / UFFICIO": "GRAPHICS / OFFICE", "STRUMENTI / CLI": "TOOLS / CLI",
    "RETE / SVILUPPO": "NETWORK / DEV",
}
DESC_EN = {
    "il server grafico": "the graphics server",
    "uscita su framebuffer": "framebuffer output",
    "tasti e stick": "buttons and sticks",
    "avvio della sessione": "session startup",
    "xset, xrefresh, xdpyinfo": "xset, xrefresh, xdpyinfo",
    "comunicazione tra applicazioni": "inter-app communication",
    "font di sistema": "system fonts",
    "connessioni https": "https connections",
    "gestore di sessione": "session manager",
    "cornici e finestre": "window frames",
    "barra applicazioni": "taskbar",
    "sfondo e icone": "wallpaper and icons",
    "aspetto, tastiera, mouse": "appearance, keyboard, mouse",
    "Thunar": "Thunar",
    "terminale grafico": "graphical terminal",
    "processi e memoria": "processes and memory",
    "catture schermo": "screen captures",
    "editor di testo": "text editor",
    "gamepad -> mouse e tasti": "gamepad -> mouse and keys",
    "tastiera virtuale a schermo": "on-screen keyboard",
    "serve all'auto-comparsa tastiera": "needed for keyboard auto-show",
    "automazione finestre": "window automation",
    "finestre di dialogo": "dialog windows",
    "amixer, alsamixer, aplay": "amixer, alsamixer, aplay",
    "server audio e mixer grafico": "sound server and graphical mixer",
    "bluetoothctl + gestore grafico": "bluetoothctl + graphical manager",
    "reti wifi dal desktop": "wifi networks from the desktop",
    "automount chiavette in Thunar": "USB automount in Thunar",
    "ip, ping, iwconfig": "ip, ping, iwconfig",
    "browser leggerissimo (~20MB)": "ultra-light browser (~20MB)",
    "browser Qt completo (~350MB)": "full Qt browser (~350MB)",
    "browser minimale, velocissimo": "minimal, very fast browser",
    "client torrent": "torrent client",
    "trasferimento FTP/SFTP": "FTP/SFTP transfers",
    "desktop remoto RDP/VNC": "RDP/VNC remote desktop",
    "player video": "video player",
    "player musicale leggero": "light music player",
    "visualizzatore immagini": "image viewer",
    "conversione e codec": "conversion and codecs",
    "disegno e ritocco leggero": "light drawing and editing",
    "fotoritocco completo (PESANTE)": "full photo editor (HEAVY)",
    "videoscrittura": "word processor",
    "fogli di calcolo": "spreadsheets",
    "visualizzatore PDF": "PDF viewer",
    "calcolatrice": "calculator",
    "archivi zip/tar/7z": "zip/tar/7z archives",
    "zip, 7z da terminale": "zip, 7z from the terminal",
    "monitor processi da terminale": "process monitor for the terminal",
    "file manager da terminale": "terminal file manager",
    "controllo versione": "version control",
    "interprete e pip": "interpreter and pip",
    "editor da terminale": "terminal editor",
    "download da terminale": "downloads from the terminal",
    "neofetch, lshw": "neofetch, lshw",
    "tastiera virtuale (MENU la apre)": "on-screen keyboard (MENU opens it)",
    "gestione reti (puo' litigare con muOS)":
        "network manager (may fight with muOS)",
    "entra nel desktop dal PC (porta 22)":
        "log into the desktop from your PC (port 22)",
    "ssh, scp verso altri PC": "ssh, scp to other machines",
    "vedi il desktop dal PC": "see the desktop from your PC",
    "android debug bridge": "android debug bridge",
    "interprete, pip, venv": "interpreter, pip, venv",
    "gcc, make (PESANTE)": "gcc, make (HEAVY)",
    "sincronizza cartelle": "sync folders",
    "sessioni terminale persistenti": "persistent terminal sessions",
    "cartelle di rete Windows": "Windows network shares",
    "sincronizza file (muOS ne ha uno suo)":
        "file sync (muOS has its own instance)",
    "VPN personale (script ufficiale)": "personal VPN (official script)",
    "mouse e tastiera dal PC via rete": "mouse and keyboard from your PC",
    "telefono <-> desktop (PESANTE)": "phone <-> desktop (HEAVY)",
}
VAL_EN = {
    "sinistro": "left stick", "classico": "right stick", "custom": "custom",
    "destro": "right", "ambra": "amber", "cremisi": "crimson",
    "ciano": "cyan", "verde": "green", "acciaio": "steel",
    "installato": "installed", "non installato": "not installed",
    "assente": "missing", "attivo": "on", "spento": "off",
    "non connesso": "not connected", "n/d": "n/a",
    "tutte presenti": "all present", "non raggiungibile": "unreachable",
    "curl assente": "curl missing",
    "piccolo": "small", "normale": "normal", "grande": "large",
    "molto grande": "extra large",
}
STAT_EN = {
    "SISTEMA": "SYSTEM", "MEMORIA": "MEMORY", "ARCHIVIAZIONE": "STORAGE",
    "RETE": "NETWORK", "AUDIO": "AUDIO", "DESKTOP XFCE": "XFCE DESKTOP",
    "RUNTIME": "RUNTIME", "KERNEL": "KERNEL", "ACCESO DA": "UPTIME",
    "TEMPERATURA": "TEMPERATURE", "RAM": "RAM", "SD1 (MMC)": "SD1 (MMC)",
    "SD2 (SDCARD)": "SD2 (SDCARD)", "IMMAGINE XFCE": "XFCE IMAGE",
    "WIFI": "WI-FI", "SEGNALE": "SIGNAL", "INDIRIZZO IP": "IP ADDRESS",
    "BLUETOOTH": "BLUETOOTH", "INTERNET": "INTERNET", "VOLUME": "VOLUME",
    "STATO": "STATUS", "ULTIMA SESSIONE": "LAST SESSION",
    "CONTROLLER": "CONTROLLER", "INTERFACCIA": "INTERFACE",
    "connesso": "connected", "PYTHON": "PYTHON", "PYGAME": "PYGAME",
    "DIPENDENZE": "DEPENDENCIES", "VOID SUITE": "VOID SUITE",
    "PIATTAFORMA": "PLATFORM", "COME FUNZIONA": "HOW IT WORKS",
    "CREDITI": "CREDITS", "TARGET": "TARGET", "OS": "OS",
    "DESKTOP": "DESKTOP", "UI": "UI",
}

COMP_MENU = [
    ("install", "pkg", "Installa / Reinstalla software",
     "Install / reinstall software",
     "catalogo con stato di ogni componente",
     "catalogue with per-component status"),
    ("remove", "archive", "Disinstalla software", "Uninstall software",
     "libera spazio rimuovendo pacchetti",
     "free space by removing packages"),
    ("autostart", "start", "Avvio al boot", "Startup apps",
     "quali programmi partono con XFCE",
     "which programs start with XFCE"),
    ("update", "download", "Aggiorna sistema", "Update system",
     "apt update + upgrade nel chroot",
     "apt update + upgrade in the chroot"),
    ("clean", "task", "Pulisci cache apt", "Clean apt cache",
     "recupera spazio nell'immagine", "reclaim space in the image"),
    ("shell", "terminal", "Terminal shell", "Terminal shell",
     "terminale con tastiera a schermo",
     "terminal with on-screen keyboard"),
]

TR = {
 "it": {
  "xfce_run": "▶  DESKTOP XFCE", "xfce_inst": "▶  INSTALLA DESKTOP XFCE",
  "xfce_run_s": "avvia il desktop a schermo intero",
  "xfce_inst_s": "~400MB via WiFi, 10-20 minuti",
  "comp": "◈  VOID INSTALLER",
  "comp_s": "driver, desktop, browser, tool: stato e installazione",
  "info": "▤  VOID STATS",
  "info_s": "sistema, memoria, rete, audio, desktop",
  "opts": "⚒  OPZIONI", "opts_s": "tema, lingua, controller, avvio",
  "logs": "≡  LOGS & ABOUT", "logs_s": "diari di bordo e info sul progetto",
  "quit": "◉  ESCI", "quit_s": "torna a muOS",
  "open": "apri", "back": "indietro", "exit": "esci", "install": "installa",
  "change": "cambia", "row": "riga", "page": "pagina", "sel": "seleziona",
  "select": "seleziona", "details": "dettagli", "confirm": "conferma",
  "view": "stile",
  "all": "tutti/nessuno", "inst_sel": "installa selezione",
  "title_comp": "VOID INSTALLER", "title_info": "VOID STATS",
  "title_logs": "LOGS & ABOUT", "title_opts": "OPZIONI",
  "checking": "controllo in corso...",
  "need_xfce": "Prima installa il desktop XFCE (voce in alto nel menu).",
  "opt_theme": "Tema colore", "opt_home_style": "Stile menu principale",
  "opt_font_scale": "Dimensione testo",
  "opt_lang": "Lingua",
  "opt_ctrl": "Profilo controller", "opt_batt": "Batteria nell'header",
  "opt_st_clock": "Orologio nell'header",
  "opt_st_batt": "Icona batteria", "opt_st_vol": "Icona volume",
  "opt_st_bt": "Icona bluetooth", "opt_st_wifi": "Icona wifi",
  "opt_st_usb": "Icona USB/ADB",
  "opt_st_hotspot": "Icona hotspot",
  "opt_intro": "Sigla d'avvio",
  "sess": "START SESSION",
  "sess_s": "scegli e avvia l'ambiente desktop",
  "e_active": "ATTIVO", "e_inst": "Installato",
  "e_missing": "Non installato",
  "e_base": "richiede la base (~400MB)",
  "e_launch": "A: avvia", "sess_a": "avvia / installa",
  "ed_boot": "Sigla d'avvio (bootanim)",
  "ed_repair": "Ripara / reinstalla pacchetti",
  "ed_log": "Vedi log di sessione",
  "ed_remove": "Rimuovi ambiente",
  "ed_update": "Controlla e aggiorna sistema",
  "ed_removed": "ambiente rimosso", "ed_confirm_rm": "Rimuovere questo ambiente?",
  "img_never": "mai controllato", "img_updated": "controllato il",
  "img_stale": "da un po': valuta un controllo",
  "mapps": "MUOS APPS", "mapps_s": "gestore completo: avvia, governor, glyph, rimuovi",
  "mapps_t": "MUOS APPS", "mapps_none": "nessuna app in MUOS/application",
  "mapps_scan": "scansione e sistemazione glyph...",
  "mapps_go": "avvia", "mapps_r1": "glyph+scan",
  "h_forge": "FORGE", "h_forge_s": "installer, avvio al boot, update",
  "h_work": "WORKSHOP", "h_work_s": "stats, diagnosi, log, memorie, boost",
  "h_up": "UPLINK", "h_up_s": "rete: wifi, hotspot, bluetooth · lingue, tastiere",
  "h_tool": "Rt:TOOLBOX", "h_tool_s": "terminale, calcolatrice, utility",
  "h_info": "INFO & ABOUT", "h_info_s": "progetto, manuale, guida rapida",
  "h_set": "SETTINGS", "h_set_s": "aspetto, audio, lingua dell'app",
  "h_exit": "SHUTDOWN", "h_exit_s": "torna a muOS",
  "f_inst": "Void Installer", "f_inst_s": "installa e rimuovi (L1: tab)",
  "f_auto": "Avvio al boot", "f_auto_s": "app che partono col desktop",
  "f_upd": "Aggiorna sistema", "f_upd_s": "apt update + upgrade",
  "f_vdupd": "Void-Desk Update", "f_vdupd_s": "aggiorna l'app da GitHub",
  "f_cli": "CLI Tools", "f_cli_s": "roba simpatica da terminale",
  "w_stats": "Void Stats", "w_stats_s": "il quadro completo del sistema",
  "w_diag": "Void Diag", "w_diag_s": "salute di immagine e sessioni",
  "w_sto": "Memorie", "w_sto_s": "partizioni, spazio, cosa occupa",
  "w_boost": "Void Boost", "w_boost_s": "swap e governor, separati",
  "w_clean": "Pulisci cache apt", "w_clean_s": "recupera spazio",
  "w_logs": "Registro log", "w_logs_s": "tutti i diari, per area",
  "t_clock": "Clock", "t_clock_s": "digitale o analogico, con sveglie",
  "u_dlang": "Lingua desktop", "u_dlang_s": "solo gli ambienti, non l'app",
  "u_kmb": "Layout tastiera schermo", "u_kmb_s": "matchbox-keyboard",
  "u_kx": "Layout tastiera fisica", "u_kx_s": "se ne colleghi una USB",
  "u_ctrl": "Profilo controller", "u_ctrl_s": "stick e mappatura mouse",
  "u_map": "Mappatura tasti", "u_map_s": "ridefinisci i pulsanti",
  "u_wifi": "WiFi", "u_wifi_s": "gestore completo: scan e connetti",
  "u_bt": "Bluetooth", "u_bt_s": "gestore completo: pair e connetti",
  "u_hot": "Hotspot", "u_hot_s": "rileva e usa lo script muOS",
  "t_sh": "Terminale", "t_sh_s": "shell nel chroot, tastiera a schermo",
  "t_calc": "Calcolatrice", "t_calc_s": "scientifica, nativa Void",
  "t_fm": "File manager", "t_fm_s": "VOID FILES: nativo, completo",
  "t_mc": "Midnight Commander", "t_mc_s": "file manager da terminale",
  "t_ftp": "FTP", "t_ftp_s": "client FTP nativo, con profili",
  "t_ed": "Editor di testo", "t_ed_s": "VOID EDIT: apri e modifica qui",
  "t_sync": "Syncthing", "t_sync_s": "pannello nativo via REST",
  "t_cal": "Calendario", "t_cal_s": "eventi: data, ora, priorita'",
  "t_note": "Note", "t_note_s": "appunti rapidi: scrivi e via",
  "t_rss": "RSS Reader", "t_rss_s": "notizie, tech, anime: eng + ita",
  "t_wx": "Meteo", "t_wx_s": "città monitorate, previsioni settimanali",
  "wx_add": "+ aggiungi città", "wx_none": "nessuna città monitorata",
  "wx_searching": "cerco la città...", "wx_updating": "aggiorno il meteo...",
  "wx_notfound": "nessuna città trovata", "wx_pick": "quale intendi?",
  "wx_err": "meteo non disponibile",
  "deps_title": "DIPENDENZE MANCANTI",
  "deps_body": "non puo' essere avviata su questo dispositivo: mancano le seguenti dipendenze",
  "deps_ask": "Scaricare e installare gli elementi mancanti?",
  "feat_hotspot": "Hotspot",
  "rss_upd": "aggiorno i feed...", "rss_empty": "nessun feed attivo",
  "rss_none": "nessuna notizia: R1 per aggiornare",
  "rss_sel_hint": "X: attiva/disattiva  ·  aggiungi i tuoi in",
  "rss_err": "errore", "rss_eng": "INGLESE", "rss_ita": "ITALIANO",
  "rss_gen": "GENERALE (personalizzati)",
  "cat_news": "news", "cat_tech": "tech", "cat_linux": "linux",
  "cat_gaming": "gaming", "cat_retro": "retrogaming",
  "cat_anime": "anime", "cat_general": "generale",
  "t_mon": "Void Monitor", "t_mon_s": "cpu, ram, temp, rete: live",
  "t_py": "Python", "t_py_s": "console interattiva (host muOS)",
  "w_bak": "Backup immagine", "w_bak_s": "salva e ripristina xfce.img",
  "wm_scan": "cerco le reti..." , "wm_pass": "PASSWORD WIFI",
  "bt_scan": "cerco dispositivi (8s)...",
  "t_tsg": "Tailscale", "t_tsg_s": "pannello nativo // cuore Rt",
  "t_tss": "SSH via Tailscale", "t_tss_s": "in arrivo nella 6.1",
  "i_about": "Il progetto", "i_about_s": "versione, crediti, stack",
  "i_man": "Manuale tecnico", "i_man_s": "capitoli, tutto spiegato",
  "i_guide": "Guida rapida", "i_guide_s": "i comandi essenziali",
  "i_manifesto": "Manifesto", "i_manifesto_s": "un segnale dal VOID",
  "installed": "installato", "notinst": "non installato - A: installa",
  "opens_desk": "si apre nel desktop: la trovi nel menu applicazioni",
  "tab_inst": "TAB: INSTALLA", "tab_rm": "TAB: RIMUOVI",
  "gov": "Governor", "glyphp": "Change Glyph", "arch": "Archivia (.muxapp)",
  "removeapp": "Rimuovi app", "sysapp": "APP DI SISTEMA",
  "confirm_rm": "Confermi la rimozione? A: si'   B: no",
  "arch_ok": "archivio creato in", "size": "dimensione",
  "clock_set": "A: applica ora e fuso", "applied": "applicato",
  "bs_swap": "Boost SWAP (zram/file)", "bs_cpu": "Boost CPU (governor)",
  "opt_fx": "Interferenze video",
  "opt_sfx": "Suoni interfaccia",
  "opt_anim": "Transizioni a finestra",
  "opt_bgm": "Musica delle sigle",
  "opt_boost": "Void Boost (swap, cpu)",
  "yes": "si'", "no": "no",
  "ho_xfce": "AVVIO DESKTOP XFCE...",
  "ho_inst": "INSTALLAZIONE DESKTOP XFCE...",
  "ho_pkg": "PASSO ALL'INSTALLATORE...",
  "ho_rm": "PASSO AL DISINSTALLATORE...",
  "ho_update": "AGGIORNAMENTO SISTEMA...",
  "cleaning": "pulizia della cache apt...",
  "no_space": "Solo %s liberi nell'immagine XFCE.",
  "no_space_s": "Usa 'Pulisci cache apt' o disinstalla qualcosa.",
  "guide": "GUIDA RAPIDA", "guide_s": "comandi del menu e del desktop",
  "k_ud": "SU/GIU", "k_lr": "SX/DX",
  "free": "liberi: %s",
  "n_sel": "%d selezionati", "mounting": "leggo lo stato dei componenti...",
  "about": "INFO SUL PROGETTO", "about_s": "suite Void, piattaforma, crediti",
  "title_compmenu": "VOID INSTALLER", "refresh": "aggiorna",
  "title_remove": "DISINSTALLA SOFTWARE", "title_auto": "AVVIO AL BOOT",
  "remove_btn": "disinstalla", "auto_on": "all'avvio", "auto_off": "no",
  "not_inst": "non installato", "sel_none": "nessuna voce selezionata",
  "no_base": "I componenti base del desktop non si possono rimuovere:",
  "confirm_rm": "Disinstallo %d componenti?", "yes_a": "A = si'",
  "no_b": "B = annulla", "shell_hint": "SELECT esce",
  "opt_map": "Mappatura tasti", "title_map": "MAPPATURA TASTI",
  "map_stick": "Mouse sullo stick", "press": "PREMI IL TASTO DA ASSEGNARE A:",
  "press_s": "attendi 5 secondi per annullare",
  "used_by": "Il tasto %s e' gia' usato da: %s",
  "swap_q": "A = scambia le due funzioni     B = annulla",
  "assign": "assegna", "reset": "ripristina", "reset_all": "tutti default",
  "none": "(nessuno)",
 },
 "en": {
  "xfce_run": "▶  XFCE DESKTOP", "xfce_inst": "▶  INSTALL XFCE DESKTOP",
  "xfce_run_s": "launch the full-screen Linux desktop",
  "xfce_inst_s": "about 400MB over Wi-Fi, 10-20 minutes",
  "comp": "◈  VOID INSTALLER",
  "comp_s": "drivers, desktop, browsers, tools: status and install",
  "info": "▤  VOID STATS",
  "info_s": "system, memory, network, audio, desktop",
  "opts": "⚒  SETTINGS", "opts_s": "theme, language, controller, startup",
  "logs": "≡  LOGS & ABOUT", "logs_s": "log files and project info",
  "quit": "◉  EXIT", "quit_s": "back to muOS",
  "open": "open", "back": "back", "exit": "exit", "install": "install",
  "change": "change", "row": "line", "page": "scroll", "sel": "select",
  "select": "select", "details": "details", "confirm": "confirm",
  "view": "view",
  "all": "all / none", "inst_sel": "install selection",
  "title_comp": "VOID INSTALLER", "title_info": "VOID STATS",
  "title_logs": "LOGS & ABOUT", "title_opts": "SETTINGS",
  "checking": "checking...",
  "need_xfce": "Install the XFCE desktop first (top menu entry).",
  "opt_theme": "Colour theme", "opt_home_style": "Main menu style",
  "opt_font_scale": "Text size",
  "opt_lang": "Language",
  "opt_ctrl": "Controller profile", "opt_batt": "Status bar icons",
  "opt_st_clock": "Clock in header",
  "opt_st_batt": "Battery icon", "opt_st_vol": "Volume icon",
  "opt_st_bt": "Bluetooth icon", "opt_st_wifi": "WiFi icon",
  "opt_st_usb": "USB/ADB icon",
  "opt_st_hotspot": "Hotspot icon",
  "opt_intro": "Intro animation",
  "sess": "START SESSION",
  "sess_s": "choose and launch a desktop",
  "e_active": "ACTIVE", "e_inst": "Installed",
  "e_missing": "Not installed",
  "e_base": "needs the base (~400MB)",
  "e_launch": "A: launch", "sess_a": "launch / install",
  "ed_boot": "Boot animation (bootanim)",
  "ed_repair": "Repair / reinstall packages",
  "ed_log": "View session log",
  "ed_remove": "Remove environment",
  "ed_update": "Check and update system",
  "ed_removed": "environment removed", "ed_confirm_rm": "Remove this environment?",
  "img_never": "never checked", "img_updated": "checked on",
  "img_stale": "a while ago: worth a check",
  "mapps": "MUOS APPS", "mapps_s": "full manager: launch, governor, glyph, remove",
  "mapps_t": "MUOS APPS", "mapps_none": "no apps in MUOS/application",
  "mapps_scan": "scanning and fixing glyphs...",
  "mapps_go": "launch", "mapps_r1": "glyph+scan",
  "h_forge": "FORGE", "h_forge_s": "installer, startup apps, update",
  "h_work": "WORKSHOP", "h_work_s": "stats, diagnostics, logs, storage",
  "h_up": "UPLINK", "h_up_s": "network: wifi, hotspot, bluetooth · languages, keyboards",
  "h_tool": "Rt:TOOLBOX", "h_tool_s": "terminal, calculator, utilities",
  "h_info": "INFO & ABOUT", "h_info_s": "project, manual, quick guide",
  "h_set": "SETTINGS", "h_set_s": "look, audio, app language",
  "h_exit": "SHUTDOWN", "h_exit_s": "back to muOS",
  "f_inst": "Void Installer", "f_inst_s": "install & remove (L1: tab)",
  "f_auto": "Startup apps", "f_auto_s": "apps that boot with the desktop",
  "f_upd": "Update system", "f_upd_s": "apt update + upgrade",
  "f_vdupd": "Void-Desk Update", "f_vdupd_s": "update the app from GitHub",
  "f_cli": "CLI Tools", "f_cli_s": "fun stuff for the terminal",
  "w_stats": "Void Stats", "w_stats_s": "the full system picture",
  "w_diag": "Void Diag", "w_diag_s": "image and session health",
  "w_sto": "Storage", "w_sto_s": "partitions, space, what fills it",
  "w_boost": "Void Boost", "w_boost_s": "swap and governor, split",
  "w_clean": "Clean apt cache", "w_clean_s": "reclaim space",
  "w_logs": "Log registry", "w_logs_s": "every diary, by area",
  "t_clock": "Clock", "t_clock_s": "digital or analog, with alarms",
  "u_dlang": "Desktop language", "u_dlang_s": "desktops only, not the app",
  "u_kmb": "On-screen kbd layout", "u_kmb_s": "matchbox-keyboard",
  "u_kx": "Physical kbd layout", "u_kx_s": "if you plug a USB one",
  "u_ctrl": "Controller profile", "u_ctrl_s": "stick and mouse mapping",
  "u_map": "Button mapping", "u_map_s": "redefine the pads",
  "u_wifi": "WiFi", "u_wifi_s": "full manager: scan and join",
  "u_bt": "Bluetooth", "u_bt_s": "full manager: pair and connect",
  "u_hot": "Hotspot", "u_hot_s": "detects and drives the muOS script",
  "t_sh": "Terminal", "t_sh_s": "chroot shell, on-screen keys",
  "t_calc": "Calculator", "t_calc_s": "scientific, Void-native",
  "t_fm": "File manager", "t_fm_s": "VOID FILES: native, complete",
  "t_mc": "Midnight Commander", "t_mc_s": "terminal file manager",
  "t_ftp": "FTP", "t_ftp_s": "native FTP client, with profiles",
  "t_ed": "Text editor", "t_ed_s": "VOID EDIT: open and edit here",
  "t_sync": "Syncthing", "t_sync_s": "native panel via REST",
  "t_cal": "Calendar", "t_cal_s": "events: date, time, priority",
  "t_note": "Notes", "t_note_s": "quick notes: jot and go",
  "t_rss": "RSS Reader", "t_rss_s": "news, tech, anime: eng + it",
  "t_wx": "Weather", "t_wx_s": "monitored cities, weekly forecast",
  "wx_add": "+ add city", "wx_none": "no cities monitored",
  "wx_searching": "searching city...", "wx_updating": "updating weather...",
  "wx_notfound": "no city found", "wx_pick": "which one did you mean?",
  "wx_err": "weather unavailable",
  "deps_title": "MISSING DEPENDENCIES",
  "deps_body": "can't be started on this device: the following dependencies are missing",
  "deps_ask": "Download and install the missing pieces?",
  "feat_hotspot": "Hotspot",
  "rss_upd": "updating feeds...", "rss_empty": "no active feeds",
  "rss_none": "no news yet: R1 to refresh",
  "rss_sel_hint": "X: enable/disable  ·  add your own in",
  "rss_err": "error", "rss_eng": "ENGLISH", "rss_ita": "ITALIAN",
  "rss_gen": "GENERAL (custom)",
  "cat_news": "news", "cat_tech": "tech", "cat_linux": "linux",
  "cat_gaming": "gaming", "cat_retro": "retrogaming",
  "cat_anime": "anime", "cat_general": "general",
  "t_mon": "Void Monitor", "t_mon_s": "cpu, ram, temp, net: live",
  "t_py": "Python", "t_py_s": "interactive console (muOS host)",
  "w_bak": "Image backup", "w_bak_s": "save and restore xfce.img",
  "wm_scan": "scanning networks...", "wm_pass": "WIFI PASSWORD",
  "bt_scan": "scanning devices (8s)...",
  "t_tsg": "Tailscale", "t_tsg_s": "native panel // Rt core",
  "t_tss": "SSH over Tailscale", "t_tss_s": "coming in 6.1",
  "i_about": "The project", "i_about_s": "version, credits, stack",
  "i_man": "Technical manual", "i_man_s": "chapters, everything explained",
  "i_guide": "Quick guide", "i_guide_s": "the essential controls",
  "i_manifesto": "Manifesto", "i_manifesto_s": "a signal from the VOID",
  "installed": "installed", "notinst": "not installed - A: install",
  "opens_desk": "opens in the desktop: find it in the app menu",
  "tab_inst": "TAB: INSTALL", "tab_rm": "TAB: REMOVE",
  "gov": "Governor", "glyphp": "Change Glyph", "arch": "Archive (.muxapp)",
  "removeapp": "Remove app", "sysapp": "SYSTEM APP",
  "confirm_rm": "Confirm removal? A: yes   B: no",
  "arch_ok": "archive created in", "size": "size",
  "clock_set": "A: apply time and zone", "applied": "applied",
  "bs_swap": "SWAP boost (zram/file)", "bs_cpu": "CPU boost (governor)",
  "opt_fx": "Video interference",
  "opt_sfx": "UI sounds",
  "opt_anim": "Window transitions",
  "opt_bgm": "Bootanim music",
  "opt_boost": "Void Boost (swap, cpu)",
  "yes": "on", "no": "off",
  "ho_xfce": "STARTING XFCE DESKTOP...",
  "ho_inst": "INSTALLING XFCE DESKTOP...",
  "ho_pkg": "HANDING OFF TO INSTALLER...",
  "ho_rm": "HANDING OFF TO UNINSTALLER...",
  "ho_update": "UPDATING SYSTEM...",
  "cleaning": "cleaning the apt cache...",
  "no_space": "Only %s free inside the XFCE image.",
  "no_space_s": "Use 'Clean apt cache' or uninstall something.",
  "guide": "QUICK GUIDE", "guide_s": "menu and desktop controls",
  "k_ud": "UP/DN", "k_lr": "LT/RT",
  "free": "free: %s",
  "n_sel": "%d selected", "mounting": "reading component status...",
  "opt_map": "Button mapping", "title_map": "BUTTON MAPPING",
  "map_stick": "Mouse on stick", "press": "PRESS THE BUTTON TO ASSIGN TO:",
  "press_s": "wait 5 seconds to cancel",
  "used_by": "Button %s is already assigned to: %s",
  "swap_q": "A = swap the two functions     B = cancel",
  "assign": "assign", "reset": "restore default", "reset_all": "reset all",
  "none": "(none)",
  "about": "ABOUT THE PROJECT", "about_s": "Void suite, platform, credits",
  "title_compmenu": "VOID INSTALLER", "refresh": "refresh",
  "title_remove": "UNINSTALL SOFTWARE", "title_auto": "STARTUP APPS",
  "remove_btn": "uninstall", "auto_on": "at startup", "auto_off": "no",
  "not_inst": "not installed", "sel_none": "nothing selected",
  "no_base": "Core desktop components cannot be removed:",
  "confirm_rm": "Uninstall %d components?", "yes_a": "A = yes",
  "no_b": "B = cancel", "shell_hint": "SELECT quits",
 },

}


def font(size):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.Font(None, size)


def chroot_path_exists(root, relpath, depth=0):
    """Come os.path.exists(), ma risolve i link simbolici ASSOLUTI
    come se stessimo davvero dentro il chroot (root), non sul
    filesystem dell'host. Molti pacchetti (figlet e tanti altri)
    usano update-alternatives: il binario vero e' altrove e
    /usr/bin/<nome> e' solo un link assoluto -- senza questa
    risoluzione, dall'host quel link punterebbe a un percorso che su
    muOS stesso non esiste mai, e il pacchetto sembrerebbe sempre
    mancante anche quando e' installato per davvero."""
    if depth > 8:
        return False
    relpath = relpath.lstrip("/")
    full = os.path.join(root, relpath)
    if os.path.islink(full):
        try:
            target = os.readlink(full)
        except OSError:
            return False
        if target.startswith("/"):
            return chroot_path_exists(root, target, depth + 1)
        newrel = os.path.normpath(
            os.path.join(os.path.dirname(relpath), target))
        return chroot_path_exists(root, newrel, depth + 1)
    return os.path.exists(full)


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return "%dB" % n if u == "B" else "%.1f%s" % (n, u)
        n /= 1024.0


def disk_free(path):
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize
    except OSError:
        return None, None


def battery():
    base = "/sys/class/power_supply"
    try:
        for n in os.listdir(base):
            cap = os.path.join(base, n, "capacity")
            if os.path.exists(cap):
                return "%s%%" % open(cap).read().strip()
    except OSError:
        pass
    return "n/d"


bt_on = sysinfo.bt_status
volume_pct = sysinfo.volume
batt_state = sysinfo.battery


def net_test():
    try:
        rc = subprocess.call(["curl", "-sI", "--max-time", "5",
                              "https://ports.ubuntu.com"],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return "OK" if rc == 0 else "non raggiungibile"
    except OSError:
        return "curl assente"


def load_cfg():
    import json
    try:
        with open(os.path.join(DATA, "desk_config.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    import json
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, "desk_config.json"), "w") as f:
            json.dump(cfg, f, indent=1)
    except OSError:
        pass


def mounted(p):
    try:
        return (" %s " % os.path.abspath(p)) in open("/proc/mounts").read()
    except OSError:
        return False


class App(object):
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.surface = pygame.display.set_mode((W, H))
        if not fbdisplay.attach(self.surface):
            print("fbdisplay non disponibile")
        self.cfg = load_cfg()
        self.lang = self.cfg.get("lang", "it")
        self.accent = ACCENTS.get(self.cfg.get("theme", "ambra"),
                                  ACCENTS["ambra"])
        self.sel_bg = sel_tint(self.accent)
        self.bg_img = None
        self.fx_img = None
        self.stripe_img = None
        self.build_style()
        self.build_cli_bg()
        self.build_forge_bg()
        self.trans = None
        self.prev_frame = None
        self.last_sel_rect = None
        self.env_sel = 0
        self.mapps = []
        self.mapp_sel = 0
        self.mapp_icons = {}
        self.hub_sel = 0
        self.clock_f = 0
        self.clock_v = [2026, 1, 1, 0, 0, 0]
        self.calc_expr = ""
        self.calc_sel = 0
        self.calc_ans = 0.0
        self.man_sel = 0
        self.det_sel = 0
        self.boost_sel = 0
        self.confirm = None
        self.osk_buf = ""
        self.osk_cursor = 0
        self.osk_title = ""
        self.osk_cb = None
        self.osk_page = 0
        self.osk_sel = 0
        self.fm_path = None
        self.fm_sel = 0
        self.fm_marked = set()
        self.fm_clip = None
        self.fm_pick = None
        self.fm_items = []
        self.ed_path = ""
        self.ed_lines = [""]
        self.ed_cur = 0
        self.ed_dirty = False
        self.ed_msg = ""
        self.img_path = ""
        self.ftpc = None
        self._ftp_factory = ftplib.FTP
        self.ftp_cwd = "/"
        self.ftp_items = []
        self.ftp_sel = 0
        self.ftp_marked = set()
        self.ftp_prof_sel = 0
        self.sync = None
        self.ts = None
        self.ts_sel = 0
        self.mon = {"cpu": [], "ram": [], "net": [], "tmp": [],
                    "last": None, "t": 0}
        self.py_ns = {}
        self.py_out = [">>> "]
        self.bak_sel = 0
        self.viewer_live = False
        self.wm_nets = []
        self.wm_sel = 0
        self.bt_devs = []
        self.bt_sel = 0
        self.gp_list = []
        self.gp_sel = 0
        self.evs = []
        self.ev_sel = 0
        self.cw = [2026, 1, 1, 12, 0, 0]
        self.cal_cur = [2026, 1, 1]
        self.cal_view = "month"
        self.cw_f = 0
        self.cw_title = ""
        self.cw_edit = None
        self.notes = []
        self.note_sel = 0
        self.rss_items = []
        self.rss_errors = {}
        self.rss_sel = 0
        self.rss_sel_sel = 0
        self.envdet_env = "xfce"
        self.envdet_sel = 0
        self.alarm_sel = 0
        self.alarm_edit = None
        self.aw = [0, 0, 0]
        self.aw_f = 0
        self.aw_title = ""
        self._alarm_ringing = None
        self._alarm_snd = None
        self._alarm_fired_min = None
        self.wx_sel = 0
        self.wx_data = {}
        self.wx_errors = {}
        self.wx_pick_results = []
        self.wx_pick_sel = 0
        self.wx_detail_city = None
        self.mon_tab = 0
        self.deps_missing_list = []
        self.deps_feature_icon = "pkg"
        self.deps_feature_title = ""
        self.hotcfg_sel = 0
        self.hotcfg_ssid = ""
        self.hotcfg_pass = ""
        self.vdupd_result = None
        self.vdupd_progress = 0
        self.clitools_sel = 0
        self.clihub_sel = 0
        self.cliinst_sel = 0
        self.cliinst_marked = set()
        self.cliinst_mode = "install"
        self.clidetail_sel = 0
        self.clidetail_idx = 0
        self.logarchive_sel = 0
        self.clisettings_sel = 0
        self.cli_accent, self.cli_accent_dim = CLI_ACCENTS.get(
            self.cfg.get("cli_accent", "verde"), CLI_ACCENTS["verde"])
        self.mapp_cur = None
        self.mapp_size = None
        self.mapp_grid_cols = 4
        self.toolbox_scroll = 0
        self.sfx = self.build_sfx()
        self.busy_label = ""
        self.busy_t0 = 0.0
        self.img_free = None
        self.img_total = None
        self.build_fonts()
        self.clock = pygame.time.Clock()
        self.running = True
        self.exit_code = 0
        self.stack = ["home"]
        try:
            land = os.path.join(DATA, ".land_clitools")
            if os.path.isfile(land):
                os.remove(land)
                self.stack = ["home", "clihub", "clitools"]
        except OSError:
            pass
        self.sel = 0
        self.sel_log = 0
        self.opt_sel = 0
        self.opt_scroll = 0
        self.scroll = 0
        self.log_lines = []
        self.info_lines = None
        self._stat = ({}, 0.0)
        self._dpad_t = 0.0
        self.map_sel = 0
        self.comp_sel = 0
        self.mode = "install"
        self.js_fd = None
        self.capture_t = 0.0
        self.pending = None
        self.rows = []          # righe del gestore componenti
        self.row_sel = 0
        self.cat_collapsed = set()
        self.marked = set()     # indici selezionati per l'installazione
        self.status = {}        # nome -> True/False/None
        self.logs = self.build_logs()
        evinput.start()
        self.rebuild_menu()
        if self.cfg.get("intro", True) and \
                os.environ.get("VOIDDESK_NOINTRO") != "1":
            try:
                self.play_intro()
            except Exception as e:
                import traceback
                sys.stderr.write("intro non riuscita: %s\n" % e)
                traceback.print_exc(file=sys.stderr)
        # migrazione v6: boost separato in swap+cpu, animazioni/bgm on
        if self.cfg.get("boost") is False:
            self.cfg.setdefault("boost_swap", False)
            self.cfg.setdefault("boost_cpu", False)
        # avviso il loader di consegna (vd_loader) che il menu e' a schermo
        try:
            open("/tmp/.vd_menu_up", "w").close()
        except OSError:
            pass
        # l'avvio automatico di XFCE non esiste piu': pulisco i residui
        self.cfg.pop("auto_xfce", None)
        # bonifica avvio-al-boot: in v4.4 ci si poteva mettere pezzi di
        # sessione; li tolgo dalla config cosi' al prossimo avvio di XFCE
        # i .desktop doppi spariscono e il desktop torna sano.
        a0 = self.cfg.get("autostart") or []
        e0 = self.cfg.get("autostart_exec") or []
        a1 = sorted(n for n in a0 if n in AUTOSTART_OK)
        e1 = sorted(e for e in e0 if e in AUTOSTART_EXEC)
        if a1 != sorted(a0) or e1 != sorted(e0):
            self.cfg["autostart"], self.cfg["autostart_exec"] = a1, e1
            save_cfg(self.cfg)
        try:
            os.remove(os.path.join(DATA, ".autolaunch"))
        except OSError:
            pass

    # ---------------------------------------------------------------- i18n
    def t(self, k):
        return TR.get(self.lang, TR["it"]).get(k, k)

    def tx(self, table, txt):
        """Traduce una stringa di dato/etichetta se la lingua e' inglese."""
        if self.lang != "en" or not txt:
            return txt
        return table.get(txt, txt)

    def rebuild_menu(self):
        xfce_ok = os.path.exists(os.path.join(DATA, ".xfce_ready"))
        t = self.t
        self.menu = [
            (t("sess"), t("sess_s")),
            (t("mapps"), t("mapps_s")),
            (t("h_forge"), t("h_forge_s")),
            (t("h_tool"), t("h_tool_s")),
            (t("h_up"), t("h_up_s")),
            (t("h_work"), t("h_work_s")),
            (t("h_set"), t("h_set_s")),
            (t("h_info"), t("h_info_s")),
            (t("h_exit"), t("h_exit_s")),
        ]
        self.menu_icons = ["start", "window", "forge", "toolbox",
                           "uplink", "workshop", "gear", "book", "power"]

    # ---------------------------------------------------- stile SPDW/BLAME!
    def build_fonts(self):
        """Le quattro taglie di font dell'app, scalate secondo la
        preferenza dell'utente (Impostazioni > Dimensione testo).
        Limitata a 0.85-1.3 apposta: oltre questi margini alcuni
        layout comincerebbero a rompersi."""
        sc = FONT_SCALES.get(self.cfg.get("font_scale", "normale"), 1.0)
        self.f_big = font(round(26 * sc))
        self.f_med = font(round(19 * sc))
        self.f_small = font(round(15 * sc))
        self.f_tiny = font(round(13 * sc))

    def build_forge_bg(self):
        """Sfondo a tema fucina per FORGE: metallo caldo, non verde
        fosforo. Spaziatura griglia 32px: divide esattamente sia 640
        che 480, la stessa lezione imparata dal bug della griglia
        principale -- mai piu' una cucitura visibile allo scorrimento."""
        bg = pygame.Surface((W, H))
        bg.fill((14, 6, 4))
        for gx in range(0, W, 32):
            pygame.draw.line(bg, (46, 18, 10), (gx, 0), (gx, H), 1)
        for gy in range(0, H, 32):
            pygame.draw.line(bg, (46, 18, 10), (0, gy), (W, gy), 1)
        for sy in range(0, H, 3):
            pygame.draw.line(bg, (8, 3, 2), (0, sy), (W, sy), 1)
        self.forge_bg_img = bg

    def forge_backdrop(self):
        t = time.time()
        dx = int((t * 6) % W)
        dy = int((t * 4) % H)
        self.surface.set_clip(pygame.Rect(0, 44, W, H - 44))
        for ox in (-dx, W - dx):
            for oy in (dy, dy - H):
                self.surface.blit(self.forge_bg_img, (ox, oy))
        # braci che salgono, come scintille da una fucina vera
        rnd = random.Random(41)
        for i in range(22):
            seedx = rnd.randrange(W)
            speed = 30 + rnd.random() * 40
            phase = (t * speed + i * 71) % (H + 40)
            ey = H - phase
            if 44 < ey < H:
                ex = seedx + math.sin(t * 1.2 + i) * 10
                flick = 0.5 + 0.5 * abs(math.sin(t * 5 + i))
                col = (int(255 * flick), int(120 * flick), 20)
                pygame.draw.circle(self.surface, col, (int(ex), int(ey)),
                                   1)
        self.surface.set_clip(None)

    def build_cli_bg(self):
        """Sfondo verde-fosforo per l'area CLI Tools, calcolato una
        volta sola: griglia sottile + scanline, coerente con
        l'identita' 'terminale retro, mondo a parte'."""
        bg = pygame.Surface((W, H))
        bg.fill((3, 8, 4))
        for gx in range(0, W, 34):
            pygame.draw.line(bg, (9, 24, 12), (gx, 0), (gx, H), 1)
        for gy in range(0, H, 34):
            pygame.draw.line(bg, (9, 24, 12), (0, gy), (W, gy), 1)
        for sy in range(0, H, 3):
            pygame.draw.line(bg, (2, 6, 3), (0, sy), (W, sy), 1)
        self.cli_bg_img = bg

    def cli_backdrop(self):
        t = time.time()
        dx = int((t * 7) % W)
        dy = int((t * 4) % H)
        for ox in (-dx, W - dx):
            for oy in (dy, dy - H):
                self.surface.blit(self.cli_bg_img, (ox, oy))
        gg = 22
        gang = t * 1.0
        for k in range(8):
            a = gang + k * math.pi / 4
            x1 = gg + int(10 * math.cos(a))
            y1 = H - gg + int(10 * math.sin(a))
            x2 = gg + int(14 * math.cos(a))
            y2 = H - gg + int(14 * math.sin(a))
            pygame.draw.line(self.surface, self.cli_accent_dim, (x1, y1), (x2, y2), 2)

    def build_style(self):
        """Precalcola sfondo e overlay: costano una volta sola, non a frame.
        Megastruttura alla BLAME!: griglia ortogonale (MAI diagonale --
        e' quello che creava lo stacco quando lo sfondo scorre, una
        linea inclinata non si richiude mai su se stessa ai bordi),
        finestre, piattaforme, tubature, un vano ascensore, il tutto
        con rifinitura cel-shading: bordi netti chiari/scuri, mai
        sfumature morbide. Overlay: scanline + vignettatura + grana."""
        rnd = random.Random(0xB1A)          # fisso: la struttura non balla
        bg = pygame.Surface((W, H))
        bg.fill(BG)
        # griglia ortogonale della megastruttura: SOLO orizzontale e
        # verticale, mai diagonale -- si richiude sempre su se stessa
        # ai bordi, qualunque offset di scorrimento venga applicato
        for gx in range(0, W, 40):
            pygame.draw.line(bg, LINE, (gx, 0), (gx, H), 1)
        for gy in range(0, H, 40):
            pygame.draw.line(bg, LINE, (0, gy), (W, gy), 1)
        # condotti principali (doppia linea = tubo), posizioni fisse
        for gy in (118, 296, 430):
            pygame.draw.line(bg, LINE, (0, gy), (W, gy), 2)
            pygame.draw.line(bg, INK, (0, gy + 2), (W, gy + 2), 1)
        sec = theme_secondary(self.accent)
        # piattaforme: lastre orizzontali sporgenti, con rifinitura
        # cel-shading -- riga chiara sopra, riga scura sotto, mai una
        # sfumatura morbida
        for _ in range(4):
            rx = rnd.randrange(0, W - 140)
            ry = rnd.randrange(52, H - 90)
            rw = rnd.randrange(100, 220)
            rh = rnd.randrange(14, 22)
            pygame.draw.rect(bg, INK, (rx, ry, rw, rh))
            pygame.draw.line(bg, STEEL_HI, (rx, ry), (rx + rw, ry), 1)
            pygame.draw.line(bg, (0, 0, 0), (rx, ry + rh),
                             (rx + rw, ry + rh), 1)
            pygame.draw.rect(bg, LINE, (rx, ry, rw, rh), 1)
        # lastre scure verticali, come pannellature -- stessa cura
        for _ in range(4):
            rx = rnd.randrange(0, W - 60)
            ry = rnd.randrange(40, H - 160)
            rw = rnd.randrange(30, 60)
            rh = rnd.randrange(90, 160)
            pygame.draw.rect(bg, INK, (rx, ry, rw, rh))
            pygame.draw.line(bg, STEEL_HI, (rx, ry), (rx, ry + rh), 1)
            pygame.draw.line(bg, (0, 0, 0), (rx + rw, ry),
                             (rx + rw, ry + rh), 1)
        # finestre sparse: lastra scura, alcune "accese" con l'accento
        # del tema, altre spente -- una citta' megastruttura vive cosi'
        for _ in range(14):
            wx = rnd.randrange(10, W - 20)
            wy = rnd.randrange(40, H - 30)
            ww_, wh_ = 8, 10
            lit = rnd.random() < 0.3
            pygame.draw.rect(bg, sec if lit else LINE,
                             (wx, wy, ww_, wh_), 0 if lit else 1)
        # vano ascensore: colonna con pioli, ancorata a un lato
        eshx = W - 26
        pygame.draw.line(bg, LINE, (eshx, 20), (eshx, H - 20), 1)
        pygame.draw.line(bg, LINE, (eshx + 14, 20), (eshx + 14, H - 20), 1)
        for ey in range(24, H - 20, 20):
            pygame.draw.line(bg, LINE, (eshx, ey), (eshx + 14, ey), 1)
        # sporco di china: puntinato rado
        for _ in range(360):
            x = rnd.randrange(W)
            y = rnd.randrange(H)
            bg.set_at((x, y), INK if rnd.random() < 0.7 else LINE)
        # tacche hazard sul bordo destro
        for hy in range(60, H - 40, 26):
            pygame.draw.line(bg, self.accent, (W - 4, hy), (W - 1, hy + 7), 2)

        # cavo che pende tra due ancoraggi (catenaria approssimata)
        cx1, cy1, cx2, cy2, sag = 40, 60, 260, 60, 34
        pts = []
        for i in range(13):
            t = i / 12.0
            x = cx1 + (cx2 - cx1) * t
            y = cy1 + (cy2 - cy1) * t + sag * math.sin(math.pi * t)
            pts.append((x, y))
        pygame.draw.lines(bg, sec, False, pts, 2)
        for ax, ay in ((cx1, cy1), (cx2, cy2)):
            pygame.draw.circle(bg, sec, (ax, ay), 3)

        # ingranaggio in un angolo, ancorato in basso a sinistra
        gx0, gy0, gr = 34, H - 46, 16
        gpts = []
        for i in range(16):
            ang = i * math.pi / 8
            rr = gr if i % 2 == 0 else gr - 4
            gpts.append((gx0 + rr * math.cos(ang), gy0 + rr * math.sin(ang)))
        pygame.draw.polygon(bg, sec, gpts, 2)
        pygame.draw.circle(bg, sec, (gx0, gy0), 5, 1)

        # mini monitor appeso, in alto a destra della zona centrale
        mx, my, mw, mh = W - 110, 70, 52, 38
        pygame.draw.rect(bg, INK, (mx, my, mw, mh))
        pygame.draw.rect(bg, sec, (mx, my, mw, mh), 1)
        for lx in range(mx + 6, mx + mw - 4, 9):
            pygame.draw.line(bg, sec, (lx, my + 5), (lx, my + mh - 5), 1)
        pygame.draw.line(bg, sec, (mx + mw // 2, my + mh),
                         (mx + mw // 2, my + mh + 8), 1)

        # insegna/targa hazard, appesa in basso a destra
        sx, sy = W - 56, H - 70
        pygame.draw.polygon(bg, INK, [(sx, sy - 12), (sx + 12, sy),
                                      (sx, sy + 12), (sx - 12, sy)])
        pygame.draw.polygon(bg, sec, [(sx, sy - 12), (sx + 12, sy),
                                      (sx, sy + 12), (sx - 12, sy)], 1)
        pygame.draw.line(bg, sec, (sx, sy - 5), (sx, sy + 3), 2)
        bg.set_at((sx, sy + 7), sec)

        self.bg_img = bg
        # overlay: scanline + vignetta + grana (una Surface, un blit a frame)
        fx = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(fx, (0, 0, 0, 26), (0, y), (W, y))
        steps, th = 7, 9
        for i in range(steps):
            a = int(88 * ((steps - i) / float(steps)) ** 2.4)
            pygame.draw.rect(fx, (0, 0, 0, a),
                             (i * th, i * th, W - 2 * i * th, H - 2 * i * th),
                             th)
        for _ in range(260):
            fx.set_at((rnd.randrange(W), rnd.randrange(H)),
                      (255, 255, 255, rnd.randrange(6, 16)))
        self.fx_img = fx
        # barra hazard della selezione: strisce diagonali accento/nero
        st = pygame.Surface((6, 24))
        st.fill(INK)
        for d in range(-24, 24, 8):
            pygame.draw.line(st, self.accent, (d, 24), (d + 24, 0), 3)
        self.stripe_img = st
        self.sel_bg = sel_tint(self.accent)

    def build_intro_jingle(self):
        """Il colpo sonoro sincronizzato con l'impatto del logo nella
        sigla d'avvio: una rincorsa che sale, poi un accordo pieno
        (due toni impilati + un pizzico di rumore per il punch) esatto
        nell'istante in cui compaiono anelli e scintille."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 256)
        except pygame.error:
            return None
        sr = 22050

        def synth(events):
            dur = max(t0 + d for t0, f0, f1, d, vol, noise in events)
            n = int(sr * dur)
            buf = [0.0] * n
            rnd = random.Random(11)
            for t0, f0, f1, d, vol, noise in events:
                i0, nn = int(t0 * sr), int(d * sr)
                ph = 0.0
                for i in range(nn):
                    if i0 + i >= n:
                        break
                    tt = i / float(nn)
                    ph += 2 * math.pi * (f0 + (f1 - f0) * tt) / sr
                    v = math.sin(ph)
                    if noise:
                        v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
                    env = min(1.0, i / 30.0) * (1 - tt) ** 1.8
                    buf[i0 + i] += vol * env * v
            raw = bytearray()
            for v in buf:
                s = max(-1.0, min(1.0, v))
                raw += int(s * 32767).to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(raw))
        try:
            return synth([
                (0.00, 500, 1400, 0.16, 0.22, 0.05),   # rincorsa che sale
                (0.16, 220, 210, 0.35, 0.34, 0.10),     # impatto: fondamentale
                (0.16, 440, 415, 0.30, 0.22, 0.10),     # impatto: ottava
                (0.16, 60, 55, 0.40, 0.30, 0.35),       # punch grave
            ])
        except pygame.error:
            return None

    def build_sfx(self):
        """Suoni UI sintetizzati al volo: blip di apertura, ritorno,
        movimento e scatto d'aggancio. Zero asset; se l'audio manca,
        silenzio e pace."""
        try:
            pygame.mixer.init(22050, -16, 1, 256)
        except pygame.error:
            return None

        def tone(f0, f1, ms, vol=0.30, noise=0.0):
            n = int(22050 * ms / 1000)
            buf = bytearray()
            ph = 0.0
            rnd = random.Random(3)
            for i in range(n):
                t = i / float(n)
                ph += 2 * math.pi * (f0 + (f1 - f0) * t) / 22050
                v = math.sin(ph)
                if noise:
                    v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
                env = min(1.0, i / 40.0) * (1 - t) ** 1.6
                smp = int(vol * env * 32767 * v)
                buf += smp.to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(buf))
        try:
            return {"open": tone(420, 980, 70),
                    "back": tone(760, 320, 60),
                    "move": tone(1240, 1240, 16, 0.16),
                    "snap": tone(190, 130, 45, 0.34, 0.55),
                    "off": tone(320, 38, 480, 0.42, 0.35),
                    "nexus": tone(560, 1520, 110, 0.24, 0.10)}
        except pygame.error:
            return None

    def play(self, name):
        if self.sfx and self.cfg.get("sfx", True):
            try:
                self.sfx[name].play()
            except (KeyError, pygame.error):
                pass

    def push(self, state, color=None):
        """Apre uno stato come una finestra di un OS cyberpunk: blip,
        cattura del frame corrente, esplosione dal rettangolo selezionato."""
        self.play("open")
        self.prev_frame = self.surface.copy()
        r = self.last_sel_rect or (W // 2 - 60, H // 2 - 40, 120, 80)
        self.trans = ({"t0": time.time(), "rect": r, "color": color}
                      if self.cfg.get("anim", True) else None)
        self.stack.append(state)

    def pop_state(self):
        if len(self.stack) <= 1:
            return
        self.play("back")
        self.prev_frame = self.surface.copy()
        self.trans = ({"t0": time.time(), "rect": (0, 42, 52, H - 70),
                       "color": None}
                      if self.cfg.get("anim", True) else None)
        self.stack.pop()

    def switch(self, x, y, on, w=64, h=30):
        tr = OK_G if on else (70, 74, 82)
        pygame.draw.rect(self.surface, tr, (x, y, w, h),
                         border_radius=h // 2)
        pygame.draw.rect(self.surface, LINE, (x, y, w, h), 2,
                         border_radius=h // 2)
        kx = x + (w - h + 3) if on else x + 3
        pygame.draw.circle(self.surface, FG,
                           (kx + (h - 6) // 2, y + h // 2),
                           (h - 8) // 2)

    def render_prev_dim(self):
        if self.prev_frame:
            self.surface.blit(self.prev_frame, (0, 0))
        veil = pygame.Surface((W, H))
        veil.fill((0, 0, 0))
        veil.set_alpha(150)
        self.surface.blit(veil, (0, 0))

    def interference(self):
        """Interferenze orizzontali leggere: due bande in scorrimento con
        micro-shift, uno spike raro. Non sono le scanline: e' il tremolio
        del segnale. Spegnibile dalle opzioni."""
        if not self.cfg.get("fx", True):
            return
        t = time.time()
        for spd, ph, amp, hh in ((26.0, 0, 2, 2), (9.0, 170, 1, 3)):
            y = int((t * spd + ph) % (H + 50)) - 25
            if 0 <= y < H - hh:
                band = self.surface.subsurface((0, y, W, hh)).copy()
                self.surface.blit(band,
                                  (amp if int(t * 7) % 2 else -amp, y))
        if int(t * 10) % 47 == 0:
            base = int((t * 26) % (H - 8))
            for k in range(3):
                y = (base + k * 57) % (H - 3)
                band = self.surface.subsurface((0, y, W, 2)).copy()
                self.surface.blit(band, ((-3, 3)[k % 2], y))

    def crt_off(self):
        """Spegnimento da vecchia TV: tremolio che si propaga, il quadro
        collassa in una riga luminosa, la riga in un punto, il punto muore.
        Poi si torna a muOS."""
        self.play("off")
        frame = self.surface.copy()
        rnd = random.Random()
        t0 = time.time()
        while time.time() - t0 < 0.34:          # interferenza crescente
            k = (time.time() - t0) / 0.34
            self.surface.blit(frame, (0, 0))
            for _ in range(int(4 + 26 * k)):
                y = rnd.randrange(H - 4)
                band = frame.subsurface((0, y, W, rnd.randrange(2, 5)))
                self.surface.blit(band, (rnd.randrange(-int(3 + 14 * k),
                                                       int(4 + 14 * k)), y))
            if rnd.random() < k * 0.7:
                veil = pygame.Surface((W, H))
                veil.fill((255, 255, 255))
                veil.set_alpha(rnd.randrange(10, 40))
                self.surface.blit(veil, (0, 0))
            pygame.display.flip()
            self.clock.tick(45)
        for f in range(12):                     # collasso verticale
            k = f / 11.0
            hh = max(3, int(H * (1 - k) ** 2.2))
            img = pygame.transform.scale(frame, (W, hh))
            self.surface.fill((0, 0, 0))
            self.surface.blit(img, (0, (H - hh) // 2))
            br = int(120 + 135 * k)
            pygame.draw.rect(self.surface, (br, br, br),
                             (0, H // 2 - 1, W, 3))
            pygame.display.flip()
            self.clock.tick(45)
        for f in range(10):                     # la riga muore in un punto
            k = f / 9.0
            ww = max(4, int(W * (1 - k) ** 1.7))
            self.surface.fill((0, 0, 0))
            c = int(255 * (1 - k * 0.55))
            pygame.draw.rect(self.surface, (c, c, c),
                             ((W - ww) // 2, H // 2 - 1, ww, 3))
            pygame.display.flip()
            self.clock.tick(45)
        for f in range(7):
            self.surface.fill((0, 0, 0))
            c = int(200 * (1 - f / 6.0))
            pygame.draw.circle(self.surface, (c, c, c), (W // 2, H // 2), 2)
            pygame.display.flip()
            self.clock.tick(30)
        self.exit_code = 0
        self.running = False

    def ensure_status(self):
        if not getattr(self, "_scanned", False):
            self.run_busy(self.t("mounting"), self.scan_status)
            self._scanned = True

    def hub_action(self, hub, key, kind):
        if kind == "cycle":
            ck, vals = CYCLES[key]
            cur = self.cfg.get(ck, vals[0])
            self.cfg[ck] = vals[(vals.index(cur) + 1) % len(vals)
                                if cur in vals else 0]
            save_cfg(self.cfg)
            return
        if hub == "forge":
            if key == "vdupdate":
                self.vdupd_result = self.run_busy(
                    self.t("checking"), self.update_check)
                self.push("vdupdate")
            elif key == "clitools":
                self.run_busy(self.t("checking"), self.scan_status)
                self.clihub_sel = 0
                self.push("clihub")
            else:
                self.comp_action({"installer": "install", "autostart":
                                  "autostart", "update": "update"}[key])
        elif hub == "workshop":
            if key == "stats":
                self.info_lines = self.run_busy(self.t("checking"),
                                                self.void_stats) or []
                self.scroll = 0
                self.push("info")
            elif key == "diag":
                self.info_lines = self.run_busy(self.t("checking"),
                                                self.diag_lines) or []
                self.scroll = 0
                self.push("info")
            elif key == "monitor":
                self.mon = {"cpu": [], "ram": [], "net": [], "tmp": [],
                            "last": None, "t": 0}
                self.mon_tab = 0
                self.push("monitor")
            elif key == "storage":
                self.info_lines = self.run_busy(self.t("checking"),
                                                self.storage_lines) or []
                self.scroll = 0
                self.push("info")
            elif key == "boost":
                self.boost_sel = 0
                self.push("boostcfg")
            elif key == "clean":
                self.comp_action("clean")
            elif key == "logs":
                self.sel_log = 1
                self.logs = self.build_logs()
                self.push("logs")
            elif key == "backup":
                self.bak_sel = 0
                self.push("backup")
        elif hub == "uplink":
            if key == "map":
                self.push("map")
            elif key == "wifi":
                self.wm_sel = 0
                self.wm_nets = self.run_busy(self.t("wm_scan"),
                                             self.wm_scan) or []
                self.push("wifimgr")
            elif key == "bt":
                self.bt_sel = 0
                self.bt_devs = self.run_busy("bluetooth...",
                                             lambda:
                                             self.bt_list(False)) or []
                self.push("btmgr")
            elif key == "hotspot":
                self.push("hotmgr")
        elif hub == "toolbox":
            if key == "shell":
                self.comp_action("shell")
            elif key == "clockmain":
                self.push("clock")
            elif key == "calc":
                self.calc_expr = ""
                self.calc_sel = 0
                self.push("calc")
            elif key == "cal":
                self.evs = self.cal_load()
                lt = time.localtime()
                self.cal_cur = [lt.tm_year, lt.tm_mon, lt.tm_mday]
                self.cal_view = "month"
                self.ev_sel = 0
                self.push("cal")
            elif key == "notes":
                self.notes = self.notes_refresh()
                self.note_sel = 0
                self.push("notes")
            elif key == "rss":
                self.rss_sel = 0
                self.push("rss")
                if not self.rss_items and self.rss_enabled_feeds():
                    self.run_busy(self.t("rss_upd"), self.rss_refresh)
            elif key == "weather":
                self.wx_sel = 0
                self.push("weather")
                cities = self.cfg.get("weather_cities") or []
                if cities and not self.wx_data:
                    self.run_busy(self.t("wx_updating"),
                                  self.wx_refresh_all)
            elif key == "pyrepl":
                self.py_ns = {}
                self.py_out = ["Python %s // host muOS" %
                               sys.version.split()[0],
                               ">>> "]
                self.push("pyrepl")
            elif key == "fileman":
                self.fm_open()
            elif key == "ftp":
                self.ftp_prof_sel = 0
                self.push("ftpprof")
            elif key == "editor":
                self.fm_open()
            elif key == "sync":
                self.sync_open()
            elif key in TOOL_PKGS:
                self.tool_open(key)
            elif key == "tsgui":
                self.ts_open()
        elif hub == "infohub":
            if key == "about":
                self.info_lines = self.about_lines()
            elif key == "guide":
                self.info_lines = self.guide_lines()
            elif key == "manifesto":
                self.scroll = 0
                self.push("manifesto")
                return
            else:
                self.man_sel = 0
                self.push("manual")
                return
            self.scroll = 0
            self.push("info")

    def tool_open(self, key):
        label, pkgs = TOOL_PKGS[key]
        self.ensure_status()
        inst = bool(self.status.get(label.split(" ")[0])) or             bool(self.status.get({"fileman": "File manager",
                                  "mc": "Midnight Commander",
                                  "ftp": "FileZilla",
                                  "editor": "Blocco note",
                                  "sync": "Syncthing"}.get(key, "")))
        if inst:
            body = self.t("opens_desk")
            if key == "mc":
                body = ("nel terminale: scrivi mc" if self.lang == "it"
                        else "in the terminal: type mc")
            if key == "sync":
                body += "  ·  http://localhost:8384"
            self.info_lines = self.stub_lines(label, [body])
            self.scroll = 0
            self.push("info")
        else:
            os.makedirs(DATA, exist_ok=True)
            with open(os.path.join(DATA, ".install_pkg"), "w") as f:
                f.write("%s\n%s\n" % (label, pkgs))
            self.handoff(("INSTALLO %s..." if self.lang == "it"
                          else "INSTALLING %s...") % label.upper())
            self.exit_code = EXIT_PKG_INSTALL
            self.running = False

    def launch_muos(self, app):
        os.makedirs(DATA, exist_ok=True)
        gov = (self.cfg.get("mapp_gov") or {}).get(app["name"], "default")
        with open(os.path.join(DATA, ".muos_gov"), "w") as f:
            f.write(gov + "\n")
        with open(os.path.join(DATA, ".muos_app"), "w") as f:
            f.write("%s\n%s\n" % (app["dir"], app["name"]))
        self.handoff(("AVVIO %s..." if self.lang == "it"
                      else "LAUNCHING %s...") % app["name"].upper())
        self.exit_code = EXIT_MUOS_APP
        self.running = False

    # ================== VOID FTP: client nativo ==================
    def ftp_connect(self, prof):
        it = (self.lang == "it")

        def job():
            c = self._ftp_factory()
            c.connect(prof["host"], int(prof.get("port", 21)),
                      timeout=10)
            c.login(prof.get("user") or "anonymous",
                    prof.get("pass", ""))
            try:
                c.set_pasv(True)
            except Exception:
                pass
            return c
        try:
            self.ftpc = self.run_busy(
                ("connetto a %s..." if it else "connecting to %s...")
                % prof["host"], job)
        except Exception as e:
            self.ftpc = None
        if not self.ftpc:
            self.info_lines = self.stub_lines(
                "VOID FTP", [("connessione fallita a %s" if it else
                              "connection failed to %s") % prof["host"]])
            self.scroll = 0
            self.push("info")
            return
        self.ftp_cwd = "/"
        self.ftp_marked.clear()
        self.ftp_sel = 0
        self.run_busy("...", self.ftp_refresh)
        self.push("ftpls")

    def ftp_refresh(self):
        items = []
        try:
            for name, facts in self.ftpc.mlsd(self.ftp_cwd):
                if name in (".", ".."):
                    continue
                items.append((name, facts.get("type") == "dir",
                              int(facts.get("size", 0) or 0)))
        except Exception:
            lines = []
            try:
                self.ftpc.retrlines("LIST " + self.ftp_cwd,
                                    lines.append)
            except Exception:
                lines = []
            for ln in lines:
                f = ln.split(None, 8)
                if len(f) < 9:
                    continue
                items.append((f[8], ln[:1] == "d",
                              int(f[4]) if f[4].isdigit() else 0))
        items.sort(key=lambda a: (not a[1], a[0].lower()))
        self.ftp_items = [("..", True, 0)] + items
        self.ftp_sel = min(self.ftp_sel,
                           max(0, len(self.ftp_items) - 1))

    def ftp_join(self, name):
        base = self.ftp_cwd.rstrip("/")
        return (base + "/" + name) if base else "/" + name

    def ftp_download(self, names):
        it = (self.lang == "it")
        dest = self.fm_path if (self.fm_path and
                                os.path.isdir(self.fm_path)) else             os.path.join(DATA, "downloads")
        os.makedirs(dest, exist_ok=True)

        def job():
            got = 0
            for i, nm in enumerate(names):
                out = os.path.join(dest, nm)
                st = {"b": 0}

                def cb(chunk, _f=None):
                    fh.write(chunk)
                    st["b"] += len(chunk)
                    self.busy_label = "%s %d/%d: %s (%s)" % (
                        "scarico" if it else "downloading",
                        i + 1, len(names), nm[:18], human(st["b"]))
                try:
                    with open(out, "wb") as fh:
                        self.ftpc.retrbinary(
                            "RETR " + self.ftp_join(nm), cb)
                    got += 1
                except Exception:
                    try:
                        os.remove(out)
                    except OSError:
                        pass
            return dest if got else None
        d = self.run_busy("...", job)
        self.info_lines = self.stub_lines(
            "VOID FTP",
            [((("%d file in " % len(names)) + d) if d else
              ("scaricamento fallito" if it else "download failed"))])
        self.scroll = 0
        self.push("info")

    def ftp_upload(self, local):
        it = (self.lang == "it")
        nm = os.path.basename(local)

        def job():
            self.busy_label = ("carico %s..." if it
                               else "uploading %s...") % nm[:22]
            with open(local, "rb") as fh:
                self.ftpc.storbinary("STOR " + self.ftp_join(nm), fh)
            return True
        try:
            self.run_busy("...", job)
            self.ftp_refresh()
        except Exception:
            pass

    def ftp_new_profile(self):
        it = (self.lang == "it")
        prof = {}
        steps = [("NOME" if it else "NAME", "name", "NAS"),
                 ("HOST", "host", "192.168.1."),
                 ("PORTA" if it else "PORT", "port", "21"),
                 ("UTENTE" if it else "USER", "user", "anonymous"),
                 ("PASSWORD", "pass", "")]

        def ask(i):
            if i >= len(steps):
                if prof.get("host"):
                    self.cfg.setdefault("ftp_profiles", []).append(prof)
                    save_cfg(self.cfg)
                return
            title, key, init = steps[i]

            def done(v, i=i, key=key):
                prof[key] = v.strip()
                ask(i + 1)
            self.osk_open(title, init, done)
        ask(0)

    def ftp_menu_items(self):
        it = (self.lang == "it")
        n = len(self.ftp_marked)
        return [("dl", ("Scarica (%d)" if it else "Download (%d)")
                 % max(1, n)),
                ("ul", "Carica un file..." if it else "Upload a file..."),
                ("refresh", "Aggiorna" if it else "Refresh"),
                ("close", "Disconnetti" if it else "Disconnect")]

    def sync_open_refresh(self):
        if self.sync:
            os.environ.setdefault("VD_SYNC_URL", self.sync["url"])
            os.environ.setdefault("VD_SYNC_KEY", self.sync["key"])
        self.pop_state()
        self.sync_open()

    def ftp_close(self):
        try:
            if self.ftpc:
                self.ftpc.quit()
        except Exception:
            pass
        self.ftpc = None

    # ================== CALENDARIO ==================
    def cal_path(self):
        return os.path.join(DATA, "calendar.json")

    def cal_load(self):
        import json as _j
        try:
            evs = _j.load(open(self.cal_path()))
        except (OSError, ValueError):
            evs = []
        evs.sort(key=lambda e: (e["y"], e["mo"], e["d"],
                                e["h"], e["mi"]))
        return evs

    def cal_save(self):
        import json as _j
        os.makedirs(DATA, exist_ok=True)
        with open(self.cal_path(), "w") as f:
            _j.dump(self.evs, f)

    def cal_names(self):
        it = (self.lang == "it")
        mesi = (["GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO",
                 "GIUGNO", "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE",
                 "NOVEMBRE", "DICEMBRE"] if it else
                ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY",
                 "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER",
                 "NOVEMBER", "DECEMBER"])
        gg = (["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
              if it else
              ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
        gg_full = (["Lunedì", "Martedì", "Mercoledì", "Giovedì",
                    "Venerdì", "Sabato", "Domenica"] if it else
                   ["Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday"])
        return mesi, gg, gg_full

    def cal_shift(self, days):
        d = dtmod.date(*self.cal_cur) + dtmod.timedelta(days=days)
        self.cal_cur = [d.year, d.month, d.day]

    def cal_month_shift(self, dm):
        y, m, d = self.cal_cur
        m += dm
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        d = min(d, calmod.monthrange(y, m)[1])
        self.cal_cur = [y, m, d]

    def ev_on(self, y, m, d):
        return [e for e in self.evs
                if (e["y"], e["mo"], e["d"]) == (y, m, d)]

    def imp_label(self, i):
        it = (self.lang == "it")
        return (["bassa", "media", "ALTA"] if it
                else ["low", "medium", "HIGH"])[max(0, min(2, i))]

    def imp_color(self, i):
        return [FAINT, self.accent, NO_R][max(0, min(2, i))]

    # ================== NOTE ==================
    def notes_dir(self):
        d = os.path.join(DATA, "notes")
        os.makedirs(d, exist_ok=True)
        return d

    def notes_refresh(self):
        d = self.notes_dir()
        pins = set(self.cfg.get("note_pins", []))
        out = []
        try:
            for f in os.listdir(d):
                if f.endswith(".txt"):
                    p = os.path.join(d, f)
                    try:
                        txt = open(p, errors="ignore").read(240)
                    except OSError:
                        txt = ""
                    out.append({"p": p, "txt": txt or "(vuota)",
                                "mt": os.path.getmtime(p),
                                "pin": f in pins})
        except OSError:
            pass
        out.sort(key=lambda a: (not a["pin"], -a["mt"]))
        return out

    def note_pin_toggle(self, path):
        pins = self.cfg.setdefault("note_pins", [])
        b = os.path.basename(path)
        if b in pins:
            pins.remove(b)
        else:
            pins.append(b)
        save_cfg(self.cfg)
        self.notes = self.notes_refresh()

    def note_card_h(self, txt):
        n = len(txt)
        return 88 if n < 70 else (126 if n < 160 else 164)

    def note_layout(self):
        """Bacheca a 3 colonne: la card va nella colonna piu' corta.
        La prima card e' sempre [+ nuova]."""
        colw = (W - 40) // 3
        cols = [46, 46, 46]
        rects = []
        r0 = pygame.Rect(10, 46, colw, 72)      # + nuova
        rects.append(r0)
        cols[0] = r0.bottom + 8
        for nt in self.notes:
            h = self.note_card_h(nt["txt"])
            c = cols.index(min(cols))
            rects.append(pygame.Rect(10 + c * (colw + 10), cols[c],
                                     colw, h))
            cols[c] += h + 8
        return rects

    def note_wrap(self, txt, width_px, font, maxlines):
        out = []
        for raw in txt.split("\n"):
            ln = ""
            for w2 in raw.split(" "):
                t2 = (ln + " " + w2).strip()
                if font.size(t2)[0] <= width_px:
                    ln = t2
                else:
                    out.append(ln)
                    ln = w2
                if len(out) >= maxlines:
                    return out
            out.append(ln)
            if len(out) >= maxlines:
                return out
        return out

    # ================== RSS READER ==================
    def rss_custom_path(self):
        return os.path.join(DATA, "rss_custom.json")

    def rss_custom_load(self):
        import json as _j
        try:
            raw = _j.load(open(self.rss_custom_path()))
        except (OSError, ValueError):
            return []
        out = []
        for f in raw if isinstance(raw, list) else []:
            if isinstance(f, dict) and f.get("name") and f.get("url"):
                out.append((f["name"], f["url"], "xx", "general"))
        return out

    def rss_all_feeds(self):
        return RSS_FEEDS + self.rss_custom_load()

    def rss_enabled_feeds(self):
        en = self.cfg.get("rss_enabled")
        allf = self.rss_all_feeds()
        if en is None:                     # primo avvio: tutto attivo
            return allf
        enset = set(en)
        return [f for f in allf if f[0] in enset]

    def rss_is_enabled(self, name):
        en = self.cfg.get("rss_enabled")
        if en is None:
            return True
        return name in en

    def rss_sel_rows(self):
        """Righe hdr+feed raggruppate per lingua (ENG/ITA), poi
        GENERALE per i feed che l'utente ha aggiunto da file."""
        rows = []
        eng = [f for f in RSS_FEEDS if f[2] == "en"]
        ita = [f for f in RSS_FEEDS if f[2] == "it"]
        gen = self.rss_custom_load()
        if eng:
            rows.append(("hdr", self.t("rss_eng")))
            rows += [("feed", f) for f in eng]
        if ita:
            rows.append(("hdr", self.t("rss_ita")))
            rows += [("feed", f) for f in ita]
        if gen:
            rows.append(("hdr", self.t("rss_gen")))
            rows += [("feed", f) for f in gen]
        return rows

    def rss_remove_custom(self, name):
        """Rimuove per sempre un feed personalizzato da rss_custom.json
        (solo quelli 'generale': i built-in si possono solo disattivare,
        non esiste un file da cui cancellarli)."""
        import json as _j
        try:
            raw = _j.load(open(self.rss_custom_path()))
        except (OSError, ValueError):
            return False
        raw = [f for f in raw if isinstance(f, dict) and
               f.get("name") != name]
        try:
            _j.dump(raw, open(self.rss_custom_path(), "w"))
        except OSError:
            return False
        return True

    def rss_disable(self, name):
        en = self.cfg.get("rss_enabled")
        if en is None:
            en = [f[0] for f in self.rss_all_feeds()]
        en = [n for n in en if n != name]
        self.cfg["rss_enabled"] = en
        save_cfg(self.cfg)

    def rss_toggle(self, name):
        allf = self.rss_all_feeds()
        cur = self.cfg.get("rss_enabled")
        if cur is None:
            cur = [f[0] for f in allf]
        cur = list(cur)
        if name in cur:
            cur.remove(name)
        else:
            cur.append(name)
        self.cfg["rss_enabled"] = cur
        save_cfg(self.cfg)

    def rss_parse(self, xml_bytes):
        """RSS2 e Atom, stdlib puro. Ogni voce: titolo, link, quando."""
        import xml.etree.ElementTree as ET
        import email.utils as eut
        root = ET.fromstring(xml_bytes)
        items = []
        tag = root.tag.lower()
        if tag.endswith("feed"):                          # Atom
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entries = root.findall("a:entry", ns) or \
                root.findall("entry")
            for e in entries[:20]:
                t = (e.findtext("a:title", default="", namespaces=ns)
                     or e.findtext("title", default="")).strip()
                link = ""
                for l_ in (e.findall("a:link", ns) or
                          e.findall("link")):
                    href = l_.get("href")
                    if href and (l_.get("rel") in (None, "alternate")):
                        link = href
                        break
                when = (e.findtext("a:updated", default="",
                                   namespaces=ns) or
                        e.findtext("updated", default="") or
                        e.findtext("a:published", default="",
                                   namespaces=ns))
                ts = 0.0
                try:
                    ts = time.mktime(time.strptime(
                        when[:19], "%Y-%m-%dT%H:%M:%S"))
                except (ValueError, TypeError):
                    pass
                if t:
                    items.append({"title": t, "link": link, "ts": ts})
        else:                                              # RSS 2.0
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                when = it.findtext("pubDate") or ""
                ts = 0.0
                try:
                    ts = eut.mktime_tz(eut.parsedate_tz(when))
                except (TypeError, ValueError):
                    pass
                if t:
                    items.append({"title": t, "link": link, "ts": ts})
        return items

    def rss_fetch_one(self, feed):
        import urllib.request
        name, url, lang, cat = feed
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "VoidDesk/1.0 RSS Reader"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read(600000)
            items = self.rss_parse(data)
            return (name, lang, cat, items, None)
        except Exception as e:
            return (name, lang, cat, [], str(e)[:70])

    def rss_refresh(self):
        from concurrent.futures import ThreadPoolExecutor
        feeds = self.rss_enabled_feeds()
        all_items = []
        errors = {}
        if not feeds:
            self.rss_items = []
            self.rss_errors = {}
            return
        with ThreadPoolExecutor(max_workers=min(6, len(feeds))) as ex:
            for name, lang, cat, items, err in ex.map(
                    self.rss_fetch_one, feeds):
                icon, col = RSS_CATS.get(cat, RSS_CATS["general"])
                if err:
                    errors[name] = err
                for it in items:
                    all_items.append({
                        "site": name, "title": it["title"],
                        "link": it["link"], "ts": it["ts"],
                        "cat": cat, "icon": icon, "col": col})
        all_items.sort(key=lambda a: -a["ts"])
        self.rss_items = all_items[:120]
        self.rss_errors = errors

    def rss_ago(self, ts):
        it = (self.lang == "it")
        if not ts:
            return ""
        d = max(0, time.time() - ts)
        if d < 3600:
            m = int(d // 60)
            return ("%dm fa" % m) if it else ("%dm ago" % m)
        if d < 86400:
            h = int(d // 3600)
            return ("%dh fa" % h) if it else ("%dh ago" % h)
        g = int(d // 86400)
        return ("%dg fa" % g) if it else ("%dd ago" % g)

    # ================== GESTORE WIFI (wpa_cli) ==================
    def wm_cli(self, *args, timeout=8):
        return subprocess.run(WPA + list(args), capture_output=True,
                              text=True, timeout=timeout).stdout

    def wm_radio_on(self):
        base = os.environ.get("VD_NET_SYS", "/sys/class/net")
        try:
            return int(open(os.path.join(base, "wlan0", "flags")
                            ).read().strip(), 16) & 1 == 1
        except (OSError, ValueError):
            return True

    def wm_radio_toggle(self):
        ipc = os.environ.get("VD_IPCMD", "ip").split()
        act = "down" if self.wm_radio_on() else "up"
        subprocess.run(ipc + ["link", "set", "wlan0", act],
                       capture_output=True, timeout=8)

    def wm_info_lines(self):
        it = (self.lang == "it")
        base = os.environ.get("VD_NET_SYS", "/sys/class/net")
        st = self.wm_status()
        L = [("sec", "wifi", "WIFI // INFO")]
        L.append(("kv", "INTERFACCIA" if it else "INTERFACE",
                  "wlan0", DIM))
        try:
            L.append(("kv", "MAC", open(os.path.join(
                base, "wlan0", "address")).read().strip(), FG))
        except OSError:
            pass
        ron = self.wm_radio_on()
        L.append(("kv", "RADIO", "on" if ron else "off",
                  OK_G if ron else NO_R))
        for k, lbl in (("ssid", "SSID"), ("bssid", "BSSID"),
                       ("freq", "FREQ"), ("ip_address", "IP")):
            if st.get(k):
                L.append(("kv", lbl, st[k] +
                          (" MHz" if k == "freq" else ""),
                          OK_G if k == "ssid" else FG
                          if k == "ip_address" else DIM))
        try:
            for ln in open("/proc/net/wireless").readlines()[2:]:
                if ln.strip().startswith("wlan0"):
                    L.append(("kv", "SEGNALE" if it else "SIGNAL",
                              ln.split()[3].rstrip(".") + " dBm",
                              DIM))
        except OSError:
            pass
        try:
            rx = int(open(os.path.join(base, "wlan0", "statistics",
                                       "rx_bytes")).read())
            tx = int(open(os.path.join(base, "wlan0", "statistics",
                                       "tx_bytes")).read())
            L.append(("kv", "RX / TX", "%s / %s" %
                      (human(rx), human(tx)), DIM))
        except (OSError, ValueError):
            pass
        try:
            out = subprocess.run(["ip", "route"],
                                 capture_output=True, text=True,
                                 timeout=3).stdout
            m = re.search(r"default via ([0-9.]+)", out)
            if m:
                L.append(("kv", "GATEWAY", m.group(1), DIM))
        except Exception:
            pass
        return L

    def wm_iw_link(self):
        """SSID/BSSID/segnale dalla connessione attiva via iw: e' la
        via seguita dal WiFi Manager di amosjerbi ('iw funziona meglio
        di iwconfig su questo hardware') e funziona anche quando
        wpa_cli non riesce ad agganciare il control socket di
        wpa_supplicant (il sintomo esatto: menu che dice 'nessuna
        connessione' mentre l'indicatore di sistema mostra il WiFi
        attivo)."""
        try:
            out = subprocess.run(["iw", "dev", WM_IFACE, "link"],
                                 capture_output=True, text=True,
                                 timeout=5).stdout
        except Exception:
            return {}
        if not out or "Not connected" in out:
            return {}
        d = {}
        m = re.search(r"Connected to ([0-9a-fA-F:]{17})", out)
        if m:
            d["bssid"] = m.group(1)
        m = re.search(r"SSID:\s*(.+)", out)
        if m:
            d["ssid"] = m.group(1).strip()
        m = re.search(r"freq:\s*(\d+)", out)
        if m:
            d["freq"] = m.group(1)
        m = re.search(r"signal:\s*(-?\d+)", out)
        if m:
            d["signal"] = m.group(1)
        if d.get("ssid"):
            d["wpa_state"] = "COMPLETED"
        return d

    def wm_ip(self):
        try:
            out = subprocess.run(["ip", "-4", "addr", "show", WM_IFACE],
                                 capture_output=True, text=True,
                                 timeout=3).stdout
            m = re.search(r"inet ([0-9.]+)", out)
            return m.group(1) if m else ""
        except Exception:
            return ""

    def wm_status(self):
        """Fonde wpa_cli (quando risponde) con iw link (sempre
        affidabile su questo hardware) cosi' lo stato mostrato riflette
        la connessione vera anche se una delle due vie e' muta."""
        st = {}
        try:
            for ln in self.wm_cli("status").splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    st[k] = v
        except Exception:
            pass
        if st.get("wpa_state") != "COMPLETED" or not st.get("ssid"):
            iwd = self.wm_iw_link()
            if iwd:
                st.update({k: v for k, v in iwd.items()
                          if not st.get(k)})
        if not st.get("ip_address"):
            ip = self.wm_ip()
            if ip:
                st["ip_address"] = ip
        return st

    def wm_saved(self):
        out = {}
        try:
            for ln in self.wm_cli("list_networks").splitlines()[1:]:
                f = ln.split("\t")
                if len(f) >= 2:
                    out[f[1]] = f[0]
        except Exception:
            pass
        return out

    def wm_scan_iw(self):
        """Scansione diretta via nl80211 (iw), senza passare dal
        control socket di wpa_supplicant: quando wpa_cli non risponde,
        questa e' l'unica via che resta per vedere le reti intorno."""
        nets = {}
        try:
            subprocess.run(["ip", "link", "set", WM_IFACE, "up"],
                           capture_output=True, timeout=5)
            out = subprocess.run(["iw", "dev", WM_IFACE, "scan"],
                                 capture_output=True, text=True,
                                 timeout=20).stdout
        except Exception:
            return nets
        cur_sig = -90
        for ln in out.splitlines():
            ls = ln.strip()
            if ls.startswith("BSS "):
                cur_sig = -90
            m = re.search(r"signal:\s*(-?\d+(?:\.\d+)?)\s*dBm", ls)
            if m:
                cur_sig = int(float(m.group(1)))
            m = re.match(r"SSID:\s*(.*)", ls)
            if m and m.group(1):
                ssid = m.group(1)
                sec = "capabilities: WPA" in out or True
                if ssid not in nets or cur_sig > nets[ssid][0]:
                    nets[ssid] = (cur_sig, True)
        return nets

    def wm_scan(self):
        nets = {}
        try:
            self.wm_cli("scan")
            time.sleep(2.5)
            for ln in self.wm_cli("scan_results").splitlines()[1:]:
                f = ln.split("\t")
                if len(f) >= 5 and f[4]:
                    sig = int(f[2]) if f[2].lstrip("-").isdigit() else -90
                    if f[4] not in nets or sig > nets[f[4]][0]:
                        nets[f[4]] = (sig, "WPA" in f[3] or
                                      "RSN" in f[3])
        except Exception:
            pass
        if not nets:
            nets = self.wm_scan_iw()
        try:
            saved = self.wm_saved()
            cur = self.wm_status().get("ssid", "")
            out = [{"ssid": k, "sig": v[0], "sec": v[1],
                    "saved": k in saved, "id": saved.get(k),
                    "cur": k == cur}
                   for k, v in nets.items()]
            for k, nid in saved.items():
                if k not in nets:      # salvata ma fuori portata
                    out.append({"ssid": k, "sig": -95, "sec": True,
                                "saved": True, "id": nid,
                                "cur": False})
            out.sort(key=lambda n: (-n["cur"], -n["saved"], -n["sig"]))
            return out
        except Exception:
            return [{"ssid": k, "sig": v[0], "sec": v[1],
                    "saved": False, "id": None, "cur": False}
                    for k, v in nets.items()]

    def wm_bounce_connect(self, ssid, psk):
        """Fallback quando wpa_cli non parla col demone: la ricetta del
        WiFi Manager di amosjerbi per questo hardware. Riscrive
        wpa_supplicant.conf dando priorita' massima alla rete voluta,
        killa e rilancia wpa_supplicant in foreground-background (-B),
        poi verifica via iw. La configurazione originale viene sempre
        ripristinata, connessione riuscita o no."""
        path = SYS_WPA_CONF
        try:
            orig = open(path).read() if os.path.exists(path) else ""
        except OSError:
            orig = ""
        blocks = re.findall(r"network=\{[^}]*\}", orig, re.DOTALL)
        prios = [int(m.group(1)) for b in blocks
                 for m in [re.search(r"priority=(\d+)", b)] if m]
        top = (max(prios) if prios else 0) + 1
        psk_line = ('psk="%s"' % psk) if psk else "key_mgmt=NONE"
        lines = ["", "network={", '    ssid="%s"' % ssid,
                 "    scan_ssid=1", "    " + psk_line,
                 "    priority=%d" % top, "}", ""]
        block = "\n".join(lines)
        try:
            with open(path, "w") as f:
                f.write(orig + block)
            subprocess.run(["killall", "wpa_supplicant"],
                           capture_output=True, timeout=5)
            time.sleep(1)
            subprocess.run(["wpa_supplicant", "-B", "-i", WM_IFACE,
                            "-c", path], capture_output=True,
                           timeout=10)
            time.sleep(5)
            subprocess.run(["udhcpc", "-i", WM_IFACE, "-n", "-q"],
                           capture_output=True, timeout=12)
        except Exception:
            pass
        ok = self.wm_iw_link().get("ssid") == ssid
        try:
            with open(path, "w") as f:
                f.write(orig)
        except OSError:
            pass
        return ok

    def wm_connect(self, net, psk=None):
        def job():
            nid = net.get("id")
            wpa_ok = True
            try:
                if nid is None:
                    r = self.wm_cli("add_network").strip()
                    nid = r.splitlines()[-1] if r else ""
                    if not nid.isdigit():
                        wpa_ok = False
                    else:
                        self.wm_cli("set_network", nid, "ssid",
                                    '"%s"' % net["ssid"])
                        if psk:
                            self.wm_cli("set_network", nid, "psk",
                                        '"%s"' % psk)
                        else:
                            self.wm_cli("set_network", nid, "key_mgmt",
                                        "NONE")
                if wpa_ok:
                    self.wm_cli("select_network", nid)
                    self.wm_cli("enable_network", nid)
                    self.wm_cli("save_config")
                    time.sleep(3)
            except Exception:
                wpa_ok = False
            st = self.wm_status()
            if wpa_ok and st.get("ssid") == net["ssid"]:
                return st
            # wpa_cli non ha funzionato o non ha portato alla rete
            # giusta: ripiego sulla ricetta amosjerbi (bounce diretto)
            if self.wm_bounce_connect(net["ssid"], psk):
                return self.wm_status()
            return st
        st = self.run_busy(("connetto a %s..." if self.lang == "it"
                            else "joining %s...") % net["ssid"], job)
        ok = (st or {}).get("ssid") == net["ssid"]
        self.info_lines = self.stub_lines(
            net["ssid"], ["%s  ·  %s" %
                          (("connessa" if ok else "non riuscita")
                           if self.lang == "it" else
                           ("connected" if ok else "failed"),
                           (st or {}).get("ip_address", ""))])
        self.scroll = 0
        self.push("info")

    # ================== GESTORE BLUETOOTH (bluetoothctl) ============
    def bt_run(self, *args, timeout=12):
        return subprocess.run(BTCTL + list(args), capture_output=True,
                              text=True, timeout=timeout).stdout

    def bt_connected(self, mac):
        try:
            out = self.bt_run("--", "info", mac, timeout=6)
            return "Connected: yes" in out
        except Exception:
            return False

    def bt_list(self, scan):
        if not self.bt_powered():
            return []
        try:
            if scan:
                subprocess.run(BTCTL + ["--timeout", "8", "scan", "on"],
                               capture_output=True, timeout=14)
            paired = set()
            out = []
            for cmd in (["devices", "Paired"], ["paired-devices"]):
                try:
                    for ln in self.bt_run("--", *cmd).splitlines():
                        f = ln.split(None, 2)
                        if len(f) >= 3 and f[0] == "Device":
                            paired.add(f[1])
                            out.append({"mac": f[1], "name": f[2],
                                        "paired": True,
                                        "connected":
                                        self.bt_connected(f[1])})
                    if paired:
                        break
                except Exception:
                    pass
            for ln in self.bt_run("--", "devices").splitlines():
                f = ln.split(None, 2)
                if len(f) >= 3 and f[0] == "Device" and \
                        f[1] not in paired:
                    out.append({"mac": f[1], "name": f[2],
                                "paired": False, "connected": False})
            return out
        except Exception:
            return []

    def bt_hci(self, *args):
        hc = os.environ.get("VD_HCICFG", "hciconfig").split()
        return subprocess.run(hc + list(args), capture_output=True,
                              text=True, timeout=8).stdout

    def bt_powered(self):
        try:
            out = self.bt_hci("hci0")
            if "UP" in out or "DOWN" in out:
                return "UP" in out
        except Exception:
            pass
        try:
            return "Powered: yes" in self.bt_run("--", "show",
                                                 timeout=6)
        except Exception:
            return False

    def bt_hci_up(self):
        try:
            return "UP" in self.bt_hci("hci0")
        except Exception:
            return False

    def bt_bringup(self):
        """Accensione completa del chip, ricetta bltMuos
        (github.com/nvcuong1312/bltMuos): rfkill, modulo kernel,
        attach HCI via UART se serve, demone bluetoothd se non gira.
        Ogni passo e' innocuo se gia' soddisfatto: su hardware dove
        l'adattatore risponde subito a hciconfig, la cascata si ferma
        al primo gradino. Ogni comando e' isolato in try/except: un
        binario mancante non deve mai bloccare gli altri passi."""
        try:
            subprocess.run(["rfkill", "unblock", "all"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
        try:
            self.bt_hci("hci0", "up")
        except Exception:
            pass
        if self.bt_hci_up():
            return
        # il chip non ha risposto: prova il resto della cascata
        try:
            lsmod = subprocess.run(["lsmod"], capture_output=True,
                                   text=True, timeout=5).stdout
            if BT_MODULE not in lsmod:
                subprocess.run(["modprobe", BT_MODULE],
                               capture_output=True, timeout=8)
        except Exception:
            pass
        import shutil as _sh3
        if _sh3.which(BT_HCIATTACH) or os.environ.get(
                "VD_FORCE_HCIATTACH"):
            try:
                subprocess.Popen([BT_HCIATTACH, "-n", "-s", BT_BAUD,
                                  BT_UART, "rtk_h5"],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            except Exception:
                pass
            for _ in range(7):
                time.sleep(1)
                if self.bt_hci_up():
                    break
        try:
            self.bt_hci("hci0", "up")
        except Exception:
            pass
        # bluetoothd va tenuto vivo a mano: qui non c'e' systemd
        try:
            running = subprocess.run(
                ["pgrep", "-f", "bluetoothd"],
                capture_output=True, timeout=4).returncode == 0
        except Exception:
            running = True    # non blocco l'accensione per un pgrep fallito
        if not running and os.path.exists(BTD_BIN):
            try:
                subprocess.Popen([BTD_BIN, "-n", "-d"],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                time.sleep(1)
            except Exception:
                pass

    def bt_power_toggle(self):
        if self.bt_powered():
            try:
                self.bt_hci("hci0", "down")
            except Exception:
                pass
            self.bt_run("--", "power", "off")
        else:
            self.bt_bringup()
            self.bt_run("--", "power", "on")

    def bt_info_lines(self):
        it = (self.lang == "it")
        L = [("sec", "bt", "BLUETOOTH // INFO")]
        try:
            show = self.bt_run("--", "show", timeout=6)
        except Exception:
            show = ""
        for k, lbl in [("Address", "MAC"),
                       ("Name", "NOME" if it else "NAME"),
                       ("Alias", "ALIAS"),
                       ("Class", "CLASSE" if it else "CLASS"),
                       ("Powered", "ALIMENTAZIONE" if it else "POWER"),
                       ("Discoverable", "VISIBILE" if it
                        else "DISCOVERABLE"),
                       ("Pairable", "ASSOCIABILE" if it
                        else "PAIRABLE")]:
            m = re.search(k + r":\s*(.+)", show)
            if m:
                v = m.group(1).strip()
                L.append(("kv", lbl, v[:40],
                          OK_G if v == "yes" else
                          (FAINT if v == "no" else FG)))
        try:
            hci = self.bt_hci("hci0")
            m = re.search(r"RX bytes:(\d+)", hci)
            m2 = re.search(r"TX bytes:(\d+)", hci)
            if m and m2:
                L.append(("kv", "RX / TX", "%s / %s" %
                          (human(int(m.group(1))),
                           human(int(m2.group(1)))), DIM))
        except Exception:
            pass
        L.append(("kv", "PAIRED",
                  str(sum(1 for d in self.bt_devs if d["paired"])),
                  DIM))
        return L

    def bt_pair(self, dev):
        it = (self.lang == "it")

        def job():
            self.busy_label = "pair %s..." % dev["name"][:20]
            self.bt_run("--", "pair", dev["mac"], timeout=25)
            self.bt_run("--", "trust", dev["mac"])
            self.busy_label = "connect..."
            r = self.bt_run("--", "connect", dev["mac"], timeout=20)
            return r
        r = self.run_busy("...", job) or ""
        ok = "successful" in r.lower() or "connected: yes" in r.lower()
        self.info_lines = self.stub_lines(
            dev["name"], [("collegato" if it else "connected")
                          if ok else r.strip().splitlines()[-1][:90]
                          if r.strip() else "?"])
        self.scroll = 0
        self.push("info")

    # ================== HOTSPOT (script muOS) ==================
    def hot_find(self):
        """Gli script nativi (hostapd+dnsmasq, bin/vd_hotspot_*.sh) ci
        sono sempre: mai piu' un hotspot che dipende da uno script di
        terzi introvabile."""
        start = os.path.join(APP_DIR, "bin", "vd_hotspot_start.sh")
        stop = os.path.join(APP_DIR, "bin", "vd_hotspot_stop.sh")
        return {
            "start": (start, []),
            "start5": (start, ["5g"]),
            "stop": (stop, []),
        }

    def hot_active(self):
        try:
            for p in os.listdir("/proc"):
                if p.isdigit():
                    try:
                        if open("/proc/%s/comm" % p).read(
                                ).strip() == "hostapd":
                            return True
                    except OSError:
                        pass
        except OSError:
            pass
        return False

    def hot_toggle(self):
        """Interruttore diretto: A sullo switch. Spegne con lo script
        Stop se acceso, accende col 2.4GHz (piu' compatibile) se
        spento -- gli script nativi ci sono sempre, non serve piu'
        cercarli."""
        sc = self.hot_scripts if isinstance(
            getattr(self, "hot_scripts", None), dict) else \
            self.hot_find()
        on = self.hot_active()
        key = "stop" if on else "start"
        if key not in sc:
            return None
        p, arg = sc[key]
        try:
            return subprocess.run(["sh", p] + arg, capture_output=True,
                                  text=True, timeout=40).stdout
        except Exception as e:
            return str(e)

    def hot_devices(self):
        """Dispositivi connessi all'hotspot, letti dai lease DHCP veri
        di dnsmasq (non un conteggio approssimato): MAC, IP, nome se
        il device lo annuncia."""
        mode = "host"
        try:
            mode = open(os.path.join(DATA, ".hotspot_mode")).read().strip()
        except OSError:
            pass
        path = (os.path.join(DATA, "xfce_mnt", "tmp",
                             "dnsmasq_ap.leases") if mode == "chroot"
                else os.path.join(DATA, "dnsmasq_ap.leases"))
        out = []
        try:
            now = time.time()
            for ln in open(path).read().splitlines():
                parts = ln.split()
                if len(parts) < 4:
                    continue
                exp, mac, ip, host = parts[:4]
                try:
                    if int(exp) < now:
                        continue
                except ValueError:
                    pass
                out.append({"mac": mac, "ip": ip,
                           "host": host if host != "*" else ""})
        except OSError:
            pass
        return out

    def ani_cli_path(self):
        return os.path.join(DATA, "xfce_mnt", "usr", "local", "bin",
                            "ani-cli")

    def ani_cli_installed(self):
        p = self.ani_cli_path()
        return os.path.isfile(p) and os.access(p, os.X_OK)

    def ani_cli_download(self):
        """Scarica lo script ani-cli da GitHub dentro il chroot e lo
        rende eseguibile. Non e' un pacchetto apt: e' sempre stato
        cosi' anche a monte, un singolo script shell."""
        dbg = os.path.join(DATA, "ani_cli.log")

        def log(msg):
            try:
                with open(dbg, "a") as f:
                    f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
            except OSError:
                pass

        root = os.path.join(DATA, "xfce_mnt")
        was_mounted = imgmount.is_mounted(root)
        log("avvio: era gia' montato=%r" % was_mounted)
        we_remounted = False
        if not was_mounted:
            ok, err = imgmount.mount_img(
                os.path.join(DATA, "xfce.img"), root)
            log("mount fresco (rw): ok=%r err=%r" % (ok, err))
            if not ok:
                return False, err
        elif not imgmount.is_mounted_rw(root):
            # gia' montato, ma in sola lettura (es. residuo di uno scan
            # precedente): senza questo, la scrittura fallirebbe muta
            log("montato ma in SOLA LETTURA: rimonto in scrittura")
            rc = subprocess.run(["mount", "-o", "remount,rw", root],
                                capture_output=True, text=True, timeout=8)
            we_remounted = (rc.returncode == 0)
            log("remount rw: rc=%d stderr=%r" %
                (rc.returncode, rc.stderr.strip()))
            if not we_remounted:
                return False, ("chroot in sola lettura, remount "
                               "fallito: chiudi eventuali sessioni "
                               "attive e riprova")
        try:
            import urllib.request
            import urllib.error
            dest_dir = os.path.join(root, "usr", "local", "bin")
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, "ani-cli")
            url = os.environ.get("VD_ANI_CLI_URL", ANI_CLI_URL)
            log("scarico da %s" % url)
            req = urllib.request.Request(
                url, headers={"User-Agent": "VoidDesk"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            log("scaricati %d byte" % len(data))
            if not data or b"#!/" not in data[:20]:
                log("risposta non sembra uno script, primi byte: %r"
                    % data[:60])
                return False, "risposta inattesa: non sembra uno script"
            with open(dest, "wb") as f:
                f.write(data)
            os.chmod(dest, 0o755)
            log("scritto e reso eseguibile: %s" % dest)
            return True, "ani-cli installato"
        except urllib.error.URLError as e:
            reason = str(getattr(e, "reason", e))
            log("URLError: %s" % reason)
            if "CERTIFICATE" in reason.upper():
                return False, ("certificati SSL non validi sul "
                               "dispositivo: %s" % reason[:80])
            return False, ("rete non raggiungibile: %s" % reason[:90])
        except Exception as e:
            log("eccezione: %r" % e)
            return False, str(e)[:120]
        finally:
            if not was_mounted:
                imgmount.umount_tree(root)
                log("smontato (era stato montato fresco da qui)")

    def hotcfg_load(self):
        ssid, pw = "VoidDesk-AP", "voiddesk99"
        cf = os.path.join(DATA, "hotspot_custom.conf")
        try:
            for ln in open(cf).read().splitlines():
                if ln.startswith("SSID="):
                    ssid = ln.split("=", 1)[1]
                elif ln.startswith("PASS="):
                    pw = ln.split("=", 1)[1]
        except OSError:
            pass
        return ssid, pw

    def hotcfg_save(self, ssid, pw):
        # niente newline (romperebbero il formato riga-per-riga), niente
        # '=' iniziale ambiguo: lo script legge con grep+cut, mai eval,
        # quindi qualsiasi carattere e' innocuo -- ma restiamo puliti
        ssid = (ssid or "VoidDesk-AP").replace("\n", "").replace("\r",
                                                                  "")[:32]
        pw = (pw or "voiddesk99").replace("\n", "").replace("\r", "")
        if len(pw) < 8:
            pw = (pw + "00000000")[:8]
        pw = pw[:63]
        cf = os.path.join(DATA, "hotspot_custom.conf")
        try:
            with open(cf, "w") as f:
                f.write("SSID=%s\nPASS=%s\n" % (ssid, pw))
        except OSError:
            pass

    def hot_conf(self):
        mode = "host"
        try:
            mode = open(os.path.join(DATA, ".hotspot_mode")).read().strip()
        except OSError:
            pass
        default = (os.path.join(DATA, "xfce_mnt", "tmp", "hostapd.conf")
                   if mode == "chroot" else
                   os.path.join(DATA, "hostapd.conf"))
        cf = os.environ.get("VD_HOSTAPD_CONF", default)
        d = {}
        try:
            for ln in open(cf).read().splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    d[k.strip()] = v.strip()
        except OSError:
            pass
        return d

    def hot_info_lines(self):
        it = (self.lang == "it")
        cf = self.hot_conf()
        on = self.hot_active()
        iface = cf.get("interface", "wlan1")
        L = [("sec", "uplink", "HOTSPOT // INFO")]
        L.append(("kv", "STATO" if it else "STATE",
                  ("attivo" if it else "active") if on else
                  ("spento" if it else "off"), OK_G if on else FAINT))
        if cf:
            L.append(("kv", "SSID", cf.get("ssid", "?"), FG))
            L.append(("kv", "PASSWORD",
                      cf.get("wpa_passphrase", "?"), DIM))
            L.append(("kv", "CANALE" if it else "CHANNEL",
                      cf.get("channel", "?") +
                      ("  ·  " + cf.get("hw_mode", "")), DIM))
        L.append(("kv", "INTERFACCIA" if it else "INTERFACE",
                  iface, DIM))
        try:
            out = subprocess.run(["ip", "-4", "addr", "show", iface],
                                 capture_output=True, text=True,
                                 timeout=3).stdout
            m = re.search(r"inet ([0-9.]+)", out)
            if m:
                L.append(("kv", "IP", m.group(1), FG))
        except Exception:
            pass
        devs = self.hot_devices()
        L.append(("kv", "CLIENT" if it else "CLIENTS", str(len(devs)),
                  OK_G if devs else DIM))
        for d in devs:
            nm = d["host"] or ("sconosciuto" if it else "unknown")
            L.append(("kv", d["ip"], "%s  ·  %s" % (nm, d["mac"]), DIM))
        sc = self.hot_scripts if isinstance(
            getattr(self, "hot_scripts", None), dict) else {}
        for k, lbl in (("start", "script start"),
                       ("start5", "script 5GHz"),
                       ("stop", "script stop")):
            if sc.get(k):
                L.append(("kv", lbl, sc[k][0], FAINT))
        return L

    # ================== VOID MONITOR ==================
    def mon_stats(self, data):
        if not data:
            return 0, 0, 0, 0
        return data[-1], min(data), max(data), sum(data) // len(data)

    def mon_pill(self, x, y, w, h, pct, col):
        """Barra a pillola (estremi tondi): widget CPU."""
        pygame.draw.rect(self.surface, (14, 15, 19), (x, y, w, h),
                         border_radius=h // 2)
        fw = max(h, int(w * pct / 100.0))
        if pct > 0:
            pygame.draw.rect(self.surface, col, (x, y, fw, h),
                             border_radius=h // 2)
        pygame.draw.rect(self.surface, LINE, (x, y, w, h), 1,
                         border_radius=h // 2)

    def mon_blocks(self, x, y, w, h, pct, col, n=16):
        """Blocchi accesi in sequenza, stile VU-meter: widget RAM."""
        gap = 3
        bw = (w - gap * (n - 1)) // n
        lit = int(round(n * pct / 100.0))
        for i2 in range(n):
            on = i2 < lit
            c = col if on else (26, 28, 34)
            if on and i2 >= n - 3 and pct > 85:
                c = NO_R
            pygame.draw.rect(self.surface, c,
                             (x + i2 * (bw + gap), y, bw, h),
                             border_radius=2)

    def mon_thermo(self, cx, top_y, bot_y, r, pct, col):
        """Termometro verticale: widget TEMP, il bulbo in basso."""
        w = r * 2
        pygame.draw.rect(self.surface, (14, 15, 19),
                         (cx - r // 2, top_y, r, bot_y - top_y))
        pygame.draw.circle(self.surface, (14, 15, 19), (cx, bot_y), r)
        fill_h = int((bot_y - top_y) * pct / 100.0)
        pygame.draw.rect(self.surface, col,
                         (cx - r // 2, bot_y - fill_h, r,
                          fill_h + r))
        pygame.draw.circle(self.surface, col, (cx, bot_y), r)
        pygame.draw.rect(self.surface, LINE,
                         (cx - r // 2, top_y, r, bot_y - top_y), 1)
        pygame.draw.circle(self.surface, LINE, (cx, bot_y), r, 1)

    def mon_spark(self, x, y, w, h, data, col, n=44):
        bw2 = max(2, w // n)
        for i2, v in enumerate(data[-n:]):
            hh = max(1, v * h // 100)
            self.surface.fill(col, (x + i2 * bw2, y + h - hh,
                                    max(1, bw2 - 1), hh))
        pygame.draw.line(self.surface, LINE, (x, y + h), (x + w, y + h))

    def mon_sample(self):
        m = self.mon
        now = time.time()
        if now - m["t"] < 0.5:
            return
        m["t"] = now
        try:
            f = open("/proc/stat").readline().split()[1:8]
            v = [int(x) for x in f]
            idle, tot = v[3] + v[4], sum(v)
            if m["last"]:
                di, dt = idle - m["last"][0], tot - m["last"][1]
                cpu = 100 - (di * 100 // max(1, dt))
            else:
                cpu = 0
            rx = tx = 0
            for ln in open("/proc/net/dev").readlines()[2:]:
                p = ln.split()
                if p[0].rstrip(":") in ("lo",):
                    continue
                rx += int(p[1]); tx += int(p[9])
            net = 0
            if m["last"]:
                net = (rx + tx - m["last"][2]) / 1024.0 / \
                    max(0.2, now - m["last"][3])
            m["last"] = (idle, tot, rx + tx, now)
            mi = {}
            for ln in open("/proc/meminfo").readlines()[:4]:
                k, v2 = ln.split(":")
                mi[k] = int(v2.split()[0])
            ram = 100 - mi.get("MemAvailable", 0) * 100 // \
                max(1, mi.get("MemTotal", 1))
            t = 0
            for zz in range(3):
                try:
                    t = max(t, int(open(
                        "/sys/class/thermal/thermal_zone%d/temp" % zz
                        ).read()) // 1000)
                except OSError:
                    pass
            for k, val in (("cpu", cpu), ("ram", ram),
                           ("net", min(100, int(net / 20))),
                           ("tmp", t)):
                m[k].append(max(0, min(100, val)))
                del m[k][:-90]
            m["netkb"] = net
            m["tempc"] = t
        except (OSError, ValueError, IndexError):
            pass

    # ================== BACKUP IMMAGINE ==================
    def bak_dir(self):
        for d in ([os.environ["VD_ARCHIVE"]]
                  if os.environ.get("VD_ARCHIVE") else []) + \
                ["/mnt/mmc/ARCHIVE", "/mnt/sdcard/ARCHIVE", DATA]:
            try:
                os.makedirs(d, exist_ok=True)
                return d
            except OSError:
                continue
        return DATA

    def bak_list(self):
        d = self.bak_dir()
        out = []
        try:
            for f in sorted(os.listdir(d), reverse=True):
                if f.startswith("voiddesk_img_") and f.endswith(".gz"):
                    p = os.path.join(d, f)
                    out.append((f, p, os.path.getsize(p)))
        except OSError:
            pass
        return out

    def bak_create(self):
        import gzip
        it = (self.lang == "it")
        img = os.path.join(DATA, "xfce.img")
        if not os.path.exists(img):
            return "no-img"
        if "xfce_mnt" in open("/proc/mounts").read():
            return "mounted"
        dst = os.path.join(self.bak_dir(), "voiddesk_img_%s.gz"
                           % time.strftime("%Y%m%d_%H%M"))
        tot = os.path.getsize(img)
        done = 0
        try:
            with open(img, "rb") as fi, \
                    gzip.open(dst, "wb", compresslevel=1) as fo:
                while True:
                    b = fi.read(4 * 1024 * 1024)
                    if not b:
                        break
                    fo.write(b)
                    done += len(b)
                    self.busy_label = "%s %d%%  (%s / %s)" % (
                        "backup" if it else "backing up",
                        done * 100 // tot, human(done), human(tot))
        except OSError:
            try:
                os.remove(dst)
            except OSError:
                pass
            return "err"
        return dst

    def bak_restore(self, path):
        import gzip
        it = (self.lang == "it")
        if "xfce_mnt" in open("/proc/mounts").read():
            return "mounted"
        img = os.path.join(DATA, "xfce.img")
        tot = os.path.getsize(path)
        done = 0
        try:
            with gzip.open(path, "rb") as fi, \
                    open(img + ".new", "wb") as fo:
                while True:
                    b = fi.read(4 * 1024 * 1024)
                    if not b:
                        break
                    fo.write(b)
                    done += len(b)
                    self.busy_label = "%s... (%s)" % (
                        "ripristino" if it else "restoring",
                        human(fo.tell()))
            os.replace(img + ".new", img)
        except OSError:
            try:
                os.remove(img + ".new")
            except OSError:
                pass
            return "err"
        return "ok"

    # ================== PYTHON REPL (host) ==================
    def py_exec(self, line):
        import io as _io
        import contextlib
        self.py_out[-1] = ">>> " + line
        if line.startswith("!"):
            try:
                r = subprocess.run(["sh", "-c", line[1:]],
                                   capture_output=True, text=True,
                                   timeout=30)
                out = (r.stdout + r.stderr).strip() or "(ok)"
            except subprocess.TimeoutExpired:
                out = "timeout (30s)"
            for ln in out.splitlines()[-30:]:
                self.py_out.append(ln[:110])
            self.py_out.append(">>> ")
            del self.py_out[:-200]
            return
        buf = _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), \
                    contextlib.redirect_stderr(buf):
                try:
                    r = eval(line, self.py_ns)
                    if r is not None:
                        print(repr(r))
                except SyntaxError:
                    exec(line, self.py_ns)
        except Exception as e:
            buf.write("%s: %s" % (type(e).__name__, e))
        for ln in buf.getvalue().splitlines():
            self.py_out.append(ln[:110])
        self.py_out.append(">>> ")
        del self.py_out[:-200]

    def py_runfile(self, path):
        import io as _io
        import contextlib
        self.py_out[-1] = ">>> # run " + os.path.basename(path)
        buf = _io.StringIO()
        try:
            code = open(path, errors="replace").read()
            with contextlib.redirect_stdout(buf), \
                    contextlib.redirect_stderr(buf):
                exec(compile(code, path, "exec"), self.py_ns)
        except Exception as e:
            buf.write("%s: %s" % (type(e).__name__, e))
        for ln in buf.getvalue().splitlines()[-40:]:
            self.py_out.append(ln[:110])
        self.py_out.append(">>> ")
        del self.py_out[:-200]

    def run_script(self, path):
        it = (self.lang == "it")
        ext = path.rsplit(".", 1)[-1].lower()
        cmd = ["sh", path] if ext == "sh" else ["python3", path]

        def job():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=60)
                return (r.stdout + r.stderr).strip() or "(nessun output)"
            except subprocess.TimeoutExpired:
                return "timeout (60s)"
        out = self.run_busy(("eseguo %s..." if it else "running %s...")
                            % os.path.basename(path), job)
        L = [("sec", "terminal", os.path.basename(path)[:26])]
        for ln in (out or "").splitlines()[-14:]:
            L.append(("kv", "", ln[:100], DIM))
        self.info_lines = L
        self.scroll = 0
        self.push("info")

    # ================== TAILSCALE: pannello nativo (cuore Rt) ==========
    def ts_cli(self, *args, timeout=10):
        return subprocess.run([TS_BIN, "--socket=" + TS_SOCK]
                              + list(args), capture_output=True,
                              text=True, timeout=timeout)

    def ts_status(self):
        import json as _j
        r = self.ts_cli("status", "--json")
        st = _j.loads(r.stdout or "{}")
        me = st.get("Self") or {}
        peers = []
        for p in (st.get("Peer") or {}).values():
            peers.append({
                "name": p.get("HostName", "?"),
                "ip": (p.get("TailscaleIPs") or ["?"])[0],
                "on": bool(p.get("Online")),
                "os": p.get("OS", ""),
                "exit": bool(p.get("ExitNodeOption")),
                "using": bool(p.get("ExitNode"))})
        peers.sort(key=lambda p: (not p["on"], p["name"].lower()))
        return {"state": st.get("BackendState", "?"),
                "ip": (me.get("TailscaleIPs") or [""])[0],
                "host": me.get("HostName", ""),
                "ssh": bool((st.get("Self") or {}).get("SSH_HostKeys")),
                "peers": peers}

    def ts_open(self):
        it = (self.lang == "it")
        if not os.path.exists(TS_BIN):
            self.info_lines = self.stub_lines(
                "TAILSCALE",
                ["tailscale non trovato in /opt/muos/bin: aggiorna muOS "
                 "o installa Rt-Tailscale." if it else
                 "tailscale not found in /opt/muos/bin: update muOS or "
                 "install Rt-Tailscale."])
            self.scroll = 0
            self.push("info")
            return
        try:
            self.ts = self.run_busy("tailscale...", self.ts_status)
        except Exception:
            self.ts = None
        if not self.ts:
            self.info_lines = self.stub_lines(
                "TAILSCALE",
                ["demone non raggiungibile (socket %s)" % TS_SOCK])
            self.scroll = 0
            self.push("info")
            return
        self.ts_sel = 0
        self.mon = {"cpu": [], "ram": [], "net": [], "tmp": [],
                    "last": None, "t": 0}
        self.py_ns = {}
        self.py_out = [">>> "]
        self.bak_sel = 0
        self.viewer_live = False
        self.wm_nets = []
        self.wm_sel = 0
        self.bt_devs = []
        self.bt_sel = 0
        if not hasattr(self, "ts_logo"):
            try:
                img = pygame.image.load(
                    os.path.join(APP_DIR, "assets", "tailscale.png"))
                self.ts_logo = pygame.transform.smoothscale(img, (30, 30))
            except pygame.error:
                self.ts_logo = None
        self.push("tspanel")

    def ts_refresh(self):
        try:
            self.ts = self.run_busy("tailscale...", self.ts_status)
        except Exception:
            pass

    def ts_menu_items(self):
        it = (self.lang == "it")
        run = (self.ts or {}).get("state") == "Running"
        A = []
        if (self.ts or {}).get("state") == "NeedsLogin":
            A.append(("login", "Login (mostra URL)" if it
                      else "Login (show URL)"))
        A.append(("down" if run else "up",
                  ("Disconnetti" if run else "Connetti") if it else
                  ("Disconnect" if run else "Connect")))
        A.append(("exitoff", "Exit node: nessuno" if it
                  else "Exit node: none"))
        A.append(("recv", "Ricevi file (Taildrop)" if it
                  else "Receive files (Taildrop)"))
        A.append(("rtapp", "Apri Rt-Tailscale" if it
                  else "Open Rt-Tailscale"))
        A.append(("logout", "Logout"))
        return A

    def ts_menu_do(self, key):
        it = (self.lang == "it")
        if key == "up":
            self.run_busy("tailscale up...",
                          lambda: self.ts_cli("up", "--accept-dns=true",
                                              "--accept-routes=true",
                                              timeout=20))
            self.ts_refresh()
        elif key == "down":
            self.run_busy("...", lambda: self.ts_cli("down"))
            self.ts_refresh()
        elif key == "exitoff":
            self.run_busy("...",
                          lambda: self.ts_cli("set", "--exit-node="))
            self.ts_refresh()
        elif key == "recv":
            dest = "/mnt/mmc/ROMS/Taildrop"
            try:
                os.makedirs(dest, exist_ok=True)
            except OSError:
                dest = os.path.join(DATA, "taildrop")
                os.makedirs(dest, exist_ok=True)
            r = self.run_busy("taildrop...",
                              lambda: self.ts_cli("file", "get", dest,
                                                  timeout=30))
            self.info_lines = self.stub_lines(
                "TAILDROP", [(r.stdout or r.stderr or "ok").strip()[:90],
                             dest])
            self.scroll = 0
            self.push("info")
        elif key == "rtapp":
            hit = [a for a in self.scan_muos()
                   if "tailscale" in a["name"].lower()]
            if hit:
                self.launch_muos(hit[0])
        elif key == "logout":
            def go():
                self.run_busy("...", lambda: self.ts_cli("logout"))
                self.ts_refresh()
            self.confirm = ("Tailscale logout", go)
            self.push("confirm")
        elif key == "login":
            def job():
                import re as _re
                proc = subprocess.Popen(
                    [TS_BIN, "--socket=" + TS_SOCK, "up",
                     "--accept-dns=true", "--accept-routes=true"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True)
                url = ""
                t0 = time.time()
                for ln in proc.stdout:
                    m = _re.search(r"https://login\.tailscale\.com/\S+",
                                   ln)
                    if m:
                        url = m.group(0)
                        break
                    if time.time() - t0 > 12:
                        break
                return url
            url = self.run_busy("genero il link..." if it
                                else "getting the link...", job)
            self.info_lines = self.stub_lines(
                "LOGIN TAILSCALE",
                [url or ("nessun URL: forse sei gia' loggato" if it
                         else "no URL: maybe already logged in"),
                 "apri l'URL da un altro device; il QR e' in "
                 "Rt-Tailscale" if it else
                 "open the URL from another device; QR lives in "
                 "Rt-Tailscale"])
            self.scroll = 0
            self.push("info")

    def ts_peer_do(self, key, peer):
        it = (self.lang == "it")
        if key == "ping":
            r = self.run_busy("ping %s..." % peer["name"],
                              lambda: self.ts_cli("ping", "-c", "3",
                                                  peer["ip"],
                                                  timeout=20))
            self.info_lines = self.stub_lines(
                "PING " + peer["name"],
                [(r.stdout or r.stderr or "?").strip().splitlines()[-1]
                 [:90]])
            self.scroll = 0
            self.push("info")
        elif key == "exit":
            self.run_busy("...", lambda: self.ts_cli(
                "set", "--exit-node=" + peer["ip"]))
            self.ts_refresh()
        elif key == "send":
            def cb(local):
                self.run_busy(("invio a %s..." if it else
                               "sending to %s...") % peer["name"],
                              lambda: self.ts_cli(
                                  "file", "cp", local,
                                  peer["name"] + ":", timeout=120))
            self.fm_open(pick=cb)
        elif key == "pinfo":
            self.info_lines = self.stub_lines(
                peer["name"], ["%s  ·  %s  ·  %s" %
                               (peer["ip"], peer["os"] or "?",
                                "online" if peer["on"] else "offline")])
            self.scroll = 0
            self.push("info")

    # ================== SYNCTHING: pannello nativo ==================
    def sync_rest(self, url, key, path):
        import urllib.request
        import json as _j
        req = urllib.request.Request(url + path,
                                     headers={"X-API-Key": key})
        with urllib.request.urlopen(req, timeout=4) as r:
            return _j.loads(r.read().decode() or "{}")

    def sync_open(self):
        it = (self.lang == "it")
        url = os.environ.get("VD_SYNC_URL")
        key = os.environ.get("VD_SYNC_KEY")
        if not url:
            cand = ["/mnt/mmc/MUOS/syncthing/config.xml",
                    "/mnt/sdcard/MUOS/syncthing/config.xml",
                    "/root/.local/state/syncthing/config.xml",
                    "/root/.config/syncthing/config.xml",
                    os.path.expanduser("~/.config/syncthing/config.xml")]
            for r_ in MUOS_APP_ROOTS:
                try:
                    for d in os.listdir(r_):
                        if "syncthing" in d.lower():
                            for sub in ("config.xml",
                                        "config/config.xml",
                                        "state/config.xml"):
                                cand.append(os.path.join(r_, d, sub))
                except OSError:
                    pass
            root = os.path.join(DATA, "xfce_mnt")
            cand += [os.path.join(root, c) for c in
                     ("root/.local/state/syncthing/config.xml",
                      "root/.config/syncthing/config.xml")]
            for p in cand:
                if os.path.exists(p):
                    txt = open(p, errors="ignore").read()
                    m = re.search(r"<apikey>([^<]+)</apikey>", txt)
                    a = re.search(r"<address>([0-9.:]+)</address>", txt)
                    if not m:
                        apitxt = os.path.join(os.path.dirname(p),
                                              "api.txt")
                        if os.path.exists(apitxt):
                            k2 = open(apitxt, errors="ignore"
                                     ).read().strip()
                            if k2:
                                key = k2
                                url = "http://" + (a.group(1) if a
                                                   else "127.0.0.1:8384")
                                self._sync_home = os.path.dirname(p)
                                break
                    if m:
                        key = m.group(1)
                        url = "http://" + (a.group(1) if a
                                           else "127.0.0.1:8384")
                        self._sync_home = os.path.dirname(
                            os.path.dirname(p))
                    break
        if not (url and key):
            self.info_lines = self.stub_lines(
                "SYNCTHING",
                ["Syncthing non configurato nell'immagine: installalo "
                 "dal FORGE e avvialo una volta nel desktop." if it else
                 "Syncthing not configured in the image: install it "
                 "from FORGE and run it once in the desktop."])
            self.scroll = 0
            self.push("info")
            return

        def job():
            try:
                self.sync_rest(url, key, "/rest/system/ping")
            except Exception:
                if os.environ.get("VD_SYNC_NOSTART"):
                    return None
                import shutil as _sh2
                host_bin = _sh2.which("syncthing") or \
                    ("/opt/muos/bin/syncthing"
                     if os.path.exists("/opt/muos/bin/syncthing")
                     else None)
                if host_bin:
                    subprocess.Popen(
                        [host_bin, "serve", "--no-browser",
                         "--no-restart"],
                        env=dict(os.environ,
                                 HOME=getattr(self, "_sync_home",
                                              "/root")),
                        stdout=open(os.path.join(DATA,
                                                 "syncthing.log"),
                                    "ab"),
                        stderr=subprocess.STDOUT)
                else:
                    mnt = os.path.join(DATA, "xfce_mnt")
                    subprocess.Popen(
                        ["chroot", mnt, "/usr/bin/env", "HOME=/root",
                         "syncthing", "serve", "--no-browser",
                         "--no-restart"],
                        stdout=open(os.path.join(DATA,
                                                 "syncthing.log"),
                                    "ab"),
                        stderr=subprocess.STDOUT)
                for _ in range(16):
                    time.sleep(0.5)
                    try:
                        self.sync_rest(url, key, "/rest/system/ping")
                        break
                    except Exception:
                        pass
            try:
                st = self.sync_rest(url, key, "/rest/system/status")
                cfg = self.sync_rest(url, key, "/rest/config")
                folders = []
                for f in cfg.get("folders", []):
                    pct = -1
                    try:
                        c = self.sync_rest(
                            url, key,
                            "/rest/db/completion?folder=" + f["id"])
                        pct = int(c.get("completion", 0))
                    except Exception:
                        pass
                    folders.append((f.get("label") or f["id"],
                                    f.get("path", ""), pct))
                return {"id": st.get("myID", "?")[:14],
                        "url": url, "key": key, "folders": folders}
            except Exception:
                return None
        self.sync = self.run_busy(
            "interrogo syncthing..." if it else "querying syncthing...",
            job)
        if not self.sync:
            self.info_lines = self.stub_lines(
                "SYNCTHING",
                ["demone non raggiungibile: avvialo nel desktop o "
                 "riprova" if it else
                 "daemon unreachable: start it in the desktop and retry"])
            self.scroll = 0
            self.push("info")
        else:
            self.push("syncpanel")

    # ================== VOID EDIT: editor di testo ==================
    def ed_load(self, path):
        it = (self.lang == "it")
        try:
            if os.path.getsize(path) > 512 * 1024:
                self.info_lines = self.stub_lines(
                    os.path.basename(path),
                    ["file troppo grande per l'editor (max 512KB)" if it
                     else "file too big for the editor (512KB max)"])
                self.scroll = 0
                self.push("info")
                return
            txt = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            txt = ""
        self.ed_path = path
        self.ed_lines = txt.split("\n") or [""]
        self.ed_cur = 0
        self.ed_dirty = False
        self.ed_msg = ""
        self.push("edit")

    def ed_save(self, path=None):
        it = (self.lang == "it")
        p = path or self.ed_path
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(self.ed_lines))
            self.ed_path = p
            self.ed_dirty = False
            self.ed_msg = ("salvato " if it else "saved ") + \
                time.strftime("%H:%M:%S")
        except OSError as e:
            self.ed_msg = "ERR: %s" % e

    # ================== OSK: input testo col pad ==================
    def osk_open(self, title, initial, cb):
        self.osk_title = title
        self.osk_buf = initial or ""
        self.osk_cb = cb
        self.osk_page = 0
        self.osk_sel = 0
        self.osk_cursor = len(self.osk_buf)
        self.push("osk")

    def osk_key(self):
        rows = OSK_PAGES[self.osk_page]
        r, c = divmod(self.osk_sel, 10)
        return rows[r][c]

    # ================== VOID FILES: file manager nativo ==================
    def fm_roots(self):
        it = (self.lang == "it")
        R = []
        for p, lbl in (("/mnt/mmc", "SD1"), ("/mnt/sdcard", "SD2"),
                       (DATA, "DATI VOID" if it else "VOID DATA")):
            if os.path.isdir(p):
                R.append((os.path.realpath(p), lbl))
        return R or [(os.path.expanduser("~"), "HOME")]

    def fm_list(self, path):
        try:
            names = os.listdir(path)
        except OSError:
            return [("..", True, 0)]
        dirs, files = [], []
        for n in names:
            p = os.path.join(path, n)
            try:
                if os.path.isdir(p):
                    dirs.append((n, True, 0))
                else:
                    files.append((n, False, os.path.getsize(p)))
            except OSError:
                files.append((n, False, 0))
        dirs.sort(key=lambda a: a[0].lower())
        files.sort(key=lambda a: a[0].lower())
        return [("..", True, 0)] + dirs + files

    def fm_open(self, pick=None):
        self.fm_pick = pick
        if not self.fm_path or not os.path.isdir(self.fm_path):
            self.fm_path = None          # None = schermata radici
        self.fm_sel = 0
        self.fm_marked.clear()
        self.fm_refresh()
        self.push("files")

    def fm_refresh(self):
        if self.fm_path:
            self.fm_items = self.fm_list(self.fm_path)
        else:
            self.fm_items = [(lbl, True, 0) for _p, lbl in self.fm_roots()]
        self.fm_sel = min(self.fm_sel, max(0, len(self.fm_items) - 1))

    def fm_icon(self, name, is_dir):
        if is_dir:
            return "folder"
        e = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        return {"png": "image", "jpg": "image", "jpeg": "image",
                "gif": "image", "bmp": "image", "txt": "text",
                "log": "text", "md": "text", "cfg": "text", "conf": "text",
                "ini": "text", "json": "text", "sh": "terminal",
                "py": "terminal", "zip": "archive", "muxapp": "archive",
                "gz": "archive", "7z": "archive", "mp3": "music",
                "ogg": "music", "wav": "music", "mp4": "video",
                "mkv": "video", "pdf": "doc"}.get(e, "doc")

    def fm_enter(self):
        name, is_dir, _sz = self.fm_items[self.fm_sel]
        if self.fm_path is None:
            self.fm_path = dict((l, p) for p, l in self.fm_roots())[name]
            self.fm_sel = 0
            self.fm_refresh()
            return
        if name == "..":
            self.fm_up()
            return
        p = os.path.join(self.fm_path, name)
        if is_dir:
            self.fm_path = p
            self.fm_sel = 0
            self.fm_refresh()
        elif self.fm_pick:
            cb = self.fm_pick
            self.fm_pick = None
            self.pop_state()
            cb(p)
        else:
            ic = self.fm_icon(name, False)
            if ic == "image":
                self.img_path = p
                self.push("imgview")
            elif ic in ("text", "terminal"):
                self.ed_load(p)
            else:
                self.info_lines = self.stub_lines(
                    name, ["%s  ·  %s" % (human(_sz), p)])
                self.scroll = 0
                self.push("info")

    def fm_up(self):
        roots = [p for p, _l in self.fm_roots()]
        if self.fm_path in roots or self.fm_path is None:
            self.fm_path = None
        else:
            self.fm_path = os.path.dirname(self.fm_path)
        self.fm_sel = 0
        self.fm_refresh()

    def fm_do(self, op):
        """Esegue copia/sposta/elimina con progresso vivo nel busy."""
        import shutil as _sh
        it = (self.lang == "it")
        if op in ("copy", "cut"):
            sel = sorted(self.fm_marked) or                 ([os.path.join(self.fm_path,
                               self.fm_items[self.fm_sel][0])]
                 if self.fm_items[self.fm_sel][0] != ".." else [])
            if sel:
                self.fm_clip = (op, sel)
                self.fm_marked.clear()
            return
        if op == "paste" and self.fm_clip:
            kind, paths = self.fm_clip

            def job():
                done = 0
                for i, src in enumerate(paths):
                    self.busy_label = "%s %d/%d: %s" % (
                        "copio" if it else "copying", i + 1, len(paths),
                        os.path.basename(src)[:22])
                    dst = os.path.join(self.fm_path,
                                       os.path.basename(src))
                    if os.path.exists(dst):
                        continue
                    try:
                        if kind == "cut":
                            _sh.move(src, dst)
                        elif os.path.isdir(src):
                            _sh.copytree(src, dst)
                        else:
                            _sh.copy2(src, dst)
                        done += 1
                    except OSError:
                        pass
                return done
            n = self.run_busy("...", job)
            if self.fm_clip[0] == "cut":
                self.fm_clip = None
            self.fm_refresh()
            return
        if op == "delete":
            sel = sorted(self.fm_marked) or                 ([os.path.join(self.fm_path,
                               self.fm_items[self.fm_sel][0])]
                 if self.fm_items[self.fm_sel][0] != ".." else [])
            if not sel:
                return

            def go():
                for p in sel:
                    try:
                        if os.path.isdir(p):
                            _sh.rmtree(p)
                        else:
                            os.remove(p)
                    except OSError:
                        pass
                self.fm_marked.clear()
                self.fm_refresh()
            self.confirm = ("%d file" % len(sel), go)
            self.push("confirm")

    def fm_menu_items(self):
        it = (self.lang == "it")
        n = len(self.fm_marked)
        cur = self.fm_items[self.fm_sel][0] if self.fm_items else ".."
        A = []
        if self.fm_clip:
            A.append(("paste", ("Incolla qui (%d)" if it else
                                "Paste here (%d)") % len(self.fm_clip[1])))
        A.append(("copy", ("Copia (%d)" if it else "Copy (%d)")
                  % max(1, n)))
        A.append(("cut", ("Taglia (%d)" if it else "Cut (%d)")
                  % max(1, n)))
        if n <= 1 and cur != "..":
            A.append(("rename", "Rinomina" if it else "Rename"))
        A.append(("newdir", "Nuova cartella" if it else "New folder"))
        A.append(("newfile", "Nuovo file di testo" if it else
                  "New text file"))
        A.append(("delete", ("Elimina (%d)" if it else "Delete (%d)")
                  % max(1, n)))
        if n <= 1 and cur.rsplit(".", 1)[-1].lower() in ("sh", "py"):
            A.append(("frun", "Esegui" if it else "Run"))
        A.append(("finfo", "Info" if it else "Info"))
        return A

    def fm_menu_do(self, key):
        it = (self.lang == "it")
        if key in ("copy", "cut", "paste", "delete"):
            self.fm_do(key)
            return
        cur = self.fm_items[self.fm_sel][0]
        if key == "rename":
            def rn(nm):
                if nm and nm != cur:
                    try:
                        os.rename(os.path.join(self.fm_path, cur),
                                  os.path.join(self.fm_path, nm))
                    except OSError:
                        pass
                    self.fm_refresh()
            self.osk_open("RINOMINA" if it else "RENAME", cur, rn)
        elif key == "newdir":
            def nd(nm):
                if nm:
                    try:
                        os.makedirs(os.path.join(self.fm_path, nm),
                                    exist_ok=True)
                    except OSError:
                        pass
                    self.fm_refresh()
            self.osk_open("NUOVA CARTELLA" if it else "NEW FOLDER",
                          "", nd)
        elif key == "newfile":
            def nf(nm):
                if nm:
                    p = os.path.join(self.fm_path, nm)
                    try:
                        open(p, "a").close()
                    except OSError:
                        return
                    self.fm_refresh()
                    self.ed_load(p)
            self.osk_open("NUOVO FILE" if it else "NEW FILE",
                          "nuovo.txt" if it else "new.txt", nf)
        elif key == "frun":
            self.run_script(os.path.join(self.fm_path, cur))
        elif key == "finfo":
            p = os.path.join(self.fm_path, cur)
            L = [("sec", "folder", cur[:26])]
            try:
                st = os.stat(p)
                L.append(("kv", self.t("size"),
                          human(self.app_size(p)
                                if os.path.isdir(p) else st.st_size), FG))
                L.append(("kv", "mtime",
                          time.strftime("%Y-%m-%d %H:%M",
                                        time.localtime(st.st_mtime)),
                          DIM))
            except OSError:
                pass
            L.append(("kv", "path", p, FAINT))
            self.info_lines = L
            self.scroll = 0
            self.push("info")

    def mapp_quick_info(self, app):
        """Solo info a costo quasi zero: mai una du -sk qui dentro,
        con tante app scorrerebbe malissimo. Data e tag HELP bastano
        per la vista Dettagliato."""
        info = {"date": "", "help": ""}
        try:
            ctime = os.path.getctime(app["dir"])
            info["date"] = time.strftime("%d/%m/%Y",
                                         time.localtime(ctime))
        except OSError:
            pass
        try:
            head = open(os.path.join(app["dir"], "mux_launch.sh"),
                        errors="ignore").read(600)
            for ln in head.splitlines():
                ls = ln.strip()
                if ls.upper().startswith("# HELP:"):
                    info["help"] = ls.split(":", 1)[1].strip()[:40]
                    break
        except OSError:
            pass
        return info

    def app_size(self, d):
        try:
            out = subprocess.run(["du", "-sk", d], capture_output=True,
                                 timeout=6, text=True).stdout.split()
            return int(out[0]) * 1024
        except Exception:
            tot = 0
            for i, (r, _dd, ff) in enumerate(os.walk(d)):
                for f in ff:
                    try:
                        tot += os.path.getsize(os.path.join(r, f))
                    except OSError:
                        pass
                if i > 400:
                    break
            return tot

    def is_sys_protected(self, name):
        n = name.lower()
        return any(p in n for p in PROTECTED)

    def is_user_protected(self, name):
        return name in (self.cfg.get("mapp_protected") or [])

    def is_protected(self, name):
        return self.is_sys_protected(name) or self.is_user_protected(name)

    def mapp_other_root(self, app):
        """Restituisce (root, etichetta) della SD opposta a dove l'app
        vive ora, o None se non c'e' una seconda SD configurata."""
        try:
            cur_idx = int(app["sd"][2:]) - 1
        except (ValueError, IndexError):
            return None
        other_idx = 1 - cur_idx
        if other_idx < 0 or other_idx >= len(MUOS_APP_ROOTS):
            return None
        return MUOS_APP_ROOTS[other_idx], "SD%d" % (other_idx + 1)

    def mapp_move_label(self):
        it = (self.lang == "it")
        dest = self.mapp_other_root(self.mapp_cur)
        if not dest:
            return "SD" if it else "SD"
        return (("Sposta su %s" if it else "Move to %s") % dest[1])

    def mapp_move(self, app):
        dest = self.mapp_other_root(app)
        if not dest:
            return "no-dest"
        root, _lbl = dest
        try:
            os.makedirs(root, exist_ok=True)
        except OSError:
            return "err"
        target = os.path.join(root, os.path.basename(app["dir"]))
        if os.path.exists(target):
            return "exists"
        try:
            import shutil
            shutil.move(app["dir"], target)
        except OSError:
            return "err"
        return "ok"

    def mapp_info_lines(self, app):
        it = (self.lang == "it")
        L = [("sec", "info", app["name"][:26])]
        L.append(("kv", "SD", app["sd"], FG))
        L.append(("kv", self.t("size"), human(self.mapp_size or 0), FG))
        try:
            ctime = os.path.getctime(app["dir"])
            L.append(("kv", "installata il" if it else "installed on",
                      time.strftime("%d/%m/%Y %H:%M",
                                    time.localtime(ctime)), DIM))
        except OSError:
            pass
        L.append(("kv", "percorso" if it else "path", app["dir"], FAINT))
        tags = {}
        try:
            head = open(os.path.join(app["dir"], "mux_launch.sh"),
                        errors="ignore").read(800)
            for ln in head.splitlines():
                ls = ln.strip()
                for k2 in ("HELP", "ICON", "GRID"):
                    pre = "# %s:" % k2
                    if ls.upper().startswith(pre):
                        tags[k2] = ls.split(":", 1)[1].strip()
        except OSError:
            pass
        for k2, v in tags.items():
            L.append(("kv", k2, v[:44], DIM))
        gov = (self.cfg.get("mapp_gov") or {}).get(app["name"], "default")
        L.append(("kv", self.t("gov"), gov, self.accent))
        prot = ("sistema" if self.is_sys_protected(app["name"]) else
                "utente" if self.is_user_protected(app["name"]) else
                "no") if it else \
            ("system" if self.is_sys_protected(app["name"]) else
             "user" if self.is_user_protected(app["name"]) else "no")
        L.append(("kv", "protetta" if it else "protected", prot,
                  OK_G if prot != "no" else FAINT))
        return L

    def detail_actions(self):
        it = (self.lang == "it")
        app = self.mapp_cur
        A = [("launch", "start", self.t("mapps_go").upper()),
             ("gov", "gauge", self.t("gov")),
             ("glyphp", "image", self.t("glyphp")),
             ("move", "download", self.mapp_move_label()),
             ("arch", "archive", self.t("arch")),
             ("info", "info", "Informazioni estese" if it else
              "Extended info")]
        if self.is_sys_protected(app["name"]):
            A.append(("noremove", "shield", self.t("sysapp")))
        else:
            prot = self.is_user_protected(app["name"])
            A.append(("protect", "shield",
                      ("Rimuovi protezione" if it else "Unprotect")
                      if prot else
                      ("Proteggi da rimozione" if it else
                       "Protect from removal")))
            if not prot:
                A.append(("remove", "trash", self.t("removeapp")))
        return A

    def detail_do(self, key):
        app = self.mapp_cur
        it = (self.lang == "it")
        if key == "launch":
            self.launch_muos(app)
        elif key == "gov":
            g = self.cfg.setdefault("mapp_gov", {})
            cur = g.get(app["name"], "default")
            g[app["name"]] = GOVS[(GOVS.index(cur) + 1) % len(GOVS)]
            save_cfg(self.cfg)
        elif key == "glyphp":
            self.gp_sel = 0
            self.gp_list = self.gp_scan()
            self.push("glyphpick")
        elif key == "move":
            dest = self.mapp_other_root(app)
            if not dest:
                self.info_lines = self.stub_lines(
                    self.mapp_move_label(),
                    ["nessun'altra SD disponibile" if it else
                     "no other SD available"])
                self.scroll = 0
                self.push("info")
                return

            def go():
                r = self.run_busy(self.mapp_move_label(),
                                  lambda: self.mapp_move(app))
                msg = {"ok": "spostata" if it else "moved",
                       "exists": "esiste gia' a destinazione" if it
                       else "already exists at destination",
                       "err": "errore durante lo spostamento" if it
                       else "error while moving",
                       "no-dest": "nessun'altra SD disponibile" if it
                       else "no other SD available"}.get(r, r)
                self.info_lines = self.stub_lines(app["name"], [msg])
                self.scroll = 0
                self.mapps = self.scan_muos()
                self.mapp_sel = 0
                if self.stack and self.stack[-1] == "mappdetail":
                    self.pop_state()
                self.push("info")
            self.confirm = (self.mapp_move_label() + "?", go)
            self.push("confirm")
        elif key == "arch":
            path = self.run_busy(self.t("mapps_scan"),
                                 lambda: self.archive_app(app))
            self.info_lines = self.stub_lines(
                self.t("arch"),
                [(self.t("arch_ok") + " " + path) if path else
                 ("scrittura fallita: vedi log" if it
                  else "write failed: see log")])
            self.scroll = 0
            self.push("info")
        elif key == "info":
            self.info_lines = self.mapp_info_lines(app)
            self.scroll = 0
            self.push("info")
        elif key == "protect":
            plist = self.cfg.setdefault("mapp_protected", [])
            if app["name"] in plist:
                plist.remove(app["name"])
            else:
                plist.append(app["name"])
            save_cfg(self.cfg)
        elif key == "remove":
            def go():
                import shutil
                try:
                    shutil.rmtree(app["dir"])
                except OSError:
                    pass
                self.mapps = self.scan_muos()
                self.mapp_sel = 0
                if self.stack and self.stack[-1] == "mappdetail":
                    self.pop_state()
            self.confirm = (app["name"], go)
            self.push("confirm")

    def gp_dirs(self):
        return [os.path.join(APP_DIR, "assets", "glyphs"),
                os.path.join(DATA, "glyphs")]

    def gp_scan(self):
        out = []
        for d in self.gp_dirs():
            try:
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith(".png"):
                        out.append(os.path.join(d, f))
            except OSError:
                pass
        return out

    def gp_paths(self):
        app = self.mapp_cur
        tag = self.icon_tag(app["dir"]) or "app"
        g = os.path.join(app["dir"], "glyph")
        return (os.path.join(g, tag + ".png"),
                os.path.join(g, tag + ".orig.png"), g)

    def gp_apply(self, src):
        import shutil
        cur, bak, g = self.gp_paths()
        try:
            os.makedirs(g, exist_ok=True)
            if os.path.exists(cur) and not os.path.exists(bak):
                shutil.copy(cur, bak)      # backup automatico
            pygame.image.save(self.glyph_white22(src), cur)
        except (OSError, pygame.error):
            return
        self.mapp_icons.clear()
        self.mapp_cur["icon"] = self.find_icon(self.mapp_cur["dir"])

    def gp_restore(self):
        import shutil
        cur, bak, _g = self.gp_paths()
        if os.path.exists(bak):
            try:
                shutil.copy(bak, cur)
            except OSError:
                return
            self.mapp_icons.clear()
            self.mapp_cur["icon"] = self.find_icon(self.mapp_cur["dir"])

    def glyph_white22(self, src):
        """Qualsiasi immagine -> 22x22, bianco puro, alpha preservato."""
        img = pygame.image.load(src) if isinstance(src, str) else src
        img = img.convert_alpha()
        if img.get_size() != (22, 22):
            img = pygame.transform.smoothscale(img, (22, 22))
        out = pygame.Surface((22, 22), pygame.SRCALPHA)
        for x in range(22):
            for y in range(22):
                a = img.get_at((x, y))[3]
                if a:
                    out.set_at((x, y), (255, 255, 255, a))
        return out

    def glyph_is_ok(self, path):
        try:
            img = pygame.image.load(path)
        except pygame.error:
            return False
        if img.get_size() != (22, 22):
            return False
        img = img.convert_alpha()
        for x in range(0, 22, 3):
            for y in range(0, 22, 3):
                r, g, b, a = img.get_at((x, y))
                if a and (r, g, b) != (255, 255, 255):
                    return False
        return True

    def glyph_disk_white(self, name):
        s2 = pygame.Surface((22, 22), pygame.SRCALPHA)
        s2.fill((0, 0, 0, 0))
        pygame.draw.rect(s2, (255, 255, 255), (0, 0, 22, 22), 2)
        ch = (name[:1] or "?").upper()
        img = self.f_small.render(ch, True, (255, 255, 255))
        s2.blit(img, ((22 - img.get_width()) // 2,
                      (22 - img.get_height()) // 2))
        return s2

    def preset_glyph(self, name, style, size):
        surf = pygame.Surface((size, size))
        acc = list(ACCENTS.values())[style % len(ACCENTS)]
        surf.fill(INK)
        cut = size // 6
        if style % 5 == 1:      # hazard diagonale
            for d in range(-size, size, 10):
                pygame.draw.line(surf, acc, (d, size), (d + size, 0), 4)
            pygame.draw.rect(surf, INK,
                             (6, 6, size - 12, size - 12))
        elif style % 5 == 2:    # anello
            pygame.draw.circle(surf, acc, (size // 2, size // 2),
                               size // 2 - 4, 4)
        elif style % 5 == 3:    # blocco pieno invertito
            surf.fill(acc)
        pygame.draw.polygon(surf, acc if style % 5 != 3 else INK,
                            [(0, 0), (size - cut, 0), (size - 1, cut),
                             (size - 1, size - 1), (0, size - 1)], 2)
        ch = (name[:1] or "?").upper()
        img = self.f_big.render(ch, True,
                                acc if style % 5 != 3 else INK)
        surf.blit(img, ((size - img.get_width()) // 2,
                        (size - img.get_height()) // 2))
        return surf

    def archive_app(self, app):
        import zipfile
        dests = ([os.environ["VD_ARCHIVE"]]
                 if os.environ.get("VD_ARCHIVE") else []) +             ["/mnt/mmc/ARCHIVE", "/mnt/sdcard/ARCHIVE", DATA]
        for d in dests:
            try:
                os.makedirs(d, exist_ok=True)
                dst = os.path.join(d, app["name"] + "_backup.muxapp")
                with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as z:
                    base = os.path.dirname(app["dir"])
                    for r, _dd, ff in os.walk(app["dir"]):
                        for f in ff:
                            p = os.path.join(r, f)
                            z.write(p, os.path.relpath(p, base))
                return dst
            except OSError:
                continue
        return None

    # ================== SVEGLIE ==================
    def alarms(self):
        return self.cfg.get("alarms") or []

    def alarm_save(self, lst):
        self.cfg["alarms"] = lst
        save_cfg(self.cfg)

    def alarm_toggle(self, idx):
        lst = self.alarms()
        if 0 <= idx < len(lst):
            lst[idx]["enabled"] = not lst[idx].get("enabled", True)
            self.alarm_save(lst)

    def alarm_delete(self, idx):
        lst = self.alarms()
        if 0 <= idx < len(lst):
            lst.pop(idx)
            self.alarm_save(lst)

    def alarm_add_or_edit(self, idx, h, m, sound, label):
        lst = self.alarms()
        ent = {"h": h, "m": m, "sound": sound, "label": label,
               "enabled": True}
        if idx is None:
            lst.append(ent)
        else:
            ent["enabled"] = lst[idx].get("enabled", True)
            lst[idx] = ent
        self.alarm_save(lst)

    def alarm_path(self, sound):
        return os.path.join(APP_DIR, "assets", "alarms",
                            (sound or "classic") + ".wav")

    # ================== METEO (Open-Meteo, no API key) ==================
    def wx_icon_for(self, code):
        return WMO_CODES.get(code, ("w_cloudy", "?", "?"))

    def wx_geocode(self, name):
        import urllib.request
        import urllib.parse
        import json as _j
        base = os.environ.get(
            "VD_WX_GEOCODE_URL",
            "https://geocoding-api.open-meteo.com/v1/search")
        url = (base + "?name=" + urllib.parse.quote(name) +
               "&count=5&language=" +
               ("it" if self.lang == "it" else "en"))
        req = urllib.request.Request(
            url, headers={"User-Agent": "VoidDesk/1.0 Weather"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = _j.loads(r.read().decode())
        out = []
        for res in (data.get("results") or []):
            out.append({"name": res.get("name", name),
                        "admin1": res.get("admin1", ""),
                        "country": res.get("country", ""),
                        "lat": res["latitude"], "lon": res["longitude"]})
        return out

    def wx_fetch(self, city):
        import urllib.request
        import json as _j
        base = os.environ.get("VD_WX_FORECAST_URL",
                              "https://api.open-meteo.com/v1/forecast")
        url = (base + "?latitude=%s"
               "&longitude=%s&current=temperature_2m,weather_code"
               "&hourly=temperature_2m,weather_code"
               "&daily=weather_code,temperature_2m_max,temperature_2m_min"
               "&timezone=auto&forecast_days=7" %
               (city["lat"], city["lon"]))
        req = urllib.request.Request(
            url, headers={"User-Agent": "VoidDesk/1.0 Weather"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return _j.loads(r.read().decode())

    def wx_refresh_all(self):
        for city in (self.cfg.get("weather_cities") or []):
            name = city["name"]
            try:
                self.wx_data[name] = self.wx_fetch(city)
                self.wx_errors.pop(name, None)
            except Exception as e:
                self.wx_errors[name] = str(e)[:80]

    def wx_grid(self, data):
        """Righe = giorni, colonne = segmenti (mattina/pomeriggio/sera
        alle 9/15/21), estratte dall'array orario di Open-Meteo."""
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        temps = hourly.get("temperature_2m") or []
        codes = hourly.get("weather_code") or []
        by_day = {}
        for i, t in enumerate(times):
            if len(t) < 13:
                continue
            day, hour = t[:10], t[11:13]
            if hour in WX_SEGMENTS:
                by_day.setdefault(day, {})[hour] = (
                    temps[i] if i < len(temps) else None,
                    codes[i] if i < len(codes) else None)
        days = sorted(by_day.keys())[:7]
        return [(d, [by_day[d].get(h) for h in WX_SEGMENTS])
                for d in days]

    def wx_add_city(self, res):
        cities = self.cfg.setdefault("weather_cities", [])
        cities.append({"name": res["name"], "admin1": res.get("admin1",
                                                              ""),
                       "country": res.get("country", ""),
                       "lat": res["lat"], "lon": res["lon"]})
        save_cfg(self.cfg)

    def wx_remove_city(self, idx):
        cities = self.cfg.get("weather_cities") or []
        if 0 <= idx < len(cities):
            name = cities[idx]["name"]
            cities.pop(idx)
            save_cfg(self.cfg)
            self.wx_data.pop(name, None)
            self.wx_errors.pop(name, None)

    def check_alarms(self):
        """Chiamata a ogni giro del loop principale: suona finche' sei
        dentro il menu di VoidDesk. Se lanci un gioco o un desktop
        VoidDesk cede il posto e chiude -- una sveglia vera in
        background non e' possibile con questa architettura, e non
        prometto quello che non posso mantenere: qui suona finche'
        resti nei nostri menu, non oltre."""
        if self._alarm_ringing:
            return
        lt = time.localtime()
        cur = (lt.tm_hour, lt.tm_min)
        stamp = "%04d%02d%02d%02d%02d" % lt[:5]
        for i, a in enumerate(self.alarms()):
            if not a.get("enabled", True):
                continue
            if (a["h"], a["m"]) != cur:
                continue
            if self._alarm_fired_min == stamp + "-%d" % i:
                continue
            self._alarm_fired_min = stamp + "-%d" % i
            self._alarm_ringing = a
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init(44100, -16, 2, 1024)
                snd = pygame.mixer.Sound(self.alarm_path(a.get("sound")))
                snd.play(loops=-1)
                self._alarm_snd = snd
            except Exception:
                self._alarm_snd = None
            self.push("alarmring")
            return

    def alarm_dismiss(self):
        if self._alarm_snd:
            try:
                self._alarm_snd.stop()
            except Exception:
                pass
        self._alarm_snd = None
        self._alarm_ringing = None
        if self.stack and self.stack[-1] == "alarmring":
            self.pop_state()

    def calc_press(self, k):
        import math as _m
        if k == "C":
            self.calc_expr = ""
        elif k == "<":
            self.calc_expr = self.calc_expr[:-1]
        elif k == "=":
            e = self.calc_expr.replace("^", "**")
            if re.match(r"^[0-9a-z\.\+\-\*/\(\)\s]*$", e or " "):
                ns = {"sin": _m.sin, "cos": _m.cos, "tan": _m.tan,
                      "log": _m.log10, "ln": _m.log, "sqrt": _m.sqrt,
                      "pi": _m.pi, "e": _m.e,
                      "ans": getattr(self, "calc_ans", 0.0)}
                try:
                    r = eval(e, {"__builtins__": {}}, ns)
                    self.calc_ans = r
                    self.calc_expr = ("%.10g" % r)
                except Exception:
                    self.calc_expr = "ERR"
            else:
                self.calc_expr = "ERR"
        elif k in ("sin", "cos", "tan", "log", "ln", "sqrt"):
            self.calc_expr += k + "("
        elif k:
            if self.calc_expr == "ERR":
                self.calc_expr = ""
            self.calc_expr += k
        if len(self.calc_expr) > 34:
            self.calc_expr = self.calc_expr[:34]

    def diag_lines(self):
        it = (self.lang == "it")
        L = [("sec", "gear", "VOID DIAG")]
        img = os.path.join(DATA, "xfce.img")
        L.append(("kv", "IMMAGINE" if it else "IMAGE",
                  human(os.path.getsize(img)) if os.path.exists(img)
                  else ("assente" if it else "missing"),
                  FG if os.path.exists(img) else NO_R))
        base, extra = self.read_envs()
        L.append(("kv", "AMBIENTI" if it else "ENVS",
                  ("xfce " + " ".join(sorted(extra - {"xfce"}))).strip()
                  if base else ("base non installata" if it
                                else "base not installed"),
                  FG if base else DIM))
        try:
            sw = open("/proc/swaps").read().splitlines()[1:]
            L.append(("kv", "SWAP", sw[0].split()[0] if sw else
                      ("nessuna" if it else "none"),
                      OK_G if sw else DIM))
        except OSError:
            pass
        try:
            gv = open("/sys/devices/system/cpu/cpufreq/policy0/"
                      "scaling_governor").read().strip()
            L.append(("kv", "GOVERNOR", gv, FG))
        except OSError:
            pass
        for name, p in (("voiddesk.log", LOG),
                        ("session", os.path.join(DATA,
                                                 "xfce_session.log"))):
            try:
                bad = [ln for ln in open(p, errors="ignore").read()
                       .splitlines()[-200:]
                       if "FALLITO" in ln or "error" in ln.lower()][-2:]
                for b in bad:
                    L.append(("kv", "!", b[-70:], NO_R))
            except OSError:
                pass
        if len(L) < 6:
            L.append(("kv", "", "tutto in ordine" if it else "all clear",
                      OK_G))
        return L

    def storage_lines(self):
        it = (self.lang == "it")
        L = [("sec", "disk", "MEMORIE" if it else "STORAGE")]
        seen_dev = set()
        try:
            for ln in open("/proc/mounts"):
                dev, mnt = ln.split()[:2]
                if not dev.startswith("/dev/") or dev in seen_dev:
                    continue
                if "/xfce_mnt" in mnt:
                    continue
                try:
                    sv = os.statvfs(mnt)
                    tot = sv.f_blocks * sv.f_frsize
                    fre = sv.f_bavail * sv.f_frsize
                    if tot < 32 * 1024 * 1024:
                        continue
                    seen_dev.add(dev)
                    L.append(("kv", mnt[:18],
                              "%s %s / %s" % (human(fre),
                                              "liberi" if it else "free",
                                              human(tot)),
                              OK_G if fre > tot // 10 else NO_R))
                except OSError:
                    pass
        except OSError:
            pass
        L.append(("sec", "pkg", "COSA OCCUPA" if it else "WHAT FILLS IT"))
        img = os.path.join(DATA, "xfce.img")
        if os.path.exists(img):
            L.append(("kv", "xfce.img", human(os.path.getsize(img)), FG))
        if self.img_total:
            used = self.img_total - (self.img_free or 0)
            L.append(("kv", "  " + ("dentro l'immagine" if it
                                    else "inside the image"),
                      "%s / %s" % (human(used), human(self.img_total)),
                      DIM))
        L.append(("kv", "VoidDesk data",
                  human(self.app_size(DATA)), FG))
        for root in MUOS_APP_ROOTS:
            if os.path.isdir(root):
                L.append(("kv", root.split("/MUOS")[0].split("/")[-1] +
                          " apps", human(self.app_size(root)), FG))
        return L

    def net_lines(self, kind):
        it = (self.lang == "it")
        L = []
        if kind == "wifi":
            L.append(("sec", "wifi", "WIFI"))
            up, ip = "down", ""
            try:
                up = open("/sys/class/net/wlan0/operstate").read().strip()
            except OSError:
                pass
            try:
                out = subprocess.run(["ip", "-4", "addr", "show", "wlan0"],
                                     capture_output=True, text=True,
                                     timeout=3).stdout
                m = re.search(r"inet ([0-9.]+)", out)
                ip = m.group(1) if m else ""
            except Exception:
                pass
            L.append(("kv", "STATO" if it else "STATE", up,
                      OK_G if up == "up" else NO_R))
            if ip:
                L.append(("kv", "IP", ip, FG))
            L.append(("kv", "", "gestione reti: menu WiFi di muOS" if it
                      else "network setup: muOS WiFi menu", DIM))
        else:
            L.append(("sec", "bt", "BLUETOOTH"))
            hci = os.path.isdir("/sys/class/bluetooth")
            devs = []
            try:
                devs = os.listdir("/sys/class/bluetooth")
            except OSError:
                pass
            L.append(("kv", "ADATTATORE" if it else "ADAPTER",
                      ", ".join(devs) if devs else
                      ("assente" if it else "missing"),
                      OK_G if devs else NO_R))
            L.append(("kv", "", "pairing: blueman nel desktop, o muOS" if it
                      else "pairing: blueman in the desktop, or muOS",
                      DIM))
        return L

    def manual_lines(self, idx):
        it = (self.lang == "it")
        key, icon = MANUAL[idx]
        T = {"intro": ("VOID-DESK", [
            ("Extensive Desktop Experience // muOS", FG),
            ("__sec__", "COS'E'" if it else "WHAT IT IS", "info"),
            ("Un ambiente Linux completo (Ubuntu, chroot) dentro la tua "
             "console, con menu, installer e pannello di casa SPDW." if it
             else "A full Linux environment (Ubuntu chroot) inside your "
             "handheld, with SPDW-made menu, installer and panel.", DIM),
            ("Non solo un lanciatore: file manager, FTP, editor, "
             "orologio con sveglie, RSS, meteo, hotspot -- tutto nativo, "
             "nessuna app di terzi richiesta per le funzioni di base."
             if it else "Not just a launcher: file manager, FTP, editor, "
             "clock with alarms, RSS, weather, hotspot -- all native, "
             "no third-party app required for the basics.", DIM),
            ("__sec__", "ARCHITETTURA" if it else "ARCHITECTURE",
             "gear"),
            ("Tutto vive in un'immagine ext4 da 4GB: xfce.img. Un'unica "
             "immagine condivisa, un solo apt, per tutti e tre gli "
             "ambienti desktop." if it else "Everything lives in one "
             "4GB ext4 image: xfce.img. One shared image, one apt, for "
             "all three desktop environments.", DIM),
            ("Quando avvii un ambiente o un'app muOS, VoidDesk cede il "
             "posto e chiude (mai un doppio processo che si contende "
             "schermo e input): e' per questo che il menu e' cosi' "
             "leggero." if it else "Launching an environment or a muOS "
             "app makes VoidDesk hand off and exit (never a double "
             "process fighting over screen and input): that's why the "
             "menu is this light.", DIM),
            ("__sec__", "PRIMO AVVIO" if it else "FIRST LAUNCH", "start"),
            ("START SESSION la prima volta installa la base (~400MB, "
             "serve il WiFi): dopo quello, ogni ambiente si avvia o "
             "installa in pochi secondi." if it else "START SESSION the "
             "first time installs the base (~400MB, needs WiFi): after "
             "that, each environment launches or installs in seconds.",
             DIM)]),
          "sessions": ("START SESSION", [
            ("__sec__", "I TRE AMBIENTI" if it else "THE THREE ENVS",
             "start"),
            ("XFCE // CORE (completo, la megastruttura), IceWM // "
             "TURBO (10MB, velocissimo), LXDE // LIGHT (leggero). A "
             "avvia; se manca, A lo installa." if it else
             "XFCE // CORE (full, the megastructure), IceWM // TURBO "
             "(10MB, blazing fast), LXDE // LIGHT (light). A launches; "
             "if missing, A installs it.", DIM),
            ("Le dipendenze sono condivise: un'immagine, un apt. "
             "Installare un secondo ambiente costa solo i suoi "
             "pacchetti in piu'." if it else "Dependencies are shared: "
             "one image, one apt. Installing a second environment "
             "only costs its extra packages.", DIM),
            ("__sec__", "IL RIQUADRO" if it else "THE BOX", "disk"),
            ("Ogni ambiente ha sagoma e decorazione proprie: bulloni "
             "per CORE, strisce hazard per TURBO, fori perforati per "
             "LIGHT." if it else "Each environment has its own "
             "silhouette and decoration: rivets for CORE, hazard "
             "stripes for TURBO, perforated holes for LIGHT.", DIM),
            ("Il bollino a destra dice tutto a colpo d'occhio: ▶ "
             "ATTIVO (verde), ✓ Installed (verde), ✗ Not installed "
             "(rosso). In fondo, l'ultimo controllo aggiornamenti "
             "dell'immagine." if it else "The badge on the right says "
             "it all at a glance: ▶ ACTIVE (green), ✓ Installed "
             "(green), ✗ Not installed (red). At the bottom, the "
             "image's last update check.", DIM),
            ("__sec__", "TASTO X: DETTAGLIO AMBIENTE" if it else
             "X KEY: ENVIRONMENT DETAIL", "gauge"),
            ("Sigla d'avvio on/off solo per questo ambiente, ripara/"
             "reinstalla pacchetti (apt e' idempotente, sicuro anche "
             "se gia' installati), log di sessione diretto, controlla "
             "e aggiorna il sistema." if it else "Boot animation on/off "
             "just for this environment, repair/reinstall packages "
             "(apt is idempotent, safe even if already installed), "
             "direct session log, check and update the system.", DIM),
            ("Rimuovi ambiente: solo IceWM/LXDE, mai XFCE che e' la "
             "base condivisa. Libera spazio senza toccare gli altri."
             if it else "Remove environment: only IceWM/LXDE, never "
             "XFCE which is the shared base. Frees space without "
             "touching the others.", DIM)]),
          "forge": ("FORGE", [
            ("__sec__", "APPS INSTALLER", "pkg"),
            ("L1 e' la tab installer, R1 la tab uninstaller: colori "
             "invertiti (complementare al tema), liste speculari. X "
             "marca, Y marca/smarca tutti, A esegue, SELECT riscansiona."
             if it else "L1 is the installer tab, R1 the uninstaller: "
             "inverted colours (theme complement), mirrored lists. X "
             "marks, Y marks/unmarks all, A runs, SELECT rescans.",
             DIM),
            ("In modalita' rimozione i pacchetti non installati sono "
             "grigi e non selezionabili: non si puo' disinstallare cio' "
             "che non c'e'." if it else "In removal mode, packages not "
             "installed show grey and aren't selectable: you can't "
             "uninstall what isn't there.", DIM),
            ("Reinstallare un pacchetto gia' presente e' sicuro: apt "
             "e' idempotente." if it else "Reinstalling an already "
             "present package is safe: apt is idempotent.", DIM),
            ("__sec__", "AVVIO AL BOOT" if it else "STARTUP APPS",
             "power"),
            ("Solo vere applicazioni compaiono in elenco: mai pezzi "
             "interni della sessione (pannello, demoni)." if it else
             "Only real applications show in the list: never internal "
             "session pieces (panel, daemons).", DIM),
            ("__sec__", "AGGIORNA SISTEMA" if it else "UPDATE SYSTEM",
             "download"),
            ("apt update + upgrade nel chroot, con barra di progresso "
             "reale. A fine corsa scrive un marcatore con data e ora: "
             "e' quello che il riquadro di START SESSION mostra come "
             "'ultimo controllo'." if it else "apt update + upgrade in "
             "the chroot, with a real progress bar. On completion it "
             "writes a timestamp marker: that's what the START SESSION "
             "box shows as 'last checked'.", DIM),
            ("__sec__", "VOID-DESK UPDATE", "forge"),
            ("Diverso dal precedente: qui si aggiorna VoidDesk stesso, "
             "non il desktop. Controlla l'ultima release su GitHub, "
             "confronta la versione, scarica e sostituisce solo se il "
             "pacchetto e' valido -- data/ (le tue configurazioni) non "
             "viene mai toccata, nemmeno se il pacchetto scaricato ne "
             "contenesse una." if it else "Different from the one "
             "above: this updates VoidDesk itself, not the desktop. "
             "Checks the latest GitHub release, compares the version, "
             "downloads and replaces only if the package is valid -- "
             "data/ (your configuration) is never touched, even if the "
             "downloaded package contained one.", DIM),
            ("Serve riavviare l'app perche' la nuova versione prenda "
             "effetto." if it else "You'll need to restart the app for "
             "the new version to take effect.", DIM)]),
          "mapps": ("MUOS APPS", [
            ("__sec__", "IL GESTORE" if it else "THE MANAGER", "window"),
            ("Un gestore multifunzione per le app di muOS, non solo un "
             "lanciatore: le trovi tutte (SD1+SD2), le avvii a schermo "
             "pieno, poi torni qui." if it else
             "A full multi-function manager for muOS apps, not just a "
             "launcher: every app (SD1+SD2), launched full-screen, then "
             "back here.", DIM),
            ("R1 sistema le glyph secondo lo standard # ICON: di muOS "
             "su tutte le app in un colpo solo." if it else "R1 fixes "
             "glyphs per muOS # ICON: standard on every app in one "
             "pass.", DIM),
            ("__sec__", "TASTO X: OPZIONI" if it else "X KEY: OPTIONS",
             "gauge"),
            ("Governor per-app (impostato prima del lancio, ripristinato "
             "dopo), sposta tra SD1/SD2, ricrea il pacchetto .muxapp in "
             "ARCHIVE, informazioni estese (percorso, data "
             "installazione, tag HELP/ICON/GRID)." if it else
             "Per-app governor (set before launch, restored after), "
             "move between SD1/SD2, rebuild the .muxapp package into "
             "ARCHIVE, extended info (path, install date, HELP/ICON/"
             "GRID tags).", DIM),
            ("Proteggi da rimozione: lista tua, in aggiunta a quella "
             "di sistema. Un'app protetta nasconde 'rimuovi' dalla "
             "lista." if it else "Protect from removal: your own list, "
             "on top of the system one. A protected app hides 'remove' "
             "from the list.", DIM),
            ("Rimuovere un'app da qui non e' possibile dal menu muOS "
             "originale: le app di sistema (PortMaster, RetroArch, "
             "PPSSPP...) restano comunque protette per sempre." if it
             else "Removing an app here isn't possible from the native "
             "muOS menu: system apps (PortMaster, RetroArch, PPSSPP...) "
             "stay protected forever either way.", DIM),
            ("__sec__", "IL SISTEMA GLYPH" if it else "THE GLYPH SYSTEM",
             "image"),
            ("Cambia glyph apre una griglia stile character-select con "
             "26 preset SPDW, tutti 22x22 bianco puro (lo standard che "
             "muOS si aspetta)." if it else "Change Glyph opens a "
             "character-select style grid with 26 SPDW presets, all "
             "22x22 pure white (the standard muOS expects).", DIM),
            ("Il primo cambio fa sempre un backup automatico "
             "dell'originale: X lo ripristina in qualsiasi momento."
             if it else "The first change always makes an automatic "
             "backup of the original: X restores it any time.", DIM),
            ("Aggiungi le tue: butta i PNG in assets/glyphs, compaiono "
             "nella griglia. Se non sono a norma, viene chiesta "
             "conferma prima di convertirli in 22x22 bianco." if it
             else "Add your own: drop PNGs in assets/glyphs, they show "
             "up in the grid. If they don't conform, you're asked to "
             "confirm before converting to 22x22 white.", DIM)]),
          "workshop": ("WORKSHOP", [
            ("__sec__", "DIAGNOSI E STATISTICHE" if it else
             "DIAGNOSTICS & STATS", "monitor"),
            ("In cima alla schermata, tre widget live (CPU/RAM/TEMP) "
             "sempre aggiornati -- un colpo d'occhio prima ancora di "
             "aprire una voce." if it else "At the top of the screen, "
             "three live widgets (CPU/RAM/TEMP) always up to date -- "
             "a glance before even opening an entry.", DIM),
            ("Void Stats e Void Diag: il quadro completo e la salute "
             "di immagine e sessioni (swap, governor, ultimi errori "
             "pescati dai log)." if it else "Void Stats and Void Diag: "
             "the full picture and the health of image and sessions "
             "(swap, governor, latest errors fished from the logs).",
             DIM),
            ("Memorie: partizioni reali, spazio libero, cosa occupa "
             "l'immagine e i dati dell'app." if it else "Storage: real "
             "partitions, free space, what fills the image and the "
             "app's data.", DIM),
            ("Void Monitor: cinque schede (L1/R1) -- Dashboard con "
             "quattro widget diversi a colpo d'occhio, poi CPU/RAM/TEMP/"
             "NET in dettaglio con minimo, media, massimo." if it else
             "Void Monitor: five tabs (L1/R1) -- Dashboard with four "
             "distinct widgets at a glance, then CPU/RAM/TEMP/NET in "
             "detail with min, average, max.", DIM),
            ("__sec__", "VOID BOOST", "gauge"),
            ("Swap (zram o file) e governor CPU, due interruttori "
             "separati: puoi tenere il boost CPU e spegnere solo lo "
             "swap, o viceversa." if it else "Swap (zram or file) and "
             "CPU governor, two separate switches: keep the CPU boost "
             "and turn off just the swap, or the other way round.",
             DIM),
            ("__sec__", "REGISTRO LOG" if it else "LOG REGISTRY", "doc"),
            ("Ogni diario, raggruppato per area: VoidDesk, sessioni "
             "per ambiente (xfce/icewm/lxde separati), installer, "
             "media." if it else "Every diary, grouped by area: "
             "VoidDesk, per-environment sessions (xfce/icewm/lxde "
             "separate), installer, media.", DIM),
            ("R1 nel visualizzatore attiva la modalita' LIVE: il file "
             "si ricarica da solo, perfetto per guardare una sessione "
             "mentre succede. UP la mette in pausa." if it else "R1 in "
             "the viewer turns on LIVE mode: the file reloads itself, "
             "perfect for watching a session as it happens. UP pauses "
             "it.", DIM),
            ("__sec__", "BACKUP IMMAGINE" if it else "IMAGE BACKUP",
             "archive"),
            ("Backup compresso di xfce.img in ARCHIVE con percentuale "
             "live, ripristino con conferma (scrive su file temporaneo, "
             "sostituisce solo a successo)." if it else "Compressed "
             "backup of xfce.img into ARCHIVE with a live percentage, "
             "restore with confirmation (writes to a temp file, swaps "
             "in only on success).", DIM),
            ("Serve l'immagine smontata: se un desktop e' aperto da "
             "qualche parte, VoidDesk te lo dice invece di rischiare."
             if it else "Needs the image unmounted: if a desktop is "
             "open somewhere, VoidDesk tells you instead of risking "
             "it.", DIM)]),
          "uplink": ("UPLINK", [
            ("__sec__", "LINGUA E TASTIERE" if it else
             "LANGUAGE & KEYBOARDS", "lang"),
            ("Lingua desktop (vale solo per gli ambienti, non per "
             "l'app) e layout tastiera, sia a schermo (matchbox) sia "
             "fisica (se colleghi una USB)." if it else "Desktop "
             "language (only for the environments, not the app) and "
             "keyboard layout, both on-screen (matchbox) and physical "
             "(if you plug in a USB one).", DIM),
            ("__sec__", "WIFI", "wifi"),
            ("Interruttore acceso/spento della radio, scansione, "
             "connetti con tastiera per la password. LED verde+IP "
             "quando online, rosso+OFFLINE quando no." if it else "Radio "
             "on/off switch, scan, join with on-screen keyboard for "
             "the password. Green LED+IP when online, red+OFFLINE when "
             "not.", DIM),
            ("Rilevamento e riconnessione doppi: se wpa_cli non "
             "risponde, si ripiega su iw e su una riscrittura diretta "
             "della configurazione." if it else "Double detection and "
             "reconnection: if wpa_cli doesn't answer, it falls back "
             "to iw and a direct config rewrite.", DIM),
            ("__sec__", "BLUETOOTH", "bt"),
            ("Stesso schema: interruttore vero (accende/spegne la "
             "radio fisica), scansione, pair+trust+connect in un tocco, "
             "pannello con le info del dispositivo." if it else "Same "
             "pattern: a real switch (turns the physical radio on/"
             "off), scan, pair+trust+connect in one tap, device info "
             "panel.", DIM),
            ("__sec__", "HOTSPOT", "uplink"),
            ("Nativo, scritto da zero (hostapd+dnsmasq): sempre pronto, "
             "nessuna app esterna richiesta. 2.4 o 5GHz, interruttore "
             "diretto con Y." if it else "Native, built from scratch "
             "(hostapd+dnsmasq): always ready, no external app "
             "required. 2.4 or 5GHz, direct switch with Y.", DIM),
            ("Sceglie da solo l'interfaccia giusta: una seconda radio "
             "se il device ce l'ha, altrimenti riusa la principale."
             if it else "Picks the right interface on its own: a "
             "second radio if the device has one, otherwise reuses "
             "the main one.", DIM)]),
          "toolbox": ("TOOLBOX", [
            ("__sec__", "PRODUTTIVITA'" if it else "PRODUCTIVITY",
             "calc"),
            ("Calcolatrice scientifica nativa (sin/cos/log/ans)."
             if it else "Native scientific calculator (sin/cos/log/"
             "ans).", DIM),
            ("Clock: digitale in 3 stili o analogico con lancette vere, "
             "X apre data/ora/fuso, A le sveglie con suono a scelta -- "
             "suonano finche' resti nei menu di VoidDesk, non oltre "
             "(lanciare un gioco cede il posto e chiude l'app)." if it
             else "Clock: digital in 3 styles or analog with real "
             "hands, X opens date/time/zone, A opens alarms with a "
             "sound of your choice -- they ring while you stay in "
             "VoidDesk's own menus, not beyond (launching a game hands "
             "off and exits the app).", DIM),
            ("Calendario (vista mese/settimana/giorno, priorita' "
             "colorate) e Note a bacheca stile post-it, con puntine "
             "per fissare le preferite in cima." if it else "Calendar "
             "(month/week/day view, coloured priorities) and a "
             "post-it style Notes board, with pins to keep favourites "
             "on top.", DIM),
            ("__sec__", "RETE E FILE" if it else "NETWORK & FILES",
             "folder"),
            ("VOID FILES: file manager completo, clipboard, "
             "rinomina, elimina con conferma, visualizzatore immagini, "
             "esegue script .sh/.py." if it else "VOID FILES: full "
             "file manager, clipboard, rename, delete with "
             "confirmation, image viewer, runs .sh/.py scripts.", DIM),
            ("VOID FTP: profili salvati, scarica con percentuale "
             "live, carica scegliendo il file dal file manager."
             if it else "VOID FTP: saved profiles, download with a "
             "live percentage, upload by picking the file from the "
             "file manager.", DIM),
            ("Syncthing (config muOS-first) e Tailscale (stesso "
             "socket del servizio muOS: peer, ping, Taildrop, exit "
             "node)." if it else "Syncthing (muOS-first config) and "
             "Tailscale (same socket as the muOS service: peers, ping, "
             "Taildrop, exit node).", DIM),
            ("__sec__", "SVILUPPO" if it else "DEVELOPMENT", "terminal"),
            ("Terminale con tastiera a schermo. Console Python "
             "interattiva: namespace persistente, comandi shell col "
             "prefisso !, Y apre ed esegue un file .py dallo storage."
             if it else "Terminal with on-screen keys. Interactive "
             "Python console: persistent namespace, shell commands "
             "with the ! prefix, Y opens and runs a .py file from "
             "storage.", DIM),
            ("__sec__", "INFORMAZIONE" if it else "INFORMATION",
             "globe"),
            ("RSS Reader: libreria pronta ENG+ITA per categoria (news, "
             "tech, linux, gaming, retrogaming, anime), colorata per "
             "categoria; Y sceglie i feed attivi, aggiungi i tuoi in "
             "rss_custom.json." if it else "RSS Reader: ready-made "
             "ENG+ITA library by category (news, tech, linux, gaming, "
             "retrogaming, anime), colour-coded; Y picks active feeds, "
             "add your own in rss_custom.json.", DIM),
            ("Meteo: cerca la citta' (con disambiguazione se il nome "
             "e' ambiguo), previsione attuale piu' tabella settimanale "
             "(7 giorni x mattina/pomeriggio/sera); dati Open-Meteo, "
             "nessuna chiave richiesta." if it else "Weather: search a "
             "city (with disambiguation if the name is ambiguous), "
             "current conditions plus a weekly table (7 days x "
             "morning/afternoon/evening); Open-Meteo data, no key "
             "required.", DIM)]),
          "live": ("PANNELLO LIVE" if it else "LIVE PANEL", [
            ("__sec__", "COME SI APRE" if it else "HOW IT OPENS",
             "panel"),
            ("START+SELECT insieme, in qualsiasi momento dentro un "
             "desktop: il pannello compare sopra, la sessione resta "
             "esattamente com'era sotto." if it else "START+SELECT "
             "together, any time inside a desktop: the panel appears "
             "on top, the session stays exactly as it was underneath.",
             DIM),
            ("__sec__", "LE VOCI" if it else "THE ITEMS", "task"),
            ("Torna al desktop, diagnosi sistema, risoluzione problemi "
             "rapida, volume, luminosita', tastiera virtuale, task "
             "manager, riavvia o chiudi la sessione." if it else "Back "
             "to the desktop, system check, quick troubleshooting, "
             "volume, brightness, virtual keyboard, task manager, "
             "restart or close the session.", DIM),
            ("__sec__", "ADATTIVO PER AMBIENTE" if it else
             "ADAPTIVE PER ENVIRONMENT", "uplink"),
            ("Colore, nome ('Torna a IceWM', non solo XFCE) e comandi "
             "di riparazione seguono davvero l'ambiente attivo: ognuno "
             "usa i propri strumenti (xfwm4/icewm/openbox)." if it else
             "Colour, name ('Back to IceWM', not just XFCE) and repair "
             "commands genuinely follow the active environment: each "
             "uses its own tools (xfwm4/icewm/openbox).", DIM)]),
          "trouble": ("SE QUALCOSA VA STORTO" if it else
                      "IF SOMETHING BREAKS", [
            ("__sec__", "I LOG DICONO LA VERITA'" if it else
             "LOGS TELL THE TRUTH", "doc"),
            ("WORKSHOP > Registro log: ogni area ha il suo diario. La "
             "modalita' LIVE (R1) mostra un problema mentre succede."
             if it else "WORKSHOP > Log registry: every area has its "
             "own diary. LIVE mode (R1) shows a problem as it "
             "happens.", DIM),
            ("__sec__", "PROBLEMI COMUNI" if it else "COMMON ISSUES",
             "gear"),
            ("Spazio finito? Pulisci cache apt in WORKSHOP, o rimuovi "
             "software da FORGE che non usi." if it else "Out of "
             "space? Clean apt cache in WORKSHOP, or remove software "
             "you don't use from FORGE.", DIM),
            ("Un ambiente non parte? Il launcher ripiega su XFCE e lo "
             "scrive nel log; da START SESSION prova 'ripara pacchetti' "
             "su quell'ambiente." if it else "An environment won't "
             "start? The launcher falls back to XFCE and logs it; from "
             "START SESSION try 'repair packages' on that environment.",
             DIM),
            ("WiFi/Bluetooth che non si aggiornano? Esci e rientra nel "
             "pannello: se il problema persiste, controlla il log "
             "specifico." if it else "WiFi/Bluetooth not refreshing? "
             "Leave and re-enter the panel: if it persists, check the "
             "specific log.", DIM),
            ("__sec__", "I LIMITI ONESTI" if it else "HONEST LIMITS",
             "info"),
            ("Le sveglie di Clock suonano solo mentre stai nei menu di "
             "VoidDesk: lanciare un gioco o un desktop chiude l'app "
             "(e' il patto di consegna pulito che tiene tutto "
             "leggero)." if it else "Clock alarms only ring while "
             "you're inside VoidDesk's own menus: launching a game or "
             "a desktop exits the app (that's the clean hand-off deal "
             "that keeps everything light).", DIM)])}
        title, rows = T[key]
        L = [("sec", icon, title)]
        for row in rows:
            if row[0] == "__sec__":
                L.append(("sec", row[2] if len(row) > 2 else icon,
                          row[1]))
            else:
                txt, col = row
                L.append(("kv", "", txt, col))
        return L

    def stub_lines(self, title, body):
        L = [("sec", "info", title)]
        for b in body:
            L.append(("kv", "", b, DIM))
        return L

    def env_glyph(self, env, x, y, sc, col):
        m = ENV_GLYPHS.get(env)
        if not m:
            return
        for ry in range(16):
            bits = m[ry]
            if not bits:
                continue
            for rx in range(16):
                if bits & (1 << (15 - rx)):
                    pygame.draw.rect(
                        self.surface, col,
                        (x + rx * sc, y + ry * sc, sc - 1, sc - 1))

    # -------------------------------------------------- app muOS in Void
    def scan_muos(self):
        """Censisce MUOS/application su SD1 e SD2: nome, script, icona."""
        apps = []
        me = os.path.realpath(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        for ri, root in enumerate(MUOS_APP_ROOTS):
            try:
                names = sorted(os.listdir(root))
            except OSError:
                continue
            for n in names:
                d = os.path.join(root, n)
                sh_ = os.path.join(d, "mux_launch.sh")
                if not os.path.isfile(sh_):
                    continue
                if (os.path.realpath(d) == me
                        or n.lower().startswith("voiddesk")):
                    continue
                apps.append({"name": n, "dir": d, "script": sh_,
                             "sd": "SD%d" % (ri + 1),
                             "icon": self.find_icon(d)})
        return apps

    def icon_tag(self, d):
        """Legge '# ICON: nome' dal mux_launch.sh dell'app (convenzione
        muOS: la glyph si chiama <nome>.png dentro glyph/)."""
        try:
            head = open(os.path.join(d, "mux_launch.sh")).read(600)
        except OSError:
            return None
        for ln in head.splitlines():
            if ln.strip().upper().startswith("# ICON:"):
                tag = ln.split(":", 1)[1].strip()
                return tag or None
        return None

    def find_icon(self, d):
        cand = []
        g = os.path.join(d, "glyph")
        tag = self.icon_tag(d)
        if tag and os.path.isfile(os.path.join(g, tag + ".png")):
            return os.path.join(g, tag + ".png")
        try:
            cand += [os.path.join(g, f) for f in sorted(os.listdir(g))
                     if f.lower().endswith(".png")]
        except OSError:
            pass
        for f in ("icon.png", "cover.png", "preview.png", "logo.png"):
            p = os.path.join(d, f)
            if os.path.isfile(p):
                cand.append(p)
        return cand[0] if cand else None

    def mapp_icon(self, app, size=36):
        """Icona caricata e scalata, con cache; placeholder SPDW se manca."""
        key = (app["icon"] or app["name"], size)
        if key in self.mapp_icons:
            return self.mapp_icons[key]
        surf = None
        if app["icon"]:
            try:
                img = pygame.image.load(app["icon"])
                surf = pygame.transform.smoothscale(img, (size, size))
            except pygame.error:
                surf = None
        if surf is None:
            surf = self.mapp_placeholder(app["name"], size)
        self.mapp_icons[key] = surf
        return surf

    def mapp_placeholder(self, name, size):
        surf = pygame.Surface((size, size))
        surf.fill(INK)
        cut = max(4, size // 6)
        pygame.draw.polygon(surf, self.accent,
                            [(0, 0), (size - cut, 0), (size - 1, cut),
                             (size - 1, size - 1), (0, size - 1)], 1)
        ch = (name[:1] or "?").upper()
        f = self.f_med if size >= 30 else self.f_small
        img = f.render(ch, True, self.accent)
        surf.blit(img, ((size - img.get_width()) // 2,
                        (size - img.get_height()) // 2))
        return surf

    def normalize_glyphs(self):
        """Convenzione muOS completa: glyph/<nome>.png dove <nome> e' il
        tag '# ICON:' nello script. Se il tag manca, lo aggiungiamo (una
        riga di commento dopo lo shebang); l'icona trovata viene copiata
        col nome giusto, e a chi non ha nulla generiamo la glyph SPDW."""
        import re as _re
        import shutil
        for app in self.mapps:
            d = app["dir"]
            g = os.path.join(d, "glyph")
            tag = self.icon_tag(d)
            if not tag:
                tag = _re.sub(r"[^a-z0-9]", "", app["name"].lower()) or "app"
                try:
                    sh_ = os.path.join(d, "mux_launch.sh")
                    txt = open(sh_).read()
                    lines = txt.split("\n")
                    ins = 1 if lines and lines[0].startswith("#!") else 0
                    lines.insert(ins, "# ICON: " + tag)
                    open(sh_, "w").write("\n".join(lines))
                except OSError:
                    pass
            dst = os.path.join(g, tag + ".png")
            try:
                if os.path.exists(dst):
                    continue
                os.makedirs(g, exist_ok=True)
                if app["icon"]:
                    shutil.copy(app["icon"], dst)
                else:
                    pygame.image.save(
                        self.glyph_disk_white(app["name"]), dst)
            except (OSError, pygame.error):
                pass
        self.mapp_icons.clear()
        self.mapps = self.scan_muos()

    def env_box_motif(self, env, x, y, w, h, col):
        """Decorazione strutturale distintiva: bulloni sul bordo
        sinistro per CORE (megastruttura), strisce hazard sul bordo
        destro per TURBO (velocita'), fori perforati in alto per
        LIGHT (leggerezza)."""
        if env == "xfce":
            ry = y + 16
            while ry < y + h - 14:
                pygame.draw.rect(self.surface, col, (x + 5, ry, 5, 5))
                pygame.draw.rect(self.surface, INK, (x + 6, ry + 1, 3, 3))
                ry += 22
        elif env == "icewm":
            for k in range(5):
                xx = x + w - 34 + (k % 2) * 5
                yy = y + 12 + k * 15
                pygame.draw.line(self.surface, col, (xx, yy),
                                 (xx + 14, yy + 7), 2)
        else:
            rx = x + 26
            while rx < x + w - 20:
                pygame.draw.circle(self.surface, col, (rx, y + 5), 2)
                rx += 15

    def env_icon_frame(self, env, x, y, size, col, fill):
        """Cornice dell'icona: piastra a doppio bordo per CORE,
        parallelogramma sbrancato per TURBO, cerchio morbido per
        LIGHT."""
        if env == "xfce":
            cut = 9
            pts = [(x, y), (x + size - cut, y), (x + size, y + cut),
                   (x + size, y + size), (x, y + size)]
            pygame.draw.polygon(self.surface, fill, pts)
            pygame.draw.polygon(self.surface, col, pts, 2)
            pygame.draw.rect(self.surface, col,
                             (x + 4, y + 4, size - 8, size - 8), 1)
        elif env == "icewm":
            sk = 12
            pts = [(x + sk, y), (x + size, y),
                   (x + size - sk, y + size), (x, y + size)]
            pygame.draw.polygon(self.surface, fill, pts)
            pygame.draw.polygon(self.surface, col, pts, 2)
        else:
            cx, cy, r = x + size // 2, y + size // 2, size // 2
            pygame.draw.circle(self.surface, fill, (cx, cy), r)
            pygame.draw.circle(self.surface, col, (cx, cy), r, 2)

    def env_name_frame(self, env, x, y, w, h, col, fill):
        """Cornice del nome ambiente, agganciata all'icona: stessa
        famiglia di taglio dell'icon-frame, per continuita' visiva."""
        if env == "xfce":
            cut = 14
            pts = [(x, y), (x + w - cut, y), (x + w, y + cut),
                   (x + w, y + h), (x, y + h)]
        elif env == "icewm":
            sk = 14
            pts = [(x, y), (x + w, y), (x + w - sk, y + h), (x, y + h)]
        else:
            cut = 10
            pts = [(x, y), (x + w - cut, y), (x + w, y + cut),
                   (x + w, y + h - cut), (x + w - cut, y + h), (x, y + h)]
        pygame.draw.polygon(self.surface, fill, pts)
        pygame.draw.polygon(self.surface, col, pts, 2)

    def env_color(self, env):
        if env == "xfce":
            return self.accent
        th = self.cfg.get("theme", "ambra")
        return ENV_SECONDARY.get(th, ENV_SECONDARY["ambra"]).get(
            env, self.accent)

    def read_envs(self):
        base = os.path.exists(os.path.join(DATA, ".xfce_ready"))
        extra = set()
        try:
            extra = set(open(os.path.join(DATA, ".envs")).read().split())
        except OSError:
            pass
        return base, extra

    def env_bootanim_on(self, env):
        return (self.cfg.get("env_bootanim") or {}).get(env, True)

    def env_bootanim_toggle(self, env):
        d = self.cfg.setdefault("env_bootanim", {})
        d[env] = not self.env_bootanim_on(env)
        save_cfg(self.cfg)

    def img_state(self):
        """Legge il marcatore lasciato da xfce_update.py: quando e'
        stato controllato l'ultima volta, se risulta aggiornato."""
        try:
            import json as _j
            return _j.load(open(os.path.join(DATA, ".apt_state.json")))
        except (OSError, ValueError):
            return None

    def img_state_line(self):
        it = (self.lang == "it")
        st = self.img_state()
        if not st or not st.get("ts"):
            return self.t("img_never"), FAINT
        ts = st["ts"]
        stamp = time.strftime("%d/%m/%Y", time.localtime(ts))
        stale = (time.time() - ts) > 30 * 86400
        txt = "%s %s" % (self.t("img_updated"), stamp)
        if stale:
            txt += "  ·  " + self.t("img_stale")
        return txt, (self.accent if stale else OK_G)

    def env_repair(self, env):
        """Reinstalla i pacchetti dell'ambiente: apt e' idempotente,
        stessa strada gia' collaudata dell'installazione normale."""
        _key, _lbl, pkgs = next(e for e in ENVS if e[0] == env)
        up = env.upper()
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, ".install_pkg"), "w") as f:
            f.write("%s\n%s\n" % (up, pkgs))
        self.handoff(("RIPARO %s..." if self.lang == "it" else
                      "REPAIRING %s...") % up)
        self.exit_code = EXIT_PKG_INSTALL
        self.running = False

    def env_remove(self, env):
        """Rimuove i pacchetti extra di un ambiente (mai xfce: e' la
        base condivisa). Stessa strada gia' collaudata usata dal
        catalogo FORGE per i singoli pacchetti; '.envs' si autocorregge
        al prossimo scan_status() controllando i binari reali."""
        _key, _lbl, pkgs = next(e for e in ENVS if e[0] == env)
        up = env.upper()
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, ".install_pkg"), "w") as f:
            f.write("%s\n%s\n" % (up, pkgs))
        self.handoff(("RIMUOVO %s..." if self.lang == "it" else
                      "REMOVING %s...") % up)
        self.exit_code = EXIT_PKG_REMOVE
        self.running = False

    def env_detail_actions(self, env, base, inst):
        it = (self.lang == "it")
        A = []
        if not base or not inst:
            A.append(("launch", "start", self.t("sess_a").upper()))
            return A
        A.append(("launch", "start", ("AVVIA" if it else "LAUNCH")))
        onoff = self.t("yes") if self.env_bootanim_on(env) else \
            self.t("no")
        A.append(("boot", "start", self.t("ed_boot") + "  ·  " + onoff))
        A.append(("repair", "gear", self.t("ed_repair")))
        A.append(("log", "doc", self.t("ed_log")))
        A.append(("update", "download", self.t("ed_update")))
        if env != "xfce":
            A.append(("remove", "trash", self.t("ed_remove")))
        return A

    def env_detail_do(self, env, key):
        it = (self.lang == "it")
        base, extra = self.read_envs()
        inst = base and (env == "xfce" or env in extra)
        if key == "launch":
            self.cfg["desk_env"] = env
            save_cfg(self.cfg)
            _k, _l, pkgs = next(e for e in ENVS if e[0] == env)
            up = env.upper()
            if not base:
                self.handoff(self.t("ho_inst"))
                self.exit_code = EXIT_XFCE_INSTALL
            elif inst:
                self.handoff(("AVVIO DESKTOP %s..." if it else
                              "STARTING %s DESKTOP...") % up)
                self.exit_code = EXIT_XFCE_LAUNCH
            else:
                os.makedirs(DATA, exist_ok=True)
                with open(os.path.join(DATA, ".install_pkg"), "w") as f:
                    f.write("%s\n%s\n" % (up, pkgs))
                self.handoff(("INSTALLO %s..." if it else
                              "INSTALLING %s...") % up)
                self.exit_code = EXIT_PKG_INSTALL
            self.running = False
        elif key == "boot":
            self.env_bootanim_toggle(env)
        elif key == "repair":
            self.env_repair(env)
        elif key == "log":
            p = os.path.join(DATA, "session_%s.log" % env)
            self.load_log(p)
            self.push("viewer")
        elif key == "update":
            self.comp_action("update")
        elif key == "remove":
            def go():
                self.env_remove(env)
            self.confirm = (self.t("ed_confirm_rm"), go)
            self.push("confirm")

    def backdrop(self):
        t = time.time()
        dx = int((t * 9) % W)
        dy = int((t * 6) % H)
        for ox in (-dx, W - dx):
            for oy in (dy, dy - H):
                self.surface.blit(self.bg_img, (ox, oy))
        self._backdrop_corners(t)

    def _backdrop_corners(self, t):
        """I quattro accenti animati agli angoli, fissi rispetto allo
        schermo (non scorrono col fondo): ingranaggio in basso a sx,
        rombo in basso a dx, griglia in alto a dx, linea curva in alto
        a sx. Sobri apposta -- decorano, non distraggono."""
        sec = theme_secondary(self.accent)
        # ingranaggio, basso sinistra
        ggx, ggy, ggr = 22, H - 24, 14
        gang = t * 1.1
        for k in range(8):
            a = gang + k * math.pi / 4
            x1 = ggx + int((ggr - 4) * math.cos(a))
            y1 = ggy + int((ggr - 4) * math.sin(a))
            x2 = ggx + int(ggr * math.cos(a))
            y2 = ggy + int(ggr * math.sin(a))
            pygame.draw.line(self.surface, sec, (x1, y1), (x2, y2), 2)
        pygame.draw.circle(self.surface, sec, (ggx, ggy), ggr - 6, 1)
        # rombo, basso destra: pulsa di dimensione
        rx, ry = W - 24, H - 26
        rs = 10 + int(4 * abs(math.sin(t * 1.6)))
        pygame.draw.polygon(self.surface, sec, [
            (rx, ry - rs), (rx + rs, ry), (rx, ry + rs), (rx - rs, ry)], 2)
        # griglia, alto destra: una riga che la percorre in loop
        gx0, gy0, gw, gh = W - 58, 12, 46, 26
        for i in range(4):
            lx = gx0 + i * (gw // 3)
            pygame.draw.line(self.surface, sec, (lx, gy0),
                             (lx, gy0 + gh), 1)
        for j in range(3):
            ly = gy0 + j * (gh // 2)
            pygame.draw.line(self.surface, sec, (gx0, ly),
                             (gx0 + gw, ly), 1)
        sweep = gy0 + int((gh - 2) * ((math.sin(t * 1.3) + 1) / 2))
        pygame.draw.line(self.surface, self.accent, (gx0, sweep),
                         (gx0 + gw, sweep), 2)
        # linea curva, alto sinistra: una scintilla la percorre
        cx0, cy0, cx1, cy1 = 8, 10, 56, 30
        ccx, ccy = 20, 34
        steps = 14
        prev = (cx0, cy0)
        for s in range(1, steps + 1):
            tt = s / float(steps)
            bx = (1-tt)**2*cx0 + 2*(1-tt)*tt*ccx + tt**2*cx1
            by = (1-tt)**2*cy0 + 2*(1-tt)*tt*ccy + tt**2*cy1
            pygame.draw.line(self.surface, sec, prev, (bx, by), 1)
            prev = (bx, by)
        pk = (t * 0.6) % 1.0
        px = (1-pk)**2*cx0 + 2*(1-pk)*pk*ccx + pk**2*cx1
        py = (1-pk)**2*cy0 + 2*(1-pk)*pk*ccy + pk**2*cy1
        pygame.draw.circle(self.surface, self.accent, (int(px), int(py)),
                           2)
        # (i due pozzi di luce sono stati tolti: BLEND_RGBA_ADD ignorava
        # l'alpha e produceva cerchi pieni vistosi invece di un
        # bagliore sottile -- da rifare con una tecnica diversa)
        # ventola, meta' altezza a sinistra: pale che ruotano davvero
        fx0, fy0, fr = 16, H // 2, 15
        fang = t * 2.4
        for k in range(4):
            a = fang + k * math.pi / 2
            bx1 = fx0 + int(4 * math.cos(a + 0.5))
            by1 = fy0 + int(4 * math.sin(a + 0.5))
            bx2 = fx0 + int(fr * math.cos(a))
            by2 = fy0 + int(fr * math.sin(a))
            pygame.draw.polygon(self.surface, sec, [
                (fx0, fy0), (bx1, by1), (bx2, by2)], 1)
        pygame.draw.circle(self.surface, sec, (fx0, fy0), 4, 1)
        # tre LED lungo il margine destro, ognuno col suo ritmo
        for k, (lyf, spd) in enumerate(((0.32, 1.7), (0.5, 2.3),
                                        (0.68, 1.3))):
            on = math.sin(t * spd + k * 2) > 0.4
            lcol = OK_G if on else (40, 46, 42)
            pygame.draw.circle(self.surface, lcol,
                               (W - 10, int(H * lyf)), 3)

    def apply_fx(self):
        self.surface.blit(self.fx_img, (0, 0))

    def _toolbox_layout(self):
        """Posizione (non scrollata) di ogni voce e intestazione del
        Rt:TOOLBOX. Un'unica fonte di verita' per lo scroll e per il
        disegno, cosi' non rischiano mai di disallinearsi."""
        headers, layout_items = [], []
        y = 0
        idx = 0
        for title_it, title_en, gic, count, layout in TOOLBOX_GROUPS:
            headers.append((title_it, title_en, gic, y))
            y += 26
            group_idx = list(range(idx, idx + count))
            if layout == "grid2":
                colw, rowh, gap = (W - 24) // 2, 60, 6
                for k, j in enumerate(group_idx):
                    r_, c_ = divmod(k, 2)
                    x = 8 + c_ * (colw + 8)
                    yy = y + r_ * (rowh + gap)
                    layout_items.append((j, x, yy, colw, rowh))
                y += 2 * (rowh + gap) + 4
            elif layout == "row4":
                colw = (W - 8 - count * 6) // count
                rowh, gap = 58, 6
                for k, j in enumerate(group_idx):
                    x = 8 + k * (colw + gap)
                    layout_items.append((j, x, y, colw, rowh))
                y += rowh + 10
            elif layout == "row3":
                colw = (W - 16 - (count - 1) * 6) // count
                rowh, gap = 62, 6
                for k, j in enumerate(group_idx):
                    x = 8 + k * (colw + gap)
                    layout_items.append((j, x, y, colw, rowh))
                y += rowh + 10
            else:
                colw, rowh, gap = (W - 24) // 2, 64, 8
                for k, j in enumerate(group_idx):
                    x = 8 + k * (colw + gap)
                    layout_items.append((j, x, y, colw, rowh))
                y += rowh + 10
            idx += count
        return headers, layout_items, y

    def _nexus_curve(self, i, j, cx0, cy0, cx1, cy1):
        """Punto di controllo della curva tra il nodo i e il nodo j:
        sempre la stessa forma per quella coppia (seed sull'indice
        della connessione), diversa da tutte le altre."""
        rnd = random.Random(3100 + min(i, j) * 7 + max(i, j))
        mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
        dx, dy = cx1 - cx0, cy1 - cy0
        dist = max(1, math.hypot(dx, dy))
        nx, ny = -dy / dist, dx / dist
        perp = rnd.uniform(-54, 54)
        return mx + nx * perp, my + ny * perp

    def _nexus_sphere(self, cx, cy, r, col, icon_key, t_now, pulse_extra=0.0):
        """La sfera-nodo con un effetto di profondità un po' piu'
        marcato: bordo in ombra, corpo pieno, riflesso freddo in alto
        a sinistra, piccola aura esterna pulsante."""
        pulse = 0.75 + 0.25 * abs(math.sin(t_now * 2.2)) + pulse_extra
        glow = tuple(min(255, int(c * pulse)) for c in col)
        pygame.draw.circle(self.surface, tuple(min(255, int(c * 0.5))
                           for c in col), (int(cx) + 2, int(cy) + 3),
                           r)
        pygame.draw.circle(self.surface, (8, 9, 16), (int(cx), int(cy)),
                           r + 4, 2)
        pygame.draw.circle(self.surface, glow, (int(cx), int(cy)), r)
        for k, (off, sz, add) in enumerate(((0.32, 0.42, 90),
                                            (0.15, 0.18, 140))):
            hi = tuple(min(255, c + add) for c in glow)
            pygame.draw.circle(self.surface, hi,
                               (int(cx - r * off), int(cy - r * off)),
                               max(2, int(r * sz) - k * 2))
        pygame.draw.circle(self.surface, INK, (int(cx), int(cy)), r, 1)
        icons.draw(self.surface, icon_key, int(cx - r * 0.55),
                  int(cy - r * 0.55), max(10, int(r * 1.1)), INK)

    def _nexus_bg(self):
        pygame.draw.rect(self.surface, (4, 5, 10), (0, 44, W, H - 44))
        rnd = random.Random(77)
        t_now = time.time()
        for i in range(140):
            sx, sy = rnd.randrange(W), rnd.randrange(44, H)
            phase = (t_now * 0.5 + i * 0.37) % 4.0
            if phase > 2.6:          # la stella e' "spenta" per un tratto
                continue
            tw = 0.3 + 0.7 * abs(math.sin(t_now * 1.3 + sx * 0.1))
            v = int(70 * tw)
            self.surface.set_at((sx, sy), (v, v, v + 22))
        for gy in range(H - 90, H, 18):
            fade = (gy - (H - 90)) / 90.0
            col = (10, 12, 22 + int(20 * fade))
            pygame.draw.line(self.surface, col, (0, gy), (W, gy), 1)
        # glitch digitale occasionale: una sottile fascia sfasata,
        # compare a scatti imprevedibili, mai per piu' di un istante
        gseed = int(t_now * 3.7)
        grnd = random.Random(gseed)
        if grnd.random() < 0.10:
            gy2 = grnd.randrange(44, H - 6)
            gh = grnd.randrange(2, 6)
            shift = grnd.randrange(-14, 14)
            band = self.surface.subsurface(
                (0, gy2, W, gh)).copy()
            self.surface.blit(band, (shift, gy2))
            gcol = self.accent if grnd.random() < 0.5 else (200, 60, 90)
            pygame.draw.line(self.surface, gcol, (0, gy2), (W, gy2), 1)

    def _nexus_hue(self, i):
        hues = [self.env_color(e) for e, *_r in ENVS] + \
            [self.accent, (110, 195, 250), (200, 130, 250),
             OK_G, STEEL, (250, 150, 90)]
        return hues[i % len(hues)]

    def render_home_nexus(self):
        """Nexus: un nodo alla volta, grande, a sinistra. Rette che
        accennano ai vicini senza mostrare l'intero percorso -- lo
        vedi tutto solo viaggiandoci sopra, un salto alla volta. I
        due riquadri d'informazione stanno a destra, un cavo li
        collega fisicamente al primo."""
        self.header("__brand__")
        self._nexus_bg()
        n = len(self.menu)
        cx, cy = 138, H // 2 + 6
        r = 58 if self.sel == 0 else 44
        for nb, sign in ((self.sel - 1, -1), (self.sel + 1, 1)):
            nb %= n
            _cx, _cy = self._nexus_curve(self.sel, nb, cx, cy,
                                         cx + sign * 200, cy)
            steps = 10
            prev = (cx, cy)
            for s in range(1, steps + 1):
                tt = s / float(steps) * 0.4
                bx = (1-tt)**2*cx + 2*(1-tt)*tt*_cx + tt**2*(cx+sign*200)
                by = (1-tt)**2*cy + 2*(1-tt)*tt*_cy + tt**2*cy
                a = max(0, 120 - s * 12)
                pygame.draw.line(self.surface, (a, a, a + 10), prev,
                                 (bx, by), 2)
                prev = (bx, by)
        self._nexus_sphere(cx, cy, r, self._nexus_hue(self.sel),
                           self.menu_icons[self.sel], time.time())
        self.last_sel_rect = (cx - r, cy - r, r * 2, r * 2)
        label, sub = self.menu[self.sel]
        bx = cx + r + 34
        bw = W - bx - 14
        by = H // 2 - 92
        # cavo dal bordo inferiore centrale del riquadro nome verso il
        # riquadro dettaglio sotto: due segmenti dritti, non una linea
        # dritta unica, per sembrare un vero cavo posato
        cable_x = bx + bw // 2
        cable_y0 = by + 46
        cable_y1 = by + 68
        pygame.draw.line(self.surface, STEEL, (cable_x, cable_y0),
                         (cable_x - 14, cable_y0 + 11), 3)
        pygame.draw.line(self.surface, STEEL, (cable_x - 14, cable_y0 + 11),
                         (cable_x, cable_y1), 3)
        self.npanel(bx, by, bw, 46, border=self.accent, fill=INK, cut=8)
        self.text("NODO" if self.lang == "it" else "NODE", (bx + 10, by + 3),
                  self.f_tiny, self.accent)
        self.f_med.set_bold(True)
        lw = self.f_med.size(label)[0]
        self.text(label, (bx + (bw - lw) // 2, by + 18), self.f_med, FG,
                  maxw=bw - 20)
        self.f_med.set_bold(False)
        by2 = by + 68
        self.npanel(bx, by2, bw, 62, border=LINE, fill=INK, cut=6)
        self.text("IN DEPTH", (bx + 10, by2 + 3), self.f_tiny, self.accent)
        self.text(sub, (bx + 10, by2 + 22), self.f_small, FAINT,
                  maxw=bw - 20)
        self.footer([("Y", self.t("view")),
                     ("SX/DX", self.t("change")), ("A", self.t("open")),
                     ("B", self.t("exit"))])

    def nexus_travel(self, direction):
        """Animazione bloccante: la vista viaggia lungo la retta dal
        nodo attuale al successivo, seguendo davvero la curva di
        quella connessione, poi arriva e il nuovo nodo cresce a
        sinistra. Suono dedicato, diverso da tutti gli altri."""
        self.play("nexus")
        n = len(self.menu)
        i0 = self.sel
        i1 = (self.sel + direction) % n
        cx, cy = 138, H // 2 + 6
        r0 = 58 if i0 == 0 else 44
        r1 = 58 if i1 == 0 else 44
        col0, col1 = self._nexus_hue(i0), self._nexus_hue(i1)
        ic0, ic1 = self.menu_icons[i0], self.menu_icons[i1]
        tx = cx + direction * 200
        ccx, ccy = self._nexus_curve(i0, i1, cx, cy, tx, cy)
        frames = 20
        t0 = time.time()
        for f in range(frames):
            k = f / float(frames - 1)
            self.header("__brand__")
            self._nexus_bg()
            bx = (1 - k) ** 2 * cx + 2 * (1 - k) * k * ccx + \
                k ** 2 * tx
            by = (1 - k) ** 2 * cy + 2 * (1 - k) * k * ccy + \
                k ** 2 * cy
            steps = max(2, int(18 * k))
            prev = (cx, cy)
            for s in range(1, steps + 1):
                tt = s / 18.0
                lx = (1-tt)**2*cx + 2*(1-tt)*tt*ccx + tt**2*tx
                ly = (1-tt)**2*cy + 2*(1-tt)*tt*ccy + tt**2*cy
                pygame.draw.line(self.surface, self.accent, prev,
                                 (lx, ly), 2)
                prev = (lx, ly)
            shrink = max(0.15, 1 - k * 1.6)
            grow = max(0.0, k * 1.6 - 0.6) if k > 0.4 else 0.0
            if shrink > 0.15:
                self._nexus_sphere(cx, cy, max(4, int(r0 * shrink)),
                                   col0, ic0, t0)
            spark_r = max(3, int(6 - abs(k - 0.5) * 6))
            pygame.draw.circle(self.surface, FG, (int(bx), int(by)),
                               spark_r)
            if grow > 0:
                self._nexus_sphere(tx, cy, max(4, int(r1 * min(1.0,
                                   grow))), col1, ic1, t0)
            self.footer([("SX/DX", self.t("change"))])
            pygame.display.flip()
            self.clock.tick(40)
        self.sel = i1
        self.render()

    def _tb_tile(self, j, item, x, y, w, h, icon_sz=24, big=False,
                compact=False):
        """Un riquadro del Rt:Toolbox: stesso disegno per tutti e
        quattro i layout dei gruppi, solo dimensioni/proporzioni
        diverse -- cosi' i quattro widget sembrano parenti, non
        estranei."""
        key, ic, lk, sk, kind = item
        sel = (j == self.hub_sel)
        if sel:
            self.sel_frame(x, y, w, h)
        else:
            self.npanel(x, y, w, h, border=LINE, fill=INK, cut=8)
        if compact:
            icons.draw(self.surface, ic, x + (w - icon_sz) // 2, y + 6,
                      icon_sz, self.accent if sel else FAINT)
            lab = self.t(lk)
            lw = self.f_tiny.size(lab)[0]
            while lw > w - 8 and len(lab) > 3:
                lab = lab[:-1]
                lw = self.f_tiny.size(lab + "..")[0]
            if lw > w - 8:
                lab = lab[:max(1, len(lab))] + ".."
            self.text(lab, (x + (w - self.f_tiny.size(lab)[0]) // 2,
                            y + icon_sz + 10), self.f_tiny,
                      FG if sel else DIM)
        elif big:
            icons.draw(self.surface, ic, x + 12, y + (h - icon_sz) // 2,
                      icon_sz, self.accent if sel else FAINT)
            self.text(self.t(lk), (x + 20 + icon_sz, y + 12),
                      self.f_small, FG if sel else DIM,
                      maxw=w - icon_sz - 30)
            self.text(self.t(sk), (x + 20 + icon_sz, y + 34),
                      self.f_tiny, FAINT, maxw=w - icon_sz - 30)
        else:
            icons.draw(self.surface, ic, x + 8, y + (h - icon_sz) // 2,
                      icon_sz, self.accent if sel else FAINT)
            self.text(self.t(lk), (x + 14 + icon_sz, y + (h - 18) // 2),
                      self.f_tiny, FG if sel else DIM,
                      maxw=w - icon_sz - 22)

    def npanel(self, x, y, w, h, border=None, fill=PANEL, cut=9):
        """Pannello con l'angolo tagliato in alto a destra, vignetta manga,
        bevel a freddo e rivetti d'acciaio: una lastra vera, non un
        rettangolo piatto -- e non sparisce piu' sotto il contenuto."""
        pts = [(x, y), (x + w - cut, y), (x + w, y + cut),
               (x + w, y + h), (x, y + h)]
        pygame.draw.polygon(self.surface, fill, pts)
        pygame.draw.polygon(self.surface, border or LINE, pts, 1)
        if w > 20 and h > 14:
            pygame.draw.line(self.surface, STEEL_HI, (x + 2, y + 1),
                             (x + w - cut - 2, y + 1), 1)
            pygame.draw.line(self.surface, STEEL_HI, (x + 1, y + 2),
                             (x + 1, y + h - 2), 1)
            pygame.draw.line(self.surface, INK, (x + 2, y + h - 2),
                             (x + w - 2, y + h - 2), 1)
            pygame.draw.line(self.surface, INK, (x + w - 2, y + cut + 2),
                             (x + w - 2, y + h - 2), 1)
            for rx, ry in ((x + 6, y + h - 6), (x + 6, y + 6)):
                pygame.draw.circle(self.surface, INK, (rx, ry), 2)
                pygame.draw.circle(self.surface, STEEL, (rx, ry), 2, 1)

    def content_panel(self, y0, y1, x0=8, x1=None):
        """Pannello metallico dietro il contenuto di una schermata: lo
        sfondo animato resta visibile nei margini, ma qui sotto il
        testo appoggia su una superficie ferma e leggibile. Rifinitura
        cel-shading: riflesso netto in alto, ombra netta in basso,
        mai una sfumatura morbida."""
        if x1 is None:
            x1 = W - 8
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((*PANEL, 235))
        pygame.draw.line(panel, (*STEEL_HI, 235), (0, 0), (w, 0), 2)
        pygame.draw.line(panel, (*STEEL_HI, 235), (0, 0), (0, h), 2)
        pygame.draw.line(panel, (*INK, 235), (0, h - 2), (w, h - 2), 2)
        pygame.draw.line(panel, (*INK, 235), (w - 2, 0), (w - 2, h), 2)
        pygame.draw.rect(panel, (*LINE, 235), (0, 0, w, h), 1)
        self.surface.blit(panel, (x0, y0))

    def clock_backdrop(self):
        """Tinta unita + ingranaggi grandi che ruotano piano, tenui.
        Niente griglia che scorre: qui il protagonista e' l'orologio,
        non lo sfondo. Ritagliato sotto l'header: un ingranaggio
        altrimenti ci sconfinerebbe dentro."""
        self.surface.set_clip(pygame.Rect(0, 44, W, H - 44))
        self.surface.fill((10, 11, 15), (0, 44, W, H - 44))
        t = time.time()
        gcol = (24, 26, 33)
        for gx, gy, gr, teeth, speed, spin in (
                (70, 380, 74, 10, 0.09, 1), (W - 60, 90, 60, 8, -0.07, -1),
                (W - 40, 400, 46, 8, 0.12, 1)):
            ang0 = t * speed * spin
            pts = []
            for i in range(teeth * 2):
                a = ang0 + i * math.pi / teeth
                rr = gr if i % 2 == 0 else gr * 0.82
                pts.append((gx + rr * math.cos(a), gy + rr * math.sin(a)))
            pygame.draw.polygon(self.surface, gcol, pts, 2)
            pygame.draw.circle(self.surface, gcol, (gx, gy),
                               int(gr * 0.3), 2)
            for i in range(6):
                a = ang0 + i * math.pi / 3
                pygame.draw.line(self.surface, gcol, (gx, gy),
                                 (gx + gr * 0.28 * math.cos(a),
                                  gy + gr * 0.28 * math.sin(a)), 1)
        self.surface.set_clip(None)

    def _clock_hand(self, cx, cy, ang, length, w0, w1, color, tail=0):
        """Lancetta affusolata: larga alla base (w0), stretta in punta
        (w1), con coda-contrappeso opzionale dalla parte opposta."""
        px, py = math.cos(ang), math.sin(ang)
        nx, ny = -py, px
        tip = (cx + length * px, cy + length * py)
        base_l = (cx + nx * w0 / 2, cy + ny * w0 / 2)
        base_r = (cx - nx * w0 / 2, cy - ny * w0 / 2)
        mid = (cx + 0.15 * length * px + nx * w1 / 2,
              cy + 0.15 * length * py + ny * w1 / 2)
        mid2 = (cx + 0.15 * length * px - nx * w1 / 2,
               cy + 0.15 * length * py - ny * w1 / 2)
        pygame.draw.polygon(self.surface, color,
                            [base_l, mid, tip, mid2, base_r])
        if tail:
            pygame.draw.line(self.surface, color, (cx, cy),
                             (cx - tail * px, cy - tail * py),
                             max(2, int(w0 * 0.4)))

    def sel_frame(self, x, y, w, h, color=None, cut=8):
        """Riga selezionata: lastra tinta, barra hazard, staffe agli angoli
        e un tick che scorre sul bordo basso. `color` e' la tinta
        identitaria dell'ambiente nel selettore START SESSION. Registra
        il rettangolo: origine della prossima transizione a finestra."""
        self.last_sel_rect = (x, y, w, h)
        a = color or self.accent
        pts = [(x, y), (x + w - cut, y), (x + w, y + cut),
               (x + w, y + h), (x, y + h)]
        pygame.draw.polygon(self.surface,
                            sel_tint(a) if color else self.sel_bg, pts)
        pygame.draw.polygon(self.surface, a, pts, 1)
        # barra hazard a sinistra
        sy = y + 1
        while sy < y + h - 1:
            hh = min(24, y + h - 1 - sy)
            self.surface.blit(self.stripe_img, (x + 1, sy),
                              (0, 0, 6, hh))
            sy += hh
        for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y + cut, -1, 1),
                               (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
            pygame.draw.line(self.surface, a, (cx, cy), (cx + 7 * dx, cy), 2)
            pygame.draw.line(self.surface, a, (cx, cy), (cx, cy + 6 * dy), 2)
        tick = x + 10 + int((time.time() * 90) % max(1, w - 30))
        pygame.draw.line(self.surface, a, (tick, y + h - 1),
                         (tick + 9, y + h - 1), 2)

    def spinner(self, cx, cy, r=11):
        """Rotore di caricamento: tre archi sfalsati, stile radar."""
        t = time.time() * 5.2
        for i, (rr, wd) in enumerate(((r, 3), (r - 5, 2))):
            a0 = t * (1 if i == 0 else -1.4) + i * 2.1
            pygame.draw.arc(self.surface, self.accent,
                            (cx - rr, cy - rr, rr * 2, rr * 2),
                            a0, a0 + 3.6, wd)
        pygame.draw.circle(self.surface, self.accent, (cx, cy), 2)

    def render_busy(self):
        """Frame di attesa animato sopra la schermata corrente."""
        self.render(flip=False)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        self.surface.blit(veil, (0, 0))
        lab = self.busy_label or ""
        if lab:
            lab = lab[:1].upper() + lab[1:]
        lab = lab.rstrip(".")
        dots = "." * (1 + int(time.time() * 2.5) % 3)
        pw = 380
        lines = self.note_wrap(lab + dots, pw - 92, self.f_med, 2)
        ph = 118 if len(lines) < 2 else 138
        px, py = (W - pw) // 2, (H - ph) // 2
        self.npanel(px, py, pw, ph, border=self.accent, fill=INK)
        self.spinner(px + 34, py + 36)
        ly = py + 22
        for ln in lines:
            self.text(ln, (px + 62, ly), self.f_med, FG, maxw=pw - 92)
            ly += 22
        el = max(0.0, time.time() - self.busy_t0)
        bar_x, bar_w, bar_y = px + 30, pw - 60, py + ph - 36
        est = "%d s" % int(el)
        ew = self.f_tiny.size(est)[0]
        self.text(est, (bar_x + bar_w - ew, bar_y - 17), self.f_tiny, DIM)
        m_pct = re.search(r"(\d{1,3})\s*%", lab)
        if m_pct:
            pct = max(0, min(100, int(m_pct.group(1))))
        else:
            pct = min(96, int(100 * el / (el + 3.0))) if el > 0.05 else 3
        pygame.draw.rect(self.surface, (14, 15, 19),
                         (bar_x, bar_y, bar_w, 8))
        pygame.draw.rect(self.surface, self.accent,
                         (bar_x, bar_y, max(4, bar_w * pct // 100), 8))
        pygame.draw.rect(self.surface, LINE, (bar_x, bar_y, bar_w, 8), 1)
        pygame.display.flip()

    def run_busy(self, label, fn):
        """Esegue fn in un thread e anima lo spinner finche' non finisce:
        mai piu' schermate incantate durante i lavori lunghi."""
        self.busy_label = label
        self.busy_t0 = time.time()
        box = {}

        def work():
            try:
                box["v"] = fn()
            except Exception as e:      # il chiamante decide cosa farne
                box["e"] = e

        th = threading.Thread(target=work)
        th.daemon = True
        th.start()
        while th.is_alive():
            evinput.poll()              # scarto l'input: niente code strane
            self.render_busy()
            self.clock.tick(30)
        evinput.poll()
        return box.get("v")

    def handoff(self, label):
        """Ultimo frame prima di passare la mano a uno script esterno:
        lo schermo cambia SUBITO, poi vd_loader continua l'animazione."""
        self.backdrop()
        pw, ph = 420, 120
        px, py = (W - pw) // 2, (H - ph) // 2
        self.npanel(px, py, pw, ph, border=self.accent, fill=INK)
        self.spinner(px + 36, py + ph // 2)
        self.text(label, (px + 66, py + 30), self.f_med, FG, maxw=pw - 84)
        self.text("SPDW FACTORY // handoff", (px + 66, py + 62),
                  self.f_tiny, FAINT)
        self.apply_fx()
        pygame.display.flip()

    # --------------------------------------------------------------- disegno
    def text(self, s, pos, f, color, maxw=None):
        if maxw:
            while s and f.size(s)[0] > maxw:
                s = s[:-1]
        self.surface.blit(f.render(s, True, color), pos)

    def mark(self, x, y, state):
        """Spunta verde / croce rossa / trattino grigio, disegnate a mano
        (le emoji non esistono nel font)."""
        if state is True:
            pygame.draw.lines(self.surface, OK_G, False,
                              [(x, y + 7), (x + 4, y + 12), (x + 13, y - 1)],
                              3)
        elif state is False:
            pygame.draw.line(self.surface, NO_R, (x, y - 1), (x + 12, y + 11),
                             3)
            pygame.draw.line(self.surface, NO_R, (x + 12, y - 1), (x, y + 11),
                             3)
        else:
            pygame.draw.line(self.surface, UNK, (x, y + 5), (x + 12, y + 5), 3)

    def checkbox(self, x, y, checked):
        pygame.draw.rect(self.surface, DIM, (x, y, 14, 14), 1)
        if checked:
            pygame.draw.rect(self.surface, self.accent, (x + 3, y + 3, 8, 8))

    def status_snapshot(self):
        now = time.time()
        if now - self._stat[1] > 8:
            pct, chg = sysinfo.battery()
            conn, ssid, lvl, iface, ip = sysinfo.wifi_status()
            self._stat = ({"batt": pct, "chg": chg, "ssid": ssid,
                           "wifi": lvl if conn else None, "conn": conn,
                           "iface": iface, "ip": ip,
                           "bt": sysinfo.bt_status(),
                           "vol": sysinfo.volume(),
                           "usb": sysinfo.usb_mode(),
                           "hot": self.hot_active()}, now)
        return self._stat[0]

    def header(self, title, right="", icon=None):
        self.backdrop()
        pygame.draw.rect(self.surface, INK, (0, 0, W, 42))
        pygame.draw.line(self.surface, LINE, (0, 0), (W, 0), 1)
        pygame.draw.line(self.surface, self.accent, (0, 42), (W, 42), 2)
        pygame.draw.line(self.surface, INK, (0, 44), (W, 44), 2)
        for rx in range(60, W - 20, 58):
            pygame.draw.circle(self.surface, STEEL, (rx, 2), 1)
        # tratti hazard che mordono la riga dell'header, come una tavola
        for hx in range(0, 46, 9):
            pygame.draw.line(self.surface, self.accent, (hx, 42),
                             (hx + 5, 46), 2)
        if title == "__brand__":
            # ghost cromatici sfalsati: la firma SPDW
            self.text("Void-DESK", (13, 9), self.f_big, (150, 30, 30))
            self.text("Void-DESK", (15, 7), self.f_big, (25, 90, 100))
            self.text("Void-", (14, 8), self.f_big, FG)
            bw = self.f_big.size("Void-")[0]
            self.text("DESK", (14 + bw, 8), self.f_big, self.accent)
        else:
            tx0 = 14
            if icon:
                icons.draw(self.surface, icon, 12, 8, 28, self.accent)
                tx0 = 48
            else:
                self.text("▚ ", (13, 9), self.f_big, (140, 30, 30))
                self.text("▚ ", (14, 8), self.f_big, self.accent)
                tx0 = 14 + self.f_big.size("▚ ")[0]
            self.text(title, (tx0 - 1, 9), self.f_big, (140, 30, 30))
            self.text(title, (tx0, 8), self.f_big, self.accent)
        show_clock = self.cfg.get("clock_badge", True)
        cw = 52 if show_clock else 0
        x = W - 14 - (cw + 6 if show_clock else 0)
        if right:
            rw = self.f_small.size(right)[0]
            x -= rw
            self.text(right, (x, 14), self.f_small, DIM)
            x -= 14
        if self.cfg.get("battery", True):
            st = self.status_snapshot()
            # batteria (con percentuale e saetta se in carica), volume,
            # bluetooth, wifi -- ognuno rispetta il proprio interruttore
            if st["batt"] is not None and self.cfg.get("st_batt", True):
                txt = "%d%%" % st["batt"]
                tw = self.f_tiny.size(txt)[0]
                x -= tw
                self.text(txt, (x, 16), self.f_tiny,
                          NO_R if st["batt"] <= 20 else DIM)
                x -= 26
                icons.battery_icon(self.surface, x, 8, 20, st["batt"],
                                   st["chg"], OK_G, NO_R, DIM)
            if self.cfg.get("st_vol", True):
                x -= 28
                icons.volume_icon(self.surface, x, 10, 20, st["vol"],
                                  self.accent, FAINT)
            if st.get("usb") and self.cfg.get("st_usb", True):
                x -= 24
                icons.draw(self.surface, "usb" if st["usb"] == "mtp"
                           else "android", x, 10, 18, self.accent)
            if st.get("hot") and self.cfg.get("st_hotspot", True):
                x -= 26
                icons.draw(self.surface, "uplink", x, 10, 20, OK_G)
            if st["bt"] is not None and self.cfg.get("st_bt", True):
                x -= 26
                icons.bt_icon(self.surface, x, 10, 20, st["bt"],
                              self.accent, FAINT)
            if self.cfg.get("st_wifi", True):
                x -= 26
                icons.wifi_icon(self.surface, x, 10, 20, st["wifi"],
                                self.accent, FAINT)
                lab = st.get("ip") or st.get("ssid")
                if lab:
                    sw = min(self.f_tiny.size(lab)[0], 108)
                    x -= sw + 6
                    self.text(lab, (x, 16), self.f_tiny, DIM, maxw=108)
        if show_clock:
            self.header_clock_badge()

    def header_clock_badge(self):
        """Orologio conficcato nell'angolo, cornice tonda: l'header
        resta invariato dietro, il quadrante sta sopra. Solo l'ora:
        niente data, cifre grandi in grassetto, bordo nero sottile e
        sfondo LCD scuro per un aspetto davvero digitale."""
        cx, cy, r = W - 38, 24, 24
        pygame.draw.circle(self.surface, INK, (cx, cy), r)
        pygame.draw.circle(self.surface, self.accent, (cx, cy), r, 4)
        pygame.draw.circle(self.surface, LINE, (cx, cy), r - 6, 1)
        lt = time.localtime()
        blink = int(time.time() * 2) % 2 == 0
        sep = ":" if blink or not self.cfg.get("clock_blink", True) \
            else " "
        hm = "%02d%s%02d" % (lt.tm_hour, sep, lt.tm_min)
        self.f_med.set_bold(True)
        img = self.f_med.render(hm, True, FG)
        iw, ih = img.get_size()
        ix, iy = cx - iw // 2, cy - ih // 2
        pygame.draw.rect(self.surface, (6, 14, 10),
                         (ix - 3, iy - 1, iw + 6, ih + 2),
                         border_radius=3)
        digi = (120, 240, 170)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            edge = self.f_med.render(hm, True, INK)
            self.surface.blit(edge, (ix + dx, iy + dy))
        img = self.f_med.render(hm, True, digi)
        self.f_med.set_bold(False)
        self.surface.blit(img, (ix, iy))

    def footer(self, hints):
        pygame.draw.rect(self.surface, INK, (0, H - 28, W, 28))
        pygame.draw.line(self.surface, LINE, (0, H - 28), (W, H - 28), 1)
        # il simbolo di Minoru vive sempre al centro: divido i
        # suggerimenti in due meta', sinistra verso destra e destra
        # verso sinistra, cosi' non possono mai arrivare a
        # sovrapporlo qualunque sia il numero di voci
        half = (len(hints) + 1) // 2
        left, right = hints[:half], hints[half:]
        x = 10
        for k, lab in left:
            kw = self.f_small.size(k)[0]
            self.npanel(x, H - 25, kw + 12, 20, border=self.accent, fill=INK,
                        cut=5)
            self.text(k, (x + 6, H - 23), self.f_small, self.accent)
            x += kw + 18
            self.text(lab, (x, H - 23), self.f_small, DIM)
            x += self.f_small.size(lab)[0] + 15
        xr = W - 10
        for k, lab in reversed(right):
            lw = self.f_small.size(lab)[0]
            xr -= lw
            self.text(lab, (xr, H - 23), self.f_small, DIM)
            xr -= 6
            kw = self.f_small.size(k)[0]
            xr -= kw + 12
            self.npanel(xr, H - 25, kw + 12, 20, border=self.accent,
                        fill=INK, cut=5)
            self.text(k, (xr + 6, H - 23), self.f_small, self.accent)
            xr -= 15
        # simbolo di Minoru: sempre verde fosforo e nero, mai il colore
        # del tema -- e' la sua identita', non decorazione della UI
        mcx, mcy, mr = W // 2, H - 14, 9
        pygame.draw.circle(self.surface, (5, 5, 5), (mcx, mcy), mr)
        pygame.draw.circle(self.surface, GRN, (mcx, mcy), mr, 1)
        pygame.draw.line(self.surface, GRN, (mcx - mr + 3, mcy),
                         (mcx + mr - 3, mcy), 2)

    # ------------------------------------------------------------ componenti
    def chroot_root(self):
        mnt = os.path.join(DATA, "xfce_mnt")
        return mnt if mounted(mnt) else None

    def deps_missing(self, feature_key):
        """Nomi delle voci del catalogo mancanti per una funzionalita'.
        None se manca la base XFCE stessa (problema piu' a monte, non
        una singola dipendenza)."""
        needed = FEATURE_DEPS.get(feature_key, [])
        dbg = os.path.join(DATA, "deps_check.log")

        def log(msg):
            try:
                with open(dbg, "a") as f:
                    f.write("%s %s: %s\n" % (time.strftime("%H:%M:%S"),
                                             feature_key, msg))
            except OSError:
                pass
        log("richiesto, needed=%r" % needed)
        if not needed:
            return []
        if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
            log("base XFCE non pronta (.xfce_ready assente)")
            return None
        root = os.path.join(DATA, "xfce_mnt")
        was_mounted = imgmount.is_mounted(root)
        log("era gia' montato? %r" % was_mounted)
        if not was_mounted:
            ok, _e = imgmount.mount_img(
                os.path.join(DATA, "xfce.img"), root, ro=True)
            log("mount fresco (ro): ok=%r err=%r" % (ok, _e))
            if not ok:
                log("mount fallito: assumo tutto mancante")
                return list(needed)
        missing = []
        try:
            for _cat, items in CATEGORIES:
                for name, _pkgs, _desc, paths, _ic in items:
                    if name not in needed:
                        continue
                    ok2 = True
                    for token in paths.split():
                        if "|" in token:
                            found = [chroot_path_exists(root, alt)
                                     for alt in token.split("|")]
                            log("  %s: alternative %r -> %r" %
                                (name, token.split("|"), found))
                            ok2 = ok2 and any(found)
                        else:
                            exists = chroot_path_exists(root, token)
                            log("  %s: %s -> %r" % (name, token, exists))
                            ok2 = ok2 and exists
                    if not ok2:
                        missing.append(name)
            log("risultato finale: mancanti=%r" % missing)
        finally:
            if not was_mounted:
                imgmount.umount_tree(root)
                log("smontato (era stato montato fresco da qui)")
        return missing

    def deps_dialog_open(self, feature_key, icon, title):
        """True se le dipendenze ci sono gia' (si puo' procedere). Se
        mancano, apre la finestrella dedicata e ritorna False: chi
        chiama deve fermarsi li'."""
        missing = self.run_busy(self.t("checking"),
                                lambda: self.deps_missing(feature_key))
        if missing == []:
            return True
        self.deps_missing_list = missing or FEATURE_DEPS.get(
            feature_key, [])
        self.deps_feature_icon = icon
        self.deps_feature_title = title
        self.push("depsmissing")
        return False

    def scan_status(self):
        """Monta l'immagine in sola lettura, verifica i file, poi smonta
        e LIBERA il loop (altrimenti dopo qualche giro i loop finiscono
        e l'installazione non riesce piu' a montare)."""
        img = os.path.join(DATA, "xfce.img")
        mnt = os.path.join(DATA, "xfce_mnt")
        temp = False
        if not imgmount.is_mounted(mnt) and os.path.exists(img):
            imgmount.cleanup_stale(img)
            ok, _err = imgmount.mount_img(img, mnt, ro=True)
            temp = ok
        root = mnt if imgmount.is_mounted(mnt) else None
        if root:
            try:
                sv = os.statvfs(root)
                self.img_free = sv.f_bavail * sv.f_frsize
                self.img_total = sv.f_blocks * sv.f_frsize
                envs = ["xfce"]
                if chroot_path_exists(root, "usr/bin/icewm-session"):
                    envs.append("icewm")
                if chroot_path_exists(root, "usr/bin/startlxde"):
                    envs.append("lxde")
                os.makedirs(DATA, exist_ok=True)
                with open(os.path.join(DATA, ".envs"), "w") as f:
                    f.write(" ".join(envs))
            except OSError:
                self.img_free = None
                self.img_total = None
        st = {}
        for _cat, items in CATEGORIES:
            for name, _pkgs, _desc, paths, _ic in items:
                if root is None:
                    st[name] = None
                    continue
                ok = True
                for token in paths.split():
                    if "|" in token:
                        ok = ok and any(
                            chroot_path_exists(root, alt)
                            for alt in token.split("|"))
                    else:
                        ok = ok and chroot_path_exists(root, token)
                st[name] = ok
        if temp:
            imgmount.umount_tree(mnt, img)
        self.status = st

    def build_rows(self):
        """Righe piatte: ('cat', titolo) oppure ('item', nome, pkgs, desc)."""
        rows = []
        for cat, items in CATEGORIES:
            rows.append(("cat", cat))
            for name, pkgs, desc, _p, ic in items:
                rows.append(("item", name, pkgs, desc, ic))
        self.rows = rows
        self.row_sel = next(i for i, r in enumerate(rows) if r[0] == "item")

    def cat_of(self, idx):
        """Nome della categoria a cui appartiene la riga idx (guarda
        all'indietro fino al più vicino header 'cat')."""
        for i in range(idx, -1, -1):
            if self.rows[i][0] == "cat":
                return self.rows[i][1]
        return None

    def move_rows(self, step):
        i = self.row_sel
        n = len(self.rows)
        for _ in range(n):
            i = (i + step) % n
            if self.rows[i][0] == "item" and \
                    self.cat_of(i) not in self.cat_collapsed:
                self.row_sel = i
                return

    def toggle_category(self):
        cat = self.cat_of(self.row_sel)
        if cat is None:
            return
        if cat in self.cat_collapsed:
            self.cat_collapsed.discard(cat)
        else:
            self.cat_collapsed.add(cat)
            self.move_rows(1)

    def cat_starts(self):
        """Indici della prima voce di ogni categoria."""
        out = []
        for i, r in enumerate(self.rows):
            if r[0] == "cat" and i + 1 < len(self.rows) \
                    and self.rows[i + 1][0] == "item":
                out.append(i + 1)
        return out

    def jump_category(self, step):
        starts = self.cat_starts()
        if not starts:
            return
        # indice della categoria in cui mi trovo ora
        cur = 0
        for k, s0 in enumerate(starts):
            if self.row_sel >= s0:
                cur = k
        if step > 0:
            self.row_sel = starts[(cur + 1) % len(starts)]
        else:
            # se non sono gia' sulla prima voce, torno all'inizio di questa
            # categoria; altrimenti vado alla precedente (era il bug: SX
            # sembrava non fare nulla)
            if self.row_sel != starts[cur]:
                self.row_sel = starts[cur]
            else:
                self.row_sel = starts[(cur - 1) % len(starts)]

    def install_marked(self):
        idxs = sorted(self.marked) or [self.row_sel]
        names, pkgs = [], []
        for i in idxs:
            if i >= len(self.rows) or self.rows[i][0] != "item":
                continue
            names.append(self.rows[i][1])
            pkgs.append(self.rows[i][2])
        if not pkgs:
            return
        label = (names[0] if len(names) == 1 else
                 ("%d componenti" if self.lang == "it" else "%d components")
                 % len(names))
        # in modalita' disinstalla non si tocca la base del desktop:
        # senza Xorg o sessione XFCE il desktop non parte piu'.
        if self.mode == "remove":
            base = {n for _c, items in CATEGORIES[:2] for n, _p, _d, _pa, _i
                    in items}
            blocked = [n for n in names if n in base]
            if blocked:
                self.info_lines = [
                    ("sec", "info", "ATTENZIONE" if self.lang == "it"
                     else "WARNING"),
                    ("kv", "", self.t("no_base"), NO_R),
                    ("kv", "", ", ".join(blocked[:6]), DIM)]
                self.push("info")
                return
        # guardia: se l'immagine ext4 e' quasi piena, apt fallirebbe a meta'
        # lasciando pacchetti rotti. Meglio dirlo prima.
        if self.mode != "remove" and self.img_free is not None \
                and self.img_free < 250 * 1024 * 1024:
            self.info_lines = [
                ("sec", "disk", "SPAZIO INSUFFICIENTE" if self.lang == "it"
                 else "NOT ENOUGH SPACE"),
                ("kv", "", self.t("no_space") % human(self.img_free), NO_R),
                ("kv", "", self.t("no_space_s"), DIM)]
            self.scroll = 0
            self.push("info")
            return
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, ".install_pkg"), "w") as f:
            f.write("%s\n%s\n" % (label, " ".join(pkgs)))
        self.handoff(self.t("ho_rm") if self.mode == "remove"
                     else self.t("ho_pkg"))
        self.exit_code = (EXIT_PKG_REMOVE if self.mode == "remove"
                          else EXIT_PKG_INSTALL)
        self.running = False

    # ----------------------------------------------------------- info di stato
    def void_stats(self):
        """Righe: ('sec', ICONA, TITOLO) | ('kv', etichetta, valore, colore)"""
        L = []
        st = self.status_snapshot()

        L.append(("sec", "xorg", "SISTEMA"))
        try:
            un = os.uname()
            L.append(("kv", "KERNEL", "%s %s" % (un.sysname, un.release), FG))
        except Exception:
            pass
        ver = ""
        for p in ("/opt/muos/config/system/version",
                  "/opt/muos/config/version.txt"):
            if os.path.exists(p):
                ver = open(p).read().strip().splitlines()[0]
                break
        if ver:
            L.append(("kv", "muOS", ver, FG))
        up = ""
        try:
            s_ = int(float(open("/proc/uptime").read().split()[0]))
            up = "%dh %02dm" % (s_ // 3600, (s_ % 3600) // 60)
        except (OSError, ValueError):
            pass
        if up:
            L.append(("kv", "ACCESO DA", up, FG))
        t = ""
        for z in ("/sys/class/thermal/thermal_zone0/temp",):
            v = ""
            try:
                v = open(z).read().strip()
            except OSError:
                pass
            if v.isdigit():
                iv = int(v)
                t = "%.1f °C" % (iv / 1000.0 if iv > 1000 else float(iv))
        if t:
            L.append(("kv", "TEMPERATURA", t, FG))

        L.append(("sec", "task", "MEMORIA"))
        tot = avail = 0
        try:
            for ln in open("/proc/meminfo"):
                if ln.startswith("MemTotal:"):
                    tot = int(ln.split()[1])
                elif ln.startswith("MemAvailable:"):
                    avail = int(ln.split()[1])
        except OSError:
            pass
        if tot:
            used = tot - avail
            L.append(("kv", "RAM", "%d MB usati / %d MB" %
                      (used // 1024, tot // 1024),
                      NO_R if used * 100 // tot > 85 else FG))

        L.append(("sec", "disk", "ARCHIVIAZIONE"))
        for lbl, p in (("SD1 (mmc)", "/mnt/mmc"), ("SD2 (sdcard)",
                                                   "/mnt/sdcard")):
            free, tt = disk_free(p)
            if free is not None:
                pctf = 100 - (free * 100 // tt if tt else 0)
                L.append(("kv", lbl.upper(), "%s liberi / %s  (%d%% usato)"
                          % (human(free), human(tt), pctf),
                          NO_R if pctf > 92 else FG))
        img = os.path.join(DATA, "xfce.img")
        if os.path.exists(img):
            L.append(("kv", "IMMAGINE XFCE", human(os.path.getsize(img)), FG))

        L.append(("sec", "wifi", "RETE"))
        wtxt = st["ssid"] or ("connesso" if st.get("conn") else
                              "non connesso")
        L.append(("kv", "WIFI", wtxt, OK_G if st.get("conn") else DIM))
        if st.get("iface"):
            L.append(("kv", "INTERFACCIA", st["iface"], FG))
        if st["wifi"] is not None:
            L.append(("kv", "SEGNALE", "%d/3 tacche" % st["wifi"], FG))
        addr = st.get("ip")
        L.append(("kv", "INDIRIZZO IP", addr or "n/d", FG if addr else DIM))
        L.append(("kv", "BLUETOOTH",
                  "n/d" if st["bt"] is None else
                  ("attivo" if st["bt"] else "spento"),
                  OK_G if st["bt"] else DIM))
        L.append(("kv", "INTERNET", net_test(), FG))

        L.append(("sec", "speaker", "AUDIO"))
        L.append(("kv", "VOLUME", "%d%%" % st["vol"] if st["vol"] is not None
                  else "n/d", FG))

        L.append(("sec", "desktop", "DESKTOP XFCE"))
        ready = os.path.exists(os.path.join(DATA, ".xfce_ready"))
        L.append(("kv", "STATO", "installato" if ready else "non installato",
                  OK_G if ready else NO_R))
        last = ""
        try:
            for ln in open(os.path.join(DATA, "xfce_session.log"),
                           errors="replace"):
                if "sessione terminata" in ln:
                    last = ln.strip().split()[-1]
        except OSError:
            pass
        if last:
            L.append(("kv", "ULTIMA SESSIONE",
                  ("uscita %s" if self.lang == "it" else "exit %s") % last,
                  FG))
        L.append(("kv", "CONTROLLER", self.cfg.get("controller",
                                                   "sinistro"), FG))

        L.append(("sec", "gear", "VOID BOOST"))
        bon = self.cfg.get("boost", True)
        L.append(("kv", "STATO", "attivo" if bon else "spento",
                  OK_G if bon else DIM))
        binfo = []
        try:
            binfo = open(os.path.join(DATA, ".boost_info")
                         ).read().strip().splitlines()
        except OSError:
            pass
        for ln in binfo[:3]:
            L.append(("kv", "", ln, FG))
        if bon and not binfo:
            L.append(("kv", "", "dettagli al primo avvio del desktop"
                      if self.lang == "it"
                      else "details at the next desktop launch", DIM))

        L.append(("sec", "python", "RUNTIME"))
        L.append(("kv", "PYTHON", sys.version.split()[0], FG))
        L.append(("kv", "PYGAME", "%s (SDL %s)" % (
            pygame.version.ver,
            ".".join(map(str, pygame.get_sdl_version()))), FG))
        miss = [c for c in ("curl", "gzip", "tar", "chroot", "mount")
                if not any(os.access(os.path.join(d, c), os.X_OK)
                           for d in os.environ.get("PATH", "").split(":"))]
        L.append(("kv", "DIPENDENZE",
                  ("tutte presenti" if self.lang == "it" else "all present")
                  if not miss else
                  (("mancanti: %s" if self.lang == "it" else "missing: %s")
                   % ", ".join(miss)), OK_G if not miss else NO_R))
        return L

    def about_lines(self):
        it = (self.lang == "it")
        L = [("sec", "info", "VOID SUITE")]
        L.append(("kv", "VOIDDESK", "v%s  -  %s" % (VERSION,
                  ("pannello di controllo + desktop XFCE" if it
                   else "control panel + XFCE desktop")), FG))
        L.append(("kv", "VOIDCAST", "v2.2  -  %s" %
                  ("IPTV, EPG, registrazione" if it
                   else "IPTV, EPG, recording"), FG))
        L.append(("kv", "VOIDDIAG", "v1.5  -  %s" %
                  ("report diagnostico" if it else "diagnostic report"), FG))
        L.append(("sec", "xorg", "PIATTAFORMA" if it else "PLATFORM"))
        L.append(("kv", "TARGET", "Anbernic RG35XX-H", FG))
        L.append(("kv", "OS", "muOS 2601 Jacaranda", FG))
        L.append(("kv", "DESKTOP", "Ubuntu 24.04 + XFCE (chroot ext4)", FG))
        L.append(("kv", "UI", "pygame su /dev/fb0, input evdev", FG))
        L.append(("sec", "gear", "COME FUNZIONA" if it else "HOW IT WORKS"))
        for t in (("immagine ext4 in loopback: aggira i limiti di exFAT"
                   if it else
                   "loopback ext4 image: works around exFAT limits"),
                  ("Xorg su framebuffer, senza GPU"
                   if it else "Xorg on framebuffer, no GPU"),
                  ("QJoyPad traduce il gamepad in mouse e tasti"
                   if it else "QJoyPad turns the gamepad into mouse and keys"),
                  ("START+SELECT: pannello LIVE sopra XFCE"
                   if it else "START+SELECT: LIVE panel over XFCE")):
            L.append(("kv", "", t, DIM))
        L.append(("sec", "git", "CREDITI" if it else "CREDITS"))
        L.append(("kv", "SPDW FACTORY", "Void suite - universo ß", FG))
        L.append(("kv", "MustardOS", "muOS - mustard.foo", DIM))
        L.append(("kv", "MrJackSpade", "RG35XXP-XFCE (ispirazione)"
                  if it else "RG35XXP-XFCE (inspiration)", DIM))
        L.append(("kv", "iptv-org", "liste IPTV libere" if it
                  else "free IPTV playlists", DIM))
        L.append(("kv", "nvcuong1312/bltMuos",
                  "accensione BT (rfkill, HCI, bluetoothd)" if it else
                  "BT bring-up (rfkill, HCI, bluetoothd)", DIM))
        L.append(("kv", "nvcuong1312/hotspotmuos",
                  "ispirazione (SSID/subnet); hotspot ora nativo "
                  "hostapd+dnsmasq" if it else
                  "inspiration (SSID/subnet); hotspot now native "
                  "hostapd+dnsmasq", DIM))
        L.append(("kv", "amosjerbi/WiFi_Manager",
                  "rilevamento via iw + riconnessione di riserva" if it
                  else "iw-based detection + reconnect fallback", DIM))
        L.append(("kv", "open-meteo.com",
                  "dati meteo e geocoding, libero e senza chiave" if it
                  else "weather data and geocoding, free and keyless",
                  DIM))
        L.append(("kv", "", "DejaVu Fonts - pygame - Ubuntu Ports", DIM))
        L.append(("sec", "info", "IL MANIFESTO" if it else "THE MANIFESTO"))
        if it:
            L.append(("kv", "", "A I.R. Minoru, ovunque tu sia nel "
                      "universo \u03b2: questa ha smesso di essere "
                      "una semplice app desktop da un pezzo.", DIM))
            L.append(("kv", "", "E' un intero universo, infilato a "
                      "forza dentro una console da 200 grammi che non "
                      "avrebbe dovuto contenerlo.", DIM))
            L.append(("kv", "", "Ogni corrente l'abbiamo cavalcata "
                      "noi. Ogni dettaglio, curato apposta fino "
                      "all'osso.", DIM))
            L.append(("kv", "", "Probabilmente non userai mai meta' "
                      "di quello che c'e' qui dentro. Non importa: "
                      "esiste, funziona, e l'abbiamo fatto noi.", FG))
        else:
            L.append(("kv", "", "To I.R. Minoru, wherever you are in "
                      "the \u03b2 universe: this stopped being a "
                      "plain desktop app a while ago.", DIM))
            L.append(("kv", "", "It's a whole universe, forced into a "
                      "200-gram handheld that was never meant to hold "
                      "it.", DIM))
            L.append(("kv", "", "Every current, we rode it ourselves. "
                      "Every detail, obsessed over on purpose.", DIM))
            L.append(("kv", "", "You'll probably never use half of "
                      "what's in here. Doesn't matter: it exists, it "
                      "works, and we built it.", FG))
        return L

    def logs_archive(self, dest_root):
        """Zip di tutti i log del registro (build_logs()), in una
        cartella dedicata sulla destinazione scelta. Ritorna
        (ok, messaggio/percorso)."""
        import zipfile
        dbg = os.path.join(DATA, "log_archive.log")

        def log(msg):
            try:
                with open(dbg, "a") as f:
                    f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
            except OSError:
                pass
        try:
            log("avvio: dest_root=%r, self.logs ha %d voci" %
                (dest_root, len(self.logs)))
            out_dir = os.path.join(dest_root, "VoidDesk_Backups")
            os.makedirs(out_dir, exist_ok=True)
            log("cartella pronta: %s" % out_dir)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(out_dir,
                                    "voiddesk_logs_%s.zip" % stamp)
            n = 0
            with zipfile.ZipFile(out_path, "w",
                                 zipfile.ZIP_DEFLATED) as z:
                for entry in self.logs:
                    if entry[0] == "hdr":
                        continue
                    name, path = entry
                    exists = path and os.path.isfile(path)
                    log("  %s -> %s (esiste=%r)" % (name, path, exists))
                    if exists:
                        arcname = os.path.basename(path)
                        try:
                            z.write(path, arcname)
                            n += 1
                        except OSError as e:
                            log("  errore scrivendo %s nello zip: %r" %
                                (path, e))
            log("completato: %s, %d file inclusi" % (out_path, n))
            try:
                fd = os.open(out_path, os.O_RDONLY)
                os.fsync(fd)
                os.close(fd)
                dfd = os.open(out_dir, os.O_RDONLY)
                os.fsync(dfd)
                os.close(dfd)
            except OSError as e:
                log("fsync non riuscito (non fatale): %r" % e)
            return True, (out_path, n)
        except Exception as e:
            log("ECCEZIONE: %r" % e)
            return False, str(e)[:160]

    def logs_total_size(self):
        total = 0
        n = 0
        for entry in self.logs:
            if entry[0] == "hdr":
                continue
            _name, path = entry
            try:
                total += os.path.getsize(path)
                n += 1
            except OSError:
                pass
        return total, n

    def build_logs(self):
        it = (self.lang == "it")
        H = lambda t_: ("hdr", t_)
        E = lambda n, p: (n, p)
        return [
            H("VOID DESK"),
            E("voiddesk.log", LOG),
            E("vd_hotkey.log", os.path.join(DATA, "vd_hotkey.log")),
            E("deps_check.log", os.path.join(DATA, "deps_check.log")),
            E("log_archive.log", os.path.join(DATA, "log_archive.log")),
            H("SESSIONI DESKTOP" if it else "DESKTOP SESSIONS"),
            E("session_xfce.log", os.path.join(DATA, "session_xfce.log")),
            E("session_icewm.log", os.path.join(DATA, "session_icewm.log")),
            E("session_lxde.log", os.path.join(DATA, "session_lxde.log")),
            E("storico sessioni" if it else "sessions history",
              os.path.join(DATA, "xfce_session.log")),
            H("CLI TOOLS"),
            E("xterm.log", os.path.join(DATA, "xterm.log")),
            E("ani_cli.log", os.path.join(DATA, "ani_cli.log")),
            H("INSTALLER"),
            E("install.log (software)", os.path.join(DATA, "install.log")),
            E("bootstrap ambienti" if it else "env bootstrap",
              os.path.join(DATA, "bootstrap.log")),
            E("post_install_check.log",
              os.path.join(DATA, "post_install_check.log")),
            H("RETE" if it else "NETWORK"),
            E("hotspot.log", os.path.join(DATA, "hotspot.log")),
            E("syncthing.log", os.path.join(DATA, "syncthing.log")),
            H("MEDIA"),
            E("voidcast.log", os.path.join(os.path.dirname(APP_DIR),
                                           "VoidCast", "voidcast.log")),
            E("mpv.log", os.path.join(os.path.dirname(APP_DIR),
                                      "VoidCast", "mpv.log")),
        ]

    def manifesto_lines(self):
        it = (self.lang == "it")
        if it:
            return [
                ("sys", "anonimo@ß-relay ha stabilito una connessione."),
                ("sys", "[in attesa di risposta dall'altro capo...]"),
                ("gap", ""),
                ("msg", "non sappiamo chi legge questo. non sappiamo "
                 "nemmeno se qualcuno lo far\u00e0 mai. ma se sei "
                 "arrivato fin qui, dentro un menu nascosto di un "
                 "firmware nascosto su una consolina che nessuno "
                 "guardava pi\u00f9 -- allora forse sei uno di noi."),
                ("gap", ""),
                ("msg", "VoidDesk non \u00e8 nato per essere perfetto. "
                 "\u00e8 nato perch\u00e9 il firmware di fabbrica non "
                 "bastava, e perch\u00e9 \"non si pu\u00f2 fare\" non "
                 "\u00e8 mai stata una risposta che ci ha convinto."),
                ("gap", ""),
                ("msg", "IR Minoru\u2076 osserva da qualche parte "
                 "nell'universo \u03b2. non sappiamo cosa veda. "
                 "sappiamo solo che ogni volta che qualcuno smonta, "
                 "ricompila, rompe e ripara qualcosa che non gli "
                 "apparteneva davvero -- il VOID si allarga un poco."),
                ("gap", ""),
                ("msg", "continua a smontare le cose."),
                ("gap", ""),
                ("sig", "-- SPDW Factory, da qualche parte nel VOID"),
            ]
        return [
            ("sys", "anon@\u03b2-relay has established a connection."),
            ("sys", "[waiting for a reply from the other end...]"),
            ("gap", ""),
            ("msg", "we don't know who's reading this. we don't even "
             "know if anyone ever will. but if you made it this far, "
             "inside a hidden menu of a hidden firmware on a handheld "
             "nobody looked at twice anymore -- then maybe you're "
             "one of us."),
            ("gap", ""),
            ("msg", "VoidDesk wasn't built to be perfect. it was "
             "built because the factory firmware wasn't enough, and "
             "because \"you can't do that\" was never an answer "
             "that convinced us."),
            ("gap", ""),
            ("msg", "IR Minoru\u2076 watches from somewhere in the "
             "\u03b2 universe. we don't know what it sees. we only "
             "know that every time someone takes something apart, "
             "recompiles it, breaks it and fixes it again -- "
             "something that wasn't really theirs to begin with -- "
             "the VOID grows a little wider."),
            ("gap", ""),
            ("msg", "keep taking things apart."),
            ("gap", ""),
            ("sig", "-- SPDW Factory, somewhere in the VOID"),
        ]

    def guide_lines(self):
        it = (self.lang == "it")

        def kv(k, v, c=FG):
            return ("kv", k, v, c)

        L = [("sec", "gamepad", "NEL MENU" if it else "IN THE MENU")]
        L.append(kv("A / B", "conferma / indietro" if it
                    else "confirm / back"))
        L.append(kv("SX / DX", "salta di categoria (componenti)" if it
                    else "jump by category (components)"))
        L.append(kv("X / Y", "seleziona / tutti-nessuno" if it
                    else "mark / all-none"))
        L.append(kv("R1", "aggiorna lo stato dei componenti" if it
                    else "refresh component status"))
        L.append(("sec", "desktop", "DENTRO XFCE" if it else "INSIDE XFCE"))
        L.append(kv("STICK", "muove il mouse" if it else "moves the mouse"))
        L.append(kv("A / X", "click sinistro / destro" if it
                    else "left / right click"))
        L.append(kv("L1 / R1", "rotella giu' / su" if it
                    else "wheel down / up"))
        L.append(kv("MENU", "tastiera a schermo" if it
                    else "on-screen keyboard"))
        L.append(kv("START+SELECT", "pannello LIVE (volume, esci...)" if it
                    else "LIVE panel (volume, quit...)", self.accent))
        L.append(kv("", "per uscire: Logout dal menu XFCE" if it
                    else "to quit: Logout from the XFCE menu", DIM))
        L.append(("sec", "gear", "SE QUALCOSA VA STORTO" if it
                  else "IF SOMETHING BREAKS"))
        L.append(kv("", "i diari sono in LOGS & ABOUT" if it
                    else "log files live in LOGS & ABOUT", DIM))
        L.append(kv("", "mappatura tasti: OPZIONI > Mappatura" if it
                    else "button mapping: SETTINGS > Mapping", DIM))
        L.append(kv("", "ambiente: prima voce START SESSION" if it
                    else "environment: first entry START SESSION", DIM))
        return L

    def load_log(self, path):
        self._viewer_path = path
        self.viewer_live = False
        self.wm_nets = []
        self.wm_sel = 0
        self.bt_devs = []
        self.bt_sel = 0
        try:
            with open(path, "rb") as f:
                txt = f.read()[-40000:].decode("utf-8", "replace")
            self.log_lines = txt.splitlines()[-400:] or ["(vuoto)"]
        except OSError:
            self.log_lines = ["file non trovato:", path]
        self.scroll = max(0, len(self.log_lines) - 23)

    # ------------------------------------------------------------- opzioni
    def opt_defs(self):
        it = (self.lang == "it")
        return [
            ("hdr", "ASPETTO" if it else "LOOK", None),
            ("opt_theme", "theme", list(ACCENTS.keys())),
            ("opt_home_style", "home_style", HOME_STYLES),
            ("opt_font_scale", "font_scale", CYCLES["fscale"][1]),
            ("opt_fx", "fx", [True, False]),
            ("opt_anim", "anim", [True, False]),
            ("opt_intro", "intro", [True, False]),
            ("opt_batt", "battery", [True, False]),
            ("hdr", "STATUS BAR", None),
            ("opt_st_clock", "clock_badge", [True, False]),
            ("opt_st_batt", "st_batt", [True, False]),
            ("opt_st_vol", "st_vol", [True, False]),
            ("opt_st_bt", "st_bt", [True, False]),
            ("opt_st_wifi", "st_wifi", [True, False]),
            ("opt_st_usb", "st_usb", [True, False]),
            ("opt_st_hotspot", "st_hotspot", [True, False]),
            ("hdr", "AUDIO", None),
            ("opt_sfx", "sfx", [True, False]),
            ("opt_bgm", "bgm", [True, False]),
            ("hdr", "LINGUA APP" if it else "APP LANGUAGE", None),
            ("opt_lang", "lang", ["it", "en"]),
        ]

    # ---- mappatura tasti ---------------------------------------------
    def cur_map(self):
        m = self.cfg.get("map")
        if not m:
            m = default_map()
            self.cfg["map"] = m
        return m

    def map_rows(self):
        """Riga 0 = stick del mouse, poi una riga per funzione."""
        return ["__stick__"] + [f[0] for f in FUNCS]

    def btn_names(self, evs):
        return ", ".join(EV2NAME.get(e, "?") for e in evs) or self.t("none")

    def owner_of(self, ev, skip):
        for k, evs in self.cur_map().items():
            if k != skip and ev in evs:
                return k
        return None

    def apply_map(self):
        """Scrive il layout personalizzato e attiva il profilo custom."""
        self.cfg["controller"] = "custom"
        write_custom_layout(self.cfg, os.path.join(DATA,
                                                   "qjoypad_custom.lyt"))
        with open(os.path.join(DATA, ".qjoypad_profile"), "w") as f:
            f.write("custom\n")
        save_cfg(self.cfg)

    # -------------------------------------------------------------- input
    def on_button(self, btn):
        if btn in ("UP", "DOWN", "LEFT", "RIGHT"):
            self.play("move")
        top = self.stack[-1]
        if top == "home":
            style = self.cfg.get("home_style", "blame")
            if btn == "Y":
                idx = (HOME_STYLES.index(style) + 1) % len(HOME_STYLES)
                self.cfg["home_style"] = HOME_STYLES[idx]
                save_cfg(self.cfg)
                self.sel = 0
                self.play("snap")
                return
            if style == "blame":
                if btn == "UP":
                    if self.sel == 0:
                        self.sel = len(self.menu) - 1
                    elif self.sel <= 2:
                        self.sel = 0
                    else:
                        self.sel -= 2
                elif btn == "DOWN":
                    if self.sel == 0:
                        self.sel = 1
                    elif self.sel >= len(self.menu) - 2:
                        self.sel = 0
                    else:
                        self.sel += 2
                elif btn == "LEFT":
                    if self.sel > 0 and (self.sel - 1) % 2 == 1:
                        self.sel -= 1
                    elif self.sel > 0:
                        self.sel += 1
                elif btn == "RIGHT":
                    if self.sel > 0 and (self.sel - 1) % 2 == 0:
                        self.sel += 1
                    elif self.sel > 0:
                        self.sel -= 1
                elif btn == "A":
                    self.activate(self.sel)
                elif btn in ("B", "START"):
                    self.crt_off()
            elif style in ("hud", "terminal"):
                if btn == "UP":
                    self.sel = (self.sel - 1) % len(self.menu)
                elif btn == "DOWN":
                    self.sel = (self.sel + 1) % len(self.menu)
                elif btn == "A":
                    self.activate(self.sel)
                elif btn in ("B", "START"):
                    self.crt_off()
            elif style == "orbit":
                if btn in ("LEFT", "UP"):
                    self.sel = (self.sel - 1) % len(self.menu)
                elif btn in ("RIGHT", "DOWN"):
                    self.sel = (self.sel + 1) % len(self.menu)
                elif btn == "A":
                    self.activate(self.sel)
                elif btn in ("B", "START"):
                    self.crt_off()
            elif style == "nexus":
                if btn in ("LEFT", "UP"):
                    self.nexus_travel(-1)
                elif btn in ("RIGHT", "DOWN"):
                    self.nexus_travel(1)
                elif btn == "A":
                    self.activate(self.sel)
                elif btn in ("B", "START"):
                    self.crt_off()
        elif top == "muosapps":
            n = len(self.mapps)
            view = self.cfg.get("mapp_view", "list")
            cols = self.mapp_grid_cols if view == "grid" else 1
            if btn == "UP" and n:
                self.mapp_sel = (self.mapp_sel - cols) % n
            elif btn == "DOWN" and n:
                self.mapp_sel = (self.mapp_sel + cols) % n
            elif btn == "LEFT" and n and view == "grid":
                if self.mapp_sel % cols > 0:
                    self.mapp_sel -= 1
            elif btn == "RIGHT" and n and view == "grid":
                if self.mapp_sel % cols < cols - 1 and \
                        self.mapp_sel + 1 < n:
                    self.mapp_sel += 1
            elif btn == "Y":
                i2 = (MAPP_VIEWS.index(view) + 1) % len(MAPP_VIEWS)
                self.cfg["mapp_view"] = MAPP_VIEWS[i2]
                save_cfg(self.cfg)
            elif btn == "R1":
                self.run_busy(self.t("mapps_scan"), self.normalize_glyphs)
                self.mapp_sel = min(self.mapp_sel,
                                    max(0, len(self.mapps) - 1))
            elif btn == "A" and n:
                self.launch_muos(self.mapps[self.mapp_sel])
            elif btn == "X" and n:
                self.mapp_cur = self.mapps[self.mapp_sel]
                self.det_sel = 0
                self.mapp_size = self.run_busy(
                    self.t("checking"),
                    lambda: self.app_size(self.mapp_cur["dir"]))
                self.push("mappdetail")
            elif btn == "B":
                self.pop_state()
        elif top == "session":
            base, extra = self.read_envs()
            if btn == "UP":
                self.env_sel = (self.env_sel - 1) % len(ENVS)
            elif btn == "DOWN":
                self.env_sel = (self.env_sel + 1) % len(ENVS)
            elif btn == "A":
                env, _lbl, pkgs = ENVS[self.env_sel]
                self.cfg["desk_env"] = env
                save_cfg(self.cfg)
                up = env.upper()
                if not base:
                    # niente base: qualsiasi scelta parte dall'installazione
                    # completa; l'ambiente scelto restera' in config
                    self.handoff(self.t("ho_inst"))
                    self.exit_code = EXIT_XFCE_INSTALL
                elif env == "xfce" or env in extra:
                    self.handoff(("AVVIO DESKTOP %s..." if self.lang == "it"
                                  else "STARTING %s DESKTOP...") % up)
                    self.exit_code = EXIT_XFCE_LAUNCH
                else:
                    os.makedirs(DATA, exist_ok=True)
                    with open(os.path.join(DATA, ".install_pkg"),
                              "w") as f:
                        f.write("%s\n%s\n" % (up, pkgs))
                    self.handoff(("INSTALLO %s..." if self.lang == "it"
                                  else "INSTALLING %s...") % up)
                    self.exit_code = EXIT_PKG_INSTALL
                self.running = False
            elif btn == "X":
                self.envdet_env = ENVS[self.env_sel][0]
                self.envdet_sel = 0
                self.push("envdetail")
            elif btn == "B":
                self.pop_state()
        elif top == "envdetail":
            env = self.envdet_env
            base, extra = self.read_envs()
            inst = base and (env == "xfce" or env in extra)
            acts = self.env_detail_actions(env, base, inst)
            if btn == "UP":
                self.envdet_sel = (self.envdet_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.envdet_sel = (self.envdet_sel + 1) % len(acts)
            elif btn == "A":
                self.env_detail_do(env, acts[self.envdet_sel][0])
            elif btn == "B":
                self.pop_state()
        elif top == "comp":
            if btn == "UP":
                self.move_rows(-1)
            elif btn == "DOWN":
                self.move_rows(1)
            elif btn == "LEFT":
                self.jump_category(-1)
            elif btn == "RIGHT":
                self.jump_category(1)
            elif btn == "X":
                if (self.mode == "remove" and not
                        self.status.get(self.rows[self.row_sel][1])):
                    return
                if self.row_sel in self.marked:
                    self.marked.discard(self.row_sel)
                else:
                    self.marked.add(self.row_sel)
            elif btn == "Y":
                items = {i for i, r in enumerate(self.rows) if r[0] == "item"}
                self.marked = set() if self.marked else items
            elif btn == "L1":
                if self.mode != "install":
                    self.mode = "install"
                    self.marked.clear()
                    self.play("open")
            elif btn == "R1":
                if self.mode != "remove":
                    self.mode = "remove"
                    self.marked.clear()
                    self.play("open")
            elif btn == "SELECT":
                self.run_busy(self.t("mounting"), self.scan_status)
            elif btn == "START":
                self.toggle_category()
            elif btn == "A":
                if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
                    self.info_lines = [("sec", "info", self.t("need_xfce"))]
                    self.push("info")
                else:
                    self.install_marked()
            elif btn == "B":
                self.marked.clear()
                self.pop_state()
        elif top == "autostart":
            rows = [r for r in self.rows if r[0] == "item"]
            auto = set(self.cfg.get("autostart", []))
            if btn == "UP":
                self.row_sel = (self.row_sel - 1) % len(rows)
            elif btn == "DOWN":
                self.row_sel = (self.row_sel + 1) % len(rows)
            elif btn == "A":
                name, exe = rows[self.row_sel][1], rows[self.row_sel][2]
                if name == "-":
                    return
                execs = set(self.cfg.get("autostart_exec", []))
                if name in auto:
                    auto.discard(name)
                    execs.discard(exe)
                else:
                    auto.add(name)
                    execs.add(exe)
                self.cfg["autostart"] = sorted(auto)
                self.cfg["autostart_exec"] = sorted(execs)
                save_cfg(self.cfg)
            elif btn == "B":
                save_cfg(self.cfg)
                self.pop_state()
        elif top == "options":
            defs = self.opt_defs()
            if btn in ("UP", "DOWN"):
                d = -1 if btn == "UP" else 1
                k = self.opt_sel
                for _ in range(len(defs)):
                    k = (k + d) % len(defs)
                    if defs[k][0] != "hdr":
                        break
                self.opt_sel = k
                self.opt_scroll = max(0, min(self.opt_sel - 5,
                                             max(0, len(defs) - 10)))
            elif btn == "A":
                key, ck, vals = defs[self.opt_sel]
                if key == "hdr" or not vals:
                    return
                cur = self.cfg.get(ck, vals[0])
                nxt = vals[(vals.index(cur) + 1) % len(vals)
                           if cur in vals else 0]
                self.cfg[ck] = nxt
                if ck == "theme":
                    self.accent = ACCENTS[nxt]
                    self.build_style()
                elif ck == "font_scale":
                    self.build_fonts()
                elif ck == "lang":
                    self.lang = nxt
                    self.rebuild_menu()
                    self.logs = self.build_logs()
            elif btn == "B":
                save_cfg(self.cfg)
                self.pop_state()
        elif top == "map":
            rows = self.map_rows()
            if btn == "UP":
                self.map_sel = (self.map_sel - 1) % len(rows)
            elif btn == "DOWN":
                self.map_sel = (self.map_sel + 1) % len(rows)
            elif btn == "A":
                if rows[self.map_sel] == "__stick__":
                    cur = self.cfg.get("mouse_stick", "sinistro")
                    self.cfg["mouse_stick"] = ("destro" if cur == "sinistro"
                                               else "sinistro")
                    self.apply_map()
                else:
                    self.capture_t = time.time()
                    if self.js_fd is None:
                        self.js_fd = jsmap.js_open()
                    jsmap.js_poll(self.js_fd)     # svuota gli eventi vecchi
                    self.push("capture")
            elif btn == "Y":
                key = rows[self.map_sel]
                if key != "__stick__":
                    self.cur_map()[key] = list(FUNC_BY_KEY[key][5])
                    self.apply_map()
            elif btn == "X":
                self.cfg["map"] = default_map()
                self.cfg["mouse_stick"] = "sinistro"
                self.apply_map()
            elif btn == "B":
                self.apply_map()
                self.pop_state()
        elif top == "swap":
            if btn == "A":
                key, ev, other = self.pending
                m = self.cur_map()
                old = list(m[key])
                m[other] = [e for e in m[other] if e != ev] + old
                m[key] = [ev]
                self.apply_map()
                self.pop_state()
            elif btn == "B":
                self.pop_state()
        elif top == "logs":
            n = len(self.logs)
            if btn in ("UP", "DOWN") and n:
                d = -1 if btn == "UP" else 1
                k = self.sel_log
                for _ in range(n):
                    k = (k + d) % n
                    if self.logs[k][0] != "hdr":
                        break
                self.sel_log = k
            elif btn == "A" and n and self.logs[self.sel_log][0] != "hdr":
                self.scroll = 0
                self.load_log(self.logs[self.sel_log][1])
                self.push("viewer")
            elif btn == "X":
                self.logarchive_sel = 0
                self.push("logarchive")
            elif btn == "B":
                self.pop_state()
        elif top == "logarchive":
            roots = self.fm_roots()
            actions = [("sd:" + p, lbl) for p, lbl in roots] + \
                [("clear", None)]
            n = len(actions)
            if btn == "UP":
                self.logarchive_sel = (self.logarchive_sel - 1) % n
            elif btn == "DOWN":
                self.logarchive_sel = (self.logarchive_sel + 1) % n
            elif btn == "A":
                act, _lbl = actions[self.logarchive_sel]
                if act == "clear":
                    def go():
                        n_del = 0
                        for entry in self.logs:
                            if entry[0] == "hdr":
                                continue
                            _nm, path = entry
                            try:
                                open(path, "w").close()
                                n_del += 1
                            except OSError:
                                pass
                        self.info_lines = self.stub_lines(
                            "LOG REGISTRY",
                            [("%d file svuotati" if self.lang == "it"
                             else "%d files cleared") % n_del])
                        self.scroll = 0
                        self.pop_state()
                        self.push("info")
                    self.confirm = (("svuotare tutti i log?" if
                                     self.lang == "it" else
                                     "clear all logs?"), go)
                    self.push("confirm")
                else:
                    dest = act[3:]
                    ok, res = self.run_busy(
                        self.t("checking"), lambda: self.logs_archive(
                            dest))
                    if ok:
                        path, cnt = res
                        msg = (("archivio creato: %s (%d file)" %
                               (path, cnt)) if self.lang == "it" else
                               ("archive created: %s (%d files)" %
                               (path, cnt)))
                    else:
                        msg = res
                    self.info_lines = self.stub_lines("LOG REGISTRY",
                                                      [msg])
                    self.scroll = 0
                    self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top.startswith("hub:") and top[4:] == "uplink":
            items = HUBS["uplink"][2]
            n = len(items)
            if self.hub_sel < 3:
                if btn == "LEFT":
                    self.hub_sel = (self.hub_sel - 1) % 3
                elif btn == "RIGHT":
                    self.hub_sel = (self.hub_sel + 1) % 3
                elif btn == "DOWN":
                    self.hub_sel = 3
                elif btn == "UP":
                    self.hub_sel = n - 1
                elif btn == "A":
                    k, ic, lk, sk, kind = items[self.hub_sel]
                    self.hub_action("uplink", k, kind)
                elif btn == "B":
                    self.pop_state()
            else:
                if btn == "UP":
                    self.hub_sel = self.hub_sel - 1 if self.hub_sel > 3 \
                        else 0
                elif btn == "DOWN":
                    self.hub_sel = self.hub_sel + 1 if \
                        self.hub_sel < n - 1 else 0
                elif btn == "A":
                    k, ic, lk, sk, kind = items[self.hub_sel]
                    self.hub_action("uplink", k, kind)
                elif btn == "B":
                    self.pop_state()
        elif top.startswith("hub:"):
            hub = top[4:]
            items = HUBS[hub][2]
            if btn == "UP":
                self.hub_sel = (self.hub_sel - 1) % len(items)
            elif btn == "DOWN":
                self.hub_sel = (self.hub_sel + 1) % len(items)
            elif btn == "A":
                k, ic, lk, sk, kind = items[self.hub_sel]
                self.hub_action(hub, k, kind)
            elif btn == "B":
                self.pop_state()
        elif top == "boostcfg":
            keys = ["boost_swap", "boost_cpu"]
            if btn in ("UP", "DOWN"):
                self.boost_sel = 1 - self.boost_sel
            elif btn == "A":
                ck = keys[self.boost_sel]
                self.cfg[ck] = not self.cfg.get(ck, True)
                save_cfg(self.cfg)
            elif btn == "B":
                self.pop_state()
        elif top == "clock":
            if btn == "Y":
                self.cfg["clock_layout"] = (
                    self.cfg.get("clock_layout", 0) + 1) % \
                    len(CLOCK_LAYOUTS)
                save_cfg(self.cfg)
            elif btn == "X":
                lt = time.localtime()
                self.clock_v = [lt.tm_year, lt.tm_mon, lt.tm_mday,
                                lt.tm_hour, lt.tm_min,
                                max(0, TZS.index(self.cfg.get(
                                    "tz", "UTC")) if self.cfg.get(
                                    "tz", "UTC") in TZS else 0)]
                self.clock_f = 0
                self.push("clocksettings")
            elif btn == "A":
                self.alarm_sel = 0
                self.push("alarmlist")
            elif btn == "B":
                self.pop_state()
        elif top == "alarmlist":
            lst = self.alarms()
            n = len(lst) + 1
            if btn == "UP":
                self.alarm_sel = (self.alarm_sel - 1) % n
            elif btn == "DOWN":
                self.alarm_sel = (self.alarm_sel + 1) % n
            elif btn == "A":
                if self.alarm_sel == 0:
                    self.alarm_edit = None
                    self.aw = [7, 0, 0]
                    self.aw_f = 0
                    self.aw_title = ""
                    self.push("alarmwhen")
                else:
                    a = lst[self.alarm_sel - 1]
                    self.alarm_edit = self.alarm_sel - 1
                    self.aw = [a["h"], a["m"],
                              ALARM_SOUNDS.index(a.get("sound",
                                                       "classic"))
                              if a.get("sound") in ALARM_SOUNDS else 0]
                    self.aw_f = 0
                    self.aw_title = a.get("label", "")
                    self.push("alarmwhen")
            elif btn == "X" and self.alarm_sel > 0:
                idx = self.alarm_sel - 1

                def rm(idx=idx):
                    self.alarm_delete(idx)
                    self.alarm_sel = 0
                self.confirm = (lst[idx].get("label") or
                                "%02d:%02d" % (lst[idx]["h"],
                                              lst[idx]["m"]), rm)
                self.push("confirm")
            elif btn == "Y" and self.alarm_sel > 0:
                self.alarm_toggle(self.alarm_sel - 1)
            elif btn == "B":
                self.pop_state()
        elif top == "alarmwhen":
            lim = [(0, 23), (0, 59), (0, len(ALARM_SOUNDS) - 1)]
            if btn == "UP":
                self.aw_f = (self.aw_f - 1) % 3
            elif btn == "DOWN":
                self.aw_f = (self.aw_f + 1) % 3
            elif btn in ("LEFT", "RIGHT"):
                d = 1 if btn == "RIGHT" else -1
                lo, hi = lim[self.aw_f]
                self.aw[self.aw_f] = lo + (self.aw[self.aw_f] - lo +
                                           d) % (hi - lo + 1)
            elif btn == "Y":
                def done(t):
                    self.aw_title = t.strip()
                self.osk_open("ETICHETTA" if self.lang == "it"
                              else "LABEL", self.aw_title, done)
            elif btn == "A":
                self.alarm_add_or_edit(
                    self.alarm_edit, self.aw[0], self.aw[1],
                    ALARM_SOUNDS[self.aw[2]], self.aw_title)
                self.pop_state()
            elif btn == "B":
                self.pop_state()
        elif top == "alarmring":
            if btn in ("A", "B"):
                self.alarm_dismiss()
        elif top == "weather":
            it = (self.lang == "it")
            cities = self.cfg.get("weather_cities") or []
            n = len(cities) + 1
            if btn == "UP":
                self.wx_sel = (self.wx_sel - 1) % n
            elif btn == "DOWN":
                self.wx_sel = (self.wx_sel + 1) % n
            elif btn == "A":
                if self.wx_sel == 0:
                    def done(t):
                        t = t.strip()
                        if not t:
                            return
                        res = self.run_busy(self.t("wx_searching"),
                                            lambda: self.wx_geocode(t))
                        if not res:
                            self.info_lines = self.stub_lines(
                                self.t("t_wx"), [self.t("wx_notfound")])
                            self.scroll = 0
                            self.push("info")
                        elif len(res) == 1:
                            self.wx_add_city(res[0])
                            self.run_busy(self.t("wx_updating"),
                                         self.wx_refresh_all)
                        else:
                            self.wx_pick_results = res
                            self.wx_pick_sel = 0
                            self.push("weatherpick")
                    self.osk_open("CITTA'" if it else "CITY", "", done)
                else:
                    city = cities[self.wx_sel - 1]
                    self.wx_detail_city = city
                    if city["name"] not in self.wx_data:
                        self.run_busy(self.t("wx_updating"),
                                     self.wx_refresh_all)
                    self.push("weatherdetail")
            elif btn == "X" and self.wx_sel > 0:
                idx = self.wx_sel - 1

                def rm(idx=idx):
                    self.wx_remove_city(idx)
                    self.wx_sel = 0
                self.confirm = (cities[idx]["name"], rm)
                self.push("confirm")
            elif btn == "R1" and cities:
                self.run_busy(self.t("wx_updating"), self.wx_refresh_all)
            elif btn == "B":
                self.pop_state()
        elif top == "weatherpick":
            n = len(self.wx_pick_results)
            if btn == "UP" and n:
                self.wx_pick_sel = (self.wx_pick_sel - 1) % n
            elif btn == "DOWN" and n:
                self.wx_pick_sel = (self.wx_pick_sel + 1) % n
            elif btn == "A" and n:
                res = self.wx_pick_results[self.wx_pick_sel]
                self.wx_add_city(res)
                self.pop_state()
                self.run_busy(self.t("wx_updating"), self.wx_refresh_all)
            elif btn == "B":
                self.pop_state()
        elif top == "weatherdetail":
            if btn == "R1":
                self.run_busy(self.t("wx_updating"), self.wx_refresh_all)
            elif btn == "B":
                self.pop_state()
        elif top == "depsmissing":
            if btn == "A":
                self.pop_state()
                self.comp_action("install")
                self.marked.clear()
                for j, r_ in enumerate(self.rows):
                    if r_[0] == "item" and r_[1] in self.deps_missing_list:
                        self.marked.add(j)
            elif btn == "B":
                self.pop_state()
        elif top == "clocksettings":
            v = self.clock_v
            lim = [(2024, 2099), (1, 12), (1, 31), (0, 23), (0, 59),
                   (0, len(TZS) - 1)]
            if btn == "UP":
                self.clock_f = (self.clock_f - 1) % 6
            elif btn == "DOWN":
                self.clock_f = (self.clock_f + 1) % 6
            elif btn in ("LEFT", "RIGHT"):
                d = 1 if btn == "RIGHT" else -1
                lo, hi = lim[self.clock_f]
                v[self.clock_f] = lo + (v[self.clock_f] - lo + d) % \
                    (hi - lo + 1)
            elif btn == "A":
                self.cfg["tz"] = TZS[v[5]]
                save_cfg(self.cfg)
                stamp = "%04d-%02d-%02d %02d:%02d:00" % tuple(v[:5])
                if not os.environ.get("VD_NO_DATE"):
                    subprocess.call(["date", "-s", stamp],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                    subprocess.call(["hwclock", "-w"],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                self.info_lines = self.stub_lines(
                    "CLOCK", ["%s  ·  %s  ·  %s" %
                             (stamp, TZS[v[5]], self.t("applied"))])
                self.scroll = 0
                self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top == "calc":
            R, C = len(CALC_KEYS), len(CALC_KEYS[0])
            r, c = divmod(self.calc_sel, C)
            if btn == "UP":
                r = (r - 1) % R
            elif btn == "DOWN":
                r = (r + 1) % R
            elif btn == "LEFT":
                c = (c - 1) % C
            elif btn == "RIGHT":
                c = (c + 1) % C
            elif btn == "A":
                self.calc_press(CALC_KEYS[r][c])
            elif btn == "X":
                self.calc_press("<")
            elif btn == "Y":
                self.calc_press("=")
            elif btn == "B":
                self.pop_state()
            self.calc_sel = r * C + c
        elif top == "manual":
            if btn == "UP":
                self.man_sel = (self.man_sel - 1) % len(MANUAL)
            elif btn == "DOWN":
                self.man_sel = (self.man_sel + 1) % len(MANUAL)
            elif btn == "A":
                self.info_lines = self.manual_lines(self.man_sel)
                self.scroll = 0
                self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top == "mappdetail":
            acts = self.detail_actions()
            if btn == "UP":
                self.det_sel = (self.det_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.det_sel = (self.det_sel + 1) % len(acts)
            elif btn == "A":
                self.detail_do(acts[self.det_sel][0])
            elif btn == "B":
                self.pop_state()
        elif top == "cal":
            it = (self.lang == "it")
            v = self.cal_view
            if btn == "Y":
                self.cal_view = {"month": "week", "week": "day",
                                 "day": "month"}[v]
                self.ev_sel = 0
            elif btn == "L1":
                if v == "month":
                    self.cal_month_shift(-1)
                else:
                    self.cal_shift(-7 if v == "week" else -1)
            elif btn == "R1":
                if v == "month":
                    self.cal_month_shift(1)
                else:
                    self.cal_shift(7 if v == "week" else 1)
            elif v == "month":
                if btn == "LEFT":
                    self.cal_shift(-1)
                elif btn == "RIGHT":
                    self.cal_shift(1)
                elif btn == "UP":
                    self.cal_shift(-7)
                elif btn == "DOWN":
                    self.cal_shift(7)
                elif btn == "A":
                    self.cal_view = "day"
                    self.ev_sel = 0
                elif btn == "B":
                    self.pop_state()
            elif v == "week":
                if btn == "UP":
                    self.cal_shift(-1)
                elif btn == "DOWN":
                    self.cal_shift(1)
                elif btn == "LEFT":
                    self.cal_shift(-7)
                elif btn == "RIGHT":
                    self.cal_shift(7)
                elif btn == "A":
                    self.cal_view = "day"
                    self.ev_sel = 0
                elif btn == "B":
                    self.cal_view = "month"
            else:                              # day
                evd = self.ev_on(*self.cal_cur)
                n = len(evd) + 1
                if btn == "UP":
                    self.ev_sel = (self.ev_sel - 1) % n
                elif btn == "DOWN":
                    self.ev_sel = (self.ev_sel + 1) % n
                elif btn == "LEFT":
                    self.cal_shift(-1)
                    self.ev_sel = 0
                elif btn == "RIGHT":
                    self.cal_shift(1)
                    self.ev_sel = 0
                elif btn == "A":
                    if self.ev_sel == 0:
                        def done(t):
                            if not t.strip():
                                return
                            self.cw = list(self.cal_cur) + [12, 0, 0]
                            self.cw_title = t.strip()
                            self.cw_edit = None
                            self.cw_f = 3
                            self.push("calwhen")
                        self.osk_open("TITOLO EVENTO" if it
                                      else "EVENT TITLE", "", done)
                    else:
                        ev = evd[self.ev_sel - 1]

                        def done(t, ev=ev):
                            self.cw = [ev["y"], ev["mo"], ev["d"],
                                       ev["h"], ev["mi"], ev["imp"]]
                            self.cw_title = (t.strip() or ev["t"])
                            self.cw_edit = self.evs.index(ev)
                            self.cw_f = 0
                            self.push("calwhen")
                        self.osk_open("TITOLO EVENTO" if it
                                      else "EVENT TITLE", ev["t"],
                                      done)
                elif btn == "X" and self.ev_sel > 0:
                    ev = evd[self.ev_sel - 1]

                    def rm(ev=ev):
                        self.evs.remove(ev)
                        self.cal_save()
                        self.ev_sel = 0
                    self.confirm = (ev["t"][:28], rm)
                    self.push("confirm")
                elif btn == "B":
                    self.cal_view = "month"
        elif top == "calwhen":
            lim = [(2024, 2099), (1, 12), (1, 31), (0, 23), (0, 59),
                   (0, 2)]
            if btn == "UP":
                self.cw_f = (self.cw_f - 1) % 6
            elif btn == "DOWN":
                self.cw_f = (self.cw_f + 1) % 6
            elif btn in ("LEFT", "RIGHT"):
                d = 1 if btn == "RIGHT" else -1
                lo, hi = lim[self.cw_f]
                self.cw[self.cw_f] = lo + (self.cw[self.cw_f] - lo
                                           + d) % (hi - lo + 1)
            elif btn == "A":
                ev = {"t": self.cw_title, "y": self.cw[0],
                      "mo": self.cw[1], "d": self.cw[2],
                      "h": self.cw[3], "mi": self.cw[4],
                      "imp": self.cw[5]}
                if self.cw_edit is not None:
                    self.evs[self.cw_edit] = ev
                else:
                    self.evs.append(ev)
                self.evs.sort(key=lambda e: (e["y"], e["mo"], e["d"],
                                             e["h"], e["mi"]))
                self.cal_save()
                self.pop_state()
            elif btn == "B":
                self.pop_state()
        elif top == "notes":
            it = (self.lang == "it")
            n = len(self.notes) + 1
            if btn in ("UP", "LEFT"):
                self.note_sel = (self.note_sel - 1) % n
            elif btn in ("DOWN", "RIGHT"):
                self.note_sel = (self.note_sel + 1) % n
            elif btn == "A":
                if self.note_sel == 0:
                    def done(t):
                        if not t.strip():
                            return
                        p = os.path.join(self.notes_dir(),
                                         "note_%d.txt" %
                                         int(time.time()))
                        try:
                            open(p, "w").write(t.strip() + "\n")
                        except OSError:
                            return
                        self.notes = self.notes_refresh()
                    self.osk_open("NUOVA NOTA" if it else "NEW NOTE",
                                  "", done)
                else:
                    self.ed_load(self.notes[self.note_sel - 1]["p"])
            elif btn == "Y" and self.note_sel > 0:
                self.note_pin_toggle(
                    self.notes[self.note_sel - 1]["p"])
                self.note_sel = 0
            elif btn == "X" and self.note_sel > 0:
                nt = self.notes[self.note_sel - 1]

                def rm(p=nt["p"]):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                    pins = self.cfg.get("note_pins", [])
                    if os.path.basename(p) in pins:
                        pins.remove(os.path.basename(p))
                        save_cfg(self.cfg)
                    self.notes = self.notes_refresh()
                    self.note_sel = 0
                self.confirm = (nt["txt"].split("\n")[0][:28], rm)
                self.push("confirm")
            elif btn == "B":
                self.pop_state()
        elif top == "rss":
            n = len(self.rss_items)
            if btn == "UP" and n:
                self.rss_sel = (self.rss_sel - 1) % n
            elif btn == "DOWN" and n:
                self.rss_sel = (self.rss_sel + 1) % n
            elif btn == "A" and n:
                it_ = self.rss_items[self.rss_sel]
                L = [("sec", it_["icon"], it_["site"])]
                L.append(("kv", "", it_["title"], FG))
                if it_["link"]:
                    L.append(("kv", "link", it_["link"], DIM))
                ago = self.rss_ago(it_["ts"])
                if ago:
                    L.append(("kv", "", ago, FAINT))
                self.info_lines = L
                self.scroll = 0
                self.push("info")
            elif btn == "R1":
                self.run_busy(self.t("rss_upd"), self.rss_refresh)
                self.rss_sel = 0
            elif btn == "Y":
                self.rss_sel_sel = 0
                self.push("rsssel")
            elif btn == "B":
                self.pop_state()
        elif top == "rsssel":
            rows = self.rss_sel_rows()
            n = len(rows)
            if btn == "UP" and n:
                k = self.rss_sel_sel
                for _ in range(n):
                    k = (k - 1) % n
                    if rows[k][0] != "hdr":
                        break
                self.rss_sel_sel = k
            elif btn == "DOWN" and n:
                k = self.rss_sel_sel
                for _ in range(n):
                    k = (k + 1) % n
                    if rows[k][0] != "hdr":
                        break
                self.rss_sel_sel = k
            elif btn in ("A", "X") and n:
                r_ = rows[self.rss_sel_sel]
                if r_[0] == "feed":
                    self.rss_toggle(r_[1][0])
            elif btn == "Y" and n:
                r_ = rows[self.rss_sel_sel]
                if r_[0] == "feed":
                    name, _url, _lang, cat = r_[1]
                    it = (self.lang == "it")

                    def go(name=name, cat=cat):
                        if cat == "general":
                            self.rss_remove_custom(name)
                        else:
                            self.rss_disable(name)
                        self.rss_sel_sel = max(0, self.rss_sel_sel - 1)
                    self.confirm = (name, go)
                    self.push("confirm")
            elif btn == "B":
                self.pop_state()
        elif top == "glyphpick":
            n = len(self.gp_list)
            C = 8
            if btn == "LEFT" and n:
                self.gp_sel = (self.gp_sel - 1) % n
            elif btn == "RIGHT" and n:
                self.gp_sel = (self.gp_sel + 1) % n
            elif btn == "UP" and n:
                self.gp_sel = (self.gp_sel - C) % n
            elif btn == "DOWN" and n:
                self.gp_sel = (self.gp_sel + C) % n
            elif btn == "A" and n:
                src = self.gp_list[self.gp_sel]
                if self.glyph_is_ok(src):
                    self.gp_apply(src)
                else:
                    def go(src=src):
                        self.gp_apply(src)
                    self.confirm = (("converto in 22x22 bianco?"
                                     if self.lang == "it" else
                                     "convert to white 22x22?"), go)
                    self.push("confirm")
            elif btn == "X":
                self.gp_restore()
            elif btn == "B":
                self.pop_state()
        elif top == "confirm":
            if btn == "A" and self.confirm:
                cb = self.confirm[1]
                self.confirm = None
                self.pop_state()
                cb()
            elif btn == "B":
                self.confirm = None
                self.pop_state()
        elif top == "wifimgr":
            n = len(self.wm_nets)
            if btn == "UP" and n:
                self.wm_sel = (self.wm_sel - 1) % n
            elif btn == "DOWN" and n:
                self.wm_sel = (self.wm_sel + 1) % n
            elif btn == "R1":
                self.wm_nets = self.run_busy(self.t("wm_scan"),
                                             self.wm_scan) or []
                self.wm_sel = 0
            elif btn == "A" and n:
                net = self.wm_nets[self.wm_sel]
                if net["saved"] or not net["sec"]:
                    self.wm_connect(net)
                else:
                    def done(pw, net=net):
                        if pw:
                            self.wm_connect(net, pw)
                    self.osk_open(self.t("wm_pass"), "", done)
            elif btn == "X" and n:
                net = self.wm_nets[self.wm_sel]
                if net.get("id") is not None:
                    self.wm_cli("remove_network", net["id"])
                    self.wm_cli("save_config")
                    net["saved"] = False
                    net["id"] = None
            elif btn == "L1":
                self.info_lines = self.wm_info_lines()
                self.scroll = 0
                self.push("info")
            elif btn == "Y":
                self.run_busy("wifi...", self.wm_radio_toggle)
                self.wm_nets = self.run_busy(self.t("wm_scan"),
                                             self.wm_scan) or []
            elif btn == "B":
                self.pop_state()
        elif top == "btmgr":
            n = len(self.bt_devs)
            if btn == "UP" and n:
                self.bt_sel = (self.bt_sel - 1) % n
            elif btn == "DOWN" and n:
                self.bt_sel = (self.bt_sel + 1) % n
            elif btn == "R1":
                if self.bt_powered():
                    self.bt_devs = self.run_busy(self.t("bt_scan"),
                                                 lambda:
                                                 self.bt_list(True)
                                                 ) or []
                    self.bt_sel = 0
            elif btn == "A" and n:
                self.bt_pair(self.bt_devs[self.bt_sel])
                self.bt_devs = self.run_busy("...",
                                             lambda: self.bt_list(False))
            elif btn == "X" and n:
                dev = self.bt_devs[self.bt_sel]
                if dev["paired"]:
                    def rm(dev=dev):
                        self.bt_run("--", "remove", dev["mac"])
                        self.bt_devs = self.run_busy(
                            "...", lambda: self.bt_list(False))
                        self.bt_sel = 0
                    self.confirm = (dev["name"][:26], rm)
                    self.push("confirm")
            elif btn == "Y" and n:
                dev = self.bt_devs[self.bt_sel]
                self.run_busy("...", lambda: self.bt_run(
                    "--", "disconnect", dev["mac"]))
                self.bt_devs = self.run_busy("...",
                                             lambda: self.bt_list(False))
            elif btn == "SELECT":
                self.run_busy("bluetooth...", self.bt_power_toggle)
                self.bt_devs = self.run_busy("...",
                                             lambda: self.bt_list(False))
                self.bt_sel = 0
            elif btn == "L1":
                self.info_lines = self.bt_info_lines()
                self.scroll = 0
                self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top == "hotmgr":
            sc = getattr(self, "hot_scripts", None)
            if not isinstance(sc, dict):
                sc = self.hot_scripts = self.hot_find()
            acts = [k for k in ("start", "start5", "stop")
                    if sc.get(k)]
            if btn == "UP" and acts:
                self.hub_sel = (self.hub_sel - 1) % len(acts)
            elif btn == "DOWN" and acts:
                self.hub_sel = (self.hub_sel + 1) % len(acts)
            elif btn == "Y" and acts:
                if not self.hot_active():
                    if not self.deps_dialog_open(
                            "hotspot", "uplink", self.t("feat_hotspot")):
                        return
                out = self.run_busy("hotspot...", self.hot_toggle)
                self.info_lines = self.stub_lines(
                    "HOTSPOT", [(out or "eseguito").strip()[-96:]])
                self.scroll = 0
                self.push("info")
            elif btn == "A" and acts:
                key = acts[self.hub_sel % len(acts)]
                if key in ("start", "start5"):
                    if not self.deps_dialog_open(
                            "hotspot", "uplink", self.t("feat_hotspot")):
                        return
                p, arg = sc[key]
                out = self.run_busy("hotspot...",
                                    lambda: subprocess.run(
                                        ["sh", p] + arg,
                                        capture_output=True, text=True,
                                        timeout=40).stdout)
                self.info_lines = self.stub_lines(
                    "HOTSPOT", [(out or "eseguito").strip()[-96:], p])
                self.scroll = 0
                self.push("info")
            elif btn == "L1":
                self.info_lines = self.hot_info_lines()
                self.scroll = 0
                self.push("info")
            elif btn == "X":
                self.hotcfg_ssid, self.hotcfg_pass = self.hotcfg_load()
                self.hotcfg_sel = 0
                self.push("hotcfg")
            elif btn == "B":
                self.pop_state()
        elif top == "vdupdate":
            r = self.vdupd_result or {}
            if btn == "A" and r.get("has_update") and r.get("url"):
                def do_dl():
                    def cb(pct):
                        self.vdupd_progress = pct
                        self.busy_label = "%s %d%%" % (
                            "aggiorno" if self.lang == "it" else
                            "updating", pct)
                    return self.update_download_install(r["url"], cb)
                ok, msg = self.run_busy(
                    "aggiorno 0%" if self.lang == "it" else
                    "updating 0%",
                    do_dl)
                self.info_lines = self.stub_lines(
                    "VOID-DESK UPDATE", [msg])
                self.scroll = 0
                self.push("info")
            elif btn == "Y":
                self.vdupd_result = self.run_busy(
                    self.t("checking"), self.update_check)
            elif btn == "B":
                self.pop_state()
        elif top == "clihub":
            if btn == "UP":
                self.clihub_sel = (self.clihub_sel - 1) % 4
            elif btn == "DOWN":
                self.clihub_sel = (self.clihub_sel + 1) % 4
            elif btn == "A":
                if self.clihub_sel == 0:
                    self.clitools_sel = 0
                    self.push("clitools")
                elif self.clihub_sel == 1:
                    self.cliinst_sel = 0
                    self.cliinst_marked = set()
                    self.push("cliinstall")
                elif self.clihub_sel == 2:
                    self.clisettings_sel = 0
                    self.push("clisettings")
                else:
                    self.info_lines = self.clihelp_lines()
                    self.scroll = 0
                    self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top == "clisettings":
            n = 2
            if btn == "UP":
                self.clisettings_sel = (self.clisettings_sel - 1) % n
            elif btn == "DOWN":
                self.clisettings_sel = (self.clisettings_sel + 1) % n
            elif btn == "A" and self.clisettings_sel == 0:
                names = list(CLI_ACCENTS.keys())
                cur = self.cfg.get("cli_accent", "verde")
                nxt = names[(names.index(cur) + 1) % len(names)
                           if cur in names else 0]
                self.cfg["cli_accent"] = nxt
                self.cli_accent, self.cli_accent_dim = CLI_ACCENTS[nxt]
                save_cfg(self.cfg)
            elif btn == "B":
                self.pop_state()
        elif top == "clitools":
            n = len(CLI_TOOLS)
            if btn == "UP":
                self.clitools_sel = (self.clitools_sel - 1) % n
            elif btn == "DOWN":
                self.clitools_sel = (self.clitools_sel + 1) % n
            elif btn == "A":
                name, cat_name, cmd, _di, _de, _ic, _dp = \
                    CLI_TOOLS[self.clitools_sel]
                if cat_name is None:
                    if not self.ani_cli_installed():
                        ok, msg = self.run_busy(
                            self.t("checking"), self.ani_cli_download)
                        if not ok:
                            self.info_lines = self.stub_lines(
                                "CLI TOOLS", [msg])
                            self.scroll = 0
                            self.push("info")
                            return
                    self.open_real_terminal(cmd)
                else:
                    if self.deps_dialog_open("clitool_" + name,
                                             "terminal", name):
                        self.open_real_terminal(cmd)
            elif btn == "B":
                self.pop_state()
        elif top == "cliinstall":
            n = len(CLI_TOOLS)
            if btn == "UP":
                self.cliinst_sel = (self.cliinst_sel - 1) % n
            elif btn == "DOWN":
                self.cliinst_sel = (self.cliinst_sel + 1) % n
            elif btn == "X":
                if self.cliinst_sel in self.cliinst_marked:
                    self.cliinst_marked.discard(self.cliinst_sel)
                else:
                    self.cliinst_marked.add(self.cliinst_sel)
            elif btn == "Y":
                allidx = set(range(n))
                self.cliinst_marked = set() if self.cliinst_marked \
                    else allidx
            elif btn == "L1":
                if self.cliinst_mode != "install":
                    self.cliinst_mode = "install"
                    self.cliinst_marked = set()
                    self.play("open")
            elif btn == "R1":
                if self.cliinst_mode != "remove":
                    self.cliinst_mode = "remove"
                    self.cliinst_marked = set()
                    self.play("open")
            elif btn == "A":
                self.clidetail_idx = self.cliinst_sel
                self.clidetail_sel = 0
                self.scroll = 0
                self.push("clidetail")
            elif btn == "START":
                self.cliinst_execute()
            elif btn == "B":
                self.cliinst_marked = set()
                self.pop_state()
        elif top == "clidetail":
            name, cat_name, cmd, di, de, ic, dp = \
                CLI_TOOLS[self.clidetail_idx]
            installed = (self.ani_cli_installed() if cat_name is None
                        else bool(self.status.get(cat_name)))
            actions = (["reinstall", "uninstall", "back"] if installed
                      else ["install", "back"])
            if btn == "LEFT":
                self.clidetail_sel = (self.clidetail_sel - 1) % \
                    len(actions)
            elif btn == "RIGHT":
                self.clidetail_sel = (self.clidetail_sel + 1) % \
                    len(actions)
            elif btn in ("UP", "DOWN"):
                d = -1 if btn == "UP" else 1
                self.scroll = max(0, self.scroll + d)
            elif btn == "A":
                act = actions[self.clidetail_sel]
                if act == "back":
                    self.pop_state()
                elif act == "install":
                    self.cliinst_marked = {self.clidetail_idx}
                    self.cliinst_mode = "install"
                    self.cliinst_execute()
                    self.pop_state()
                elif act == "reinstall":
                    if cat_name is None:
                        try:
                            os.remove(self.ani_cli_path())
                        except OSError:
                            pass
                        self.run_busy(self.t("checking"),
                                     self.ani_cli_download)
                        self.pop_state()
                    else:
                        self.cliinst_marked = {self.clidetail_idx}
                        self.cliinst_mode = "install"
                        self.cliinst_execute(force=True)
                        self.pop_state()
                elif act == "uninstall":
                    self.cliinst_marked = {self.clidetail_idx}
                    self.cliinst_mode = "remove"
                    self.cliinst_execute()
                    self.pop_state()
            elif btn == "B":
                self.pop_state()
        elif top == "hotcfg":
            if btn == "UP":
                self.hotcfg_sel = (self.hotcfg_sel - 1) % 2
            elif btn == "DOWN":
                self.hotcfg_sel = (self.hotcfg_sel + 1) % 2
            elif btn == "A":
                it = (self.lang == "it")
                if self.hotcfg_sel == 0:
                    def done_s(t):
                        self.hotcfg_ssid = t.strip()[:32]
                    self.osk_open("SSID", self.hotcfg_ssid, done_s)
                else:
                    def done_p(t):
                        self.hotcfg_pass = t.strip()[:63]
                    self.osk_open("PASSWORD", self.hotcfg_pass, done_p)
            elif btn == "Y":
                self.hotcfg_save(self.hotcfg_ssid, self.hotcfg_pass)
                self.info_lines = self.stub_lines(
                    "HOTSPOT", [("salvato: %s" % self.hotcfg_ssid)
                               if self.lang == "it" else
                               ("saved: %s" % self.hotcfg_ssid)])
                self.scroll = 0
                self.push("info")
            elif btn == "B":
                self.pop_state()
        elif top == "monitor":
            if btn == "L1":
                self.mon_tab = (self.mon_tab - 1) % 5
            elif btn == "R1":
                self.mon_tab = (self.mon_tab + 1) % 5
            elif btn == "B":
                self.pop_state()
        elif top == "pyrepl":
            if btn == "Y":
                def cb(p):
                    if p.lower().endswith(".py"):
                        self.py_runfile(p)
                self.fm_open(pick=cb)
            elif btn == "A":
                def done(line):
                    if line.strip():
                        self.py_exec(line.strip())
                self.osk_open("PYTHON >>>", "", done)
            elif btn == "X":
                self.py_out = [self.py_out[0], ">>> "]
            elif btn == "B":
                self.pop_state()
        elif top == "backup":
            baks = self.bak_list()
            n = len(baks) + 1
            if btn == "UP":
                self.bak_sel = (self.bak_sel - 1) % n
            elif btn == "DOWN":
                self.bak_sel = (self.bak_sel + 1) % n
            elif btn == "A":
                it = (self.lang == "it")
                if self.bak_sel == 0:
                    r = self.run_busy("...", self.bak_create)
                    msg = {"no-img": "immagine assente" if it
                           else "no image",
                           "mounted": "smonta prima l'immagine (chiudi "
                           "il desktop)" if it else
                           "unmount the image first",
                           "err": "backup fallito: spazio?" if it
                           else "backup failed: space?"}.get(
                               r, (r or ""))
                    self.info_lines = self.stub_lines(
                        "BACKUP", [msg[:96]])
                    self.scroll = 0
                    self.push("info")
                else:
                    nm, p, _sz = baks[self.bak_sel - 1]

                    def go(p=p):
                        r = self.run_busy("...",
                                          lambda: self.bak_restore(p))
                        self.info_lines = self.stub_lines(
                            "RESTORE",
                            ["ok: immagine ripristinata" if r == "ok"
                             and it else r])
                        self.scroll = 0
                        self.push("info")
                    self.confirm = (nm[:30], go)
                    self.push("confirm")
            elif btn == "X" and self.bak_sel > 0:
                nm, p, _sz = baks[self.bak_sel - 1]

                def rm(p=p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                    self.bak_sel = 0
                self.confirm = (nm[:30], rm)
                self.push("confirm")
            elif btn == "B":
                self.pop_state()
        elif top == "tspanel":
            peers = (self.ts or {}).get("peers", [])
            if btn == "UP" and peers:
                self.ts_sel = (self.ts_sel - 1) % len(peers)
            elif btn == "DOWN" and peers:
                self.ts_sel = (self.ts_sel + 1) % len(peers)
            elif btn == "A" and peers:
                self.hub_sel = 0
                self.push("tsact")
            elif btn == "Y":
                self.hub_sel = 0
                self.push("tsmenu")
            elif btn == "R1":
                self.ts_refresh()
            elif btn == "B":
                self.pop_state()
        elif top == "tsmenu":
            acts = self.ts_menu_items()
            if btn == "UP":
                self.hub_sel = (self.hub_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.hub_sel = (self.hub_sel + 1) % len(acts)
            elif btn == "A":
                key = acts[self.hub_sel][0]
                self.pop_state()
                self.ts_menu_do(key)
            elif btn == "B":
                self.pop_state()
        elif top == "tsact":
            peer = (self.ts or {}).get("peers", [])[self.ts_sel]
            acts = [("ping", "Ping")]
            if peer.get("exit"):
                acts.append(("exit", "Usa come exit node"
                             if self.lang == "it" else
                             "Use as exit node"))
            acts += [("send", "Invia file (Taildrop)"
                      if self.lang == "it" else "Send file (Taildrop)"),
                     ("pinfo", "Info")]
            if btn == "UP":
                self.hub_sel = (self.hub_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.hub_sel = (self.hub_sel + 1) % len(acts)
            elif btn == "A":
                key = acts[self.hub_sel][0]
                self.pop_state()
                self.ts_peer_do(key, peer)
            elif btn == "B":
                self.pop_state()
        elif top == "ftpprof":
            profs = self.cfg.get("ftp_profiles", [])
            n = len(profs) + 1
            if btn == "UP":
                self.ftp_prof_sel = (self.ftp_prof_sel - 1) % n
            elif btn == "DOWN":
                self.ftp_prof_sel = (self.ftp_prof_sel + 1) % n
            elif btn == "A":
                if self.ftp_prof_sel < len(profs):
                    self.ftp_connect(profs[self.ftp_prof_sel])
                else:
                    self.ftp_new_profile()
            elif btn == "X" and self.ftp_prof_sel < len(profs):
                p = profs[self.ftp_prof_sel]

                def go():
                    profs.remove(p)
                    save_cfg(self.cfg)
                    self.ftp_prof_sel = 0
                self.confirm = (p.get("name", "?"), go)
                self.push("confirm")
            elif btn == "B":
                self.pop_state()
        elif top == "ftpls":
            n = len(self.ftp_items)
            if btn == "UP" and n:
                self.ftp_sel = (self.ftp_sel - 1) % n
            elif btn == "DOWN" and n:
                self.ftp_sel = (self.ftp_sel + 1) % n
            elif btn == "A" and n:
                nm, isd, _sz = self.ftp_items[self.ftp_sel]
                if nm == "..":
                    if self.ftp_cwd in ("/", ""):
                        self.ftp_close()
                        self.pop_state()
                    else:
                        self.ftp_cwd = os.path.dirname(
                            self.ftp_cwd.rstrip("/")) or "/"
                        self.ftp_sel = 0
                        self.run_busy("...", self.ftp_refresh)
                elif isd:
                    self.ftp_cwd = self.ftp_join(nm)
                    self.ftp_sel = 0
                    self.run_busy("...", self.ftp_refresh)
                else:
                    self.ftp_download([nm])
            elif btn == "X" and n:
                nm, isd, _sz = self.ftp_items[self.ftp_sel]
                if not isd:
                    if nm in self.ftp_marked:
                        self.ftp_marked.discard(nm)
                    else:
                        self.ftp_marked.add(nm)
            elif btn == "Y":
                self.hub_sel = 0
                self.push("ftpmenu")
            elif btn == "B":
                if self.ftp_cwd in ("/", ""):
                    self.ftp_close()
                    self.pop_state()
                else:
                    self.ftp_cwd = os.path.dirname(
                        self.ftp_cwd.rstrip("/")) or "/"
                    self.ftp_sel = 0
                    self.run_busy("...", self.ftp_refresh)
        elif top == "ftpmenu":
            acts = self.ftp_menu_items()
            if btn == "UP":
                self.hub_sel = (self.hub_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.hub_sel = (self.hub_sel + 1) % len(acts)
            elif btn == "A":
                key = acts[self.hub_sel][0]
                self.pop_state()
                if key == "dl":
                    sel = sorted(self.ftp_marked) or \
                        ([self.ftp_items[self.ftp_sel][0]]
                         if self.ftp_items and
                         not self.ftp_items[self.ftp_sel][1] else [])
                    self.ftp_marked.clear()
                    if sel:
                        self.ftp_download(sel)
                elif key == "ul":
                    self.fm_open(pick=self.ftp_upload)
                elif key == "refresh":
                    self.run_busy("...", self.ftp_refresh)
                elif key == "close":
                    self.ftp_close()
                    self.pop_state()
            elif btn == "B":
                self.pop_state()
        elif top == "syncpanel":
            if btn == "A":
                self.sync_open_refresh()
            elif btn == "B":
                self.pop_state()
        elif top == "osk":
            if btn == "UP":
                self.osk_sel = (self.osk_sel - 10) % 40
            elif btn == "DOWN":
                self.osk_sel = (self.osk_sel + 10) % 40
            elif btn == "LEFT":
                self.osk_sel = (self.osk_sel // 10) * 10 + \
                    (self.osk_sel % 10 - 1) % 10
            elif btn == "RIGHT":
                self.osk_sel = (self.osk_sel // 10) * 10 + \
                    (self.osk_sel % 10 + 1) % 10
            elif btn == "A":
                if len(self.osk_buf) < 96:
                    c = self.osk_cursor
                    self.osk_buf = self.osk_buf[:c] + self.osk_key() + \
                        self.osk_buf[c:]
                    self.osk_cursor += 1
            elif btn == "X":
                c = self.osk_cursor
                if c > 0:
                    self.osk_buf = self.osk_buf[:c - 1] + \
                        self.osk_buf[c:]
                    self.osk_cursor -= 1
            elif btn == "Y":
                c = self.osk_cursor
                self.osk_buf = self.osk_buf[:c] + " " + self.osk_buf[c:]
                self.osk_cursor += 1
            elif btn == "L1":
                self.osk_cursor = max(0, self.osk_cursor - 1)
            elif btn == "R1":
                self.osk_cursor = min(len(self.osk_buf),
                                      self.osk_cursor + 1)
            elif btn == "SELECT":
                self.osk_page = (self.osk_page + 1) % len(OSK_PAGES)
            elif btn == "START":
                cb = self.osk_cb
                self.osk_cb = None
                self.pop_state()
                if cb:
                    cb(self.osk_buf)
            elif btn == "B":
                self.osk_cb = None
                self.pop_state()
        elif top == "files":
            n = len(self.fm_items)
            if btn == "UP" and n:
                self.fm_sel = (self.fm_sel - 1) % n
            elif btn == "DOWN" and n:
                self.fm_sel = (self.fm_sel + 1) % n
            elif btn == "A" and n:
                self.fm_enter()
            elif btn == "X" and n and self.fm_path:
                nm = self.fm_items[self.fm_sel][0]
                if nm != "..":
                    p = os.path.join(self.fm_path, nm)
                    if p in self.fm_marked:
                        self.fm_marked.discard(p)
                    else:
                        self.fm_marked.add(p)
            elif btn == "Y" and self.fm_path and not self.fm_pick:
                self.hub_sel = 0
                self.push("fmenu")
            elif btn == "B":
                if self.fm_path is None:
                    self.fm_pick = None
                    self.pop_state()
                else:
                    self.fm_up()
        elif top == "fmenu":
            acts = self.fm_menu_items()
            if btn == "UP":
                self.hub_sel = (self.hub_sel - 1) % len(acts)
            elif btn == "DOWN":
                self.hub_sel = (self.hub_sel + 1) % len(acts)
            elif btn == "A":
                key = acts[self.hub_sel][0]
                self.pop_state()
                self.fm_menu_do(key)
            elif btn == "B":
                self.pop_state()
        elif top == "imgview":
            if btn in ("B", "A"):
                self.pop_state()
        elif top == "edit":
            if btn == "UP":
                self.ed_cur = max(0, self.ed_cur - 1)
            elif btn == "DOWN":
                self.ed_cur = min(len(self.ed_lines) - 1, self.ed_cur + 1)
            elif btn == "LEFT":
                self.ed_cur = max(0, self.ed_cur - 10)
            elif btn == "RIGHT":
                self.ed_cur = min(len(self.ed_lines) - 1,
                                  self.ed_cur + 10)
            elif btn == "A":
                def done(txt, i=self.ed_cur):
                    self.ed_lines[i] = txt
                    self.ed_dirty = True
                self.osk_open("RIGA %d" % (self.ed_cur + 1)
                              if self.lang == "it"
                              else "LINE %d" % (self.ed_cur + 1),
                              self.ed_lines[self.ed_cur], done)
            elif btn == "Y":
                self.ed_lines.insert(self.ed_cur + 1, "")
                self.ed_cur += 1
                self.ed_dirty = True
            elif btn == "X":
                if len(self.ed_lines) > 1:
                    self.ed_lines.pop(self.ed_cur)
                    self.ed_cur = min(self.ed_cur,
                                      len(self.ed_lines) - 1)
                else:
                    self.ed_lines[0] = ""
                self.ed_dirty = True
            elif btn == "START":
                self.ed_save()
            elif btn == "SELECT":
                d = os.path.dirname(self.ed_path) or "."

                def sa(nm):
                    if nm:
                        self.ed_save(os.path.join(d, nm))
                self.osk_open("SALVA COME" if self.lang == "it"
                              else "SAVE AS",
                              os.path.basename(self.ed_path), sa)
            elif btn == "B":
                if self.ed_dirty:
                    self.confirm = (("uscire senza salvare?"
                                     if self.lang == "it"
                                     else "leave without saving?"),
                                    self.pop_state)
                    self.push("confirm")
                else:
                    self.pop_state()
        elif top == "info":
            n = len(self.info_lines or [])
            if btn == "UP":
                self.scroll = max(0, self.scroll - 1)
            elif btn == "DOWN":
                self.scroll = min(max(0, n - 1), self.scroll + 1)
            elif btn == "B":
                self.pop_state()
        elif top == "manifesto":
            if btn == "UP":
                self.scroll = max(0, self.scroll - 1)
            elif btn == "DOWN":
                self.scroll += 1
            elif btn == "B":
                self.pop_state()
        elif top == "viewer":
            if btn == "R1":
                self.viewer_live = not self.viewer_live
            elif btn == "UP":
                self.viewer_live = False
                self.scroll = max(0, self.scroll - 3)
            elif btn == "DOWN":
                self.scroll += 3
            elif btn == "B":
                self.viewer_live = False
                self.pop_state()
        else:
            # rete di sicurezza: uno stato senza gestore non deve MAI piu'
            # murare la console. B torna sempre indietro.
            if btn == "B" and len(self.stack) > 1:
                self.pop_state()

    def comp_action(self, key):
        if key in ("install", "remove", "autostart"):
            if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
                self.info_lines = [("sec", "info", self.t("need_xfce"))]
                self.push("info")
                return
            self.run_busy(self.t("mounting"), self.scan_status)
            self.build_rows()
            self.marked.clear()
            self.mode = key
            self.push("comp" if key != "autostart" else "autostart")
            if key == "autostart":
                self.auto_rows()
        elif key == "update":
            os.makedirs(DATA, exist_ok=True)
            with open(os.path.join(DATA, ".install_pkg"), "w") as f:
                f.write("update\n-\n")
            self.handoff(self.t("ho_update"))
            self.exit_code = EXIT_APT_UPDATE
            self.running = False
        elif key == "clean":
            self.info_lines = self.run_busy(self.t("cleaning"),
                                            self.apt_clean) or []
            self.scroll = 0
            self.push("info")
        elif key == "shell":
            self.open_real_terminal()

    # ================== VOID-DESK UPDATE ==================
    def update_check(self):
        """Interroga l'ultima release GitHub e confronta la versione.
        Non tocca nulla: solo lettura."""
        import urllib.request
        import json as _j
        api = os.environ.get(
            "VD_UPDATE_API",
            "https://api.github.com/repos/%s/releases/latest" %
            GITHUB_REPO)
        try:
            req = urllib.request.Request(
                api, headers={"User-Agent": "VoidDesk-Updater",
                              "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = _j.loads(r.read().decode())
        except Exception as e:
            return {"error": str(e)[:120]}
        tag = (data.get("tag_name") or "").strip().lstrip("vV")
        url = None
        for a in (data.get("assets") or []):
            name = (a.get("name") or "").lower()
            if name.endswith(".muxapp") or name.endswith(".zip"):
                url = a.get("browser_download_url")
                break
        if not url:
            url = data.get("zipball_url")

        def ver_tuple(s):
            out = []
            for part in s.split("."):
                digits = "".join(c for c in part if c.isdigit())
                out.append(int(digits) if digits else 0)
            return tuple(out)
        cur, new = ver_tuple(VERSION), ver_tuple(tag or "0")
        return {"tag": tag or "?", "url": url, "has_update": new > cur,
                "notes": (data.get("body") or "").strip()[:280],
                "current": VERSION}

    def update_download_install(self, url, progress_cb=None):
        """Scarica, verifica, estrae in una cartella temporanea e SOLO
        se tutto e' andato bene sovrascrive l'app dal vivo -- data/
        non viene mai toccata. Ritorna (ok, messaggio)."""
        import urllib.request
        import zipfile
        import shutil
        import tempfile
        try:
            tmp_zip = os.path.join(tempfile.gettempdir(),
                                   "voiddesk_update.zip")
            req = urllib.request.Request(
                url, headers={"User-Agent": "VoidDesk-Updater"})
            with urllib.request.urlopen(req, timeout=20) as r:
                total = int(r.headers.get("Content-Length", 0) or 0)
                done = 0
                with open(tmp_zip, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb and total:
                            progress_cb(min(99, done * 100 // total))
        except Exception as e:
            return False, "download fallito: %s" % str(e)[:100]

        stage = os.path.join(tempfile.gettempdir(), "voiddesk_stage")
        shutil.rmtree(stage, ignore_errors=True)
        try:
            with zipfile.ZipFile(tmp_zip) as z:
                z.extractall(stage)
        except Exception as e:
            return False, "archivio non valido: %s" % str(e)[:100]
        finally:
            try:
                os.remove(tmp_zip)
            except OSError:
                pass

        # trovo la vera radice: puo' essere stage/VoidDesk/ oppure un
        # unico sottodirectory generato da GitHub (nomeutente-repo-hash)
        root = None
        for cand in [stage] + [os.path.join(stage, d)
                               for d in os.listdir(stage)
                               if os.path.isdir(os.path.join(stage, d))]:
            if os.path.exists(os.path.join(cand, "desk", "main.py")):
                root = cand
                break
        if not root:
            shutil.rmtree(stage, ignore_errors=True)
            return False, ("pacchetto scaricato ma senza desk/main.py: "
                          "aggiornamento annullato per sicurezza")

        try:
            for entry in os.listdir(root):
                if entry == "data":
                    continue
                src = os.path.join(root, entry)
                dst = os.path.join(APP_DIR, entry)
                if os.path.isdir(src):
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        except Exception as e:
            shutil.rmtree(stage, ignore_errors=True)
            return False, "copia fallita: %s" % str(e)[:100]
        shutil.rmtree(stage, ignore_errors=True)
        return True, "aggiornato: riavvia VoidDesk per applicarlo"

    def apt_clean(self):
        img = os.path.join(DATA, "xfce.img")
        mnt = os.path.join(DATA, "xfce_mnt")
        out = []
        ok, err = imgmount.mount_img(img, mnt)
        if not ok:
            return [("sec", "info", "ERRORE"), ("kv", "mount", err, NO_R)]
        try:
            before = os.statvfs(mnt)
            subprocess.call(["chroot", mnt, "/bin/sh", "-c",
                             "apt-get clean; rm -rf /var/lib/apt/lists/*; "
                             "rm -rf /tmp/* /var/tmp/*"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            after = os.statvfs(mnt)
            self.img_free = after.f_bavail * after.f_frsize
            freed = (after.f_bavail - before.f_bavail) * after.f_frsize
            out = [("sec", "task", "PULIZIA" if self.lang == "it"
                    else "CLEANUP"),
                   ("kv", "SPAZIO LIBERATO" if self.lang == "it"
                    else "SPACE FREED", human(max(0, freed)), OK_G),
                   ("kv", "LIBERI ORA" if self.lang == "it" else "FREE NOW",
                    human(after.f_bavail * after.f_frsize), FG)]
        finally:
            imgmount.umount_tree(mnt, img)
        return out

    def clihelp_lines(self):
        it = (self.lang == "it")
        L = [("sec", "info", "CLI TOOLS -- HELP & ABOUT")]
        L.append(("kv", "", "Un angolo di terminale retro dentro "
                  "VoidDesk: tool CLI simpatici e utili, lanciati in "
                  "un terminale VERO (xterm su X, non la shell finta "
                  "in pygame)." if it else
                  "A retro terminal corner inside VoidDesk: fun and "
                  "useful CLI tools, launched in a REAL terminal "
                  "(xterm on X, not the fake pygame shell).", FG))
        L.append(("sec", "terminal", "CLI ARSENAL"))
        L.append(("kv", "", "L'elenco dei tool pronti da lanciare "
                  "subito. Seleziona, premi A." if it else
                  "The list of tools ready to launch right away. "
                  "Select, press A.", DIM))
        L.append(("sec", "pkg", "CLI INSTALLER"))
        L.append(("kv", "", "Installa e rimuove i CLI tool. X segna "
                  "una voce, Y segna/toglie tutte, L1/R1 passano tra "
                  "Installer e Uninstaller, START esegue quanto "
                  "selezionato. A apre la scheda dettaglio di un "
                  "singolo tool." if it else
                  "Installs and removes CLI tools. X marks an entry, "
                  "Y marks/unmarks all, L1/R1 switch between Installer "
                  "and Uninstaller, START runs what's selected. A "
                  "opens a single tool's detail card.", DIM))
        L.append(("sec", "info", "ANI-CLI"))
        L.append(("kv", "", "Non e' un pacchetto apt: e' uno script "
                  "scaricato dal repository ufficiale su GitHub. "
                  "Dipende da mpv, curl e fzf." if it else
                  "Not an apt package: it's a script downloaded from "
                  "the official GitHub repository. Depends on mpv, "
                  "curl and fzf.", DIM))
        L.append(("sec", "keyboard", "TASTIERA NEL TERMINALE" if it
                  else "KEYBOARD IN THE TERMINAL"))
        L.append(("kv", "", "Nessuna tastiera fisica? Il tasto "
                  "dedicato (MENU) apre/chiude la tastiera a schermo, "
                  "esattamente come nei desktop XFCE/IceWM/LXDE. "
                  "START+SELECT apre il pannello LIVE." if it else
                  "No physical keyboard? The dedicated key (MENU) "
                  "opens/closes the on-screen keyboard, exactly like "
                  "in the XFCE/IceWM/LXDE desktops. START+SELECT opens "
                  "the LIVE panel.", DIM))
        return L

    def cliinst_execute(self, force=False):
        """Installa o rimuove i CLI tool selezionati. ani-cli (script
        GitHub, non apt) viene gestito subito e a parte; i pacchetti
        apt veri passano per il meccanismo standard di FORGE (stesso
        percorso collaudato del Void Installer). force=True salta il
        filtro "gia' installato": serve per Reinstall, dove il tool
        e' li' apposta."""
        idxs = sorted(self.cliinst_marked) or [self.cliinst_sel]
        apt_names, apt_pkgs = [], []
        do_ani = False
        for i in idxs:
            if i >= len(CLI_TOOLS):
                continue
            name, cat_name, _cmd, _di, _de, _ic, _dp = CLI_TOOLS[i]
            if cat_name is None:
                if self.cliinst_mode == "install":
                    do_ani = True
                else:
                    try:
                        os.remove(self.ani_cli_path())
                    except OSError:
                        pass
                continue
            if not force and self.cliinst_mode == "remove" and \
                    not self.status.get(cat_name):
                continue
            if not force and self.cliinst_mode == "install" and \
                    self.status.get(cat_name):
                continue
            for _cat, items in CATEGORIES:
                for nm, pkgs, _d, _p, _i in items:
                    if nm == cat_name:
                        apt_names.append(nm)
                        apt_pkgs.append(pkgs)
        ani_msg = None
        if do_ani:
            ok, ani_msg = self.run_busy(self.t("checking"),
                                        self.ani_cli_download)
        if apt_names:
            if self.cliinst_mode != "remove" and self.img_free is not \
                    None and self.img_free < 250 * 1024 * 1024:
                self.info_lines = [
                    ("sec", "disk", "SPAZIO INSUFFICIENTE"
                     if self.lang == "it" else "NOT ENOUGH SPACE"),
                    ("kv", "", self.t("no_space") % human(self.img_free),
                     NO_R),
                    ("kv", "", self.t("no_space_s"), DIM)]
                self.scroll = 0
                self.push("info")
                return
            label = (apt_names[0] if len(apt_names) == 1 else
                     ("%d componenti" if self.lang == "it" else
                      "%d components") % len(apt_names))
            with open(os.path.join(DATA, ".install_pkg"), "w") as f:
                f.write(label + "\n")
                f.write(" ".join(apt_pkgs) + "\n")
            self.exit_code = (EXIT_PKG_REMOVE if self.cliinst_mode ==
                              "remove" else EXIT_PKG_INSTALL)
            self.running = False
        elif ani_msg is not None:
            self.info_lines = self.stub_lines("ANI-CLI", [ani_msg])
            self.scroll = 0
            self.push("info")
        self.cliinst_marked = set()

    def open_real_terminal(self, cmd=None):
        """Terminale VERO (xterm su X, niente window manager): per i
        CLI tools interattivi/continui, che nella shell finta in
        pygame andrebbero sempre in timeout o non disegnerebbero
        nulla. Esce da VoidDesk con EXIT_XTERM; mux_launch.sh lancia
        vd_xterm_launch.sh e ci rilancia al ritorno."""
        if not self.deps_dialog_open("real_terminal", "terminal",
                                     "xterm"):
            return
        try:
            with open(os.path.join(DATA, ".xterm_cmd"), "w") as f:
                f.write(cmd or "")
        except OSError:
            pass
        self.exit_code = EXIT_XTERM
        self.running = False

    def open_shell(self, auto_cmd=None):
        """Terminale con tastiera a schermo (dentro il chroot se montato).
        Se auto_cmd e' dato, lo esegue subito -- e' cosi' che i CLI
        tools si aprono direttamente nel loro programma."""
        img = os.path.join(DATA, "xfce.img")
        mnt = os.path.join(DATA, "xfce_mnt")
        state = {"temp": False}

        def prep():
            if os.path.exists(img) and not imgmount.is_mounted(mnt):
                ok, _e = imgmount.mount_img(img, mnt)
                state["temp"] = ok
                if not ok:
                    return
                for typ, src, dst in (("bind", "/dev", "/dev"),
                                      ("proc", "proc", "/proc"),
                                      ("sysfs", "sys", "/sys")):
                    d = os.path.join(mnt, dst.lstrip("/"))
                    if not imgmount.is_mounted(d):
                        os.makedirs(d, exist_ok=True)
                        if typ == "bind":
                            subprocess.call(["mount", "-o", "bind", src, d],
                                            stderr=subprocess.DEVNULL)
                        else:
                            subprocess.call(["mount", "-t", typ, src, d],
                                            stderr=subprocess.DEVNULL)
                try:
                    import shutil
                    shutil.copy("/etc/resolv.conf",
                                os.path.join(mnt, "etc/resolv.conf"))
                except OSError:
                    pass

        self.run_busy(self.t("mounting"), prep)
        temp = state["temp"]
        sh = shell.Shell(self.surface, FONT_PATH, self.accent,
                         mnt if imgmount.is_mounted(mnt) else "",
                         self.lang, auto_cmd=auto_cmd)
        clock = pygame.time.Clock()
        dpad_t = 0.0
        while sh.running:
            for b in evinput.poll():
                if b != "MENU":
                    sh.on_button(b)
            hx, hy = evinput.hat()
            now = time.time()
            if (hx or hy) and now - dpad_t > 0.13:
                dpad_t = now
                if hy > 0:
                    sh.on_button("UP")
                elif hy < 0:
                    sh.on_button("DOWN")
                if hx < 0:
                    sh.on_button("LEFT")
                elif hx > 0:
                    sh.on_button("RIGHT")
            sh.draw()
            clock.tick(30)
        if temp:
            imgmount.umount_tree(mnt, img)

    def auto_rows(self):
        """Righe della schermata avvio al boot: solo programmi installati."""
        rows = []
        for cat, items in CATEGORIES:
            for name, pkgs, desc, paths, ic in items:
                if name not in AUTOSTART_OK:
                    continue
                if self.status.get(name) and not pkgs.startswith("!"):
                    exe = paths.split()[0].split("/")[-1]
                    rows.append(("item", name, exe, desc, ic))
        self.rows = rows or [("item", "-", "-", "-", "pkg")]
        self.row_sel = 0

    def activate(self, i):
        if i == 0:
            cur = self.cfg.get("desk_env", "xfce")
            self.env_sel = next((j for j, e in enumerate(ENVS)
                                 if e[0] == cur), 0)
            self.push("session")
        elif i == 1:
            self.mapp_sel = 0
            self.mapps = self.scan_muos()
            self.push("muosapps")
        elif i in (2, 3, 4, 5):
            hub = ("forge", "toolbox", "uplink", "workshop")[i - 2]
            self.hub_sel = 0
            self.push("hub:" + hub)
        elif i == 6:
            self.opt_sel = 0
            self.push("options")
        elif i == 7:
            self.hub_sel = 0
            self.push("hub:infohub")
        else:
            self.crt_off()

    # -------------------------------------------------------------- render
    def render_home_hud(self):
        """HUD futuristico: pannelli angolari con taglio doppio, bagliori,
        parentesi da mirino sulla voce attiva, scanline che scorre."""
        self.surface.fill(BG)
        pygame.draw.rect(self.surface, INK, (0, 0, W, 40))
        pygame.draw.line(self.surface, self.accent, (0, 40), (W, 40), 2)
        self.f_big.set_bold(True)
        tw_title = self.f_big.size("VOID // DESK")[0]
        self.text("VOID // DESK", (14, 6), self.f_big, self.accent)
        self.f_big.set_bold(False)
        rcx, rcy, rr = 14 + tw_title + 24, 20, 11
        pygame.draw.circle(self.surface, LINE, (rcx, rcy), rr, 1)
        rang = time.time() * 2.1
        for a_off in (0, math.pi):
            ex = rcx + int(rr * math.cos(rang + a_off))
            ey = rcy + int(rr * math.sin(rang + a_off))
            pygame.draw.line(self.surface, self.accent, (rcx, rcy),
                             (ex, ey), 1)
        clk = time.strftime("%H:%M:%S")
        cw2 = self.f_small.size(clk)[0]
        self.text(clk, (W - 16 - cw2, 12), self.f_small, DIM)
        sweep_y = 44 + int((time.time() * 70) % (H - 84))
        pygame.draw.line(self.surface, sel_tint(self.accent),
                         (0, sweep_y), (W, sweep_y), 1)
        y = 48
        rh = (H - 56 - 48) // len(self.menu)
        for i, (label, sub) in enumerate(self.menu):
            sel = (i == self.sel)
            cut = 16
            pts = [(10, y), (W - 10 - cut, y), (W - 10, y + cut),
                   (W - 10, y + rh - 6), (10 + cut, y + rh - 6),
                   (10, y + rh - 6 - cut)]
            pygame.draw.polygon(self.surface,
                                sel_tint(self.accent) if sel else INK, pts)
            pygame.draw.polygon(self.surface,
                                self.accent if sel else LINE, pts,
                                3 if sel else 1)
            if sel:
                self.last_sel_rect = (10, y, W - 20, rh - 6)
                for cx2, cy2, sx, sy in ((10, y, 1, 1), (W - 10, y, -1, 1),
                                         (10, y + rh - 6, 1, -1),
                                         (W - 10, y + rh - 6, -1, -1)):
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2 + 10 * sx, cy2), 2)
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2, cy2 + 10 * sy), 2)
            dsz = 30
            dcx, dcy = 32, y + (rh - 6) // 2
            pts2 = [(dcx, dcy - dsz // 2), (dcx + dsz // 2, dcy),
                    (dcx, dcy + dsz // 2), (dcx - dsz // 2, dcy)]
            pygame.draw.polygon(self.surface, INK, pts2)
            pygame.draw.polygon(self.surface,
                                self.accent if sel else FAINT, pts2, 2)
            icons.draw(self.surface, self.menu_icons[i], dcx - 10,
                       dcy - 10, 20, self.accent if sel else FAINT)
            self.f_med.set_bold(True)
            self.text(label, (58, y + 8), self.f_med,
                      FG if sel else DIM)
            self.f_med.set_bold(False)
            self.f_tiny.set_italic(True)
            self.text(sub, (58, y + 30), self.f_tiny, FAINT,
                      maxw=W - 200)
            self.f_tiny.set_italic(False)
            tag = "0x%02X" % (i * 17)
            tgw = self.f_tiny.size(tag)[0]
            self.text(tag, (W - 24 - tgw, y + (rh - 6) // 2 - 6),
                      self.f_tiny, self.accent if sel else FAINT)
            y += rh
        self.footer([("Y", self.t("view")), ("A", self.t("open")),
                     ("B", self.t("exit"))])

    def render_home_terminal(self):
        """Terminal retrocomputing: fosforo verde, elenco numerato,
        cursore che lampeggia, scanline sempre attive."""
        self.surface.fill((3, 8, 4))
        self.f_small.set_bold(True)
        self.text("VOID-DESK OS -- READY", (12, 8), self.f_small, GRN)
        self.f_small.set_bold(False)
        led_on = int(time.time() * 1.4) % 2 == 0
        pygame.draw.circle(self.surface, GRN if led_on else DGRN,
                           (W - 16, 14), 4)
        self.text("PWR", (W - 40, 8), self.f_tiny,
                  GRN if led_on else DGRN)
        pygame.draw.line(self.surface, DGRN, (0, 28), (W, 28), 1)
        y = 40
        for i, (label, sub) in enumerate(self.menu):
            sel = (i == self.sel)
            blink = int(time.time() * 2) % 2 == 0
            cursor = ">" if (sel and blink) else " "
            ln = "%s %d. %s" % (cursor, i + 1, label.upper())
            self.text(ln, (14, y), self.f_med, GRN if sel else DGRN)
            if sel:
                self.last_sel_rect = (10, y - 4, W - 20, 40)
                self.text("    " + sub, (14, y + 20), self.f_tiny, GRN)
            y += 40
        for sy in range(0, H, 3):
            pygame.draw.line(self.surface, (0, 0, 0, 40), (0, sy),
                             (W, sy))
        blink2 = int(time.time() * 2) % 2 == 0
        self.text("root@voiddesk:~$ " + ("_" if blink2 else ""),
                  (12, H - 44), self.f_small, GRN)
        self.footer([("Y", self.t("view")), ("A", self.t("open")),
                     ("B", self.t("exit"))])

    def render_home_orbit(self):
        """Menu radiale: gli hub orbitano attorno al marchio centrale,
        la voce attiva si illumina e mostra i dettagli in alto."""
        self.surface.fill(BG)
        cx, cy, r = W // 2, H // 2 + 6, 128
        for ring in (r, r - 30):
            pygame.draw.circle(self.surface, LINE, (cx, cy), ring, 1)
        t_now = time.time()
        for pi, (pr, speed, psize) in enumerate(
                ((r, 0.35, 2), (r - 30, -0.5, 2), (r - 30, 0.28, 1))):
            pang = t_now * speed + pi * 2.1
            px = cx + int(pr * math.cos(pang))
            py = cy + int(pr * math.sin(pang))
            pygame.draw.circle(self.surface, sel_tint(self.accent),
                               (px, py), psize)
        pygame.draw.circle(self.surface, sel_tint(self.accent),
                           (cx, cy), 34)
        pygame.draw.circle(self.surface, self.accent, (cx, cy), 34, 3)
        icons.draw(self.surface, "start", cx - 16, cy - 16, 32,
                   self.accent)
        n = len(self.menu)
        for i, (label, sub) in enumerate(self.menu):
            ang = -math.pi / 2 + i * (2 * math.pi / n)
            sel = (i == self.sel)
            nx = cx + int(r * math.cos(ang))
            ny = cy + int(r * math.sin(ang))
            pulse = 0.6 + 0.4 * abs(math.sin(time.time() * 3)) \
                if sel else 1.0
            lcol = tuple(min(255, int(c * pulse)) for c in self.accent) \
                if sel else LINE
            pygame.draw.line(self.surface, lcol, (cx, cy), (nx, ny),
                             2 if sel else 1)
            nr = 22 if sel else 14
            pygame.draw.circle(self.surface, sel_tint(self.accent)
                               if sel else INK, (nx, ny), nr)
            pygame.draw.circle(self.surface, self.accent if sel else
                               FAINT, (nx, ny), nr, 2 if sel else 1)
            icons.draw(self.surface, self.menu_icons[i], nx - nr + 6,
                       ny - nr + 6, nr * 2 - 12,
                       self.accent if sel else FAINT)
            if sel:
                self.last_sel_rect = (nx - nr, ny - nr, nr * 2, nr * 2)
        label, sub = self.menu[self.sel]
        self.f_big.set_bold(True)
        lw = self.f_big.size(label)[0]
        self.text(label, ((W - lw) // 2, 10), self.f_big, FG)
        self.f_big.set_bold(False)
        self.f_small.set_italic(True)
        sw = self.f_small.size(sub)[0]
        self.text(sub, ((W - sw) // 2, 40), self.f_small, FAINT)
        self.f_small.set_italic(False)
        self.footer([("Y", self.t("view")),
                     ("SX/DX", self.t("change")), ("A", self.t("open")),
                     ("B", self.t("exit"))])

    def render_state(self):
        top = self.stack[-1]
        home_style = self.cfg.get("home_style", "blame")
        if top == "home" and home_style == "hud":
            self.render_home_hud()
        elif top == "home" and home_style == "terminal":
            self.render_home_terminal()
        elif top == "home" and home_style == "orbit":
            self.render_home_orbit()
        elif top == "home" and home_style == "nexus":
            self.render_home_nexus()
        elif top == "home":
            self.header("__brand__")
            hy, hh = 50, 96
            hero_sel = (self.sel == 0)
            cut = 26
            pts = [(8, hy), (W - 8 - cut, hy), (W - 8, hy + cut),
                   (W - 8, hy + hh), (8, hy + hh)]
            pygame.draw.polygon(self.surface,
                                sel_tint(self.accent) if hero_sel
                                else INK, pts)
            pygame.draw.polygon(self.surface, self.accent, pts,
                                6 if hero_sel else 5)
            pygame.draw.polygon(self.surface, (40, 30, 10), pts, 1)
            if hero_sel:
                self.last_sel_rect = (8, hy, W - 16, hh)
                for cx2, cy2, dx, dy in ((8, hy, 1, 1),
                                         (8, hy + hh, 1, -1)):
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2 + 12 * dx, cy2), 4)
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2, cy2 + 12 * dy), 4)
                tick = 8 + int((time.time() * 90) % (W - 46))
                pygame.draw.line(self.surface, self.accent,
                                 (tick, hy + hh - 1),
                                 (tick + 9, hy + hh - 1), 2)
            icons.draw(self.surface, self.menu_icons[0], 22, hy + 22, 50,
                       self.accent if hero_sel else DIM)
            label0, sub0 = self.menu[0]
            self.f_big.set_bold(True)
            self.text(label0, (90, hy + 16), self.f_big,
                      FG if hero_sel else DIM)
            self.f_big.set_bold(False)
            self.f_small.set_italic(True)
            self.text(sub0, (92, hy + 56), self.f_small, FAINT,
                      maxw=W - 190)
            self.f_small.set_italic(False)
            base, extra = self.read_envs()
            led_y = hy + 24
            led_x0 = W - 24 - len(ENVS) * 24
            for k, (e, _lbl, _pkgs) in enumerate(ENVS):
                ec = self.env_color(e)
                inst = base and (e == "xfce" or e in extra)
                lx = led_x0 + k * 24
                if inst:
                    pulse = 0.55 + 0.45 * abs(
                        math.sin(time.time() * 2.2 + k * 1.3))
                    glow = tuple(min(255, int(c * pulse)) for c in ec)
                    pygame.draw.circle(self.surface, glow, (lx, led_y), 8)
                    pygame.draw.circle(self.surface, ec, (lx, led_y),
                                       8, 2)
                else:
                    pygame.draw.circle(self.surface, (30, 32, 38),
                                       (lx, led_y), 8)
                    pygame.draw.circle(self.surface, (60, 62, 68),
                                       (lx, led_y), 8, 1)
                pygame.draw.line(self.surface, (60, 62, 68),
                                 (lx - 8, led_y + 16), (lx + 8, led_y + 16))
            ggx, ggy, ggr = W - 30, led_y + 34, 10
            gang = time.time() * 1.3
            for tth in range(8):
                a = gang + tth * math.pi / 4
                x1 = ggx + int((ggr - 3) * math.cos(a))
                y1 = ggy + int((ggr - 3) * math.sin(a))
                x2 = ggx + int(ggr * math.cos(a))
                y2 = ggy + int(ggr * math.sin(a))
                pygame.draw.line(self.surface, STEEL, (x1, y1),
                                 (x2, y2), 2)
            pygame.draw.circle(self.surface, INK, (ggx, ggy), ggr - 4)
            pygame.draw.circle(self.surface, STEEL, (ggx, ggy), ggr - 4,
                               1)
            gx0, gy0, colw, rowh, gap = 8, hy + hh + 10, 308, 67, 8
            for i in range(1, len(self.menu)):
                r_, c_ = divmod(i - 1, 2)
                x = gx0 + c_ * (colw + gap)
                y = gy0 + r_ * (rowh + gap)
                sel = (i == self.sel)
                if sel:
                    self.sel_frame(x, y, colw, rowh)
                else:
                    self.npanel(x, y, colw, rowh, border=LINE, fill=INK,
                                cut=10)
                isz = 34
                icx = (x + colw - isz - 14) if c_ == 0 else (x + 14)
                icy = y + (rowh - isz) // 2
                if sel:
                    gcx, gcy = icx + isz // 2, icy + isz // 2
                    pulse = 0.5 + 0.5 * abs(math.sin(time.time() * 3))
                    for rr, alpha_c in ((isz, 40), (isz * 3 // 4, 70)):
                        glow_col = tuple(
                            min(255, int(BG[ci] + (self.accent[ci] -
                                BG[ci]) * (alpha_c / 255.0) * pulse))
                            for ci in range(3))
                        pygame.draw.circle(self.surface, glow_col,
                                           (gcx, gcy), rr)
                icons.draw(self.surface, self.menu_icons[i], icx, icy,
                           isz, self.accent if sel else FAINT)
                label, sub = self.menu[i]
                tx = (x + 14) if c_ == 0 else (x + 14 + isz + 12)
                tmaxw = colw - isz - 40
                self.f_med.set_bold(True)
                self.text(label, (tx, y + (10 if sel else
                                          (rowh - 20) // 2)),
                          self.f_med, FG if sel else DIM, maxw=tmaxw)
                self.f_med.set_bold(False)
                if sel:
                    self.f_tiny.set_italic(True)
                    self.text(sub, (tx, y + 36), self.f_tiny,
                              FAINT, maxw=tmaxw)
                    self.f_tiny.set_italic(False)
            self.footer([("Y", self.t("view")), ("A", self.t("open")),
                         ("B", self.t("exit"))])
        elif top == "comp":
            it = (self.lang == "it")
            rm = (self.mode == "remove")
            ac, cc = self.accent, comp_color(self.accent)
            bg = getattr(self, "bg", None)
            if bg is not None:
                self.surface.blit(bg, (0, 0))
            else:
                self.surface.fill((7, 8, 11))

            def tab(x, y, w, h, col, chip, icon, label, big, on):
                self.npanel(x, y, w, h, border=col,
                            fill=(sel_tint(col) if on else INK),
                            cut=10 if big else 6)
                f = self.f_big if big else self.f_small
                cw = self.f_small.size(chip)[0]
                self.npanel(x + 10, y + (h - 24) // 2, cw + 14, 24,
                            border=col, fill=INK, cut=5)
                self.text(chip, (x + 17, y + (h - 24) // 2 + 3),
                          self.f_small, col)
                ix = x + 10 + cw + 26
                icons.draw(self.surface, icon, ix,
                           y + (h - (26 if big else 18)) // 2,
                           26 if big else 18, col)
                self.text(label, (ix + (34 if big else 26),
                                  y + (h - f.get_height()) // 2), f,
                          col)
            if not rm:
                tab(10, 6, 366, 40, ac, "L1", "pkg", "INSTALLER",
                    True, True)
                tab(404, 12, 226, 30, cc, "R1", "trash", "UNINSTALLER",
                    False, False)
            else:
                tab(10, 12, 206, 30, ac, "L1", "pkg", "INSTALLER",
                    False, False)
                tab(264, 6, 366, 40, cc, "R1", "trash", "UNINSTALLER",
                    True, True)
            mc = cc if rm else ac
            n = len(self.marked)
            y0 = 88
            if self.img_total:
                used = self.img_total - (self.img_free or 0)
                pct = min(100, used * 100 // self.img_total)
                self.npanel(8, 50, W - 16, 32, border=LINE, fill=INK,
                            cut=8)
                self.text("%s / %s" % (human(used),
                                       human(self.img_total)),
                          (20, 57), self.f_small, DIM)
                ptxt = "%d%%" % pct
                if n:
                    ptxt = ("%d sel   " % n) + ptxt
                self.text(ptxt,
                          (W - 26 - self.f_small.size(ptxt)[0], 57),
                          self.f_small,
                          mc if n else (NO_R if pct > 85 else DIM))
                bw = W - 240
                pygame.draw.rect(self.surface, (14, 15, 19),
                                 (170, 72, bw, 5))
                pygame.draw.rect(self.surface,
                                 NO_R if pct > 85 else mc,
                                 (170, 72, bw * pct // 100, 5))
            else:
                y0 = 52
            per = (H - 46 - y0) // 44
            visible = [(j2, rr) for j2, rr in enumerate(self.rows)
                      if rr[0] == "cat" or
                      self.cat_of(j2) not in self.cat_collapsed]
            sel_pos = next((k2 for k2, (j2, _) in enumerate(visible)
                           if j2 == self.row_sel), 0)
            first = max(0, min(sel_pos - per // 2, len(visible) - per))
            y = y0
            for j, r_ in visible[first:first + per]:
                if r_[0] == "cat":
                    catic = CAT_ICONS.get(r_[1], "pkg")
                    cattxt = CAT_NAMES_EN.get(r_[1], r_[1]) if not it \
                        else r_[1]
                    coll = r_[1] in self.cat_collapsed
                    arrow = "> " if coll else "v "
                    if rm:
                        pygame.draw.line(self.surface, LINE,
                                         (10, y + 30), (W - 10, y + 30),
                                         3)
                        tw = self.f_med.size(cattxt)[0]
                        icons.draw(self.surface, catic, W - 40 - tw,
                                   y + 6, 22, mc)
                        self.text(arrow + cattxt, (W - 54 - tw, y + 8),
                                  self.f_med, mc)
                    else:
                        pygame.draw.line(self.surface, LINE,
                                         (10, y + 30), (W - 10, y + 30),
                                         3)
                        icons.draw(self.surface, catic, 12, y + 6, 22,
                                   mc)
                        self.text(arrow + cattxt, (40, y + 8),
                                  self.f_med, mc)
                    y += 40
                    continue
                name, desc, ic_ = r_[1], r_[3], r_[4]
                inst = bool(self.status.get(name))
                if not it:
                    name, desc = PKG_TR_EN.get(name, (name, desc))
                sel = (j == self.row_sel)
                mk = (j in self.marked)
                if sel:
                    self.sel_frame(6, y, W - 12, 40, color=mc)
                if not rm:
                    self.npanel(16, y + 9, 22, 22, border=mc,
                                fill=(mc if mk else INK), cut=5)
                    icons.draw(self.surface, ic_, 46, y + 8, 24,
                               mc if sel else FAINT)
                    self.text(name, (78, y + 2), self.f_med,
                              FG if sel else DIM, maxw=W - 236)
                    self.text(desc, (78, y + 23), self.f_tiny, FAINT,
                              maxw=W - 256)
                    st = "OK" if inst else "—"
                    self.text(st,
                              (W - 26 - self.f_small.size(st)[0],
                               y + 10), self.f_small,
                              OK_G if inst else FAINT)
                else:
                    self.npanel(W - 38, y + 9, 22, 22, border=mc,
                                fill=(mc if mk else INK), cut=5)
                    sym = "V" if inst else "X"
                    self.text(sym, (W - 64, y + 8), self.f_med,
                              OK_G if inst else (92, 96, 104))
                    icons.draw(self.surface, ic_, W - 96, y + 9, 20,
                               mc if sel else FAINT)
                    ncol = (FG if sel else DIM) if inst else FAINT
                    nw = min(self.f_med.size(name)[0], W - 340)
                    self.text(name, (W - 104 - nw, y + 2), self.f_med,
                              ncol, maxw=nw + 4)
                    dw = min(self.f_tiny.size(desc)[0], W - 340)
                    self.text(desc, (W - 104 - dw, y + 23),
                              self.f_tiny, FAINT, maxw=dw + 4)
                y += 44
            foot = [("A", (("rimuovi" if it else "remove") if rm else
                           ("installa" if it else "install"))
                     + ((" (%d)" % n) if n else "")),
                    ("X", "sel"), ("Y", "tutti" if it else "all"),
                    ("START", "+/-" ), ("SEL", "scan")]
            foot.append(("L1", "installer") if rm
                        else ("R1", "uninstaller"))
            foot.append(("B", self.t("back")))
            self.footer(foot)

        elif top == "muosapps":
            it = (self.lang == "it")
            view = self.cfg.get("mapp_view", "list")
            vtag = {"list": "LISTA" if it else "LIST",
                    "grid": "GRIGLIA" if it else "GRID",
                    "compact": "ELENCO" if it else "COMPACT",
                    "detailed": "DETTAGLIATO" if it else "DETAILED"}[view]
            self.header(self.t("mapps_t"), vtag)
            if not self.mapps:
                self.npanel(60, 180, W - 120, 100, border=LINE, fill=INK)
                self.text(self.t("mapps_none"), (84, 210), self.f_med, DIM,
                          maxw=W - 160)
                self.text("SD1/SD2: MUOS/application/<app>/mux_launch.sh",
                          (84, 244), self.f_tiny, FAINT, maxw=W - 160)
            elif view == "grid":
                cols = self.mapp_grid_cols
                cw2 = (W - 16 - (cols - 1) * 8) // cols
                ch2 = 84
                rows_vis = (H - 90) // (ch2 + 8)
                sel_row = self.mapp_sel // cols
                first_row = max(0, min(sel_row - rows_vis // 2,
                                       max(0, (len(self.mapps) - 1) //
                                          cols - rows_vis + 1)))
                y0 = 50
                for j in range(first_row * cols,
                              min((first_row + rows_vis) * cols,
                                 len(self.mapps))):
                    r_, c_ = divmod(j - first_row * cols, cols)
                    x = 8 + c_ * (cw2 + 8)
                    y = y0 + r_ * (ch2 + 8)
                    sel = (j == self.mapp_sel)
                    app = self.mapps[j]
                    if sel:
                        self.sel_frame(x, y, cw2, ch2)
                    else:
                        self.npanel(x, y, cw2, ch2, border=LINE, fill=INK,
                                    cut=8)
                    icon_img = self.mapp_icon(app, 40)
                    self.surface.blit(icon_img,
                                      (x + (cw2 - 40) // 2, y + 8))
                    self.text(app["name"][:14], (x + 4, y + 54),
                              self.f_tiny, FG if sel else DIM,
                              maxw=cw2 - 8)
            elif view == "compact":
                per = 13
                first = max(0, min(self.mapp_sel - per // 2,
                                   len(self.mapps) - per))
                y = 50
                for j in range(first, min(first + per, len(self.mapps))):
                    app = self.mapps[j]
                    sel = (j == self.mapp_sel)
                    if sel:
                        self.sel_frame(8, y, W - 16, 28)
                    self.text(app["name"], (18, y + 5), self.f_small,
                              FG if sel else DIM, maxw=W - 110)
                    self.text(app["sd"], (W - 70, y + 5), self.f_tiny,
                              FAINT)
                    y += 28
            elif view == "detailed":
                per = 4
                first = max(0, min(self.mapp_sel - per // 2,
                                   len(self.mapps) - per))
                y = 50
                for j in range(first, min(first + per, len(self.mapps))):
                    app = self.mapps[j]
                    sel = (j == self.mapp_sel)
                    rh = 86
                    if sel:
                        self.sel_frame(8, y, W - 16, rh)
                    else:
                        self.npanel(8, y, W - 16, rh, border=LINE,
                                    fill=INK)
                    self.surface.blit(self.mapp_icon(app, 44),
                                      (18, y + 10))
                    self.text(app["name"], (72, y + 8), self.f_med,
                              FG if sel else DIM, maxw=W - 110)
                    qi = self.mapp_quick_info(app)
                    self.text(app["sd"], (72, y + 32), self.f_tiny,
                              FAINT)
                    if qi["date"]:
                        self.text(("installata " if it else "installed ")
                                  + qi["date"], (72, y + 48),
                                  self.f_tiny, FAINT)
                    if qi["help"]:
                        self.text(qi["help"], (72, y + 64), self.f_tiny,
                                  DIM, maxw=W - 110)
                    y += rh + 6
            else:                                   # list (default)
                per = 7
                first = max(0, min(self.mapp_sel - per // 2,
                                   len(self.mapps) - per))
                y = 50
                for j in range(first, min(first + per, len(self.mapps))):
                    app = self.mapps[j]
                    if j == self.mapp_sel:
                        self.sel_frame(8, y, W - 16, 52)
                    self.surface.blit(self.mapp_icon(app), (20, y + 8))
                    self.text(app["name"], (68, y + 8), self.f_med,
                              FG if j == self.mapp_sel else DIM,
                              maxw=W - 180)
                    self.text(app["sd"], (68, y + 32), self.f_tiny, FAINT)
                    y += 52
            self.footer([("A", self.t("mapps_go")),
                         ("X", "opzioni" if it else "options"),
                         ("Y", "vista" if it else "view"),
                         ("R1", self.t("mapps_r1")),
                         ("B", self.t("back"))])
        elif top == "session":
            it = (self.lang == "it")
            self.header(self.t("sess"))
            base, extra = self.read_envs()
            cur = self.cfg.get("desk_env", "xfce")
            imgtxt, imgcol = self.img_state_line()
            CUTS = {"xfce": 20, "icewm": 30, "lxde": 10}
            y = 50
            bh = 122
            for j, (env, _lbl, _pkgs) in enumerate(ENVS):
                col = self.env_color(env)
                inst = base and (env == "xfce" or env in extra)
                sel = (j == self.env_sel)
                dim = col if (inst or not base) else FAINT
                if sel:
                    self.sel_frame(8, y, W - 16, bh, color=col,
                                   cut=CUTS[env])
                else:
                    self.npanel(8, y, W - 16, bh, border=LINE, fill=INK,
                                cut=CUTS[env])
                self.env_box_motif(env, 8, y, W - 16, bh, dim)
                icx, icy, icsz = 20, y + 15, 60
                fillbox = sel_tint(col) if sel else INK
                self.env_icon_frame(env, icx, icy, icsz, dim, fillbox)
                self.env_glyph(env, icx + 8, icy + 7, 3, dim)
                nbx = icx + icsz + 4
                nbw = 216
                self.env_name_frame(env, nbx, icy, nbw, icsz, dim,
                                    fillbox)
                self.text(env.upper(), (nbx + 18, icy + 8), self.f_big,
                          dim)
                self.text(ENV_CODENAME.get(env, ""), (nbx + 19,
                          icy + 42), self.f_small,
                          DIM if (inst or not base) else FAINT)
                if not base:
                    btxt, bcol = self.t("e_base"), DIM
                elif env == cur and inst:
                    btxt, bcol = "\u25b6 " + self.t("e_active"), OK_G
                elif inst:
                    btxt, bcol = "\u2713 " + self.t("e_inst"), OK_G
                else:
                    btxt, bcol = "\u2715 " + self.t("e_missing"), NO_R
                bw_ = self.f_small.size(btxt)[0]
                bx = W - 26 - bw_
                self.npanel(bx - 14, y + 15, bw_ + 24, 26, border=bcol,
                            fill=INK, cut=6)
                self.text(btxt, (bx - 4, y + 19), self.f_small, bcol)
                pygame.draw.line(self.surface, LINE, (18, y + bh - 24),
                                 (W - 18, y + bh - 24), 1)
                self.text(imgtxt, (18, y + bh - 19), self.f_tiny, imgcol)
                y += bh + 8
            self.footer([("A", self.t("sess_a")),
                         ("X", "dettagli" if it else "details"),
                         ("B", self.t("back"))])
        elif top == "envdetail":
            it = (self.lang == "it")
            env = self.envdet_env
            base, extra = self.read_envs()
            inst = base and (env == "xfce" or env in extra)
            col = self.env_color(env)
            self.header(env.upper() + " // " + ENV_CODENAME.get(env, ""),
                        icon="uplink")
            self.npanel(8, 48, W - 16, 46, border=col, fill=INK, cut=10)
            self.env_glyph(env, 18, 55, 2, col)
            if not base:
                stxt, scol = self.t("e_base"), DIM
            elif inst:
                stxt = ("attivo" if env == self.cfg.get("desk_env")
                        and it else "active" if env ==
                        self.cfg.get("desk_env") else self.t("e_inst"))
                scol = OK_G
            else:
                stxt, scol = self.t("e_missing"), NO_R
            self.text(stxt, (56, 62), self.f_med, scol)
            imgtxt, imgcol = self.img_state_line()
            self.text(imgtxt, (W - 26 - self.f_tiny.size(imgtxt)[0], 68),
                      self.f_tiny, imgcol)
            acts = self.env_detail_actions(env, base, inst)
            y = 104
            for j, (k, ic, lab) in enumerate(acts):
                sel = (j == self.envdet_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 44, color=col)
                icons.draw(self.surface, ic, 18, y + 10, 24,
                           NO_R if k == "remove" else
                           (col if sel else FAINT))
                self.text(lab, (54, y + 11), self.f_med,
                          NO_R if k == "remove" else
                          (FG if sel else DIM), maxw=W - 80)
                y += 46
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "autostart":
            rows = [r for r in self.rows if r[0] == "item"]
            auto = set(self.cfg.get("autostart", []))
            self.header(self.t("title_auto"), "%d" % len(auto))
            if not rows:
                self.text(self.t("not_inst"), (26, 70), self.f_med, DIM)
            per = 8
            first = max(0, min(self.row_sel - per // 2, len(rows) - per))
            y = 54
            for i in range(first, min(first + per, len(rows))):
                _t0, name, exe, desc, ic = rows[i]
                on = name in auto
                if i == self.row_sel:
                    self.sel_frame(8, y, W - 16, 44)
                icons.draw(self.surface, ic, 20, y + 11, 22,
                           self.accent if on else DIM)
                self.text(name, (54, y + 3), self.f_med,
                          FG if i == self.row_sel else DIM)
                self.text(exe, (54, y + 24), self.f_tiny, FAINT)
                lab = self.t("auto_on") if on else self.t("auto_off")
                lw = self.f_small.size(lab)[0]
                self.npanel(W - lw - 34, y + 10, lw + 18, 24,
                            border=(OK_G if on else LINE), fill=INK, cut=6)
                self.text(lab, (W - lw - 25, y + 13), self.f_small,
                          OK_G if on else FAINT)
                y += 46
            self.footer([("A", self.t("change")), ("B", self.t("back"))])
        elif top == "map":
            self.header(self.t("title_map"))
            rows = self.map_rows()
            per = 8
            first = max(0, min(self.map_sel - per // 2, len(rows) - per))
            y = 50
            for i in range(first, min(first + per, len(rows))):
                key = rows[i]
                if i == self.map_sel:
                    self.sel_frame(8, y, W - 16, 44)
                if key == "__stick__":
                    icons.draw(self.surface, "gamepad", 20, y + 10, 24,
                               self.accent)
                    self.text(self.t("map_stick"), (54, y + 3), self.f_med,
                              FG if i == self.map_sel else DIM)
                    val = self.cfg.get("mouse_stick", "sinistro")
                else:
                    f = FUNC_BY_KEY[key]
                    icons.draw(self.surface, f[3], 20, y + 10, 24,
                               self.accent)
                    lab = f[1] if self.lang == "it" else f[2]
                    self.text(lab, (54, y + 3), self.f_med,
                              FG if i == self.map_sel else DIM)
                    if key == "kbd":
                        self.text("watcher VoidDesk", (54, y + 25),
                                  self.f_tiny, FAINT)
                    val = self.btn_names(self.cur_map().get(key, []))
                vw = self.f_med.size(val)[0]
                # "chip" col tasto assegnato
                self.npanel(W - vw - 34, y + 8, vw + 16, 26,
                            border=LINE, fill=INK, cut=6)
                self.text(val, (W - vw - 26, y + 11), self.f_med,
                          self.accent)
                y += 46
            self.footer([("A", self.t("assign")), ("Y", self.t("reset")),
                         ("X", self.t("reset_all")), ("B", self.t("back"))])
        elif top == "capture":
            self.header(self.t("title_map"))
            key = self.map_rows()[self.map_sel]
            f = FUNC_BY_KEY[key]
            lab = f[1] if self.lang == "it" else f[2]
            self.npanel(60, 150, W - 120, 170, border=self.accent,
                        fill=INK, cut=14)
            icons.draw(self.surface, f[3], W // 2 - 16, 172, 32, self.accent)
            t1 = self.t("press")
            self.text(t1, (W // 2 - self.f_small.size(t1)[0] // 2, 218),
                      self.f_small, DIM)
            self.text(lab, (W // 2 - self.f_big.size(lab)[0] // 2, 240),
                      self.f_big, FG)
            left = max(0, 5 - int(time.time() - self.capture_t))
            t2 = "%s  (%ds)" % (self.t("press_s"), left)
            self.text(t2, (W // 2 - self.f_tiny.size(t2)[0] // 2, 288),
                      self.f_tiny, FAINT)
        elif top == "swap":
            key, ev, other = self.pending
            self.header(self.t("title_map"))
            fk = FUNC_BY_KEY[key]
            fo = FUNC_BY_KEY[other]
            lk = fk[1] if self.lang == "it" else fk[2]
            lo = fo[1] if self.lang == "it" else fo[2]
            self.npanel(40, 150, W - 80, 170, border=NO_R,
                        fill=INK, cut=14)
            m1 = self.t("used_by") % (EV2NAME.get(ev, "?"), lo)
            self.text(m1, (W // 2 - self.f_med.size(m1)[0] // 2, 180),
                      self.f_med, FG, maxw=W - 100)
            m2 = "%s  →  %s" % (EV2NAME.get(ev, "?"), lk)
            self.text(m2, (W // 2 - self.f_med.size(m2)[0] // 2, 222),
                      self.f_med, self.accent)
            m3 = self.t("swap_q")
            self.text(m3, (W // 2 - self.f_small.size(m3)[0] // 2, 270),
                      self.f_small, DIM)
        elif top == "options":
            self.header(self.t("h_set"), icon="gear")
            defs = self.opt_defs()
            first = max(0, min(getattr(self, "opt_scroll", 0),
                               max(0, len(defs) - 1)))
            y = 50
            self.content_panel(46, H - 40)
            for k in range(first, len(defs)):
                if y > H - 44:
                    break
                key, ck, vals = defs[k]
                if key == "hdr":
                    pygame.draw.line(self.surface, LINE, (10, y + 18),
                                     (W - 10, y + 18), 1)
                    pygame.draw.rect(self.surface, self.accent,
                                     (10, y + 10, 4, 12))
                    self.text(ck, (22, y + 6), self.f_small, self.accent)
                    y += 30
                    continue
                if k == self.opt_sel:
                    self.sel_frame(8, y, W - 16, 36)
                self.text(self.t(key), (22, y + 7), self.f_med,
                          FG if k == self.opt_sel else DIM)
                val = self.cfg.get(ck, vals[0] if vals else "")
                vs = self.tx(VAL_EN, self.t("yes") if val is True else
                             self.t("no") if val is False else str(val))
                vw = self.f_med.size(vs)[0]
                self.npanel(W - vw - 40, y + 4, vw + 20, 28,
                            border=LINE, fill=INK, cut=6)
                self.text(vs, (W - vw - 30, y + 8), self.f_med, self.accent)
                y += 40
            self.footer([("A", self.t("change")), ("B", self.t("back"))])
        elif top == "logs":
            self.header(self.t("w_logs"), icon="doc")
            per = 9
            first = max(0, min(self.sel_log - per // 2,
                               len(self.logs) - per))
            y = 50
            self.content_panel(46, H - 40)
            for k in range(first, min(first + per, len(self.logs))):
                kind, a = self.logs[k][0], self.logs[k]
                if kind == "hdr":
                    pygame.draw.line(self.surface, LINE, (10, y + 20),
                                     (W - 10, y + 20), 1)
                    pygame.draw.rect(self.surface, self.accent,
                                     (10, y + 12, 4, 12))
                    self.text(a[1], (22, y + 8), self.f_small, self.accent)
                    y += 34
                    continue
                if k == self.sel_log:
                    self.sel_frame(8, y, W - 16, 40)
                icons.draw(self.surface, "doc", 18, y + 8, 22, FAINT)
                self.text(a[0], (50, y + 3), self.f_med,
                          FG if k == self.sel_log else DIM)
                ok = os.path.exists(a[1])
                self.text(a[1] if ok else self.t("log_missing"),
                          (50, y + 23), self.f_tiny,
                          FAINT if ok else NO_R, maxw=W - 80)
                y += 42
            self.footer([("A", self.t("open")),
                         ("X", "archivio" if self.lang == "it" else
                         "archive"), ("B", self.t("back"))])
        elif top == "logarchive":
            it = (self.lang == "it")
            self.header("LOG REGISTRY", icon="doc")
            roots = self.fm_roots()
            actions = [("sd:" + p, lbl) for p, lbl in roots] + \
                [("clear", None)]
            total, cnt = self.logs_total_size()
            self.text(("archivio di TUTTI i log in un file .zip -- "
                      "%d log, %s totali" % (cnt, human(total))) if it
                      else ("archive of ALL logs in one .zip file -- "
                      "%d logs, %s total" % (cnt, human(total))),
                      (14, 50), self.f_small, FAINT, maxw=W - 28)
            y = 84
            for j, (act, lbl) in enumerate(actions):
                sel = (j == self.logarchive_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 44)
                if act == "clear":
                    icons.draw(self.surface, "trash", 18, y + 10, 24,
                              NO_R if sel else FAINT)
                    self.text("svuota tutti i log" if it else
                              "clear all logs", (54, y + 6), self.f_med,
                              NO_R if sel else DIM)
                    self.text("azzera il contenuto, i file restano" if
                              it else "empties the content, files "
                              "remain", (54, y + 26), self.f_tiny,
                              FAINT, maxw=W - 80)
                else:
                    icons.draw(self.surface, "download", 18, y + 10, 24,
                              self.accent if sel else FAINT)
                    self.text(("crea archivio su " + lbl) if it else
                              ("create archive on " + lbl),
                              (54, y + 6), self.f_med,
                              FG if sel else DIM)
                    self.text(act[3:], (54, y + 26), self.f_tiny, FAINT,
                              maxw=W - 80)
                y += 52
            self.footer([("A", self.t("confirm")), ("B", self.t("back"))])
        elif top == "info":
            self.header(self.t("title_info"))
            rows = self.info_lines or []
            first = max(0, min(self.scroll, max(0, len(rows) - 1)))
            y = 50
            bottom = H - 46
            self.content_panel(46, bottom + 4)
            for r in rows[first:]:
                if y >= bottom:
                    break
                if not isinstance(r, tuple):
                    self.text(str(r), (30, y), self.f_med, FG, maxw=W - 60)
                    y += 24
                    continue
                if r[0] == "sec":
                    icons.draw(self.surface, r[1], 14, y + 1, 15, self.accent)
                    lab = self.tx(STAT_EN, r[2])
                    self.text(lab, (36, y), self.f_small, self.accent)
                    tw = self.f_small.size(lab)[0]
                    pygame.draw.line(self.surface, LINE, (44 + tw, y + 8),
                                     (W - 14, y + 8), 1)
                    y += 22
                else:
                    key_s = self.tx(STAT_EN, r[1])
                    val_s = self.tx(VAL_EN, r[2])
                    col = r[3]
                    if key_s:
                        self.text(key_s, (30, y), self.f_tiny, FAINT)
                    avail_w = (W - 240) if key_s else (W - 60)
                    x0 = 220 if key_s else 30
                    if self.f_small.size(val_s)[0] <= avail_w:
                        self.text(val_s, (x0, y - 2), self.f_small, col,
                                  maxw=avail_w)
                        y += 20
                    else:
                        wrapped = self.note_wrap(val_s, W - 60,
                                                 self.f_small, 6)
                        if key_s:
                            y += 18
                        for wln in wrapped:
                            if y >= bottom:
                                break
                            self.text(wln, (30, y), self.f_small, col,
                                      maxw=W - 60)
                            y += 19
                        y += 5
            self.footer([(self.t("k_ud"), self.t("page")), ("B", self.t("back"))])
        elif top == "manifesto":
            self.header("MANIFESTO", icon="terminal")
            self.surface.fill((4, 5, 7), (0, 44, W, H - 44))
            for sy in range(44, H, 3):
                pygame.draw.line(self.surface, (2, 3, 4), (0, sy),
                                 (W, sy), 1)
            self.content_panel(46, H - 40)
            pad = 24
            maxw = W - pad * 2
            disp = []
            for kind, txt in self.manifesto_lines():
                if kind == "gap":
                    disp.append(("gap", ""))
                elif kind == "msg":
                    for wl in self.note_wrap(txt, maxw, self.f_small, 40):
                        disp.append(("msg", wl))
                else:
                    disp.append((kind, txt))
            first = max(0, min(self.scroll, max(0, len(disp) - 3)))
            y = 54
            bottom = H - 46
            for kind, txt in disp[first:]:
                if y >= bottom:
                    break
                if kind == "gap":
                    y += 12
                elif kind == "sys":
                    self.text(txt, (pad, y), self.f_tiny, FAINT,
                              maxw=maxw)
                    y += 18
                elif kind == "sig":
                    self.text(txt, (pad, y), self.f_small, self.accent,
                              maxw=maxw)
                    y += 20
                else:
                    self.text(txt, (pad, y), self.f_small, FG, maxw=maxw)
                    y += 19
            if y < bottom - 4:
                blink = int(time.time() * 2) % 2 == 0
                if blink:
                    self.text("_", (pad, y), self.f_small, self.accent)
            self.footer([(self.t("k_ud"), self.t("page")),
                        ("B", self.t("back"))])
        elif top == "viewer":
            if getattr(self, "viewer_live", False):
                try:
                    txt = open(self._viewer_path, errors="ignore"
                               ).read()[-16000:]
                    self.viewer_lines = txt.splitlines()[-400:]
                    self.scroll = max(0, len(self.viewer_lines) - 18)
                except (OSError, AttributeError):
                    pass

            self.header("LOG", "%d-%d / %d" %
                        (self.scroll + 1,
                         min(self.scroll + 23, len(self.log_lines)),
                         len(self.log_lines)))
            y = 48
            self.content_panel(44, H - 40)
            for ln in self.log_lines[self.scroll:self.scroll + 23]:
                self.text(ln, (10, y), self.f_small, DIM, maxw=W - 20)
                y += 17
            self.footer([(self.t("k_ud"), self.t("row")), (self.t("k_lr"), self.t("page")),
                         ("B", self.t("back"))])
        elif top.startswith("hub:") and top[4:] == "forge":
            icon, tkey, items = HUBS["forge"]
            self.header(self.t(tkey), icon=icon)
            self.forge_backdrop()
            n = len(items)
            tw_, th_ = 260, 46
            gap = 18
            total_h = n * th_ + (n - 1) * gap
            y0 = max(50, (H - 40 - total_h) // 2 + 44)
            cx = W // 2
            # catena verticale che collega i riquadri: una serie di
            # anelli ovali alternati orizzontale/verticale, come una
            # catena vera vista di lato
            if n > 1:
                ly = y0 + th_
                link = 0
                while ly < y0 + total_h - th_ + 2:
                    horiz = (link % 2 == 0)
                    rw_, rh_ = (14, 8) if horiz else (8, 14)
                    pygame.draw.ellipse(self.surface, STEEL,
                                       (cx - rw_ // 2, ly, rw_, rh_), 2)
                    ly += 10
                    link += 1
            for j, (k, ic, lk, sk, kind) in enumerate(items):
                ty = y0 + j * (th_ + gap)
                sel = (j == self.hub_sel)
                x0 = cx - tw_ // 2
                col = self.accent if sel else LINE
                if sel:
                    self.sel_frame(x0, ty, tw_, th_)
                else:
                    self.npanel(x0, ty, tw_, th_, border=col, fill=INK,
                               cut=10)
                icons.draw(self.surface, ic, x0 + 14, ty + (th_ - 28) //
                          2, 28, self.accent if sel else FAINT)
                self.text(self.t(lk), (x0 + 54, ty + 8), self.f_med,
                          FG if sel else DIM)
                self.text(self.t(sk), (x0 + 54, ty + 32), self.f_small,
                          FAINT, maxw=tw_ - 66)
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top.startswith("hub:") and top[4:] == "workshop":
            it = (self.lang == "it")
            items = HUBS["workshop"][2]
            self.header(self.t("h_work"), icon="workshop")
            self.mon_sample()
            m = self.mon
            widgets = [("CPU", m["cpu"], self.accent, "pill"),
                      ("RAM", m["ram"], (110, 195, 250), "blocks"),
                      ("TEMP", m["tmp"], NO_R, "thermo")]
            ww = (W - 24) // 3
            wy = 48
            for i2, (lbl, data, col, kind) in enumerate(widgets):
                x = 8 + i2 * (ww + 4)
                self.npanel(x, wy, ww, 56, border=LINE, fill=INK,
                           cut=8)
                self.text(lbl, (x + 8, wy + 6), self.f_tiny, col)
                cur = data[-1] if data else 0
                vs = ("%d°C" % m.get("tempc", 0) if lbl == "TEMP"
                      else "%d%%" % cur)
                vw = self.f_small.size(vs)[0]
                self.text(vs, (x + ww - vw - 8, wy + 4), self.f_small,
                          col)
                if kind == "pill":
                    self.mon_pill(x + 8, wy + 32, ww - 16, 14, cur, col)
                elif kind == "blocks":
                    self.mon_blocks(x + 8, wy + 32, ww - 16, 14, cur,
                                    col, n=10)
                else:
                    self.mon_thermo(x + ww // 2, wy + 26, wy + 50, 7,
                                    cur, col)
            y = wy + 64
            per = 7
            first = max(0, min(self.hub_sel - per // 2, len(items) - per))
            for j in range(first, min(first + per, len(items))):
                k, ic, lk, sk, kind = items[j]
                if j == self.hub_sel:
                    self.sel_frame(8, y, W - 16, 42)
                icons.draw(self.surface, ic, 18, y + 9, 24,
                          self.accent if j == self.hub_sel else FAINT)
                self.text(self.t(lk), (54, y + 4), self.f_med,
                          FG if j == self.hub_sel else DIM)
                self.text(self.t(sk), (54, y + 24), self.f_tiny, FAINT,
                          maxw=W - 200)
                y += 44
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top.startswith("hub:") and top[4:] == "toolbox":
            it = (self.lang == "it")
            items = HUBS["toolbox"][2]
            self.header(self.t("h_tool"), icon="toolbox")
            headers, layout_items, total_h = self._toolbox_layout()
            vtop, vbot = 48, H - 40
            vh = vbot - vtop
            sel_y, sel_h = 0, 40
            for j, lx, ly, lw, lh in layout_items:
                if j == self.hub_sel:
                    sel_y, sel_h = ly, lh
                    break
            scroll = getattr(self, "toolbox_scroll", 0)
            if sel_y - scroll < 0:
                scroll = max(0, sel_y - 26)
            elif sel_y + sel_h - scroll > vh:
                scroll = sel_y + sel_h - vh
            scroll = max(0, min(scroll, max(0, total_h - vh)))
            self.toolbox_scroll = scroll
            for title_it, title_en, gic, hy in headers:
                sy = vtop + hy - scroll
                if sy < vtop - 20 or sy > vbot:
                    continue
                title = title_it if it else title_en
                pygame.draw.line(self.surface, LINE, (10, sy + 16),
                                 (W - 10, sy + 16), 1)
                icons.draw(self.surface, gic, 8, sy, 20, self.accent)
                self.text(title, (34, sy + 2), self.f_small, self.accent)
            for j, lx, ly, lw, lh in layout_items:
                sy = vtop + ly - scroll
                if sy + lh < vtop - 4 or sy > vbot:
                    continue
                self._tb_tile(j, items[j], lx, sy, lw, lh,
                              icon_sz=(28 if lh >= 64 else
                                      24 if lh <= 58 else 26),
                              big=(lh >= 64 and lw > 250),
                              compact=(lh == 58))
            if total_h > vh:
                bar_h = max(20, int(vh * vh / total_h))
                bar_y = vtop + int((vh - bar_h) * scroll /
                                   max(1, total_h - vh))
                pygame.draw.rect(self.surface, LINE,
                                 (W - 5, vtop, 3, vh))
                pygame.draw.rect(self.surface, self.accent,
                                 (W - 5, bar_y, 3, bar_h))
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top.startswith("hub:") and top[4:] == "uplink":
            it = (self.lang == "it")
            items = HUBS["uplink"][2]
            self.header(self.t("h_up"), icon="uplink")
            st = self.status_snapshot()
            hot_on = self.hot_active()
            row_defs = [("wifi", "wifi", bool(st.get("conn"))),
                       ("hotspot", "uplink", hot_on),
                       ("bt", "bt", bool(st.get("bt")))]
            rw = (W - 24) // 3
            for i, (key, ic, on) in enumerate(row_defs):
                x = 8 + i * (rw + 4)
                y = 50
                sel = (self.hub_sel == i)
                lk = items[i][2]
                if sel:
                    self.sel_frame(x, y, rw, 84)
                else:
                    self.npanel(x, y, rw, 84, border=LINE, fill=INK,
                                cut=10)
                icons.draw(self.surface, ic, x + (rw - 30) // 2, y + 8,
                          30, self.accent if sel else
                          (OK_G if on else FAINT))
                lab = self.t(lk)
                lw = self.f_small.size(lab)[0]
                self.text(lab, (x + (rw - lw) // 2, y + 44),
                          self.f_small, FG if sel else DIM)
                dot_col = OK_G if on else (70, 72, 78)
                pygame.draw.circle(self.surface, dot_col,
                                   (x + rw // 2, y + 68), 5)
                pygame.draw.circle(self.surface, INK,
                                   (x + rw // 2, y + 68), 5, 1)
                onoff = ("ON" if on else "OFF")
                ow = self.f_tiny.size(onoff)[0]
                self.text(onoff, (x + rw // 2 + 10, y + 62), self.f_tiny,
                          OK_G if on else FAINT)
            y = 150
            per = 5
            list_items = items[3:]
            first = max(0, min(self.hub_sel - 3 - per // 2,
                               len(list_items) - per))
            for j in range(first, min(first + per, len(list_items))):
                real_j = j + 3
                k, ic, lk, sk, kind = items[real_j]
                sel = (real_j == self.hub_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 42)
                icons.draw(self.surface, ic, 18, y + 9, 24,
                          self.accent if sel else FAINT)
                self.text(self.t(lk), (54, y + 4), self.f_med,
                          FG if sel else DIM)
                self.text(self.t(sk), (54, y + 24), self.f_tiny, FAINT,
                          maxw=W - 200)
                if kind == "cycle":
                    ck, vals = CYCLES[k]
                    vs = self.tx(VAL_EN, str(self.cfg.get(ck, vals[0])))
                    vw = self.f_small.size(vs)[0]
                    self.npanel(W - vw - 38, y + 8, vw + 18, 26,
                                border=LINE, fill=INK, cut=6)
                    self.text(vs, (W - vw - 29, y + 13), self.f_small,
                              self.accent)
                y += 44
            self.footer([("A", self.t("open")),
                        ("SX/DX", "rete" if it else "network"),
                        ("B", self.t("back"))])
        elif top.startswith("hub:"):
            hub = top[4:]
            icon, tkey, items = HUBS[hub]
            self.header(self.t(tkey), icon=icon)
            y = 52
            per = 9
            first = max(0, min(self.hub_sel - per // 2, len(items) - per))
            shown = min(per, len(items))
            self.content_panel(y - 4, y - 4 + shown * 44 + 8)
            for j in range(first, min(first + per, len(items))):
                k, ic, lk, sk, kind = items[j]
                if j == self.hub_sel:
                    self.sel_frame(8, y, W - 16, 42)
                icons.draw(self.surface, ic, 18, y + 9, 24,
                           self.accent if j == self.hub_sel else FAINT)
                self.text(self.t(lk), (54, y + 4), self.f_med,
                          FG if j == self.hub_sel else DIM)
                self.text(self.t(sk), (54, y + 24), self.f_tiny, FAINT,
                          maxw=W - 200)
                if kind == "cycle":
                    ck, vals = CYCLES[k]
                    vs = self.tx(VAL_EN, str(self.cfg.get(ck, vals[0])))
                    vw = self.f_small.size(vs)[0]
                    self.npanel(W - vw - 38, y + 8, vw + 18, 26,
                                border=LINE, fill=INK, cut=6)
                    self.text(vs, (W - vw - 29, y + 13), self.f_small,
                              self.accent)
                y += 44
            self.footer([("A", self.t("open")), ("B", self.t("back"))])

        elif top == "boostcfg":
            self.header("VOID BOOST", icon="gauge")
            for j, (ck, lk) in enumerate((("boost_swap", "bs_swap"),
                                          ("boost_cpu", "bs_cpu"))):
                y = 60 + j * 52
                if j == self.boost_sel:
                    self.sel_frame(8, y, W - 16, 46)
                icons.draw(self.surface, "gauge", 18, y + 11, 24,
                           self.accent)
                self.text(self.t(lk), (54, y + 12), self.f_med, FG)
                on = self.cfg.get(ck, True)
                vs = self.t("yes") if on else self.t("no")
                vw = self.f_med.size(vs)[0]
                self.npanel(W - vw - 40, y + 8, vw + 20, 30,
                            border=(OK_G if on else LINE), fill=INK, cut=6)
                self.text(vs, (W - vw - 30, y + 12), self.f_med,
                          OK_G if on else FAINT)
            self.npanel(8, 176, W - 16, 200, border=LINE, fill=INK)
            yy = 190
            try:
                for ln in open(os.path.join(DATA, ".boost_info")
                               ).read().splitlines()[:5]:
                    self.text(ln, (24, yy), self.f_small, DIM,
                              maxw=W - 48)
                    yy += 26
            except OSError:
                self.text("dettagli al prossimo avvio del desktop"
                          if self.lang == "it" else
                          "details at the next desktop launch",
                          (24, yy), self.f_small, FAINT)
            self.footer([("A", self.t("change")), ("B", self.t("back"))])
        elif top == "clock":
            it = (self.lang == "it")
            layout = CLOCK_LAYOUTS[self.cfg.get("clock_layout", 0)
                                   % len(CLOCK_LAYOUTS)]
            self.header(self.t("t_clock"), layout.upper(), icon="clock")
            self.clock_backdrop()
            lt = time.localtime()
            wd = (["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
                  if it else
                  ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
                  )[lt.tm_wday]
            date_s = "%s %02d/%02d/%04d" % (wd, lt.tm_mday, lt.tm_mon,
                                            lt.tm_year)
            blink = int(time.time() * 2) % 2 == 0
            sep = ":" if blink else " "
            if layout == "classic":
                self.npanel(30, 90, W - 60, 220, border=self.accent,
                            fill=INK, cut=22)
                for cx2, cy2, dx, dy in ((38, 98, 1, 1), (W - 38, 98,
                                         -1, 1), (38, 302, 1, -1),
                                         (W - 38, 302, -1, -1)):
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2 + 22 * dx, cy2), 3)
                    pygame.draw.line(self.surface, self.accent,
                                     (cx2, cy2), (cx2, cy2 + 22 * dy), 3)
                hm = "%02d%s%02d%s%02d" % (lt.tm_hour, sep, lt.tm_min,
                                           sep, lt.tm_sec)
                img = self.f_big.render(hm, True, FG)
                sc_f = min(2.6, (W - 120) / max(1, img.get_width()))
                big = pygame.transform.smoothscale(
                    img, (int(img.get_width() * sc_f),
                          int(img.get_height() * sc_f)))
                self.surface.blit(big, ((W - big.get_width()) // 2, 148))
                dimg = self.f_med.render(date_s, True, DIM)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         250))
            elif layout == "minimal":
                hm = "%02d%s%02d" % (lt.tm_hour, sep, lt.tm_min)
                img = self.f_big.render(hm, True, self.accent)
                sc_f = min(3.2, (W - 60) / max(1, img.get_width()))
                big = pygame.transform.smoothscale(
                    img, (int(img.get_width() * sc_f),
                          int(img.get_height() * sc_f)))
                self.surface.blit(big, ((W - big.get_width()) // 2, 150))
                pygame.draw.line(self.surface, LINE, (W // 2 - 60,
                                 260), (W // 2 + 60, 260), 1)
                dimg = self.f_small.render(date_s, True, FAINT)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         272))
            elif layout == "segmented":
                digs = "%02d%02d%02d" % (lt.tm_hour, lt.tm_min,
                                         lt.tm_sec)
                cw2, ch2, gap = 62, 84, 8
                total = cw2 * 6 + gap * 7 + 40
                x0 = (W - total) // 2
                x = x0
                for gi, dch in enumerate(digs):
                    if gi in (2, 4):
                        x += 20
                    x += gap
                    self.npanel(x, 130, cw2, ch2, border=self.accent,
                                fill=sel_tint(self.accent), cut=8)
                    dimg = self.f_big.render(dch, True, FG)
                    self.surface.blit(
                        dimg, (x + (cw2 - dimg.get_width()) // 2,
                              130 + (ch2 - dimg.get_height()) // 2))
                    x += cw2
                dimg = self.f_med.render(date_s, True, DIM)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         240))
            elif layout == "analog":
                cx2, cy2, r = W // 2, 195, 118
                pygame.draw.circle(self.surface, INK, (cx2, cy2), r)
                pygame.draw.circle(self.surface, self.accent,
                                   (cx2, cy2), r, 3)
                pygame.draw.circle(self.surface, LINE, (cx2, cy2),
                                   r - 12, 1)
                roman = {0: "XII", 3: "III", 6: "VI", 9: "IX"}
                for k in range(12):
                    ang = k * math.pi / 6 - math.pi / 2
                    if k in roman:
                        rimg = self.f_small.render(roman[k], True,
                                                   self.accent)
                        rx = cx2 + int((r - 30) * math.cos(ang))
                        ry = cy2 + int((r - 30) * math.sin(ang))
                        self.surface.blit(rimg, (rx - rimg.get_width() //
                                                 2, ry - rimg.get_height()
                                                 // 2))
                    else:
                        x1p = cx2 + int((r - 8) * math.cos(ang))
                        y1p = cy2 + int((r - 8) * math.sin(ang))
                        x2p = cx2 + int((r - 16) * math.cos(ang))
                        y2p = cy2 + int((r - 16) * math.sin(ang))
                        pygame.draw.line(self.surface, DIM, (x1p, y1p),
                                         (x2p, y2p), 2)
                for k in range(60):
                    if k % 5:
                        ang = k * math.pi / 30 - math.pi / 2
                        x1p = cx2 + int((r - 12) * math.cos(ang))
                        y1p = cy2 + int((r - 12) * math.sin(ang))
                        self.surface.set_at((x1p, y1p), LINE)
                # sotto-quadrante secondi, verso il basso
                sdx, sdy, sdr = cx2, cy2 + 52, 26
                pygame.draw.circle(self.surface, (0, 0, 0), (sdx, sdy),
                                   sdr)
                pygame.draw.circle(self.surface, DIM, (sdx, sdy), sdr, 1)
                for k in range(12):
                    a = k * math.pi / 6 - math.pi / 2
                    pygame.draw.line(self.surface, DIM,
                        (sdx + int((sdr - 3) * math.cos(a)),
                         sdy + int((sdr - 3) * math.sin(a))),
                        (sdx + int(sdr * math.cos(a)),
                         sdy + int(sdr * math.sin(a))), 1)
                sa2 = lt.tm_sec / 60.0 * 2 * math.pi - math.pi / 2
                self._clock_hand(sdx, sdy, sa2, sdr - 5, 3, 1, NO_R)
                pygame.draw.circle(self.surface, NO_R, (sdx, sdy), 2)
                hh = (lt.tm_hour % 12) + lt.tm_min / 60.0
                ha = hh / 12.0 * 2 * math.pi - math.pi / 2
                ma = lt.tm_min / 60.0 * 2 * math.pi - math.pi / 2
                self._clock_hand(cx2, cy2, ha, r * 0.5, 10, 4, FG,
                                 tail=10)
                self._clock_hand(cx2, cy2, ma, r * 0.75, 7, 3, FG,
                                 tail=14)
                pygame.draw.circle(self.surface, self.accent,
                                   (cx2, cy2), 6)
                pygame.draw.circle(self.surface, INK, (cx2, cy2), 2)
                dimg = self.f_med.render(date_s, True, DIM)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         332))
            elif layout == "skeleton":
                cx2, cy2, r = W // 2, 195, 118
                pygame.draw.circle(self.surface, self.accent,
                                   (cx2, cy2), r, 2)
                pygame.draw.circle(self.surface, LINE, (cx2, cy2),
                                   r - 8, 1)
                # ingranaggi a vista, decorativi, parte del quadrante
                for gx, gy, gr, teeth in ((cx2 - 30, cy2 - 20, 30, 8),
                                          (cx2 + 34, cy2 + 26, 20, 6)):
                    pts = []
                    for i in range(teeth * 2):
                        a = i * math.pi / teeth
                        rr = gr if i % 2 == 0 else gr * 0.8
                        pts.append((gx + rr * math.cos(a),
                                   gy + rr * math.sin(a)))
                    pygame.draw.polygon(self.surface, LINE, pts, 1)
                    pygame.draw.circle(self.surface, LINE, (gx, gy),
                                       int(gr * 0.25), 1)
                for k in range(12):
                    ang = k * math.pi / 6 - math.pi / 2
                    x1p = cx2 + int((r - 10) * math.cos(ang))
                    y1p = cy2 + int((r - 10) * math.sin(ang))
                    pygame.draw.circle(self.surface, self.accent
                                       if k % 3 == 0 else DIM,
                                       (x1p, y1p), 3 if k % 3 == 0
                                       else 2)
                hh = (lt.tm_hour % 12) + lt.tm_min / 60.0
                ha = hh / 12.0 * 2 * math.pi - math.pi / 2
                ma = lt.tm_min / 60.0 * 2 * math.pi - math.pi / 2
                sa = lt.tm_sec / 60.0 * 2 * math.pi - math.pi / 2
                self._clock_hand(cx2, cy2, ha, r * 0.48, 4, 1, FG)
                self._clock_hand(cx2, cy2, ma, r * 0.74, 3, 1, FG)
                pygame.draw.line(self.surface, NO_R,
                                 (cx2 - int(14 * math.cos(sa)),
                                  cy2 - int(14 * math.sin(sa))),
                                 (cx2 + int(r * 0.8 * math.cos(sa)),
                                  cy2 + int(r * 0.8 * math.sin(sa))), 1)
                pygame.draw.circle(self.surface, self.accent,
                                   (cx2, cy2), 4, 1)
                dimg = self.f_med.render(date_s, True, DIM)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         332))
            else:                                   # pilot
                cx2, cy2, r = W // 2, 195, 118
                pygame.draw.circle(self.surface, INK, (cx2, cy2), r)
                pygame.draw.circle(self.surface, FG, (cx2, cy2), r, 4)
                tri = [(cx2, cy2 - r + 6), (cx2 - 12, cy2 - r + 26),
                      (cx2 + 12, cy2 - r + 26)]
                pygame.draw.polygon(self.surface, self.accent, tri)
                big_hrs = {3: "3", 6: "6", 9: "9"}
                for k in range(12):
                    ang = k * math.pi / 6 - math.pi / 2
                    if k == 0:
                        continue
                    if k in big_hrs:
                        nimg = self.f_med.render(big_hrs[k], True, FG)
                        nx2 = cx2 + int((r - 32) * math.cos(ang))
                        ny2 = cy2 + int((r - 32) * math.sin(ang))
                        self.surface.blit(nimg, (nx2 - nimg.get_width() //
                                                 2, ny2 - nimg.get_height()
                                                 // 2))
                    else:
                        x1p = cx2 + int((r - 10) * math.cos(ang))
                        y1p = cy2 + int((r - 10) * math.sin(ang))
                        x2p = cx2 + int((r - 22) * math.cos(ang))
                        y2p = cy2 + int((r - 22) * math.sin(ang))
                        pygame.draw.line(self.surface, FG, (x1p, y1p),
                                         (x2p, y2p), 4)
                hh = (lt.tm_hour % 12) + lt.tm_min / 60.0
                ha = hh / 12.0 * 2 * math.pi - math.pi / 2
                ma = lt.tm_min / 60.0 * 2 * math.pi - math.pi / 2
                sa = lt.tm_sec / 60.0 * 2 * math.pi - math.pi / 2
                self._clock_hand(cx2, cy2, ha, r * 0.48, 14, 6, FG)
                self._clock_hand(cx2, cy2, ma, r * 0.78, 10, 4,
                                 self.accent)
                pygame.draw.line(self.surface, NO_R, (cx2, cy2),
                                 (cx2 + int(r * 0.82 * math.cos(sa)),
                                  cy2 + int(r * 0.82 * math.sin(sa))), 2)
                pygame.draw.circle(self.surface, FG, (cx2, cy2), 7)
                pygame.draw.circle(self.surface, NO_R, (cx2, cy2), 3)
                dimg = self.f_med.render(date_s, True, DIM)
                self.surface.blit(dimg, ((W - dimg.get_width()) // 2,
                                         332))
            n_al = len([a for a in self.alarms() if a.get("enabled",
                                                           True)])
            if n_al:
                atxt = ("%d sveglie attive" % n_al if it else
                        "%d alarms active" % n_al) if n_al > 1 else \
                    ("1 sveglia attiva" if it else "1 alarm active")
                self.text(atxt, (18, H - 54), self.f_tiny, self.accent)
            self.footer([("Y", "layout"),
                         ("X", "data/ora" if it else "date/time"),
                         ("A", "sveglie" if it else "alarms"),
                         ("B", self.t("back"))])
        elif top == "alarmlist":
            it = (self.lang == "it")
            self.header("SVEGLIE" if it else "ALARMS", icon="clock")
            lst = self.alarms()
            y = 52
            if self.alarm_sel == 0:
                self.sel_frame(8, y, W - 16, 42)
            icons.draw(self.surface, "clock", 18, y + 9, 24,
                       self.accent)
            self.text("+ " + ("nuova sveglia" if it else "new alarm"),
                      (54, y + 10), self.f_med, self.accent)
            y += 48
            for j, a in enumerate(lst):
                sel = (j + 1 == self.alarm_sel)
                on = a.get("enabled", True)
                if sel:
                    self.sel_frame(8, y, W - 16, 46)
                self.switch(18, y + 12, on, w=40, h=20)
                ts = "%02d:%02d" % (a["h"], a["m"])
                self.text(ts, (72, y + 5), self.f_med,
                          FG if on else FAINT)
                lab = a.get("label") or ALARM_SOUNDS[
                    ALARM_SOUNDS.index(a.get("sound", "classic"))
                    if a.get("sound") in ALARM_SOUNDS else 0]
                self.text(lab, (160, y + 10), self.f_small,
                          DIM if on else FAINT, maxw=W - 200)
                y += 50
            if not lst:
                self.text("nessuna sveglia impostata" if it else
                          "no alarms set", (54, y + 14), self.f_small,
                          DIM)
            self.footer([("A", self.t("open")),
                         ("Y", "on/off"),
                         ("X", "elimina" if it else "delete"),
                         ("B", self.t("back"))])
        elif top == "alarmwhen":
            it = (self.lang == "it")
            self.header(self.aw_title or ("NUOVA SVEGLIA" if it else
                        "NEW ALARM"), icon="clock")
            labs = (["ORE", "MINUTI", "SUONO"] if it else
                    ["HOURS", "MINUTES", "SOUND"])
            for j in range(3):
                y = 60 + j * 56
                if j == self.aw_f:
                    self.sel_frame(8, y, W - 16, 48)
                self.text(labs[j], (24, y + 14), self.f_med,
                          FG if j == self.aw_f else DIM)
                vs = (ALARM_SOUNDS[self.aw[2]] if j == 2 else
                      "%02d" % self.aw[j])
                vw = self.f_med.size(vs)[0]
                self.text("◂", (W - vw - 74, y + 14), self.f_med,
                          self.accent if j == self.aw_f else FAINT)
                self.text(vs, (W - vw - 44, y + 14), self.f_med,
                          self.accent)
                self.text("▸", (W - 30, y + 14), self.f_med,
                          self.accent if j == self.aw_f else FAINT)
            self.footer([("SX/DX", self.t("change")),
                         ("Y", "etichetta" if it else "label"),
                         ("A", "salva" if it else "save"),
                         ("B", self.t("back"))])
        elif top == "alarmring":
            it = (self.lang == "it")
            self.surface.fill((14, 4, 4))
            a = self._alarm_ringing or {}
            pulse = int(time.time() * 3) % 2 == 0
            col = NO_R if pulse else (255, 140, 140)
            pygame.draw.circle(self.surface, col, (W // 2, 150), 60, 6)
            icons.draw(self.surface, "clock", W // 2 - 22, 128, 44, col)
            ts = "%02d:%02d" % (a.get("h", 0), a.get("m", 0))
            img = self.f_big.render(ts, True, FG)
            self.surface.blit(img, ((W - img.get_width()) // 2, 230))
            lab = a.get("label") or ("SVEGLIA" if it else "ALARM")
            limg = self.f_med.render(lab, True, DIM)
            self.surface.blit(limg, ((W - limg.get_width()) // 2, 290))
            self.footer([("A/B", "ferma" if it else "dismiss")])
        elif top == "weather":
            it = (self.lang == "it")
            self.header(self.t("t_wx"), icon="w_partly")
            self.content_panel(46, H - 40)
            cities = self.cfg.get("weather_cities") or []
            y = 50
            if self.wx_sel == 0:
                self.sel_frame(8, y, W - 16, 42)
            icons.draw(self.surface, "w_sunny", 18, y + 9, 24,
                       self.accent)
            self.text(self.t("wx_add"), (54, y + 10), self.f_med,
                      self.accent)
            y += 48
            for j, city in enumerate(cities):
                sel = (j + 1 == self.wx_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 52)
                data = self.wx_data.get(city["name"])
                err = self.wx_errors.get(city["name"])
                if data and data.get("current"):
                    cur = data["current"]
                    ic, lab_it, lab_en = self.wx_icon_for(
                        cur.get("weather_code"))
                    icons.draw(self.surface, ic, 18, y + 12, 28,
                               self.accent)
                    self.text(city["name"], (56, y + 6), self.f_med,
                              FG if sel else DIM, maxw=W - 220)
                    lab = lab_it if it else lab_en
                    self.text(lab, (56, y + 29), self.f_tiny, FAINT)
                    tt = "%.0f°" % cur.get("temperature_2m", 0)
                    tw = self.f_big.size(tt)[0]
                    self.text(tt, (W - 26 - tw, y + 8), self.f_big,
                              self.accent)
                elif err:
                    icons.draw(self.surface, "w_fog", 18, y + 12, 28,
                               FAINT)
                    self.text(city["name"], (56, y + 6), self.f_med,
                              FG if sel else DIM, maxw=W - 220)
                    self.text(self.t("wx_err"), (56, y + 29),
                              self.f_tiny, NO_R)
                else:
                    self.text(city["name"], (56, y + 15), self.f_med,
                              FG if sel else DIM, maxw=W - 220)
                y += 58
            if not cities:
                self.text(self.t("wx_none"), (54, y + 10),
                          self.f_small, DIM)
            self.footer([("A", self.t("open")),
                         ("X", "rimuovi" if it else "remove"),
                         ("R1", "aggiorna" if it else "refresh"),
                         ("B", self.t("back"))])
        elif top == "weatherpick":
            it = (self.lang == "it")
            self.header(self.t("wx_pick"), icon="w_partly")
            y = 52
            for j, res in enumerate(self.wx_pick_results):
                sel = (j == self.wx_pick_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 46)
                self.text(res["name"], (24, y + 6), self.f_med,
                          FG if sel else DIM)
                sub = ", ".join(p for p in (res.get("admin1"),
                                            res.get("country")) if p)
                self.text(sub, (24, y + 27), self.f_tiny, FAINT,
                          maxw=W - 48)
                y += 50
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "weatherdetail":
            it = (self.lang == "it")
            city = self.wx_detail_city or {"name": "?"}
            self.header(city["name"][:22], icon="w_partly")
            data = self.wx_data.get(city["name"])
            if not data:
                self.text(self.t("wx_err"), (30, 140), self.f_med,
                          NO_R)
                self.footer([("R1", "aggiorna" if it else "refresh"),
                            ("B", self.t("back"))])
            else:
                cur = data.get("current") or {}
                ic, lab_it, lab_en = self.wx_icon_for(
                    cur.get("weather_code"))
                self.npanel(20, 48, W - 40, 78, border=self.accent,
                            fill=INK, cut=14)
                icons.draw(self.surface, ic, 30, 60, 54, self.accent)
                tt = "%.0f°" % cur.get("temperature_2m", 0)
                self.text(tt, (100, 58), self.f_big, FG)
                self.text(lab_it if it else lab_en,
                          (100, 96), self.f_small, DIM)
                grid = self.wx_grid(data)
                gx0, gy0 = 20, 148
                colw = (W - 40 - 60) // max(1, min(7, len(grid)))
                labs = (["Mat", "Pom", "Sera"] if it else
                        ["Morn", "Aft", "Eve"])
                for r_, lab in enumerate(labs):
                    self.text(lab, (gx0, gy0 + 26 + r_ * 42),
                              self.f_tiny, FAINT)
                for c_, (day, segs) in enumerate(grid[:7]):
                    x = gx0 + 56 + c_ * colw
                    wd = dtmod.date(*[int(p) for p in day.split("-")]
                                    ).strftime("%a")[:3]
                    self.text(wd, (x, gy0), self.f_tiny, self.accent)
                    for r_, seg in enumerate(segs):
                        yy = gy0 + 20 + r_ * 42
                        if seg and seg[1] is not None:
                            sic, _li, _le = self.wx_icon_for(seg[1])
                            icons.draw(self.surface, sic, x, yy, 20,
                                      DIM)
                            tstr = "%.0f°" % seg[0]
                            self.text(tstr, (x, yy + 20), self.f_tiny,
                                      FAINT)
                self.footer([("R1", "aggiorna" if it else "refresh"),
                            ("B", self.t("back"))])
        elif top == "depsmissing":
            it = (self.lang == "it")
            self.surface.fill(BG)
            self.npanel(20, 20, W - 40, H - 40, border=NO_R, fill=INK,
                        cut=20)
            icons.draw(self.surface, "shield", 36, 36, 30, NO_R)
            self.text(self.t("deps_title"), (78, 40), self.f_big, NO_R)
            icons.draw(self.surface, self.deps_feature_icon, 36, 92, 26,
                       self.accent)
            self.text(self.deps_feature_title, (70, 96), self.f_med, FG)
            body = ('"%s" %s:' % (self.deps_feature_title,
                                  self.t("deps_body")))
            y = 132
            for ln in self.note_wrap(body, W - 76, self.f_small, 3):
                self.text(ln, (36, y), self.f_small, DIM)
                y += 20
            y += 6
            for dep in self.deps_missing_list:
                self.text("•", (36, y), self.f_small, NO_R)
                for ln in self.note_wrap(dep, W - 96, self.f_small, 2):
                    self.text(ln, (52, y), self.f_small, FG)
                    y += 19
                y += 3
            y += 10
            for ln in self.note_wrap(self.t("deps_ask"), W - 76,
                                     self.f_med, 2):
                self.text(ln, (36, y), self.f_med, FG)
                y += 24
            self.footer([("A", "SI" if it else "YES"),
                         ("B", "NO")])
        elif top == "clocksettings":
            self.header("CLOCK", icon="clock")
            v = self.clock_v
            labs = (["ANNO", "MESE", "GIORNO", "ORE", "MINUTI", "FUSO"]
                    if self.lang == "it" else
                    ["YEAR", "MONTH", "DAY", "HOURS", "MINUTES", "ZONE"])
            for j in range(6):
                y = 56 + j * 52
                if j == self.clock_f:
                    self.sel_frame(8, y, W - 16, 46)
                self.text(labs[j], (24, y + 12), self.f_med,
                          FG if j == self.clock_f else DIM)
                vs = TZS[v[5]] if j == 5 else "%02d" % v[j]
                vw = self.f_med.size(vs)[0]
                self.text("◂", (W - vw - 74, y + 12), self.f_med,
                          self.accent if j == self.clock_f else FAINT)
                self.text(vs, (W - vw - 44, y + 12), self.f_med,
                          self.accent)
                self.text("▸", (W - 30, y + 12), self.f_med,
                          self.accent if j == self.clock_f else FAINT)
            self.footer([("SX/DX", self.t("change")),
                         ("A", self.t("clock_set")),
                         ("B", self.t("back"))])
        elif top == "calc":
            self.header(self.t("t_calc"), icon="calc")
            self.npanel(10, 52, W - 20, 54, border=self.accent, fill=INK)
            disp = self.calc_expr or "0"
            dw = self.f_big.size(disp)[0]
            self.text(disp, (W - 26 - dw, 64), self.f_big, FG)
            R, C = len(CALC_KEYS), len(CALC_KEYS[0])
            bw, bh = (W - 24) // C, 56
            for r in range(R):
                for c in range(C):
                    k = CALC_KEYS[r][c]
                    x = 12 + c * bw
                    y = 118 + r * (bh + 6)
                    sel = (r * C + c) == self.calc_sel
                    self.npanel(x, y, bw - 6, bh,
                                border=(self.accent if sel else LINE),
                                fill=(sel_tint(self.accent) if sel
                                      else INK), cut=7)
                    col = self.accent if k in ("=", "C", "<") else                         (FG if sel else DIM)
                    kw = self.f_med.size(k)[0]
                    self.text(k, (x + (bw - 6 - kw) // 2, y + 16),
                              self.f_med, col)
            self.footer([("A", "premi" if self.lang == "it" else "press"),
                         ("X", "⌫"), ("Y", "="), ("B", self.t("back"))])
        elif top == "manual":
            self.header(self.t("i_man"), icon="book")
            y = 54
            self.content_panel(46, 46 + len(MANUAL) * 42 + 8)
            for j, (key, ic) in enumerate(MANUAL):
                if j == self.man_sel:
                    self.sel_frame(8, y, W - 16, 40)
                icons.draw(self.surface, ic, 18, y + 8, 24,
                           self.accent if j == self.man_sel else FAINT)
                title = self.manual_lines(j)[0][2]
                self.text("%d. %s" % (j + 1, title), (54, y + 9),
                          self.f_med, FG if j == self.man_sel else DIM)
                y += 42
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "mappdetail":
            app = self.mapp_cur
            self.header(app["name"][:24], icon="window")
            self.npanel(8, 48, W - 16, 82, border=LINE, fill=INK)
            self.surface.blit(self.mapp_icon(app, 56), (20, 60))
            self.text(app["name"], (92, 54), self.f_med, FG,
                      maxw=W - 120)
            self.text("%s  ·  %s: %s" %
                      (app["sd"], self.t("size"),
                       human(self.mapp_size or 0)),
                      (92, 78), self.f_small, DIM)
            self.text(app["dir"], (92, 100), self.f_tiny, FAINT,
                      maxw=W - 120)
            gov = (self.cfg.get("mapp_gov") or {}).get(app["name"],
                                                       "default")
            acts = self.detail_actions()
            per = 6
            first = max(0, min(self.det_sel - per // 2,
                               len(acts) - per))
            y = 140
            for j in range(max(0, first), min(first + per, len(acts))):
                k, ic, lab = acts[j]
                sel = (j == self.det_sel)
                bad = k in ("remove",)
                good = k == "protect" and self.is_user_protected(
                    app["name"])
                if sel:
                    self.sel_frame(8, y, W - 16, 42)
                icons.draw(self.surface, ic, 18, y + 9, 22,
                           NO_R if bad else
                           OK_G if good else
                           (self.accent if sel else FAINT))
                self.text(lab, (52, y + 10), self.f_med,
                          NO_R if bad else
                          OK_G if good else
                          (FG if sel else DIM), maxw=W - 170)
                if k == "gov":
                    vw = self.f_small.size(gov)[0]
                    self.npanel(W - vw - 34, y + 7, vw + 16, 26,
                                border=LINE, fill=INK, cut=6)
                    self.text(gov, (W - vw - 26, y + 12), self.f_small,
                              self.accent)
                if k == "glyphp":
                    idx = (self.cfg.get("mapp_glyph") or {}
                           ).get(app["name"])
                    if idx is not None:
                        self.text("#%d" % (idx + 1),
                                  (W - 56, y + 12), self.f_small,
                                  self.accent)
                y += 42
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "cal":
            it = (self.lang == "it")
            mesi, gg, gg_full = self.cal_names()
            y0, m0, d0 = self.cal_cur
            lt = time.localtime()
            today = (lt.tm_year, lt.tm_mon, lt.tm_mday)
            v = self.cal_view
            if v == "month":
                self.header("%s %d" % (mesi[m0 - 1], y0),
                            icon="clock")
                cw2 = (W - 22) // 7
                for c in range(7):
                    self.text(gg[c], (14 + c * cw2 + (cw2 - 28) // 2,
                                      46), self.f_tiny, FAINT)
                fw, nd = calmod.monthrange(y0, m0)
                ch = 56
                rows = -(-(fw + nd) // 7)          # arrotonda per eccesso
                gx0, gy0 = 12, 66
                gw2, gh2 = cw2 * 7, ch * rows
                # griglia vera: una linea per ogni bordo di cella, come
                # una vera tabella da calendario -- non solo numeri
                # fluttuanti nel vuoto
                for r_ in range(rows + 1):
                    pygame.draw.line(self.surface, LINE,
                                     (gx0, gy0 + r_ * ch),
                                     (gx0 + gw2, gy0 + r_ * ch), 1)
                for c_ in range(8):
                    pygame.draw.line(self.surface, LINE,
                                     (gx0 + c_ * cw2, gy0),
                                     (gx0 + c_ * cw2, gy0 + gh2), 1)
                pygame.draw.rect(self.surface, self.accent,
                                 (gx0, gy0, gw2, gh2), 2)
                for d in range(1, nd + 1):
                    idx = fw + d - 1
                    r_, c_ = divmod(idx, 7)
                    x = 12 + c_ * cw2
                    yy = 66 + r_ * ch
                    cell = (y0, m0, d)
                    if cell == today:
                        pygame.draw.rect(self.surface,
                                         sel_tint(self.accent),
                                         (x + 1, yy + 1, cw2 - 2,
                                          ch - 2))
                        pygame.draw.rect(self.surface, self.accent,
                                         (x + 1, yy + 1, cw2 - 2,
                                          ch - 2), 2)
                    if d == d0:
                        self.sel_frame(x - 2, yy - 2, cw2, ch)
                    self.text(str(d), (x + 6, yy + 3),
                              self.f_small,
                              self.accent if cell == today else
                              (FG if d == d0 else DIM))
                    evd = self.ev_on(y0, m0, d)
                    for k2, e in enumerate(evd[:3]):
                        pygame.draw.circle(
                            self.surface, self.imp_color(e["imp"]),
                            (x + 10 + k2 * 12, yy + ch - 13), 4)
                foot_a = "giorno" if it else "day"
            elif v == "week":
                base = dtmod.date(y0, m0, d0)
                mon = base - dtmod.timedelta(days=base.weekday())
                self.header(("SETTIMANA DEL %02d/%02d" if it else
                             "WEEK OF %02d/%02d")
                            % (mon.day, mon.month), icon="clock")
                for k2 in range(7):
                    dd = mon + dtmod.timedelta(days=k2)
                    yy = 50 + k2 * 52
                    cell = (dd.year, dd.month, dd.day)
                    if cell == today:
                        pygame.draw.rect(self.surface,
                                         sel_tint(self.accent),
                                         (8, yy, W - 16, 48))
                    if (dd.year, dd.month, dd.day) == (y0, m0, d0):
                        self.sel_frame(8, yy, W - 16, 48)
                    self.text("%s %d, %s" % (gg_full[k2], dd.day,
                              mesi[dd.month - 1].capitalize()),
                              (20, yy + 6), self.f_med,
                              self.accent if cell == today else FG,
                              maxw=280)
                    evd = self.ev_on(dd.year, dd.month, dd.day)
                    if evd:
                        e = sorted(evd, key=lambda a: (a["h"],
                                                       a["mi"]))[0]
                        txt = "%02d:%02d %s" % (e["h"], e["mi"],
                                                e["t"])
                        if len(evd) > 1:
                            txt += "  +%d" % (len(evd) - 1)
                        self.text(txt, (150, yy + 14), self.f_small,
                                  DIM, maxw=W - 260)
                        for k3, e2 in enumerate(evd[:4]):
                            pygame.draw.circle(
                                self.surface,
                                self.imp_color(e2["imp"]),
                                (W - 90 + k3 * 14, yy + 24), 4)
                foot_a = "giorno" if it else "day"
            else:
                dd = dtmod.date(y0, m0, d0)
                self.header("%s %02d %s %d" %
                            (gg[dd.weekday()], d0, mesi[m0 - 1], y0),
                            icon="clock")
                evd = sorted(self.ev_on(y0, m0, d0),
                             key=lambda a: (a["h"], a["mi"]))
                y = 54
                if self.ev_sel == 0:
                    self.sel_frame(8, y, W - 16, 40)
                icons.draw(self.surface, "clock", 18, y + 8, 24,
                           self.accent)
                self.text("+ " + ("nuovo evento qui" if it
                                  else "new event here"),
                          (54, y + 9), self.f_med, self.accent)
                y += 46
                for j2, e in enumerate(evd):
                    if self.ev_sel == j2 + 1:
                        self.sel_frame(8, y, W - 16, 44)
                    pygame.draw.rect(self.surface,
                                     self.imp_color(e["imp"]),
                                     (14, y + 8, 5, 28))
                    self.text("%02d:%02d" % (e["h"], e["mi"]),
                              (30, y + 12), self.f_med, DIM)
                    self.text(e["t"], (110, y + 12), self.f_med,
                              FG if self.ev_sel == j2 + 1 else DIM,
                              maxw=W - 240)
                    lb = self.imp_label(e["imp"])
                    self.text(lb, (W - 26 - self.f_tiny.size(lb)[0],
                                   y + 16), self.f_tiny,
                              self.imp_color(e["imp"]))
                    y += 46
                if not evd:
                    self.text("giornata libera" if it
                              else "free day", (54, y + 10),
                              self.f_small, DIM)
                foot_a = ("nuovo/modifica" if it else "new/edit")
            self.footer([("A", foot_a),
                         ("Y", "vista" if it else "view"),
                         ("L1/R1", "±"),
                         ("X", "elim." if it else "del."),
                         ("B", self.t("back"))])
        elif top == "calwhen":
            it = (self.lang == "it")
            self.header(self.cw_title[:24], icon="clock")
            labs = (["ANNO", "MESE", "GIORNO", "ORE", "MINUTI",
                     "PRIORITA'"] if it else
                    ["YEAR", "MONTH", "DAY", "HOURS", "MINUTES",
                     "PRIORITY"])
            for j in range(6):
                y = 56 + j * 52
                if j == self.cw_f:
                    self.sel_frame(8, y, W - 16, 46)
                self.text(labs[j], (24, y + 12), self.f_med,
                          FG if j == self.cw_f else DIM)
                vs = (self.imp_label(self.cw[5]) if j == 5
                      else "%02d" % self.cw[j])
                col = (self.imp_color(self.cw[5]) if j == 5
                       else self.accent)
                vw = self.f_med.size(vs)[0]
                self.text("◂", (W - vw - 74, y + 12), self.f_med,
                          self.accent if j == self.cw_f else FAINT)
                self.text(vs, (W - vw - 44, y + 12), self.f_med, col)
                self.text("▸", (W - 30, y + 12), self.f_med,
                          self.accent if j == self.cw_f else FAINT)
            self.footer([("SX/DX", self.t("change")),
                         ("A", "salva" if it else "save"),
                         ("B", self.t("back"))])
        elif top == "notes":
            it = (self.lang == "it")
            self.header(self.t("t_note"), icon="text")
            rects = self.note_layout()
            sel_r = rects[min(self.note_sel, len(rects) - 1)]
            off = 0
            if sel_r.bottom > H - 50:
                off = sel_r.bottom - (H - 50)
            PAL = [(242, 208, 96), (150, 214, 230),
                   (168, 226, 152), (238, 170, 186)]
            r0 = rects[0].move(0, -off)
            pygame.draw.rect(self.surface, INK, r0)
            for k2 in range(0, r0.w, 10):
                pygame.draw.line(self.surface, self.accent,
                                 (r0.x + k2, r0.y),
                                 (r0.x + min(k2 + 5, r0.w), r0.y), 2)
                pygame.draw.line(self.surface, self.accent,
                                 (r0.x + k2, r0.bottom - 1),
                                 (r0.x + min(k2 + 5, r0.w),
                                  r0.bottom - 1), 2)
            self.text("+ " + ("nuova" if it else "new"),
                      (r0.x + 16, r0.y + 24), self.f_med,
                      self.accent)
            if self.note_sel == 0:
                self.sel_frame(r0.x - 3, r0.y - 3, r0.w + 6,
                               r0.h + 6)
            for j2, nt in enumerate(self.notes):
                r_ = rects[j2 + 1].move(0, -off)
                if r_.bottom < 40 or r_.y > H - 44:
                    continue
                col = PAL[hash(os.path.basename(nt["p"])) % 4]
                pygame.draw.rect(self.surface, col, r_)
                dk = tuple(max(0, c2 - 60) for c2 in col)
                pygame.draw.polygon(self.surface, dk,
                                    [(r_.right - 16, r_.bottom),
                                     (r_.right, r_.bottom - 16),
                                     (r_.right, r_.bottom)])
                lines = self.note_wrap(nt["txt"], r_.w - 20,
                                       self.f_tiny,
                                       (r_.h - 34) // 17)
                for k3, ln in enumerate(lines):
                    self.text(ln, (r_.x + 10, r_.y + 8 + k3 * 17),
                              self.f_tiny, INK)
                self.text(time.strftime("%d/%m",
                                        time.localtime(nt["mt"])),
                          (r_.x + 10, r_.bottom - 18), self.f_tiny,
                          dk)
                if nt["pin"]:
                    pygame.draw.circle(self.surface, NO_R,
                                       (r_.right - 12, r_.y + 12), 6)
                    pygame.draw.circle(self.surface, (120, 20, 30),
                                       (r_.right - 12, r_.y + 12), 6,
                                       2)
                if self.note_sel == j2 + 1:
                    self.sel_frame(r_.x - 3, r_.y - 3, r_.w + 6,
                                   r_.h + 6)
            if not self.notes:
                self.text("bacheca vuota: scrivi la prima." if it
                          else "empty board: jot the first.",
                          (24, 140), self.f_small, DIM)
            self.footer([("A", "nuova/apri" if it else "new/open"),
                         ("Y", "pin"),
                         ("X", "elimina" if it else "delete"),
                         ("B", self.t("back"))])
        elif top == "rss":
            it = (self.lang == "it")
            self.header(self.t("t_rss"), icon="globe",
                        right=("%d" % len(self.rss_items))
                        if self.rss_items else "")
            self.content_panel(46, H - 40)
            per = 6
            first = max(0, min(self.rss_sel - per // 2,
                               len(self.rss_items) - per))
            y = 50
            if not self.rss_enabled_feeds():
                self.npanel(30, 140, W - 60, 110, border=LINE,
                            fill=INK)
                self.text(self.t("rss_empty"), (54, 168),
                          self.f_med, DIM)
                self.text("Y: " + ("scegli i feed" if it
                                   else "pick feeds"),
                          (54, 196), self.f_small, FAINT)
            elif not self.rss_items:
                self.text(self.t("rss_none"), (30, 140),
                          self.f_med, DIM, maxw=W - 60)
            for j in range(first, min(first + per,
                                      len(self.rss_items))):
                it_ = self.rss_items[j]
                if j == self.rss_sel:
                    self.sel_frame(8, y, W - 16, 62)
                icons.draw(self.surface, it_["icon"], 18, y + 8, 24,
                           it_["col"])
                self.text(it_["site"], (54, y + 4), self.f_small,
                          it_["col"])
                ago = self.rss_ago(it_["ts"])
                if ago:
                    self.text(ago, (W - 26 - self.f_tiny.size(ago)[0],
                                    y + 7), self.f_tiny, FAINT)
                self.text(it_["title"], (54, y + 24), self.f_med,
                          FG if j == self.rss_sel else DIM,
                          maxw=W - 80)
                y += 66
            if self.rss_errors:
                ex = "%d feed in errore" % len(self.rss_errors) if it \
                    else "%d feeds errored" % len(self.rss_errors)
                self.text(ex, (14, H - 48), self.f_tiny, NO_R)
            self.footer([("A", self.t("open")), ("Y", "feed"),
                         ("R1", "aggiorna" if it else "refresh"),
                         ("B", self.t("back"))])
        elif top == "rsssel":
            it = (self.lang == "it")
            self.header(self.t("t_rss"), icon="globe")
            rows = self.rss_sel_rows()
            per = 8
            first = max(0, min(self.rss_sel_sel - per // 2,
                               len(rows) - per))
            y = 50
            for j in range(max(0, first), min(first + per, len(rows))):
                kind = rows[j][0]
                if kind == "hdr":
                    pygame.draw.line(self.surface, LINE,
                                     (10, y + 20), (W - 10, y + 20), 1)
                    pygame.draw.rect(self.surface, self.accent,
                                     (10, y + 12, 4, 12))
                    self.text(rows[j][1], (22, y + 8), self.f_small,
                              self.accent)
                    y += 32
                    continue
                name, url, lang, cat = rows[j][1]
                icon, col = RSS_CATS.get(cat, RSS_CATS["general"])
                on = self.rss_is_enabled(name)
                broken = name in (self.rss_errors or {})
                sel = (j == self.rss_sel_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 40,
                                   color=NO_R if broken else None)
                self.npanel(16, y + 8, 22, 22,
                            border=(OK_G if on else LINE),
                            fill=(OK_G if on else INK), cut=5)
                icons.draw(self.surface, icon, 52, y + 8, 22,
                           NO_R if broken else col)
                self.text(name, (84, y + 9), self.f_med,
                          NO_R if broken else (col if on else FAINT),
                          maxw=W - 190)
                if broken:
                    err = self.rss_errors.get(name, "")[:40]
                    self.text(("errore: " if it else "error: ") + err,
                              (84, y + 26), self.f_tiny, NO_R,
                              maxw=W - 190)
                else:
                    ctag = self.t("cat_" + cat)
                    self.text(ctag, (W - 26 - self.f_tiny.size(ctag)[0],
                                     y + 13), self.f_tiny, FAINT)
                y += 42
            self.text(self.t("rss_sel_hint") + " " +
                      self.rss_custom_path(),
                      (14, H - 30), self.f_tiny, FAINT, maxw=W - 28)
            self.footer([("A/X", "on/off"),
                         ("Y", "rimuovi" if it else "remove"),
                         ("B", self.t("back"))])
        elif top == "glyphpick":
            it = (self.lang == "it")
            app = self.mapp_cur
            self.header("CHANGE GLYPH", icon="image")
            cur, bak, _g = self.gp_paths()
            self.npanel(8, 46, W - 16, 56, border=LINE, fill=INK)
            pygame.draw.rect(self.surface, (24, 26, 33),
                             (20, 54, 40, 40))
            try:
                og = pygame.transform.scale(
                    pygame.image.load(cur).convert_alpha(), (36, 36))
                self.surface.blit(og, (22, 56))
            except (OSError, pygame.error):
                self.text("—", (34, 62), self.f_med, FAINT)
            self.text(app["name"], (74, 54), self.f_med, FG,
                      maxw=W - 260)
            self.text(("originale salvato" if it else "original saved")
                      if os.path.exists(bak) else
                      ("X: ripristina" if it else "X: restore")
                      if False else "", (74, 78), self.f_tiny, OK_G)
            if os.path.exists(bak):
                tag = "X: " + ("ripristina orig." if it
                               else "restore orig.")
                self.text(tag, (W - 30 - self.f_tiny.size(tag)[0], 78),
                          self.f_tiny, self.accent)
            C = 8
            cell = (W - 24) // C
            y0 = 112
            for j, p in enumerate(self.gp_list):
                r_, c_ = divmod(j, C)
                x = 12 + c_ * cell
                y = y0 + r_ * (cell + 6)
                if y > H - 70:
                    break
                sel = (j == self.gp_sel)
                self.npanel(x, y, cell - 6, cell,
                            border=(self.accent if sel else LINE),
                            fill=(sel_tint(self.accent) if sel
                                  else INK), cut=6)
                try:
                    key = (p, "gp")
                    if key not in self.mapp_icons:
                        self.mapp_icons[key] = pygame.transform.scale(
                            pygame.image.load(p).convert_alpha(),
                            (44, 44))
                    self.surface.blit(self.mapp_icons[key],
                                      (x + (cell - 50) // 2, y + 8))
                except (OSError, pygame.error):
                    pass
            fold = self.gp_dirs()[0]
            self.text(("aggiungi i tuoi PNG in: " if it
                       else "drop your PNGs in: ") + fold,
                      (14, H - 52), self.f_tiny, FAINT, maxw=W - 28)
            self.footer([("A", "applica" if it else "apply"),
                         ("X", "ripristina" if it else "restore"),
                         ("B", self.t("back"))])
        elif top == "confirm":
            self.header(self.t("removeapp"), icon="trash")
            self.npanel(50, 160, W - 100, 130, border=NO_R, fill=INK)
            self.text(self.confirm[0] if self.confirm else "?",
                      (74, 184), self.f_big, NO_R, maxw=W - 148)
            self.text(self.t("confirm_rm"), (74, 232), self.f_small, DIM,
                      maxw=W - 148)
            self.footer([("A", "si'" if self.lang == "it" else "yes"),
                         ("B", "no")])
        elif top == "wifimgr":
            it = (self.lang == "it")
            self.header("WIFI", icon="wifi")
            st = self.wm_status()
            ron = self.wm_radio_on()
            self.npanel(8, 44, W - 16, 46, border=LINE, fill=INK)
            self.switch(22, 52, ron)
            cur = st.get("ssid") or ("non connesso" if it
                                     else "not connected")
            self.text(cur, (100, 48), self.f_med,
                      OK_G if st.get("ssid") else
                      (FG if ron else FAINT))
            ip = st.get("ip_address", "")
            online = bool(ip)
            led_col = OK_G if online else NO_R
            pygame.draw.circle(self.surface, led_col, (105, 75), 4)
            status_txt = ip if online else "OFFLINE"
            self.text(status_txt, (116, 71), self.f_tiny, led_col)
            sw = self.f_tiny.size(status_txt)[0]
            self.text("   ·   Y: on/off   ·   L1: info",
                      (116 + sw, 71), self.f_tiny, FAINT)
            y = 100
            per = 7
            first = max(0, min(self.wm_sel - per // 2,
                               len(self.wm_nets) - per))
            if not self.wm_nets:
                self.text("nessuna rete: R1 per cercare" if it
                          else "no networks: R1 to scan",
                          (40, 150), self.f_med, DIM)
            for j in range(first, min(first + per,
                                      len(self.wm_nets))):
                nt = self.wm_nets[j]
                if j == self.wm_sel:
                    self.sel_frame(8, y, W - 16, 46)
                bars = max(1, min(4, (nt["sig"] + 90) // 12))
                for b2 in range(4):
                    hh = 5 + b2 * 5
                    col = (self.accent if b2 < bars else LINE)
                    pygame.draw.rect(self.surface, col,
                                     (20 + b2 * 7, y + 34 - hh, 5, hh))
                self.text(nt["ssid"], (56, y + 5), self.f_med,
                          OK_G if nt["cur"] else
                          (FG if j == self.wm_sel else DIM),
                          maxw=W - 240)
                sub = []
                if nt["cur"]:
                    sub.append("connessa" if it else "connected")
                if nt["saved"]:
                    sub.append(("salvata" if it else "saved")
                               + ("" if nt["sig"] > -95 else
                                  (" · fuori portata" if it
                                   else " · out of range")))
                sub.append("WPA" if nt["sec"] else "aperta"
                           if it else "open")
                self.text("  ·  ".join(sub), (56, y + 27),
                          self.f_tiny, FAINT)
                y += 48
            self.footer([("A", "connetti" if it else "join"),
                         ("X", "dimentica" if it else "forget"),
                         ("Y", "radio on/off"), ("L1", "info"),
                         ("R1", "scan"), ("B", self.t("back"))])
        elif top == "btmgr":
            it = (self.lang == "it")
            self.header("BLUETOOTH", icon="bt")
            bon = self.bt_powered()
            self.npanel(8, 44, W - 16, 46, border=LINE, fill=INK)
            self.switch(22, 52, bon)
            self.text(("BLUETOOTH ACCESO" if it else "BLUETOOTH ON")
                      if bon else ("BLUETOOTH SPENTO" if it
                                   else "BLUETOOTH OFF"),
                      (100, 48), self.f_med, OK_G if bon else FAINT)
            self.text("SEL: on/off   ·   L1: info",
                      (100, 71), self.f_tiny, FAINT)
            y = 100
            per = 8
            first = max(0, min(self.bt_sel - per // 2,
                               len(self.bt_devs) - per))
            if not self.bt_devs:
                self.text("nessun dispositivo: R1 per cercare (8s)"
                          if it else "no devices: R1 to scan (8s)",
                          (40, 150), self.f_med, DIM)
            for j in range(first, min(first + per,
                                      len(self.bt_devs))):
                d = self.bt_devs[j]
                if j == self.bt_sel:
                    self.sel_frame(8, y, W - 16, 44)
                icons.draw(self.surface, "bt", 18, y + 10, 24,
                           OK_G if d.get("connected") else
                           (self.accent if d["paired"] else FAINT))
                self.text(d["name"], (52, y + 4), self.f_med,
                          FG if j == self.bt_sel else DIM,
                          maxw=W - 220)
                sub = d["mac"]
                if d.get("connected"):
                    sub += "  ·  " + ("connesso" if it else "connected")
                elif d["paired"]:
                    sub += "  ·  " + ("accoppiato" if it else "paired")
                self.text(sub, (52, y + 26), self.f_tiny,
                          OK_G if d.get("connected") else FAINT)
                y += 46
            self.footer([("A", "pair+connetti" if it
                          else "pair+connect"),
                         ("Y", "disconnetti" if it else "disconnect"),
                         ("X", "rimuovi" if it else "remove"),
                         ("SEL", "on/off"), ("L1", "info"),
                         ("R1", "scan"), ("B", self.t("back"))])
        elif top == "hotmgr":
            it = (self.lang == "it")
            self.header("HOTSPOT", icon="uplink")
            sc = getattr(self, "hot_scripts", None)
            if not isinstance(sc, dict):
                sc = self.hot_scripts = self.hot_find()
            on = self.hot_active()
            cf = self.hot_conf()
            self.npanel(8, 46, W - 16, 64, border=LINE, fill=INK)
            self.switch(24, 60, on)
            self.text(("HOTSPOT ATTIVO" if it else "HOTSPOT ACTIVE")
                      if on else ("HOTSPOT SPENTO" if it
                                  else "HOTSPOT OFF"),
                      (104, 54), self.f_med, OK_G if on else FAINT)
            if cf:
                sub = cf.get("ssid", "")
                if cf.get("interface"):
                    sub += "  ·  " + cf["interface"]
            else:
                sub = ("Y: accendi/spegni   ·   L1: info" if it
                       else "Y: power on/off   ·   L1: info")
            self.text(sub, (104, 80), self.f_tiny, DIM, maxw=W - 140)
            acts = [k for k in ("start", "start5", "stop")
                    if sc.get(k)]
            labs = {"start": "Avvia hotspot (2.4GHz)" if it
                    else "Start hotspot (2.4GHz)",
                    "start5": "Avvia hotspot (5GHz)" if it
                    else "Start hotspot (5GHz)",
                    "stop": "Ferma hotspot" if it else "Stop hotspot"}
            y = 126
            for j2, k in enumerate(acts):
                if j2 == self.hub_sel % max(1, len(acts)):
                    self.sel_frame(8, y, W - 16, 44)
                icons.draw(self.surface,
                           "power" if k == "stop" else "uplink",
                           18, y + 10, 24,
                           NO_R if k == "stop" else self.accent)
                self.text(labs[k], (54, y + 6), self.f_med,
                          FG if j2 == self.hub_sel % max(1, len(acts))
                          else DIM)
                self.text(os.path.basename(sc[k][0]), (54, y + 27),
                          self.f_tiny, FAINT)
                y += 48
            if not acts:
                self.npanel(30, 140, W - 60, 110, border=LINE,
                            fill=INK)
                self.text("errore inatteso: script nativi assenti dal "
                          "pacchetto." if it else
                          "unexpected: native scripts missing from "
                          "the package.", (54, 168), self.f_small,
                          NO_R, maxw=W - 110)
            self.footer([("A", "esegui" if it else "run"),
                         ("Y", "on/off"), ("X", "SSID/pass"),
                         ("L1", "info"), ("B", self.t("back"))])
        elif top == "vdupdate":
            it = (self.lang == "it")
            self.header("VOID-DESK UPDATE", icon="forge")
            r = self.vdupd_result or {}
            self.text(("versione installata" if it else
                       "installed version") + ": v" + VERSION,
                      (24, 56), self.f_small, DIM)
            if r.get("error"):
                self.npanel(20, 90, W - 40, 90, border=NO_R, fill=INK)
                self.text("controllo fallito" if it else "check failed",
                          (34, 104), self.f_med, NO_R)
                for ln in self.note_wrap(r["error"], W - 68,
                                         self.f_tiny, 3):
                    self.text(ln, (34, 130), self.f_tiny, DIM)
            elif r.get("has_update"):
                self.npanel(20, 90, W - 40, 110, border=OK_G, fill=INK)
                self.text(("nuova versione disponibile" if it else
                          "new version available"), (34, 100),
                          self.f_med, OK_G)
                self.text("v" + r.get("tag", "?"), (34, 124),
                          self.f_big, OK_G)
                for k, ln in enumerate(self.note_wrap(
                        r.get("notes", ""), W - 68, self.f_tiny, 2)):
                    self.text(ln, (34, 158 + k * 17), self.f_tiny, DIM)
            elif r:
                self.npanel(20, 90, W - 40, 60, border=LINE, fill=INK)
                self.text(("sei gia' all'ultima versione" if it else
                          "you're already on the latest version"),
                          (34, 112), self.f_med, DIM, maxw=W - 68)
            self.text(("gli aggiornamenti arrivano da GitHub: " +
                      GITHUB_REPO) if it else
                      ("updates come from GitHub: " + GITHUB_REPO),
                      (24, H - 54), self.f_tiny, FAINT, maxw=W - 48)
            foot = [("Y", "ricontrolla" if it else "recheck")]
            if r.get("has_update") and r.get("url"):
                foot.append(("A", "installa" if it else "install"))
            foot.append(("B", self.t("back")))
            self.footer(foot)
        elif top == "clitools":
            it = (self.lang == "it")
            self.cli_backdrop()
            pygame.draw.rect(self.surface, (2, 5, 2), (0, 0, W, 42))
            pygame.draw.line(self.surface, self.cli_accent, (0, 42), (W, 42), 2)
            ttl = "CLI ARSENAL"
            tw0 = self.f_big.size(ttl)[0]
            self.text(ttl, ((W - tw0) // 2, 8), self.f_big, self.cli_accent)
            y = 50
            for j, (name, cat_name, cmd, di, de, ic, dp) in \
                    enumerate(CLI_TOOLS):
                sel = (j == self.clitools_sel)
                col = self.cli_accent if sel else self.cli_accent_dim
                pygame.draw.rect(self.surface, (6, 14, 8),
                                 (8, y, W - 16, 54))
                pygame.draw.rect(self.surface, col, (8, y, W - 16, 54), 2
                                 if sel else 1)
                icons.draw(self.surface, ic, 18, y + 14, 26,
                          self.cli_accent if sel else self.cli_accent_dim)
                self.text(name, (56, y + 6), self.f_med,
                          FG if sel else self.cli_accent)
                self.text(di if it else de, (56, y + 30), self.f_small,
                          self.cli_accent_dim, maxw=W - 140)
                if cat_name is None:
                    known = self.ani_cli_installed()
                else:
                    known = bool(self.status.get(cat_name))
                tag = ("pronto" if it else "ready") if known else \
                    ("da scaricare" if it else "needs install")
                tw = self.f_small.size(tag)[0]
                self.text(tag, (W - 18 - tw, y + 18), self.f_small,
                          self.cli_accent if known else self.cli_accent_dim)
                y += 58
            self.text("ani-cli e' uno script scaricato da GitHub, non "
                      "un pacchetto apt -- gli altri si installano da "
                      "CLI Installer." if it else
                      "ani-cli is a script downloaded from GitHub, not "
                      "an apt package -- the others install from CLI "
                      "Installer.", (12, H - 50), self.f_small, self.cli_accent_dim,
                      maxw=W - 24)
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "clihub":
            it = (self.lang == "it")
            self.cli_backdrop()
            pygame.draw.rect(self.surface, (2, 5, 2), (0, 0, W, 42))
            pygame.draw.line(self.surface, self.cli_accent, (0, 42), (W, 42), 2)
            ttl = "CLI TOOLS"
            tw0 = self.f_big.size(ttl)[0]
            self.text(ttl, ((W - tw0) // 2, 8), self.f_big, self.cli_accent)
            items = [("CLI ARSENAL", "elenco tool pronti da lanciare"
                      if it else "list of tools ready to launch"),
                     ("CLI INSTALLER", "installa, rimuovi, gestisci "
                      "i CLI tool" if it else
                      "install, remove, manage CLI tools"),
                     ("IMPOSTAZIONI" if it else "SETTINGS",
                      "colori, stile, shell" if it else
                      "colours, style, shell"),
                     ("HELP & ABOUT", "a cosa serve questa sezione"
                      if it else "what this section is for")]
            y = 60
            for j, (lab, sub) in enumerate(items):
                sel = (j == self.clihub_sel)
                col = self.cli_accent if sel else self.cli_accent_dim
                pygame.draw.rect(self.surface, (6, 14, 8),
                                 (8, y, W - 16, 58))
                pygame.draw.rect(self.surface, col, (8, y, W - 16, 58),
                                 2 if sel else 1)
                lw = self.f_med.size(lab)[0]
                sw = self.f_small.size(sub)[0]
                self.text(lab, ((W - lw) // 2, y + 8), self.f_med,
                          FG if sel else self.cli_accent)
                self.text(sub, ((W - sw) // 2, y + 32), self.f_small,
                          self.cli_accent_dim, maxw=W - 40)
                y += 66
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "clisettings":
            it = (self.lang == "it")
            self.cli_backdrop()
            pygame.draw.rect(self.surface, (2, 5, 2), (0, 0, W, 42))
            pygame.draw.line(self.surface, self.cli_accent, (0, 42),
                             (W, 42), 2)
            ttl = "IMPOSTAZIONI" if it else "SETTINGS"
            tw0 = self.f_big.size(ttl)[0]
            self.text(ttl, ((W - tw0) // 2, 8), self.f_big,
                      self.cli_accent)
            sel0 = (self.clisettings_sel == 0)
            col0 = self.cli_accent if sel0 else self.cli_accent_dim
            pygame.draw.rect(self.surface, (6, 14, 8), (8, 54, W - 16, 70))
            pygame.draw.rect(self.surface, col0, (8, 54, W - 16, 70),
                             2 if sel0 else 1)
            self.text("COLORE FOSFORO" if it else "PHOSPHOR COLOUR",
                      (22, 62), self.f_med, FG if sel0 else self.cli_accent)
            cur = self.cfg.get("cli_accent", "verde")
            for k, name in enumerate(CLI_ACCENTS):
                bright, dim = CLI_ACCENTS[name]
                cx0 = 22 + k * 70
                pygame.draw.rect(self.surface, bright,
                                 (cx0, 96, 24, 16),
                                 0 if name == cur else 2)
            y2 = 138
            sel1 = (self.clisettings_sel == 1)
            col1 = self.cli_accent if sel1 else self.cli_accent_dim
            pygame.draw.rect(self.surface, (6, 14, 8),
                             (8, y2, W - 16, 90))
            pygame.draw.rect(self.surface, col1, (8, y2, W - 16, 90),
                             2 if sel1 else 1)
            self.text("SHELL / AMBIENTE CLI" if it else "SHELL / CLI ENV",
                      (22, y2 + 8), self.f_med,
                      FG if sel1 else self.cli_accent)
            self.text("in arrivo con Update Desktop Systems: qui "
                      "sceglierai la combinazione shell preferita, "
                      "anche per singolo tool." if it else
                      "coming with Update Desktop Systems: you'll "
                      "choose your preferred shell combo here, even "
                      "per tool.", (22, y2 + 34), self.f_small,
                      self.cli_accent_dim, maxw=W - 44)
            self.text("la dimensione del testo si regola da "
                      "Impostazioni generali > Dimensione testo" if it
                      else "text size is set from general Settings > "
                      "Text size", (12, H - 40), self.f_small,
                      self.cli_accent_dim, maxw=W - 24)
            self.footer([("A", "cambia" if it else "change"),
                        ("B", self.t("back"))])
        elif top == "cliinstall":
            it = (self.lang == "it")
            self.cli_backdrop()
            pygame.draw.rect(self.surface, (2, 5, 2), (0, 0, W, 42))
            pygame.draw.line(self.surface, self.cli_accent, (0, 42), (W, 42), 2)
            mode_lbl = ("INSTALLER" if self.cliinst_mode == "install"
                       else "UNINSTALLER")
            ttl = "CLI " + mode_lbl
            tw0 = self.f_big.size(ttl)[0]
            self.text(ttl, ((W - tw0) // 2, 8), self.f_big, self.cli_accent)
            n = len(CLI_TOOLS)
            per = 3
            first = max(0, min(self.cliinst_sel - per // 2, n - per))
            y = 48
            for j in range(first, min(first + per, n)):
                name, cat_name, cmd, di, de, ic, dp = CLI_TOOLS[j]
                sel = (j == self.cliinst_sel)
                marked = (j in self.cliinst_marked)
                installed = (self.ani_cli_installed() if cat_name is
                            None else bool(self.status.get(cat_name)))
                col = self.cli_accent if sel else self.cli_accent_dim
                pygame.draw.rect(self.surface, (6, 14, 8),
                                 (8, y, W - 16, 88))
                pygame.draw.rect(self.surface, col, (8, y, W - 16, 88),
                                 2 if sel else 1)
                if marked:
                    pygame.draw.rect(self.surface, FG,
                                     (14, y + 6, 12, 12), 2)
                    self.text("x", (16, y + 4), self.f_small, FG)
                icons.draw(self.surface, ic, 34, y + 8, 30,
                          self.cli_accent if sel else self.cli_accent_dim)
                self.text(name, (74, y + 6), self.f_med,
                          FG if sel else self.cli_accent)
                led_col = OK_G if installed else NO_R
                led_txt = (("Installed" if it else "Installed") if
                          installed else ("Not Installed" if it else
                          "Not Installed"))
                lw = self.f_small.size(led_txt)[0]
                pygame.draw.circle(self.surface, led_col,
                                   (W - 30 - lw, y + 18), 5)
                self.text(led_txt, (W - 20 - lw, y + 11), self.f_small,
                          led_col)
                self.text((di if it else de), (74, y + 30), self.f_small,
                          self.cli_accent_dim, maxw=W - 120)
                dep_txt = ("dipendenze: " if it else "deps: ") + \
                    (", ".join(dp) if dp else ("nessuna" if it
                     else "none"))
                self.text(dep_txt, (74, y + 64), self.f_small, self.cli_accent_dim,
                          maxw=W - 120)
                y += 96
            nmark = len(self.cliinst_marked)
            self.text(("%d selezionati" % nmark) if it else
                      ("%d selected" % nmark), (14, H - 48),
                      self.f_small, self.cli_accent if nmark else self.cli_accent_dim)
            self.footer([("X", self.t("select")), ("Y", "tutti/e"
                         if it else "all"),
                         ("L1/R1", "inst/uninst"),
                         ("A", self.t("details")),
                         ("START", "esegui" if it else "run")])
        elif top == "clidetail":
            it = (self.lang == "it")
            name, cat_name, cmd, di, de, ic, dp = \
                CLI_TOOLS[self.clidetail_idx]
            installed = (self.ani_cli_installed() if cat_name is None
                        else bool(self.status.get(cat_name)))
            self.cli_backdrop()
            pygame.draw.rect(self.surface, (2, 5, 2), (0, 0, W, 42))
            pygame.draw.line(self.surface, self.cli_accent, (0, 42), (W, 42), 2)
            tw0 = self.f_big.size(name)[0]
            self.text(name, ((W - tw0) // 2, 8), self.f_big, self.cli_accent)
            y = 56 - self.scroll
            icons.draw(self.surface, ic, W // 2 - 24, y, 48, self.cli_accent)
            y += 60
            led_col = OK_G if installed else NO_R
            led_txt = ("Installed" if installed else "Not Installed")
            self.text(led_txt, (W // 2 - self.f_small.size(led_txt)[0]
                               // 2, y), self.f_small, led_col)
            y += 34
            self.text(di if it else de, (20, y), self.f_small, FG,
                      maxw=W - 40)
            y += 44
            self.text("DIPENDENZE" if it else "DEPENDENCIES",
                      (20, y), self.f_small, self.cli_accent)
            y += 22
            self.text(", ".join(dp) if dp else
                      ("nessuna" if it else "none"), (20, y),
                      self.f_small, self.cli_accent_dim, maxw=W - 40)
            y += 36
            self.text("COMANDO" if it else "COMMAND", (20, y),
                      self.f_small, self.cli_accent)
            y += 22
            self.text(cmd, (20, y), self.f_small, self.cli_accent_dim, maxw=W - 40)
            y += 36
            if cat_name is None:
                self.text("script GitHub, non un pacchetto apt" if it
                          else "GitHub script, not an apt package",
                          (20, y), self.f_small, self.cli_accent_dim, maxw=W - 40)
                y += 32
            actions = (["reinstall", "uninstall", "back"] if installed
                      else ["install", "back"])
            act_labels = {"install": "Install", "reinstall": "Reinstall",
                         "uninstall": "Uninstall", "back": "Back"}
            ay = max(y + 20, H - 70)
            ax = 20
            for k, act in enumerate(actions):
                sel = (k == self.clidetail_sel)
                lab = act_labels[act]
                lw = self.f_small.size(lab)[0] + 24
                col = self.cli_accent if sel else self.cli_accent_dim
                pygame.draw.rect(self.surface, (6, 14, 8),
                                 (ax, ay, lw, 32))
                pygame.draw.rect(self.surface, col, (ax, ay, lw, 32),
                                 2 if sel else 1)
                self.text(lab, (ax + 12, ay + 7), self.f_small,
                          FG if sel else self.cli_accent)
                ax += lw + 10
            self.footer([("SX/DX", self.t("change")),
                        ("A", self.t("confirm")),
                        ("SU/GIU", "scroll")])
        elif top == "hotcfg":
            it = (self.lang == "it")
            self.header("HOTSPOT", icon="uplink")
            labs = [("SSID", self.hotcfg_ssid),
                    ("PASSWORD", self.hotcfg_pass)]
            for j, (lab, val) in enumerate(labs):
                y = 60 + j * 66
                sel = (j == self.hotcfg_sel)
                if sel:
                    self.sel_frame(8, y, W - 16, 56)
                self.text(lab, (24, y + 8), self.f_small,
                          FG if sel else DIM)
                vs = val or "—"
                self.npanel(24, y + 26, W - 48, 24, border=LINE,
                            fill=INK, cut=6)
                self.text(vs, (32, y + 30), self.f_small, self.accent,
                          maxw=W - 64)
            if len(self.hotcfg_pass) < 8:
                self.text("WPA2 richiede almeno 8 caratteri" if it else
                          "WPA2 needs at least 8 characters",
                          (24, 200), self.f_tiny, NO_R)
            self.text("le modifiche valgono dal prossimo avvio "
                      "dell'hotspot" if it else
                      "changes apply from the next hotspot start",
                      (24, H - 70), self.f_tiny, FAINT, maxw=W - 48)
            self.footer([("A", "modifica" if it else "edit"),
                         ("Y", "salva" if it else "save"),
                         ("B", self.t("back"))])
        elif top == "monitor":
            self.mon_sample()
            it = (self.lang == "it")
            self.header("VOID MONITOR", icon="task")
            m = self.mon
            tabs = ["DASHBOARD", "CPU", "RAM", "TEMP", "NET"]
            tw2 = W // len(tabs)
            for i2, tl in enumerate(tabs):
                sel = (i2 == self.mon_tab)
                if sel:
                    pygame.draw.rect(self.surface, sel_tint(self.accent),
                                     (i2 * tw2, 44, tw2, 26))
                    pygame.draw.line(self.surface, self.accent,
                                     (i2 * tw2, 68), (i2 * tw2 + tw2, 68),
                                     2)
                tcol = self.accent if sel else FAINT
                timg = self.f_tiny.render(tl, True, tcol)
                self.surface.blit(timg, (i2 * tw2 + (tw2 -
                                         timg.get_width()) // 2, 51))
            y0 = 76
            if self.mon_tab == 0:
                cards = [("CPU", m["cpu"], self.accent, "%d%%", "pill"),
                        ("RAM", m["ram"], (110, 195, 250), "%d%%",
                         "blocks"),
                        ("TEMP", m["tmp"], NO_R, "°C", "thermo"),
                        ("NET", m["net"], OK_G, "", "spark")]
                cw2, ch2 = (W - 24) // 2, 168
                for i2, (lbl, data, col, fmt, kind) in enumerate(cards):
                    r_, c_ = divmod(i2, 2)
                    x = 8 + c_ * (cw2 + 8)
                    y = y0 + r_ * (ch2 + 8)
                    self.npanel(x, y, cw2, ch2, border=LINE, fill=INK,
                                cut=12)
                    self.text(lbl, (x + 14, y + 10), self.f_small, col)
                    cur = data[-1] if data else 0
                    vs = ("%.0f KB/s" % m.get("netkb", 0) if lbl == "NET"
                          else ("%d°C" % m.get("tempc", 0) if lbl == "TEMP"
                                else fmt % cur))
                    vw = self.f_med.size(vs)[0]
                    self.text(vs, (x + cw2 - vw - 14, y + 8), self.f_med,
                              col)
                    if kind == "pill":
                        self.mon_pill(x + 14, y + 56, cw2 - 28, 22, cur,
                                      col)
                        self.mon_spark(x + 14, y + 96, cw2 - 28, 52,
                                       data, col, n=cw2 // 5)
                    elif kind == "blocks":
                        self.mon_blocks(x + 14, y + 60, cw2 - 28, 26,
                                        cur, col, n=14)
                        self.mon_spark(x + 14, y + 100, cw2 - 28, 48,
                                       data, col, n=cw2 // 5)
                    elif kind == "thermo":
                        self.mon_thermo(x + 30, y + 44, y + ch2 - 16,
                                        11, cur, col)
                        self.mon_spark(x + 60, y + 50, cw2 - 90,
                                       ch2 - 70, data, col, n=(cw2-90)//5)
                    else:
                        self.mon_spark(x + 14, y + 50, cw2 - 28,
                                       ch2 - 66, data, col, n=(cw2-28)//5)
            else:
                lbl, data, col, unit = {
                    1: ("CPU", m["cpu"], self.accent, "%"),
                    2: ("RAM", m["ram"], (110, 195, 250), "%"),
                    3: ("TEMP", m["tmp"], NO_R, "°C"),
                    4: ("NET", m["net"], OK_G, ""),
                }[self.mon_tab]
                cur, mn, mx, avg = self.mon_stats(data)
                if self.mon_tab == 3:
                    cur_disp, mn_disp = m.get("tempc", 0), mn
                elif self.mon_tab == 4:
                    cur_disp = m.get("netkb", 0)
                else:
                    cur_disp = cur
                big = ("%.0f" % cur_disp) + (unit if self.mon_tab != 4
                                             else " KB/s")
                bimg = self.f_big.render(big, True, col)
                self.surface.blit(bimg, ((W - bimg.get_width()) // 2,
                                         y0 + 4))
                if self.mon_tab == 1:
                    self.mon_pill(30, y0 + 60, W - 60, 30, cur, col)
                elif self.mon_tab == 2:
                    self.mon_blocks(30, y0 + 60, W - 60, 34, cur, col,
                                    n=22)
                elif self.mon_tab == 3:
                    self.mon_thermo(W // 2, y0 + 56, y0 + 168, 16, cur,
                                    col)
                stat_y = y0 + (200 if self.mon_tab == 3 else 110)
                self.text(("min %d%s  ·  media %d%s  ·  max %d%s" if it
                           else "min %d%s  ·  avg %d%s  ·  max %d%s") %
                          (mn, unit, avg, unit, mx, unit),
                          (30, stat_y), self.f_small, DIM)
                gy = stat_y + 28
                self.npanel(20, gy, W - 40, H - gy - 44, border=LINE,
                            fill=INK)
                self.mon_spark(30, gy + 10, W - 60, H - gy - 64, data,
                               col, n=(W - 60) // 6)
            self.footer([("L1/R1", "scheda" if it else "tab"),
                         ("B", self.t("back"))])
        elif top == "pyrepl":
            self.header("PYTHON", icon="terminal")
            it2 = (self.lang == "it")
            self.npanel(8, 44, W - 16, 34, border=self.accent,
                        fill=sel_tint(self.accent), cut=8)
            icons.draw(self.surface, "folder", 18, 50, 22,
                       self.accent)
            self.text(("Y  ·  APRI UN FILE .PY DALLO STORAGE" if it2
                       else "Y  ·  OPEN A .PY FILE FROM STORAGE"),
                      (50, 52), self.f_med, self.accent)
            per = 15
            rows = self.py_out[-per:]
            y = 86
            for ln in rows:
                col = self.accent if ln.startswith(">>>") else DIM
                self.text(ln, (16, y), self.f_small, col, maxw=W - 32)
                y += 21
            self.footer([("A", "scrivi" if self.lang == "it"
                          else "type"),
                         ("Y", "apri .py" if self.lang == "it"
                          else "open .py"), ("X", "clear"),
                         ("!cmd", "shell"),
                         ("B", self.t("back"))])
        elif top == "backup":
            it = (self.lang == "it")
            self.header(self.t("w_bak"), icon="archive")
            baks = self.bak_list()
            y = 54
            if self.bak_sel == 0:
                self.sel_frame(8, y, W - 16, 46)
            icons.draw(self.surface, "archive", 18, y + 11, 24,
                       self.accent)
            self.text("+ " + ("crea backup adesso" if it
                              else "create backup now"),
                      (54, y + 12), self.f_med, self.accent)
            y += 52
            for j, (nm, p, sz) in enumerate(baks):
                if self.bak_sel == j + 1:
                    self.sel_frame(8, y, W - 16, 46)
                icons.draw(self.surface, "disk", 18, y + 11, 24, FAINT)
                self.text(nm, (54, y + 5), self.f_med, FG,
                          maxw=W - 200)
                self.text(human(sz) + "  ·  " + os.path.dirname(p),
                          (54, y + 27), self.f_tiny, FAINT,
                          maxw=W - 90)
                y += 50
            if not baks:
                self.text("nessun backup: creane uno." if it
                          else "no backups yet: make one.",
                          (54, y + 10), self.f_small, DIM)
            self.footer([("A", "crea/ripristina" if it
                          else "create/restore"),
                         ("X", "elimina" if it else "delete"),
                         ("B", self.t("back"))])
        elif top == "tspanel":
            it = (self.lang == "it")
            self.header("TAILSCALE")
            if getattr(self, "ts_logo", None):
                pygame.draw.rect(self.surface, INK, (10, 5, 36, 34))
                self.surface.blit(self.ts_logo, (13, 7))
            ts = self.ts or {}
            run = ts.get("state") == "Running"
            self.npanel(8, 46, W - 16, 54, border=TS_BLUE, fill=INK,
                        cut=9)
            self.text(ts.get("host", "?"), (22, 52), self.f_med, FG)
            self.text(ts.get("ip") or "-", (22, 76), self.f_small,
                      TS_GRAY)
            stt = ts.get("state", "?")
            self.text(stt, (W - 28 - self.f_med.size(stt)[0], 52),
                      self.f_med, OK_G if run else NO_R)
            using = [p["name"] for p in ts.get("peers", [])
                     if p.get("using")]
            if using:
                ex = ("exit: " + using[0])[:26]
                self.text(ex, (W - 28 - self.f_small.size(ex)[0], 78),
                          self.f_small, TS_BLUE)
            peers = ts.get("peers", [])
            per = 6
            first = max(0, min(self.ts_sel - per // 2,
                               len(peers) - per))
            y = 110
            if not peers:
                self.text("nessun peer nella tailnet" if it
                          else "no peers in the tailnet", (40, 160),
                          self.f_med, DIM)
            for j in range(first, min(first + per, len(peers))):
                p = peers[j]
                if j == self.ts_sel:
                    self.sel_frame(8, y, W - 16, 48, color=TS_BLUE)
                pygame.draw.circle(self.surface,
                                   OK_G if p["on"] else (90, 94, 102),
                                   (26, y + 24), 6)
                self.text(p["name"], (46, y + 6), self.f_med,
                          FG if j == self.ts_sel else DIM,
                          maxw=W - 260)
                self.text("%s  ·  %s" % (p["ip"], p["os"] or "?"),
                          (46, y + 28), self.f_tiny, TS_GRAY
                          if p["on"] else FAINT)
                if p.get("exit"):
                    tag = "EXIT"
                    tw = self.f_tiny.size(tag)[0]
                    self.npanel(W - tw - 40, y + 14, tw + 16, 20,
                                border=TS_BLUE, fill=INK, cut=5)
                    self.text(tag, (W - tw - 32, y + 17), self.f_tiny,
                              TS_BLUE)
                y += 50
            self.footer([("A", "peer"), ("Y", "azioni" if it
                                         else "actions"),
                         ("R1", "aggiorna" if it else "refresh"),
                         ("B", self.t("back"))])
        elif top in ("tsmenu", "tsact"):
            self.render_prev_dim()
            if top == "tsmenu":
                acts = self.ts_menu_items()
            else:
                peer = (self.ts or {}).get("peers", [])[self.ts_sel]
                acts = [("ping", "Ping")]
                if peer.get("exit"):
                    acts.append(("exit", "Usa come exit node"
                                 if self.lang == "it" else
                                 "Use as exit node"))
                acts += [("send", "Invia file (Taildrop)"
                          if self.lang == "it" else
                          "Send file (Taildrop)"), ("pinfo", "Info")]
            hgt = 24 + len(acts) * 40
            self.npanel(140, 120, W - 280, hgt, border=TS_BLUE,
                        fill=INK, cut=10)
            for j, (k, lab) in enumerate(acts):
                y = 132 + j * 40
                if j == self.hub_sel:
                    self.sel_frame(148, y, W - 296, 36, color=TS_BLUE)
                self.text(lab, (166, y + 8), self.f_med,
                          FG if j == self.hub_sel else DIM)
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "ftpprof":
            it = (self.lang == "it")
            self.header("VOID FTP", icon="download")
            profs = self.cfg.get("ftp_profiles", [])
            y = 56
            for j, p in enumerate(profs + [None]):
                if j == self.ftp_prof_sel:
                    self.sel_frame(8, y, W - 16, 46)
                if p is None:
                    icons.draw(self.surface, "pkg", 18, y + 11, 24,
                               self.accent)
                    self.text("+ " + ("nuovo profilo" if it
                                      else "new profile"),
                              (54, y + 12), self.f_med, self.accent)
                else:
                    icons.draw(self.surface, "remote", 18, y + 11, 24,
                               FAINT)
                    self.text(p.get("name") or p["host"], (54, y + 5),
                              self.f_med, FG)
                    self.text("%s@%s:%s" % (p.get("user", ""),
                                            p.get("host", ""),
                                            p.get("port", 21)),
                              (54, y + 26), self.f_tiny, FAINT)
                y += 50
            self.footer([("A", "connetti" if it else "connect"),
                         ("X", "elimina" if it else "delete"),
                         ("B", self.t("back"))])
        elif top == "ftpls":
            it = (self.lang == "it")
            self.header("VOID FTP", icon="download")
            pb = self.ftp_cwd
            if len(pb) > 50:
                pb = "..." + pb[-47:]
            self.npanel(8, 46, W - 16, 26, border=LINE, fill=INK, cut=7)
            self.text(pb, (18, 50), self.f_small, DIM, maxw=W - 140)
            if self.ftp_marked:
                ex = "%d sel" % len(self.ftp_marked)
                self.text(ex, (W - 22 - self.f_small.size(ex)[0], 50),
                          self.f_small, self.accent)
            per = 8
            first = max(0, min(self.ftp_sel - per // 2,
                               len(self.ftp_items) - per))
            y = 78
            for j in range(first, min(first + per,
                                      len(self.ftp_items))):
                nm, isd, sz = self.ftp_items[j]
                if j == self.ftp_sel:
                    self.sel_frame(8, y, W - 16, 42)
                if nm in self.ftp_marked:
                    pygame.draw.rect(self.surface, self.accent,
                                     (10, y + 8, 4, 26))
                icons.draw(self.surface,
                           "folder" if isd else "download", 20, y + 9,
                           24, self.accent if j == self.ftp_sel
                           else FAINT)
                self.text(nm, (56, y + 5), self.f_med,
                          FG if j == self.ftp_sel else DIM,
                          maxw=W - 200)
                self.text("<DIR>" if isd else human(sz),
                          (56, y + 25), self.f_tiny, FAINT)
                y += 44
            self.footer([("A", self.t("open")), ("X", "sel"),
                         ("Y", "azioni" if it else "actions"),
                         ("B", self.t("back"))])
        elif top == "ftpmenu":
            self.render_prev_dim()
            acts = self.ftp_menu_items()
            hgt = 24 + len(acts) * 40
            self.npanel(150, 140, W - 300, hgt, border=self.accent,
                        fill=INK, cut=10)
            for j, (k, lab) in enumerate(acts):
                y = 152 + j * 40
                if j == self.hub_sel:
                    self.sel_frame(158, y, W - 316, 36)
                self.text(lab, (176, y + 8), self.f_med,
                          FG if j == self.hub_sel else DIM)
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "syncpanel":
            it = (self.lang == "it")
            self.header("SYNCTHING", icon="remote")
            sy = self.sync or {"id": "?", "folders": []}
            self.npanel(8, 48, W - 16, 30, border=LINE, fill=INK, cut=8)
            self.text("ID: " + sy["id"], (20, 54), self.f_small, DIM)
            ok = "demone attivo" if it else "daemon up"
            self.text(ok, (W - 24 - self.f_small.size(ok)[0], 54),
                      self.f_small, OK_G)
            y = 92
            if not sy["folders"]:
                self.text("nessuna cartella condivisa" if it
                          else "no shared folders", (40, 140),
                          self.f_med, DIM)
            for lbl, path, pct in sy["folders"][:6]:
                self.npanel(8, y, W - 16, 52, border=LINE, fill=INK)
                self.text(lbl, (22, y + 6), self.f_med, FG,
                          maxw=W - 160)
                self.text(path, (22, y + 28), self.f_tiny, FAINT,
                          maxw=W - 200)
                if pct >= 0:
                    ps = "%d%%" % pct
                    self.text(ps, (W - 30 - self.f_med.size(ps)[0],
                                   y + 6), self.f_med,
                              OK_G if pct >= 100 else self.accent)
                    bw = W - 190
                    pygame.draw.rect(self.surface, (14, 15, 19),
                                     (22, y + 44, bw, 5))
                    pygame.draw.rect(self.surface,
                                     OK_G if pct >= 100 else self.accent,
                                     (22, y + 44, bw * pct // 100, 5))
                y += 58
            self.footer([("A", "aggiorna" if it else "refresh"),
                         ("B", self.t("back"))])
        elif top == "osk":
            self.header(self.osk_title[:26], icon="keyboard")
            self.npanel(10, 52, W - 20, 50, border=self.accent, fill=INK)
            buf = self.osk_buf
            cpos = max(0, min(len(buf), getattr(self, "osk_cursor",
                                                len(buf))))
            bw = self.f_med.size(buf)[0]
            bx = min(24, W - 40 - bw) if bw > W - 64 else 24
            self.text(buf, (bx, 66), self.f_med, FG)
            pre_w = self.f_med.size(buf[:cpos])[0]
            cx = bx + pre_w
            if int(time.time() * 2) % 2:
                pygame.draw.rect(self.surface, self.accent,
                                 (cx, 62, 3, 26))
            rows = OSK_PAGES[self.osk_page]
            kw = (W - 28) // 10
            for r in range(4):
                for c in range(10):
                    x = 14 + c * kw
                    y = 122 + r * 62
                    sel = (r * 10 + c) == self.osk_sel
                    self.npanel(x, y, kw - 6, 54,
                                border=(self.accent if sel else LINE),
                                fill=(sel_tint(self.accent) if sel
                                      else INK), cut=6)
                    ch = rows[r][c]
                    cw2 = self.f_med.size(ch)[0]
                    self.text(ch, (x + (kw - 6 - cw2) // 2, y + 15),
                              self.f_med, FG if sel else DIM)
            it2 = (self.lang == "it")
            self.footer([("A", "car." if it2 else "char"),
                         ("X", "⌫"),
                         ("Y", "spazio" if it2 else "space"),
                         ("L1/R1", "cursore" if it2 else "cursor"),
                         ("SEL", "pag." if it2 else "page"),
                         ("START", "OK")])
        elif top == "files":
            it = (self.lang == "it")
            self.header("VOID FILES", icon="folder")
            pb = self.fm_path or ("scegli una memoria" if it
                                  else "choose a drive")
            if len(pb) > 52:
                pb = "..." + pb[-49:]
            self.npanel(8, 46, W - 16, 26, border=LINE, fill=INK, cut=7)
            self.text(pb, (18, 50), self.f_small, DIM, maxw=W - 180)
            extra = []
            if self.fm_marked:
                extra.append("%d sel" % len(self.fm_marked))
            if self.fm_clip:
                extra.append("clip:%d" % len(self.fm_clip[1]))
            if self.fm_pick:
                extra.append("PICK")
            if extra:
                ex = "  ".join(extra)
                self.text(ex, (W - 22 - self.f_small.size(ex)[0], 50),
                          self.f_small, self.accent)
            per = 8
            first = max(0, min(self.fm_sel - per // 2,
                               len(self.fm_items) - per))
            y = 78
            for j in range(first, min(first + per,
                                      len(self.fm_items))):
                nm, isd, sz = self.fm_items[j]
                full = (os.path.join(self.fm_path, nm)
                        if self.fm_path else nm)
                if j == self.fm_sel:
                    self.sel_frame(8, y, W - 16, 42)
                if self.fm_path and full in self.fm_marked:
                    pygame.draw.rect(self.surface, self.accent,
                                     (10, y + 8, 4, 26))
                icons.draw(self.surface, self.fm_icon(nm, isd), 20,
                           y + 9, 24,
                           self.accent if j == self.fm_sel else FAINT)
                self.text(nm, (56, y + 5), self.f_med,
                          FG if j == self.fm_sel else DIM, maxw=W - 200)
                self.text("<DIR>" if isd else human(sz),
                          (56, y + 25), self.f_tiny, FAINT)
                y += 44
            self.footer([("A", self.t("open")), ("X", "sel"),
                         ("Y", "azioni" if it else "actions"),
                         ("B", self.t("back"))])
        elif top == "fmenu":
            self.render_prev_dim()
            acts = self.fm_menu_items()
            hgt = 24 + len(acts) * 40
            self.npanel(150, 110, W - 300, hgt, border=self.accent,
                        fill=INK, cut=10)
            for j, (k, lab) in enumerate(acts):
                y = 122 + j * 40
                if j == self.hub_sel:
                    self.sel_frame(158, y, W - 316, 36)
                self.text(lab, (176, y + 8), self.f_med,
                          FG if j == self.hub_sel else DIM)
            self.footer([("A", self.t("open")), ("B", self.t("back"))])
        elif top == "imgview":
            self.surface.fill((0, 0, 0))
            try:
                img = pygame.image.load(self.img_path)
                iw, ih = img.get_size()
                k = min((W - 20) / iw, (H - 60) / ih, 4)
                img = pygame.transform.smoothscale(
                    img, (int(iw * k), int(ih * k)))
                self.surface.blit(img, ((W - img.get_width()) // 2,
                                        (H - 44 - img.get_height()) // 2))
            except pygame.error:
                self.text("immagine illeggibile", (200, 220),
                          self.f_med, NO_R)
            self.footer([(os.path.basename(self.img_path)[:40], ""),
                         ("B", self.t("back"))])
        elif top == "edit":
            it = (self.lang == "it")
            nm = os.path.basename(self.ed_path) + \
                (" *" if self.ed_dirty else "")
            self.header(nm[:26], icon="text")
            if self.ed_msg:
                self.text(self.ed_msg,
                          (W - 24 - self.f_tiny.size(self.ed_msg)[0], 30),
                          self.f_tiny, OK_G)
            per = 18
            first = max(0, min(self.ed_cur - per // 2,
                               len(self.ed_lines) - per))
            y = 50
            for j in range(first, min(first + per,
                                      len(self.ed_lines))):
                if j == self.ed_cur:
                    pygame.draw.rect(self.surface,
                                     sel_tint(self.accent),
                                     (8, y - 1, W - 16, 21))
                    pygame.draw.rect(self.surface, self.accent,
                                     (8, y - 1, 3, 21))
                self.text("%3d" % (j + 1), (12, y), self.f_tiny, FAINT)
                self.text(self.ed_lines[j][:96], (46, y), self.f_small,
                          FG if j == self.ed_cur else DIM, maxw=W - 60)
                y += 21
            self.footer([("A", "modifica" if it else "edit"),
                         ("Y", "+riga" if it else "+line"), ("X", "-"),
                         ("START", "salva" if it else "save"),
                         ("B", self.t("back"))])
        else:
            # stato senza schermata: meglio dirlo che congelarsi
            self.header("VOID-DESK")
            self.npanel(60, 180, W - 120, 100, border=NO_R, fill=INK)
            self.text("stato sconosciuto: %s" % top, (84, 210), self.f_med,
                      NO_R)
            self.text("B: " + self.t("back"), (84, 240), self.f_small, DIM)
        self.apply_fx()

    def render(self, flip=True):
        self.render_state()
        if self.trans:
            dur = self.trans.get("dur", 0.34)
            k = (time.time() - self.trans["t0"]) / dur
            if k >= 1.0:
                self.trans = None
                self.play("snap")
            else:
                # easing "back-out": supera leggermente il bersaglio
                # prima di assestarsi, come un meccanismo con inerzia
                # vera invece di un dissolvenza morbida
                c1, c3 = 1.70158, 2.70158
                kk = k - 1
                e = 1 + c3 * kk ** 3 + c1 * kk ** 2
                cur = self.surface.copy()
                if self.prev_frame:
                    self.surface.blit(self.prev_frame, (0, 0))
                x0, y0, w0, h0 = self.trans["rect"]
                r = pygame.Rect(int(x0 * (1 - e)), int(y0 * (1 - e)),
                                max(10, int(w0 + (W - w0) * e)),
                                max(10, int(h0 + (H - h0) * e)))
                r = r.clip(pygame.Rect(-40, -40, W + 80, H + 80))
                self.surface.set_clip(r)
                self.surface.blit(cur, (0, 0))
                self.surface.set_clip(None)
                c = self.trans.get("color") or self.accent
                pygame.draw.rect(self.surface, c, r, 1)
                for cx, cy, dx, dy in ((r.left, r.top, 1, 1),
                                       (r.right - 1, r.top, -1, 1),
                                       (r.left, r.bottom - 1, 1, -1),
                                       (r.right - 1, r.bottom - 1,
                                        -1, -1)):
                    pygame.draw.line(self.surface, c, (cx, cy),
                                     (cx + 10 * dx, cy), 2)
                    pygame.draw.line(self.surface, c, (cx, cy),
                                     (cx, cy + 8 * dy), 2)
                if 1 < r.top < H and r.h > 8:
                    band = self.surface.subsurface(
                        (0, max(0, r.top - 1), W, 2)).copy()
                    self.surface.blit(band, (3, max(0, r.top - 1)))
        self.interference()
        if flip:
            pygame.display.flip()

    # --------------------------------------------------------------- intro
    def play_intro(self):
        """Sigla d'avvio; l'ultimo atto atterra dentro il menu vero."""
        real_flip = pygame.display.flip
        pygame.display.flip = lambda *a, **k: None
        try:
            self.render()                 # disegno il menu, senza mostrarlo
            menu_img = self.surface.copy()
        finally:
            pygame.display.flip = real_flip
        # Il tasto con cui muOS ha lanciato l'app puo' essere ancora in coda:
        # svuoto la coda e per un attimo ignoro i tasti, altrimenti la sigla
        # verrebbe saltata prima ancora di cominciare.
        evinput.poll()
        t_start = time.time()

        def can_skip():
            if time.time() - t_start < 0.8:
                evinput.poll()
                return False
            return bool(evinput.poll())

        jingle = None
        if self.cfg.get("sfx", True):
            jingle = self.build_intro_jingle()
        intro.play(self.surface, pygame.display.flip, "Void-DESK",
                   self.accent, skip_check=can_skip, font_path=FONT_PATH,
                   duration=0.45, menu_surf=menu_img,
                   jingle=jingle)

    # ---------------------------------------------------------------- loop
    def handle_capture(self):
        """Cattura: aspetta un tasto fisico. Legge in parallelo js0 per
        imparare il numero pulsante che vede QJoyPad (verita' dal kernel)."""
        js = jsmap.js_poll(self.js_fd)
        raw = evinput.poll_raw()
        if js and raw:
            self.cfg.setdefault("qj_map", {})[str(raw[0])] = js[0] + 1
        if raw:
            ev = raw[0]
            key0 = self.map_rows()[self.map_sel]
            # QJoyPad non vede i tasti volume: ammessi solo per la tastiera
            if ev in VOLUME_KEYS and key0 != "kbd":
                return
            key = self.map_rows()[self.map_sel]
            other = self.owner_of(ev, key)
            self.pop_state()                      # esce da "capture"
            if other:
                self.pending = (key, ev, other)
                self.push("swap")
            else:
                self.cur_map()[key] = [ev]
                self.apply_map()
            return
        if time.time() - self.capture_t > 5:      # annulla per timeout
            self.pop_state()

    def run(self):
        while self.running:
            if self.stack[-1] == "capture":
                self.handle_capture()
                self.render()
                self.clock.tick(30)
                continue
            if self.alarms():
                self.check_alarms()
            for btn in evinput.poll():
                if btn != "MENU":
                    self.on_button(btn)
            hx, hy = evinput.hat()
            now = time.time()
            if (hx or hy) and now - self._dpad_t > 0.15:
                self._dpad_t = now
                if hy > 0:
                    self.on_button("UP")
                elif hy < 0:
                    self.on_button("DOWN")
                if hx < 0:
                    self.on_button("LEFT")
                elif hx > 0:
                    self.on_button("RIGHT")
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
            self.render()
            self.clock.tick(30)
        evinput.stop()
        fbdisplay.detach()
        return self.exit_code


if __name__ == "__main__":
    sys.exit(App().run())
