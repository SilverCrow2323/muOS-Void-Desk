#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // env_install — installs an ADDITIONAL desktop environment
# (icewm | lxde) into the existing XFCE chroot image.
#
# bin/xfce_launch.sh already knows how to start any of the three
# ("desk_env" config key, picked in START SESSION) and already falls
# back to xfce if the chosen one isn't installed — see its DESKENV
# case block. What was actually missing was a way to get the icewm/
# lxde *packages* into the rootfs that xfce_bootstrap.py already built,
# so this is deliberately NOT a second xfce_bootstrap: no ubuntu-base
# download, no new ext4 image — just `apt-get install` into the image
# that's already there, which is why it's much faster (a minute or two,
# not 10-20).
import os
import subprocess
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
IMG = os.path.join(DATA, "xfce.img")
MNT = os.path.join(DATA, "xfce_mnt")

sys.path.insert(0, os.path.join(APP, "desk"))
import imgmount  # noqa: E402

import json
import time

STATUS_FILE = None

ENVS = {
    "icewm": {
        "pkgs": "icewm icewm-themes",
        "verify": "/usr/bin/icewm-session",
        "marker": ".icewm_ready",
        "title": "IceWM",
    },
    "lxde": {
        # lxde-core: panel + session + openbox + pcmanfm, without the
        # full lxde metapackage's extra apps (games, lxde-common clutter)
        "pkgs": "lxde-core",
        "verify": "/usr/bin/startlxde",
        "marker": ".lxde_ready",
        "title": "LXDE",
    },
}


def log(msg):
    print(msg, flush=True)


def report(data_dir, progress, phase, message, detail="", status="running",
           animation="install", severity="info"):
    global STATUS_FILE
    if STATUS_FILE is None:
        STATUS_FILE = os.path.join(data_dir, ".%s_install_state.json" % env_id)
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
        log("WARNING: could not publish operation status: %s" % exc)


def fail(data_dir, message, progress=0, phase="FAILED"):
    log("ERROR: " + message)
    report(data_dir, progress, phase, message, status="failed",
           animation="verify", severity="error")
    return 1


def sh(cmd):
    return subprocess.call(cmd, shell=isinstance(cmd, str))


def bind_all():
    for src, dst in (("/dev", MNT + "/dev"), ("/proc", MNT + "/proc"),
                     ("/sys", MNT + "/sys")):
        os.makedirs(dst, exist_ok=True)
        if not imgmount.is_mounted(dst):
            if src == "/proc":
                sh(["mount", "-t", "proc", "proc", dst])
            elif src == "/sys":
                sh(["mount", "-t", "sysfs", "sys", dst])
            else:
                sh(["mount", "-o", "bind", src, dst])


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ENVS:
        print("usage: env_install.py <icewm|lxde>", file=sys.stderr)
        return 2
    env_id = sys.argv[1]
    spec = ENVS[env_id]
    report(DATA, 1, "PRE-FLIGHT", "Checking the existing XFCE image",
           "This operation adds a desktop environment to the existing isolated image.",
           animation="loading")
    if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
        return fail(DATA, "Install XFCE first; this desktop uses the existing XFCE image.", 2, "PRE-FLIGHT")
    if not os.path.exists(IMG):
        return fail(DATA, "The XFCE desktop image is missing.", 3, "PRE-FLIGHT")
    already = os.path.join(DATA, spec["marker"])
    if os.path.exists(already):
        report(DATA, 100, "COMPLETED", spec["title"] + " is already installed",
               status="done", animation="verify", severity="success")
        return 0

    log("==== VOID DESK %s INSTALL ====" % spec["title"].upper())
    report(DATA, 8, "MOUNT", "Mounting the existing desktop image",
           "The operation will not modify the muOS host root filesystem.",
           animation="loading")
    if imgmount.is_mounted(MNT):
        return fail(DATA, "The desktop image is already mounted; close the desktop session first.", 8, "MOUNT")
    os.makedirs(MNT, exist_ok=True)
    ok, err = imgmount.mount_img(IMG, MNT)
    if not ok and not imgmount.is_mounted(MNT):
        return fail(DATA, "Could not mount the desktop image: %s" % (err or "unknown error"), 8, "MOUNT")

    result = 1
    try:
        bind_all()
        env = "DEBIAN_FRONTEND=noninteractive PATH=/usr/sbin:/usr/bin:/sbin:/bin"
        aptop = ("-o Acquire::ForceIPv4=true "
                 "-o Acquire::https::Verify-Peer=false "
                 "-o Acquire::https::Verify-Host=false "
                 "-o Acquire::Retries=2")
        report(DATA, 22, "PACKAGE INDEX", "Refreshing Ubuntu package indexes",
               "Checking the repositories configured in the isolated image.",
               animation="download")
        log("Refreshing Ubuntu package indexes...")
        if sh("chroot '%s' /bin/bash -c '%s apt-get %s update'"
              % (MNT, env, aptop)) != 0:
            return fail(DATA, "Ubuntu package index update failed.", 22, "PACKAGE INDEX")

        report(DATA, 55, "INSTALLATION", "Installing " + spec["title"],
               "Installing only the selected window manager into the existing XFCE image.",
               animation="install")
        log("Installing %s packages..." % spec["title"])
        if sh("chroot '%s' /bin/bash -c \"%s apt-get %s install -y "
              "--no-install-recommends %s && apt-get clean\""
              % (MNT, env, aptop, spec["pkgs"])) != 0:
            return fail(DATA, spec["title"] + " package installation failed.", 55, "INSTALLATION")

        report(DATA, 90, "VERIFICATION", "Checking " + spec["title"],
               "Verifying the session launch executable before marking it installed.",
               animation="verify")
        if not os.path.exists(MNT + spec["verify"]):
            return fail(DATA, "Required executable is missing after installation: " + spec["verify"], 90, "VERIFICATION")

        with open(already, "w", encoding="utf-8") as handle:
            handle.write(env_id + " ok\n")
        log(spec["title"] + " is installed.")
        result = 0
    finally:
        report(DATA, 96, "CLEANUP", "Releasing temporary mounts",
               "Finishing the operation before returning to Void Desk.",
               animation="loading")
        cleanup_ok = imgmount.umount_tree(MNT, IMG)
        if not cleanup_ok:
            fail(DATA, "Desktop image cleanup is incomplete; one or more mounts or loop devices remain active.", 96, "CLEANUP")
            result = 1

    if result == 0:
        report(DATA, 100, "COMPLETED", spec["title"] + " is installed and ready",
               "The desktop passed its post-install check.",
               status="done", animation="verify", severity="success")
        log("==== %s INSTALL COMPLETED ====" % spec["title"].upper())
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
