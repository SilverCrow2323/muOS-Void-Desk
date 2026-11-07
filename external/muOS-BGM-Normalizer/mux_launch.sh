#!/bin/sh
# HELP: BGM Normalizer - LUFS normalizer, OGG conversion, track cleanup
# ICON: music
# GRID: BGM Normalizer

. /opt/muos/script/var/func.sh
SETUP_APP "python3" ""

if pgrep -f "playbgm.sh" >/dev/null; then
    killall -q "playbgm.sh" "mpg123"
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOG_DIR="$VOIDDESK_DIR/data/logs"
mkdir -p "$LOG_DIR"
echo "Starting BGM Normalizer" > "$LOG_DIR/bgm_normalizer.log"
exec >> "$LOG_DIR/bgm_normalizer.log" 2>&1

export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"

cd "$SCRIPT_DIR"
exec python3 "$SCRIPT_DIR/bgm_normalizer.py"
