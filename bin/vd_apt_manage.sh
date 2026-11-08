#!/bin/sh
# VoidDesk APT access, strictly inside the optional Debian/Ubuntu XFCE image.
# Usage: vd_apt_manage.sh catalog <search|installed|info> [query|package]
#        vd_apt_manage.sh <update|upgrade|clean|install|remove> [package...]
set -eu
umask 077
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
LOG="$DATA/apt_manage.log"
ACTION="${1:-}"
[ -n "$ACTION" ] || { echo "missing action"; exit 2; }
shift || true
[ -f "$IMG" ] || { echo "XFCE image not found: $IMG"; exit 2; }
case "$ACTION" in
  catalog)
    MODE="${1:-}"; shift || true
    case "$MODE" in search|installed|info) ;; *) echo "invalid catalog mode"; exit 2;; esac
    ;;
  update|upgrade|clean|install|remove) MODE="$ACTION" ;;
  *) echo "unsupported APT action"; exit 2 ;;
esac
valid_pkg() {
  case "$1" in
    ''|*[!a-z0-9+.-]*|[-+.]*) return 1 ;;
    *) return 0 ;;
  esac
}
case "$MODE" in
  search) [ $# -eq 1 ] || { echo "search requires one query"; exit 2; } ;;
  installed) [ $# -eq 0 ] || { echo "installed takes no arguments"; exit 2; } ;;
  info|install|remove)
    [ $# -ge 1 ] || { echo "$MODE requires package names"; exit 2; }
    for pkg in "$@"; do valid_pkg "$pkg" || { echo "invalid package name: $pkg"; exit 2; }; done
    ;;
  update|upgrade|clean) [ $# -eq 0 ] || { echo "$MODE takes no package arguments"; exit 2; } ;;
esac
mkdir -p "$DATA" "$MNT"
LOCK="$DATA/.apt-manager.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "another APT operation is already using the XFCE image"
  exit 75
fi
: > "$LOG"
printf '%s === %s %s ===\n' "$(date)" "$ACTION" "$*" >> "$LOG"
mounted() { grep -Fq " $1 " /proc/mounts 2>/dev/null; }
WE_MOUNTED=0 DEV_MOUNTED=0 PROC_MOUNTED=0 SYS_MOUNTED=0
cleanup() {
  rmdir "$LOCK" 2>/dev/null || true
  [ "$SYS_MOUNTED" = 1 ] && umount "$MNT/sys" 2>/dev/null || true
  [ "$PROC_MOUNTED" = 1 ] && umount "$MNT/proc" 2>/dev/null || true
  [ "$DEV_MOUNTED" = 1 ] && umount "$MNT/dev" 2>/dev/null || true
  if [ "$WE_MOUNTED" = 1 ]; then
    sync
    umount "$MNT" 2>/dev/null || umount -l "$MNT" 2>/dev/null || true
  fi
}
trap cleanup EXIT HUP INT TERM
if ! mounted "$MNT"; then
  mount -o loop "$IMG" "$MNT" || { echo "cannot mount XFCE image"; exit 1; }
  WE_MOUNTED=1
fi
mkdir -p "$MNT/dev" "$MNT/proc" "$MNT/sys"
if ! mounted "$MNT/dev"; then mount -o bind /dev "$MNT/dev" && DEV_MOUNTED=1; fi
if ! mounted "$MNT/proc"; then mount -t proc proc "$MNT/proc" && PROC_MOUNTED=1; fi
if ! mounted "$MNT/sys"; then mount -t sysfs sys "$MNT/sys" && SYS_MOUNTED=1; fi
[ -f /etc/resolv.conf ] && cp -f /etc/resolv.conf "$MNT/etc/resolv.conf" 2>/dev/null || true
CHROOT="chroot"
ENV="/usr/bin/env"
case "$MODE" in
  search) set -- apt-cache search --names-only -- "$1" ;;
  installed) set -- dpkg-query -W '-f=${binary:Package}\t${Version}\n' ;;
  info) set -- apt-cache show "$@" ;;
  update) set -- apt-get update ;;
  upgrade) set -- apt-get upgrade -y ;;
  clean) set -- apt-get clean ;;
  install) set -- apt-get install -y --no-install-recommends "$@" ;;
  remove) set -- apt-get remove -y "$@" ;;
esac
if "$CHROOT" "$MNT" "$ENV" DEBIAN_FRONTEND=noninteractive PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$@" > "$LOG" 2>&1; then
  cat "$LOG"
else
  RC=$?
  cat "$LOG"
  exit "$RC"
fi
