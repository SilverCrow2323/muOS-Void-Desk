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

# Read engine preference
ENGINE="$(python3 -c "
import json
try:
    print(json.load(open('$DATA/desk_config.json')).get('engine','love'))
except Exception:
    print('love')
" 2>/dev/null)"
[ -z "$ENGINE" ] && ENGINE="love"
echo "$(date) engine: $ENGINE" >>"$LOG"

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

# The py engine needs a bootstrapped pygame runtime (desk/../runtime).
# If it was never built (or got wiped), build it now instead of crashing;
# if that's not possible (offline, download failure, etc.) fall back to
# LOVE so the device never gets stuck on a broken engine choice.
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

# Start Python service
python3 "$APP_DIR/service/voiddesk_service.py" >>"$LOG" 2>&1 &
SERVICE_PID=$!

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

kill "$SERVICE_PID" 2>/dev/null
echo "$(date) exit rc=$RC" >>"$LOG"
exit $RC
