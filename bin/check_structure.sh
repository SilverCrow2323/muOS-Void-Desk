#!/bin/sh
# Controlla la struttura delle cartelle di VoidDesk
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "Root: $APP_DIR"
echo "--- File obbligatori ---"
for f in mux_launch.sh bin/bootstrap_lite.py desk/main.py data/desk_config.json; do
    if [ -e "$APP_DIR/$f" ]; then
        echo "  [OK] $f"
    else
        echo "  [MANCANTE] $f"
    fi
done
echo "--- Cartelle ---"
for d in runtime lib assets data bin desk outdesk sgrub glyph; do
    if [ -d "$APP_DIR/$d" ]; then
        echo "  [OK] $d/"
    else
        echo "  [MANCANTE] $d/"
    fi
done
echo "--- Permessi ---"
if [ -x "$APP_DIR/mux_launch.sh" ]; then
    echo "  [OK] mux_launch.sh eseguibile"
else
    echo "  [ERRORE] mux_launch.sh NON eseguibile (chmod +x mux_launch.sh)"
fi
echo "--- Runtime pygame ---"
if [ -f "$APP_DIR/data/.pygame_ready" ]; then
    echo "  [OK] .pygame_ready presente"
else
    echo "  [NOTE] .pygame_ready assente (verra' creato al primo avvio)"
fi
if [ -d "$APP_DIR/runtime" ]; then
    echo "  [OK] runtime/ presente"
else
    echo "  [NOTE] runtime/ assente (verra' creato al bootstrap)"
fi
