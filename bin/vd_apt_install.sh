#!/bin/sh
# VOIDDESK // vd_apt_install.sh - install apt packages in the XFCE chroot
# Usage: vd_apt_install.sh <pkg1> [pkg2 ...]
set -f
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
LOG="$DATA/apt_install.log"

if [ $# -eq 0 ]; then echo "Usage: $0 <package> [package...]"; exit 1; fi
if [ ! -f "$IMG" ]; then echo "XFCE image not found: $IMG"; exit 2; fi

. "$APP_DIR/bin/vd_mount_common.sh"
MNTED() { vd_mount_present "$APP_DIR" "$1"; }
mkdir -p "$DATA" "$MNT"
: > "$LOG"
echo "$(date) === vd_apt_install: $* ===" >> "$LOG"

WE_MOUNTED=0
if ! MNTED "$MNT"; then
  mount -o loop "$IMG" "$MNT" 2>>"$LOG" || { echo "mount failed"; exit 1; }
  WE_MOUNTED=1
fi

DEV_MOUNTED=0; PROC_MOUNTED=0; SYS_MOUNTED=0
for D in dev proc sys; do mkdir -p "$MNT/$D"; done
if [ -e /dev ] && ! MNTED "$MNT/dev"; then
  mount -o bind /dev "$MNT/dev" 2>>"$LOG" && DEV_MOUNTED=1
fi
if ! MNTED "$MNT/proc"; then mount -t proc proc "$MNT/proc" 2>>"$LOG" && PROC_MOUNTED=1; fi
if ! MNTED "$MNT/sys"; then mount -t sysfs sys "$MNT/sys" 2>>"$LOG" && SYS_MOUNTED=1; fi
cp -f /etc/resolv.conf "$MNT/etc/resolv.conf" 2>/dev/null

chroot "$MNT" /usr/bin/env HOME=/root USER=root LOGNAME=root SHELL=/bin/bash \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  DEBIAN_FRONTEND=noninteractive \
  apt-get install -y "$@" 2>&1 | tee -a "$LOG"
RC=$?

[ "$SYS_MOUNTED" = 1 ] && umount "$MNT/sys" 2>/dev/null
[ "$PROC_MOUNTED" = 1 ] && umount "$MNT/proc" 2>/dev/null
[ "$DEV_MOUNTED" = 1 ] && umount "$MNT/dev" 2>/dev/null
if [ "$WE_MOUNTED" = 1 ]; then
  sleep 0.3
  umount "$MNT" 2>/dev/null || umount -l "$MNT" 2>/dev/null
fi
echo "exit: $RC"
exit $RC
