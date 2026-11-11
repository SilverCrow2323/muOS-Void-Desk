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
import re
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


def _decode_mount_field(value):
    """Decode the octal escapes used by /proc/mounts and losetup output."""
    return re.sub(
        r"\\([0-7]{3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


def _normal_path(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def mounts():
    try:
        with open("/proc/mounts") as stream:
            return stream.read().splitlines()
    except OSError:
        return []


def is_mounted(path):
    target = _normal_path(path)
    for line in mounts():
        fields = line.split()
        if len(fields) > 1 and _normal_path(_decode_mount_field(fields[1])) == target:
            return True
    return False


def is_mounted_rw(path):
    """Return whether the exact mountpoint is mounted read/write."""
    target = _normal_path(path)
    for line in mounts():
        fields = line.split()
        if len(fields) > 3 and _normal_path(_decode_mount_field(fields[1])) == target:
            return "rw" in fields[3].split(",")
    return False


def submounts(root):
    """Return all mountpoints below root, deepest first."""
    target = _normal_path(root)
    out = []
    for line in mounts():
        fields = line.split()
        if len(fields) < 2:
            continue
        mountpoint = _normal_path(_decode_mount_field(fields[1]))
        if mountpoint == target or mountpoint.startswith(target + os.sep):
            out.append(mountpoint)
    out.sort(key=len, reverse=True)
    return out


def loop_of(img):
    """Return the loop device whose backing file exactly matches img."""
    target = _normal_path(img)
    output = _run(["losetup", "-a"]).stdout
    for line in output.splitlines():
        device, separator, details = line.partition(":")
        if not separator or not device.strip().startswith("/dev/loop"):
            continue
        opening = details.find("(")
        closing = details.rfind(")")
        if opening < 0 or closing <= opening:
            continue
        backing_file = _decode_mount_field(details[opening + 1:closing])
        if _normal_path(backing_file) == target:
            return device.strip()
    return None


def loop_is_mounted(device):
    """Check the mount source field exactly, avoiding loop1/loop10 matches."""
    for line in mounts():
        fields = line.split()
        if fields and fields[0] == device:
            return True
    return False


def umount_tree(mnt, img=None):
    """Unmount all mounts below mnt and release its loop when possible.

    Returns True only when the root mountpoint is no longer mounted.
    """
    for path in submounts(mnt):
        if _call(["umount", path]) != 0:
            _call(["umount", "-l", path])
    if img:
        device = loop_of(img)
        if device and not loop_is_mounted(device):
            _call(["losetup", "-d", device])
    return not is_mounted(mnt)


def free_loop():
    r = _run(["losetup", "-f"])
    dev = r.stdout.strip()
    return dev if dev.startswith("/dev/loop") else None


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
        return False, "immagine missing: %s" % img

    if ro:
        attempts = [["-o", "ro"], ["-o", "ro,noload"], []]
        fallback_opts = ["loop,ro", "loop,ro,noload", "loop"]
    else:
        attempts = [[]]
        fallback_opts = ["loop"]

    # 1) loop esplicito (riuso quello gia' associato, se c'e')
    dev = loop_of(img)
    detach = False
    if dev and loop_is_mounted(dev):
        return False, "immagine gia' montata tramite %s; chiudere la sessione esistente" % dev
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
    if dev and not loop_is_mounted(dev):
        return _call(["losetup", "-d", dev]) == 0
    return False
