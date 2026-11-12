#!/bin/sh
# VOIDDESK v10.5.4 — muOS device launcher
# HELP: VoidDesk - Void suite (LÖVE or Pygame frontend, switchable in Settings)
# ICON: voiddesk
# GRID: voiddesk

. /opt/muos/script/var/func.sh
APP_BIN="python3"
SETUP_APP "$APP_BIN" ""

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="$APP_DIR/data"
LOG="$DATA/voiddesk.log"
mkdir -p "$DATA"

. "$APP_DIR/lib/glyph_install.sh"
INSTALL_GLYPH "$APP_DIR/resources/voiddesk.png" "voiddesk"

echo "$(date) === VOIDDESK launch (dir: $APP_DIR) ===" >>"$LOG"

export LD_LIBRARY_PATH="$APP_DIR/lib:${LD_LIBRARY_PATH:-}"
export VOIDDESK_APP_DIR="$APP_DIR"
export VOIDDESK_FULLSCREEN=1
export VOIDDESK_PLATFORM=muos
export VOIDDESK_MODEL=H700

# Helper: force engine back to LOVE in desk_config.json (self-heal on failure)
revert_engine_to_love() {
    python3 -c "
import json
p = '$DATA/desk_config.json'
try:
    d = json.load(open(p))
except Exception:
    d = {}
d['engine'] = 'love'
json.dump(d, open(p, 'w'), indent=1)
" >>"$LOG" 2>&1
}

# Runs whichever engine is currently configured, once, and sets $RC to
# its exit code. Re-reads the config each call so a toggle made while
# VoidDesk was running (or a session hand-off round-trip) picks up the
# latest choice instead of the one from process start.
run_engine() {
    ENGINE="$(python3 -c "
import json
try:
    print(json.load(open('$DATA/desk_config.json')).get('engine','love'))
except Exception:
    print('love')
" 2>/dev/null)"
    [ -z "$ENGINE" ] && ENGINE="love"
    echo "$(date) engine: $ENGINE" >>"$LOG"

    # Build one engine-neutral profile snapshot for both Pygame and LÖVE.
    # The resolver is read-only with respect to the source manifest/profile.
    if [ -f "$APP_DIR/tools/qwasar_profile_resolver.py" ]; then
        python3 "$APP_DIR/tools/qwasar_profile_resolver.py" \
            --root "$APP_DIR" \
            --platform muos --model H700 \
            --default-profile data/profiles/voiddesk-handheld-default.qprofile.json \
            --output "$DATA/qwasar_effective_profile.json" >>"$LOG" 2>&1
        PROFILE_RC=$?
        if [ "$PROFILE_RC" -ne 0 ]; then
            echo "$(date) QWASAR profile preflight failed (rc=$PROFILE_RC); continuing with legacy frontend defaults" >>"$LOG"
        fi
    fi

    # The py engine needs a bootstrapped pygame runtime (desk/../runtime).
    # If it was never built (or got wiped), build it now instead of
    # crashing; if that's not possible (offline, download failure, etc.)
    # fall back to LOVE so the device never gets stuck on a broken choice.
    if [ "$ENGINE" = "py" ]; then
        MARKER="$DATA/.pygame_ready"
        if [ ! -f "$MARKER" ] || [ ! -d "$APP_DIR/runtime" ]; then
            echo "$(date) pygame runtime not ready, bootstrapping..." >>"$LOG"
            python3 "$APP_DIR/bin/bootstrap_lite.py" >>"$LOG" 2>&1
            BOOT_RC=$?
            if [ $BOOT_RC -ne 0 ] || [ ! -f "$MARKER" ]; then
                echo "$(date) bootstrap FAILED (rc=$BOOT_RC) - falling back to LOVE engine" >>"$LOG"
                ENGINE="love"
                revert_engine_to_love
            fi
        fi
    fi

    if [ "$ENGINE" = "py" ]; then
        echo "$(date) launching Pygame frontend" >>"$LOG"
        PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
            PYGAME_HIDE_SUPPORT_PROMPT=1 \
            python3 "$APP_DIR/desk/main.py" >>"$LOG" 2>&1
        RC=$?
        if [ "$RC" -eq 16 ] && [ -f "$MUOS_APP" ]; then
            echo "$(date) Pygame requested a muOS application hand-off" >>"$LOG"
            return
        fi
        if [ $RC -ne 0 ]; then
            echo "$(date) Pygame frontend crashed (rc=$RC) - reverting engine to LOVE for next boot" >>"$LOG"
            revert_engine_to_love
            echo "$(date) launching LÖVE frontend as fallback" >>"$LOG"
            "$APP_DIR/lib/love" "$APP_DIR/love" >>"$LOG" 2>&1
            RC=$?
        fi
    else
        echo "$(date) launching LÖVE frontend" >>"$LOG"
        "$APP_DIR/lib/love" "$APP_DIR/love" >>"$LOG" 2>&1
        RC=$?
    fi
}

