#!/usr/bin/env bash
# Build both local Void Desk deliverables: muOS .muxapp and Debian PC .deb.
# Run from the project root, or invoke this file by its absolute path.
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
OUT_DIR="$ROOT/dist"
VERSION=""
UPDATE_SUBMODULES=1

usage() {
    cat <<'USAGE'
Usage: ./build-packages.sh [options]

Builds:
  dist/Void-Desk-VERSION.muxapp       muOS handheld package
  dist/voiddesk_VERSION_all.deb      Debian/Ubuntu PC installer
  SHA-256 sidecar files for both packages

Options:
  --version VERSION          Override the version read from voiddesk.py
  --output-dir DIRECTORY     Write packages to another directory (default: ./dist)
  --skip-submodule-update    Do not run git submodule update automatically
  -h, --help                 Show this help

Requirements: Linux, Bash, Git, Python 3.10+, dpkg-deb, tar and sha256sum.
The PC .deb installs the Pygame desktop frontend. First launch needs Internet
access to create a private Python virtual environment and install pygame/psutil.
USAGE
}

die() {
    printf '[voiddesk-build] ERROR: %s\n' "$*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        --version)
            (($# >= 2)) || die "--version requires a value"
            VERSION="$2"
            shift 2
            ;;
        --output-dir)
            (($# >= 2)) || die "--output-dir requires a path"
            OUT_DIR="$2"
            shift 2
            ;;
        --skip-submodule-update)
            UPDATE_SUBMODULES=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1 (use --help)"
            ;;
    esac
done

for command in git python3 dpkg-deb tar sha256sum; do
    command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10 or newer is required"

[[ -f "$ROOT/tools/build_muxapp.py" ]] || die "run this script from a complete VoidDesk checkout"
[[ -f "$ROOT/tools/build_pc.py" ]] || die "tools/build_pc.py is missing"
[[ -f "$ROOT/tools/validate_muxapp.py" ]] || die "tools/validate_muxapp.py is missing"

if [[ -z "$VERSION" ]]; then
    VERSION="$(sed -nE 's/.*VOIDDESK NEXUS v([0-9][A-Za-z0-9.+~_-]*).*/\1/p' "$ROOT/voiddesk.py" | head -n 1)"
fi
[[ -n "$VERSION" ]] || die "cannot detect the version from voiddesk.py; pass --version"
[[ "$VERSION" =~ ^[0-9][A-Za-z0-9.+~_-]{0,39}$ ]] \
    || die "invalid version '$VERSION' (use letters, digits, dot, plus, tilde, underscore or hyphen)"

if ((UPDATE_SUBMODULES)); then
    printf '[voiddesk-build] Initializing pinned submodules...\n'
    git -C "$ROOT" submodule update --init --recursive \
        || die "submodule initialization failed; check network access and .gitmodules"
fi

# build_pc.py snapshots HEAD with git archive. Refuse a dirty checkout so the
# .muxapp and .deb cannot silently contain different source revisions.
WORKTREE_STATUS="$(git -C "$ROOT" status --porcelain --untracked-files=normal | awk '$0 != "?? build-packages.sh"')"
if [[ -n "$WORKTREE_STATUS" ]]; then
    git -C "$ROOT" status --short >&2
    die "working tree is not clean; commit or stash changes before packaging"
fi

BUILD_TMP="$(mktemp -d "${TMPDIR:-/tmp}/voiddesk-packages.XXXXXX")"
cleanup() {
    rm -rf -- "$BUILD_TMP"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$OUT_DIR"
OUT_DIR="$(cd -- "$OUT_DIR" && pwd -P)"
MUXAPP="$OUT_DIR/Void-Desk-${VERSION}.muxapp"
DEB="$OUT_DIR/voiddesk_${VERSION}_all.deb"
PC_TARBALL="$BUILD_TMP/Void-Desk-PC-Linux-${VERSION}.tar.gz"

printf '\n[1/2] Building and validating muOS package...\n'
python3 "$ROOT/tools/build_muxapp.py" --output "$MUXAPP"
python3 "$ROOT/tools/validate_muxapp.py" "$MUXAPP"
(
    cd "$OUT_DIR"
    sha256sum -c "$(basename "$MUXAPP").sha256"
)

printf '\n[2/2] Building Debian PC package...\n'
python3 "$ROOT/tools/build_pc.py" \
    --version "$VERSION" \
    --output "$PC_TARBALL"

PC_EXTRACT="$BUILD_TMP/pc"
mkdir -p "$PC_EXTRACT"
# This archive comes from the repository's own sanitizer. Still verify that
# every member stays inside its one expected top-level directory before extract.
if ! tar -tzf "$PC_TARBALL" | awk '
    /^VoidDesk-PC\/$/ { next }
    /^VoidDesk-PC\// { next }
    { print "[voiddesk-build] unsafe PC archive member: " $0 > "/dev/stderr"; bad=1 }
    END { exit bad }
'; then
    die "PC source archive contains an unexpected path"
fi
tar -xzf "$PC_TARBALL" -C "$PC_EXTRACT" --no-same-owner
PC_SOURCE="$PC_EXTRACT/VoidDesk-PC"
[[ -f "$PC_SOURCE/voiddesk.py" ]] || die "PC source bundle is incomplete"
[[ -f "$PC_SOURCE/resources/voiddesk.png" ]] || die "PC source bundle has no VoidDesk icon"

DEB_ROOT="$BUILD_TMP/deb-root"
APP_DEST="$DEB_ROOT/usr/lib/voiddesk/app"
install -d "$APP_DEST" \
    "$DEB_ROOT/DEBIAN" \
    "$DEB_ROOT/usr/bin" \
    "$DEB_ROOT/usr/share/applications" \
    "$DEB_ROOT/usr/share/pixmaps" \
    "$DEB_ROOT/usr/share/doc/voiddesk"

cp -R --preserve=mode,timestamps "$PC_SOURCE/." "$APP_DEST/"

# The PC package is architecture-independent source. Do not ship the handheld's
# ARM LÖVE/LuaJIT binaries or the large muOS XFCE image in an all-architecture .deb.
rm -rf -- \
    "$APP_DEST/data" \
    "$APP_DEST/assets/runtime_archives"
rm -f -- \
    "$APP_DEST/lib/love" \
    "$APP_DEST/lib/libluajit-5.1.so.2" \
    "$APP_DEST/assets/xfce.img.gz" \
    "$APP_DEST/launch-pc.sh" \
    "$APP_DEST/build-packages.sh"

install -m 0644 "$PC_SOURCE/resources/voiddesk.png" \
    "$DEB_ROOT/usr/share/pixmaps/voiddesk.png"

cat > "$DEB_ROOT/usr/share/applications/voiddesk.desktop" <<'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Void Desk
GenericName=Linux Desktop Hub
Comment=Controller-friendly Linux desktop and utility hub
Exec=voiddesk
Icon=voiddesk
Terminal=false
StartupNotify=true
Categories=Utility;Game;
DESKTOP

cat > "$DEB_ROOT/usr/share/doc/voiddesk/README.Debian" <<'DEBIAN_README'
Void Desk — Debian / Ubuntu installation
========================================

Launch Void Desk from the desktop application menu or run voiddesk.
The Debian package starts the Pygame PC frontend; handheld-only muOS features
(framebuffer, package management and the XFCE image lifecycle) are unavailable.

On first launch, Void Desk creates a private Python virtual environment and
installs pygame and psutil. An Internet connection is required for this setup.
User configuration, logs and the virtual environment are stored in
~/.local/share/voiddesk/app (or $XDG_DATA_HOME/voiddesk/app).

These per-user files survive package upgrades and apt remove voiddesk. To remove
all personal state as well, delete the voiddesk folder from your own account
after uninstalling.

The optional LÖVE frontend requires a system LÖVE installation (love). The
Debian package does not ship the handheld's ARM LÖVE/LuaJIT binaries.
DEBIAN_README

cat > "$DEB_ROOT/usr/share/doc/voiddesk/copyright" <<'COPYRIGHT'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Void Desk
Source: https://github.com/SilverCrow2323/Void-Desk-Project

Files: *
Copyright: 2026 SPDW Factory
License: unknown
 The upstream repository does not currently declare an overall project
 licence. This package does not imply a new licence grant. Consult the upstream
 repository and its THIRD-PARTY.md for current notices before redistribution.
COPYRIGHT

cat > "$DEB_ROOT/DEBIAN/control" <<CONTROL
Package: voiddesk
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: Sir Pips / SPDW Factory
Depends: python3 (>= 3.10), python3-venv, ca-certificates
Recommends: libgl1, libglib2.0-0 | libglib2.0-0t64, libasound2 | libasound2t64
Suggests: love, mpv
Homepage: https://github.com/SilverCrow2323/Void-Desk-Project
Description: Linux desktop hub and utility frontend
 Void Desk is a controller-friendly desktop and utility hub. This package
 installs its Pygame-based Linux PC frontend; muOS-only features remain
 available only on compatible handheld firmware.
CONTROL

cat > "$DEB_ROOT/usr/bin/voiddesk" <<'VOIDDESK_LAUNCHER'
#!/bin/sh
set -eu
umask 077

PACKAGE_VERSION="@PACKAGE_VERSION@"
SOURCE_APP="/usr/lib/voiddesk/app"

if [ -z "${HOME:-}" ]; then
    echo "Void Desk: HOME is not set; cannot create a per-user installation." >&2
    exit 1
fi

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
case "$DATA_HOME" in
    /*) ;;
    *) DATA_HOME="$HOME/.local/share" ;;
esac
USER_ROOT="$DATA_HOME/voiddesk"
APP_HOME="$USER_ROOT/app"
VERSION_FILE="$APP_HOME/.voiddesk-package-version"

[ -d "$SOURCE_APP" ] || {
    echo "Void Desk: packaged application files are missing at $SOURCE_APP." >&2
    exit 1
}

mkdir -p "$USER_ROOT"
chmod 700 "$USER_ROOT" 2>/dev/null || true

# Keep all writable state inside this user's real app directory. Python's venv
# creator cannot initialize an environment through a symlinked directory.
[ ! -L "$APP_HOME" ] || {
    echo "Void Desk: refusing a symbolic-link application directory: $APP_HOME" >&2
    exit 1
}
mkdir -p "$APP_HOME"

for persistent in data .venv_desktop runtime; do
    if [ -L "$APP_HOME/$persistent" ]; then
        echo "Void Desk: refusing a symbolic link for persistent path $APP_HOME/$persistent" >&2
        exit 1
    fi
done

CURRENT_VERSION=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION="$(cat "$VERSION_FILE")"
fi

if [ "$CURRENT_VERSION" != "$PACKAGE_VERSION" ]; then
    # Preserve user data, logs, the first-run virtualenv and generated runtime,
    # while replacing stale application code on package upgrades.
    find "$APP_HOME" -mindepth 1 -maxdepth 1 \
        ! -name data \
        ! -name .venv_desktop \
        ! -name runtime \
        -exec rm -rf -- {} +

    cp -R --preserve=mode,timestamps "$SOURCE_APP/." "$APP_HOME/"
    mkdir -p "$APP_HOME/data" "$APP_HOME/runtime"
    printf '%s\n' "$PACKAGE_VERSION" > "$VERSION_FILE"
fi

export VOIDDESK_PC=1
export VOIDDESK_APP_DIR="$APP_HOME"
exec python3 "$APP_HOME/voiddesk.py" --py "$@"

VOIDDESK_LAUNCHER

sed -i "s/@PACKAGE_VERSION@/$VERSION/g" "$DEB_ROOT/usr/bin/voiddesk"
chmod 0755 "$DEB_ROOT/usr/bin/voiddesk"

rm -f -- "$DEB"
dpkg-deb --root-owner-group --build "$DEB_ROOT" "$DEB" >/dev/null

DEB_SHA="$DEB.sha256"
(
    cd "$OUT_DIR"
    sha256sum "$(basename "$DEB")" > "$(basename "$DEB_SHA")"
    sha256sum -c "$(basename "$DEB_SHA")"
)

printf '\n[voiddesk-build] COMPLETE\n'
printf '  muOS: %s\n' "$MUXAPP"
printf '  PC:   %s\n' "$DEB"
printf '  SHA:  %s\n' "$MUXAPP.sha256"
printf '  SHA:  %s\n' "$DEB_SHA"
printf '\nInstall the PC package with:\n  sudo apt install ./%s\n' "$(basename "$DEB")"
printf 'Copy the .muxapp to the device SD card ARCHIVE/ folder and install it\nwith the muOS Archive Manager.\n'
