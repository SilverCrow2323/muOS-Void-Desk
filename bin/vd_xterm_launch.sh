#!/bin/sh
# vd_xterm_launch.sh -- terminale VERO (xterm su una sessione X minima,
# senza window manager) per i CLI tools e per Rt:TOOLBOX > Terminal.
#
# Perche' non la shell finta in pygame: programmi come cmatrix, nyancat
# o ani-cli (che usa fzf per i suoi menu) non finiscono mai da soli o
# hanno bisogno di un vero terminale ANSI/TTY per disegnare -- catturare
# il loro output con subprocess.run() li fa solo scadere in timeout.
# Qui invece girano dentro un terminale vero, esattamente come su un PC.
set -f
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
LOG="$DATA/xterm.log"
CMD="$1"
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

if [ ! -f "$DATA/.xfce_ready" ] || [ ! -f "$IMG" ]; then
	echo "$(date) base XFCE non pronta: niente terminale vero senza di essa" >>"$LOG"
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
			exit 1
		}
		WE_MOUNTED=1
		;;
	*)
		echo "$(date) stato mount non verificabile: abort prima del chroot" >>"$LOG"
		exit 1
		;;
esac

# stessa identica ricetta di /dev-proc-sys di xfce_launch.sh: senza,
# xterm non trova nemmeno /dev/pts per aprire un pseudo-terminale
for D in dev proc sys; do mkdir -p "$MNT/$D"; done
WE_MOUNTED_DEV=0
WE_MOUNTED_PROC=0
WE_MOUNTED_SYS=0
WE_MOUNTED_PTS=0
WE_MOUNTED_SHM=0
WE_MOUNTED_INPUT=0

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
	echo "$(date) preparazione mount fallita; chroot annullato" >>"$LOG"
	if [ "$WE_MOUNTED" = 1 ]; then
		PYTHONPATH="$APP_DIR/desk${PYTHONPATH:+:$PYTHONPATH}" \
			"$PY3" -c 'import imgmount, sys; sys.exit(0 if imgmount.umount_tree(sys.argv[1], sys.argv[2]) else 1)' \
			"$MNT" "$IMG" >>"$LOG" 2>&1
		[ "$?" -eq 0 ] || echo "$(date) cleanup immagine incompleto" >>"$LOG"
	else
		[ "$WE_MOUNTED_INPUT" = 1 ] && UNMOUNT_OWNED "$MNT/dev/input"
		[ "$WE_MOUNTED_SHM" = 1 ] && UNMOUNT_OWNED "$MNT/dev/shm"
		[ "$WE_MOUNTED_PTS" = 1 ] && UNMOUNT_OWNED "$MNT/dev/pts"
		[ "$WE_MOUNTED_PROC" = 1 ] && UNMOUNT_OWNED "$MNT/proc"
		[ "$WE_MOUNTED_SYS" = 1 ] && UNMOUNT_OWNED "$MNT/sys"
		[ "$WE_MOUNTED_DEV" = 1 ] && UNMOUNT_OWNED "$MNT/dev"
	fi
	exit 1
}

if ! MOUNT_IF_NEEDED "$MNT/dev" mount -o bind /dev "$MNT/dev"; then
	echo "$(date) stato mount /dev non valido; abort prima del chroot" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_DEV=1
if ! MOUNT_IF_NEEDED "$MNT/proc" mount -t proc proc "$MNT/proc"; then
	echo "$(date) stato mount /proc non valido; abort prima del chroot" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_PROC=1
if ! MOUNT_IF_NEEDED "$MNT/sys" mount -t sysfs sys "$MNT/sys"; then
	echo "$(date) stato mount /sys non valido; abort prima del chroot" >>"$LOG"
	ABORT_SETUP()
fi
[ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_SYS=1
for SUB in /dev/pts /dev/shm /dev/input; do
	[ -e "$SUB" ] || continue
	mkdir -p "$MNT$SUB"
	if ! MOUNT_IF_NEEDED "$MNT$SUB" mount -o bind "$SUB" "$MNT$SUB" 2>/dev/null; then
		echo "$(date) stato mount non valido: $MNT$SUB; abort prima del chroot" >>"$LOG"
		ABORT_SETUP()
	fi
	case "$SUB" in
		/dev/pts) [ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_PTS=1 ;;
		/dev/shm) [ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_SHM=1 ;;
		/dev/input) [ "$MOUNT_CREATED" = 1 ] && WE_MOUNTED_INPUT=1 ;;
	esac
done

