#!/bin/sh
# vd_chdman_run.sh -- esegue chdman dentro il chroot per Void CHD.
# Niente X, niente qjoypad: chdman non e' interattivo, basta il chroot
# con le SD collegate (dentro ci sono i file sorgente/destinazione).
set -f
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
LOG="$DATA/chd_op.log"
DONE="$DATA/.chd_done"
shift 0
ARGS="$*"

MNTED() { grep -q " $1 " /proc/mounts 2>/dev/null; }

rm -f "$DONE"
: >"$LOG"

if [ ! -f "$DATA/.xfce_ready" ] || [ ! -f "$IMG" ]; then
	echo "$(date) base non pronta: niente Void CHD senza di essa" >>"$LOG"
	echo "12" >"$DONE"
	exit 12
fi

WE_MOUNTED=0
mkdir -p "$MNT"
if ! MNTED "$MNT"; then
	mount -o loop "$IMG" "$MNT" || {
		echo "$(date) mount loop fallito" >>"$LOG"
		echo "1" >"$DONE"
		exit 1
	}
	WE_MOUNTED=1
fi

for D in dev proc sys; do mkdir -p "$MNT/$D"; done
WE_MOUNTED_DEV=0
if ! MNTED "$MNT/dev"; then
	mount -o bind /dev "$MNT/dev" && WE_MOUNTED_DEV=1
fi
MNTED "$MNT/proc" || mount -t proc proc "$MNT/proc"
MNTED "$MNT/sys" || mount -t sysfs sys "$MNT/sys"

# le SD, cosi' chdman vede i file dei giochi -- stesso posto identico
# sia fuori che dentro il chroot, nessuna traduzione di percorso serve
for D in /mnt/mmc /mnt/sdcard; do
	[ -d "$D" ] || continue
	mkdir -p "$MNT$D"
	MNTED "$MNT$D" || mount -o bind "$D" "$MNT$D"
done

echo "$(date) === chdman $ARGS ===" >>"$LOG"
chroot "$MNT" /usr/bin/env \
	PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games \
	chdman $ARGS >>"$LOG" 2>&1
RC=$?
echo "$(date) chdman terminato (rc=$RC)" >>"$LOG"

for D in /mnt/mmc /mnt/sdcard; do
	MNTED "$MNT$D" && umount "$MNT$D" 2>/dev/null
done
MNTED "$MNT/proc" && umount "$MNT/proc" 2>/dev/null
MNTED "$MNT/sys" && umount "$MNT/sys" 2>/dev/null
[ "$WE_MOUNTED_DEV" = 1 ] && { MNTED "$MNT/dev" && umount "$MNT/dev" 2>/dev/null; }
if [ "$WE_MOUNTED" = 1 ]; then
	sleep 0.3
	umount "$MNT" 2>/dev/null || umount -l "$MNT" 2>/dev/null
fi
echo "$RC" >"$DONE"
exit $RC
