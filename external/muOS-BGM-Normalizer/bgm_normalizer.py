#!/usr/bin/env python3
"""
SPDW BGM Normalizer v8.6 - DEFINITIVE EDITION
==============================================
SDL2 GUI for muOS - RG35XX H / RG40XXV & PC
- Header Anime-style: Massive BGM + Pixel Normalizer Box
- Glitch FX: Vertical lines, subtle edge flow
- About: Optimized layout (fixed spacing)
- Pure Vector Primitive SDL2 Icons (VoidDesk inspiration)
- External Multilingual Support (lang.json)

SPDW Factory Lab - Normalize your world. One track at a time.
"""

import ctypes
import ctypes.util
import subprocess
import os
import sys
import json
import threading
import time
import datetime
import re
import math
import random

APP_VERSION = "8.6"
APP_NAME = "BGM Normalizer"

# =============================================================================
# PATHS & PLATFORM
# =============================================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(APP_DIR, "spdw_bgm_normalizer.log")
LANG_FILE = os.path.join(APP_DIR, "lang.json")

# --- FONT PATHS (Multi-Font Anime Header) ---
FONT_REGULAR = os.path.join(APP_DIR, "font.ttf")
FONT_BGM = os.path.join(APP_DIR, "fontbgm.ttf")
FONT_NORM = os.path.join(APP_DIR, "fontnorm.ttf")

# =============================================================================
# PLATFORM DETECTION
# =============================================================================
IS_MUOS = os.path.exists("/mnt/mmc") and os.path.exists("/opt/muos")
IS_PC = not IS_MUOS

BRAND = "SPDW"
FACTORY = "SPDW Factory"

SD1_INPUT = "/mnt/mmc/MUOS/music"
SD1_OUTPUT = "/mnt/mmc/MUOS/music"
SD2_INPUT = "/mnt/sdcard/MUOS/music"
SD2_OUTPUT = "/mnt/sdcard/MUOS/music"

DEFAULT_PC_INPUT = os.path.expanduser("~/Music/BGM")
DEFAULT_PC_OUTPUT = os.path.expanduser("~/Music/BGM_Normalized")

PRESETS_LUFS = [
    ("-14.0 LUFS (muOS / BGM Standard)", -14.0),
    ("-12.0 LUFS (Retro Handheld / Loud)", -12.0),
    ("-10.0 LUFS (Punchy High-Volume)", -10.0),
    ("-23.0 LUFS (EBU R128 TV Broadcast)", -23.0),
]

TARGET_LUFS = -14.0
SAMPLE_RATE = 44100
OGG_QUALITY = "6"
SUPPORTED_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".mp4", ".webm"}

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{0}] {1}\n".format(timestamp, msg)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
            f.flush()
    except Exception:
        pass

log("=" * 60)
log("SPDW BGM Normalizer v8.6 DEFINITIVE STARTED")

# =============================================================================
# LOCALIZATION ENGINE
# =============================================================================
TRANSLATIONS = {}

def load_translations():
    global TRANSLATIONS
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                TRANSLATIONS = json.load(f)
                log("Loaded external translations from lang.json")
                return
        except Exception as e:
            log("Error loading lang.json: {0}".format(e))

load_translations()

# =============================================================================
# GRAPHICAL FOLDER PICKER FOR PC
# =============================================================================
def pick_folder_gui(title="Select Folder", initialdir=""):
    if not IS_PC:
        return None
    init_path = initialdir if (initialdir and os.path.exists(initialdir)) else os.path.expanduser("~")

    try:
        cmd = ["zenity", "--file-selection", "--directory", "--title=" + title, "--filename=" + init_path + "/"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title=title, initialdir=init_path)
        root.destroy()
        if folder:
            return folder
    except Exception:
        pass

    return None

# =============================================================================
# AUDIO PREVIEW PLAYER
# =============================================================================
class AudioPreviewPlayer:
    def __init__(self):
        self.proc = None
        self.current_file = None
        self.is_playing = False

    def play(self, filepath):
        self.stop()
        if not os.path.exists(filepath):
            return
        self.current_file = filepath
        self.is_playing = True
        t = threading.Thread(target=self._play_thread, args=(filepath,), daemon=True)
        t.start()

    def _play_thread(self, filepath):
        try:
            cmd = ["ffplay", "-nodisp", "-autoexit", "-ss", "0", "-t", "15", filepath]
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.proc.wait()
        except Exception as e:
            log("Preview player error: {0}".format(e))
        finally:
            self.is_playing = False
            self.current_file = None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.is_playing = False
        self.current_file = None

PLAYER = AudioPreviewPlayer()

# =============================================================================
# SDL2 Structures & Setup
# =============================================================================
class SDL_Rect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("w", ctypes.c_int), ("h", ctypes.c_int)]

class SDL_Color(ctypes.Structure):
    _fields_ = [("r", ctypes.c_uint8), ("g", ctypes.c_uint8), ("b", ctypes.c_uint8), ("a", ctypes.c_uint8)]

class SDL_Event(ctypes.Union):
    class _key(ctypes.Structure):
        class _keysym(ctypes.Structure):
            _fields_ = [("scancode", ctypes.c_int), ("sym", ctypes.c_int), ("mod", ctypes.c_uint16), ("unused", ctypes.c_uint32)]
        _fields_ = [("type", ctypes.c_uint32), ("timestamp", ctypes.c_uint32), ("windowID", ctypes.c_uint32),
                    ("state", ctypes.c_uint8), ("repeat", ctypes.c_uint8), ("padding2", ctypes.c_uint8),
                    ("padding3", ctypes.c_uint8), ("keysym", _keysym)]
    class _jbutton(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint32), ("timestamp", ctypes.c_uint32), ("which", ctypes.c_int32),
                    ("button", ctypes.c_uint8), ("state", ctypes.c_uint8), ("padding1", ctypes.c_uint8), ("padding2", ctypes.c_uint8)]
    class _jaxis(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint32), ("timestamp", ctypes.c_uint32), ("which", ctypes.c_int32),
                    ("axis", ctypes.c_uint8), ("padding1", ctypes.c_uint8), ("padding2", ctypes.c_uint8),
                    ("padding3", ctypes.c_uint8), ("value", ctypes.c_int16), ("padding4", ctypes.c_uint16)]
    class _jhat(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint32), ("timestamp", ctypes.c_uint32), ("which", ctypes.c_int32),
                    ("hat", ctypes.c_uint8), ("value", ctypes.c_uint8), ("padding1", ctypes.c_uint8), ("padding2", ctypes.c_uint8)]
    _fields_ = [("type", ctypes.c_uint32), ("key", _key), ("jbutton", _jbutton), ("jaxis", _jaxis), ("jhat", _jhat), ("padding", ctypes.c_uint8 * 56)]

SDL2 = ctypes.CDLL("libSDL2-2.0.so.0")

SDL2.SDL_CreateWindow.restype = ctypes.c_void_p
SDL2.SDL_CreateRenderer.restype = ctypes.c_void_p
SDL2.SDL_CreateTextureFromSurface.restype = ctypes.c_void_p
SDL2.SDL_JoystickOpen.restype = ctypes.c_void_p
SDL2.SDL_GetError.restype = ctypes.c_char_p

SDL2_TTF = None
try:
    SDL2_TTF = ctypes.CDLL("libSDL2_ttf-2.0.so.0")
    SDL2_TTF.TTF_OpenFont.restype = ctypes.c_void_p
    SDL2_TTF.TTF_OpenFont.argtypes = [ctypes.c_char_p, ctypes.c_int]
    SDL2_TTF.TTF_RenderUTF8_Blended.restype = ctypes.c_void_p
    SDL2_TTF.TTF_RenderUTF8_Blended.argtypes = [ctypes.c_void_p, ctypes.c_char_p, SDL_Color]
    SDL2_TTF.TTF_SizeUTF8.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
    SDL2_TTF.TTF_CloseFont.argtypes = [ctypes.c_closeFont] if hasattr(SDL2_TTF, 'TTF_closeFont') else [ctypes.c_void_p]
except Exception:
    pass

SDL2_IMAGE = None
try:
    SDL2_IMAGE = ctypes.CDLL("libSDL2_image-2.0.so.0")
    SDL2_IMAGE.IMG_Init(0x00000002)
    SDL2_IMAGE.IMG_Load.restype = ctypes.c_void_p
    SDL2_IMAGE.IMG_Load.argtypes = [ctypes.c_char_p]
except Exception:
    pass

SDL_INIT_VIDEO, SDL_INIT_JOYSTICK, SDL_INIT_GAMECONTROLLER = 0x00000020, 0x00000200, 0x00002000
SDL_WINDOW_SHOWN = 0x00000004
SDL_RENDERER_ACCELERATED, SDL_RENDERER_SOFTWARE = 0x00000002, 0x00000001
SDL_QUIT, SDL_KEYDOWN, SDL_JOYBUTTONDOWN = 0x100, 0x300, 0x603
SDL_JOYAXISMOTION, SDL_JOYHATMOTION = 0x600, 0x602

SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT = 1073741906, 1073741905, 1073741904, 1073741903
SDLK_RETURN, SDLK_ESCAPE, SDLK_SPACE, SDLK_a, SDLK_b, SDLK_x, SDLK_y = 13, 27, 32, 97, 98, 120, 121
SDLK_PAGEUP, SDLK_PAGEDOWN = 1073741899, 1073741902
SDLK_r, SDLK_p, SDLK_f = 114, 112, 102

BTN_A_CODES = (0, 3)
BTN_B_CODES = (1, 4)
BTN_X_CODES = (2,)
BTN_Y_CODES = (3, 5)
BTN_L1_CODES = (4, 6)
BTN_R1_CODES = (5, 7)
BTN_START_CODES = (9, 11)
HAT_UP, HAT_DOWN, HAT_LEFT, HAT_RIGHT = 1, 4, 8, 2

W, H = 640, 480

