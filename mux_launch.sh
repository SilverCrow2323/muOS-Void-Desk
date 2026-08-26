#!/bin/sh
# HELP: VoidDesk - pannello di controllo suite Void (runtime pygame, log, info)
# ICON: voiddesk
# GRID: voiddesk

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="$APP_DIR/data"
mkdir -p "$DATA"
mkdir -p "$DATA/logs"
LOG="$DATA/logs/voiddesk.log"

echo "$(date) === VOIDDESK v10.5.0 "D.N" launch (dir: $APP_DIR) ===" >>"$LOG"

PY3="$(command -v python3)"
if [ -z "$PY3" ]; then
	echo "FATAL: python3 non trovato" >>"$LOG"
	exit 1
fi

RC_FILE="$DATA/.last_rc"

# tutti gli script python devono vedere il runtime pygame installato
# nella cartella dell'app (senza, niente schermate: era il bug).
PYRUN() {
	PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
		PYGAME_HIDE_SUPPORT_PROMPT=1 \
		VOIDDESK_NOINTRO="$NOINTRO" \
		"$PY3" "$@"
}

# --- Verifica e installazione pygame migliorata ---
BOOTSTRAP() {
    # Se il marker .pygame_ready non esiste o runtime è assente, esegui bootstrap
    if [ ! -f "$DATA/.pygame_ready" ] || [ ! -d "$APP_DIR/runtime" ]; then
        echo "$(date) === BOOTSTRAP: avvio bootstrap_lite.py ===" >>"$LOG"
        { PYRUN "$APP_DIR/bin/bootstrap_lite.py"; echo "$?" >"$RC_FILE"; } 2>&1 | tee -a "$LOG"
        RC="$(cat "$RC_FILE" 2>/dev/null || echo 1)"
        if [ "$RC" -ne 0 ]; then
            echo "FATAL: bootstrap fallito, impossibile procedere." >>"$LOG"
            return 1
        fi
    fi
    return 0
}

DESK() {
	echo "$(date) === DESK start ===" >>"$LOG"
	# Use debug wrapper to capture silent crashes
	PYRUN "$APP_DIR/bin/debug_main.py" >>"$LOG" 2>&1
	RC=$?
	echo "$(date) === DESK exit ($RC) ===" >>"$LOG"
	if [ -f "$DATA/logs/voiddesk_debug.log" ]; then
		echo "=== DEBUG LOG ===" >>"$LOG"
		cat "$DATA/logs/voiddesk_debug.log" >>"$LOG"
	fi
	return $RC
}

VDLANG() {
	grep -q '"lang": *"en"' "$DATA/desk_config.json" 2>/dev/null &&
		echo en || echo it
}

# loader "torno al menu": copre il riavvio di python+pygame dopo le azioni
# pesanti. Muore quando main.py tocca /tmp/.vd_menu_up (o dopo 25s).
MENULOAD() {
	rm -f /tmp/.vd_menu_up
	L="torno al menu..."
	[ "$(VDLANG)" = "en" ] && L="back to the menu..."
	"$PY3" "$APP_DIR/bin/vd_loader.py" --title "VOID-DESK" --label "$L" \
		--feature "Menu" \
		--stop /tmp/.vd_menu_up --timeout 25 >/dev/null 2>&1 &
}

if [ ! -f "$DATA/.pygame_ready" ] || [ ! -d "$APP_DIR/runtime" ]; then
	BOOTSTRAP || { sleep 6; exit 1; }
fi

