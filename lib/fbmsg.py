# -*- coding: utf-8 -*-
"""fbmsg.py TITOLO [SECONDI] [riga...]  (altre righe da stdin)"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbtext

title = sys.argv[1] if len(sys.argv) > 1 else ""
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 8
lines = []
try:
    if not sys.stdin.isatty():
        lines = [ln.rstrip("\n") for ln in sys.stdin.read().splitlines()]
except Exception:
    pass
lines += list(sys.argv[3:])
scr = fbtext.Screen(title=title)
scr.lines = lines
scr.render()
time.sleep(secs)
