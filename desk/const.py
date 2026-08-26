import os
import sys

# Define APP_DIR locally to avoid circular imports
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure parent directory is in sys.path to find desk package
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Add desk directory to path for local module imports
_desk_dir = os.path.dirname(os.path.abspath(__file__))
if _desk_dir not in sys.path:
    sys.path.insert(0, _desk_dir)

# --- [B1] Screen Dimensions & Base Colors ---
W, H = 640, 480
BG = (7, 8, 11)            # nero megastruttura
PANEL = (18, 20, 26)       # lastra scura
LINE = (34, 38, 47)        # nervature della struttura
INK = (2, 2, 4)            # china: piu' nero del fondo
STEEL = (78, 86, 98)       # acciaio strutturale: mai un accento, sempre struttura
STEEL_HI = (128, 138, 150) # riflesso freddo sull'acciaio, per il bevel

# --- [B2] CLI Accent Palettes ---
GRN = (60, 255, 110)        # fosforo verde: terminale retro, mondo a parte
DGRN = (20, 90, 45)
CLI_ACCENTS = {
    "verde":  ((60, 255, 110), (20, 90, 45)),
    "ambra":  ((255, 190, 60), (95, 70, 20)),
    "ciano":  ((80, 220, 255), (25, 82, 96)),
    "bianco": ((228, 228, 222), (86, 86, 82)),
}
FG = (233, 233, 226)       # bianco osso

# --- [B3] Theme Accents & Secondary Tints ---
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

# --- [C1] HUBS Definition (FORGE, UPLINK, MEDIA, WORKSHOP, TOOLBOX, INFO, SETTINGS) ---
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
    ("chd",     "disk",    "w_chd",   "w_chd_s",   "push"),
    ("doppel",  "shield",  "w_dop",   "w_dop_s",   "push"),
    ("clean",   "trash",   "w_clean", "w_clean_s", "act"),
    ("logs",    "doc",     "w_logs",  "w_logs_s",  "push"),
    ("backup",  "archive", "w_bak",   "w_bak_s",   "push"),
 ]),
 "uplink": ("uplink", "h_up", [
    ("sync",    "remote",  "u_sync",  "u_sync_s",  "act"),
    ("tsgui",   "uplink",  "u_ts",    "u_ts_s",    "act"),
    ("ftp",     "download","u_ftp",   "u_ftp_s",   "act"),
    ("netdiag", "globe",   "u_netdiag", "u_netdiag_s", "act"),
    ("wifi",    "wifi",    "u_wifi",  "u_wifi_s",  "push"),
    ("hotspot", "uplink",  "u_hot",   "u_hot_s",   "push"),
    ("bt",      "bt",      "u_bt",    "u_bt_s",    "push"),
    ("pcup",    "monitor", "u_pcup",  "u_pcup_s",  "push"),
    ("basestation", "remote", "u_base", "u_base_s", "push"),
    ("deviceremapper", "gamepad", "u_devmap", "u_devmap_s", "act"),
    ("wiredcontroller", "keyboard", "u_wired", "u_wired_s", "act"),
  ]),
 "ctrlhub": ("keyboard", "h_cthub", [
    ("kbdmb",   "keyboard","u_kmb",   "u_kmb_s",   "cycle"),
    ("kbdx",    "keyboard","u_kx",    "u_kx_s",    "cycle"),
    ("ctrl",    "gamepad", "u_ctrl",  "u_ctrl_s",  "cycle"),
    ("map",     "gamepad", "u_map",   "u_map_s",   "push"),
    ("devices", "keyboard","u_devs",  "u_devs_s",  "act"),
 ]),
 "mediahub": ("speaker", "h_media", [
    ("radio",    "speaker", "m_radio", "m_radio_s", "push"),
    ("voidcast", "video",   "m_iptv",  "m_iptv_s",  "act"),
    ("library",  "folder",  "m_lib",   "m_lib_s",   "act"),
    ("bgmnorm",  "music",   "m_bgm",   "m_bgm_s",   "act"),
 ]),
 "toolbox": ("toolbox", "h_tool", [
    ("calc",    "calc",    "t_calc",  "t_calc_s",  "push"),
    ("clockmain", "clock", "t_clock", "t_clock_s", "push"),
    ("cal",     "clock",   "t_cal",   "t_cal_s",   "push"),
    ("notes",   "text",    "t_note",  "t_note_s",  "push"),
    ("fileman", "folder",  "t_fm",    "t_fm_s",    "act"),
    ("shell",   "terminal","t_sh",    "t_sh_s",    "act"),
    ("pyrepl",  "terminal","t_py",    "t_py_s",    "push"),
     ("void_edit", "text",    "t_ed",    "t_ed_s",    "act"),
    ("rss",     "globe",   "t_rss",   "t_rss_s",   "push"),
    ("weather", "w_partly","t_wx",    "t_wx_s",    "push"),
  ]),
 "infohub": ("book", "h_info", [
     ("about",   "info",    "i_about", "i_about_s", "act"),
     ("manual",  "book",    "i_man",   "i_man_s",   "push"),
     ("guide",   "gamepad", "i_guide", "i_guide_s", "act"),
     ("manifesto", "terminal", "i_manifesto", "i_manifesto_s", "act"),
     ("voidupdate", "gear", "i_update", "i_update_s", "act"),
     ("cursedev", "", "cursedev_title", "cursedev_title", "act"),
  ]),
 "games": ("games", "h_games", [
     ("portmaster", "gamepad", "g_pm", "g_pm_s", "act"),
     ("native", "gamepad", "g_nat", "g_nat_s", "act"),
     ("collections", "folder", "g_col", "g_col_s", "act"),
  ]),
 "develop": ("develop", "h_develop", [
     ("repl", "terminal", "d_repl", "d_repl_s", "push"),
     ("editor", "text", "d_ed", "d_ed_s", "act"),
     ("builder", "gear", "d_bld", "d_bld_s", "act"),
  ]),
 "community": ("community", "h_community", [
     ("forum", "globe", "c_forum", "c_forum_s", "act"),
     ("wiki", "book", "c_wiki", "c_wiki_s", "act"),
     ("share", "folder", "c_share", "c_share_s", "act"),
  ]),
 "outerdesk": ("outerdesk", "h_outerdesk", [
     ("apps", "outer", "od_apps", "od_apps_s", "push"),
  ]),
 "legacy": ("legacy", "h_legacy", [
     ("archive", "archive", "l_arch", "l_arch_s", "act"),
     ("memorial", "info", "l_mem", "l_mem_s", "act"),
  ]),
}

# --- [C2] CYCLES (User-togglable Settings) ---
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
RTSH_LAYOUTS = {
    "lower": ["qwertyuiop", "asdfghjkl", "zxcvbnm"],
    "upper": ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"],
    "symbols": ["-_=+[]{}\\|", ";:'\",.<>/?", "~`^*()#@"],
}
RTSH_NUM_DEFAULT = list("1234567890")
RTSH_NUM_SYMBOLS = list("!@#$%^&*()")
RTSH_SYMBOL_CANDIDATES = list("!@#$%^&*()-_=+[]{}|;:'\",.<>/?~`\\")
RTSH_HOTKEYS_DEFAULT = [
    ("^C", "\x03"), ("^D", "\x04"), ("^L", "\x0c"), ("^Z", "\x1a"),
    ("TAB", "\t"), ("ESC", "\x1b"), ("^A", "\x01"), ("^E", "\x05"),
]
RTSH_HOTKEYS_ALL = RTSH_HOTKEYS_DEFAULT + [
    ("^U", "\x15"), ("^W", "\x17"), ("^R", "\x12"), ("^K", "\x0b"),
]

OSK_PAGES = [
    ["qwertyuiop", "asdfghjkl-", "zxcvbnm_.,", "1234567890"],
    ["QWERTYUIOP", "ASDFGHJKL-", "ZXCVBNM_.,", "1234567890"],
    ["1234567890", "!@#$%^&*()", "+-*/=<>[]{", "}:;'\"~`|\\ "],
]

CLOCK_LAYOUTS = ["classic", "minimal", "segmented", "analog", "skeleton",
                 "pilot"]