mkdir -p "$MNT/root" "$MNT/tmp"
cp -f "$APP_DIR/assets/xterm/xinitrc" "$MNT/root/.xinitrc_term" 2>/dev/null
chmod +x "$MNT/root/.xinitrc_term" 2>/dev/null
printf '%s' "$CMD" > "$MNT/tmp/vd_xterm_cmd" 2>/dev/null
printf 'cli' > "$MNT/tmp/.vd_env" 2>/dev/null
KBH="$(sed -n 's/.*"kbd_h": *\([0-9]*\).*/\1/p' \
	"$DATA/desk_config.json" 2>/dev/null | head -1)"
printf '%s' "${KBH:-230}" > "$MNT/tmp/vd_kbd_h" 2>/dev/null

# profilo dedicato "terminale": niente mouse, solo frecce vere -- qui
# serve una tastiera seria, non un cursore che non useremo mai
PROFILE="terminale"
mkdir -p "$MNT/root/.qjoypad3"
if [ -n "$PY3" ] && ! "$PY3" "$APP_DIR/bin/gen_layout.py" "$PROFILE" \
		"$MNT/root/.qjoypad3/Default.lyt" 2>>"$LOG"; then
	[ -f "$APP_DIR/assets/xfce/qjoypad_$PROFILE.lyt" ] &&
		cp -f "$APP_DIR/assets/xfce/qjoypad_$PROFILE.lyt" \
			"$MNT/root/.qjoypad3/Default.lyt"
fi
printf 'Default\n' > "$MNT/root/.qjoypad3/layout"

# vd_hotkey.py sul lato host: gestisce il tasto per la tastiera a
# schermo (matchbox-keyboard on-demand) e START+SELECT per il
# pannello -- VD_TERM_KBD=1 dice a onboard_toggle() di usare la
# geometria grande e ancorata in basso, non quella minuscola di default
# pannello LIVE -- identico a quello che gira nei desktop veri
HOTKEY_PID=""
if [ -n "$PY3" ] && [ -f "$APP_DIR/bin/vd_hotkey.py" ]; then
	PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
		PYGAME_HIDE_SUPPORT_PROMPT=1 VD_TERM_KBD=1 \
		"$PY3" "$APP_DIR/bin/vd_hotkey.py" "$MNT" \
		>>"$DATA/vd_hotkey.log" 2>&1 &
	HOTKEY_PID=$!
fi

echo "$(date) === avvio terminale vero (cmd='$CMD') ===" >>"$LOG"
TRIES=0
while :; do
	chroot "$MNT" /usr/bin/env \
		HOME=/root USER=root LOGNAME=root SHELL=/bin/bash \
		PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games \
		/usr/bin/startx /root/.xinitrc_term -- :0 vt1 -novtswitch -keeptty \
		>>"$LOG" 2>&1
	RC=$?
	echo "$(date) terminale chiuso (rc=$RC)" >>"$LOG"
	TRIES=$((TRIES + 1))
	if [ -f "$MNT/tmp/.vd_restart" ] && [ "$TRIES" -lt 5 ]; then
		rm -f "$MNT/tmp/.vd_restart"
		echo "$(date) riavvio richiesto, ricarico lo stesso tool" >>"$LOG"
		continue
	fi
	break
done
[ -n "$HOTKEY_PID" ] && kill "$HOTKEY_PID" 2>/dev/null

if [ "$WE_MOUNTED" = 1 ]; then
	PYTHONPATH="$APP_DIR/desk${PYTHONPATH:+:$PYTHONPATH}" \
		"$PY3" -c 'import imgmount, sys; sys.exit(0 if imgmount.umount_tree(sys.argv[1], sys.argv[2]) else 1)' \
		"$MNT" "$IMG" >>"$LOG" 2>&1
	if [ "$?" -ne 0 ]; then
		echo "$(date) cleanup immagine incompleto" >>"$LOG"
		RC=1
	fi
else
	[ "$WE_MOUNTED_INPUT" = 1 ] && UNMOUNT_OWNED "$MNT/dev/input"
	[ "$WE_MOUNTED_SHM" = 1 ] && UNMOUNT_OWNED "$MNT/dev/shm"
	[ "$WE_MOUNTED_PTS" = 1 ] && UNMOUNT_OWNED "$MNT/dev/pts"
	[ "$WE_MOUNTED_PROC" = 1 ] && UNMOUNT_OWNED "$MNT/proc"
	[ "$WE_MOUNTED_SYS" = 1 ] && UNMOUNT_OWNED "$MNT/sys"
	[ "$WE_MOUNTED_DEV" = 1 ] && UNMOUNT_OWNED "$MNT/dev"
fi
exit $RC
