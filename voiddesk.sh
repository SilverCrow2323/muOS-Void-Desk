#!/usr/bin/env bash
# VoidDesk unified launcher
#   voiddesk.sh              → TUI menu
#   voiddesk.sh --love       → launch LÖVE directly
#   voiddesk.sh --py         → launch Pygame directly
#   voiddesk.sh --engine X   → launch specific engine
#   voiddesk.sh --desktop    → TUI (compat with old run_desktop.sh)
set +e
cd "$(dirname "$0")" || exit 1

case "${1:-}" in
    --love)
        python3 -c "
import sys; sys.path.insert(0, '.')
from voiddesk_tui import action_launch
sys.exit(action_launch('love'))
"
        ;;
    --py)
        python3 -c "
import sys; sys.path.insert(0, '.')
from voiddesk_tui import action_launch
sys.exit(action_launch('py'))
"
        ;;
    --engine)
        ENGINE="${2:-love}"
        python3 -c "
import sys; sys.path.insert(0, '.')
from voiddesk_tui import action_launch
sys.exit(action_launch('$ENGINE'))
"
        ;;
    --desktop)
        exec python3 voiddesk_tui.py
        ;;
    --help|-h)
        cat << 'HELP'
VoidDesk launcher
  voiddesk.sh              TUI menu
  voiddesk.sh --love       Launch LÖVE engine
  voiddesk.sh --py         Launch Pygame engine
  voiddesk.sh --engine X   Launch engine X (py|love)
  voiddesk.sh --desktop    TUI menu (default)
  voiddesk.sh --help       This help
HELP
        ;;
    *)
        exec python3 voiddesk_tui.py
        ;;
esac
