#!/bin/sh
# HELP: Media Player - Player audio/video standalone per Media Vault
# ICON: void_radio
# GRID: Media Player

. /opt/muos/script/var/func.sh

SETUP_APP "python3" ""

if pgrep -f "playbgm.sh" >/dev/null; then
    killall -q "playbgm.sh" "mpg123"
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOG_DIR="$VOIDDESK_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/media_player_launcher.log"
echo "Starting Media Player" > "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"

INTRO_SCRIPT="$VOIDDESK_DIR/outdesk/outdeskintro.py"
MP_SCRIPT="$SCRIPT_DIR/media_player.py"
LOGO_PATH="$VOIDDESK_DIR/assets/logos/media_vault.png"

if [ -f "$INTRO_SCRIPT" ] && [ -f "$MP_SCRIPT" ]; then
    python3 "$INTRO_SCRIPT" \
        --logo "$LOGO_PATH" \
        --name "Media Player" \
        --cmd "python3 $MP_SCRIPT"
else
    echo "Script o logo mancante. Verifica i percorsi."
    exit 1
fi
