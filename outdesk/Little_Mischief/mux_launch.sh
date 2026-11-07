#!/bin/sh
# HELP: Little Mischief
# ICON: little_mischief
# GRID: Little Mischief
. /opt/muos/script/var/func.sh
SETUP_APP "python3" ""
if pgrep -f "playbgm.sh" >/dev/null; then killall -q "playbgm.sh" "mpg123"; fi
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$VOIDDESK_DIR/data/logs"; mkdir -p "$LOG_DIR"
echo "Starting Little Mischief" > "$LOG_DIR/little_mischief_launcher.log"
exec >> "$LOG_DIR/little_mischief_launcher.log" 2>&1
export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"
cd "$SCRIPT_DIR"
INTRO="$VOIDDESK_DIR/outdesk/outdeskintro.py"
MAIN="$SCRIPT_DIR/wifi_penetration.py"
LOGO="$VOIDDESK_DIR/assets/logos/little_mischief.png"
if [ -f "$INTRO" ] && [ -f "$MAIN" ]; then
    python3 "$INTRO" --logo "$LOGO" --name "Little Mischief" --cmd "python3 $MAIN"
else
    python3 "$MAIN"
fi
