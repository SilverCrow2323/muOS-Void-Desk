# ============================================================================
#  VOID DESK — Utility Functions
#  Extracted from main.py section [D]
# ============================================================================
import os
import re
import subprocess
import time
import collections
import pygame

from desk.const import (
    FONT_PATH, FONT_BOLD_PATH, FONT_MONO_PATH, FONT_MONO_BOLD_PATH,
    FONT_DISPLAY_PATH, DATA,
)


def font(size):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.Font(None, size)


def font_bold(size):
    try:
        return pygame.font.Font(FONT_BOLD_PATH, size)
    except Exception:
        f = font(size)
        f.set_bold(True)
        return f


def font_mono(size, bold=False):
    path = FONT_MONO_BOLD_PATH if bold else FONT_MONO_PATH
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return font_bold(size) if bold else font(size)


def font_display(size):
    try:
        return pygame.font.Font(FONT_DISPLAY_PATH, size)
    except Exception:
        return font_bold(size)


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


DOPPEL_DISC_RE = re.compile(
    r"[\(\[]?\s*(?:disc|disk|cd|part)\s*([0-9]+)\s*[\)\]]?",
    re.IGNORECASE)


ROMAN_MAP = [("XIII", "13"), ("XII", "12"), ("XI", "11"), ("IX", "9"),
             ("VIII", "8"), ("VII", "7"), ("VI", "6"), ("IV", "4"),
             ("X", "10"), ("V", "5"), ("III", "3"), ("II", "2"),
             ("I", "1")]


def doppel_roman_to_arabic(text):
    """Converte i numeri romani isolati (parole intere, non dentro
    ad altre lettere) in cifre arabe -- cosi' 'IV' e '4' della
    stessa serie finiscono nella stessa chiave."""
    words = text.split(" ")
    out = []
    for w in words:
        replaced = False
        for roman, arabic in ROMAN_MAP:
            if w == roman:
                out.append(arabic)
                replaced = True
                break
        if not replaced:
            out.append(w)
    return " ".join(out)


def doppel_norm(filename):
    """Chiave di confronto per un file ROM: (nome_ripulito, disco).
    Due file con la STESSA chiave sono doppioni (anche con estensioni
    diverse); con lo stesso nome ma disco diverso NON lo sono mai --
    e' cosi' che Shenmue Disc 1 e Disc 2 restano separati.

    Ignora tag tra parentesi tonde/quadre (regione, versione,
    traduzione, hack: (T2), (USA), [T+Eng], (T2 V2)...) e tratta
    underscore/trattini/punti-tra-parole come spazi, cosi' 'FF_IV',
    'FF IV', 'FF-IV' e 'FF.IV (T2)' finiscono tutti nella stessa
    chiave."""
    base, _ext = os.path.splitext(filename)
    m = DOPPEL_DISC_RE.search(base)
    disc = m.group(1) if m else None
    key = DOPPEL_DISC_RE.sub("", base)
    key = re.sub(r"\([^)]*\)", "", key)
    key = re.sub(r"\[[^\]]*\]", "", key)
    key = re.sub(r"[_\-.]", " ", key)
    key = re.sub(r"([A-Za-z])(\d)", r"\1 \2", key)
    key = re.sub(r"\s+", " ", key).strip().lower()
    key = doppel_roman_to_arabic(key.upper()).lower()
    key = key.rstrip(" -_")
    return key, disc


def doppel_group(filenames):
    """Raggruppa un elenco di nomi file per (chiave, disco). Ritorna
    solo i gruppi con 2+ file: quelli sono i doppioni veri."""
    groups = {}
    for fn in filenames:
        k = doppel_norm(fn)
        groups.setdefault(k, []).append(fn)
    return {k: v for k, v in groups.items() if len(v) > 1}


def terminal_id_generate():
    """AnnoGiornoMinutiSecondiOreMese -- verificato esatto sull'esempio
    dato: 18:36:55 del 28/07/2026 -> 20262836551807."""
    t = time.localtime()
    return "%04d%02d%02d%02d%02d%02d" % (
        t.tm_year, t.tm_mday, t.tm_min, t.tm_sec, t.tm_hour, t.tm_mon)


def safe_read_file(path, default="", errors="strict"):
    """Safely read file content with automatic cleanup.
    
    Prevents file descriptor leaks on error.
    
    Args:
        path: File path to read
        default: Default value if read fails
        errors: Error handling mode ('strict', 'replace', 'ignore')
    
    Returns:
        File content string, or default if error
    """
    try:
        with open(path, 'r', encoding='utf-8', errors=errors) as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return default
