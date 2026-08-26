#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // vd_loader — indicatore di caricamento su /dev/fb0.
#
#  Copre i tempi morti tra il menu e gli script esterni (avvio XFCE, ritorno
#  al menu): niente piu' schermate incantate. Zero dipendenze, zero pygame:
#  parte in una frazione di secondo e disegna direttamente sul framebuffer.
#
#  Protocollo: chi lavora scrive su un file di progresso righe "PCT|TESTO"
#  (l'ultima vince). PCT vuoto = indeterminato (la barra fa la spola).
#  Il loader muore quando: compare uno dei file di stop (es. X ha preso lo
#  schermo, o il menu e' tornato su), il progresso arriva a 100, scade il
#  timeout, o riceve SIGTERM.
#
#  uso: vd_loader.py --title T [--label L] [--progress FILE]
#                    [--feature F] [--items FILE]
#                    [--stop FILE ...] [--timeout SEC]
# ============================================================================
import json
import math
import os
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP, "lib"))
import fbtext  # noqa: E402

BG = (7, 8, 11)
INK = (2, 2, 4)
LINE = (34, 38, 47)
FG = (233, 233, 226)
DIM = (148, 150, 152)
FAINT = (100, 103, 110)
ACCENTS = {"ambra": (255, 176, 46), "cremisi": (231, 54, 84),
           "ciano": (74, 206, 224), "verde": (112, 224, 122),
           "acciaio": (208, 214, 210)}


def theme_accent():
    try:
        cfg = json.load(open(os.path.join(APP, "data", "desk_config.json")))
        return ACCENTS.get(cfg.get("theme", "ambra"), ACCENTS["ambra"])
    except Exception:
        return ACCENTS["ambra"]


class Painter(object):
    """Primitive veloci sopra fbtext.FB: riempimenti a colpi di slice,
    non pixel per pixel (a 640x480 in puro python fa la differenza)."""

    def __init__(self, fb):
        self.fb = fb

    def _pix(self, rgb):
        r, g, b = rgb
        if self.fb.bpp == 16:
            v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            return bytes((v & 0xFF, (v >> 8) & 0xFF))
        return bytes((b, g, r, 0))

    def fill(self, x, y, w, h, rgb):
        fb = self.fb
        x = max(0, min(fb.w, x))
        y = max(0, min(fb.h, y))
        w = max(0, min(fb.w - x, w))
        h = max(0, min(fb.h - y, h))
        if not w or not h:
            return
        row = self._pix(rgb) * w
        px = self._pix(rgb)
        n = len(px)
        for yy in range(y, y + h):
            o = yy * fb.stride + x * n
            fb.buf[o:o + len(row)] = row

    def frame(self, x, y, w, h, rgb, th=1, cut=0):
        self.fill(x, y, w - cut, th, rgb)
        self.fill(x, y + h - th, w, th, rgb)
        self.fill(x, y, th, h, rgb)
        self.fill(x + w - th, y + cut, th, h - cut, rgb)
        if cut:
            for i in range(cut):
                self.fill(x + w - cut + i, y + i, th + 1, th, rgb)

    def big_text(self, x, y, s, rgb, scale=2):
        fb = self.fb
        for i, ch in enumerate(s):
            c = ord(ch)
            if c < 32 or c > 126:
                c = ord("?")
            base = (c - 32) * fbtext.CH * 2
            gx = x + i * fbtext.CW * scale
            for dy in range(fbtext.CH):
                bits = fb.font[base + dy * 2] | (fb.font[base + dy * 2 + 1]
                                                 << 8)
                for dx in range(fbtext.CW):
                    if bits & (1 << dx):
                        self.fill(gx + dx * scale, y + dy * scale,
                                  scale, scale, rgb)


def draw_atom(pt, cx, cy, t, acc, fg):
    core_r = 5 + int(2 * abs(math.sin(t * 2.5)))
    pt.fill(cx - core_r, cy - core_r, core_r * 2, core_r * 2, acc)
    for r, spd, dr in ((22, 1.8, 4), (32, 1.2, 3)):
        ang = t * spd
        dx = int(r * math.cos(ang))
        dy = int(r * math.sin(ang))
        pt.fill(cx + dx - dr, cy + dy - dr, dr * 2, dr * 2, fg)