HOME_STYLES = ["blame", "hud", "terminal", "orbit", "nexus"]
DEFAULT_HOME_STYLE = "nexus"  # v10.0.0 "Nexus": vista di default del menu
# VOIDDESK V10 -- Net-Sphere: come sono raggruppati i 10 nodi del menu
# principale sulle 3 orbite concentriche. Gli indici sono quelli di
# self.menu/self.menu_icons. SHUTDOWN (indice 9) e' un nodo vero
# sull'anello esterno, non solo un tasto di scelta rapida: usa la
# chiave di traduzione "h_exit" che esisteva gia' nel dizionario ma
# non era mai stata agganciata a nulla.
NEXUS_RING_INNER = [0]                                    # START SESSION
NEXUS_RING_MID = [3, 5, 2, 6, 10, 11]                     # FORGE, UPLINK, MEDIA, WORKSHOP, GAMES, DEVELOP
NEXUS_RING_OUT = [4, 1, 7, 8, 12, 13]                     # TOOLBOX, MUOS APPS, SYSTEM, INFO, COMMUNITY, OUTERDESK
NEXUS_RING_FAR = [9]                                      # END NODE (solo lui)
NEXUS_RING_VOID = [14]                                    # QUARTA ORBITA — LEGACY (chiusura)
NEXUS_NODE_COLOR = {
    0: (255, 205, 120),    # START SESSION -- bianco/ambra
    3: (240, 90, 60),      # FORGE -- rosso/ambra
    5: (80, 205, 255),     # UPLINK -- ciano
    2: (230, 80, 190),     # MEDIA VAULT -- magenta/teal
    6: (175, 110, 240),    # WORKSHOP -- viola/giallo
    4: (95, 210, 140),     # TOOLBOX -- verde/acciaio
    1: (225, 225, 235),    # MUOS APPS -- bianco/argento
    7: (100, 130, 210),    # SETTINGS ("SYSTEM") -- blu scuro/grigio
    8: (150, 160, 180),    # INFO & ABOUT
    9: (215, 80, 35),      # SHUTDOWN -- rosso scuro/arancione

    # NUOVI NODI v10.14
    10: (255, 180, 50),    # GAMES — oro/ambra
    11: (60, 230, 200),    # DEVELOP — turchese
    12: (200, 150, 255),   # COMMUNITY — lavanda
    13: (255, 120, 160),   # OUTERDESK — rosa/cielo
    14: (80, 80, 90),      # LEGACY — grigio scuro (chiusura)
}
# v10.7: colore primario dedicato per il menu (e sottomenu) di THE
# FORGE -- stesso rosso identitario del nodo FORGE nel Nexus, non
# piu' agganciato al tema globale self.accent.
FORGE_ACCENT = NEXUS_NODE_COLOR[3]
# stesso trattamento per UPLINK -- ciano identitario del nodo nel
# Nexus, usato in tutta la sua sotto-sezione (pannelli sync/ftp,
# wifi/bt/hotspot/pcup/basestation e lista deviceremapper/wiredcontroller).
UPLINK_ACCENT = NEXUS_NODE_COLOR[5]
NEXUS_NODE_CODE = {
    0: "RAIL-00",
    3: "RAIL-01α", 5: "RAIL-01β", 2: "RAIL-01γ", 6: "RAIL-01δ",
    10: "RAIL-01ε", 11: "RAIL-01ζ",
    4: "RAIL-02α", 1: "RAIL-02β", 7: "RAIL-02γ", 8: "RAIL-02δ",
    12: "RAIL-02ε", 13: "RAIL-02ζ",
    9: "RAIL-999",
    14: "RAIL-000",
}
# v10.7: targhetta propria (assets/logos/) per la scheda nodo del
# Nexus -- solo i nodi per cui l'asset esiste; gli altri restano con
# icona+nome come prima (vedi _nexus_side_panels).
NEXUS_NODE_BADGE = {
    0: "start",
    1: "muosapps",
    2: "media",
    3: "forge",
    4: "rttoolbox",     # Rt:TOOLBOX
    5: "uplink",
    6: "workshop",
    7: "gear",          # SETTINGS
    8: "book",          # INFO & ABOUT
    9: "power",         # END NODE
    10: "games",
    11: "develop",
    12: "community",
    13: "outerdesk",
    14: "legacy",
}
# v10.3: illustrazioni SPDW per i nodi Nexus, una per icon_key
# (stessa chiave di self.menu_icons / icons.draw). File in
# assets/nexus_planets/. Se un file manca si torna al glifo
# procedurale di icons.draw -- nessun crash, solo meno bello.
NEXUS_PLANET_FILES = {
    "start": "start.png", "window": "muos.png",
    "speaker": "media_vault.png", "forge": "the_forge.png",
    "toolbox": "rt_toolbox.png", "uplink": "net_sphere.png",
    "workshop": "workshop.png", "gear": "settings.png",
    "book": "info.png", "power": "end.png",
    "games": "games.png", "develop": "develop.png",
    "community": "community.png", "outerdesk": "outerdesk.png",
    "legacy": "legacy.png",
}
# v10.7: targhette/loghi SPDW (assets/logos/) -- badge pronti che
# sostituiscono icona+scritta ovunque serva (header, targhetta
# Nexus, tile del toolbox). Se un file manca si torna al vecchio
# icona+testo, stesso pattern di NEXUS_PLANET_FILES: mai un crash,
# solo meno bello finche' non arriva l'asset.
BADGE_FILES = {
    "start": "r00_start_session.png", "forge": "r01a_forge.png",
    "uplink": "r01b_uplink.png", "media": "media_vault.png",
    "workshop": "workshop.png", "muosapps": "r02b_muos_apps.png",
    "rttoolbox": "r02a_rttoolbox.png", "gear": "settings.png",
    "book": "info.png", "power": "end.png",
    "calc": "calc.png", "clock": "clock.png", "notes": "notes.png",
    "cal": "calendar.png", "officert": "officert.png",
    "spdw": "spdw_factory.png", "disc_crusher": "disc_crusher.png",
    "file_grid_diver": "file_grid_diver.png",
    "void_radio": "void_radio.png", "void_cast": "void_cast.png",
    "media_lib": "media_lib.png", "bgm_norm": "bgm_norm.png",
    "cursedev": "cursedev.png", "info": "info.png",
    "manual": "manual.png", "manifesto": "manifest.png",
    "guide": "guide.png", "vd_update": "vd_update.png",
    "games": "games.png", "develop": "develop.png",
    "community": "community.png", "outerdesk": "outerdesk.png",
    "legacy": "legacy.png",
}

# --- [C6] Media Vault Constants ---
MEDIA_VAULT_COLORS = {
    "radio": (80, 220, 200),
    "voidcast": (218, 68, 96),
    "library": (105, 155, 245),
    "bgmnorm": (245, 185, 64),
}

MEDIA_VAULT_SHORT_DESC = {
    "radio": {"it": "Intercetta frequenze radio dal VOID.", "en": "Tune into radio frequencies from the VOID."},
    "voidcast": {"it": "Streaming TV e IPTV dal VOID.", "en": "TV and IPTV streaming from the VOID."},
    "library": {"it": "Esplora la tua collezione multimediale.", "en": "Browse your media collection."},
    "bgmnorm": {"it": "Normalizza il volume delle tracce BGM.", "en": "Normalize BGM track volume."},
}

MEDIA_VAULT_BADGE_KEYS = {
    "radio": "void_radio",
    "voidcast": "void_cast",
    "library": "media_lib",
    "bgmnorm": "bgm_norm",
}

MEDIA_VAULT_PHASE_NONE = None
MEDIA_VAULT_PHASE_INTRO = "intro"
MEDIA_VAULT_PHASE_FLASH = "flash"
MEDIA_VAULT_PHASE_QUADRANTS = "quadrants"

