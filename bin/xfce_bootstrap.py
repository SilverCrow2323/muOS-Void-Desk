#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // xfce_bootstrap v3.0
# Installa un desktop XFCE (Ubuntu 24.04 arm64) in un'immagine ext4
# montata in loopback: funziona anche con la SD in exFAT.
# Fasi: preflight -> immagine -> ubuntu-base -> configurazione -> apt XFCE.

import gzip
import os
import shutil
import subprocess
import sys
import uuid

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
ASSETS = os.path.join(APP, "assets")
IMG_GZ = os.path.join(ASSETS, "xfce.img.gz")
IMG = os.path.join(DATA, "xfce.img")
MNT = os.path.join(DATA, "xfce_mnt")
TGZ = os.path.join(DATA, "rootfs.tar.gz")
MARKER = os.path.join(DATA, ".xfce_ready")
UB_URL = os.environ.get(
    "VOIDDESK_UB_URL",
    "https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/"
    "ubuntu-base-24.04.3-base-arm64.tar.gz")

PKGS = ("xserver-xorg-core xserver-xorg-video-fbdev xserver-xorg-input-evdev "
        "xinit x11-xserver-utils dbus dbus-x11 xfce4-session xfwm4 "
        "xfce4-panel xfce4-settings xfdesktop4 xfce4-terminal thunar "
        "qjoypad matchbox-keyboard fonts-dejavu-core ca-certificates procps nano")

sys.path.insert(0, os.path.join(APP, "desk"))
import imgmount  # noqa: E402

sys.path.insert(0, os.path.join(APP, "lib"))
try:
    import fbtext
    SCREEN = fbtext.Screen(title="VOIDDESK - installazione desktop XFCE")
except Exception:
    SCREEN = None

os.makedirs(DATA, exist_ok=True)


def log(msg):
    print(msg, flush=True)
    if SCREEN:
        try:
            SCREEN.log(msg)
        except Exception:
            pass


def sh(cmd, **kw):
    return subprocess.call(cmd, shell=isinstance(cmd, str), **kw)


mounted = imgmount.is_mounted


def umount_all():
    imgmount.umount_tree(MNT, IMG)


def bind_all():
    os.makedirs(MNT, exist_ok=True)
    if not mounted(MNT):
        ok, _e = imgmount.mount_img(IMG, MNT)
        if not ok:
            return False
    for src, dst in (("/dev", MNT + "/dev"), ("/proc", MNT + "/proc"),
                     ("/sys", MNT + "/sys")):
        os.makedirs(dst, exist_ok=True)
        if not mounted(dst):
            if src == "/proc":
                sh(["mount", "-t", "proc", "proc", dst])
            elif src == "/sys":
                sh(["mount", "-t", "sysfs", "sys", dst])
            else:
                sh(["mount", "-o", "bind", src, dst])
    if os.path.isdir("/dev/pts"):
        os.makedirs(MNT + "/dev/pts", exist_ok=True)
        if not mounted(MNT + "/dev/pts"):
            sh(["mount", "-o", "bind", "/dev/pts", MNT + "/dev/pts"])
    return True


