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

MNTED() { grep -q " $1 " /proc/mounts 2>/dev/null; }

if [ ! -f "$DATA/.xfce_ready" ] || [ ! -f "$IMG" ]; then
	echo "$(date) base XFCE non pronta: niente terminale vero senza di essa" >>"$LOG"
	exit 12
fi

WE_MOUNTED=0
mkdir -p "$MNT"
if ! MNTED "$MNT"; then
	mount -o loop "$IMG" "$MNT" || {
		echo "$(date) mount loop fallito" >>"$LOG"
		exit 1
	}
	WE_MOUNTED=1
fi

# stessa identica ricetta di /dev-proc-sys di xfce_launch.sh: senza,
# xterm non trova nemmeno /dev/pts per aprire un pseudo-terminale
for D in dev proc sys; do mkdir -p "$MNT/$D"; done
WE_MOUNTED_DEV=0
if ! MNTED "$MNT/dev"; then
	mount -o bind /dev "$MNT/dev" && WE_MOUNTED_DEV=1
fi
MNTED "$MNT/proc" || mount -t proc proc "$MNT/proc"
MNTED "$MNT/sys" || mount -t sysfs sys "$MNT/sys"
for SUB in /dev/pts /dev/shm /dev/input; do
	[ -e "$SUB" ] || continue
	mkdir -p "$MNT$SUB"
	MNTED "$MNT$SUB" || mount -o bind "$SUB" "$MNT$SUB" 2>/dev/null
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
PY3="$(command -v python3)"
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

for P in "$MNT/dev/input" "$MNT/dev/shm" "$MNT/dev/pts"; do
	MNTED "$P" && umount "$P" 2>/dev/null
done
MNTED "$MNT/proc" && umount "$MNT/proc" 2>/dev/null
MNTED "$MNT/sys" && umount "$MNT/sys" 2>/dev/null
[ "$WE_MOUNTED_DEV" = 1 ] && { MNTED "$MNT/dev" && umount "$MNT/dev" 2>/dev/null; }
if [ "$WE_MOUNTED" = 1 ]; then
	sleep 0.3
	umount "$MNT" 2>/dev/null || umount -l "$MNT" 2>/dev/null
fi
exit $RC
