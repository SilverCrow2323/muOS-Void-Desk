# -*- coding: utf-8 -*-
# VOIDDESK // imgmount — montaggio dell'immagine XFCE, fatto per bene.
#
# Problemi veri incontrati sul campo:
#  - "mount -o loop" non libera sempre il /dev/loopN quando si smonta:
#    dopo qualche giro i loop finiscono e il mount fallisce.
#  - il desktop lascia dentro il chroot dei bind (/mnt/mmc, /dev/snd, ...):
#    smontare solo la radice fallisce con "device busy".
# Qui: losetup esplicito, smontaggio dell'albero completo, riuso del loop
# gia' associato all'immagine.

import os
import subprocess


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=20)
    except Exception:
        class R(object):
            returncode = 1
            stdout = ""
            stderr = "comando non eseguibile"
        return R()


def _call(cmd):
    return _run(cmd).returncode


def mounts():
    try:
        return open("/proc/mounts").read().splitlines()
    except OSError:
        return []


def is_mounted(path):
    p = os.path.abspath(path)
    for ln in mounts():
        f = ln.split()
        if len(f) > 1 and f[1] == p:
            return True
    return False


def is_mounted_rw(path):
    """Come is_mounted(), ma dice anche SE è scrivibile -- is_mounted()
    da sola non lo sa, e un mount rimasto in sola lettura da un
    controllo precedente farebbe fallire una scrittura in silenzio."""
    p = os.path.abspath(path)
    for ln in mounts():
        f = ln.split()
        if len(f) > 3 and f[1] == p:
            return "rw" in f[3].split(",")
    return False


def submounts(root):
    """Tutti i punti di mount sotto root, dal piu' profondo al piu' alto."""
    r = os.path.abspath(root)
    out = []
    for ln in mounts():
        f = ln.split()
        if len(f) > 1 and (f[1] == r or f[1].startswith(r + "/")):
            out.append(f[1])
    out.sort(key=len, reverse=True)
    return out


def loop_of(img):
    """/dev/loopN gia' associato all'immagine, se c'e'."""
    img = os.path.abspath(img)
    out = _run(["losetup", "-a"]).stdout
    for ln in out.splitlines():
        if img in ln:
            return ln.split(":")[0].strip()
    return None


def free_loop():
    r = _run(["losetup", "-f"])
    dev = r.stdout.strip()
    return dev if dev.startswith("/dev/loop") else None


def umount_tree(mnt, img=None):
    """Smonta TUTTO quello che sta sotto mnt (bind del desktop compresi)
    e libera il loop. Ritorna True se alla fine mnt e' libero."""
    for p in submounts(mnt):
        if _call(["umount", p]) != 0:
            _call(["umount", "-l", p])      # lazy: meglio che restare bloccati
    if img:
        dev = loop_of(img)
        if dev:
            _call(["losetup", "-d", dev])
    return not is_mounted(mnt)


def mount_img(img, mnt, ro=False):
    """Monta l'immagine. Ritorna (ok, messaggio_errore).

    Nota importante: dopo un'installazione il journal ext4 puo' essere
    "sporco" e il kernel RIFIUTA il mount in sola lettura ("cannot mount
    read-only"). Per questo, se ro fallisce, si prova ro+noload e infine
    lettura/scrittura (che riproduce il journal e lo ripulisce).
    """
    os.makedirs(mnt, exist_ok=True)
    if is_mounted(mnt):
        return True, ""
    if not os.path.exists(img):
        return False, "immagine assente: %s" % img

    if ro:
        attempts = [["-o", "ro"], ["-o", "ro,noload"], []]
        fallback_opts = ["loop,ro", "loop,ro,noload", "loop"]
    else:
        attempts = [[]]
        fallback_opts = ["loop"]

    # 1) loop esplicito (riuso quello gia' associato, se c'e')
    dev = loop_of(img)
    detach = False
    if dev is None:
        dev = free_loop()
        if dev:
            if _run(["losetup", dev, img]).returncode == 0:
                detach = True
            else:
                dev = None
    err = "nessun /dev/loop libero"
    if dev:
        for opts in attempts:
            r = _run(["mount"] + opts + [dev, mnt])
            if r.returncode == 0:
                return True, ""
            err = (r.stderr or r.stdout).strip() or err
        if detach:
            _call(["losetup", "-d", dev])

    # 2) ripiego classico (sistemi senza losetup usabile)
    for o in fallback_opts:
        r = _run(["mount", "-o", o, img, mnt])
        if r.returncode == 0:
            return True, ""
        err = (r.stderr or r.stdout).strip() or err
    return False, err


def loop_count():
    out = _run(["losetup", "-a"]).stdout
    return len([l for l in out.splitlines() if l.strip()])


def cleanup_stale(img):
    """Libera i loop rimasti attaccati all'immagine ma non montati."""
    dev = loop_of(img)
    if dev and not any(dev in ln for ln in mounts()):
        _call(["losetup", "-d", dev])
        return True
    return False
