#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK bootstrap-lite v1.5
# Downloads a compatible Pygame wheel, verifies its PyPI SHA-256 digest,
# validates ZIP members, tests the staged import, then swaps the runtime.
# No chroot is used; the runtime is stored below <app>/runtime (exFAT-safe).

import glob
import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
from desk.utils.safe_extract import safe_zip_extractall  # noqa: E402

sys.path.insert(0, os.path.join(APP, "lib"))
try:
    import fbtext
    SCREEN = fbtext.Screen(title="VOIDDESK - Pygame runtime setup")
except Exception:
    SCREEN = None

DATA = os.path.join(APP, "data")
RUNTIME = os.path.join(APP, "runtime")
STAGING = RUNTIME + ".staging"
BACKUP = RUNTIME + ".previous"
WHL = os.path.join(DATA, "pygame.whl")
MARKER = os.path.join(DATA, ".pygame_ready")
SDL_TXT = os.path.join(DATA, "sdl_path.txt")

os.makedirs(DATA, exist_ok=True)


def log(message):
    print(message, flush=True)
    if SCREEN:
        try:
            SCREEN.log(message)
        except Exception:
            pass


def opener():
    """Use the operating system trust store; never disable HTTPS verification."""
    context = ssl.create_default_context()
    result = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context)
    )
    result.addheaders = [("User-Agent", "VoidDesk/1.5")]
    return result


def pick_wheel(op, package, python_tag, machine):
    metadata_url = "https://pypi.org/pypi/%s/json" % package
    with op.open(metadata_url, timeout=30) as response:
        metadata = json.load(response)

    for item in metadata.get("urls", []):
        filename = item.get("filename", "")
        digest = str(item.get("digests", {}).get("sha256", "")).lower()
        package_url = item.get("url", "")
        host = urllib.parse.urlparse(package_url)
        if (
            filename.endswith(".whl")
            and python_tag in filename
            and machine in filename
            and "manylinux" in filename
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            and host.scheme == "https"
            and host.hostname == "files.pythonhosted.org"
        ):
            return package_url, filename, metadata["info"]["version"], digest

    return None, None, None, None


def download(op, url, destination, expected_sha256):
    """Download to a partial file and publish it only after hash verification."""
    partial = destination + ".part"
    digest = hashlib.sha256()
    next_report = 0

    try:
        with op.open(url, timeout=60) as response, open(partial, "wb") as output:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(262144)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if total:
                    percent = done * 100 // total
                    if percent >= next_report:
                        next_report = percent + 20
                        log("   %d%% (%0.1f/%0.1f MB)" %
                            (percent, done / 1e6, total / 1e6))

            output.flush()
            try:
                os.fsync(output.fileno())
            except OSError:
                pass

        actual = digest.hexdigest().lower()
        if actual != expected_sha256.lower():
            raise ValueError(
                "SHA-256 mismatch (expected %s, received %s)" %
                (expected_sha256, actual)
            )
        os.replace(partial, destination)
    except Exception:
        try:
            os.remove(partial)
        except OSError:
            pass
        raise


def find_system_sdl():
    patterns = [
        "/usr/lib/libSDL2-2.0.so*", "/usr/lib/libSDL2*.so*",
        "/usr/lib64/libSDL2*.so*", "/lib/libSDL2*.so*",
        "/usr/lib/aarch64-linux-gnu/libSDL2*.so*",
    ]
    hits = []
    for pattern in patterns:
        hits.extend(glob.glob(pattern))
    for base, _dirs, filenames in os.walk("/opt/muos"):
        for filename in filenames:
            if filename.startswith("libSDL2-2.0.so"):
                hits.append(os.path.join(base, filename))
    hits.sort(key=lambda path: (0 if ".so.0" in path else 1, len(path)))
    return hits


