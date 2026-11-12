#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara il runtime Pygame per muOS dagli archivi ARM64 inclusi o da PyPI."""

import glob
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

APP = Path(__file__).resolve().parents[1]
DATA = APP / "data"
RUNTIME = APP / "runtime"
WHL = DATA / "pygame.whl"
MARKER = DATA / ".pygame_ready"
SDL_TXT = DATA / "sdl_path.txt"
ARCHIVE_DIR = APP / "assets" / "runtime_archives"
BUNDLED_ARCHIVES = (
    "pygame.tar.gz",
    "pygame.libs.tar.gz",
    "pygame-2.6.1.data.tar.gz",
    "pygame-2.6.1.dist-info.tar.gz",
)

sys.path.insert(0, str(APP / "lib"))
try:
    import fbtext
    SCREEN = fbtext.Screen(title="VOIDDESK - Installazione runtime Pygame")
except Exception:
    SCREEN = None

DATA.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(msg, flush=True)
    if SCREEN:
        try:
            SCREEN.log(msg)
        except Exception:
            pass


def opener():
    ctx = ssl.create_default_context()
    # Mantiene attiva la verifica TLS di certificato e nome host per il download alternativo.
    # Al primo avvio viene normalmente usato il runtime offline incluso.
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    op.addheaders = [("User-Agent", "VoidDesk/1.5")]
    return op


def pick_wheel(op, pkg, tag, mach):
    url = "https://pypi.org/pypi/%s/json" % pkg
    with op.open(url, timeout=30) as response:
        data = json.load(response)
    for item in data.get("urls", []):
        filename = item.get("filename", "")
        if (filename.endswith(".whl") and tag in filename
                and mach in filename and "manylinux" in filename):
            return item["url"], filename, data["info"]["version"]
    return None, None, None


def download(op, url, dest):
    with op.open(url, timeout=60) as response, open(dest, "wb") as stream:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        next_pct = 0
        while True:
            chunk = response.read(262144)
            if not chunk:
                break
            stream.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct >= next_pct or done == total:
                    next_pct = pct + 20
                    log("   %d%% (%0.1f/%0.1fMB)" %
                        (pct, done / 1e6, total / 1e6))


