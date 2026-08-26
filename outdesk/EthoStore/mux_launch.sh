#!/bin/sh
# HELP: EthoStore -- muOS App Store by SPDW Factory
# ICON: ethostore
# GRID: EthoStore

. /opt/muos/script/var/func.sh

APP_BIN="ethostore"
SETUP_APP "$APP_BIN" ""

SETUP_STAGE_OVERLAY

APP_DIR="/run/muos/storage/application/EthoStore"
LOG_DIR="${APP_DIR}/logs"
LOG_FILE="${LOG_DIR}/mux-launch.log"

mkdir -p "$LOG_DIR"

printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "mux_launch start" >>"$LOG_FILE"

if [ ! -f "${APP_DIR}/ethostore.py" ]; then
    printf '%s\n' "ethostore.py missing" >>"$LOG_FILE"
    exit 1
fi

printf '%s\n' "calling FRONTEND stop" >>"$LOG_FILE"
FRONTEND stop

cd "$APP_DIR"
exec /usr/bin/python3 "${APP_DIR}/ethostore.py"
