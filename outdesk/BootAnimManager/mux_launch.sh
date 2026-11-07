#!/bin/sh
# HELP: Boot Anim Manager
# ICON: bootanim
# GRID: Boot Anim Manager
. /opt/muos/script/var/func.sh
SETUP_APP "python3" ""
if pgrep -f "playbgm.sh" >/dev/null; then killall -q "playbgm.sh" "mpg123"; fi
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$VOIDDESK_DIR/data/logs"; mkdir -p "$LOG_DIR"
echo "Starting Boot Anim Manager" > "$LOG_DIR/bootanim_launcher.log"
exec >> "$LOG_DIR/bootanim_launcher.log" 2>&1
export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"
cd "$SCRIPT_DIR"
INTRO="$VOIDDESK_DIR/outdesk/outdeskintro.py"
MAIN="$SCRIPT_DIR/bootanim_manager.py"
LOGO="$VOIDDESK_DIR/assets/logos/bootanim.png"
if [ -f "$INTRO" ] && [ -f "$MAIN" ]; then
    python3 "$INTRO" --logo "$LOGO" --name "Boot Anim Manager" --cmd "python3 $MAIN"
else
    python3 "$MAIN"
fi
