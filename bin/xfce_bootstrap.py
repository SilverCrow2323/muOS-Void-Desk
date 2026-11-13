#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // xfce_bootstrap v3.0
# Installa un desktop XFCE (Ubuntu 24.04 arm64) in un'immagine ext4
# montata in loopback: funziona anche con la SD in exFAT.
# Fasi: preflight -> immagine -> ubuntu-base -> configurazione -> apt XFCE.

import gzip
import json
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

STATUS_FILE = os.path.join(DATA, ".xfce_bootstrap_state.json")
os.makedirs(DATA, exist_ok=True)


def log(msg):
    # LÖVE owns the framebuffer; the UI reads this structured status.
    print(msg, flush=True)


def report(progress, phase, message, detail="", status="running",
           animation="loading", severity="info"):
    state = {
        "progress": max(0, min(100, int(progress))),
        "phase": str(phase)[:48],
        "message": str(message)[:240],
        "detail": str(detail)[:500],
        "status": status,
        "animation": animation,
        "severity": severity,
        "indeterminate": status == "running" and int(progress) <= 0,
        "can_background": True,
    }
    temporary = STATUS_FILE + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATUS_FILE)
    except OSError as exc:
        try:
            os.remove(temporary)
        except OSError:
            pass
        log("WARNING: cannot publish live operation status: %s" % exc)


def fail(message, progress=0, phase="FAILED"):
    log("ERROR: " + message)
    report(progress, phase, message, status="failed",
           animation="verify", severity="error")
    return 1


def sh(cmd, **kw):
    return subprocess.call(cmd, shell=isinstance(cmd, str), **kw)


mounted = imgmount.is_mounted