def safe_extract_tar(archive_path, destination):
    """Extract regular files/directories only; reject traversal and links."""
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            name = member.name
            relative = PurePosixPath(name)
            if (not name or "\\" in name or relative.is_absolute()
                    or ".." in relative.parts or not relative.parts):
                raise ValueError("elemento non sicuro nell'archivio: %r" % name)
            target = (root / Path(*relative.parts)).resolve()
            if target != root and root not in target.parents:
                raise ValueError("un elemento dell'archivio esce dalla cartella runtime: %r" % name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError("tipo di elemento non supportato nell'archivio: %r" % name)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("impossibile leggere l'elemento dell'archivio: %r" % name)
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            mode = 0o755 if member.mode & 0o111 else 0o644
            target.chmod(mode)


def extract_bundled_runtime(archives_dir=None, destination=None,
                            python_version=None, machine=None):
    """Estrae il runtime Pygame CPython 3.11/aarch64 incluso, senza connessione Internet."""
    archives_dir = Path(archives_dir or ARCHIVE_DIR)
    destination = Path(destination or (str(RUNTIME) + ".candidate"))
    python_version = tuple(python_version or sys.version_info[:2])
    machine = (machine or platform.machine()).lower()
    if python_version[:2] != (3, 11) or machine not in ("aarch64", "arm64"):
        return False, "il pacchetto incluso richiede CPython 3.11 e architettura aarch64"

    paths = [archives_dir / name for name in BUNDLED_ARCHIVES]
    missing = [path.name for path in paths if not path.is_file() or path.stat().st_size == 0]
    if missing:
        return False, "archivi del runtime inclusi mancanti: " + ", ".join(missing)

    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for path in paths:
            safe_extract_tar(path, destination)

        required = (
            destination / "pygame" / "__init__.py",
            destination / "pygame" / "base.cpython-311-aarch64-linux-gnu.so",
            destination / "pygame-2.6.1.dist-info" / "WHEEL",
        )
        for path in required:
            if not path.is_file():
                raise ValueError("file del runtime incluso mancante: %s" % path.name)

        libs = destination / "pygame.libs"
        if not libs.is_dir() or not any(
                item.name.startswith("libSDL2-") for item in libs.iterdir()):
            raise ValueError("librerie SDL2 del runtime incluso mancanti")

        wheel_metadata = required[2].read_text(encoding="utf-8")
        if ("cp311-cp311-manylinux2014_aarch64" not in wheel_metadata
                and "cp311-cp311-manylinux_2_17_aarch64" not in wheel_metadata):
            raise ValueError("versione ABI/piattaforma del pacchetto Pygame incluso non compatibile")
        return True, ""
    except Exception as exc:
        shutil.rmtree(destination, ignore_errors=True)
        return False, str(exc)


def verify_runtime(runtime_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(runtime_path)
    env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    env["LD_LIBRARY_PATH"] = (
        str(Path(runtime_path) / "pygame.libs") + ":"
        + env.get("LD_LIBRARY_PATH", "")
    )
    env.pop("SDL_VIDEODRIVER", None)
    try:
        return subprocess.run(
            [sys.executable, "-c",
             "import pygame,sys;sys.stdout.write(pygame.version.ver)"],
            env=env, capture_output=True, text=True, timeout=60)
    except Exception as exc:
        log("ERRORE: verifica non eseguibile: %s" % exc)
        return None


def find_system_sdl():
    patterns = [
        "/usr/lib/libSDL2-2.0.so*", "/usr/lib/libSDL2*.so*",
        "/usr/lib64/libSDL2*.so*", "/lib/libSDL2*.so*",
        "/usr/lib/aarch64-linux-gnu/libSDL2*.so*",
    ]
    hits = []
    for pattern in patterns:
        hits.extend(glob.glob(pattern))
    if os.path.isdir("/opt/muos"):
        for base, _dirs, files in os.walk("/opt/muos"):
            for filename in files:
                if filename.startswith("libSDL2-2.0.so"):
                    hits.append(os.path.join(base, filename))
    hits.sort(key=lambda path: (0 if ".so.0" in path else 1, len(path)))
    return hits


def finish_runtime(runtime_path, pygame_version, tag, machine):
    backup = APP / "runtime.previous"
    shutil.rmtree(backup, ignore_errors=True)
    if RUNTIME.exists():
        os.replace(RUNTIME, backup)
    try:
        os.replace(runtime_path, RUNTIME)
    except OSError:
        if backup.exists() and not RUNTIME.exists():
            os.replace(backup, RUNTIME)
        raise
    shutil.rmtree(backup, ignore_errors=True)

    for base, _dirs, files in os.walk(RUNTIME):
        for filename in files:
            if filename.endswith(".so") or ".so." in filename:
                try:
                    os.chmod(os.path.join(base, filename), 0o755)
                except OSError:
                    pass

    sdl = find_system_sdl()
    if sdl:
        log("Libreria SDL2 di sistema: %s" % sdl[0])
        SDL_TXT.write_text(sdl[0] + "\n", encoding="utf-8")
    else:
        log("Libreria SDL2 di sistema non trovata (verrà usata quella inclusa nel pacchetto)")
        try:
            SDL_TXT.unlink()
        except OSError:
            pass

    MARKER.write_text("Pygame %s (%s %s)\n" %
                      (pygame_version, tag, machine), encoding="utf-8")
    try:
        WHL.unlink()
    except OSError:
        pass


def main():
    log("==== AVVIO INSTALLAZIONE RUNTIME PYGAME v1.6 ====")
    tag = "cp%d%d" % sys.version_info[:2]
    machine = platform.machine()
    log("Python: %s (%s) - architettura: %s" %
        (platform.python_version(), tag, machine))

    for junk in (DATA / "rootfs", DATA / "rootfs.tar.gz"):
        if junk.is_dir():
            log("rimozione residui chroot: %s" % junk)
            shutil.rmtree(junk, ignore_errors=True)
        elif junk.is_file():
            junk.unlink()

    candidate = Path(str(RUNTIME) + ".candidate")
    log("1/4 Verifica del runtime Pygame incluso...")
    bundled, reason = extract_bundled_runtime(
        ARCHIVE_DIR, candidate, sys.version_info[:2], machine
    )
    if bundled:
        log("   Runtime ARM64/CPython 3.11 trovato: verifico il caricamento...")
        verified = verify_runtime(candidate)
        if verified is not None and verified.returncode == 0:
            log("   Pygame %s caricato correttamente (installazione offline)" % verified.stdout.strip())
            finish_runtime(candidate, verified.stdout.strip(), tag, machine)
            log("==== INSTALLAZIONE RUNTIME COMPLETATA (OFFLINE) ====")
            return 0
        detail = verified.stderr.strip()[-800:] if verified is not None else "verifica non riuscita"
        log("   Il pacchetto incluso non è caricabile su questo firmware: " + detail)
        shutil.rmtree(candidate, ignore_errors=True)
    else:
        log("   Pacchetto incluso non compatibile: %s" % reason)

    log("2/4 Ricerca di un pacchetto Pygame compatibile su PyPI...")
    opener_instance = opener()
    url = filename = version = None
    for package in ("pygame", "pygame-ce"):
        url, filename, version = pick_wheel(opener_instance, package, tag, machine)
        if url:
            log("   Trovato: %s (versione %s)" % (filename, version))
            break
    if not url:
        log("ERRORE: nessun pacchetto Pygame disponibile per %s/%s" % (tag, machine))
        return 1

    log("3/4 Download di %s..." % filename)
    try:
        download(opener_instance, url, WHL)
    except Exception as exc:
        log("ERRORE: download non riuscito: %s" % exc)
        return 1

    log("4/4 Estrazione e verifica del runtime...")
    shutil.rmtree(candidate, ignore_errors=True)
    candidate.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(WHL) as wheel:
            for info in wheel.infolist():
                relative = PurePosixPath(info.filename)
                if (relative.is_absolute() or ".." in relative.parts
                        or "\\" in info.filename):
                    raise ValueError("elemento non sicuro nel pacchetto: %s" % info.filename)
            wheel.extractall(candidate)
    except Exception as exc:
        shutil.rmtree(candidate, ignore_errors=True)
        log("ERRORE: estrazione del pacchetto non riuscita: %s" % exc)
        return 1

    verified = verify_runtime(candidate)
    if verified is None or verified.returncode != 0:
        detail = verified.stderr.strip()[-800:] if verified is not None else "verifica non riuscita"
        shutil.rmtree(candidate, ignore_errors=True)
        log("ERRORE: caricamento di Pygame non riuscito: " + detail)
        return 1

    log("   Pygame %s caricato correttamente" % verified.stdout.strip())
    finish_runtime(candidate, verified.stdout.strip(), tag, machine)
    log("==== INSTALLAZIONE RUNTIME COMPLETATA (ONLINE) ====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
