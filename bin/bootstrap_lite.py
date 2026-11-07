#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK bootstrap-lite v1.4
# Niente chroot: scarica il wheel pygame precompilato adatto a questo
# python/arch e lo scompatta in <app>/runtime. Funziona anche su exFAT.

import glob
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
try:
    import fbtext
    SCREEN = fbtext.Screen(title="VOIDDESK - installazione runtime pygame")
except Exception:
    SCREEN = None

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
RUNTIME = os.path.join(APP, "runtime")
WHL = os.path.join(DATA, "pygame.whl")
MARKER = os.path.join(DATA, ".pygame_ready")
SDL_TXT = os.path.join(DATA, "sdl_path.txt")

os.makedirs(DATA, exist_ok=True)


def log(msg):
    print(msg, flush=True)
    if SCREEN:
        try:
            SCREEN.log(msg)
        except Exception:
            pass


def opener():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False          # CA bundle vecchi sui firmware
    ctx.verify_mode = ssl.CERT_NONE
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    op.addheaders = [("User-Agent", "VoidDesk/1.4")]
    return op


def pick_wheel(op, pkg, tag, mach):
    url = "https://pypi.org/pypi/%s/json" % pkg
    with op.open(url, timeout=30) as r:
        d = json.load(r)
    for f in d.get("urls", []):
        n = f.get("filename", "")
        if (n.endswith(".whl") and tag in n and mach in n
                and "manylinux" in n):
            return f["url"], n, d["info"]["version"]
    return None, None, None


def download(op, url, dest):
    download.next_pct = 0
    with op.open(url, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct >= download.next_pct or done == total:
                    download.next_pct = pct + 20
                    log("   %d%% (%0.1f/%0.1fMB)" %
                        (pct, done / 1e6, total / 1e6))


def find_system_sdl():
    pats = [
        "/usr/lib/libSDL2-2.0.so*", "/usr/lib/libSDL2*.so*",
        "/usr/lib64/libSDL2*.so*", "/lib/libSDL2*.so*",
        "/usr/lib/aarch64-linux-gnu/libSDL2*.so*",
    ]
    hits = []
    for p in pats:
        hits.extend(glob.glob(p))
    for base, _dirs, files in os.walk("/opt/muos"):
        for fn in files:
            if fn.startswith("libSDL2-2.0.so"):
                hits.append(os.path.join(base, fn))
    # preferisce il .so.0 "vero"
    hits.sort(key=lambda h: (0 if ".so.0" in h else 1, len(h)))
    return hits


def main():
    log("==== VOIDDESK BOOTSTRAP-LITE start ====")
    tag = "cp%d%d" % sys.version_info[:2]
    mach = platform.machine()
    log("python: %s (%s) - arch: %s" % (
        platform.python_version(), tag, mach))

    # pulizia dei resti del vecchio approccio chroot (inutilizzabile su exFAT)
    for junk in (os.path.join(DATA, "rootfs"),
                 os.path.join(DATA, "rootfs.tar.gz")):
        if os.path.isdir(junk):
            log("pulizia residui chroot: %s" % junk)
            shutil.rmtree(junk, ignore_errors=True)
        elif os.path.isfile(junk):
            os.remove(junk)

    op = opener()
    log("1/4 cerco il wheel pygame per %s/%s su PyPI..." % (tag, mach))
    url = name = ver = None
    for pkg in ("pygame", "pygame-ce"):
        url, name, ver = pick_wheel(op, pkg, tag, mach)
        if url:
            log("   trovato: %s (v%s)" % (name, ver))
            break
    if not url:
        log("FATAL: nessun wheel pygame per %s/%s" % (tag, mach))
        return 1

    log("2/4 scarico %s ..." % name)
    try:
        download(op, url, WHL)
    except Exception as e:
        log("FATAL: download fallito: %s" % e)
        return 1

    log("3/4 scompatto in %s ..." % RUNTIME)
    shutil.rmtree(RUNTIME, ignore_errors=True)
    os.makedirs(RUNTIME, exist_ok=True)
    try:
        with zipfile.ZipFile(WHL) as z:
            z.extractall(RUNTIME)
    except Exception as e:
        log("FATAL: estrazione wheel fallita: %s" % e)
        return 1
    for base, _d, files in os.walk(RUNTIME):
        for fn in files:
            if fn.endswith(".so") or ".so." in fn:
                try:
                    os.chmod(os.path.join(base, fn), 0o755)
                except OSError:
                    pass

    log("4/4 verifica import pygame...")
    env = dict(os.environ)
    env["PYTHONPATH"] = RUNTIME
    env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    env.pop("SDL_VIDEODRIVER", None)
    try:
        out = subprocess.run(
            [sys.executable, "-c",
             "import pygame,sys;sys.stdout.write(pygame.version.ver)"],
            env=env, capture_output=True, text=True, timeout=60)
    except Exception as e:
        log("FATAL: verifica non eseguibile: %s" % e)
        return 1
    if out.returncode != 0:
        log("FATAL: import pygame fallito:")
        log(out.stderr.strip()[-800:])
        return 1
    log("   pygame %s OK" % out.stdout.strip())

    sdl = find_system_sdl()
    if sdl:
        log("libSDL2 di sistema: %s" % sdl[0])
        with open(SDL_TXT, "w") as f:
            f.write(sdl[0] + "\n")
    else:
        log("libSDL2 di sistema: non trovata (si usera' quella del wheel)")
        try:
            os.remove(SDL_TXT)
        except OSError:
            pass

    with open(MARKER, "w") as f:
        f.write("pygame %s (%s %s)\n" % (out.stdout.strip(), tag, mach))
    try:
        os.remove(WHL)
    except OSError:
        pass
    log("==== VOIDDESK BOOTSTRAP-LITE completato ====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
