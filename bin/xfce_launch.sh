#!/bin/sh
# VOIDDESK // xfce_launch v3.0 - avvia il desktop XFCE dal chroot in loopback.
# Torna a muOS quando la sessione termina (Logout dal menu XFCE).

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$APP_DIR/data"
IMG="$DATA/xfce.img"
MNT="$DATA/xfce_mnt"
XLOG="$DATA/xfce_session.log"
PROGRESS="/tmp/vd_progress"

# lingua per le etichette del loader
VDLANG="it"
grep -q '"lang": *"en"' "$DATA/desk_config.json" 2>/dev/null && VDLANG="en"

# ambiente desktop scelto (xfce | icewm | lxde), default xfce
DESKENV="$(sed -n 's/.*"desk_env": *"\([a-z]*\)".*/\1/p' \
	"$DATA/desk_config.json" 2>/dev/null | head -1)"
case "$DESKENV" in icewm|lxde|xfce) ;; *) DESKENV="xfce" ;; esac

# preferenze uplink: lingua desktop, tastiera fisica, fuso orario
VDLNG="$(sed -n 's/.*"desk_lang": *"\([A-Za-z_]*\)".*/\1/p' \
	"$DATA/desk_config.json" 2>/dev/null | head -1)"
VDKBD="$(sed -n 's/.*"kbd_x": *"\([a-z]*\)".*/\1/p' \
	"$DATA/desk_config.json" 2>/dev/null | head -1)"
VDTZ="$(sed -n 's|.*"tz": *"\([A-Za-z_/]*\)".*|\1|p' \
	"$DATA/desk_config.json" 2>/dev/null | head -1)"
[ -n "$VDKBD" ] || VDKBD="us"
PROG() {
	if [ "$VDLANG" = "en" ]; then
		printf '%s|%s\n' "$1" "$3" >"$PROGRESS" 2>/dev/null
	else
		printf '%s|%s\n' "$1" "$2" >"$PROGRESS" 2>/dev/null
	fi
}

. "$APP_DIR/bin/vd_boost.sh"

PY3="$(command -v python3)"

MNTED() { grep -q " $1 " /proc/mounts 2>/dev/null; }

CLEANUP() {
	BOOST_TEARDOWN
	for P in "$MNT/run/systemd" "$MNT/var/lib/bluetooth" \
		"$MNT/var/run/wpa_supplicant" "$MNT/run/wpa_supplicant" \
		"$MNT/run/udev" "$MNT/var/run/dbus" "$MNT/run/dbus" \
		"$MNT/dev/bus/usb" "$MNT/dev/dri" "$MNT/dev/input" "$MNT/dev/snd" \
		"$MNT/dev/shm" "$MNT/dev/pts" \
		"$MNT/dev" "$MNT/proc" "$MNT/sys" "$MNT"; do
		MNTED "$P" && umount "$P" 2>/dev/null
	done
}

[ -f "$DATA/.xfce_ready" ] && [ -f "$IMG" ] || {
	echo "XFCE non installato" >>"$XLOG"
	exit 12
}

PROG 8 "monto l'immagine ext4" "mounting the ext4 image"
mkdir -p "$MNT"
MNTED "$MNT" || mount -o loop "$IMG" "$MNT" || {
	echo "$(date) mount loop fallito" >>"$XLOG"
	exit 1
}
# l'ambiente scelto e' davvero installato? Altrimenti xfce e nota nel log
case "$DESKENV" in
icewm)	[ -x "$MNT/usr/bin/icewm-session" ] || {
		echo "$(date) icewm non installato: uso xfce" >>"$XLOG"
		DESKENV="xfce"; } ;;
lxde)	[ -x "$MNT/usr/bin/startlxde" ] || {
		echo "$(date) lxde non installato: uso xfce" >>"$XLOG"
		DESKENV="xfce"; } ;;
esac

# censimento ambienti installati: START SESSION legge questo file
ENVS="xfce"
[ -x "$MNT/usr/bin/icewm-session" ] && ENVS="$ENVS icewm"
[ -x "$MNT/usr/bin/startlxde" ] && ENVS="$ENVS lxde"
echo "$ENVS" >"$DATA/.envs"

# il marker "X e' su" della sessione precedente vive DENTRO l'immagine:
# va tolto appena montata, o il loader crede che X sia gia' partito
rm -f "$MNT/tmp/.vd_x_up" 2>/dev/null