# --- [C4] Home Styles & Clock Layouts ---
# fattore di schiacciamento verticale delle orbite per l'inquadratura
# a 3/4: 1.0 sarebbe un cerchio piatto visto dritto dall'alto, piu'
# si abbassa piu' il "tavolo" si inclina verso chi guarda
NEXUS_SQUASH = 0.46
# VOIDDESK 9.300 "Net-Sphere" -- planetario navigabile: le orbite
# (il sole/START SESSION all'origine, non orbita) sono SEMPRE tutte
# visibili. La zona di selezione resta fissa a sinistra dello
# schermo: e' tutto il planetario che pan-na e si ridimensiona
# (NEXUS_ZOOM, per nodo) per portarci dentro il pianeta scelto.
# NEXUS_ORBIT_SPEED e' in gradi/secondo: piu' vicino al sole, piu'
# veloce, come Keplero. Le orbite media/esterna/lontana sono
# inclinate ciascuna sul proprio piano (NEXUS_OUTER_TILT/
# NEXUS_FAR_TILT) e non sono mai parallele fra loro -- pianeti su
# piani diversi, mai un disco piatto unico.
NEXUS_SELECT_ZONE = (155, 235)
# v10.8: vista satellite (R1 su un nodo che ne ha uno, es. TOOLBOX) --
# stessa scena del planetario ma ri-ancorata a destra e ingrandita,
# invece che nella normale zona di selezione a sinistra.
NEXUS_SAT_ANCHOR = (W - 112, H // 2 + 18)
NEXUS_SAT_ZOOM_MULT = 2.6
# v10.6: orbite ridistanziate ulteriormente (era 145/235) e nuova
# terza orbita, la piu' lontana di tutte, riservata a END NODE.
# v10.14: aggiunta quarta orbita VOID per LEGACY.
NEXUS_RING_RADIUS = {1: 155, 2: 270, 3: 350, 4: 420}
NEXUS_OUTER_TILT = 18
NEXUS_FAR_TILT = -32     # v10.6: END NODE inclinato in senso opposto
                          # all'esterna -- un piano tutto suo, non solo
                          # piu' lontano ma visibilmente storto
NEXUS_VOID_TILT = -45    # v10.14: LEGACY inclinazione estrema
NEXUS_ORBIT_SPEED = {1: 7.0, 2: 3.0, 3: 1.3, 4: 0.5}     # piu' lontano, piu' lento
NEXUS_NODE_R = {
    # orbita media (RAIL-01): RAIL-01 MEDIA e' il pianeta piu'
    # grande dell'orbita, WORKSHOP il piu' piccolo, UPLINK a meta'
    # strada fra i due, FORGE un filo sotto UPLINK
    3: 18, 5: 21, 2: 26, 6: 13, 10: 16, 11: 14,
    4: 15, 1: 14, 7: 13, 8: 13, 12: 12, 13: 16,      # orbita esterna
    9: 6,                                    # END NODE: minuscolo, isolato
    14: 5,                                   # LEGACY: ancora piu' piccolo
}
NEXUS_ZOOM = {                               # v10: zoom aumentato su tutti i nodi
    0: 0.95,                                 # sole: zoom fuori un filo
    3: 1.28, 5: 1.05, 6: 1.75, 2: 1.02, 10: 1.30, 11: 1.20,  # orbita media
    4: 1.45, 1: 1.50, 7: 1.55, 8: 1.55, 12: 1.60, 13: 1.40,  # orbita esterna
    9: 2.10,                                 # END NODE: zoom deciso, e' minuscolo
    14: 3.50,                                # LEGACY: zoom enorme, e' minuscolo
}
# v10.6: decori orbitali sui pianeti di RAIL-01 -- non solo sfere
# colorate, ognuno si porta dietro qualcosa che gli orbita attorno.
# kind: "dust" = anello pieno (come quelli di Saturno), "signal" =
# stesso anello ma a impulsi/trattini (per UPLINK: un segnale
# trasmesso, non detriti), "moonlet" = una piccola luna compagna al
# posto dell'anello (per i nodi troppo piccoli per portarne uno
# intero). Formato: idx -> (kind, inclinazione_gradi, n.fasce,
# tratteggiato).
NEXUS_NODE_DECO = {
    4: ("moonlet", 0, 0, False),   # TOOLBOX: sola luna
}

NEXUS_BG_DEFAULTS = {
    "enabled": False,
    "image_path": "",
    "opacity": 0.6,
    "stars": True,
    "comets": True,
    "nebula": True,
    "orbit_color": (60, 120, 200),
    "orbit_width": 1,
    "orbit_style": "solid",
    "glitch": False,
    "scanlines": False,
    "vignette": True,
}

# v10.8: satelliti selezionabili con R1 da un nodo del Nexus -- indice
# romano, nome, stato-schermata su cui naviga la A. idx -> lista di
# (numero_romano, nome, stato).
NEXUS_SATELLITES = {
      4: [
          ("I", "Outer-Desk", "outerdesk", "remote"),
          ("II", "Deep VOID DESK", "deepvoiddesk", "cube"),
          ("III", "Rt:CORE Switcher", "sgrub", "terminal"),
      ],
      3: [
          ("I", "Void Installer", "installer", "pkg"),
          ("II", "CLI Shooter", "clitools", "terminal"),
      ],
      5: [
          ("I", "Tailscale Console", "tsgui", "uplink"),
          ("II", "Network Probe", "netprobe", "globe"),
      ],
      2: [
          ("I", "Void Radio", "radio", "speaker"),
          ("II", "VoidCast IPTV", "voidcast", "video"),
      ],
      6: [
          ("I", "Void Monitor", "monitor", "task"),
          ("II", "Disc Crusher", "chd", "disk"),
      ],
}
NOTIF_KINDS = {
    # tipo: (colore, icona, etichetta_it, etichetta_en)
    "standard": ((140, 150, 165), "info", "NOTIFICA", "NOTICE"),
    "message": ((60, 200, 210), "monitor", "MESSAGGIO", "MESSAGE"),
    "success": ((90, 205, 130), "info", "COMPLETATO", "DONE"),
    "warning": ((230, 180, 60), "shield", "AVVISO", "WARNING"),
    "urgent": ((230, 110, 50), "shield", "URGENTE", "URGENT"),
    "critical": ((220, 60, 55), "shield", "ALLARME CRITICO",
                "CRITICAL ALARM"),
    "system": ((170, 110, 220), "gear", "SISTEMA VOID", "VOID SYSTEM"),
}

# --- [C6.5] Outer-Desk App Registry // HUB: TOOLBOX Satellite (R1) ---
# Standalone apps launched from the Outer-Desk satellite. Ogni voce ha:
#   key        — identificativo interno (usato per .outdesk_sel)
#   name       — nome display (it/en)
#   icon       — chiave icona vetoriale (icons.draw)
#   logo       — asset logo in assets/logos/ (per lo schermo dettaglio)
#   desc       — descrizione breve (it/en)
#   color      — colore identitario dell'app
#   req        — path relativo a VOIDDESK_BASE del requirements.json
#   script     — path relativo al file python dell'app
#   mux        — path relativo al mux_launch.sh (None = nessun mux)
OUTERDESK_APPS = [
    {
        "key": "portable_forger",
        "name": ("Portable Forger", "Portable Forger"),
        "icon": "forge",
        "logo": "portable_forger.png",
        "desc": ("Gestore dipendenze standalone per app muOS",
                 "Standalone dependency manager for muOS apps"),
        "color": ACCENTS["ambra"],
        "req": "outdesk/Portable_Forger/requirements.json",
        "script": "outdesk/Portable_Forger/portable_forger.py",
        "mux": "outdesk/Portable_Forger/mux_launch.sh",
    },
    {
        "key": "disc_crusher",
        "name": ("Disc Crusher", "Disc Crusher"),
        "icon": "cd_disc",
        "logo": "disc_crusher.png",
        "desc": ("Converti immagini CD in formato CHD",
                 "Convert CD images to CHD format"),
        "color": ACCENTS["ciano"],
        "req": "outdesk/Disc_Crusher/requirements.json",
        "script": "outdesk/Disc_Crusher/discs_crusher.py",
        "mux": "outdesk/Disc_Crusher/mux_launch.sh",
    },
    {
        "key": "ethostore",
        "name": ("Etho$tore", "Etho$tore"),
        "icon": "pkg",
        "logo": "ethostore.png",
        "desc": ("Store di app e giochi per muOS",
                 "App and game store for muOS"),
        "color": ACCENTS["ciano"],
        "req": None,
        "script": "outdesk/EthoStore/ethostore.py",
        "mux": "outdesk/EthoStore/mux_launch.sh",
    },
    {
        "key": "media_player",
        "name": ("Media Player", "Media Player"),
        "icon": "speaker",
        "logo": "media_vault.png",
        "desc": ("Player audio/video standalone per Media Vault",
                 "Standalone audio/video player for Media Vault"),
        "color": NEXUS_NODE_COLOR[2],
        "req": "outdesk/MediaPlayer/requirements.json",
        "script": "outdesk/MediaPlayer/media_player.py",
        "mux": "outdesk/MediaPlayer/mux_launch.sh",
    },
    {
        "key": "image_viewer",
        "name": ("Image Viewer", "Image Viewer"),
        "icon": "image",
        "logo": "media_lib.png",
        "desc": ("Visualizzatore immagini standalone per Media Vault",
                 "Standalone image viewer for Media Vault"),
        "color": NEXUS_NODE_COLOR[2],
        "req": "outdesk/ImageViewer/requirements.json",
        "script": "outdesk/ImageViewer/image_viewer.py",
        "mux": "outdesk/ImageViewer/mux_launch.sh",
    },
    {
        "key": "bootanim_manager",
        "name": ("Boot Anim Manager", "Boot Anim Manager"),
        "icon": "film",
        "logo": None,
        "desc": ("Gestore animazioni di avvio per muOS",
                 "Boot animation manager for muOS"),
        "color": ACCENTS["verde"],
        "req": None,
        "script": "outdesk/BootAnimManager/bootanim_manager.py",
        "mux": None,
    },
    {
        "key": "little_mischief",
        "name": ("Little Mischief", "Little Mischief"),
        "icon": "wifi",
        "logo": "networkprobe.png",
        "desc": ("Suite di penetrazione WiFi per muOS",
                 "WiFi penetration suite for muOS"),
        "color": ACCENTS["cremisi"],
        "req": None,
        "script": "outdesk/Little_Mischief/little_mischief.py",
        "mux": None,
    },
]
OUTERDESK_COLOR = NEXUS_NODE_COLOR[4]

# --- [C6.6] Outer Panel constants ---
OUTER_PANEL_BG = (10, 12, 18)
OUTER_PANEL_BORDER = (60, 200, 210)
OUTER_PANEL_ACCENT = (60, 200, 210)
OUTER_PANEL_TEXT = (230, 240, 250)
OUTER_PANEL_DIM = (140, 150, 160)


# --- [C6] Radio Stations & URL Migrations // HUB: MEDIA VAULT ---
RADIO_BUILTIN = [
    {"name": "SomaFM Groove Salad", "url":
     "https://ice1.somafm.com/groovesalad-128-mp3",
     "tags": "chillout, ambient", "country": "US", "category": "all"},
    {"name": "SomaFM Drone Zone", "url":
     "https://ice1.somafm.com/dronezone-128-mp3",
     "tags": "ambient, atmospheric", "country": "US", "category": "all"},
    {"name": "SomaFM Beat Blender", "url":
     "https://ice1.somafm.com/beatblender-128-mp3",
     "tags": "downtempo, house", "country": "US", "category": "all"},
    {"name": "SomaFM Space Station", "url":
     "https://ice1.somafm.com/spacestation-128-mp3",
     "tags": "electronic, space", "country": "US", "category": "all"},
    {"name": "SomaFM Synphaera", "url":
     "https://ice1.somafm.com/synphaera-128-mp3",
     "tags": "synth, electronic", "country": "US", "category": "all"},
    {"name": "SomaFM Cliqhop IDM", "url":
     "https://ice1.somafm.com/cliqhop-128-mp3",
     "tags": "idm, electronic", "country": "US", "category": "tekno"},
    {"name": "RAI Radio 1", "url":
     "http://icestreaming.rai.it/1.mp3",
     "tags": "news, talk", "country": "IT", "category": "italia"},
    {"name": "RAI Radio 2", "url":
     "http://icestreaming.rai.it/2.mp3",
     "tags": "music, entertainment", "country": "IT", "category": "italia"},
    {"name": "Radio 24", "url":
     "http://shoutcast2.radio24.it:8000/;",
     "tags": "news, business", "country": "IT", "category": "italia"},
    {"name": "Radio Deejay", "url":
     "https://4c4b867c89244861ac216426883d1ad0.msvdn.net/radiodeejay/radiodeejay/master_ma.m3u8",
     "tags": "pop, hits", "country": "IT", "category": "italia"},
    {"name": "Virgin Radio Italia", "url":
     "http://icecast.unitedradio.it/Virgin.mp3",
     "tags": "rock, pop", "country": "IT", "category": "italia"},
    {"name": "Tekno Italia", "url":
     "http://radio.teknoitalia.com:8000/stream",
     "tags": "tekno, free tekno", "country": "IT", "category": "tekno"},
    {"name": "Hardtek.fm", "url":
     "https://stream2.radioking.com/radio/24096/stream/320kbps",
     "tags": "hardtek, rave", "country": "NL", "category": "tekno"},
    {"name": "Noize FM", "url":
     "https://relay.181.fm/stream",
     "tags": "tekno, free tekno", "country": "US", "category": "tekno"},
]
# Preferiti e recenti creati con le versioni precedenti restano utilizzabili
# dopo la sostituzione degli endpoint che i broadcaster hanno dismesso.
RADIO_URL_MIGRATIONS = {
    "http://radiorai.radio1.tc-live1.rai.it/radio1.mp3":
        "http://icestreaming.rai.it/1.mp3",
    "http://radiorai.radio2.tc-live1.rai.it/radio2.mp3":
        "http://icestreaming.rai.it/2.mp3",
    "https://icecast.radio24.it/radio24.mp3":
        "http://shoutcast2.radio24.it:8000/;",
    "https://deejay.ice.infomaniak.ch/deejay-128.mp3":
        "https://4c4b867c89244861ac216426883d1ad0.msvdn.net/radiodeejay/radiodeejay/master_ma.m3u8",
    "https://live.rstream.me/virginradio.mp3":
        "http://icecast.unitedradio.it/Virgin.mp3",
}
RADIO_CACHE_EXPIRY = 86400
CTRL_EXCLUDE_NAMES = ["gpio", "joypad", "power button",
                      "adc joystick", "axp2202", "muos-keys",
                      "direct-keys", "dierct-keys"]
CTRL_PRESETS = [
    ("hdr", "NESSUNO", "NONE"),
    ("custom:none", "Nessuno (personalizzato / disattivo)",
    "None (custom / inactive)"),

    ("hdr", "TASTI CONSOLE", "CONSOLE BUTTONS"),
    ("console:btn_up", "Console: D-pad Su", "Console: D-pad Up"),
    ("console:btn_down", "Console: D-pad Giù", "Console: D-pad Down"),
    ("console:btn_left", "Console: D-pad Sinistra",
    "Console: D-pad Left"),
    ("console:btn_right", "Console: D-pad Destra",
    "Console: D-pad Right"),
    ("console:btn_a", "Console: tasto A", "Console: button A"),
    ("console:btn_b", "Console: tasto B", "Console: button B"),
    ("console:btn_x", "Console: tasto X", "Console: button X"),
    ("console:btn_y", "Console: tasto Y", "Console: button Y"),
    ("console:btn_l1", "Console: L1", "Console: L1"),
    ("console:btn_l2", "Console: L2", "Console: L2"),
    ("console:btn_r1", "Console: R1", "Console: R1"),
    ("console:btn_r2", "Console: R2", "Console: R2"),
    ("console:btn_start", "Console: Start", "Console: Start"),
    ("console:btn_select", "Console: Select", "Console: Select"),
    ("console:btn_menu", "Console: Menu (M)", "Console: Menu (M)"),

    ("hdr", "AZIONI CONSOLE", "CONSOLE ACTIONS"),
    ("console:open_files", "Console: apri File Grid-Diver",
    "Console: open File Grid-Diver"),
    ("console:open_shell", "Console: apri Rt:Shell",
    "Console: open Rt:Shell"),
    ("console:open_radio", "Console: apri Void Radio",
    "Console: open Void Radio"),
    ("console:open_clock", "Console: apri Orologio",
    "Console: open Clock"),
    ("console:open_stats", "Console: apri Device Stats",
    "Console: open Device Stats"),
    ("console:open_notes", "Console: apri Note",
    "Console: open Notes"),
    ("console:open_cal", "Console: apri Calendario",
    "Console: open Calendar"),
    ("console:open_weather", "Console: apri Meteo",
    "Console: open Weather"),
    ("console:open_rss", "Console: apri RSS", "Console: open RSS"),
    ("console:open_calc", "Console: apri Calcolatrice",
    "Console: open Calculator"),
    ("console:open_options", "Console: apri Opzioni",
    "Console: open Options"),
    ("console:media_panel", "Console: apri pannello media",
    "Console: open media panel"),
    ("console:shutdown_menu", "Console: apri menu spegnimento",
    "Console: open shutdown menu"),
    ("console:screenshot", "Console: scatta screenshot",
    "Console: take screenshot"),
    ("console:wifi_toggle", "Console: attiva/disattiva WiFi",
    "Console: toggle WiFi"),
    ("console:vol_up", "Console: volume su",
    "Console: volume up"),
    ("console:vol_down", "Console: volume giù",
    "Console: volume down"),
    ("console:home", "Console: torna al menu principale",
    "Console: back to main menu"),

    ("hdr", "PC (BASESTATION)", "PC (BASESTATION)"),
    ("pc:notify", "PC: invia notifica al Basestation",
    "PC: send notification to Basestation"),
    ("pc:screenshot", "PC: richiedi screenshot al PC",
    "PC: request PC screenshot"),
    ("pc:stats", "PC: mostra statistiche PC",
    "PC: show PC stats"),
]
# lookup rapido O(1) comando -> etichette, usato nel loop di disegno
# (prima si rifaceva una scansione lineare dell'intera lista ad ogni
# riga, ad ogni fotogramma: con 40+ preset ha senso pagarla una volta
# sola qui invece che ripeterla decine di volte al secondo)
CTRL_PRESET_LABELS = {k: (lit, en) for k, lit, en in CTRL_PRESETS
                      if k != "hdr"}
SHUTDOWN_OPTS = [
    ("close", (90, 190, 220), "power"),
    ("restart_app", (230, 180, 60), "gear"),
    ("reboot", (230, 130, 50), "power"),
    ("poweroff", (220, 60, 55), "power"),
    ("cancel", (150, 150, 155), "info"),
]
# v10.9: selezione di END NODE nel planetario Nexus -- niente hub
# normale: il pianeta stesso si illumina di una luce instabile e
# inquietante (pulsa tra viola e verde tossico, mai ferma su un
# colore solo) e sale al centro in alto mentre lo schermo si
# scurisce, restando lui l'unica cosa ben visibile. Sotto di lui un
# raggio della stessa luce illumina, una alla volta, le stesse 4
# azioni di SHUTDOWN_OPTS (esclusa "cancel", che resta sul tasto B
# come ovunque nell'app) disposte in un piccolo carosello che gira
# con SU/GIU'. idx -> (chiave per shutdown_exec, icona, nome IT,
# nome EN, descrizione IT, descrizione EN).
ENDNODE_EERIE_A = (150, 20, 170)   # viola velenoso
ENDNODE_EERIE_B = (35, 205, 95)    # verde tossico -- pulsa tra i due
ENDNODE_ITEMS = [
    ("close", "monitor", "LOG OUT", "LOG OUT",
     "Termina sessione corrente di Void-Desk.",
     "Ends the current Void-Desk session."),
    ("restart_app", "gear", "RESTART", "RESTART",
     "Riavvia l'applicazione Void-Desk.",
     "Restarts the Void-Desk application."),
    ("poweroff", "power", "SHUTDOWN", "SHUTDOWN",
     "Spegne completamente il dispositivo.",
     "Powers off the device completely."),
    ("reboot", "gauge", "REBOOT", "REBOOT",
     "Riavvia il sistema del dispositivo.",
     "Reboots the device's system."),
]
BGM_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma",
           ".opus", ".mp4", ".webm"}
