#!/bin/sh
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

PENDING="$DATA/.pending_session"
rm -f "$PENDING"

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

    if [ -f "$PENDING" ]; then
        SESSION="$(cat "$PENDING" 2>/dev/null)"
        rm -f "$PENDING"
        echo "$(date) session hand-off requested: $SESSION" >>"$LOG"
        case "$SESSION" in
            xfce)
                if [ -x "$APP_DIR/bin/xfce_launch.sh" ]; then
                    "$APP_DIR/bin/xfce_launch.sh" >>"$LOG" 2>&1
                    echo "$(date) xfce session ended (rc=$?), returning to VoidDesk" >>"$LOG"
                else
                    echo "$(date) bin/xfce_launch.sh missing or not executable, skipping hand-off" >>"$LOG"
                fi
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

kill "$SERVICE_PID" 2>/dev/null
echo "$(date) exit rc=$RC" >>"$LOG"
exit $RC
