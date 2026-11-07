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

# Start Python service
python3 "$APP_DIR/service/voiddesk_service.py" >>"$LOG" 2>&1 &
SERVICE_PID=$!

if [ "$ENGINE" = "py" ]; then
    echo "$(date) launching Pygame frontend" >>"$LOG"
    PYTHONPATH="$APP_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
        PYGAME_HIDE_SUPPORT_PROMPT=1 \
        python3 "$APP_DIR/desk/main.py" >>"$LOG" 2>&1
    RC=$?
else
    echo "$(date) launching LÖVE frontend" >>"$LOG"
    "$APP_DIR/lib/love" "$APP_DIR/love" >>"$LOG" 2>&1
    RC=$?
fi

kill "$SERVICE_PID" 2>/dev/null
echo "$(date) exit rc=$RC" >>"$LOG"
exit $RC
