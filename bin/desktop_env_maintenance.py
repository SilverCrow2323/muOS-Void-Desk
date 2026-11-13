#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supervised, allowlisted maintenance for the isolated desktop environments."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DATA = APP / "data"
IMG = DATA / "xfce.img"
MNT = DATA / "xfce_mnt"
STATUS = None

sys.path.insert(0, str(APP / "desk"))
import imgmount  # noqa: E402

ENVIRONMENTS = {
    "xfce": {
        "marker": ".xfce_ready",
        "packages": None,
        "launch": "/usr/bin/startxfce4",
    },
    "icewm": {
        "marker": ".icewm_ready",
        "packages": ("icewm", "icewm-themes"),
        "launch": "/usr/bin/icewm-session",
    },
    "lxde": {
        "marker": ".lxde_ready",
        "packages": ("lxde-core",),
        "launch": "/usr/bin/startlxde",
    },
}


def log(message):
    print(str(message), flush=True)


def report(env_id, action, progress, phase, message, detail="",
           status="running", animation="loading", severity="info"):
    global STATUS
    if STATUS is None:
        STATUS = DATA / (".%s_%s_state.json" % (env_id, action))
    payload = {
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
    temporary = STATUS.with_suffix(STATUS.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATUS)
    except OSError as exc:
        log("WARNING: cannot publish operation state: %s" % exc)


def fail(env_id, action, message, progress=0, phase="FAILED"):
    log("ERROR: " + message)
    report(env_id, action, progress, phase, message,
           status="failed", animation="verify", severity="error")
    return 1


def run(command, env_id, action, progress, phase, message, animation="install"):
    report(env_id, action, progress, phase, message,
           detail="Running a fixed, allowlisted operation inside the isolated Ubuntu image.",
           animation=animation)
    log(message)
    result = subprocess.run(command, cwd=str(APP), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            check=False)
    output = (result.stdout or "")[-10000:]
    if output:
        log(output)
    return result.returncode, output


def bind_mounts():
    for src, dst in (("/dev", MNT / "dev"),
                     ("/proc", MNT / "proc"),
                     ("/sys", MNT / "sys")):
        dst.mkdir(parents=True, exist_ok=True)
        if not imgmount.is_mounted(str(dst)):
            if src == "/proc":
                rc = subprocess.call(["mount", "-t", "proc", "proc", str(dst)])
            elif src == "/sys":
                rc = subprocess.call(["mount", "-t", "sysfs", "sys", str(dst)])
            else:
                rc = subprocess.call(["mount", "-o", "bind", src, str(dst)])
            if rc != 0:
                return False
    pts = MNT / "dev" / "pts"
    if Path("/dev/pts").exists() and not imgmount.is_mounted(str(pts)):
        pts.mkdir(parents=True, exist_ok=True)
        if subprocess.call(["mount", "-o", "bind", "/dev/pts", str(pts)]) != 0:
            return False
    return True


def main():
    if len(sys.argv) != 3:
        log("usage: desktop_env_maintenance.py <uninstall|updates> <xfce|icewm|lxde>")
        return 2
    action, env_id = sys.argv[1], sys.argv[2]
    if action not in ("uninstall", "updates") or env_id not in ENVIRONMENTS:
        log("unsupported maintenance request")
        return 2

    spec = ENVIRONMENTS[env_id]
    marker = DATA / spec["marker"]
    if not marker.is_file():
        if action == "uninstall":
            report(env_id, action, 100, "COMPLETED",
                   env_id.upper() + " is already removed",
                   status="done", animation="verify", severity="success")
            return 0
        return fail(env_id, action, env_id.upper() + " is not installed.", 2, "PRE-FLIGHT")

    report(env_id, action, 2, "PRE-FLIGHT", "Checking the desktop image",
           "The operation uses only the isolated XFCE image; muOS host packages are not changed.")
    if env_id == "xfce" and action == "uninstall":
        if imgmount.is_mounted(str(MNT)):
            return fail(env_id, action,
                        "The XFCE image is mounted. Log out of the desktop session and retry.",
                        5, "PRE-FLIGHT")
        if IMG.is_symlink():
            return fail(env_id, action, "Refusing to remove a linked desktop image.", 5, "SAFETY CHECK")
        if IMG.exists() and not IMG.is_file():
            return fail(env_id, action, "The desktop image path is not a regular file.", 5, "SAFETY CHECK")
        report(env_id, action, 55, "REMOVAL", "Removing the isolated XFCE image",
               "This also removes IceWM and LXDE because they share the same image.",
               animation="extract")
        try:
            if IMG.exists():
                IMG.unlink()
            for name in (".xfce_ready", ".xfce_ready.img", ".icewm_ready", ".lxde_ready"):
                (DATA / name).unlink(missing_ok=True)
        except OSError as exc:
            return fail(env_id, action, "Could not remove the desktop image: %s" % exc,
                        55, "REMOVAL")
        report(env_id, action, 100, "COMPLETED", "XFCE image removed",
               "The personal muOS files and other Void Desk settings were left untouched.",
               status="done", animation="verify", severity="success")
        log("XFCE image removed.")
        return 0

    if not IMG.is_file() or IMG.is_symlink():
        return fail(env_id, action, "The isolated XFCE image is missing or unsafe.", 4, "PRE-FLIGHT")
    if imgmount.is_mounted(str(MNT)):
        return fail(env_id, action,
                    "The XFCE image is already mounted. Close the desktop session and retry.",
                    5, "PRE-FLIGHT")

    MNT.mkdir(parents=True, exist_ok=True)
    report(env_id, action, 8, "MOUNT", "Mounting the isolated desktop image",
           animation="loading")
    ok, err = imgmount.mount_img(str(IMG), str(MNT))
    if not ok and not imgmount.is_mounted(str(MNT)):
        return fail(env_id, action, "Could not mount the desktop image: %s" % (err or "unknown error"),
                    8, "MOUNT")

    result = 1
    try:
        if not bind_mounts():
            return fail(env_id, action, "Could not prepare the isolated image mounts.", 12, "MOUNT")
        apt_env = dict(os.environ)
        apt_env["DEBIAN_FRONTEND"] = "noninteractive"
        apt_env["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"

        if action == "uninstall":
            packages = spec["packages"]
            if not packages:
                return fail(env_id, action, "XFCE removal must use the image removal flow.", 15, "SAFETY CHECK")
            package_text = " ".join(packages)
            command = ["chroot", str(MNT), "/bin/bash", "-lc",
                       "DEBIAN_FRONTEND=noninteractive apt-get purge -y --no-install-recommends "
                       + package_text + " && apt-get clean"]
            rc, output = run(command, env_id, action, 55, "UNINSTALL",
                             "Removing " + env_id.upper() + " packages")
            if rc != 0:
                return fail(env_id, action, env_id.upper() + " package removal failed.",
                            55, "UNINSTALL")
            if Path(str(MNT) + spec["launch"]).exists():
                return fail(env_id, action, "The desktop launcher still exists after removal.",
                            90, "VERIFICATION")
            marker.unlink(missing_ok=True)
            result = 0
        else:
            rc, output = run(
                ["chroot", str(MNT), "/bin/bash", "-lc",
                 "DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::ForceIPv4=true "
                 "-o Acquire::Retries=2 update"],
                env_id, action, 38, "PACKAGE INDEX", "Refreshing desktop package indexes",
                animation="download")
            if rc != 0:
                return fail(env_id, action, "Package index refresh failed.", 38, "PACKAGE INDEX")
            rc, output = run(
                ["chroot", str(MNT), "/bin/bash", "-lc",
                 "DEBIAN_FRONTEND=noninteractive apt-get -s upgrade"],
                env_id, action, 72, "UPDATE CHECK", "Checking for available desktop updates",
                animation="verify")
            if rc != 0:
                return fail(env_id, action, "The simulated upgrade check failed.", 72, "UPDATE CHECK")
            summary = ""
            for line in output.splitlines():
                if "upgraded," in line and " newly installed" in line:
                    summary = line.strip()
            if not summary:
                summary = "The package manager completed the simulation."
            report(env_id, action, 100, "COMPLETED", "Update check completed",
                   summary + " No packages were installed or upgraded.",
                   status="done", animation="verify", severity="success")
            log("No packages were installed or upgraded.")
            result = 0
    finally:
        if not imgmount.umount_tree(str(MNT), str(IMG)):
            fail(env_id, action, "Desktop image cleanup is incomplete; mounts or loop devices remain active.",
                 96, "CLEANUP")
            result = 1

    if result == 0 and action == "uninstall":
        report(env_id, action, 100, "COMPLETED", env_id.upper() + " removed",
               "The rest of the XFCE desktop image remains installed.",
               status="done", animation="verify", severity="success")
    return result


if __name__ == "__main__":
    sys.exit(main())