PROG 18 "collego i dispositivi" "binding devices"
for D in dev proc sys; do mkdir -p "$MNT/$D"; done
MNTED "$MNT/dev" || mount -o bind /dev "$MNT/dev"
MNTED "$MNT/proc" || mount -t proc proc "$MNT/proc"
MNTED "$MNT/sys" || mount -t sysfs sys "$MNT/sys"

# ATTENZIONE: "mount -o bind" NON e' ricorsivo: i mount dentro /dev
# (pts, shm, snd...) vanno rimontati a mano o il chroot resta muto.
for SUB in /dev/pts /dev/shm /dev/snd /dev/input /dev/dri /dev/bus/usb; do
	[ -e "$SUB" ] || continue
	mkdir -p "$MNT$SUB"
	MNTED "$MNT$SUB" || mount -o bind "$SUB" "$MNT$SUB" 2>/dev/null
done

PROG 28 "servizi host: rete e bluetooth" "host services: network, bluetooth"
# socket/servizi dell'host per WiFi, Bluetooth e hotplug
for RUN in /run/dbus /var/run/dbus /run/udev /run/wpa_supplicant \
	/var/run/wpa_supplicant /var/lib/bluetooth /run/systemd; do
	[ -e "$RUN" ] || continue
	mkdir -p "$MNT$RUN"
	MNTED "$MNT$RUN" || mount -o bind "$RUN" "$MNT$RUN" 2>/dev/null
done
cp -f /etc/resolv.conf "$MNT/etc/resolv.conf" 2>/dev/null

PROG 38 "configuro la sessione" "configuring the session"
# aggiorno la sessione dentro l'immagine (idempotente: vale per i chroot esistenti)
cp -f "$APP_DIR/assets/xfce/xinitrc" "$MNT/root/.xinitrc" 2>/dev/null
chmod +x "$MNT/root/.xinitrc" 2>/dev/null

# semina prestazioni e riparazioni (idempotente, host python)
PROG 42 "ottimizzo il desktop" "tuning the desktop"
"$PY3" - "$MNT" << 'PYSEED' >>"$XLOG" 2>&1
import os, re, shutil, subprocess, sys
mnt = sys.argv[1]

# machine-id: senza, dbus-launch muore e le app D-Bus (terminale, Thunar)
# non partono. Su ubuntu-base a volte manca.
mid = os.path.join(mnt, "etc/machine-id")
if not (os.path.exists(mid) and os.path.getsize(mid) > 10):
    subprocess.call(["chroot", mnt, "/usr/bin/dbus-uuidgen", "--ensure"])
    subprocess.call(["chroot", mnt, "/bin/sh", "-c",
                     "[ -s /etc/machine-id ] || "
                     "cp /var/lib/dbus/machine-id /etc/machine-id"])
    print("machine-id generato")

# sessioni salvate: le cancello sempre. Con SaveOnExit=false sono inutili,
# e ripulisce anche i danni delle sessioni doppie (autostart v4.4).
shutil.rmtree(os.path.join(mnt, "root/.cache/sessions"),
              ignore_errors=True)

def seed(channel, branch, prop, val, typ="bool"):
    """Imposta <property name=branch><property name=prop value=val/> nel
    perchannel-xml, creando o rattoppando quel che c'e'."""
    d = os.path.join(mnt, "root/.config/xfce4/xfconf/xfce-perchannel-xml")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, channel + ".xml")
    line = ('    <property name="%s" type="%s" value="%s"/>'
            % (prop, typ, val))
    try:
        txt = open(p).read()
    except OSError:
        txt = ('<?xml version="1.0" encoding="UTF-8"?>\n\n'
               '<channel name="%s" version="1.0">\n'
               '  <property name="%s" type="empty">\n%s\n'
               '  </property>\n</channel>\n' % (channel, branch, line))
        open(p, "w").write(txt)
        return
    pat = re.compile(r'(<property name="%s"[^>]*value=")[^"]*(")'
                     % re.escape(prop))
    if pat.search(txt):
        txt = pat.sub(lambda m: m.group(1) + val + m.group(2), txt)
    else:
        bpat = '<property name="%s" type="empty">' % branch
        if bpat in txt:
            txt = txt.replace(bpat, bpat + "\n" + line, 1)
        else:
            txt = txt.replace("</channel>",
                              '  <property name="%s" type="empty">\n%s\n'
                              '  </property>\n</channel>' % (branch, line))
    open(p, "w").write(txt)