def umount_all():
    return imgmount.umount_tree(MNT, IMG)


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
    log("==== VOID DESK XFCE BOOTSTRAP ====")
    report(1, "PRE-FLIGHT", "Checking storage, image and network",
           "XFCE needs enough free space before preparing its desktop image.",
           animation="loading")

    # ---- 0. preflight -------------------------------------------------
    log("0/5 Pre-flight checks...")
    img_ok = (os.path.exists(IMG) and os.path.getsize(IMG) > 3e9
              and os.path.exists(MARKER + ".img"))
    need = 1.0 if img_ok else 5.0
    available = free_gb(DATA)
    if available < need:
        return fail("Not enough free storage. Need at least %.0f GB; only %.1f GB is available." % (need, available), 2, "STORAGE CHECK")
    if not os.path.exists(IMG_GZ):
        log("FATAL: manca assets/xfce.img.gz")
        return 1
    report(5, "NETWORK CHECK", "Checking connection to Ubuntu mirrors",
           "The installer must download the Ubuntu base image and desktop packages.",
           animation="download")
    rc = subprocess.call(["curl", "-sI", "--max-time", "8",
                          "https://cdimage.ubuntu.com"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    if rc != 0:
        return fail("No connection to cdimage.ubuntu.com. Connect to Wi-Fi and retry.", 5, "NETWORK CHECK")

    # ---- 1. immagine ext4 ---------------------------------------------
    if os.path.exists(IMG) and os.path.getsize(IMG) > 3e9 \
            and os.path.exists(MARKER + ".img"):
        log("1/5 Existing desktop image found; skipping.")
        report(18, "DESKTOP IMAGE", "Existing desktop image found", "The current ext4 image will be reused.", animation="verify")
    else:
        log("1/5 Preparing the 4 GB ext4 desktop image...")
        report(8, "DESKTOP IMAGE", "Extracting the desktop image", "Writing the ext4 image to the application data directory.", animation="extract")
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
                        pct = min(20, 8 + int(done / float(4096 << 20) * 12))
                        report(pct, "DESKTOP IMAGE", "Writing image: %d MB / 4096 MB" % (done >> 20), "Extracting the compressed ext4 image.", animation="extract")
                        log("   %d MB / 4096 MB" % (done >> 20))
                        nxt += 128 << 20
        except Exception as e:
            return fail("Could not create the desktop image: %s" % e, 8, "DESKTOP IMAGE")
        open(MARKER + ".img", "w").close()

    report(22, "MOUNT", "Mounting the desktop image", "Preparing the isolated Ubuntu filesystem. The muOS host root is not modified.", animation="loading")
    log("Mounting the desktop image...")
    if not umount_all():
        return fail("An XFCE image mount is still active; refusing to remount it.", 22, "MOUNT")
    os.makedirs(MNT, exist_ok=True)
    sh("modprobe loop 2>/dev/null || true")
    ok, err = imgmount.mount_img(IMG, MNT)
    if not ok:
        return fail("Could not mount the desktop image: %s" % (err or "unknown error"), 22, "MOUNT")
    log("   montata: %.1fGB liberi dentro l'immagine" % free_gb(MNT))

    result = 1
    try:
        # ---- 2. ubuntu-base ---------------------------------------------
        if os.path.exists(MNT + "/etc/os-release"):
            log("2/5 Ubuntu Base already extracted; skipping.")
            report(42, "UBUNTU BASE", "Existing Ubuntu Base found", "The current root filesystem will be reused.", animation="verify")
        else:
            report(26, "DOWNLOAD", "Downloading Ubuntu Base 24.04 ARM64", "The base system archive is approximately 30 MB.", animation="download")
            log("2/5 Downloading Ubuntu Base 24.04 ARM64 (about 30 MB)...")
            if not (os.path.exists(TGZ) and
                    sh(["gzip", "-t", TGZ]) == 0):
                if sh(["curl", "-fL", "--retry", "2", "-o", TGZ, UB_URL]) != 0:
                    return fail("Ubuntu Base download failed.", 26, "DOWNLOAD")
            report(36, "EXTRACTION", "Extracting Ubuntu Base", "Expanding the base filesystem into the isolated ext4 image.", animation="extract")
            log("   extracting into the ext4 filesystem...")
            if sh("gzip -dc '%s' | tar -xf - -C '%s'" % (TGZ, MNT)) != 0:
                return fail("Ubuntu Base extraction failed.", 36, "EXTRACTION")
            os.remove(TGZ)

        # ---- 3. configurazione --------------------------------------------
        report(48, "CONFIGURATION", "Configuring the isolated desktop", "Setting hostname, package sources, Xorg and controller layout.", animation="loading")
        log("3/5 Configuring the isolated desktop...")
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
        log("4/5 Installing Xorg and XFCE (typically 10-20 minutes)...")
        log("   Keep the device powered on.")
        if not bind_all():
            return fail("Could not prepare the required bind mounts.", 55, "MOUNT")
        env = "DEBIAN_FRONTEND=noninteractive " \
              "PATH=/usr/sbin:/usr/bin:/sbin:/bin"
        aptop = ("-o Acquire::ForceIPv4=true "
                 "-o Acquire::https::Verify-Peer=false "
                 "-o Acquire::https::Verify-Host=false "
                 "-o Acquire::Retries=2")
        report(60, "PACKAGE INDEX", "Refreshing Ubuntu package indexes", "Connecting to the configured Ubuntu repositories.", animation="download")
        if sh("chroot '%s' /bin/bash -c '%s apt-get %s update'"
              % (MNT, env, aptop)) != 0:
            return fail("Ubuntu package index update failed.", 60, "PACKAGE INDEX")
        report(68, "INSTALLATION", "Installing Xorg and XFCE packages", "This phase can take 10-20 minutes. Void Desk remains available while it runs.", animation="install")
        if sh("chroot '%s' /bin/bash -c \"%s apt-get %s install -y "
              "--no-install-recommends %s && apt-get clean\""
              % (MNT, env, aptop, PKGS)) != 0:
            return fail("Xorg / XFCE package installation failed.", 68, "INSTALLATION")

        # ---- 5. verifica ----------------------------------------------
        report(94, "VERIFICATION", "Checking the installed desktop", "Validating Xorg, XFCE and controller launch binaries.", animation="verify")
        log("5/5 Verifying the installed desktop...")
        for p in ("/usr/bin/startx", "/usr/bin/startxfce4",
                  "/usr/bin/qjoypad"):
            if not os.path.exists(MNT + p):
                return fail("Required desktop component is missing: %s" % p, 94, "VERIFICATION")
        with open(MARKER, "w") as f:
            f.write("xfce ok\n")
        log("==== XFCE DESKTOP INSTALLED ====")
        log("Launch it from Void Desk / Start Session.")
        result = 0
    finally:
        if not umount_all():
            fail("XFCE cleanup is incomplete; one or more mounts or loop devices remain active.", 97, "CLEANUP")
            result = 1

    if result == 0:
        report(100, "COMPLETED", "XFCE is installed and ready",
               "The desktop image passed its post-install checks.",
               status="done", animation="verify", severity="success")
        log("==== XFCE BOOTSTRAP COMPLETED ====")
    return result


if __name__ == "__main__":
    sys.exit(main())