# =============================================================================
# THEME SYSTEM
# =============================================================================
THEMES = {
    "spdw": {
        "BG": (7, 8, 11, 255), "BG2": (18, 20, 26, 255), "PANEL": (24, 26, 34, 255),
        "BORDER": (0, 255, 200, 160), "TEXT": (233, 233, 226, 255), "TEXT_DIM": (148, 150, 152, 255),
        "ACCENT": (255, 176, 46, 255), "GREEN": (96, 225, 120, 255), "RED": (238, 62, 58, 255),
        "ORANGE": (255, 140, 0, 255), "YELLOW": (255, 220, 50, 255),
        "SEL_BG": (30, 24, 38, 255), "SEL_TEXT": (255, 255, 255, 255),
        "SELECTED": (255, 176, 46, 180), "MAGENTA": (231, 54, 84, 255), "CYAN": (74, 206, 224, 255),
    },
    "tailscale": {
        "BG": (28, 28, 30, 255), "BG2": (36, 36, 38, 255), "PANEL": (44, 44, 46, 255),
        "BORDER": (60, 60, 64, 255), "TEXT": (250, 250, 250, 255), "TEXT_DIM": (170, 170, 175, 255),
        "ACCENT": (75, 81, 198, 255), "GREEN": (46, 170, 95, 255), "RED": (235, 87, 87, 255),
        "ORANGE": (242, 153, 74, 255), "YELLOW": (240, 200, 80, 255),
        "SEL_BG": (58, 58, 60, 255), "SEL_TEXT": (255, 255, 255, 255),
        "SELECTED": (75, 81, 198, 180), "MAGENTA": (140, 110, 220, 255), "CYAN": (100, 200, 255, 255),
    },
    "hybrid": {
        "BG": (14, 14, 20, 255), "BG2": (22, 22, 30, 255), "PANEL": (26, 26, 36, 255),
        "BORDER": (0, 210, 190, 140), "TEXT": (245, 245, 250, 255), "TEXT_DIM": (150, 160, 170, 255),
        "ACCENT": (0, 220, 190, 255), "GREEN": (46, 190, 110, 255), "RED": (235, 87, 87, 255),
        "ORANGE": (242, 153, 74, 255), "YELLOW": (240, 210, 80, 255),
        "SEL_BG": (35, 35, 48, 255), "SEL_TEXT": (255, 255, 255, 255),
        "SELECTED": (0, 220, 190, 180), "MAGENTA": (255, 0, 190, 255), "CYAN": (0, 200, 255, 255),
    },
}
THEME_ORDER = ["spdw", "tailscale", "hybrid"]
THEME_NAMES = {"spdw": "SPDW Megastructure", "tailscale": "Tailscale Classic", "hybrid": "SPDW Hybrid"}
CURRENT_THEME = "spdw"

def apply_theme(name):
    global CURRENT_THEME
    global C_BG, C_BG2, C_PANEL, C_BORDER, C_TEXT, C_TEXT_DIM
    global C_ACCENT, C_GREEN, C_RED, C_ORANGE, C_YELLOW, C_SEL_BG, C_SEL_TEXT, C_SELECTED, C_MAGENTA, C_CYAN
    t = THEMES.get(name, THEMES["spdw"])
    CURRENT_THEME = name if name in THEMES else "spdw"
    C_BG, C_BG2, C_PANEL, C_BORDER = t["BG"], t["BG2"], t["PANEL"], t["BORDER"]
    C_TEXT, C_TEXT_DIM = t["TEXT"], t["TEXT_DIM"]
    C_ACCENT, C_GREEN, C_RED, C_ORANGE, C_YELLOW = t["ACCENT"], t["GREEN"], t["RED"], t["ORANGE"], t["YELLOW"]
    C_SEL_BG, C_SEL_TEXT, C_SELECTED = t["SEL_BG"], t["SEL_TEXT"], t["SELECTED"]
    C_MAGENTA, C_CYAN = t["MAGENTA"], t["CYAN"]

apply_theme(CURRENT_THEME)
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")

def load_config():
    cfg = {
        "lang": "en",
        "scan_source": "both",
        "theme": CURRENT_THEME,
        "target_lufs": str(TARGET_LUFS),
        "sample_rate": str(SAMPLE_RATE),
        "ogg_quality": OGG_QUALITY,
        "delete_originals": "false",
        "normalize_volume": "true",
        "trim_silence": "false",
        "convert_to_ogg": "true",
        "glitch_fx": "true",
        "out_mode": "default",
        "custom_out_dir": "",
        "pc_input_dir": DEFAULT_PC_INPUT,
        "pc_output_dir": DEFAULT_PC_OUTPUT,
    }
    try:
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    except Exception:
        pass
    return cfg

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            for k, v in cfg.items():
                f.write("{0} = {1}\n".format(k, v))
    except Exception:
        pass

# =============================================================================
# REAL-TIME FFMPEG EXECUTION
# =============================================================================