# compositor OFF: su fbdev senza GPU e' il singolo guadagno piu' grosso
seed("xfwm4", "general", "use_compositing", "false")
# niente salvataggio sessione: avvii puliti e veloci
seed("xfce4-session", "general", "SaveOnExit", "false")
# 640x480: font compatti = dialoghi che stanno nello schermo
seed("xfwm4", "general", "title_font", "Sans Bold 8", "string")
seed("xsettings", "Gtk", "FontName", "Sans 8", "string")
seed("xsettings", "Gtk", "CursorThemeSize", "16", "int")
# DPI ridotto: restringe TUTTO il testo, quindi i dialoghi (640x480!)
seed("xsettings", "Xft", "DPI", "78", "int")

# gtk.css: la vera compattazione — padding e altezze minime giu'
css = os.path.join(mnt, "root/.config/gtk-3.0/gtk.css")
MARK = "/* SPDW compact */"
try:
    cur = open(css).read()
except OSError:
    cur = ""
if MARK in cur or not cur:
    open(css, "w").write(MARK + """
widget, button, entry, spinbutton, combobox { min-height: 0; min-width: 0; }
button { padding: 2px 7px; }
entry, spinbutton { padding: 2px 4px; }
headerbar, .titlebar { min-height: 0; padding: 0 4px; }
menuitem, .menuitem { padding: 3px 8px; }
toolbar { padding: 1px; }
notebook tab { padding: 2px 8px; min-height: 0; }
scrollbar slider { min-width: 9px; min-height: 9px; }
dialog box.dialog-action-area button { padding: 3px 10px; }
treeview { -GtkTreeView-vertical-separator: 1; }
""")
# gtk2 (GIMP e soci): font piccolo anche li'
rc2 = os.path.join(mnt, "root/.gtkrc-2.0")
try:
    r2 = open(rc2).read()
except OSError:
    r2 = ""
if "gtk-font-name" not in r2:
    open(rc2, "a").write('gtk-font-name="Sans 7"\n')