def free_gb(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def main():
    log("==== VOIDDESK XFCE bootstrap ====")

    # ---- 0. preflight -------------------------------------------------
    log("0/5 controlli preliminari...")
    img_ok = (os.path.exists(IMG) and os.path.getsize(IMG) > 3e9
              and os.path.exists(MARKER + ".img"))
    need = 1.0 if img_ok else 5.0
    if free_gb(DATA) < need:
        log("FATAL: servono almeno %.0fGB liberi (ora: %.1fGB)"
            % (need, free_gb(DATA)))
        return 1
    if not os.path.exists(IMG_GZ):
        log("FATAL: manca assets/xfce.img.gz")
        return 1
    rc = subprocess.call(["curl", "-sI", "--max-time", "8",
                          "https://cdimage.ubuntu.com"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    if rc != 0:
        log("FATAL: rete assente (attiva il WiFi e riprova)")
        return 1

    # ---- 1. immagine ext4 ---------------------------------------------
    if os.path.exists(IMG) and os.path.getsize(IMG) > 3e9 \
            and os.path.exists(MARKER + ".img"):
        log("1/5 immagine gia' presente, salto")
    else:
        log("1/5 preparo l'immagine ext4 (4GB, alcuni minuti)...")
        try:
            with gzip.open(IMG_GZ, "rb") as src, open(IMG, "wb") as dst:
                done = 0
                nxt = 0
                while True:
                    chunk = src.read(1 << 22)
                    if not chunk:
                        break
                    dst.write(chunk)
                    done += len(chunk)
                    if done >= nxt:
                        log("   %dMB / 4096MB" % (done >> 20))
                        nxt += 512 << 20
        except Exception as e:
            log("FATAL: creazione immagine fallita: %s" % e)
            return 1
        open(MARKER + ".img", "w").close()

    log("   monto l'immagine in loopback...")
    umount_all()
    imgmount.cleanup_stale(IMG)
    os.makedirs(MNT, exist_ok=True)
    sh("modprobe loop 2>/dev/null || true")
    ok, err = imgmount.mount_img(IMG, MNT)
    if not ok:
        log("FATAL: mount loop fallito - %s" % (err or "?"))
        return 1
    log("   montata: %.1fGB liberi dentro l'immagine" % free_gb(MNT))

    try:
        # ---- 2. ubuntu-base ---------------------------------------------
        if os.path.exists(MNT + "/etc/os-release"):
            log("2/5 rootfs gia' estratto, salto")
        else:
            log("2/5 scarico ubuntu-base 24.04 arm64 (~30MB)...")
            if not (os.path.exists(TGZ) and
                    sh(["gzip", "-t", TGZ]) == 0):
                if sh(["curl", "-fL", "--retry", "2", "-o", TGZ, UB_URL]) != 0:
                    log("FATAL: download fallito")
                    return 1
            log("   estraggo nel filesystem ext4...")
            if sh("gzip -dc '%s' | tar -xf - -C '%s'" % (TGZ, MNT)) != 0:
                log("FATAL: estrazione fallita")
                return 1
            os.remove(TGZ)

        # ---- 3. configurazione --------------------------------------------
        log("3/5 configuro il sistema...")
        shutil.copy("/etc/resolv.conf", MNT + "/etc/resolv.conf")
        with open(MNT + "/etc/hosts", "w") as f:
            f.write("127.0.0.1 localhost voiddesk\n")
        with open(MNT + "/etc/hostname", "w") as f:
            f.write("voiddesk\n")
        mid = uuid.uuid4().hex
        for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            os.makedirs(os.path.dirname(MNT + p), exist_ok=True)
            with open(MNT + p, "w") as f:
                f.write(mid + "\n")
        srcd = MNT + "/etc/apt/sources.list.d"
        if os.path.isdir(srcd):
            for fn in os.listdir(srcd):
                if fn.endswith(".sources") or fn.endswith(".list"):
                    os.remove(os.path.join(srcd, fn))
        shutil.copy(os.path.join(ASSETS, "xfce", "sources.list"),
                    MNT + "/etc/apt/sources.list")
        os.makedirs(MNT + "/etc/X11", exist_ok=True)
        shutil.copy(os.path.join(ASSETS, "xfce", "xorg.conf"),
                    MNT + "/etc/X11/xorg.conf")
        os.makedirs(MNT + "/root/.qjoypad3", exist_ok=True)
        shutil.copy(os.path.join(ASSETS, "xfce", "qjoypad_sinistro.lyt"),
                    MNT + "/root/.qjoypad3/Default.lyt")
        with open(MNT + "/root/.qjoypad3/layout", "w") as f:
            f.write("Default\n")
        shutil.copy(os.path.join(ASSETS, "xfce", "xinitrc"),
                    MNT + "/root/.xinitrc")
        os.chmod(MNT + "/root/.xinitrc", 0o755)

        # ---- 4. pacchetti ---------------------------------------------
        log("4/5 installo Xorg + XFCE (~400MB, 10-20 minuti)...")
        log("    NON SPEGNERE LA CONSOLE")
        if not bind_all():
            log("FATAL: bind mount falliti")
            return 1
        env = "DEBIAN_FRONTEND=noninteractive " \
              "PATH=/usr/sbin:/usr/bin:/sbin:/bin"
        aptop = ("-o Acquire::ForceIPv4=true "
                 "-o Acquire::https::Verify-Peer=false "
                 "-o Acquire::https::Verify-Host=false "
                 "-o Acquire::Retries=2")
        if sh("chroot '%s' /bin/bash -c '%s apt-get %s update'"
              % (MNT, env, aptop)) != 0:
            log("FATAL: apt-get update fallito")
            return 1
        if sh("chroot '%s' /bin/bash -c \"%s apt-get %s install -y "
              "--no-install-recommends %s && apt-get clean\""
              % (MNT, env, aptop, PKGS)) != 0:
            log("FATAL: installazione pacchetti fallita")
            return 1

        # ---- 5. verifica ----------------------------------------------
        log("5/5 verifica...")
        for p in ("/usr/bin/startx", "/usr/bin/startxfce4",
                  "/usr/bin/qjoypad"):
            if not os.path.exists(MNT + p):
                log("FATAL: manca %s nel chroot" % p)
                return 1
        with open(MARKER, "w") as f:
            f.write("xfce ok\n")
        log("==== DESKTOP XFCE INSTALLATO ====")
        log("Avvialo da VOIDDESK -> DESKTOP XFCE")
        return 0
    finally:
        umount_all()


if __name__ == "__main__":
    sys.exit(main())
