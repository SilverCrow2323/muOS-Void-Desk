#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // xfce_update — apt update + upgrade nel chroot, con progresso.
import os
import subprocess
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
IMG = os.path.join(DATA, "xfce.img")
MNT = os.path.join(DATA, "xfce_mnt")
sys.path.insert(0, os.path.join(APP, "desk"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import imgmount  # noqa: E402

spec_path = os.path.join(APP, "bin", "xfce_install.py")
sys.path.insert(0, os.path.join(APP, "bin"))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("xi", spec_path)
xi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xi)


def main():
    lang = xi.cfg_get("lang", "it")
    scr = xi.Screen("apt upgrade", ["aggiornamento" if lang == "it"
                                    else "upgrade"], lang)
    log = open(os.path.join(DATA, "install.log"), "ab")
    log.write(("\n==== %s : upgrade ====\n" % time.ctime()).encode())
    try:
        if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
            scr.msg = "FATAL: desktop XFCE non installato"
            scr.draw()
            time.sleep(4)
            return 1
        if subprocess.call(["curl", "-sI", "--max-time", "8",
                            "https://ports.ubuntu.com"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) != 0:
            scr.msg = ("FATAL: rete assente" if lang == "it"
                       else "FATAL: no network")
            scr.draw()
            time.sleep(5)
            return 1
        imgmount.umount_tree(MNT, IMG)
        imgmount.cleanup_stale(IMG)
        ok, err = imgmount.mount_img(IMG, MNT)
        if not ok:
            scr.msg = "FATAL: mount - %s" % err
            scr.draw()
            time.sleep(6)
            return 1
        for typ, src, dst in (("bind", "/dev", "/dev"),
                              ("proc", "proc", "/proc"),
                              ("sysfs", "sys", "/sys")):
            d = MNT + dst
            os.makedirs(d, exist_ok=True)
            if not imgmount.is_mounted(d):
                if typ == "bind":
                    subprocess.call(["mount", "-o", "bind", src, d])
                else:
                    subprocess.call(["mount", "-t", typ, src, d])
        try:
            import shutil
            shutil.copy("/etc/resolv.conf", MNT + "/etc/resolv.conf")
        except OSError:
            pass
        scr.phase = "prep"
        scr.cur = "apt-get update"
        scr.tot_pct = 5
        scr.draw()
        subprocess.call(["chroot", MNT, "/bin/bash", "-c",
                         "DEBIAN_FRONTEND=noninteractive apt-get "
                         "-o Acquire::ForceIPv4=true "
                         "-o Acquire::https::Verify-Peer=false "
                         "-o Acquire::https::Verify-Host=false update"],
                        stdout=log, stderr=log)
        rc = xi.apt_with_progress([], scr, log, upgrade=True)
        if rc != 0:
            scr.msg = "FATAL: upgrade rc=%d" % rc
            scr.draw()
            time.sleep(5)
            return 1
        scr.phase = "done"
        scr.cur_pct = scr.tot_pct = 100
        scr.state[scr.pkgs[0]] = "done"
        scr.msg = ("Sistema aggiornato." if lang == "it"
                   else "System updated.")
        try:
            import json as _j
            _j.dump({"ts": time.time(), "upgradable": 0},
                    open(os.path.join(DATA, ".apt_state.json"), "w"))
        except OSError:
            pass
        scr.draw()
        time.sleep(3)
        return 0
    finally:
        imgmount.umount_tree(MNT, IMG)
        scr.close()
        log.close()


if __name__ == "__main__":
    sys.exit(main())