def replace_runtime(staging):
    """Install a validated runtime while preserving the previous directory."""
    shutil.rmtree(BACKUP, ignore_errors=True)
    had_runtime = os.path.exists(RUNTIME)
    if had_runtime:
        os.replace(RUNTIME, BACKUP)

    try:
        os.replace(staging, RUNTIME)
    except Exception:
        if had_runtime and os.path.exists(BACKUP):
            os.replace(BACKUP, RUNTIME)
        raise
    else:
        shutil.rmtree(BACKUP, ignore_errors=True)


def main():
    log("==== VOIDDESK PYGAME BOOTSTRAP start ====")
    python_tag = "cp%d%d" % sys.version_info[:2]
    machine = platform.machine()
    log("python: %s (%s) - architecture: %s" %
        (platform.python_version(), python_tag, machine))

    # Clear abandoned staging data, never the active runtime.
    shutil.rmtree(STAGING, ignore_errors=True)
    for obsolete in (os.path.join(DATA, "rootfs"),
                     os.path.join(DATA, "rootfs.tar.gz")):
        if os.path.isdir(obsolete):
            log("removing obsolete bootstrap data: %s" % obsolete)
            shutil.rmtree(obsolete, ignore_errors=True)
        elif os.path.isfile(obsolete):
            os.remove(obsolete)

    try:
        op = opener()
        log("1/4 searching PyPI for a compatible Pygame wheel...")
        url = filename = version = expected_sha256 = None
        for package in ("pygame", "pygame-ce"):
            url, filename, version, expected_sha256 = pick_wheel(
                op, package, python_tag, machine
            )
            if url:
                break
    except Exception as exc:
        log("FATAL: secure package discovery failed: %s" % exc)
        log("Check the device clock, network connection and CA certificates.")
        return 1

    if not url:
        log("FATAL: no verified manylinux wheel found for %s/%s" %
            (python_tag, machine))
        return 1

    log("   found %s (v%s)" % (filename, version))
    log("2/4 downloading and verifying SHA-256...")
    try:
        download(op, url, WHL, expected_sha256)
    except Exception as exc:
        log("FATAL: verified download failed: %s" % exc)
        return 1

    log("3/4 validating and extracting into a staging directory...")
    os.makedirs(STAGING, exist_ok=True)
    try:
        with zipfile.ZipFile(WHL) as archive:
            safe_zip_extractall(archive, STAGING)

        for base, _dirs, filenames in os.walk(STAGING):
            for filename in filenames:
                if filename.endswith(".so") or ".so." in filename:
                    try:
                        os.chmod(os.path.join(base, filename), 0o755)
                    except OSError:
                        pass

        log("4/4 verifying staged Pygame import...")
        env = dict(os.environ)
        env["PYTHONPATH"] = STAGING
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        env.pop("SDL_VIDEODRIVER", None)
        result = subprocess.run(
            [sys.executable, "-c",
             "import pygame,sys;sys.stdout.write(pygame.version.ver)"],
            env=env, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()[-800:] or
                "Pygame import returned a non-zero status"
            )

        log("   Pygame %s import OK" % result.stdout.strip())
        replace_runtime(STAGING)
    except Exception as exc:
        shutil.rmtree(STAGING, ignore_errors=True)
        log("FATAL: runtime validation failed; previous runtime was preserved: %s" %
            exc)
        return 1

    sdl = find_system_sdl()
    if sdl:
        log("system SDL2 library: %s" % sdl[0])
        with open(SDL_TXT + ".tmp", "w", encoding="utf-8") as output:
            output.write(sdl[0] + "\n")
        os.replace(SDL_TXT + ".tmp", SDL_TXT)
    else:
        log("system SDL2 library not found; using the wheel-provided library")
        try:
            os.remove(SDL_TXT)
        except OSError:
            pass

    with open(MARKER + ".tmp", "w", encoding="utf-8") as output:
        output.write("pygame %s (%s %s)\n" %
                     (result.stdout.strip(), python_tag, machine))
    os.replace(MARKER + ".tmp", MARKER)

    try:
        os.remove(WHL)
    except OSError:
        pass

    log("==== VOIDDESK PYGAME BOOTSTRAP completed ====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
