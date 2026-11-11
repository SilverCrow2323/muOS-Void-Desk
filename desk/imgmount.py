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
    """Read the mount table or raise; unreadable state is never 'unmounted'."""
    with open("/proc/mounts") as stream:
        return stream.read().splitlines()


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
    """Return the exact backing loop, raising if losetup state is unavailable."""
    target = _normal_path(img)
    result = _run(["losetup", "-a"])
    if result.returncode != 0:
        raise OSError(result.stderr or "losetup -a failed")
    output = result.stdout
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


def _umount_tree_impl(mnt, img=None):
    """Unmount a mount tree and verify that no mount or loop remains.

    A lazy unmount is only a fallback attempt, not proof of cleanup. The
    function returns False while any descendant mount remains or while the
    image's loop device cannot be detached.
    """
    for path in submounts(mnt):
        if _call(["umount", path]) != 0:
            _call(["umount", "-l", path])

    # Check the whole tree, not only the root: a lazy-detached child can
    # otherwise be left behind while the root appears to be gone.
    if submounts(mnt) or is_mounted(mnt):
        return False

    if img:
        device = loop_of(img)
        if device:
            if loop_is_mounted(device):
                return False
            if _call(["losetup", "-d", device]) != 0:
                return False
            # losetup may defer detach while the kernel still holds a ref.
            if loop_of(img) is not None:
                return False

    return not submounts(mnt) and not is_mounted(mnt)


def umount_tree(mnt, img=None):
    """Return False when cleanup cannot be verified, including I/O errors."""
    try:
        return _umount_tree_impl(mnt, img)
    except OSError:
        return False


def free_loop():
    r = _run(["losetup", "-f"])
    if r.returncode != 0:
        raise OSError(r.stderr or "losetup -f failed")
    dev = r.stdout.strip()
    return dev if dev.startswith("/dev/loop") else None


def _mount_img_impl(img, mnt, ro=False):
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

    # 1) Prefer an explicitly managed loop device. Never start the
    # mount -o loop fallback while a failed explicit loop is still attached:
    # mount(8) may allocate a second loop for the same backing image.
    dev = loop_of(img)
    owned_loop = False
    if dev and loop_is_mounted(dev):
        return False, "immagine gia' montata tramite %s; chiudere la sessione esistente" % dev

    if dev is None:
        candidate = free_loop()
        if candidate:
            attached = _run(["losetup", candidate, img])
            if attached.returncode == 0:
                dev = candidate
                owned_loop = True
            else:
                # A failed attach command can still leave a device configured
                # on unusual backends or after a partial operation. Never use
                # the classic loop fallback while that state is ambiguous.
                dangling = loop_of(img)
                if dangling:
                    return False, (
                        "losetup ha fallito ma l'immagine risulta associata a "
                        "%s; fallback loop annullato" % dangling
                    )

    err = "nessun /dev/loop libero"
    if dev:
        for opts in attempts:
            result = _run(["mount"] + opts + [dev, mnt])
            if result.returncode == 0:
                return True, ""
            err = (result.stderr or result.stdout).strip() or err

        if not owned_loop:
            return False, (
                "loop %s gia' associato all'immagine ma non montabile; "
                "fallback loop evitato per non creare un secondo device: %s"
                % (dev, err)
            )

        if _call(["losetup", "-d", dev]) != 0:
            return False, (
                "impossibile sganciare il loop %s dopo il mount fallito; "
                "fallback loop annullato: %s" % (dev, err)
            )
        if loop_of(img) is not None:
            return False, (
                "il loop dell'immagine risulta ancora associato dopo il detach; "
                "fallback loop annullato: %s" % err
            )

    # 2) Classical fallback is safe only when no loop for this image remains.
    for option in fallback_opts:
        result = _run(["mount", "-o", option, img, mnt])
        if result.returncode == 0:
            return True, ""
        err = (result.stderr or result.stdout).strip() or err

    # A failed mount -o loop should normally release its own loop. Verify
    # that assumption; if it did not, clean only an unmounted stale device.
    fallback_dev = loop_of(img)
    if fallback_dev:
        if loop_is_mounted(fallback_dev):
            return False, (
                "il fallback ha fallito ma l'immagine risulta ancora montata "
                "tramite %s: %s" % (fallback_dev, err)
            )
        if _call(["losetup", "-d", fallback_dev]) != 0:
            return False, (
                "il fallback ha lasciato il loop %s occupato: %s"
                % (fallback_dev, err)
            )
        if loop_of(img) is not None:
            return False, (
                "il loop %s e' ancora associato dopo la pulizia del fallback: %s"
                % (fallback_dev, err)
            )

    return False, err


def mount_img(img, mnt, ro=False):
    """Mount an image, failing closed when mount/loop state cannot be read."""
    try:
        return _mount_img_impl(img, mnt, ro)
    except OSError as exc:
        return False, "impossibile verificare lo stato mount/loop: %s" % exc


def loop_count():
    out = _run(["losetup", "-a"]).stdout
    return len([l for l in out.splitlines() if l.strip()])


def cleanup_stale(img):
    """Release an unmounted stale loop; return False if state cannot be read."""
    try:
        dev = loop_of(img)
        if dev and not loop_is_mounted(dev):
            return _call(["losetup", "-d", dev]) == 0
    except OSError:
        return False
    return False
