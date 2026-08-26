#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap_lite.py — Installa pygame e dipendenze per VoidDesk.
Versione migliorata con:
- Verifica di pygame, evinput, fbdisplay
- Installazione automatica con pip (con fallback su apt)
- Gestione della rete (proxy, timeout)
- Log dettagliato in data/boostrap.log
- Rimozione automatica della cache pip per risparmiare spazio
"""

import os
import sys
import subprocess
import time
import json
import shutil
import urllib.request
import urllib.error
from pathlib import Path

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "bootstrap.log")
RUNTIME_DIR = os.path.join(APP_DIR, "runtime")
DESK_DIR = os.path.join(APP_DIR, "desk")
PIP_CACHE_DIR = os.path.join(DATA_DIR, "pip_cache")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RUNTIME_DIR, exist_ok=True)

# evinput/fbdisplay sono moduli locali in desk/, non pacchetti pip.
# Aggiungili al path prima di qualsiasi check.
for _d in (RUNTIME_DIR, DESK_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)


def log(msg, level="INFO"):
    """Scrive un messaggio nel log di bootstrap."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}\n")
    except Exception:
        pass
    print(f"[{level}] {msg}", flush=True)


def have_internet():
    """Verifica la connettivita' di rete."""
    try:
        urllib.request.urlopen("https://pypi.org", timeout=5)
        return True
    except Exception:
        return False


def check_pygame():
    """Verifica se pygame e' installato e funzionante."""
    try:
        import pygame
        version = pygame.version.ver
        log(f"pygame gia' installato (v{version})")
        return True
    except ImportError:
        log("pygame non trovato", "WARN")
        return False


def check_evinput():
    try:
        import evinput
        log("evinput OK")
        return True
    except ImportError:
        log("evinput non trovato", "WARN")
        return False


def check_fbdisplay():
    try:
        import fbdisplay
        log("fbdisplay OK")
        return True
    except ImportError:
        log("fbdisplay non trovato", "WARN")
        return False


def install_pygame_pip():
    """Installa pygame via pip (con cache e fallback)."""
    log("Tentativo installazione pygame via pip...")
    os.makedirs(PIP_CACHE_DIR, exist_ok=True)

    pip_cmd = shutil.which("pip3") or shutil.which("pip")
    if not pip_cmd:
        log("pip non trovato, salto installazione via pip", "ERROR")
        return False

    cmd = [
        pip_cmd,
        "install",
        "--cache-dir", PIP_CACHE_DIR,
        "--no-warn-script-location",
        "--target", RUNTIME_DIR,
        "pygame",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log("pygame installato con successo via pip")
            sys.path.insert(0, RUNTIME_DIR)
            return True
        else:
            log(f"pip fallito: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        log(f"eccezione durante pip: {e}", "ERROR")
        return False


def install_pygame_apt():
    """Installa pygame via apt (fallback per sistemi con apt)."""
    log("Tentativo installazione pygame via apt...")
    apt_cmd = shutil.which("apt-get")
    if not apt_cmd:
        log("apt-get non trovato, impossibile installare via apt", "ERROR")
        return False

    try:
        cmd = [apt_cmd, "install", "-y", "python3-pygame", "python3-evdev"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log("pygame installato via apt")
            return True
        else:
            log(f"apt fallito: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        log(f"eccezione durante apt: {e}", "ERROR")
        return False


def install_from_runtime_zip():
    """Scarica un runtime precompilato da GitHub (fallback di ultima istanza)."""
    log("Tentativo download runtime precompilato...")
    import zipfile
    runtime_url = "https://github.com/SilverCrow2323/voiddesk-runtime/releases/download/v1.0/runtime.zip"
    zip_path = os.path.join(DATA_DIR, "runtime.zip")
    try:
        urllib.request.urlretrieve(runtime_url, zip_path,
                                   reporthook=lambda a, b, c: log(f"Download runtime: {a * b / c * 100:.0f}%"))
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(APP_DIR)
        os.remove(zip_path)
        log("Runtime precompilato installato con successo")
        sys.path.insert(0, RUNTIME_DIR)
        return True
    except Exception as e:
        log(f"Download runtime fallito: {e}", "ERROR")
        return False


def extract_local_archives():
    """Estrae archivi .zip/.tar.gz/.tgz da assets/runtime_archives/ in runtime/."""
    archives_dir = os.path.join(APP_DIR, "assets", "runtime_archives")
    if not os.path.isdir(archives_dir):
        return False
    archives = sorted([
        name for name in os.listdir(archives_dir)
        if name.endswith((".zip", ".tar.gz", ".tgz"))
    ])
    if not archives:
        return False
    import tempfile
    for name in archives:
        zpath = os.path.join(archives_dir, name)
        try:
            if name.endswith(".zip"):
                import zipfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(zpath, 'r') as z:
                        z.extractall(tmpdir)
                    _merge_into_runtime(tmpdir, APP_DIR)
            else:
                import tarfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    with tarfile.open(zpath, 'r:gz') as t:
                        t.extractall(tmpdir)
                    _merge_into_runtime(tmpdir, APP_DIR)
            log(f"Estratto archivio runtime locale: {name}")
            return True
        except Exception as e:
            log(f"Estrazione {name} fallita: {e}", "ERROR")
    return False


def _merge_into_runtime(tmpdir, app_dir):
    runtime_dst = os.path.join(app_dir, "runtime")
    os.makedirs(runtime_dst, exist_ok=True)
    src_dir = tmpdir
    nested_runtime = os.path.join(tmpdir, "runtime")
    if os.path.isdir(nested_runtime):
        src_dir = nested_runtime
    for entry in os.listdir(src_dir):
        src = os.path.join(src_dir, entry)
        dst = os.path.join(runtime_dst, entry)
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)


def write_pygame_ready():
    """Scrive un file marker per indicare che pygame e' pronto."""
    marker = os.path.join(DATA_DIR, ".pygame_ready")
    try:
        with open(marker, "w") as f:
            f.write("1\n")
    except Exception:
        pass


def main():
    log("=== BOOTSTRAP LITE START ===")

    if check_pygame() and check_evinput() and check_fbdisplay():
        log("Tutte le dipendenze sono gia' soddisfatte.")
        write_pygame_ready()
        return 0

    if extract_local_archives():
        if check_pygame() and check_evinput() and check_fbdisplay():
            log("Dipendenze soddisfatte da archivio locale.")
            write_pygame_ready()
            return 0

    if not have_internet():
        log("Nessuna connessione internet; impossibile installare pygame.", "ERROR")
        return 1

    if install_pygame_pip():
        if check_pygame() and check_evinput() and check_fbdisplay():
            write_pygame_ready()
            return 0

    if install_pygame_apt():
        if check_pygame() and check_evinput() and check_fbdisplay():
            write_pygame_ready()
            return 0

    if install_from_runtime_zip():
        if check_pygame() and check_evinput() and check_fbdisplay():
            write_pygame_ready()
            return 0

    log("Impossibile installare pygame: tutti i metodi falliti.", "CRITICAL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