# Launch a scanned muOS application only from the two supported application
# roots. The .muos_app marker is shared with the Pygame frontend; it is data,
# never a command string. The child launcher runs only after LÖVE/Pygame has
# exited and released the framebuffer.
run_muos_app() {
    APP_SCRIPT="$1"
    # Pygame's existing marker stores the application directory; LÖVE uses
    # the same format. Accept an explicit launcher path too for compatibility.
    case "$APP_SCRIPT" in
        */mux_launch.sh) ;;
        *) APP_SCRIPT="${APP_SCRIPT%/}/mux_launch.sh" ;;
    esac
    APP_ROOT=""
    case "$APP_SCRIPT" in
        /mnt/mmc/MUOS/application/*/mux_launch.sh)
            APP_ROOT="/mnt/mmc/MUOS/application"
            ;;
        /mnt/sdcard/MUOS/application/*/mux_launch.sh)
            APP_ROOT="/mnt/sdcard/MUOS/application"
            ;;
        *)
            echo "$(date) rejected muOS app hand-off: unsupported root" >>"$LOG"
            return 1
            ;;
    esac

    APP_TARGET_DIR="${APP_SCRIPT%/mux_launch.sh}"
    APP_NAME="${APP_TARGET_DIR##*/}"
    case "$APP_NAME" in
        ""|"."|".."|*/*)
            echo "$(date) rejected muOS app hand-off: invalid app name" >>"$LOG"
            return 1
            ;;
    esac

    if [ -L "$APP_TARGET_DIR" ] || [ -L "$APP_SCRIPT" ] || \
       [ ! -d "$APP_TARGET_DIR" ] || [ ! -f "$APP_SCRIPT" ] || \
       [ ! -x "$APP_SCRIPT" ]; then
        echo "$(date) rejected muOS app hand-off: launcher missing or linked" >>"$LOG"
        return 1
    fi

    ROOT_REAL="$(CDPATH= cd -P "$APP_ROOT" 2>/dev/null && pwd -P)"
    APP_REAL="$(CDPATH= cd -P "$APP_TARGET_DIR" 2>/dev/null && pwd -P)"
    if [ -z "$ROOT_REAL" ] || [ -z "$APP_REAL" ] || \
       [ "$APP_REAL" != "$ROOT_REAL/$APP_NAME" ] || \
       [ "$APP_REAL" = "$APP_DIR" ]; then
        echo "$(date) rejected muOS app hand-off: path validation failed" >>"$LOG"
        return 1
    fi

    APP_NAME_LOWER="$(printf '%s' "$APP_NAME" | tr '[:upper:]' '[:lower:]')"
    case "$APP_NAME_LOWER" in
        voiddesk*)
            echo "$(date) rejected muOS app hand-off: cannot launch Void Desk recursively" >>"$LOG"
            return 1
            ;;
    esac

    APP_SCRIPT_REAL="$APP_REAL/mux_launch.sh"
    if [ -L "$APP_SCRIPT_REAL" ] || [ ! -f "$APP_SCRIPT_REAL" ] || \
       [ ! -x "$APP_SCRIPT_REAL" ]; then
        echo "$(date) rejected muOS app hand-off: invalid launcher file" >>"$LOG"
        return 1
    fi

    echo "$(date) launching muOS application: $APP_NAME" >>"$LOG"
    "$APP_SCRIPT_REAL" >>"$LOG" 2>&1
    APP_RC=$?
    echo "$(date) muOS application returned (rc=$APP_RC): $APP_NAME" >>"$LOG"
    return 0
}

PENDING="$DATA/.pending_session"
MUOS_APP="$DATA/.muos_app"
POWER_OFF="$DATA/.pending_poweroff"
rm -f "$PENDING" "$MUOS_APP" "$POWER_OFF"
POWER_OFF_REQUESTED=0

# Start Python service
python3 "$APP_DIR/service/voiddesk_service.py" >>"$LOG" 2>&1 &
SERVICE_PID=$!

# Main loop: run the engine; if it quit because a session hand-off was
# requested (service/voiddesk_service.py h_session_launch dropped
# $PENDING right before telling LÖVE to love.event.quit()), run that
# session full-screen now that LÖVE has actually released the display,
# then loop back and relaunch the engine. A normal exit (back/quit from
# the UI, no pending session) breaks out and ends the script as before.
while true; do
    run_engine

    if [ -f "$POWER_OFF" ]; then
        rm -f "$POWER_OFF"
        POWER_OFF_REQUESTED=1
        echo "$(date) power-off requested by frontend" >>"$LOG"
        break
    fi

    if [ -f "$MUOS_APP" ]; then
        MUOS_APP_SCRIPT=""
        IFS= read -r MUOS_APP_SCRIPT < "$MUOS_APP"
        rm -f "$MUOS_APP"
        run_muos_app "$MUOS_APP_SCRIPT"
        # Return to Void Desk after the selected muOS app exits, even when
        # the child launcher reports an error.
        continue
    fi

    if [ -f "$PENDING" ]; then
        SESSION="$(cat "$PENDING" 2>/dev/null)"
        rm -f "$PENDING"
        echo "$(date) session hand-off requested: $SESSION" >>"$LOG"
        case "$SESSION" in
            xfce|icewm|lxde)
                # one shared launcher for all three — it reads "desk_env"
                # from desk_config.json (already set by h_session_launch
                # before it dropped this marker) and starts the right one
                if [ -x "$APP_DIR/bin/xfce_launch.sh" ]; then
                    "$APP_DIR/bin/xfce_launch.sh" >>"$LOG" 2>&1
                    echo "$(date) $SESSION session ended (rc=$?), returning to VoidDesk" >>"$LOG"
                else
                    echo "$(date) bin/xfce_launch.sh missing or not executable, skipping hand-off" >>"$LOG"
                fi
                continue
                ;;
            voidcast)
                # standalone pygame app, same runtime the "py" engine
                # already uses (built on demand above) — not a chroot
                # desktop session, so it runs directly, no xfce_launch.sh
                echo "$(date) launching VoidCast" >>"$LOG"
                PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
                    PYGAME_HIDE_SUPPORT_PROMPT=1 \
                    python3 "$APP_DIR/outdesk/VoidCast/voidcast/main.py" >>"$LOG" 2>&1
                echo "$(date) VoidCast ended (rc=$?), returning to VoidDesk" >>"$LOG"
                continue
                ;;
            *)
                echo "$(date) unknown pending session '$SESSION', ignoring" >>"$LOG"
                continue
                ;;
        esac
    fi

    break
done

# Stop the companion service before device shutdown.
kill "$SERVICE_PID" 2>/dev/null
wait "$SERVICE_PID" 2>/dev/null

if [ "$POWER_OFF_REQUESTED" -eq 1 ]; then
    echo "$(date) syncing storage before forced power-off" >>"$LOG"
    sync

    if command -v poweroff >/dev/null 2>&1; then
        poweroff -f >>"$LOG" 2>&1
        echo "$(date) poweroff returned; trying poweroff reboot fallback" >>"$LOG"
    fi
    if command -v reboot >/dev/null 2>&1; then
        reboot -p -f >>"$LOG" 2>&1
        echo "$(date) reboot -p -f returned; trying halt fallback" >>"$LOG"
    fi
    if command -v halt >/dev/null 2>&1; then
        halt -f -p >>"$LOG" 2>&1
    fi

    echo "$(date) ERROR: every power-off command returned" >>"$LOG"
    exit 1
fi

echo "$(date) exit rc=$RC" >>"$LOG"
exit $RC