def parse_args(argv):
    a = {"title": "VOID", "label": "", "progress": "", "feature": "",
         "items": "", "stop": [], "timeout": 600.0}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--title" and i + 1 < len(argv):
            a["title"] = argv[i + 1]; i += 2
        elif k == "--label" and i + 1 < len(argv):
            a["label"] = argv[i + 1]; i += 2
        elif k == "--progress" and i + 1 < len(argv):
            a["progress"] = argv[i + 1]; i += 2
        elif k == "--feature" and i + 1 < len(argv):
            a["feature"] = argv[i + 1]; i += 2
        elif k == "--items" and i + 1 < len(argv):
            a["items"] = argv[i + 1]; i += 2
        elif k == "--stop" and i + 1 < len(argv):
            a["stop"].append(argv[i + 1]); i += 2
        elif k == "--timeout" and i + 1 < len(argv):
            try:
                a["timeout"] = float(argv[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1
    return a


def stop_hit(paths, t0):
    for s in paths:
        try:
            if os.path.getmtime(s) > t0 - 2.0:
                return True
        except OSError:
            pass
    return False


def read_progress(path, prev):
    if not path:
        return prev
    try:
        with open(path) as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
        if not lines:
            return prev
        raw = lines[-1]
        pct, _, label = raw.partition("|")
        try:
            p = max(0, min(100, int(float(pct))))
        except ValueError:
            p = None
        return (p, label or prev[1])
    except OSError:
        return prev


def read_items(path):
    if not path:
        return []
    try:
        with open(path) as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []


def open_fb():
    kw = {}
    dev = os.environ.get("VD_FB_DEV", "/dev/fb0")
    geom = os.environ.get("VD_FB_GEOM", "")
    if geom:
        try:
            w_, h_, b_, s_ = [int(v) for v in geom.split("x")]
            kw = dict(width=w_, height=h_, bpp=b_, stride=s_)
        except ValueError:
            pass
    return fbtext.FB(dev=dev, **kw)


def main():
    a = parse_args(sys.argv[1:])
    fb = open_fb()
    if not fb.ok:
        t0 = time.time()
        while time.time() - t0 < a["timeout"]:
            if stop_hit(a["stop"], t0):
                return 0
            time.sleep(0.25)
        return 0
    pt = Painter(fb)
    acc = theme_accent()
    pct, label = None, a["label"]
    feature = a.get("feature", "")
    items = read_items(a.get("items", ""))
    t0 = time.time()
    frame = 0

    PW, PH = 560, 240
    PX, PY = (fb.w - PW) // 2, (fb.h - PH) // 2
    INFO_X = PX + 16
    INFO_W = PW - 32
    ANIM_CX = PX + 70
    ANIM_CY = PY + PH // 2
    BARX = INFO_X
    BARY = PY + 70
    BARW = INFO_W
    BARH = 32
    SEGS = 24
    SEGW = BARW // SEGS

    while True:
        now = time.time()
        if stop_hit(a["stop"], t0):
            return 0
        if now - t0 > a["timeout"]:
            return 0
        pct, label = read_progress(a["progress"], (pct, label))

        fb.clear(BG)
        for gx in range(0, fb.w + 40, 64):
            for step in range(0, fb.h, 8):
                pt.fill(gx - (step * 28) // fb.h, step, 1, 8, LINE)
        for gy in (118, 430):
            pt.fill(0, gy, fb.w, 1, LINE)
            pt.fill(0, gy + 2, fb.w, 1, INK)
        for hy in range(60, fb.h - 40, 26):
            pt.fill(fb.w - 4, hy, 3, 7, acc)

        pt.fill(PX, PY, PW, PH, INK)
        pt.frame(PX, PY, PW, PH, acc, 2, cut=14)
        pt.fill(PX, PY + PH + 3, PW, 2, LINE)

        draw_atom(pt, ANIM_CX, ANIM_CY, now, acc, FG)

        fb.text((INFO_X + 70) // fbtext.CW, (PY + 18) // fbtext.CH,
                a["title"][:38], acc)
        if feature:
            fb.text((INFO_X + 70) // fbtext.CW, (PY + 36) // fbtext.CH,
                    feature[:44], DIM)

        pt.frame(BARX - 2, BARY - 2, BARW + 4, BARH + 4, LINE, 1)
        if pct is None:
            pos = frame % (SEGS * 2)
            head = pos if pos < SEGS else SEGS * 2 - pos
            for s in range(SEGS):
                on = abs(s - head) < 3
                pt.fill(BARX + s * SEGW + 1, BARY, SEGW - 2, BARH,
                        acc if on else (14, 15, 19))
        else:
            fill_n = pct * SEGS // 100
            for s in range(SEGS):
                pt.fill(BARX + s * SEGW + 1, BARY, SEGW - 2, BARH,
                        acc if s < fill_n else (14, 15, 19))
            ptxt = "%d%%" % pct
            pw_px = len(ptxt) * fbtext.CW * 2
            pt.big_text(BARX + BARW - pw_px, BARY + 8, ptxt, FG, 2)

        pw_px = (len("%d%%" % pct) * fbtext.CW * 2) if pct is not None else 0
        cx = BARX + BARW - pw_px - 34
        cy = BARY + 10
        cells = ((-1, -1), (0, -1), (1, -1), (1, 0),
                 (1, 1), (0, 1), (-1, 1), (-1, 0))
        ph = frame % 8
        for i, (dx, dy) in enumerate(cells):
            d = (i - ph) % 8
            col = acc if d < 2 else (DIM if d == 2 else LINE)
            pt.fill(cx + dx * 11 - 4, cy + dy * 11 - 4, 8, 8, col)

        if label:
            fb.text((INFO_X + 70) // fbtext.CW, (BARY + BARH + 10) // fbtext.CH,
                    label[:42], DIM)

        ty = BARY + BARH + 28
        for item in items[:5]:
            if ty + 16 > PY + PH - 8:
                break
            fb.text((INFO_X + 70) // fbtext.CW, ty // fbtext.CH, "•", acc)
            fb.text((INFO_X + 82) // fbtext.CW, ty // fbtext.CH, item[:38], FAINT)
            ty += 18

        fb.text((INFO_X + 70) // fbtext.CW, (PY + PH + 8) // fbtext.CH,
                "SPDW FACTORY // vd_loader", FAINT)

        fb.flush()
        if pct is not None and pct >= 100:
            time.sleep(0.35)
            return 0
        frame += 1
        time.sleep(0.09)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
