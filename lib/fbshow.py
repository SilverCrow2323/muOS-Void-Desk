# -*- coding: utf-8 -*-
"""fbshow.py FILE  - mostra un report a pagine sul framebuffer"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbtext

try:
    rep = open(sys.argv[1], errors="replace").read().splitlines()
except Exception:
    rep = ["report non trovato"]
scr = fbtext.Screen(title="VOIDDIAG - report")
per = (scr.fb.rows - 3) if scr.fb.ok else 20
pages = [rep[i:i + per] for i in range(0, len(rep), per)][:8]
for n, pg in enumerate(pages):
    scr.title = "VOIDDIAG - report (pag. %d/%d)" % (n + 1, len(pages))
    scr.lines = pg
    scr.render()
    time.sleep(6)
scr.title = "VOIDDIAG - fine"
scr.lines = ["", "Report completo salvato in:",
             "  /mnt/mmc/ARCHIVE/voiddiag_report.txt", "",
             "Collega la SD al PC e invialo per la diagnosi."]
scr.render()
time.sleep(8)
