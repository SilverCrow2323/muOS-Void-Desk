#!/bin/sh

# HELP: Disc Crusher - Converti immagini CD in CHD / Convert CD images to CHD
# ICON: disc_crusher
# GRID: Disc Crusher

. /opt/muos/script/var/func.sh

# Application Setup
# Disc Crusher è un'app Python, non necessita di SETUP_APP
# ma possiamo comunque chiamarla per inizializzare variabili muOS
SETUP_APP "python3" ""

# Kill background music if playing
if pgrep -f "playbgm.sh" >/dev/null; then
    killall -q "playbgm.sh" "mpg123"
fi

# Define paths
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
VOIDDESK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Hall sensor override for clamshell devices (e.g. RG35XX SP).
# Bind-mounting a constant value keeps lid-close from triggering sleep
# while Disc Crusher is running. We unmount on exit.
HALL_OVERRIDE_FILE="/tmp/disc_crusher_hallkey_override"
HALL_TARGETS="/sys/class/power_supply/axp2202-battery/hallkey /sys/devices/platform/hall-mh248/hallvalue"

setup_hall_override() {
    echo "1" > "$HALL_OVERRIDE_FILE"

    for TARGET in $HALL_TARGETS; do
        [ -e "$TARGET" ] || continue

        if findmnt -n "$TARGET" >/dev/null 2>&1; then
            echo "Hall target already mounted, skipping: $TARGET"
            continue
        fi

        if mount --bind "$HALL_OVERRIDE_FILE" "$TARGET" 2>/dev/null; then
            echo "Mounted hall override on: $TARGET"
        else
            echo "Failed to mount hall override on: $TARGET"
        fi
    done
}

cleanup() {
    # Termina eventuali processi residui
    kill -9 "$(pidof gptokeyb2)" 2>/dev/null

    for TARGET in $HALL_TARGETS; do
        [ -e "$TARGET" ] || continue

        while findmnt -n "$TARGET" >/dev/null 2>&1; do
            if umount -l "$TARGET" 2>/dev/null; then
                echo "Unmounted hall override: $TARGET"
            else
                echo "Failed to unmount hall override: $TARGET"
                break
            fi
        done
    done

    rm -f "$HALL_OVERRIDE_FILE"
}

# Redirections for debugging
LOG_DIR="$VOIDDESK_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/disc_crusher_launcher.log"
echo "Starting Disc Crusher Script" > "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

trap cleanup EXIT INT TERM

setup_hall_override

# Exports
export WIDTH=$(GET_VAR device mux/width)
export HEIGHT=$(GET_VAR device mux/height)
export SDL_GAMECONTROLLERCONFIG_FILE="/usr/lib/gamecontrollerdb.txt"
export LD_LIBRARY_PATH="$VOIDDESK_DIR/runtime:/mnt/mmc/MUOS/PortMaster:$LD_LIBRARY_PATH"
export PYTHONPATH="$VOIDDESK_DIR/runtime:$PYTHONPATH"

# Avvia outdeskintro con il logo e il comando per Disc Crusher
INTRO_SCRIPT="$VOIDDESK_DIR/outdesk/outdeskintro.py"
DC_SCRIPT="$VOIDDESK_DIR/outdesk/Disc_Crusher/disc_crusher.py"
LOGO_PATH="$VOIDDESK_DIR/assets/logos/disc_crusher.png"

if [ -f "$INTRO_SCRIPT" ] && [ -f "$DC_SCRIPT" ]; then
    echo "Lanciando outdeskintro..."
    python3 "$INTRO_SCRIPT" \
        --logo "$LOGO_PATH" \
        --name "Disc Crusher" \
        --cmd "python3 $DC_SCRIPT"
else
    echo "Script o logo mancante. Verifica i percorsi."
    exit 1
fi

# Cleanup eseguito dal trap