MEDIA_EXTS = BGM_EXTS | {".mkv", ".avi", ".mov", ".m3u", ".m3u8"}
BGM_SAMPLE_RATE = 44100
BGM_OGG_QUALITY = "6"
VERSION = "10.5.0"
VERSION_CODENAME = "D.N"
MENU_DEST_COLORS = [
    (60, 200, 130),   # 0 START SESSION -- verde, avvio
    (230, 190, 50),   # 1 MUOS APPS -- giallo mustard, coerente col brand
    (100, 205, 210),  # 2 MEDIA VAULT -- ciano broadcast
    (225, 95, 40),    # 3 FORGE -- rosso-arancio, le stesse braci vere
    (150, 165, 190),  # 4 TOOLBOX -- acciaio
    (55, 190, 220),   # 5 UPLINK -- ciano, rete
    (165, 105, 215),  # 6 WORKSHOP -- viola, diagnostica
    (195, 180, 155),  # 7 SETTINGS -- beige caldo, neutro
    (215, 215, 225),  # 8 INFO & ABOUT -- argento
    (210, 75, 35),    # 9 SHUTDOWN -- rosso scuro/arancione
    (255, 180, 50),   # 10 GAMES -- oro
    (60, 230, 200),   # 11 DEVELOP -- turchese
    (200, 150, 255),  # 12 COMMUNITY -- lavanda
    (255, 120, 160),  # 13 OUTERDESK — rosa/cielo
    (80, 80, 90),     # 14 LEGACY — grigio scuro (chiusura)
]
NEXUS_NODE_SOUND = {
    0: "nexus",
    1: "snap",
    2: "charge2",
    3: "charge",
    4: "lid_click",
    5: "charge3",
    6: "charge4",
    7: "click",
    8: "page_flip",
    9: "off",
    10: "charge5",
    11: "lid_click",
    12: "snap",
    13: "charge6",
    14: "off",
}
# Ogni universo entra con un accento sonoro differente. Non e' solo un
# click: il suono anticipa il carattere del luogo prima del suo bootanim.
MENU_ENTRY_SOUNDS = ["nexus", "snap", "charge", "charge2", "lid_click",
                     "charge3", "charge4", "click", "page_flip"]