NOINTRO=""
while :; do
	DESK
	RC=$?
	NOINTRO="1"          # la sigla la vedi al lancio, non a ogni rientro
	case "$RC" in
	10)
		echo "$(date) reinstallazione runtime richiesta" >>"$LOG"
		rm -f "$DATA/.pygame_ready"
		rm -rf "$APP_DIR/runtime"
		BOOTSTRAP || break
		;;
	11)
		echo "$(date) avvio desktop XFCE" >>"$LOG"
		rm -f /tmp/vd_progress /tmp/vd_items /tmp/.vd_x_ran /tmp/.vd_anim \
			"$DATA/xfce_mnt/tmp/.vd_x_up" 2>/dev/null
		T="AVVIO DESKTOP XFCE"; L="preparo l'ambiente"
		if [ "$(VDLANG)" = "en" ]; then
			T="STARTING XFCE DESKTOP"; L="preparing the environment"
		fi
		printf '4|%s\n' "$L" >/tmp/vd_progress
		{
			echo "inizializza server X"
			echo "prepara sessione utente"
			echo "avvia compositor"
			echo "carica pannelli"
		} > /tmp/vd_items
		"$PY3" "$APP_DIR/bin/vd_loader.py" --title "$T" \
			--progress /tmp/vd_progress \
			--feature "XFCE Desktop" \
			--items /tmp/vd_items \
			--stop "$DATA/xfce_mnt/tmp/.vd_x_up" \
			--stop /tmp/.vd_anim \
			--timeout 900 >/dev/null 2>&1 &
		VDL=$!
		"$APP_DIR/bin/xfce_launch.sh"
		XRC=$?
		kill "$VDL" 2>/dev/null
		echo "$(date) rientro da XFCE ($XRC)" >>"$LOG"
		if [ "$XRC" -ne 0 ] && [ ! -f /tmp/.vd_x_ran ]; then
			# X non e' MAI partito: errore vero, e si legge A SCHERMO
			tail -n 14 "$DATA/xfce_session.log" 2>/dev/null |
				"$PY3" "$APP_DIR/lib/fbmsg.py" \
					"AVVIO XFCE FALLITO (rc=$XRC)" 8
		fi
		MENULOAD
		;;
	13)
		NAME="$(sed -n 1p "$DATA/.install_pkg" 2>/dev/null)"
		PKGS="$(sed -n 2p "$DATA/.install_pkg" 2>/dev/null)"
		echo "$(date) installazione programma: $NAME ($PKGS)" >>"$LOG"
		{ PYRUN "$APP_DIR/bin/xfce_install.py" "$NAME" "$PKGS"; echo "$?" >"$RC_FILE"; } 2>&1 | tee -a "$LOG"
		XRC="$(cat "$RC_FILE" 2>/dev/null || echo 1)"
		[ "$XRC" -ne 0 ] && sleep 8 || sleep 3
		MENULOAD
		;;
	14)
		NAME="$(sed -n 1p "$DATA/.install_pkg" 2>/dev/null)"
		PKGS="$(sed -n 2p "$DATA/.install_pkg" 2>/dev/null)"
		echo "$(date) disinstallazione: $NAME ($PKGS)" >>"$LOG"
		{ VOIDDESK_MODE=remove PYRUN "$APP_DIR/bin/xfce_install.py" "$NAME" "$PKGS" remove; echo "$?" >"$RC_FILE"; } 2>&1 | tee -a "$LOG"
		sleep 2
		MENULOAD
		;;
	15)
		echo "$(date) aggiornamento sistema" >>"$LOG"
		{ PYRUN "$APP_DIR/bin/xfce_update.py"; echo "$?" >"$RC_FILE"; } 2>&1 | tee -a "$LOG"
		sleep 2
		MENULOAD
		;;
	12)
		echo "$(date) installazione desktop XFCE" >>"$LOG"
		{ PYRUN "$APP_DIR/bin/xfce_bootstrap.py"; echo "$?" >"$RC_FILE"; } 2>&1 | tee -a "$LOG"
		XRC="$(cat "$RC_FILE" 2>/dev/null || echo 1)"
		[ "$XRC" -ne 0 ] && sleep 8
		MENULOAD
		;;
	16)
		APPD="$(sed -n 1p "$DATA/.muos_app" 2>/dev/null)"
		APPN="$(sed -n 2p "$DATA/.muos_app" 2>/dev/null)"
		echo "$(date) avvio app muOS: $APPN" >>"$LOG"
		GOV="$(cat "$DATA/.muos_gov" 2>/dev/null)"
		GPOL="/sys/devices/system/cpu/cpufreq/policy0/scaling_governor"
		OLDGOV=""
		if [ -n "$GOV" ] && [ "$GOV" != "default" ] && [ -w "$GPOL" ]; then
			OLDGOV="$(cat "$GPOL" 2>/dev/null)"
			for P in /sys/devices/system/cpu/cpufreq/policy*; do
				echo "$GOV" >"$P/scaling_governor" 2>/dev/null
			done
			echo "$(date) governor app: $GOV" >>"$LOG"
		fi
		if [ -f "$APPD/mux_launch.sh" ]; then
			# stesso patto di muOS: schermo tutto suo, poi si torna
			( cd "$APPD" && if [ -x ./mux_launch.sh ]; then \
				./mux_launch.sh; else sh ./mux_launch.sh; fi ) \
				>>"$LOG" 2>&1
			echo "$(date) app muOS terminata ($?)" >>"$LOG"
		else
			echo "$(date) script app non trovato: $APPD" >>"$LOG"
		fi
		if [ -n "$OLDGOV" ]; then
			for P in /sys/devices/system/cpu/cpufreq/policy*; do
				echo "$OLDGOV" >"$P/scaling_governor" 2>/dev/null
			done
		fi
		MENULOAD
		;;
	17)
		CMDX="$(cat "$DATA/.xterm_cmd" 2>/dev/null)"
		echo "$(date) avvio terminale vero (cmd='$CMDX')" >>"$LOG"
		"$APP_DIR/bin/vd_xterm_launch.sh" "$CMDX"
		XRC=$?
		echo "$(date) rientro da terminale vero ($XRC)" >>"$LOG"
		MENULOAD
		;;
		18)
		PROG=$(cat "$DATA/.outdesk_sel" 2>/dev/null)
		echo "$(date) avvio Outer Desk: $PROG (diretto da .py)" >>"$LOG"
		# Mappa app key -> percorso script (.py).
		# Lancia direttamente il file python: nessun mux_launch.sh figlio,
		# nessun outdeskintro.py che blocca con SDL_VIDEODRIVER=dummy.
		SCRIPT=""
		LOGO=""
		case "$PROG" in
			portable_forger)
				SCRIPT="$APP_DIR/outdesk/Portable_Forger/portable_forger.py"
				LOGO="$APP_DIR/assets/logos/portable_forger.png"
				;;
			disc_crusher)
				SCRIPT="$APP_DIR/outdesk/Disc_Crusher/discs_crusher.py"
				LOGO="$APP_DIR/assets/logos/disc_crusher.png"
				;;
			ethostore)
				SCRIPT="$APP_DIR/outdesk/EthoStore/ethostore.py"
				LOGO="$APP_DIR/assets/logos/ethostore.png"
				;;
			media_player)
				SCRIPT="$APP_DIR/outdesk/MediaPlayer/media_player.py"
				LOGO="$APP_DIR/assets/logos/media_vault.png"
				;;
			image_viewer)
				SCRIPT="$APP_DIR/outdesk/ImageViewer/image_viewer.py"
				LOGO="$APP_DIR/assets/logos/media_lib.png"
				;;
			bootanim_manager)
				SCRIPT="$APP_DIR/outdesk/BootAnimManager/bootanim_manager.py"
				LOGO=""
				;;
			little_mischief)
				SCRIPT="$APP_DIR/outdesk/Little_Mischief/little_mischief.py"
				LOGO="$APP_DIR/assets/logos/networkprobe.png"
				;;
		esac
		if [ -n "$SCRIPT" ] && [ -f "$SCRIPT" ]; then
			# Schermata vuota intanto che l'app si carica: non blocca,
			# si limita a riempire lo schermo di nero per qualche frame.
			"$PY3" "$APP_DIR/bin/vd_blank.py" "$LOGO" >/dev/null 2>&1 &
			BLANK_PID=$!
			# Lancia direttamente il .py con environment corretto
			LD_LIBRARY_PATH="$APP_DIR/runtime:/mnt/mmc/MUOS/PortMaster${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
				PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
				PYGAME_HIDE_SUPPORT_PROMPT=1 \
				"$PY3" "$SCRIPT" >>"$LOG" 2>&1
			RC=$?
			echo "$(date) app Outer Desk terminata ($RC)" >>"$LOG"
			kill "$BLANK_PID" 2>/dev/null
		else
			echo "$(date) script app non trovato: $PROG ($SCRIPT)" >>"$LOG"
		fi
		rm -f "$DATA/.outdesk_sel"
		MENULOAD
		;;
	19)
		RTCORE=$(cat /tmp/.vd_rtcore_sel 2>/dev/null)
		echo "$(date) avvio Rt:CORE build: $RTCORE" >>"$LOG"
		if [ -n "$RTCORE" ] && [ -f "$RTCORE" ]; then
			PYRUN "$RTCORE" >>"$LOG" 2>&1
		else
			echo "$(date) Rt:CORE build non trovata: $RTCORE" >>"$LOG"
		fi
		rm -f /tmp/.vd_rtcore_sel
		MENULOAD
		;;
	20)
		echo "$(date) avvio Deep VOID DESK" >>"$LOG"
		PYRUN "$APP_DIR/sgrub/deepvoiddesk/main.py" >>"$LOG" 2>&1
		MENULOAD
		;;
	21)
		echo "$(date) avvio Rt:GRUB//Sbrobs" >>"$LOG"
		PYRUN "$APP_DIR/sgrub/grubmenu.py" >>"$LOG" 2>&1
		MENULOAD
		;;
	*)
		break
	;;
	esac
done
exit 0
