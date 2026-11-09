#!/usr/bin/env python3
"""Safe APT access to VoidDesk's optional Ubuntu XFCE ext4 image."""
import fcntl
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DATA = APP / "data"
IMAGE = DATA / "xfce.img"
MOUNT = DATA / "xfce_mnt"
LOCK = DATA / ".apt-manager.lock"
PACKAGE = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,127}$")
SEARCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 +_.-]{0,79}$")
sys.path.insert(0, str(APP / "desk"))
import imgmount  # noqa: E402


def fail(message, code=2):
    print(message, file=sys.stderr)
    return code


def main(argv):
    if not argv:
        return fail("missing APT action")
    action, *args = argv
    catalog = action == "catalog"
    if catalog:
        if not args or args[0] not in ("search", "installed", "info"):
            return fail("invalid catalog mode")
        mode, *args = args
        if mode == "search":
            if len(args) != 1 or not SEARCH.fullmatch(args[0]):
                return fail("invalid package search query")
        elif mode == "installed":
            if args:
                return fail("installed mode takes no arguments")
        elif mode == "info":
            if not 1 <= len(args) <= 20 or any(not PACKAGE.fullmatch(x) for x in args):
                return fail("invalid package list")
    else:
        if action not in ("update", "upgrade", "clean", "install", "remove"):
            return fail("unsupported APT action")
        if action in ("install", "remove"):
            if not 1 <= len(args) <= 20 or any(not PACKAGE.fullmatch(x) for x in args):
                return fail("invalid package list")
        elif args:
            return fail("this APT action takes no arguments")

    if not (DATA / ".xfce_ready").is_file() or not IMAGE.is_file():
        return fail("XFCE image is not installed")
    DATA.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return fail("another APT operation is already running", 75)

        if imgmount.is_mounted(str(MOUNT)):
            return fail("XFCE image is already mounted; close the desktop before package management", 75)
        ok, error = imgmount.mount_img(str(IMAGE), str(MOUNT))
        if not ok:
            return fail("cannot mount XFCE image: " + (error or "unknown error"), 1)

        bind_targets = []
        try:
            for source, target, kind in (
                ("/dev", MOUNT / "dev", "bind"),
                ("proc", MOUNT / "proc", "proc"),
                ("sys", MOUNT / "sys", "sysfs"),
            ):
                target.mkdir(parents=True, exist_ok=True)
                if not imgmount.is_mounted(str(target)):
                    if kind == "bind":
                        command = ["mount", "--bind", source, str(target)]
                    else:
                        command = ["mount", "-t", kind, source, str(target)]
                    result = subprocess.run(command, capture_output=True, text=True)
                    if result.returncode:
                        return fail("cannot prepare chroot mounts: " +
                                    (result.stderr or result.stdout)[-500:], 1)
                    bind_targets.append(str(target))
            resolv = Path("/etc/resolv.conf")
            if resolv.is_file():
                shutil.copyfile(str(resolv), str(MOUNT / "etc/resolv.conf"))

            if catalog and mode == "search":
                command = ["apt-cache", "search", "--names-only", args[0]]
            elif catalog and mode == "installed":
                command = ["dpkg-query", "-W", "-f=${binary:Package}\\t${Version}\\n"]
            elif catalog:
                command = ["apt-cache", "show"] + args
            elif action == "update":
                command = ["apt-get", "update"]
            elif action == "upgrade":
                command = ["apt-get", "upgrade", "-y"]
            elif action == "clean":
                command = ["apt-get", "clean"]
            elif action == "install":
                command = ["apt-get", "install", "-y", "--no-install-recommends"] + args
            else:
                command = ["apt-get", "remove", "-y"] + args

            env = dict(os.environ)
            env["DEBIAN_FRONTEND"] = "noninteractive"
            env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            result = subprocess.run(
                ["chroot", str(MOUNT), "/usr/bin/env",
                 "DEBIAN_FRONTEND=noninteractive",
                 "PATH=" + env["PATH"]] + command,
                cwd=str(APP), env=env, text=True, check=False,
            )
            return result.returncode
        finally:
            for target in reversed(bind_targets):
                subprocess.run(["umount", target], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
            imgmount.umount_tree(str(MOUNT), str(IMAGE))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