HUB_DESCRIPTIONS = {
    0: {
        "it": "Il cuore pulsante dell'universo Void-Desk: ambienti KLinux Desktop serviti con Mostarda e una Dr. Pepper in lattina.",
        "en": "The beating heart of the Void-Desk universe: KLinux Desktop environments served with mustard and a canned Dr. Pepper.",
    },
    3: {
        "it": "L'officina in cui forgerete il VOSTRO Void-Desk: installer, updater e script runner.",
        "en": "The forge where you will shape YOUR Void-Desk: installers, updaters and script runners.",
    },
    5: {
        "it": "Il ponte di comando per tutte le connessioni: rete wireless, hotspot, Bluetooth, PC link e controller esterni.",
        "en": "The command bridge for all connections: wireless, hotspot, Bluetooth, PC link and external controllers.",
    },
    2: {
        "it": "Il salotto multimediale: radio in streaming, IPTV, libreria di file e normalizzatore audio BGM.",
        "en": "The multimedia lounge: streaming radio, IPTV, file library and BGM audio normalizer.",
    },
    6: {
        "it": "Il laboratorio di manutenzione: statistiche, diagnostica, monitoraggio, analisi storage, boost e backup.",
        "en": "The maintenance lab: stats, diagnostics, monitoring, storage analysis, boost and backup.",
    },
    4: {
        "it": "La cassetta degli attrezzi: calcolatrice, orologio, agenda, note, file manager, FTP, sincronizzazione, terminale, editor e RSS.",
        "en": "The toolbox: calculator, clock, calendar, notes, file manager, FTP, sync, terminal, editor and RSS.",
    },
    1: {
        "it": "Il portale verso le app muOS: scopri, avvia e organizza le tue applicazioni.",
        "en": "The portal to muOS apps: discover, launch and organize your applications.",
    },
    7: {
        "it": "Il centro di controllo: tema, font, effetti, lingua, mappatura controller e avvio.",
        "en": "The control center: theme, fonts, effects, language, controller mapping and boot.",
    },
    8: {
        "it": "L'archivio del progetto: informazioni, manuale, guida rapida, manifesto e aggiornamenti.",
        "en": "The project archive: info, manual, quick guide, manifesto and updates.",
    },
     9: {
         "it": "Ultima fermata.",
         "en": "Final stop.",
     },
     10: {
         "it": "Il catalogo dei giochi nativi e porting per muOS.",
         "en": "The catalogue of native games and ports for muOS.",
     },
     11: {
         "it": "L'officina dello sviluppatore: Python REPL, editor, strumenti.",
         "en": "The developer workshop: Python REPL, editor, tools.",
     },
     12: {
         "it": "La piazza della community: forum, wiki, condivisione.",
         "en": "The community square: forums, wiki, sharing.",
     },
     13: {
         "it": "Il modulo Outer-Desk: app standalone e strumenti portatili.",
         "en": "The Outer-Desk module: standalone apps and portable tools.",
     },
     14: {
         "it": "L'ultima orbita. La fine di un ciclo.",
         "en": "The final orbit. The end of a cycle.",
     },
}
GITHUB_REPO = "SilverCrow2323/muOS-Void-Desk"
# gruppi tematici del Rt:Toolbox: (titolo IT, titolo EN, icona sezione,
# quante voci ci stanno, stile del widget) -- l'ordine deve combaciare
# con l'ordine delle voci in HUBS["toolbox"]
TOOLBOX_GROUPS = [
    ("PRODUTTIVITA'", "PRODUCTIVITY", "calc", 4, "grid2"),
    ("RETE E FILE", "NETWORK & FILES", "folder", 3, "row3"),
    ("SVILUPPO", "DEVELOPMENT", "terminal", 3, "row3"),
]
# v10.7: voci del toolbox che hanno una targhetta propria in
# assets/logos/ -- la tile la mostra al posto di icona+scritta. Le
# altre voci (senza asset ancora) restano come sempre.
TILE_BADGE = {
    "calc": "calc", "clockmain": "clock", "cal": "cal",
    "notes": "notes", "fileman": "file_grid_diver",
}
MAPP_VIEWS = ["list", "grid", "compact", "detailed"]
ALARM_SOUNDS = ["classic", "digital", "gentle"]

