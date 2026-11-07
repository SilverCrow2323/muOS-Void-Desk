#!/bin/sh

# HELP: Portable Forger - Gestore dipendenze standalone per muOS
# ICON: portable_forger
# GRID: Portable Forger

. /opt/muos/script/var/func.sh

# Application Setup
SETUP_APP "python3" ""

# Kill background music if playing
if pgrep -f "playbgm.sh" >/dev/null; then
    killall -q "playbgm.sh" "mpg123"
fi

# Define paths
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Redirections for debugging
LOG_DIR="$VOIDDESK_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/portable_forger_launcher.log"
echo "Starting Portable Forger Script" > "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

# Exports
export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"

# Avvia outdeskintro con il logo e il comando per Portable Forger
INTRO_SCRIPT="$VOIDDESK_DIR/outdesk/outdeskintro.py"
PF_SCRIPT="$SCRIPT_DIR/portable_forger.py"
LOGO_PATH="$VOIDDESK_DIR/assets/logos/portable_forger.png"

if [ -f "$INTRO_SCRIPT" ] && [ -f "$PF_SCRIPT" ]; then
    echo "Lanciando outdeskintro..."
    python3 "$INTRO_SCRIPT" \
        --logo "$LOGO_PATH" \
        --name "Portable Forger" \
        --cmd "python3 $PF_SCRIPT"
else
    echo "Script o logo mancante. Verifica i percorsi."
    exit 1
fi