def run_cmd_with_progress(cmd, duration_sec, start_pct, end_pct, update_cb, log_cb):
    """Esegue ffmpeg con progress tracking. Fallback a subprocess.run se il pipe fallisce."""
    log("run_cmd_progress: {0}".format(" ".join(cmd)))
    try:
        # --- METODO 1: Progress tracking via pipe (PC & muOS moderno) ---
        if "-progress" not in cmd:
            cmd_progress = cmd[:1] + ["-progress", "pipe:1", "-nostats"] + cmd[1:]
        else:
            cmd_progress = cmd

        proc = subprocess.Popen(cmd_progress, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        pattern_time = re.compile(r"out_time_us=(\d+)")
        last_update = time.time()
        progress_works = False

        while True:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue

            line = line.strip()
            if line.startswith("out_time_us="):
                m = pattern_time.search(line)
                if m and duration_sec > 0:
                    us = int(m.group(1))
                    curr_sec = us / 1000000.0
                    sub_ratio = min(1.0, max(0.0, curr_sec / float(duration_sec)))
                    curr_pct = start_pct + (end_pct - start_pct) * sub_ratio
                    update_cb(curr_pct)
                    last_update = time.time()
                    progress_works = True

            if time.time() - last_update > 180:
                log("run_cmd_progress TIMEOUT")
                proc.kill()
                proc.wait()
                return False

        proc.wait(timeout=5)
        if proc.returncode == 0:
            return True
        if progress_works:
            return False  # Progress ha funzionato ma ffmpeg ha fallito
        # Se progress non ha mai funzionato, prova metodo 2

    except Exception as e:
        log("run_cmd_progress pipe method failed: {0}".format(e))

    # --- METODO 2: subprocess.run semplice (muOS fallback) ---
    try:
        log("run_cmd_progress: using subprocess.run fallback")
        # Rimuovi -progress e -nostats se presenti
        cmd_simple = [c for c in cmd if c not in ("-progress", "pipe:1", "-nostats")]
        # Aggiorna progress a metà
        update_cb(start_pct + (end_pct - start_pct) * 0.5)
        res = subprocess.run(cmd_simple, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        update_cb(end_pct)
        return res.returncode == 0
    except Exception as e2:
        log("run_cmd_progress fallback failed: {0}".format(e2))
        return False


def check_ffmpeg():
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False


def scan_audio_recursive(directories):
    files = []
    script_name = os.path.basename(__file__)
    seen = set()
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        try:
            for root, dirs, filenames in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTS and f != script_name and not f.startswith("."):
                        full = os.path.join(root, f)
                        if full not in seen:
                            seen.add(full)
                            rel_path = os.path.relpath(full, directory)
                            files.append({"full_path": full, "rel_path": rel_path, "source_dir": directory})
        except Exception as e:
            log("ERROR scanning files in {0}: {1}".format(directory, e))
    files.sort(key=lambda x: x["full_path"])
    return files


def get_audio_info(filepath):
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            duration = float(format_info.get("duration", 0))
            bitrate = format_info.get("bit_rate", "unknown")
            size = int(format_info.get("size", 0))
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
            sample_rate = audio_stream.get("sample_rate", "unknown")
            channels = audio_stream.get("channels", "unknown")
            codec = audio_stream.get("codec_name", "unknown")
            return {"duration": duration, "bitrate": bitrate, "size": size,
                    "sample_rate": sample_rate, "channels": channels, "codec": codec}
    except Exception as e:
        log("ERROR getting info for {0}: {1}".format(filepath, e))
    return None


def analyze_loudness(filepath):
    try:
        cmd = ["ffmpeg", "-vn", "-sn", "-i", filepath, "-af", "loudnorm=print_format=json", "-f", "null", "-"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=300)
        # loudnorm output va su stderr in formato JSON
        stderr_text = res.stderr if res.stderr else ""
        match = re.search(r'\{[^}]*"input_i"[^}]*\}', stderr_text)
        if match:
            d = json.loads(match.group())
            return {
                "input_i": float(d.get("input_i", 0)),
                "input_tp": float(d.get("input_tp", 0)),
                "input_lra": float(d.get("input_lra", 0)),
                "input_thresh": float(d.get("input_thresh", 0)),
                "target_offset": float(d.get("target_offset", 0))
            }
        else:
            log("loudness: no JSON match in stderr for {0}".format(filepath))
    except Exception as e:
        log("ERROR loudness analysis for {0}: {1}".format(filepath, e))
    return None

def format_duration(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return "{0:02d}:{1:02d}".format(m, s)

def format_size(bytes_size):
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return "{0:.1f} {1}".format(bytes_size, unit)
        bytes_size /= 1024.0
    return "{0:.1f} TB".format(bytes_size)

# =============================================================================
# RENDERER WITH PRIMITIVE VECTOR ICON ENGINE
# =============================================================================
class Renderer:
    def __init__(self, renderer, font_small, font_med, font_large, font_xl, font_bgm, font_norm):
        self.r = renderer
        self.fs, self.fm, self.fl, self.fx = font_small, font_med, font_large, font_xl
        self.fb = font_bgm      # Font BGM massiccio (anime title)
        self.fn = font_norm     # Font Normalizer pixel
        self.logo_tex = None
        if SDL2_IMAGE:
            logo_path = os.path.join(APP_DIR, "glyph", "icon.png").encode()
            if os.path.exists(logo_path):
                surf_ptr = SDL2_IMAGE.IMG_Load(logo_path)
                if surf_ptr:
                    self.logo_tex = SDL2.SDL_CreateTextureFromSurface(self.r, ctypes.c_void_p(surf_ptr))
                    SDL2.SDL_FreeSurface(ctypes.c_void_p(surf_ptr))

    def text_size(self, font, txt):
        if not font or not SDL2_TTF or not txt:
            return (0, 0)
        try:
            txt_bytes = str(txt).encode("utf-8", errors="replace")
        except Exception:
            txt_bytes = b"?"
        w_out, h_out = ctypes.c_int(0), ctypes.c_int(0)
        SDL2_TTF.TTF_SizeUTF8(font, txt_bytes, ctypes.byref(w_out), ctypes.byref(h_out))
        return (w_out.value, h_out.value)

    def clear(self, color=None):
        c = color or C_BG
        SDL2.SDL_SetRenderDrawColor(self.r, c[0], c[1], c[2], c[3] if len(c) > 3 else 255)
        SDL2.SDL_RenderClear(self.r)

    def rect(self, x, y, w, h, color, fill=True):
        SDL2.SDL_SetRenderDrawColor(self.r, color[0], color[1], color[2], color[3] if len(color) > 3 else 255)
        rct = SDL_Rect(int(x), int(y), int(w), int(h))
        if fill:
            SDL2.SDL_RenderFillRect(self.r, ctypes.byref(rct))
        else:
            SDL2.SDL_RenderDrawRect(self.r, ctypes.byref(rct))

    def line(self, x1, y1, x2, y2, color):
        SDL2.SDL_SetRenderDrawColor(self.r, color[0], color[1], color[2], color[3] if len(color) > 3 else 255)
        SDL2.SDL_RenderDrawLine(self.r, int(x1), int(y1), int(x2), int(y2))

    def text(self, font, txt, x, y, color, center=False, right=False):
        if not font or not SDL2_TTF or not txt:
            return
        try:
            txt_bytes = str(txt).encode("utf-8", errors="replace")
        except Exception:
            txt_bytes = b"?"
        col = SDL_Color(color[0], color[1], color[2], 255)
        surf = SDL2_TTF.TTF_RenderUTF8_Blended(font, txt_bytes, col)
        if not surf:
            return
        tex = SDL2.SDL_CreateTextureFromSurface(self.r, ctypes.c_void_p(surf))
        SDL2.SDL_FreeSurface(ctypes.c_void_p(surf))
        if not tex:
            return
        w_out, h_out = ctypes.c_int(0), ctypes.c_int(0)
        SDL2.SDL_QueryTexture(ctypes.c_void_p(tex), None, None, ctypes.byref(w_out), ctypes.byref(h_out))
        tw, th = w_out.value, h_out.value
        rx = x - tw // 2 if center else x - tw if right else x
        dst = SDL_Rect(int(rx), int(y - th // 2) if center else int(y), tw, th)
        SDL2.SDL_RenderCopy(self.r, ctypes.c_void_p(tex), None, ctypes.byref(dst))
        SDL2.SDL_DestroyTexture(ctypes.c_void_p(tex))

    def text_clipped(self, font, txt, x, y, max_w, color, center=False, right=False):
        if not font or not SDL2_TTF or not txt:
            return
        tw, th = self.text_size(font, txt)
        if tw <= max_w:
            self.text(font, txt, x, y, color, center, right)
            return
        s = str(txt)
        lo, hi = 0, len(s)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            test = s[:mid] + "..."
            tw2, _ = self.text_size(font, test)
            if tw2 <= max_w:
                lo = mid
            else:
                hi = mid - 1
        self.text(font, s[:lo] + "...", x, y, color, center, right)

    def scrollbar(self, x, y, h, total, visible, current):
        if total <= visible:
            return
        self.rect(x, y, 4, h, C_BG2)
        thumb_h = max(10, int(h * (visible / float(total))))
        thumb_y = y + int((h - thumb_h) * (current / float(total - 1 if total > 1 else 1)))
        self.rect(x, thumb_y, 4, thumb_h, C_ACCENT)

    def present(self):
        SDL2.SDL_RenderPresent(self.r)

    def header(self, title):
        """Header Spettacolare in Stile VoidDesk / SPDW Factory"""
        self.rect(0, 0, W, 52, C_BG2)
        self.line(0, 0, W, 0, C_BORDER)
        self.line(0, 50, W, 50, C_ACCENT)
        self.line(0, 52, W, 52, C_BG)

        # Tacche Hazard nell'angolo sinistro
        for hx in range(0, 36, 8):
            self.line(hx, 50, hx + 4, 52, C_ACCENT)

        # REDESIGNED BGM NORMALIZER LOGO HEADER
        bgm_x = 12
        if self.logo_tex:
            dst = SDL_Rect(10, 8, 36, 36)
            SDL2.SDL_RenderCopy(self.r, self.logo_tex, None, ctypes.byref(dst))
            bgm_x = 52

        # Ghosting Cromatico Rosso / China per "BGM" Massiccio
        self.text(self.fx, "BGM", bgm_x - 1, 4, (180, 30, 30, 255))
        self.text(self.fx, "BGM", bgm_x + 1, 6, (20, 20, 20, 255))
        self.text(self.fx, "BGM", bgm_x, 5, C_TEXT)

        bgm_w, _ = self.text_size(self.fx, "BGM")
        
        # BADGE "NORMALIZER" CON COLORI E FONT DIVERSI
        norm_x = bgm_x + bgm_w + 8
        self.rect(norm_x, 14, 110, 22, C_PANEL)
        self.rect(norm_x, 14, 110, 22, C_CYAN, fill=False)
        self.text(self.fm, "Normalizer", norm_x + 5, 11, C_CYAN)

        if title:
            self.line(norm_x + 120, 10, norm_x + 120, 42, C_BORDER)
            self.text(self.fm, "▚ " + title, norm_x + 132, 14, C_TEXT_DIM)

    def footer(self, hints):
        self.rect(0, H - 38, W, 38, C_BG2)
        self.line(0, H - 38, W, H - 38, C_BORDER)
        x = 10
        for btn, lbl in hints:
            tw, _ = self.text_size(self.fs, btn)
            badge_w = max(28, tw + 12)
            self.rect(x, H - 30, badge_w, 24, C_PANEL)
            self.rect(x, H - 30, badge_w, 24, C_ACCENT, fill=False)
            self.text(self.fs, btn, x + badge_w // 2, H - 19, C_ACCENT, center=True)
            x += badge_w + 6
            lw, _ = self.text_size(self.fs, lbl)
            self.text(self.fs, lbl, x, H - 19, C_TEXT_DIM)
            x += lw + 14
            if x > W - 60:
                break

    def panel(self, x, y, w, h, border_col, bg_col):
        self.rect(x, y, w, h, bg_col)
        self.rect(x, y, w, h, border_col, fill=False)

    def glitch_fx(self):
        """Interferenze verticali lente e sottili ai bordi (movimento fluido)"""
        t = time.time()

        # Linee verticali fluide ai bordi
        col_accent = (C_ACCENT[0], C_ACCENT[1], C_ACCENT[2], 25)
        col_cyan = (C_CYAN[0], C_CYAN[1], C_CYAN[2], 25)

        y_flow = (t * 20) % H
        self.line(5, int(y_flow), 5, int(y_flow) + 40, col_accent)
        self.line(W - 6, int((y_flow + H // 2) % H), W - 6, int((y_flow + H // 2) % H) + 40, col_cyan)

        # Interferenze analogiche random ai lati (originale)
        if random.random() < 0.35:
            ly = random.randint(0, H)
            lw = random.randint(15, 60)
            self.rect(0, ly, lw, 1, (C_ACCENT[0], C_ACCENT[1], C_ACCENT[2], 30))

        if random.random() < 0.35:
            ry = random.randint(0, H)
            rw = random.randint(15, 60)
            self.rect(W - rw, ry, rw, 1, (C_CYAN[0], C_CYAN[1], C_CYAN[2], 30))

        if random.random() < 0.08:
            side = 0 if random.random() < 0.5 else W - 8
            py = random.randint(0, H - 10)
            self.rect(side, py, 6, 2, (C_MAGENTA[0], C_MAGENTA[1], C_MAGENTA[2], 50))

    def button(self, x, y, w, h, label, selected, font=None):
        f = font or self.fm
        if selected:
            self.rect(x, y, w, h, C_ACCENT)
            self.text(f, label, x + w // 2, y + h // 2, C_SEL_TEXT, center=True)
        else:
            self.rect(x, y, w, h, C_PANEL)
            self.rect(x, y, w, h, C_BORDER, fill=False)
            self.text(f, label, x + w // 2, y + h // 2, C_TEXT, center=True)

    def progress_bar(self, x, y, w, h, pct, color=None, label=None):
        col = color or C_ACCENT
        pct_clamped = max(0.0, min(100.0, pct))
        self.rect(x, y, w, h, C_BG2)
        if pct_clamped > 0:
            self.rect(x, y, int(w * pct_clamped / 100.0), h, col)
        self.rect(x, y, w, h, C_BORDER, fill=False)
        lbl = label if label else "{0:.1f}%".format(pct_clamped)
        self.text(self.fs, lbl, x + w // 2, y + h // 2, C_TEXT, center=True)

    def status_dot(self, x, y, ok):
        self.rect(x, y, 8, 8, C_GREEN if ok else C_RED)

    def checkbox(self, x, y, label, checked, selected):
        box_col = C_ACCENT if selected else C_BORDER
        self.rect(x, y, 18, 18, C_BG2)
        self.rect(x, y, 18, 18, box_col, fill=False)
        if checked:
            self.rect(x + 3, y + 3, 12, 12, C_GREEN)
        self.text(self.fm, label, x + 26, y - 2, C_TEXT if selected else C_TEXT_DIM)

    # VECTOR PRIMITIVE ICONS FOR MAIN MENU
    def draw_menu_icon(self, icon_type, x, y, color):
        if icon_type == "folder":
            self.rect(x, y + 4, 10, 4, color)
            self.rect(x, y + 6, 22, 14, color, fill=False)
            self.line(x, y + 6, x + 21, y + 6, color)
        elif icon_type == "settings":
            self.line(x + 4, y + 2, x + 4, y + 18, color)
            self.line(x + 11, y + 2, x + 11, y + 18, color)
            self.line(x + 18, y + 2, x + 18, y + 18, color)
            self.rect(x + 2, y + 6, 5, 4, color)
            self.rect(x + 9, y + 12, 5, 4, color)
            self.rect(x + 16, y + 4, 5, 4, color)
        elif icon_type == "options":
            self.rect(x + 2, y + 2, 8, 8, color, fill=False)
            self.rect(x + 12, y + 2, 8, 8, color)
            self.rect(x + 2, y + 12, 8, 8, color)
            self.rect(x + 12, y + 12, 8, 8, color, fill=False)
        elif icon_type == "exit":
            self.rect(x + 2, y + 2, 12, 16, color, fill=False)
            self.line(x + 10, y + 10, x + 20, y + 10, color)
            self.line(x + 16, y + 6, x + 20, y + 10, color)
            self.line(x + 16, y + 14, x + 20, y + 10, color)

# =============================================================================
# APP LOGIC
# =============================================================================
class App:
    def __init__(self):
        self.screen = "bootanim"
        self.boot_start = time.time()
        self.sel = 0
        self.running = True
        self.axis_timer = {}
        self.cfg = load_config()
        self.lang = self.cfg.get("lang", "en")
        self.scan_source = self.cfg.get("scan_source", "both")
        self.pc_input_dir = self.cfg.get("pc_input_dir", DEFAULT_PC_INPUT)
        self.pc_output_dir = self.cfg.get("pc_output_dir", DEFAULT_PC_OUTPUT)
        self.theme = self.cfg.get("theme", CURRENT_THEME)
        self.target_lufs = float(self.cfg.get("target_lufs", TARGET_LUFS))
        self.sample_rate = int(self.cfg.get("sample_rate", SAMPLE_RATE))
        self.ogg_quality = self.cfg.get("ogg_quality", OGG_QUALITY)
        self.delete_originals = self.cfg.get("delete_originals", "false").lower() == "true"
        self.normalize_volume = self.cfg.get("normalize_volume", "true").lower() == "true"
        self.trim_silence_flag = self.cfg.get("trim_silence", "false").lower() == "true"
        self.convert_to_ogg = self.cfg.get("convert_to_ogg", "true").lower() == "true"
        self.glitch_fx = self.cfg.get("glitch_fx", "true").lower() == "true"
        self.out_mode = self.cfg.get("out_mode", "default")
        self.custom_out_dir = self.cfg.get("custom_out_dir", "")
        apply_theme(self.theme)

        self.sd_paths = {
            "1": {"input": SD1_INPUT, "output": SD1_OUTPUT, "label": "SD1"},
            "2": {"input": SD2_INPUT, "output": SD2_OUTPUT, "label": "SD2"},
        }

        self.audio_files = []
        self.file_infos = {}
        self.file_sel = 0
        self.file_scroll_top = 0
        self.file_selected = set()
        self.show_file_info = True

        self.processing = False
        self.process_results = []
        self.process_completed_count = 0
        self.process_total = 0
        self.process_msg = ""
        self.process_log_lines = []
        self.process_done = False
        self.current_track_pct = 0.0
        self.overall_pct = 0.0
        self.process_start_time = 0
        self.eta_seconds = 0

        self.opt_sel = 0
        self.conv_sel = 0
        self.result_msg = ""
        self.log_view_lines = []
        self.log_view_scroll = 0

        self.osk_text = ""
        self.osk_col = 0
        self.osk_row = 0
        self.osk_callback = None
        self.osk_title = ""

        self.theme_screen_sel = 0
        self.ffmpeg_ok = check_ffmpeg()

        self.boot_particles = []
        for _ in range(35):
            self.boot_particles.append({
                "x": W // 2 + (hash(str(_)) % 220 - 110),
                "y": H // 2 + (hash(str(_ + 100)) % 160 - 80),
                "vx": (hash(str(_ + 200)) % 40 - 20) / 10.0,
                "vy": (hash(str(_ + 300)) % 40 - 20) / 10.0,
                "life": hash(str(_ + 400)) % 100 / 100.0,
                "color": C_ACCENT if _ % 3 == 0 else C_MAGENTA if _ % 3 == 1 else C_CYAN,
            })

        self.input_lock_until = 0.0
        self._scan_audio_files()

    def t(self, key, *args):
        dict_lang = TRANSLATIONS.get(self.lang, TRANSLATIONS.get("en", {}))
        text = dict_lang.get(key, key)
        if args:
            try:
                return text.format(*args)
            except Exception:
                pass
        return text

    def _get_scan_dirs(self):
        if IS_PC:
            os.makedirs(self.pc_input_dir, exist_ok=True)
            return [self.pc_input_dir]
        dirs = []
        if self.scan_source in ("sd1", "both"):
            dirs.append(self.sd_paths["1"]["input"])
        if self.scan_source in ("sd2", "both"):
            dirs.append(self.sd_paths["2"]["input"])
        return dirs

    def _scan_audio_files(self):
        dirs = self._get_scan_dirs()
        self.audio_files = scan_audio_recursive(dirs)
        self.file_infos = {}
        for i, fdata in enumerate(self.audio_files):
            info = get_audio_info(fdata["full_path"])
            if info:
                self.file_infos[i] = info
        self.file_sel = 0
        self.file_scroll_top = 0
        self.file_selected = set(range(len(self.audio_files)))

    def _get_target_output_dir(self, source_dir, full_path):
        if self.out_mode == "inplace":
            return os.path.dirname(full_path)
        elif IS_PC:
            os.makedirs(self.pc_output_dir, exist_ok=True)
            return self.pc_output_dir
        elif self.out_mode == "custom" and self.custom_out_dir:
            return self.custom_out_dir
        else:
            if source_dir == self.sd_paths["1"]["input"]:
                return self.sd_paths["1"]["output"]
            else:
                return self.sd_paths["2"]["output"]

    def handle_input(self, action):
        if self.screen == "bootanim":
            self.screen, self.sel = "main", 0
            self.input_lock_until = time.time() + 0.35
        elif self.screen == "main":
            self._handle_main(action)
        elif self.screen == "file_list":
            self._handle_file_list(action)
        elif self.screen == "conversion_params":
            self._handle_conversion_params(action)
        elif self.screen == "confirm_process":
            if action == "CONFIRM":
                if self.delete_originals:
                    self.screen = "confirm_delete"
                else:
                    self._start_processing()
            elif action == "BACK":
                self.screen = "file_list"
        elif self.screen == "confirm_delete":
            if action == "CONFIRM":
                self._start_processing()
            elif action == "BACK":
                self.screen = "confirm_process"
        elif self.screen == "processing":
            if action == "BACK" and not self.processing:
                self.screen = "main"
            elif action == "CONFIRM" and self.process_done:
                self.screen = "result"
            elif action == "BACK" and self.processing:
                self.processing = False
        elif self.screen == "result":
            if action in ("RESCAN", "TOGGLE_INFO"):
                self._open_log_viewer()
            elif action in ("CONFIRM", "BACK"):
                self.screen = "main"
        elif self.screen == "view_log":
            self._handle_view_log(action)
        elif self.screen == "about":
            if action in ("CONFIRM", "BACK"):
                self.screen = "options"
        elif self.screen == "confirm_exit":
            if action == "CONFIRM":
                PLAYER.stop()
                self.running = False
            elif action == "BACK":
                self.screen = "main"
        elif self.screen == "options":
            self._handle_options(action)
        elif self.screen == "theme_select":
            self._handle_theme_select(action)
        elif self.screen == "osk":
            self._handle_osk(action)

    def _handle_main(self, action):
        items = 4
        if action == "UP":
            self.sel = (self.sel - 1) % items
        elif action == "DOWN":
            self.sel = (self.sel + 1) % items
        elif action == "CONFIRM":
            if self.sel == 0:
                self.screen = "file_list"
            elif self.sel == 1:
                self.screen = "conversion_params"
                self.conv_sel = 0
            elif self.sel == 2:
                self.screen = "options"
                self.opt_sel = 0
            elif self.sel == 3:
                self.screen = "confirm_exit"
        elif action == "BACK":
            self.screen = "confirm_exit"

    def _handle_file_list(self, action):
        items = len(self.audio_files)
        visible = 6 if self.show_file_info else 8

        if action == "UP" and items:
            self.file_sel = (self.file_sel - 1) % items
        elif action == "DOWN" and items:
            self.file_sel = (self.file_sel + 1) % items
        elif action == "PAGE_UP":
            self.file_sel = max(0, self.file_sel - visible)
        elif action == "PAGE_DOWN":
            self.file_sel = min(items - 1, self.file_sel + visible)
        elif action == "CONFIRM":
            if self.file_selected:
                PLAYER.stop()
                self.screen = "confirm_process"
            else:
                self.result_msg = self.t("no_files")
                self.screen = "result"
        elif action == "TOGGLE_SELECT":
            if items > 0 and self.file_sel < items:
                if self.file_sel in self.file_selected:
                    self.file_selected.discard(self.file_sel)
                else:
                    self.file_selected.add(self.file_sel)
        elif action == "PREVIEW":
            if items > 0 and self.file_sel < items:
                fpath = self.audio_files[self.file_sel]["full_path"]
                if PLAYER.is_playing and PLAYER.current_file == fpath:
                    PLAYER.stop()
                else:
                    PLAYER.play(fpath)
        elif action == "FILTER_SELECT":
            non_ogg = [i for i, f in enumerate(self.audio_files) if not f["full_path"].lower().endswith(".ogg")]
            if len(self.file_selected) == len(non_ogg) and len(non_ogg) > 0:
                self.file_selected = set(range(items))
            else:
                self.file_selected = set(non_ogg)
        elif action == "TOGGLE_INFO":
            self.show_file_info = not self.show_file_info
        elif action == "BACK":
            PLAYER.stop()
            self.screen = "main"

        if items > 0:
            if self.file_sel < self.file_scroll_top:
                self.file_scroll_top = self.file_sel
            elif self.file_sel >= self.file_scroll_top + visible:
                self.file_scroll_top = self.file_sel - visible + 1

    def _handle_conversion_params(self, action):
        items = 8
        if action == "UP":
            self.conv_sel = (self.conv_sel - 1) % items
        elif action == "DOWN":
            self.conv_sel = (self.conv_sel + 1) % items
        elif action == "CONFIRM":
            if self.conv_sel == 0:
                self.normalize_volume = not self.normalize_volume
                self.cfg["normalize_volume"] = "true" if self.normalize_volume else "false"
            elif self.conv_sel == 1:
                self.trim_silence_flag = not self.trim_silence_flag
                self.cfg["trim_silence"] = "true" if self.trim_silence_flag else "false"
            elif self.conv_sel == 2:
                self.convert_to_ogg = not self.convert_to_ogg
                self.cfg["convert_to_ogg"] = "true" if self.convert_to_ogg else "false"
            elif self.conv_sel == 3:
                self.delete_originals = not self.delete_originals
                self.cfg["delete_originals"] = "true" if self.delete_originals else "false"
            elif self.conv_sel == 4:
                vals = [p[1] for p in PRESETS_LUFS]
                try:
                    idx = vals.index(self.target_lufs)
                    self.target_lufs = vals[(idx + 1) % len(vals)]
                except ValueError:
                    self.target_lufs = -14.0
                self.cfg["target_lufs"] = str(self.target_lufs)
            elif self.conv_sel == 5:
                if IS_PC:
                    chosen = pick_folder_gui(self.t("opt_in_dir"), self.pc_input_dir)
                    if chosen:
                        self.pc_input_dir = chosen
                        self.cfg["pc_input_dir"] = chosen
                        self._scan_audio_files()
                else:
                    sources = ["sd1", "sd2", "both"]
                    idx = sources.index(self.scan_source) if self.scan_source in sources else 0
                    self.scan_source = sources[(idx + 1) % len(sources)]
                    self.cfg["scan_source"] = self.scan_source
                    self._scan_audio_files()
            elif self.conv_sel == 6:
                if IS_PC:
                    chosen = pick_folder_gui(self.t("opt_out_dir"), self.pc_output_dir)
                    if chosen:
                        self.pc_output_dir = chosen
                        self.cfg["pc_output_dir"] = chosen
                else:
                    modes = ["default", "inplace", "custom"]
                    curr_i = modes.index(self.out_mode) if self.out_mode in modes else 0
                    self.out_mode = modes[(curr_i + 1) % len(modes)]
                    self.cfg["out_mode"] = self.out_mode
            elif self.conv_sel == 7:
                self.screen = "main"
                return
            save_config(self.cfg)
        elif action == "RESCAN":
            self._scan_audio_files()
        elif action == "BACK":
            self.screen = "main"

    def _start_processing(self):
        PLAYER.stop()
        if not self.ffmpeg_ok:
            self.result_msg = "ERROR: ffmpeg not found!"
            self.screen = "result"
            return
        selected_files = [self.audio_files[i] for i in sorted(self.file_selected) if i < len(self.audio_files)]
        if not selected_files:
            self.result_msg = self.t("no_files")
            self.screen = "result"
            return
        self.processing = True
        self.process_done = False
        self.process_results = []
        self.process_completed_count = 0
        self.process_total = len(selected_files)
        self.current_track_pct = 0.0
        self.overall_pct = 0.0
        self.process_msg = "..."
        self.process_log_lines = []
        self.process_start_time = time.time()
        self.screen = "processing"
        t = threading.Thread(target=self._process_thread, args=(selected_files,), daemon=True)
        t.start()

    def _update_track_progress(self, pct):
        self.current_track_pct = max(0.0, min(100.0, pct))
        self.overall_pct = ((self.process_completed_count + (self.current_track_pct / 100.0)) / float(self.process_total)) * 100.0
        elapsed = time.time() - self.process_start_time
        if self.overall_pct > 1.0:
            total_est = (elapsed / self.overall_pct) * 100.0
            self.eta_seconds = max(0, int(total_est - elapsed))

    def _process_thread(self, selected_files):
        log("=== PROCESS THREAD START === files={0}".format(len(selected_files)))
        try:
            for i, fdata in enumerate(selected_files, 1):
                if not self.processing:
                    log("Processing aborted by user")
                    break

                try:
                    self.current_track_pct = 0.0
                    self._update_track_progress(0.0)

                    filename = os.path.basename(fdata["full_path"])
                    input_file = fdata["full_path"]
                    output_dir = self._get_target_output_dir(fdata["source_dir"], input_file)

                    log("--- Track {0}/{1}: {2} ---".format(i, self.process_total, filename))
                    log("Input: {0}".format(input_file))
                    log("Output dir: {0}".format(output_dir))

                    os.makedirs(output_dir, exist_ok=True)

                    self.process_msg = "[{0}/{1}]: {2}".format(i, self.process_total, filename)
                    self._add_log("[{0}/{1}] {2}".format(i, self.process_total, filename))

                    base_name = os.path.splitext(filename)[0]
                    ext = os.path.splitext(filename)[1].lower()
                    is_ogg = ext == ".ogg"
                    result = {"file": filename, "status": "skipped"}

                    info = self.file_infos.get(self.audio_files.index(fdata)) if fdata in self.audio_files else None
                    duration_sec = info["duration"] if info and info.get("duration") else 180.0
                    log("Duration: {0}s".format(duration_sec))

                    if self.convert_to_ogg and not is_ogg:
                        output_file = os.path.join(output_dir, base_name + ".ogg")
                    else:
                        output_file = os.path.join(output_dir, filename)
                    log("Output: {0}".format(output_file))

                    loudness = None
                    if self.normalize_volume:
                        self._add_log("  [1/3] LUFS Analysis...")
                        self._update_track_progress(10.0)
                        log("Calling analyze_loudness...")
                        loudness = analyze_loudness(input_file)
                        if loudness:
                            log("LUFS OK: I={0:.1f} TP={1:.1f}".format(loudness["input_i"], loudness["input_tp"]))
                            self._add_log("  LUFS: {0:.1f} | TP: {1:.1f}".format(loudness["input_i"], loudness["input_tp"]))
                            self._update_track_progress(20.0)
                        else:
                            log("LUFS FAILED")
                            self._add_log("  [WARN] LUFS analysis failed, using 1-pass fallback...")

                    success = False

                    if self.normalize_volume and loudness:
                        self._add_log("  [2/3] 2-Pass Encoding...")
                        loudnorm_filter = (
                            "loudnorm=I={0}:TP=-1.5:LRA=11:"
                            "measured_I={1}:measured_TP={2}:measured_LRA={3}:"
                            "measured_thresh={4}:offset={5}"
                        ).format(self.target_lufs, loudness["input_i"], loudness["input_tp"],
                                 loudness["input_lra"], loudness["input_thresh"], loudness["target_offset"])

                        cmd = ["ffmpeg", "-y", "-vn", "-i", input_file, "-af", loudnorm_filter,
                               "-ar", str(SAMPLE_RATE), "-c:a", "libvorbis", "-q:a", OGG_QUALITY,
                               "-map_metadata", "-1", output_file]

                        log("CMD 2-pass: {0}".format(" ".join(cmd)))
                        success = run_cmd_with_progress(cmd, duration_sec, 20.0, 80.0, self._update_track_progress, self._add_log)
                        log("2-pass result: {0}".format(success))

                    if not success and self.normalize_volume:
                        self._add_log("  [2/3] Fallback 1-Pass...")
                        cmd_fb = ["ffmpeg", "-y", "-vn", "-i", input_file, "-af",
                                  "loudnorm=I={0}:TP=-1.5:LRA=11".format(self.target_lufs),
                                  "-ar", str(SAMPLE_RATE), "-c:a", "libvorbis", "-q:a", OGG_QUALITY,
                                  "-map_metadata", "-1", output_file]
                        log("CMD 1-pass: {0}".format(" ".join(cmd_fb)))
                        success = run_cmd_with_progress(cmd_fb, duration_sec, 20.0, 80.0, self._update_track_progress, self._add_log)
                        log("1-pass result: {0}".format(success))

                    if not success:
                        self._add_log("  [2/3] Fallback Simple OGG...")
                        cmd_simple = ["ffmpeg", "-y", "-vn", "-i", input_file,
                                      "-ar", str(SAMPLE_RATE), "-c:a", "libvorbis", "-q:a", OGG_QUALITY,
                                      "-map_metadata", "-1", output_file]
                        log("CMD simple: {0}".format(" ".join(cmd_simple)))
                        success = run_cmd_with_progress(cmd_simple, duration_sec, 20.0, 80.0, self._update_track_progress, self._add_log)
                        log("Simple result: {0}".format(success))

                    if success:
                        result["status"] = "converted"
                        self._update_track_progress(85.0)
                        log("Track converted OK")

                        if self.trim_silence_flag:
                            trimmed_file = os.path.join(output_dir, base_name + "_trimmed.ogg")
                            self._add_log("  [3/3] Trimming silence...")
                            cmd_trim = ["ffmpeg", "-y", "-vn", "-i", output_file, "-af",
                                        "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB:"
                                        "stop_periods=-1:stop_duration=0.1:stop_threshold=-50dB",
                                        "-c:a", "copy", trimmed_file]
                            log("CMD trim: {0}".format(" ".join(cmd_trim)))
                            if run_cmd_with_progress(cmd_trim, duration_sec, 85.0, 95.0, self._update_track_progress, self._add_log):
                                os.replace(trimmed_file, output_file)
                                self._add_log("  Trim complete")
                                log("Trim OK")
                    else:
                        result["status"] = "error"
                        self._add_log("  [ERR] Processing failed!")
                        log("Track FAILED")

                    if self.delete_originals and result["status"] != "error":
                        try:
                            os.remove(input_file)
                            self._add_log("  Original deleted")
                            log("Original deleted")
                        except Exception as e:
                            self._add_log("  Delete error: {0}".format(e))
                            log("Delete error: {0}".format(e))

                    self._update_track_progress(100.0)
                    self.process_completed_count = i
                    self.process_results.append(result)
                    log("Track {0} done. Status: {1}".format(i, result["status"]))

                except Exception as track_err:
                    log("TRACK ERROR: {0}".format(track_err))
                    self._add_log("  [ERR] {0}".format(track_err))
                    result = {"file": filename, "status": "error"}
                    self.process_results.append(result)
                    continue

            self.process_done = True
            self.overall_pct = 100.0
            self.process_msg = "All tracks processed!"
            self._build_result_msg()
            log("=== PROCESS THREAD COMPLETE ===")
        except Exception as e:
            log("THREAD CRASH: {0}".format(e))
            import traceback
            log("TRACEBACK: {0}".format(traceback.format_exc()))
            self.process_msg = "Crash: {0}".format(str(e)[:40])
            self.process_done = True


    def _add_log(self, line):
        self.process_log_lines.append(line)
        log("APP_UI: {0}".format(line))

    def _build_result_msg(self):
        success = sum(1 for r in self.process_results if r["status"] != "error")
        errors = sum(1 for r in self.process_results if r["status"] == "error")
        lines = [
            self.t("results_complete"),
            "",
            self.t("tracks_completed", success, len(self.process_results)),
            self.t("errors_found", errors),
            "",
            self.t("log_saved", LOG_FILE),
            "",
        ]
        for r in self.process_results:
            tag = "[OK] " if r["status"] != "error" else "[ERR]"
            lines.append("{0} {1}".format(tag, r["file"]))
        self.result_msg = "\n".join(lines)

    def _open_log_viewer(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    self.log_view_lines = [l.rstrip("\r\n") for l in f.readlines()]
            else:
                self.log_view_lines = ["No log file found."]
        except Exception as e:
            self.log_view_lines = ["Log error: " + str(e)]
        self.log_view_scroll = max(0, len(self.log_view_lines) - 15)
        self.screen = "view_log"

    def _handle_view_log(self, action):
        cnt = len(self.log_view_lines)
        if action == "UP":
            self.log_view_scroll = max(0, self.log_view_scroll - 1)
        elif action == "DOWN":
            self.log_view_scroll = min(max(0, cnt - 15), self.log_view_scroll + 1)
        elif action in ("BACK", "CONFIRM"):
            self.screen = "main"

    def _handle_options(self, action):
        items = 7
        if action == "UP":
            self.opt_sel = (self.opt_sel - 1) % items
        elif action == "DOWN":
            self.opt_sel = (self.opt_sel + 1) % items
        elif action == "CONFIRM":
            if self.opt_sel == 0:
                self.lang = "it" if self.lang == "en" else "en"
                self.cfg["lang"] = self.lang
                save_config(self.cfg)
            elif self.opt_sel == 1:
                self.theme_screen_sel = THEME_ORDER.index(self.theme) if self.theme in THEME_ORDER else 0
                self.screen = "theme_select"
            elif self.opt_sel == 2:
                self.glitch_fx = not self.glitch_fx
                self.cfg["glitch_fx"] = "true" if self.glitch_fx else "false"
                save_config(self.cfg)
            elif self.opt_sel == 3:
                self._open_log_viewer()
            elif self.opt_sel == 4:
                self.target_lufs = TARGET_LUFS
                self.normalize_volume = True
                self.trim_silence_flag = False
                self.convert_to_ogg = True
                self.glitch_fx = True
                self.lang = "en"
                self.cfg["lang"] = "en"
                self.cfg["glitch_fx"] = "true"
                self.cfg["target_lufs"] = str(TARGET_LUFS)
                save_config(self.cfg)
                self._scan_audio_files()
            elif self.opt_sel == 5:
                self.screen = "about"
            elif self.opt_sel == 6:
                self.screen = "main"
        elif action == "BACK":
            self.screen = "main"

    def _handle_theme_select(self, action):
        items = len(THEME_ORDER)
        if action == "UP":
            self.theme_screen_sel = (self.theme_screen_sel - 1) % items
        elif action == "DOWN":
            self.theme_screen_sel = (self.theme_screen_sel + 1) % items
        elif action == "CONFIRM":
            chosen = THEME_ORDER[self.theme_screen_sel]
            apply_theme(chosen)
            self.theme = chosen
            self.cfg["theme"] = chosen
            save_config(self.cfg)
            self.screen = "options"
        elif action == "BACK":
            self.screen = "options"

    OSK_ROWS = [list("abcdefghij"), list("klmnopqrst"), list("uvwxyz0123"), list("456789-_/."), ["BACK", "SPACE", "OK"]]

    def _handle_osk(self, action):
        rows, row, col = self.OSK_ROWS, self.osk_row, self.osk_col
        row_len = len(rows[row])
        if action == "UP":
            self.osk_row = (row - 1) % len(rows)
            self.osk_col = min(self.osk_col, len(rows[self.osk_row]) - 1)
        elif action == "DOWN":
            self.osk_row = (row + 1) % len(rows)
            self.osk_col = min(self.osk_col, len(rows[self.osk_row]) - 1)
        elif action == "LEFT":
            self.osk_col = (col - 1) % row_len
        elif action == "RIGHT":
            self.osk_col = (col + 1) % row_len
        elif action == "CONFIRM":
            key = rows[row][col]
            if key == "OK":
                cb, text = self.osk_callback, self.osk_text
                self.osk_callback = None
                if cb:
                    cb(text)
            elif key == "BACK":
                self.osk_text = self.osk_text[:-1]
            elif key == "SPACE":
                self.osk_text += " "
            else:
                if len(self.osk_text) < 60:
                    self.osk_text += key
        elif action == "BACK":
            self.osk_callback = None
            self.screen = "conversion_params"

    # =============================================================================
    # DRAWING
    # =============================================================================
    def draw(self, rnd):
        rnd.clear()
        if self.screen == "bootanim":
            self._draw_bootanim(rnd)
        elif self.screen == "main":
            self._draw_main(rnd)
        elif self.screen == "file_list":
            self._draw_file_list(rnd)
        elif self.screen == "conversion_params":
            self._draw_conversion_params(rnd)
        elif self.screen == "confirm_process":
            self._draw_confirm_process(rnd)
        elif self.screen == "confirm_delete":
            self._draw_confirm_delete(rnd)
        elif self.screen == "processing":
            self._draw_processing(rnd)
        elif self.screen == "result":
            self._draw_result(rnd)
        elif self.screen == "view_log":
            self._draw_view_log(rnd)
        elif self.screen == "about":
            self._draw_about(rnd)
        elif self.screen == "confirm_exit":
            self._draw_confirm_exit(rnd)
        elif self.screen == "options":
            self._draw_options(rnd)
        elif self.screen == "theme_select":
            self._draw_theme_select(rnd)
        elif self.screen == "osk":
            self._draw_osk(rnd)
        
        if self.glitch_fx:
            rnd.glitch_fx()
        rnd.present()

    def _draw_bootanim(self, rnd):
        rnd.rect(0, 0, W, H, C_BG)
        elapsed = time.time() - self.boot_start

        bar_count = 20
        bar_w = 20
        start_x = (W - (bar_count * (bar_w + 4))) // 2
        for b in range(bar_count):
            h_val = int(30 + 80 * math.sin(elapsed * 4 + b * 0.4) * math.cos(elapsed * 2 + b * 0.2))
            h_val = abs(h_val)
            bx = start_x + b * (bar_w + 4)
            by = H // 2 - h_val // 2 + 10
            rnd.rect(bx, by, bar_w, h_val, (0, 255, 200, 30 if b % 2 == 0 else 50))

        for p in self.boot_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] += 0.025
            alpha = int(255 * max(0, 1.0 - abs(p["life"] - 0.5) * 2))
            if alpha > 20:
                size = 2 + int(4 * abs(hash(str(p["x"])) % 100) / 100.0)
                col = p["color"][:3] + (alpha,)
                rnd.rect(int(p["x"]), int(p["y"]), size, size, col)
            if p["life"] > 1.0:
                p["life"] = 0
                p["x"] = W // 2 + (hash(str(int(time.time() * 1000))) % 300 - 150)
                p["y"] = H // 2 + (hash(str(int(time.time() * 1000) + 1)) % 200 - 100)

        if elapsed > 0.3:
            glow_intensity = min(255, int((elapsed - 0.3) * 300))
            for offset in [(3, 3), (-3, -3), (3, -3), (-3, 3)]:
                rnd.text(rnd.fx, BRAND, W // 2 + offset[0], H // 2 - 60 + offset[1],
                        (0, 255, 200, glow_intensity // 4), center=True)
            rnd.text(rnd.fx, BRAND, W // 2, H // 2 - 60, (0, 255, 200, glow_intensity), center=True)

        if elapsed > 0.8:
            rnd.text(rnd.fm, "F A C T O R Y   L A B", W // 2, H // 2 - 18, C_TEXT_DIM, center=True)

        if elapsed > 1.5:
            line_w = min(W - 80, int((elapsed - 1.5) * 400))
            lx = (W - line_w) // 2
            rnd.line(lx, H // 2 + 6, lx + line_w, H // 2 + 6, C_ACCENT)

        if elapsed > 2.0:
            title_glow = min(255, int((elapsed - 2.0) * 200))
            rnd.text(rnd.fl, "BGM NORMALIZER", W // 2, H // 2 + 34,
                    (C_TEXT[0], C_TEXT[1], C_TEXT[2], title_glow), center=True)

        if elapsed > 2.8:
            edition = "PC Edition" if IS_PC else "muOS Edition"
            rnd.text(rnd.fs, "v" + APP_VERSION + " | " + edition, W // 2, H // 2 + 68, C_TEXT_DIM, center=True)

        if elapsed > 3.3:
            pulse = abs(int((elapsed - 3.3) * 3) % 2 - 1)
            col = C_TEXT_DIM if pulse else C_ACCENT
            hint = "[Press A/ENTER/SPACE]" if IS_PC else "[Press Any Button]"
            rnd.text(rnd.fs, hint, W // 2, H - 44, col, center=True)

        bar_w_top = int(W * min(1.0, elapsed / 4.0))
        rnd.rect(0, H - 4, bar_w_top, 4, C_ACCENT)

    def _draw_main(self, rnd):
        rnd.header("")

        scan_text = self.t("scan_info", self.pc_input_dir if IS_PC else self.scan_source.upper(), len(self.audio_files))
        rnd.text_clipped(rnd.fs, scan_text, 16, 76, W - 32, C_TEXT_DIM)
        rnd.line(16, 94, W - 16, 94, C_BORDER)

        sy = 102
        rnd.panel(16, sy, W - 32, 64, C_BORDER, C_BG2)
        rnd.status_dot(32, sy + 18, self.ffmpeg_ok)
        rnd.text(rnd.fm, self.t("ffmpeg_ok") if self.ffmpeg_ok else self.t("ffmpeg_missing"), 48, sy + 12, C_GREEN if self.ffmpeg_ok else C_RED)

        preset_str = "LUFS:{0:.0f} | Norm:{1} | Trim:{2}".format(
            self.target_lufs, "ON" if self.normalize_volume else "OFF", "ON" if self.trim_silence_flag else "OFF")
        rnd.text_clipped(rnd.fs, preset_str, 32, sy + 38, W - 64, C_TEXT_DIM)

        menu = [
            ("folder", self.t("menu_file_list"), self.t("sub_file_list")),
            ("settings", self.t("menu_settings"), self.t("sub_settings")),
            ("options", self.t("menu_options"), self.t("sub_options")),
            ("exit", self.t("menu_exit"), self.t("sub_exit")),
        ]
        my = sy + 76
        for i, (icon_type, lbl, sub) in enumerate(menu):
            sel = (i == self.sel)
            ry = my + i * 54
            rnd.rect(16, ry, W - 32, 50, C_SEL_BG if sel else C_BG)
            if sel:
                rnd.rect(16, ry, 4, 50, C_ACCENT)
            
            rnd.draw_menu_icon(icon_type, 28, ry + 14, C_ACCENT if sel else C_TEXT_DIM)
            rnd.text(rnd.fm, lbl, 60, ry + 8, C_TEXT)
            rnd.text_clipped(rnd.fs, sub, 60, ry + 28, W - 92, C_TEXT_DIM)

        rnd.footer([(self.t("nav_select"), "A"), (self.t("nav_exit"), "ESC")])

    def _draw_file_list(self, rnd):
        rnd.header(self.t("header_file_list"))
        count = len(self.audio_files)
        sel_count = len(self.file_selected)

        playing_str = " | 🎵 " + self.t("playing") if PLAYER.is_playing else ""
        header_text = self.t("selected_tracks", sel_count, count) + playing_str
        rnd.text_clipped(rnd.fs, header_text, 16, 76, W - 32, C_GREEN if PLAYER.is_playing else C_TEXT_DIM)
        rnd.line(16, 94, W - 16, 94, C_BORDER)

        if not count:
            rnd.text(rnd.fm, self.t("no_files"), W // 2, H // 2, C_TEXT_DIM, center=True)
            rnd.footer([(self.t("nav_back"), "ESC")])
            return

        row_h = 58 if self.show_file_info else 38
        visible = 6 if self.show_file_info else 8
        start = self.file_scroll_top

        for i in range(visible):
            real_i = start + i
            if real_i >= count:
                break
            fdata = self.audio_files[real_i]
            sel = (real_i == self.file_sel)
            is_checked = real_i in self.file_selected
            is_curr_playing = PLAYER.is_playing and PLAYER.current_file == fdata["full_path"]
            row_y = 102 + i * row_h

            if sel:
                rnd.rect(12, row_y - 2, W - 24, row_h - 2, C_SEL_BG)
                rnd.rect(12, row_y - 2, 4, row_h - 2, C_ACCENT)

            cb_col = C_GREEN if is_checked else C_TEXT_DIM
            rnd.rect(24, row_y + 8, 18, 18, C_BG2)
            rnd.rect(24, row_y + 8, 18, 18, cb_col, fill=False)
            if is_checked:
                rnd.text(rnd.fs, "V", 33, row_y + 8, C_GREEN, center=True)

            fname = os.path.basename(fdata["full_path"])
            ext = os.path.splitext(fname)[1].upper()
            
            title_col = C_GREEN if is_curr_playing else (C_TEXT if sel else C_TEXT_DIM)
            prefix = "🎵 " if is_curr_playing else ""
            rnd.text_clipped(rnd.fm, prefix + fname, 50, row_y + 4, W - 160, title_col)

            rnd.text(rnd.fs, ext[1:], W - 48, row_y + 8, C_CYAN if ext == ".OGG" else C_MAGENTA, right=True)

            if self.show_file_info:
                info = self.file_infos.get(real_i)
                if info:
                    detail = "{0} | {1} | {2}".format(info["codec"].upper(), format_duration(info["duration"]), format_size(info["size"]))
                    rnd.text(rnd.fs, detail, 50, row_y + 24, C_TEXT_DIM)
                rnd.text_clipped(rnd.fs, fdata["full_path"], 50, row_y + 40, W - 80, (100, 110, 120, 255))

            rnd.line(50, row_y + row_h - 2, W - 16, row_y + row_h - 2, C_BG2)

        rnd.scrollbar(W - 10, 102, row_h * min(visible, count), count, visible, self.file_sel)
        rnd.footer([("X", self.t("nav_toggle")), ("P/START", self.t("nav_preview")), ("F/L1", self.t("nav_filter")), ("A", self.t("nav_confirm")), ("ESC", self.t("nav_back"))])

    def _draw_conversion_params(self, rnd):
        rnd.header(self.t("header_settings"))
        rnd.text(rnd.fs, self.t("sub_settings"), 20, 76, C_TEXT_DIM)
        rnd.line(20, 92, W - 20, 92, C_BORDER)

        opts = [
            (self.t("opt_normalize"), self.t("sub_normalize"), self.normalize_volume),
            (self.t("opt_trim"), self.t("sub_trim"), self.trim_silence_flag),
            (self.t("opt_ogg"), self.t("sub_ogg"), self.convert_to_ogg),
            (self.t("opt_del_orig"), self.t("sub_del_orig"), self.delete_originals),
            (self.t("opt_lufs_preset"), "{0:.1f} LUFS".format(self.target_lufs), None),
            (self.t("opt_in_dir"), self.pc_input_dir if IS_PC else self.scan_source.upper(), None),
            (self.t("opt_out_dir"), self.pc_output_dir if IS_PC else self.out_mode, None),
            (self.t("opt_back"), "", None),
        ]

        by, rh = 98, 44
        for i, (label, sub, checked) in enumerate(opts):
            sel = (i == self.conv_sel)
            row_y = by + i * rh
            if sel:
                rnd.rect(16, row_y, W - 32, rh - 2, C_SEL_BG)
                rnd.rect(16, row_y, 4, rh - 2, C_ACCENT)

            if checked is not None:
                rnd.checkbox(32, row_y + 8, label, checked, sel)
            else:
                rnd.text(rnd.fm, label, 32, row_y + 4, C_TEXT if sel else C_TEXT_DIM)

            if sub:
                rnd.text_clipped(rnd.fs, sub, 32, row_y + 24, W - 64, C_TEXT_DIM)

            rnd.line(32, row_y + rh - 2, W - 32, row_y + rh - 2, C_BG2)

        rnd.footer([(self.t("nav_select"), "A"), (self.t("nav_back"), "ESC")])

    def _draw_confirm_process(self, rnd):
        rnd.header(self.t("header_confirm"))
        rnd.panel(32, 88, W - 64, 270, C_BORDER, C_BG2)
        rnd.text(rnd.fl, self.t("confirm_prompt"), W // 2, 95, C_ACCENT, center=True)
        rnd.text(rnd.fm, self.t("tracks_selected_count", len(self.file_selected)), W // 2, 130, C_TEXT, center=True)
        rnd.text(rnd.fs, self.t("target_vol", self.target_lufs), W // 2, 165, C_GREEN, center=True)

        if self.delete_originals:
            rnd.text(rnd.fs, self.t("warn_delete"), W // 2, 200, C_RED, center=True)

        btn_y = H - 104
        rnd.button(80, btn_y, 200, 44, self.t("btn_start"), True)
        rnd.button(360, btn_y, 200, 44, self.t("btn_cancel"), False)
        rnd.footer([(self.t("nav_confirm"), "A"), (self.t("nav_cancel"), "ESC")])

    def _draw_confirm_delete(self, rnd):
        rnd.header(self.t("header_delete"))
        rnd.panel(40, 98, W - 80, 200, C_RED, C_BG2)
        rnd.text(rnd.fl, self.t("delete_title"), W // 2, 110, C_RED, center=True)
        rnd.text(rnd.fm, self.t("delete_body"), W // 2, 155, C_TEXT, center=True)

        btn_y = H - 100
        rnd.button(80, btn_y, 200, 40, self.t("btn_yes"), True)
        rnd.button(360, btn_y, 200, 40, self.t("btn_no"), False)
        rnd.footer([(self.t("nav_confirm"), "A"), (self.t("nav_cancel"), "ESC")])

    def _draw_processing(self, rnd):
        rnd.header(self.t("header_processing"))

        rnd.panel(16, 78, W - 32, 72, C_BORDER, C_BG2)
        eta_str = "ETA: {0}s".format(self.eta_seconds) if self.eta_seconds > 0 else "ETA: --"
        rnd.text(rnd.fs, self.t("total_progress"), 28, 84, C_ACCENT)
        rnd.text(rnd.fs, "{0}/{1} | {2}".format(self.process_completed_count, self.process_total, eta_str), W - 28, 84, C_TEXT, right=True)
        rnd.progress_bar(28, 106, W - 56, 24, self.overall_pct, color=C_ACCENT)

        rnd.panel(16, 156, W - 32, 70, C_BORDER, C_BG2)
        rnd.text_clipped(rnd.fm, self.process_msg, 28, 162, W - 56, C_TEXT)
        rnd.progress_bar(28, 192, W - 56, 20, self.current_track_pct, color=C_GREEN, label=self.t("track_progress", self.current_track_pct))

        log_y = 232
        rnd.panel(16, log_y, W - 32, H - log_y - 48, C_BORDER, (5, 5, 10, 255))
        rnd.text(rnd.fs, self.t("console_engine"), 26, log_y + 6, C_CYAN)
        rnd.line(16, log_y + 24, W - 16, log_y + 24, C_BORDER)

        line_y = log_y + 28
        for line in self.process_log_lines[-7:]:
            col = C_RED if "ERR" in line else (C_GREEN if "OK" in line or "complete" in line.lower() else C_TEXT_DIM)
            rnd.text_clipped(rnd.fs, line, 26, line_y, W - 52, col)
            line_y += 18

        if self.process_done:
            rnd.footer([(self.t("nav_select"), "A"), (self.t("nav_back"), "ESC")])
        else:
            rnd.footer([(self.t("nav_cancel"), "ESC")])

    def _draw_result(self, rnd):
        rnd.header(self.t("header_results"))
        rnd.panel(20, 64, W - 40, H - 140, C_BORDER, C_BG2)
        lines = self.result_msg.split("\n")
        for i, line in enumerate(lines[:18]):
            color = C_GREEN if "[OK]" in line or "COMPLETE" in line else (C_RED if "[ERR]" in line else C_TEXT)
            rnd.text(rnd.fs if i > 0 else rnd.fm, line, 36, 78 + i * 20, color)
        rnd.footer([("OK", "A/ESC"), (self.t("opt_log"), "Y")])

    def _draw_view_log(self, rnd):
        rnd.header(self.t("header_log"))
        rnd.panel(16, 78, W - 32, H - 110, C_BORDER, (5, 5, 10, 255))
        cnt = len(self.log_view_lines)
        start = max(0, min(self.log_view_scroll, max(0, cnt - 18)))
        for i in range(18):
            if start + i >= cnt:
                break
            rnd.text_clipped(rnd.fs, self.log_view_lines[start + i], 26, 86 + i * 18, W - 52, C_TEXT)
        rnd.scrollbar(W - 20, 82, H - 118, cnt, 18, start)
        rnd.footer([(self.t("nav_scroll"), "FRECCE"), (self.t("nav_close"), "ESC/A")])

    def _draw_about(self, rnd):
        rnd.header(self.t("header_about"))
        # Layout ottimizzato con spacing fisso
        rnd.panel(50, 90, W - 100, H - 180, C_BORDER, C_BG2)
        rnd.line(50, 90, W - 50, 90, C_CYAN)

        rnd.text(rnd.fl, self.t("about_title"), W // 2, 120, C_ACCENT, center=True)
        rnd.line(60, 154, W - 60, 154, C_BORDER)

        rnd.text(rnd.fm, self.t("about_desc_1"), W // 2, 178, C_TEXT, center=True)
        rnd.text(rnd.fm, self.t("about_desc_2"), W // 2, 218, C_TEXT, center=True)
        rnd.text(rnd.fs, self.t("about_desc_3"), W // 2, 264, C_TEXT_DIM, center=True)
        rnd.text(rnd.fs, self.t("about_desc_4"), W // 2, 294, C_TEXT_DIM, center=True)
        rnd.text(rnd.fs, self.t("about_desc_5"), W // 2, 324, C_TEXT_DIM, center=True)

        rnd.line(60, 360, W - 60, 360, C_BORDER)
        rnd.text(rnd.fs, self.t("about_credit"), W // 2, 380, C_GREEN, center=True)
        rnd.footer([(self.t("nav_close"), "ESC/A")])

    def _draw_confirm_exit(self, rnd):
        rnd.header(self.t("header_exit"))
        rnd.panel(32, 108, W - 64, 160, C_BORDER, C_BG2)
        rnd.text(rnd.fl, "Quit BGM Normalizer?", W // 2, 148, C_TEXT, center=True)
        btn_y = H - 110
        rnd.button(80, btn_y, 200, 44, self.t("btn_yes"), True)
        rnd.button(360, btn_y, 200, 44, self.t("btn_no"), False)
        rnd.footer([(self.t("nav_confirm"), "A"), (self.t("nav_cancel"), "ESC")])

    def _draw_options(self, rnd):
        rnd.header(self.t("header_options"))
        curr_lang_label = TRANSLATIONS.get(self.lang, {}).get("lang_name", self.lang.upper())
        opts = [
            (self.t("opt_language"), curr_lang_label, self.t("sub_language")),
            (self.t("opt_theme"), THEME_NAMES.get(self.theme, self.theme), self.t("sub_theme")),
            (self.t("opt_glitch"), "ON" if self.glitch_fx else "OFF", self.t("sub_glitch")),
            (self.t("opt_log"), self.t("sub_log"), ""),
            (self.t("opt_reset"), self.t("sub_reset"), ""),
            (self.t("opt_info"), self.t("sub_info"), ""),
            (self.t("opt_back"), "", ""),
        ]
        by = 82
        for i, item in enumerate(opts):
            sel = (i == self.opt_sel)
            ry = by + i * 50
            rnd.rect(16, ry, W - 32, 46, C_SEL_BG if sel else C_BG)
            if sel:
                rnd.rect(16, ry, 4, 46, C_ACCENT)

            label = item[0]
            val = item[1] if len(item) > 2 and item[2] != "" else ""
            sub = item[2] if len(item) > 2 and item[2] != "" else item[1]

            rnd.text(rnd.fm, label, 32, ry + 4, C_TEXT)
            if val:
                rnd.text(rnd.fm, val, W - 36, ry + 4, C_GREEN if sel else C_TEXT_DIM, right=True)
            if sub:
                rnd.text_clipped(rnd.fs, sub, 32, ry + 24, W - 64, C_TEXT_DIM)
            rnd.line(16, ry + 48, W - 16, ry + 48, C_BG2)

        rnd.footer([(self.t("nav_select"), "A"), (self.t("nav_back"), "ESC")])

    def _draw_theme_select(self, rnd):
        rnd.header(self.t("header_theme"))
        for i, key in enumerate(THEME_ORDER):
            sel = (i == self.theme_screen_sel)
            ry = 110 + i * 62
            if sel:
                rnd.rect(16, ry, W - 32, 56, C_SEL_BG)
                rnd.rect(16, ry, 4, 56, C_ACCENT)
            rnd.text(rnd.fm, THEME_NAMES[key], 32, ry + 16, C_GREEN if key == self.theme else C_TEXT)
        rnd.footer([(self.t("nav_apply"), "A"), (self.t("nav_cancel"), "ESC")])

    def _draw_osk(self, rnd):
        rnd.header(self.osk_title)
        rnd.panel(16, 82, W - 32, 48, C_BORDER, C_BG2)
        rnd.text_clipped(rnd.fm, self.osk_text + "_", 24, 96, W - 48, C_TEXT)
        start_y = 144
        for r, row in enumerate(self.OSK_ROWS):
            if r == len(self.OSK_ROWS) - 1:
                widths = [90, 220, 90]
                x = (W - sum(widths) - 8) // 2
                for c, (lbl, w) in enumerate(zip(row, widths)):
                    sel = (r == self.osk_row and c == self.osk_col)
                    rnd.button(x, start_y + r * 54, w, 44, lbl, sel, rnd.fs)
                    x += w + 8
            else:
                cell_w = (W - 32) // 10
                for c, ch in enumerate(row):
                    sel = (r == self.osk_row and c == self.osk_col)
                    cx, cy = 16 + c * cell_w, start_y + r * 54
                    rnd.button(cx, cy, cell_w - 2, 44, ch.upper(), sel, rnd.fm)
        rnd.footer([(self.t("nav_type"), "A"), (self.t("nav_cancel"), "ESC")])

# =============================================================================
# FONT LOADER & MAIN LOOP
# =============================================================================
def find_font():
    # Priorita' assoluta al font locale
    if os.path.exists(FONT_REGULAR):
        return FONT_REGULAR
    # Fallback a font di sistema
    candidates = [
        "/mnt/mmc/MUOS/application/.terminal/res/SourceCodePro-Regular.ttf",
        "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def main():
    # --- CONTROLLO FONT ---
    # font.ttf e' OBBLIGATORIO (UI principale)
    if not os.path.exists(FONT_REGULAR):
        log("ERRORE CRITICO: font.ttf mancante in {0}".format(APP_DIR))
        print("ERRORE: font.ttf mancante. Copia un font TTF nella cartella dell'app.")
        sys.exit(1)
    # fontbgm.ttf e fontnorm.ttf sono OPZIONALI (header anime)
    if not os.path.exists(FONT_BGM):
        log("AVVISO: fontbgm.ttf non trovato, uso fallback per titolo BGM")
    if not os.path.exists(FONT_NORM):
        log("AVVISO: fontnorm.ttf non trovato, uso fallback per Normalizer")
    log("Font check completato.")

    os.environ["SDL_VIDEODRIVER"], os.environ["DISPLAY"] = "x11", ":0"
    for driver in ["x11", "directfb", "fbcon", ""]:
        if driver:
            os.environ["SDL_VIDEODRIVER"] = driver
        else:
            os.environ.pop("SDL_VIDEODRIVER", None)
        if SDL2.SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) == 0:
            break

    SDL2.SDL_ShowCursor(0)
    window = SDL2.SDL_CreateWindow(b"BGM Normalizer v8.6", 0x1FFF0000, 0x1FFF0000, W, H, SDL_WINDOW_SHOWN)
    renderer = SDL2.SDL_CreateRenderer(ctypes.c_void_p(window), -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_SOFTWARE)
    if not renderer:
        renderer = SDL2.SDL_CreateRenderer(ctypes.c_void_p(window), -1, SDL_RENDERER_SOFTWARE)

    SDL2.SDL_JoystickOpen(0)

    font_small = font_med = font_large = font_xl = font_bgm = font_norm = None
    if SDL2_TTF:
        SDL2_TTF.TTF_Init()
        # Font regolare (priorita' al font.ttf locale)
        font_path = FONT_REGULAR if os.path.exists(FONT_REGULAR) else find_font()
        if font_path:
            fp = font_path.encode()
            font_small = SDL2_TTF.TTF_OpenFont(fp, 16)
            font_med = SDL2_TTF.TTF_OpenFont(fp, 22)
            font_large = SDL2_TTF.TTF_OpenFont(fp, 28)
            font_xl = SDL2_TTF.TTF_OpenFont(fp, 40)
        # Font BGM massiccio (anime title)
        if os.path.exists(FONT_BGM):
            font_bgm = SDL2_TTF.TTF_OpenFont(FONT_BGM.encode(), 48)
            log("Font BGM caricato: {0}".format(FONT_BGM))
        else:
            log("Font BGM non trovato, uso fallback")
        # Font Normalizer pixel
        if os.path.exists(FONT_NORM):
            font_norm = SDL2_TTF.TTF_OpenFont(FONT_NORM.encode(), 20)
            log("Font Normalizer caricato: {0}".format(FONT_NORM))
        else:
            log("Font Normalizer non trovato, uso fallback")

    rnd = Renderer(ctypes.c_void_p(renderer), ctypes.c_void_p(font_small), ctypes.c_void_p(font_med), ctypes.c_void_p(font_large), ctypes.c_void_p(font_xl), ctypes.c_void_p(font_bgm), ctypes.c_void_p(font_norm))
    app = App()
    event = SDL_Event()

    while app.running:
        while SDL2.SDL_PollEvent(ctypes.byref(event)):
            t = event.type
            if t == SDL_QUIT:
                PLAYER.stop()
                app.running = False
            elif time.time() < app.input_lock_until:
                continue
            elif t == SDL_KEYDOWN and IS_PC:
                sym = event.key.keysym.sym
                if sym == SDLK_UP: app.handle_input("UP")
                elif sym == SDLK_DOWN: app.handle_input("DOWN")
                elif sym == SDLK_LEFT: app.handle_input("LEFT")
                elif sym == SDLK_RIGHT: app.handle_input("RIGHT")
                elif sym in (SDLK_RETURN, SDLK_SPACE, SDLK_a): app.handle_input("CONFIRM")
                elif sym in (SDLK_ESCAPE, SDLK_b): app.handle_input("BACK")
                elif sym == SDLK_x: app.handle_input("TOGGLE_SELECT")
                elif sym == SDLK_y: app.handle_input("TOGGLE_INFO")
                elif sym == SDLK_p: app.handle_input("PREVIEW")
                elif sym == SDLK_f: app.handle_input("FILTER_SELECT")
                elif sym == SDLK_r: app.handle_input("RESCAN")
                elif sym == SDLK_PAGEUP: app.handle_input("PAGE_UP")
                elif sym == SDLK_PAGEDOWN: app.handle_input("PAGE_DOWN")
            elif t == SDL_JOYBUTTONDOWN and IS_MUOS:
                btn = event.jbutton.button
                if btn in BTN_A_CODES: app.handle_input("CONFIRM")
                elif btn in BTN_B_CODES: app.handle_input("BACK")
                elif btn in BTN_X_CODES: app.handle_input("TOGGLE_SELECT")
                elif btn in BTN_Y_CODES: app.handle_input("TOGGLE_INFO")
                elif btn in BTN_START_CODES: app.handle_input("PREVIEW")
                elif btn in BTN_L1_CODES: app.handle_input("FILTER_SELECT")
                elif btn in BTN_R1_CODES: app.handle_input("PAGE_DOWN")
            elif t == SDL_JOYHATMOTION and IS_MUOS:
                val = event.jhat.value
                if val == HAT_UP: app.handle_input("UP")
                elif val == HAT_DOWN: app.handle_input("DOWN")

        app.draw(rnd)
        SDL2.SDL_Delay(16)

    if SDL2_TTF:
        if font_small: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_small))
        if font_med: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_med))
        if font_large: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_large))
        if font_xl: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_xl))
        if font_bgm: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_bgm))
        if font_norm: SDL2_TTF.TTF_CloseFont(ctypes.c_void_p(font_norm))
        SDL2_TTF.TTF_Quit()
    SDL2.SDL_DestroyRenderer(ctypes.c_void_p(renderer))
    SDL2.SDL_DestroyWindow(ctypes.c_void_p(window))
    SDL2.SDL_Quit()

if __name__ == "__main__":
    main()
