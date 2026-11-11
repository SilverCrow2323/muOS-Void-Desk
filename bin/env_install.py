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

sys.path.insert(0, os.path.join(APP, "lib"))
try:
    import fbtext
except Exception:
    fbtext = None

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


def log(msg, screen):
    print(msg, flush=True)
    if screen:
        try:
            screen.log(msg)
        except Exception:
            pass


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

    screen = None
    if fbtext:
        try:
            screen = fbtext.Screen(
                title="VOIDDESK - installing %s" % spec["title"])
        except Exception:
            screen = None

    if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
        log("FATAL: base desktop (XFCE) not installed yet — "
            "install that first, this adds onto it", screen)
        return 1
    if not os.path.exists(IMG):
        log("FATAL: desktop image missing: %s" % IMG, screen)
        return 1
    already = os.path.join(DATA, spec["marker"])
    if os.path.exists(already):
        log("%s already installed" % spec["title"], screen)
        return 0

    log("==== VOIDDESK %s install ====" % spec["title"], screen)
    if imgmount.is_mounted(MNT):
        log("FATAL: XFCE desktop is already mounted; close the session first",
            screen)
        return 1
    log("mounting desktop image...", screen)
    os.makedirs(MNT, exist_ok=True)
    ok, err = imgmount.mount_img(IMG, MNT)
    if not ok and not imgmount.is_mounted(MNT):
        log("FATAL: mount loop failed - %s" % (err or "?"), screen)
        return 1

    try:
        bind_all()

        env = ("DEBIAN_FRONTEND=noninteractive "
               "PATH=/usr/sbin:/usr/bin:/sbin:/bin")
        aptop = ("-o Acquire::ForceIPv4=true "
                 "-o Acquire::https::Verify-Peer=false "
                 "-o Acquire::https::Verify-Host=false "
                 "-o Acquire::Retries=2")

        log("apt-get update...", screen)
        if sh("chroot '%s' /bin/bash -c '%s apt-get %s update'"
              % (MNT, env, aptop)) != 0:
            log("FATAL: apt-get update failed", screen)
            return 1

        log("installing %s (%s)..." % (spec["title"], spec["pkgs"]), screen)
        if sh("chroot '%s' /bin/bash -c \"%s apt-get %s install -y "
              "--no-install-recommends %s && apt-get clean\""
              % (MNT, env, aptop, spec["pkgs"])) != 0:
            log("FATAL: package install failed", screen)
            return 1

        if not os.path.exists(MNT + spec["verify"]):
            log("FATAL: %s missing after install" % spec["verify"], screen)
            return 1

        with open(already, "w") as f:
            f.write("%s ok\n" % env_id)
        log("==== %s INSTALLED ====" % spec["title"], screen)
        log("Launch it from VOIDDESK -> START SESSION -> %s" % spec["title"],
            screen)
        return 0
    finally:
        log("unmounting...", screen)
        cleanup_ok = imgmount.umount_tree(MNT, IMG)
        if not cleanup_ok:
            log("FATAL: XFCE cleanup incomplete; mounts or loop still active",
                screen)
            return 1


if __name__ == "__main__":
    sys.exit(main())
