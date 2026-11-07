#!/bin/sh
# HELP: VoidDesk - Void suite control panel (LOVE + Python)
# ICON: voiddesk
# GRID: voiddesk

. /opt/muos/script/var/func.sh
APP_BIN="love"
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
export VOIDDESK_FULLSCREEN=1          # device = fullscreen

python3 "$APP_DIR/service/voiddesk_service.py" >>"$LOG" 2>&1 &
SERVICE_PID=$!

"$APP_DIR/lib/love" "$APP_DIR/love" >>"$LOG" 2>&1
RC=$?

kill "$SERVICE_PID" 2>/dev/null
echo "$(date) LÖVE exit rc=$RC" >>"$LOG"
exit $RC
