#!/bin/sh
# HELP: Image Viewer - Visualizzatore immagini standalone per Media Vault
# ICON: media_lib
# GRID: Image Viewer

. /opt/muos/script/var/func.sh

SETUP_APP "python3" ""

if pgrep -f "playbgm.sh" >/dev/null; then
    killall -q "playbgm.sh" "mpg123"
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOG_DIR="$VOIDDESK_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/image_viewer_launcher.log"
echo "Starting Image Viewer" > "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"

INTRO_SCRIPT="$VOIDDESK_DIR/outdesk/outdeskintro.py"
IV_SCRIPT="$SCRIPT_DIR/image_viewer.py"
LOGO_PATH="$VOIDDESK_DIR/assets/logos/media_lib.png"

if [ -f "$INTRO_SCRIPT" ] && [ -f "$IV_SCRIPT" ]; then
    python3 "$INTRO_SCRIPT" \
        --logo "$LOGO_PATH" \
        --name "Image Viewer" \
        --cmd "python3 $IV_SCRIPT"
else
    echo "Script o logo mancante. Verifica i percorsi."
    exit 1
fi
