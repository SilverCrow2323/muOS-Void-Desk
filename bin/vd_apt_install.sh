#!/bin/sh
# VOIDDESK // vd_apt_install.sh - install apt packages in the XFCE chroot
# Usage: vd_apt_install.sh <pkg1> [pkg2 ...]
set -f
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
LOG="$DATA/apt_install.log"
PY3="${PY3:-$(command -v python3 2>/dev/null)}"

. "$APP_DIR/bin/vd_mount_common.sh"
MNTED() { vd_mount_present "$APP_DIR" "$1"; }

if [ $# -eq 0 ]; then echo "Usage: $0 <package> [package...]"; exit 1; fi
if [ ! -f "$IMG" ]; then echo "XFCE image not found: $IMG"; exit 2; fi
if [ -z "$PY3" ]; then
    echo "python3 unavailable; cannot safely inspect or clean XFCE mounts" >&2
    exit 1
fi
if ! command -v mkfifo >/dev/null 2>&1 || ! command -v tee >/dev/null 2>&1; then
    echo "mkfifo and tee are required for reliable APT output capture" >&2
    exit 1
fi

umask 077
mkdir -p "$DATA" "$MNT" || exit 1
: > "$LOG" || exit 1
echo "$(date) === vd_apt_install: $* ===" >> "$LOG"

WE_MOUNTED=0
DEV_MOUNTED=0
PROC_MOUNTED=0
SYS_MOUNTED=0
SETUP_OK=1
RC=0
CLEANUP_RC=0
FIFO="$DATA/.apt-install.$$"
TEE_PID=""

cleanup_fifo() {
    [ -n "$FIFO" ] && rm -f "$FIFO"
}
trap cleanup_fifo 0

unmount_owned() {
    TARGET=$1
    if ! umount "$TARGET" 2>/dev/null; then
        umount -l "$TARGET" 2>/dev/null || true
    fi
    if MNTED "$TARGET"; then
        echo "mount remains active: $TARGET" | tee -a "$LOG" >&2
        CLEANUP_RC=1
    fi
}

if ! MNTED "$MNT"; then
    if mount -o loop "$IMG" "$MNT" 2>>"$LOG"; then
        WE_MOUNTED=1
    else
        echo "mount failed" | tee -a "$LOG" >&2
        SETUP_OK=0
        RC=1
    fi
fi

if [ "$SETUP_OK" = 1 ]; then
    for D in dev proc sys; do
        mkdir -p "$MNT/$D" || {
            echo "cannot create $MNT/$D" | tee -a "$LOG" >&2
            SETUP_OK=0
            RC=1
            break
        }
    done
fi

if [ "$SETUP_OK" = 1 ] && [ -e /dev ] && ! MNTED "$MNT/dev"; then
    if mount -o bind /dev "$MNT/dev" 2>>"$LOG"; then
        DEV_MOUNTED=1
    else
        echo "cannot bind /dev" | tee -a "$LOG" >&2
        SETUP_OK=0
        RC=1
    fi
fi
if [ "$SETUP_OK" = 1 ] && ! MNTED "$MNT/proc"; then
    if mount -t proc proc "$MNT/proc" 2>>"$LOG"; then
        PROC_MOUNTED=1
    else
        echo "cannot mount proc" | tee -a "$LOG" >&2
        SETUP_OK=0
        RC=1
    fi
fi
if [ "$SETUP_OK" = 1 ] && ! MNTED "$MNT/sys"; then
    if mount -t sysfs sys "$MNT/sys" 2>>"$LOG"; then
        SYS_MOUNTED=1
    else
        echo "cannot mount sysfs" | tee -a "$LOG" >&2
        SETUP_OK=0
        RC=1
    fi
fi
cp -f /etc/resolv.conf "$MNT/etc/resolv.conf" 2>/dev/null || true

if [ "$SETUP_OK" = 1 ]; then
    if ! mkfifo "$FIFO"; then
        echo "cannot create APT output FIFO" | tee -a "$LOG" >&2
        RC=1
    else
        tee -a "$LOG" < "$FIFO" &
        TEE_PID=$!
        chroot "$MNT" /usr/bin/env HOME=/root USER=root LOGNAME=root SHELL=/bin/bash \
          PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
          DEBIAN_FRONTEND=noninteractive \
          apt-get install -y "$@" > "$FIFO" 2>&1
        RC=$?
        if wait "$TEE_PID"; then
            TEE_RC=0
        else
            TEE_RC=$?
        fi
        TEE_PID=""
        rm -f "$FIFO"
        FIFO=""
        if [ "$TEE_RC" -ne 0 ] && [ "$RC" -eq 0 ]; then
            echo "APT output logger failed (exit $TEE_RC)" | tee -a "$LOG" >&2
            RC=1
        fi
    fi
fi

if [ "$WE_MOUNTED" = 1 ]; then
    # This installer owns the root image: verify and release the complete tree.
    PYTHONPATH="$APP_DIR/desk${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY3" -c 'import imgmount, sys; sys.exit(0 if imgmount.umount_tree(sys.argv[1], sys.argv[2]) else 1)' \
      "$MNT" "$IMG"
    if [ $? -ne 0 ]; then
        echo "XFCE image cleanup failed; a mount or loop device is still active" \
          | tee -a "$LOG" >&2
        CLEANUP_RC=1
    fi
else
    # The root image belongs to an existing desktop session; unmount only
    # bind mounts that this installer created.
    [ "$SYS_MOUNTED" = 1 ] && unmount_owned "$MNT/sys"
    [ "$PROC_MOUNTED" = 1 ] && unmount_owned "$MNT/proc"
    [ "$DEV_MOUNTED" = 1 ] && unmount_owned "$MNT/dev"
fi

if [ "$CLEANUP_RC" -ne 0 ] && [ "$RC" -eq 0 ]; then
    RC=1
fi
echo "exit: $RC" | tee -a "$LOG"
exit "$RC"