CALC_KEYS = [
    ["7", "8", "9", "/", "sin", "cos"],
    ["4", "5", "6", "*", "tan", "log"],
    ["1", "2", "3", "-", "ln", "sqrt"],
    ["0", ".", "(", ")", "+", "^"],
    ["pi", "e", "ans", "C", "<", "="],
]
CALC_BASIC_KEYS = [
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "C", "+"],
]
CALC_SUBJECTS = [
    ("TRIGONOMETRIA", (70, 195, 225), [
        ["sin", "cos", "tan"], ["asin", "acos", "atan"]]),
    ("LOGARITMI", (230, 180, 60), [
        ["log", "ln", "exp"], ["log2", "sinh", "cosh"]]),
    ("COSTANTI", (175, 115, 225), [
        ["pi", "e", "phi"], ["tau", "ans", "C"]]),
    ("POTENZE", (100, 210, 120), [
        ["**2", "**3", "sqrt("], ["**(1/3)", "1/(", "factorial("]]),
    ("PROGRAMMATORE", (225, 110, 120), [
        ["%", "//", "abs("], ["floor(", "ceil(", "round("]]),
]
CALC_LAYOUTS = ["basic", "scientific", "rintro"]
MANUAL = [
    ("intro", "info"), ("sessions", "start"), ("forge", "forge"),
    ("mapps", "window"), ("media", "speaker"), ("workshop", "workshop"),
    ("uplink", "uplink"), ("toolbox", "toolbox"), ("controller", "gamepad"),
    ("live", "panel"), ("trouble", "gear"), ("nexus", "start"),
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


# --- [C7] Notification Kinds & Colors ---
def comp_color(c):
    """Complementare del tema, alzato se troppo scuro su fondo nero."""
    r, g, b = 255 - c[0], 255 - c[1], 255 - c[2]
    if r + g + b < 250:
        r, g, b = min(255, r + 90), min(255, g + 90), min(255, b + 90)
    return (r, g, b)


TS_BIN = os.environ.get("VD_TS_BIN", "/opt/muos/bin/tailscale")
TS_SOCK = os.environ.get("VD_TS_SOCK", "/run/tailscale/tailscaled.sock")
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


# --- [C8] RSS Categories & Feed Library // HUB: RT:TOOLBOX ---
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
WX_COUNTRY_CODES = {
    "Italy": "IT", "Italia": "IT", "United States": "US",
    "United Kingdom": "GB", "France": "FR", "Germany": "DE",
    "Spain": "ES", "Japan": "JP", "China": "CN", "Russia": "RU",
    "Canada": "CA", "Brazil": "BR", "Mexico": "MX", "India": "IN",
    "Australia": "AU", "Netherlands": "NL", "Belgium": "BE",
    "Switzerland": "CH", "Austria": "AT", "Sweden": "SE",
    "Norway": "NO", "Denmark": "DK", "Finland": "FI", "Poland": "PL",
    "Portugal": "PT", "Greece": "GR", "Turkey": "TR", "Egypt": "EG",
    "South Africa": "ZA", "South Korea": "KR", "North Korea": "KP",
    "Argentina": "AR", "Chile": "CL", "Ireland": "IE",
    "New Zealand": "NZ", "Thailand": "TH", "Vietnam": "VN",
    "Indonesia": "ID", "Philippines": "PH", "Singapore": "SG",
    "Malaysia": "MY", "Israel": "IL", "Saudi Arabia": "SA",
    "United Arab Emirates": "AE", "Ukraine": "UA", "Iceland": "IS",
    "Czechia": "CZ", "Czech Republic": "CZ", "Hungary": "HU",
    "Romania": "RO", "Croatia": "HR", "Slovenia": "SI",
}


def wx_country_code(name):
    return WX_COUNTRY_CODES.get(name, (name or "??")[:2].upper())


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
RUNTIME_DIR = os.path.join(APP_DIR, "runtime")
TEXTS_DIR = os.path.join(DATA, "Texts")
PYSCRIPTS_DIR = os.path.join(DATA, "PythonScripts")
TEXT_EXTS = {".txt", ".md", ".log", ".cfg", ".ini", ".json", ".csv",
            ".yml", ".yaml", ".sh", ".conf", ".xml"}
for _d in (TEXTS_DIR, PYSCRIPTS_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except OSError:
        pass
LOGS_DIR = os.path.join(DATA, "logs")
try:
    os.makedirs(LOGS_DIR, exist_ok=True)
except OSError:
    pass
LOG = os.path.join(LOGS_DIR, "voiddesk.log")
RADIO_BROWSER_BASE = "https://de1.api.radio-browser.info/json"
RADIO_BROWSER_SEARCH = f"{RADIO_BROWSER_BASE}/stations/search"
RADIO_BROWSER_COUNTRIES = f"{RADIO_BROWSER_BASE}/countries"
RADIO_BROWSER_LANGUAGES = f"{RADIO_BROWSER_BASE}/languages"
RADIO_BROWSER_TAGS = f"{RADIO_BROWSER_BASE}/tags"
RADIO_CACHE_FILE = os.path.join(DATA, "radio_cache.json")
RADIO_CACHE_EXPIRY = 86400
FONT_PATH = os.path.join(APP_DIR, "assets", "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(APP_DIR, "assets", "DejaVuSans-Bold.ttf")
FONT_MONO_PATH = os.path.join(APP_DIR, "assets", "JetBrainsMono-Regular.ttf")
FONT_MONO_BOLD_PATH = os.path.join(APP_DIR, "assets",
                                   "JetBrainsMono-Bold.ttf")
FONT_DISPLAY_PATH = os.path.join(APP_DIR, "assets", "font",
                                 "oxanium", "Oxanium-ExtraBold.ttf")
FONT_OXANIUM_REGULAR_PATH = os.path.join(APP_DIR, "assets", "font",
                                         "oxanium", "Oxanium-Regular.ttf")
FONT_OXANIUM_BOLD_PATH = os.path.join(APP_DIR, "assets", "font",
                                      "oxanium", "Oxanium-Bold.ttf")

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

# --- [C9] Weather WMO Codes & Country Mapping // HUB: RT:TOOLBOX ---
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
  ("mame-tools (chdman)", "mame-tools", "conversione immagini disco CHD",
   "usr/bin/chdman", "disk"),
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

# --- [C10] Catalog Components (Void Installer APT Catalogue) // HUB: FORGE ---
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
    "RETE / SVILUPPO": "NETWORK / DEV", "STRUMENTI / CLI": "CLI SHOOTER",
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

# Import jsmap locally to get pad information
try:
    import jsmap
    PAD_PATH, PAD_KEYS = jsmap.find_pad()
    EV2QJ = jsmap.ev_to_qj(PAD_KEYS) if PAD_KEYS else {}
except Exception:
    # Fallback if jsmap fails (e.g., no pad detected)
    PAD_PATH, PAD_KEYS = None, None
    EV2QJ = {}


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

# Nomi leggibili per i segnali grezzi di un dispositivo HID esterno
# (tastiera USB, gamepad generico): solo per la resa a schermo nel
# Controller Hub -- il confronto vero, ovunque, resta sempre sul
# codice numerico grezzo dentro la stringa "hid:N" / "midi:note:...".
HID_KEY_NAMES = dict(KNOWN_NAMES)
HID_KEY_NAMES.update({
    1: "ESC", 14: "BACKSPACE", 15: "TAB", 28: "ENTER", 29: "CTRL",
    42: "SHIFT", 54: "SHIFT", 56: "ALT", 57: "SPACE", 58: "CAPS",
    100: "ALT", 97: "CTRL",
    2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8",
    10: "9", 11: "0",
    16: "Q", 17: "W", 18: "E", 19: "R", 20: "T", 21: "Y", 22: "U",
    23: "I", 24: "O", 25: "P",
    30: "A", 31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J",
    37: "K", 38: "L",
    44: "Z", 45: "X", 46: "C", 47: "V", 48: "B", 49: "N", 50: "M",
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6",
    65: "F7", 66: "F8", 67: "F9", 68: "F10", 87: "F11", 88: "F12",
    102: "HOME", 103: "UP", 104: "PAGEUP", 105: "LEFT", 106: "RIGHT",
    107: "END", 108: "DOWN", 109: "PAGEDOWN", 110: "INS", 111: "DEL",
    113: "MUTE", 114: "VOL-", 115: "VOL+", 116: "POWER",
})
MIDI_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#",
                   "A", "A#", "B"]


def ctrl_sig_label(sig):
    """Etichetta leggibile per un segnale raw ('hid:304' -> 'A', una
    nota MIDI -> 'C#4 ch1'): solo estetica, non tocca mai il confronto
    vero che resta sulla stringa grezza salvata nel binding."""
    if not sig:
        return "?"
    if sig.startswith("hid:"):
        try:
            code = int(sig[4:])
        except ValueError:
            return sig
        return HID_KEY_NAMES.get(code, "HID %d" % code)
    if sig.startswith("midi:note:"):
        parts = sig.split(":")
        try:
            note = int(parts[2])
            ch = parts[3][2:] if len(parts) > 3 else "?"
        except (IndexError, ValueError):
            return sig
        return "%s%d ch%s" % (MIDI_NOTE_NAMES[note % 12],
                              note // 12 - 1, ch)
    return sig


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
  "title_comp": "VOID INSTALLER", "title_info": "INFO",
  "title_logs": "LOGS & ABOUT", "title_opts": "OPZIONI",
  "checking": "controllo in corso...",
  "need_xfce": "Prima installa il desktop XFCE (voce in alto nel menu).",
  "opt_theme": "Tema colore", "opt_home_style": "Stile menu principale",
  "opt_font_scale": "Dimensione testo",
  "opt_vfx_bg": "Sfondo animato", "opt_vfx_trans": "Transizioni",
  "opt_vfx_fx": "Effetti schermo",
   "opt_lang": "Lingua",
   "opt_dlang": "Lingua desktop", "opt_dlang_s": "solo gli ambienti, non l'app",
  "opt_ctrl": "Profilo controller", "opt_batt": "Batteria nell'header",
  "opt_st_clock": "Orologio nell'header",
  "opt_st_batt": "Icona batteria", "opt_st_vol": "Icona volume",
  "opt_st_bt": "Icona bluetooth", "opt_st_wifi": "Icona wifi",
  "opt_st_usb": "Icona USB/ADB",
  "opt_st_hotspot": "Icona hotspot",
   "opt_intro": "Sigla d'avvio",
   "opt_nexus_bg": "Sfondo Nexus",
   "opt_nexus_bg_s": "personalizza lo sfondo del planetario",
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
  "media": "MEDIA VAULT", "media_s": "radio, IPTV, libreria e normalizzazione BGM",
  "mapps_t": "MUOS APPS", "mapps_none": "nessuna app in MUOS/application",
  "mapps_scan": "scansione e sistemazione glyph...",
  "mapps_go": "avvia", "mapps_r1": "glyph+scan",
  "h_forge": "THE FORGE", "h_forge_s": "installer, avvio al boot, update",
  "h_work": "WORKSHOP", "h_work_s": "stats, diagnosi, log, memorie, boost",
   "h_up": "UPLINK", "h_up_s": "rete, sincronizzazione, FTP, Tailnet e controller",
  "h_media": "MEDIA VAULT",
  "m_radio": "Void Radio", "m_radio_s": "stazioni live e preferiti",
  "m_iptv": "VoidCast IPTV", "m_iptv_s": "M3U, EPG, guida TV e PVR",
  "m_lib": "Media Library", "m_lib_s": "audio, video e playlist sulla SD",
  "m_bgm": "BGM Normalizer", "m_bgm_s": "LUFS, conversione e pulizia tracce",
  "h_tool": "Rt:TOOLBOX", "h_tool_s": "terminale, calcolatrice, utility",
  "h_info": "INFO & ABOUT", "h_info_s": "progetto, manuale, guida rapida",
  "h_set": "SETTINGS", "h_set_s": "aspetto, audio, lingua dell'app",
  "h_exit": "END NODE", "h_exit_s": "torna a muOS",
  "f_inst": "Void Installer", "f_inst_s": "installa e rimuovi (L1: tab)",
  "f_auto": "Avvio al boot", "f_auto_s": "app che partono col desktop",
  "f_upd": "Update Environments", "f_upd_s": "apt update + upgrade",
  "f_vdupd": "Void-Desk Update", "f_vdupd_s": "aggiorna l'app da GitHub",
  "f_cli": "CLI Shooter", "f_cli_s": "roba simpatica da terminale",
  "w_stats": "Device Stats", "w_stats_s": "il quadro completo del sistema",
  "w_diag": "Void Diag", "w_diag_s": "salute di immagine e sessioni",
  "w_sto": "Memorie", "w_sto_s": "partizioni, spazio, cosa occupa",
  "w_boost": "Chou Henka", "w_boost_s": "swap e governor, separati",
  "w_chd": "Disc Crusher", "w_chd_s": "converti immagini disco in CHD",
  "w_dop": "Doppel-Defender", "w_dop_s": "trova ed elimina ROM doppie",
  "w_clean": "Pulisci cache apt", "w_clean_s": "recupera spazio",
  "w_logs": "Registro log", "w_logs_s": "tutti i diari, per area",
  "t_clock": "Clock", "t_clock_s": "digitale o analogico, con sveglie",
  "u_dlang": "Lingua desktop", "u_dlang_s": "solo gli ambienti, non l'app",
  "u_cthub": "Controller Hub", "u_cthub_s": "dispositivi USB/MIDI, profili e mappature",
  "h_cthub": "CONTROLLER HUB",
  "u_devs": "Controller esterni", "u_devs_s": "Korg, tastiere USB, comandi personalizzati",
  "u_kmb": "Layout tastiera schermo", "u_kmb_s": "matchbox-keyboard",
  "u_kx": "Layout tastiera fisica", "u_kx_s": "se ne colleghi una USB",
  "u_ctrl": "Profilo controller", "u_ctrl_s": "stick e mappatura mouse",
  "u_map": "Mappatura tasti", "u_map_s": "ridefinisci i pulsanti",
  "u_wifi": "WiFi", "u_wifi_s": "gestore completo: scan e connetti",
  "u_bt": "Bluetooth", "u_bt_s": "gestore completo: pair e connetti",
  "u_pcup": "PC Uplink", "u_pcup_s": "stats e notifiche col tuo PC",
  "u_base": "BaseStation Web", "u_base_s": "server web, trasferimento file e companion PC",
   "u_netdiag": "Network Probe", "u_netdiag_s": "internet, indirizzo e diagnostica collegamento",
   "u_ts": "Tailnet Console", "u_ts_s": "rete privata, peer, file e QR login",
   "u_sync": "Syncthing", "u_sync_s": "sincronizza file e cartelle",
   "u_ftp": "FTPiercer", "u_ftp_s": "client FTP con profili",
   "u_devmap": "Device Remapper", "u_devmap_s": "mappatura tasti e controller",
   "u_wired": "Wired Controller", "u_wired_s": "gestione controller esterni USB/MIDI",
  "u_hot": "Hotspot", "u_hot_s": "rileva e usa lo script muOS",
  "t_sh": "Rt:Shell", "t_sh_s": "terminale veloce, host diretto",
  "t_calc": "Calcolatrice", "t_calc_s": "scientifica, nativa Void",
  "t_fm": "File Grid-Diver", "t_fm_s": "esplora, tuffati nella griglia",
  "t_mc": "Midnight Commander", "t_mc_s": "file manager da terminale",
  "t_ftp": "FTP", "t_ftp_s": "client FTP nativo, con profili",
  "t_ed": "Editor di testo", "t_ed_s": "VOID EDIT: apri e modifica qui",
  "t_sync": "Syncthing", "t_sync_s": "pannello nativo via REST",
  "t_cal": "Calendario", "t_cal_s": "eventi: data, ora, priorita'",
  "t_note": "Note", "t_note_s": "appunti rapidi: scrivi e via",
  "t_rss": "RSS Reader", "t_rss_s": "notizie, tech, anime: eng + ita",
  "t_wx": "Meteo", "t_wx_s": "città monitorate, previsioni settimanali",
  "t_radio": "Void Radio", "t_radio_s": "stazioni internet, ricerca live",
  "t_bgm": "BGM Normalizer", "t_bgm_s": "normalizza il volume delle musiche",
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
  "i_update": "Void Desk Update", "i_update_s": "versione, novità, release",
  "installed": "installato", "notinst": "non installato - A: installa",
  "opens_desk": "si apre nel desktop: la trovi nel menu applicazioni",
  "tab_inst": "TAB: INSTALLA", "tab_rm": "TAB: RIMUOVI",
  "gov": "Governor", "glyphp": "Change Glyph", "arch": "Archivia (.muxapp)",
  "removeapp": "Rimuovi app", "sysapp": "APP DI SISTEMA",
  "k_ab_yn": "A: si'   B: no",
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
   "no_b": "B = annulla", "shell_hint": "SELECT esce",
   "opt_map": "Mappatura tasti", "title_map": "MAPPATURA TASTI",
   "map_stick": "Mouse sullo stick", "press": "PREMI IL TASTO DA ASSEGNARE A:",
   "press_s": "attendi 5 secondi per annullare",
   "used_by": "Il tasto %s e' gia' usato da: %s",
   "swap_q": "A = scambia le due funzioni     B = annulla",
   "assign": "assegna", "reset": "ripristina", "reset_all": "tutti default",
   "none": "(nessuno)",
   "radio_update": "Aggiorna catalogo",
   "radio_filter_country": "Paese",
   "radio_filter_language": "Lingua",
   "radio_filter_genre": "Genere",
    "radio_no_results": "Nessuna stazione trovata",
    "radio_loading": "Caricamento stazioni...",
    "radio_custom_tab": "PERSONALI",
    "radio_custom_add": "Aggiungi stazione",
    "radio_custom_del": "Rimuovi stazione",
    "radio_import_title": "Importa da M3U",
    "radio_import_select": "seleziona playlist",
    "radio_import_channels": "Canali",
    "radio_custom_url": "URL personalizzato",
    "rss_export_opml": "Esporta OPML",
   "rss_import_opml": "Importa OPML",
   "rss_import_filter": "File OPML (*.opml)",
   "cursedev_title": "CURSE DEV",
   "cursedev_cat_general": "Generali",
   "cursedev_cat_nexus": "Nexus",
   "cursedev_cat_sfx": "Suoni",
   "cursedev_cat_vfx": "Effetti Visivi",
   "cursedev_cat_details": "Dettagli",
   "cursedev_cat_user": "Utente",
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
  "title_comp": "VOID INSTALLER", "title_info": "INFO",
  "title_logs": "LOGS & ABOUT", "title_opts": "SETTINGS",
  "checking": "checking...",
  "need_xfce": "Install the XFCE desktop first (top menu entry).",
  "opt_theme": "Colour theme", "opt_home_style": "Main menu style",
  "opt_font_scale": "Text size",
  "opt_vfx_bg": "Animated background", "opt_vfx_trans": "Transitions",
  "opt_vfx_fx": "Screen effects",
   "opt_lang": "Language",
   "opt_dlang": "Desktop language", "opt_dlang_s": "desktops only, not the app",
  "opt_ctrl": "Controller profile", "opt_batt": "Status bar icons",
  "opt_st_clock": "Clock in header",
  "opt_st_batt": "Battery icon", "opt_st_vol": "Volume icon",
  "opt_st_bt": "Bluetooth icon", "opt_st_wifi": "WiFi icon",
  "opt_st_usb": "USB/ADB icon",
  "opt_st_hotspot": "Hotspot icon",
   "opt_intro": "Intro animation",
   "opt_nexus_bg": "Nexus background",
   "opt_nexus_bg_s": "customize the planetarium background",
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
  "media": "MEDIA VAULT", "media_s": "radio, IPTV, library and BGM normalization",
  "mapps_t": "MUOS APPS", "mapps_none": "no apps in MUOS/application",
  "mapps_scan": "scanning and fixing glyphs...",
  "mapps_go": "launch", "mapps_r1": "glyph+scan",
  "h_forge": "THE FORGE", "h_forge_s": "installer, startup apps, update",
  "h_work": "WORKSHOP", "h_work_s": "stats, diagnostics, logs, storage",
   "h_up": "UPLINK", "h_up_s": "network, sync, FTP, Tailnet and controllers",
  "h_media": "MEDIA VAULT",
  "m_radio": "Void Radio", "m_radio_s": "live stations and favorites",
  "m_iptv": "VoidCast IPTV", "m_iptv_s": "M3U, EPG, TV guide and PVR",
  "m_lib": "Media Library", "m_lib_s": "audio, video and SD playlists",
  "m_bgm": "BGM Normalizer", "m_bgm_s": "LUFS, conversion and track cleanup",
  "h_tool": "Rt:TOOLBOX", "h_tool_s": "terminal, calculator, utilities",
  "h_info": "INFO & ABOUT", "h_info_s": "project, manual, quick guide",
  "h_set": "SETTINGS", "h_set_s": "look, audio, app language",
  "h_exit": "END NODE", "h_exit_s": "back to muOS",
  "f_inst": "Void Installer", "f_inst_s": "install & remove (L1: tab)",
  "f_auto": "Startup apps", "f_auto_s": "apps that boot with the desktop",
  "f_upd": "Update Environments", "f_upd_s": "apt update + upgrade",
  "f_vdupd": "Void-Desk Update", "f_vdupd_s": "update the app from GitHub",
  "f_cli": "CLI Shooter", "f_cli_s": "fun stuff for the terminal",
  "w_stats": "Device Stats", "w_stats_s": "the full system picture",
  "w_diag": "Void Diag", "w_diag_s": "image and session health",
  "w_sto": "Storage", "w_sto_s": "partitions, space, what fills it",
  "w_boost": "Chou Henka", "w_boost_s": "swap and governor, split",
  "w_chd": "Disc Crusher", "w_chd_s": "convert disc images to CHD",
  "w_dop": "Doppel-Defender", "w_dop_s": "find and remove duplicate ROMs",
  "w_clean": "Clean apt cache", "w_clean_s": "reclaim space",
  "w_logs": "Log registry", "w_logs_s": "every diary, by area",
  "t_clock": "Clock", "t_clock_s": "digital or analog, with alarms",
  "u_dlang": "Desktop language", "u_dlang_s": "desktops only, not the app",
  "u_cthub": "Controller Hub", "u_cthub_s": "USB/MIDI devices, profiles and mappings",
  "h_cthub": "CONTROLLER HUB",
  "u_devs": "External controllers", "u_devs_s": "Korg, USB keyboards, custom commands",
  "u_kmb": "On-screen kbd layout", "u_kmb_s": "matchbox-keyboard",
  "u_kx": "Physical kbd layout", "u_kx_s": "if you plug a USB one",
  "u_ctrl": "Controller profile", "u_ctrl_s": "stick and mouse mapping",
  "u_map": "Button mapping", "u_map_s": "redefine the pads",
  "u_wifi": "WiFi", "u_wifi_s": "full manager: scan and join",
  "u_bt": "Bluetooth", "u_bt_s": "full manager: pair and connect",
  "u_pcup": "PC Uplink", "u_pcup_s": "live stats and notifications",
  "u_base": "BaseStation Web", "u_base_s": "web server, file transfer and PC companion",
   "u_netdiag": "Network Probe", "u_netdiag_s": "internet, address and connection diagnostics",
   "u_ts": "Tailnet Console", "u_ts_s": "private network, peers, files and QR login",
   "u_sync": "Syncthing", "u_sync_s": "sync files and folders",
   "u_ftp": "FTPiercer", "u_ftp_s": "FTP client with profiles",
   "u_devmap": "Device Remapper", "u_devmap_s": "keys and controller mapping",
   "u_wired": "Wired Controller", "u_wired_s": "USB/MIDI external controller management",
  "u_hot": "Hotspot", "u_hot_s": "detects and drives the muOS script",
  "t_sh": "Rt:Shell", "t_sh_s": "fast terminal, direct on host",
  "t_calc": "Calculator", "t_calc_s": "scientific, Void-native",
  "t_fm": "File Grid-Diver", "t_fm_s": "browse, dive the grid",
  "t_mc": "Midnight Commander", "t_mc_s": "terminal file manager",
  "t_ftp": "FTP", "t_ftp_s": "native FTP client, with profiles",
  "t_ed": "Text editor", "t_ed_s": "VOID EDIT: open and edit here",
  "t_sync": "Syncthing", "t_sync_s": "native panel via REST",
  "t_cal": "Calendar", "t_cal_s": "events: date, time, priority",
  "t_note": "Notes", "t_note_s": "quick notes: jot and go",
  "t_rss": "RSS Reader", "t_rss_s": "news, tech, anime: eng + it",
  "t_wx": "Weather", "t_wx_s": "monitored cities, weekly forecast",
  "t_radio": "Void Radio", "t_radio_s": "internet stations, live search",
  "t_bgm": "BGM Normalizer", "t_bgm_s": "normalize background music volume",
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
  "i_update": "Void Desk Update", "i_update_s": "version, news, releases",
  "installed": "installed", "notinst": "not installed - A: install",
  "opens_desk": "opens in the desktop: find it in the app menu",
  "tab_inst": "TAB: INSTALL", "tab_rm": "TAB: REMOVE",
  "gov": "Governor", "glyphp": "Change Glyph", "arch": "Archive (.muxapp)",
  "removeapp": "Remove app", "sysapp": "SYSTEM APP",
  "k_ab_yn": "A: yes   B: no",
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
    "no_b": "B = cancel", "shell_hint": "SELECT quits",
   "radio_update": "Update catalog",
   "radio_filter_country": "Country",
   "radio_filter_language": "Language",
   "radio_filter_genre": "Genre",
    "radio_no_results": "No stations found",
    "radio_loading": "Loading stations...",
    "radio_custom_tab": "CUSTOM",
    "radio_custom_add": "Add station",
    "radio_custom_del": "Remove station",
    "radio_import_title": "Import from M3U",
    "radio_import_select": "select playlist",
    "radio_import_channels": "Channels",
    "radio_custom_url": "Custom URL",
    "rss_export_opml": "Export OPML",
   "rss_import_opml": "Import OPML",
   "rss_import_filter": "OPML files (*.opml)",
   "cursedev_title": "CURSE DEV",
   "cursedev_cat_general": "General",
   "cursedev_cat_nexus": "Nexus",
   "cursedev_cat_sfx": "Sounds",
   "cursedev_cat_vfx": "Visual Effects",
   "cursedev_cat_details": "Details",
   "cursedev_cat_user": "User",
  },

}