def ensure_lines(path, header, lines):
    """File di config a sezioni: crea o garantisce le righe volute."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        txt = open(path).read()
    except OSError:
        txt = ""
    if header not in txt:
        txt = (txt + "\n" if txt and not txt.endswith("\n") else txt)
        txt += header + "\n" + "\n".join(lines) + "\n"
    else:
        for ln in lines:
            key = ln.split("=")[0]
            if key + "=" in txt:
                txt = re.sub(r"(?m)^%s=.*$" % re.escape(key), ln, txt)
            else:
                txt = txt.replace(header, header + "\n" + ln, 1)
    open(path, "w").write(txt)

# GTK3: dialoghi senza headerbar e font piccolo (schermo 640x480)
ensure_lines(os.path.join(mnt, "root/.config/gtk-3.0/settings.ini"),
             "[Settings]",
             ["gtk-font-name=Sans 8",
              "gtk-dialogs-use-header=false",
              "gtk-toolbar-icon-size=small-toolbar"])
# blueman: via i plugin di rete (Mechanism/polkit non esistono nel
# chroot: erano LORO i due popup d'errore all'avvio). Pairing e audio
# BT restano. Richiede GSETTINGS_BACKEND=keyfile (esportato in xinitrc).
ensure_lines(os.path.join(mnt,
             "root/.config/glib-2.0/settings/keyfile"),
             "[org/blueman/general]",
             ["plugin-list=['!Networking', '!DhcpClient', '!PPPSupport']"])
# fuso orario scelto in UPLINK > Void Clock (vale per tutto il chroot)
try:
    import json as _j
    _tz = _j.load(open(os.path.join(os.path.dirname(mnt),
                                    "desk_config.json"))).get("tz")
except Exception:
    _tz = None
if _tz and os.path.exists(os.path.join(mnt, "usr/share/zoneinfo", _tz)):
    lt = os.path.join(mnt, "etc/localtime")
    try:
        if os.path.islink(lt) or os.path.exists(lt):
            os.remove(lt)
        os.symlink("/usr/share/zoneinfo/" + _tz, lt)
        open(os.path.join(mnt, "etc/timezone"), "w").write(_tz + "\n")
        print("timezone:", _tz)
    except OSError:
        pass

# chroot senza init: i postinst non devono provare a lanciare servizi
prc = os.path.join(mnt, "usr/sbin/policy-rc.d")
try:
    open(prc, "w").write("#!/bin/sh\nexit 101\n")
    os.chmod(prc, 0o755)
except OSError:
    pass
print("seed prestazioni ok")
PYSEED

PROG 46 "profilo controller" "controller profile"
# profilo controller scelto dal menu VOIDDESK (riscritto a ogni avvio:
# anche se QJoyPad si incarta, al riavvio si ripara da solo)
PROFILE="$(cat "$DATA/.qjoypad_profile" 2>/dev/null)"
[ -n "$PROFILE" ] || PROFILE="$(sed -n 's/.*"controller": *"\([a-z]*\)".*/\1/p' "$DATA/desk_config.json" 2>/dev/null)"
[ -n "$PROFILE" ] || PROFILE="sinistro"
mkdir -p "$MNT/root/.qjoypad3"
# il layout viene GENERATO leggendo la numerazione reale dei pulsanti dal
# kernel: i numeri "Button N" di QJoyPad dipendono dal driver joydev.
if ! "$PY3" "$APP_DIR/bin/gen_layout.py" "$PROFILE" \
	"$MNT/root/.qjoypad3/Default.lyt" 2>>"$XLOG"; then
	echo "$(date) gen_layout fallito: uso il layout statico" >>"$XLOG"
	[ -f "$APP_DIR/assets/xfce/qjoypad_$PROFILE.lyt" ] &&
		cp -f "$APP_DIR/assets/xfce/qjoypad_$PROFILE.lyt" \
			"$MNT/root/.qjoypad3/Default.lyt"
fi
printf 'Default\n' > "$MNT/root/.qjoypad3/layout"
# la GUI di QJoyPad nel desktop e' una trappola senza input: la tolgo dal menu
rm -f "$MNT/usr/share/applications/qjoypad.desktop" 2>/dev/null

PROG 52 "VOID BOOST: swap e cpu" "VOID BOOST: swap and cpu"
BOOST_SETUP

PROG 62 "condivido le SD nel desktop" "sharing SD cards"
# condivido le SD dentro il desktop (Thunar le vede in /mnt)
for D in /mnt/mmc /mnt/sdcard; do
	[ -d "$D" ] || continue
	mkdir -p "$MNT$D"
	MNTED "$MNT$D" || mount -o bind "$D" "$MNT$D"
done

# componenti di servizio (una tantum): accessibilita', zenity, task manager
if [ ! -f "$MNT/.vd_pkgs_v6" ]; then
	PROG 68 "pacchetti di servizio (una tantum: minuti)" "service packages (one-off: minutes)"
	chroot "$MNT" /bin/bash -c "DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::ForceIPv4=true -o Acquire::https::Verify-Peer=false -o Acquire::https::Verify-Host=false install -y zenity xfce4-taskmanager xdotool x11-utils matchbox-keyboard alsa-utils pulseaudio pavucontrol bluez blueman wpagui gvfs gvfs-backends udisks2 thunar-volman" >>"$XLOG" 2>&1 \
		&& touch "$MNT/.vd_pkgs_v6"
fi

# pannello rapido START+SELECT
PROG 78 "pannello rapido e tastiera" "quick panel and keyboard"
mkdir -p "$MNT/usr/local/bin"
# (vd-menu legacy: si copia solo se esiste; il pannello vero e' vd_panel.py)
[ -f "$APP_DIR/assets/xfce/vd-menu-$VDLANG.sh" ] &&
	cp -f "$APP_DIR/assets/xfce/vd-menu-$VDLANG.sh" "$MNT/usr/local/bin/vd-menu" &&
	chmod +x "$MNT/usr/local/bin/vd-menu"
rm -f "$MNT/tmp/.vd_dbus" "$MNT/tmp/.vd_restart"
PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" PYGAME_HIDE_SUPPORT_PROMPT=1 \
	python3 "$APP_DIR/bin/vd_hotkey.py" "$MNT" >>"$DATA/vd_hotkey.log" 2>&1 &
HOTKEY_PID=$!

while :; do
	PROG 86 "programmi in avvio automatico" "startup applications"
	# programmi da avviare con la sessione (menu COMPONENTI > Avvio al boot)
"$PY3" - "$MNT" "$DATA" << 'PYAUTO' >>"$XLOG" 2>&1
import json, os, sys
mnt, data = sys.argv[1], sys.argv[2]
try:
    cfg = json.load(open(os.path.join(data, "desk_config.json")))
except Exception:
    cfg = {}
d = os.path.join(mnt, "root/.config/autostart")
os.makedirs(d, exist_ok=True)
for fn in os.listdir(d):
    if fn.startswith("voiddesk-"):
        os.remove(os.path.join(d, fn))
ICEWM_ST = []
ALLOW = {"thunar", "xfce4-terminal", "xfce4-taskmanager", "mousepad",
         "netsurf-gtk", "falkon", "dillo", "transmission-gtk", "filezilla",
         "remmina", "audacious", "ristretto", "mtpaint", "gimp", "abiword",
         "gnumeric", "xpdf", "galculator", "syncthing", "barrier",
         "kdeconnect-app", "sshd", "x11vnc", "xarchiver"}
for exe in cfg.get("autostart_exec", []):
    if exe not in ALLOW:
        print("autostart bloccato (non e' un'app):", exe)
        continue
    ICEWM_ST.append(exe)
    p = os.path.join(d, "voiddesk-%s.desktop" % exe)
    with open(p, "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=%s\n"
                "Exec=%s\nX-GNOME-Autostart-enabled=true\n" % (exe, exe))
# IceWM non legge gli XDG autostart: gli scrivo il suo startup script
iw = os.path.join(mnt, "root/.icewm")
os.makedirs(iw, exist_ok=True)
with open(os.path.join(iw, "startup"), "w") as f:
    f.write("#!/bin/sh\n# generato da VOIDDESK: avvio-al-boot\n")
    for exe in ICEWM_ST:
        f.write("%s &\n" % exe)
os.chmod(os.path.join(iw, "startup"), 0o755)

print("autostart:", cfg.get("autostart_exec", []))
PYAUTO

PROG 96 "sigla di avvio" "boot animation"
# il loader lascia il palco alla bootanim (stop dedicato), poi la sigla
: > /tmp/.vd_anim
sleep 0.2
BOOTANIM_ON=1
python3 -c "
import json, sys
try:
    cfg = json.load(open('$DATA/desk_config.json'))
    v = (cfg.get('env_bootanim') or {}).get('$DESKENV', True)
    sys.exit(0 if v else 1)
except Exception:
    sys.exit(0)
" || BOOTANIM_ON=0
if [ "$BOOTANIM_ON" = "1" ]; then
	PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" PYGAME_HIDE_SUPPORT_PROMPT=1 \
		"$PY3" "$APP_DIR/bin/vd_bootanim.py" "$DESKENV" >>"$XLOG" 2>&1
fi

rm -f "$MNT/tmp/.vd_x_up" 2>/dev/null
SLOG="$DATA/session_$DESKENV.log"
echo "$(date) === avvio sessione $DESKENV ===" >>"$XLOG"
echo "$(date) === avvio sessione ===" >>"$SLOG"
	chroot "$MNT" /usr/bin/env \
		HOME=/root USER=root LOGNAME=root SHELL=/bin/bash \
		VD_ENV="$DESKENV" VD_KBD="$VDKBD" VD_LANG="$VDLNG" \
		${VDTZ:+TZ="$VDTZ"} \
		PATH=/usr/sbin:/usr/bin:/sbin:/bin \
		/usr/bin/startx /root/.xinitrc -- :0 vt1 -novtswitch -keeptty \
		>>"$SLOG" 2>&1
	RC=$?
	echo "$(date) sessione terminata ($RC)" >>"$XLOG"
	if [ -f "$MNT/tmp/.vd_restart" ]; then
		rm -f "$MNT/tmp/.vd_restart"
		echo "$(date) riavvio XFCE richiesto dal pannello" >>"$XLOG"
		continue
	fi
	break
done
kill "$HOTKEY_PID" 2>/dev/null
# X e' davvero partito almeno una volta? Il marker vive nell'immagine:
# lo esporto prima dell'umount, cosi' mux_launch sa distinguere un vero
# crash d'avvio da un normale logout (che puo' dare rc!=0 via SIGTERM).
[ -f "$MNT/tmp/.vd_x_up" ] && : > /tmp/.vd_x_ran

for D in /mnt/sdcard /mnt/mmc; do
	MNTED "$MNT$D" && umount "$MNT$D" 2>/dev/null
done
CLEANUP
exit "$RC"
