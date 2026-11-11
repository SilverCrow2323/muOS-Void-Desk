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
PY3="$(command -v python3)"

. "$APP_DIR/bin/vd_mount_common.sh"
MNTED() { vd_mount_present "$APP_DIR" "$1"; }
MOUNT_CREATED=0
MOUNT_IF_NEEDED() {
    _target=$1
    shift
    vd_mount_ensure "$APP_DIR" "$_target" "$@"
    _mount_rc=$?
    MOUNT_CREATED=$VD_MOUNT_CREATED
    return "$_mount_rc"
}

rm -f "$DONE"
: >"$LOG"

if [ ! -f "$DATA/.xfce_ready" ] || [ ! -f "$IMG" ]; then
	echo "$(date) base non pronta: niente Void CHD senza di essa" >>"$LOG"
	echo "12" >"$DONE"
	exit 12
fi

WE_MOUNTED=0
mkdir -p "$MNT"
MNTED "$MNT"
MOUNT_STATE=$?
case "$MOUNT_STATE" in
	0) ;;
	1)
		mount -o loop "$IMG" "$MNT" || {
			echo "$(date) mount loop fallito" >>"$LOG"
			echo "1" >"$DONE"
			exit 1
		}
		WE_MOUNTED=1
		;;
	*)
		echo "$(date) stato mount non verificabile; chdman annullato" >>"$LOG"
		echo "1" >"$DONE"
		exit 1
		;;
esac

for D in dev proc sys; do mkdir -p "$MNT/$D"; done
WE_MOUNTED_DEV=0
WE_MOUNTED_PROC=0
WE_MOUNTED_SYS=0
WE_MOUNTED_MMC=0
WE_MOUNTED_SDCARD=0

UNMOUNT_OWNED() {
	_path=$1
	MNTED "$_path"
	_state=$?
	if [ "$_state" -eq 0 ]; then
		if ! umount "$_path" 2>/dev/null; then
			umount -l "$_path" 2>/dev/null || true
		fi
		MNTED "$_path"
		_after=$?
		if [ "$_after" -ne 1 ]; then
			echo "$(date) cleanup non verificato: $_path" >>"$LOG"
			RC=1
		fi
	elif [ "$_state" -gt 1 ]; then
		echo "$(date) impossibile verificare cleanup: $_path" >>"$LOG"
		RC=1
	fi
}

ABORT_SETUP() {
	echo "$(date) preparazione mount fallita; chdman annullato" >>"$LOG"
	echo "1" >"$DONE"
	if [ "$WE_MOUNTED" = 1 ]; then
		PYTHONPATH="$APP_DIR/desk${PYTHONPATH:+:$PYTHONPATH}" \
			"$PY3" -c 'import imgmount, sys; sys.exit(0 if imgmount.umount_tree(sys.argv[1], sys.argv[2]) else 1)' \
			"$MNT" "$IMG" >>"$LOG" 2>&1
		[ "$?" -eq 0 ] || echo "$(date) cleanup immagine incompleto" >>"$LOG"
	else
		[ "$WE_MOUNTED_MMC" = 1 ] && UNMOUNT_OWNED "$MNT/mnt/mmc"
		[ "$WE_MOUNTED_SDCARD" = 1 ] && UNMOUNT_OWNED "$MNT/mnt/sdcard"
		[ "$WE_MOUNTED_PROC" = 1 ] && UNMOUNT_OWNED "$MNT/proc"
		[ "$WE_MOUNTED_SYS" = 1 ] && UNMOUNT_OWNED "$MNT/sys"
		[ "$WE_MOUNTED_DEV" = 1 ] && UNMOUNT_OWNED "$MNT/dev"
	fi
	exit 1
}

if ! MOUNT_IF_NEEDED "$MNT/dev" mount -o bind /dev "$MNT/dev"; then
	echo "$(date) stato mount /dev non valido; chdman annullato" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_DEV=1
if ! MOUNT_IF_NEEDED "$MNT/proc" mount -t proc proc "$MNT/proc"; then
	echo "$(date) stato mount /proc non valido; chdman annullato" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_PROC=1
if ! MOUNT_IF_NEEDED "$MNT/sys" mount -t sysfs sys "$MNT/sys"; then
	echo "$(date) stato mount /sys non valido; chdman annullato" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_SYS=1

# le SD, cosi' chdman vede i file dei giochi -- stesso posto identico
# sia fuori che dentro il chroot, nessuna traduzione di percorso serve
for D in /mnt/mmc /mnt/sdcard; do
	[ -d "$D" ] || continue
	mkdir -p "$MNT$D"
	MOUNT_IF_NEEDED "$MNT$D" mount -o bind "$D" "$MNT$D" || {
		echo "$(date) stato mount non valido: $MNT$D; chdman annullato" >>"$LOG"
		ABORT_SETUP()
	}
	case "$D" in
		/mnt/mmc) [ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_MMC=1 ;;
		/mnt/sdcard) [ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_SDCARD=1 ;;
	esac
done

echo "$(date) === chdman $ARGS ===" >>"$LOG"
chroot "$MNT" /usr/bin/env \
	PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games \
	chdman $ARGS >>"$LOG" 2>&1
RC=$?
echo "$(date) chdman terminato (rc=$RC)" >>"$LOG"

if [ "$WE_MOUNTED" = 1 ]; then
	PYTHONPATH="$APP_DIR/desk${PYTHONPATH:+:$PYTHONPATH}" \
		"$PY3" -c 'import imgmount, sys; sys.exit(0 if imgmount.umount_tree(sys.argv[1], sys.argv[2]) else 1)' \
		"$MNT" "$IMG" >>"$LOG" 2>&1
	if [ "$?" -ne 0 ]; then
		echo "$(date) cleanup immagine incompleto" >>"$LOG"
		RC=1
	fi
else
	[ "$WE_MOUNTED_MMC" = 1 ] && UNMOUNT_OWNED "$MNT/mnt/mmc"
	[ "$WE_MOUNTED_SDCARD" = 1 ] && UNMOUNT_OWNED "$MNT/mnt/sdcard"
	[ "$WE_MOUNTED_PROC" = 1 ] && UNMOUNT_OWNED "$MNT/proc"
	[ "$WE_MOUNTED_SYS" = 1 ] && UNMOUNT_OWNED "$MNT/sys"
	[ "$WE_MOUNTED_DEV" = 1 ] && UNMOUNT_OWNED "$MNT/dev"
fi
echo "$RC" >"$DONE"
exit $RC
