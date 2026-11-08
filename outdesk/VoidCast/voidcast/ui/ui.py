# outdesk/VoidCast/voidcast/ui/ui.py
# -*- coding: utf-8 -*-
# VOIDCAST // ui.ui — cyberpunk neon HUD theme, 640x480.
import os
import time
import math
import pygame

from core import i18n
from . import icons as icons_mod
from .anim import Anim

W, H = 640, 480

ACCENTS = {
    "crimson": (220, 40, 70),
    "cyan":    (60, 220, 230),
    "amber":   (255, 176, 32),
}

BG      = (8, 8, 14)
BG_PANEL = (16, 16, 26)
BG_SEL  = (34, 20, 30)
FG      = (215, 215, 222)
FG_DIM  = (120, 120, 135)
FG_FAINT = (55, 55, 70)
OK  = (90, 200, 120)
ERR = (230, 80, 80)

_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "DejaVuSans.ttf")

def _font(size):
    try:
        return pygame.font.Font(_FONT_PATH, size)
    except Exception:
        return pygame.font.Font(None, size)


# ---------------------------------------------------------------------
#  Theme — colors, fonts, helpers, cyberpunk decoration
# ---------------------------------------------------------------------
class Theme(object):
    def __init__(self, accent_name="crimson"):
        self.accent = ACCENTS.get(accent_name, ACCENTS["crimson"])
        pygame.font.init()
        self.f_big   = _font(28)
        self.f_med   = _font(20)
        self.f_small = _font(16)
        self.f_tiny  = _font(13)
        self.f_tiny_it = _font(13)
        try: self.f_tiny_it.set_italic(True)
        except Exception: pass
        self.f_huge  = _font(40)
        self.fx_scanlines = False

    # ---------------- primitives ----------------
    def text(self, surf, txt, pos, font=None, color=FG, maxw=None):
        font = font or self.f_med
        txt = "" if txt is None else str(txt)
        if maxw:
            while font.size(txt)[0] > maxw and len(txt) > 3:
                txt = txt[:-4] + "..."
        surf.blit(font.render(txt, True, color), pos)

    def glow_text(self, surf, txt, pos, font, color, glow=None, radius=2):
        if not Anim.enabled() or radius <= 0:
            surf.blit(font.render(txt, True, color), pos)
            return
        glow = glow or color
        for r, a in ((radius * 2, 40), (radius, 90)):
            s = font.render(txt, True, glow)
            s.set_alpha(a)
            for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                surf.blit(s, (pos[0] + dx, pos[1] + dy))
        surf.blit(font.render(txt, True, color), pos)

    def corner_brackets(self, surf, rect, color, size=8, thick=2):
        x, y, w, h = rect
        for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1),
                                (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
            pygame.draw.line(surf, color, (cx, cy), (cx + dx * size, cy), thick)
            pygame.draw.line(surf, color, (cx, cy), (cx, cy + dy * size), thick)

    def scanline_overlay(self, surf, alpha=36):
        if not Anim.enabled():
            return
        line = pygame.Surface((W, 1), pygame.SRCALPHA)
        line.fill((0, 0, 0, alpha))
        for y in range(0, H, 3):
            surf.blit(line, (0, y))

    def cyber_backdrop(self, surf, t=None):
        """Animated dark grid used when bg playback is active."""
        t = t or time.time()
        surf.fill(BG)
        pulse = int(25 + 15 * math.sin(t * 1.3))
        g = pygame.Surface((W, H), pygame.SRCALPHA)
        for x in range(0, W + 40, 40):
            pygame.draw.line(g, (self.accent[0] // 3, self.accent[1] // 3,
                                  self.accent[2] // 3, pulse), (x, 0), (x, H), 1)
        for y in range(0, H + 40, 40):
            pygame.draw.line(g, (self.accent[0] // 3, self.accent[1] // 3,
                                  self.accent[2] // 3, pulse), (0, y), (W, y), 1)
        surf.blit(g, (0, 0))
        # moving bright scanline
        if Anim.enabled():
            sy = int(Anim.scan(H, 120))
            if 0 <= sy < H:
                ls = pygame.Surface((W, 2), pygame.SRCALPHA)
                ls.fill((self.accent[0], self.accent[1], self.accent[2],
                         int(90 * Anim.pulse(1.8, 0.3, 1.0))))
                surf.blit(ls, (0, sy))

    # ---------------- header ----------------
    def header(self, surf, title, subtitle=""):
        # panel
        pygame.draw.rect(surf, BG_PANEL, (0, 0, W, 52))
        # animated accent line under header
        pygame.draw.line(surf, self.accent, (0, 52), (W, 52), 2)
        if Anim.enabled():
            sx = int(Anim.scan(W, 240))
            if 0 <= sx < W:
                ls = pygame.Surface((70, 4), pygame.SRCALPHA)
                ls.fill((self.accent[0], self.accent[1], self.accent[2],
                         int(160 * Anim.pulse(1.2, 0.5, 1.0))))
                surf.blit(ls, (sx, 50))
        # corner brackets on header
        self.corner_brackets(surf, (2, 2, W - 4, 48), self.accent, size=6, thick=2)
        # brand mark: a pulsing diamond
        cx, cy = 22, 26
        size = 6 + int(2 * Anim.pulse(1.4))
        pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
        pygame.draw.polygon(surf, self.accent, pts)
        # title with glow
        title = (title or "").upper()
        self.glow_text(surf, title, (42, 8), self.f_big, self.accent,
                       glow=self.accent, radius=2 if Anim.enabled() else 0)
        if subtitle:
            tw = self.f_small.size(subtitle)[0]
            self.text(surf, subtitle, (W - tw - 16, 18),
                      self.f_small, FG_DIM)

    # ---------------- footer ----------------
    def footer(self, surf, hints):
        """hints: [(button_label, description), ...]"""
        pygame.draw.rect(surf, BG_PANEL, (0, H - 34, W, 34))
        pygame.draw.line(surf, self.accent, (0, H - 34), (W, H - 34), 1)
        x = 10
        size = 20
        for label, desc in hints:
            w = icons_mod.draw_button(surf, label, x, H - 28, size=size)
            x += w + 6
            self.text(surf, desc, (x, H - 24), self.f_small, FG_DIM)
            x += self.f_small.size(desc)[0] + 16
            if x > W - 60:
                break


# ---------------------------------------------------------------------
#  MenuList — glowing selection, slide indicator, optional icon
# ---------------------------------------------------------------------
class MenuList(object):
    def __init__(self, theme, items=None, row_h=34, top=64, bottom=H - 40,
                 logos=None):
        self.t = theme
        self.items = items or []
        self.sel = 0
        self.row_h = row_h
        self.top = top
        self.bottom = bottom
        self.logos = logos
        self._slide_x = 6  # animated selector

    def norm(self, i):
        it = self.items[i]
        if isinstance(it, str):
            return it, "", "", "", ""
        it = list(it)
        while len(it) < 5:
            it.append("")
        return it[:5]

    def visible_rows(self):
        return max(1, (self.bottom - self.top) // self.row_h)

    def move(self, delta):
        if not self.items:
            return
        self.sel = (self.sel + delta) % len(self.items)

    def page(self, delta):
        if not self.items:
            return
        self.sel = max(0, min(len(self.items) - 1,
                              self.sel + delta * self.visible_rows()))

    def _icon_or_logo(self, surf, x, y, icon_h, logo_url, icon_name):
        if icon_name and icon_name in icons_mod.ICONS:
            icons_mod.draw_icon(surf, icon_name, x, y,
                                icon_h, self.t.accent, time.time())
            return True
        if self.logos and logo_url:
            img = self.logos.get(logo_url, icon_h)
            if img is not None:
                surf.blit(img, (x + (icon_h - img.get_width()) // 2,
                                y + (icon_h - img.get_height()) // 2))
                return True
        return False

    def draw(self, surf):
        if not self.items:
            self.t.text(surf, i18n.t("ui.empty"), (24, self.top + 10),
                        self.t.f_med, FG_DIM)
            return
        vis = self.visible_rows()
        first = max(0, min(self.sel - vis // 2, len(self.items) - vis))
        y = self.top
        icon_h = self.row_h - 12
        icon_slot = icon_h + 10
        for i in range(first, min(first + vis, len(self.items))):
            label, sub, badge, logo_url, icon_name = self.norm(i)
            selected = (i == self.sel)
            if selected:
                pygame.draw.rect(surf, BG_SEL, (6, y, W - 12, self.row_h - 2))
                # pulsing left accent bar
                pulse = Anim.pulse(0.9, 0.7, 1.0)
                col = (int(self.t.accent[0] * pulse),
                       int(self.t.accent[1] * pulse),
                       int(self.t.accent[2] * pulse))
                pygame.draw.rect(surf, col, (6, y, 4, self.row_h - 2))
                # subtle border pulse
                b = pygame.Surface((W - 12, self.row_h - 2), pygame.SRCALPHA)
                a = int(60 * Anim.pulse(1.4, 0.4, 1.0))
                pygame.draw.rect(b, (*self.t.accent, a),
                                 (0, 0, W - 12, self.row_h - 2), 1)
                surf.blit(b, (6, y))
            tx = 22
            drew = self._icon_or_logo(surf, 22, y + (self.row_h - 2 - icon_h) // 2,
                                       icon_h, logo_url, icon_name)
            if drew or icon_name:
                tx = 22 + icon_slot
            self.t.text(surf, label, (tx, y + 3),
                        self.t.f_med if not sub else self.t.f_med,
                        FG if selected else FG_DIM,
                        maxw=W - 38 - tx -
                             (self.t.f_small.size(badge)[0] + 20 if badge else 0))
            if sub:
                self.t.text(surf, sub, (tx, y + 4 + 20),
                            self.t.f_tiny, FG_FAINT,
                            maxw=W - 38 - tx)
            if badge:
                bw = self.t.f_small.size(badge)[0]
                self.t.text(surf, badge, (W - bw - 20, y + 8),
                            self.t.f_small, self.t.accent)
            y += self.row_h
        # scrollbar
        if len(self.items) > vis:
            track_h = self.bottom - self.top
            bar_h = max(16, track_h * vis // len(self.items))
            bar_y = self.top + (track_h - bar_h) * self.sel // \
                    max(1, len(self.items) - 1)
            pygame.draw.rect(surf, FG_FAINT, (W - 6, self.top, 3, track_h))
            pygame.draw.rect(surf, self.t.accent, (W - 6, bar_y, 3, bar_h))


# ---------------------------------------------------------------------
#  ChannelGrid
# ---------------------------------------------------------------------
class ChannelGrid(object):
    COLS, ROWS = 4, 3

    def __init__(self, theme, channels=None, logos=None):
        self.t = theme
        self.channels = channels or []
        self.sel = 0
        self.logos = logos

    def move(self, dx, dy):
        if not self.channels:
            return
        n = len(self.channels)
        self.sel = max(0, min(n - 1, self.sel + dx + dy * self.COLS))

    def draw(self, surf, epg=None):
        if not self.channels:
            self.t.text(surf, i18n.t("ui.no_channels"), (24, 70),
                        self.t.f_med, FG_DIM)
            return
        per_page = self.COLS * self.ROWS
        page = self.sel // per_page
        start = page * per_page
        cw, chh = 150, 118
        gx, gy = 12, 62
        for i in range(start, min(start + per_page, len(self.channels))):
            k = i - start
            x = gx + (k % self.COLS) * (cw + 6)
            y = gy + (k // self.COLS) * (chh + 6)
            ch = self.channels[i]
            selected = (i == self.sel)
            pygame.draw.rect(surf, BG_SEL if selected else BG_PANEL,
                             (x, y, cw, chh))
            pygame.draw.rect(surf, self.t.accent if selected else FG_FAINT,
                             (x, y, cw, chh), 2 if selected else 1)
            if selected:
                self.t.corner_brackets(surf, (x - 2, y - 2, cw + 4, chh + 4),
                                        self.t.accent, size=6, thick=2)
            img = (self.logos.get(ch.logo, 38)
                   if (self.logos and ch.logo) else None)
            if img is not None:
                surf.blit(img, (x + (cw - img.get_width()) // 2, y + 12))
            else:
                initials = "".join(w[0] for w in ch.name.split()[:2]).upper() or "?"
                f = self.t.f_big
                iw, ih = f.size(initials)
                self.t.text(surf, initials, (x + (cw - iw) // 2, y + 18), f,
                            self.t.accent if selected else FG_DIM)
            self.t.text(surf, ch.name, (x + 6, y + 62), self.t.f_tiny,
                        FG if selected else FG_DIM, maxw=cw - 12)
            if epg is not None:
                cur, _ = epg.now_next(ch)
                if cur:
                    self.t.text(surf, "» " + cur.title, (x + 6, y + 80),
                                self.t.f_tiny, FG_FAINT, maxw=cw - 12)
            self.t.text(surf, "#%d" % (i + 1), (x + 6, y + chh - 18),
                        self.t.f_tiny, FG_FAINT)
        total_pages = (len(self.channels) + per_page - 1) // per_page
        self.t.text(surf, i18n.t("ui.grid.page", page + 1, total_pages),
                    (W - 90, H - 56), self.t.f_tiny, FG_DIM)


# ---------------------------------------------------------------------
#  GuideView
# ---------------------------------------------------------------------
class GuideView(object):
    """Timeline guide. UP/DOWN = channel, LEFT/RIGHT = EPG programme nav."""

    ROWS = 7
    SPAN = 3 * 3600

    def __init__(self, theme, channels=None, logos=None):
        self.logos = logos
        self.t = theme
        self.channels = channels or []
        self.sel = 0
        self.epg_sel = 0
        self.t0 = self._align(time.time() - 900)

    @staticmethod
    def _align(ts):
        return ts - (ts % 1800)

    def move(self, dy):
        if self.channels:
            self.sel = (self.sel + dy) % len(self.channels)
            self.epg_sel = 0

    def nav_prog(self, dx, epg):
        if not epg or not self.channels:
            return
        progs = epg.programmes_for(self.channels[self.sel])
        if progs:
            self.epg_sel = max(0, min(len(progs) - 1, self.epg_sel + dx))

    def current_prog(self, epg):
        if not epg or not self.channels:
            return None
        progs = epg.programmes_for(self.channels[self.sel])
        if 0 <= self.epg_sel < len(progs):
            return progs[self.epg_sel]
        return None

    def draw(self, surf, epg):
        if not self.channels:
            self.t.text(surf, i18n.t("ui.no_channels"), (24, 70),
                        self.t.f_med, FG_DIM)
            return
        it_font = getattr(self.t, "f_tiny_it", self.t.f_tiny)
        name_w = 152
        area_x, area_w = name_w + 4, W - name_w - 12
        top, row_h = 82, 42

        # subtle horizontal grid behind rows
        for r_i in range(self.ROWS):
            yy = top + r_i * row_h
            pygame.draw.line(surf, (36, 36, 50), (0, yy + row_h - 2),
                             (W, yy + row_h - 2), 1)

        # hour ruler
        for k in range(7):
            ts = self.t0 + k * 1800
            x = area_x + int(area_w * (ts - self.t0) / self.SPAN)
            label = time.strftime("%H:%M", time.localtime(ts))
            self.t.text(surf, label, (x, 60), self.t.f_tiny, FG_DIM)
            pygame.draw.line(surf, (55, 55, 70), (x, 78),
                             (x, top + self.ROWS * row_h), 1)

        first = max(0, min(self.sel - self.ROWS // 2,
                           len(self.channels) - self.ROWS))
        now = time.time()
        sel_prog = self.current_prog(epg)

        for r in range(first, min(first + self.ROWS, len(self.channels))):
            ch = self.channels[r]
            y = top + (r - first) * row_h
            selected_ch = (r == self.sel)
            if selected_ch:
                sel_surf = pygame.Surface((W, row_h - 2), pygame.SRCALPHA)
                sel_surf.fill((BG_SEL[0], BG_SEL[1], BG_SEL[2], 200))
                surf.blit(sel_surf, (0, y))
                pulse = Anim.pulse(1.0, 0.65, 1.0)
                col = (int(self.t.accent[0] * pulse),
                       int(self.t.accent[1] * pulse),
                       int(self.t.accent[2] * pulse))
                pygame.draw.rect(surf, col, (0, y, 3, row_h - 2))
            nx = 10
            img = (self.logos.get(ch.logo, 22)
                   if (self.logos and ch.logo) else None)
            if img is not None:
                surf.blit(img, (8, y + (row_h - 22) // 2 - 1))
                nx = 8 + min(img.get_width(), 42) + 4
            self.t.text(surf, ch.name, (nx, y + 10), self.t.f_small,
                        FG if selected_ch else FG_DIM, maxw=name_w - nx - 4)

            for p in (epg.window(ch, self.t0, self.t0 + self.SPAN)
                      if epg else []):
                x1 = area_x + int(area_w * max(0, p.start - self.t0) / self.SPAN)
                x2 = area_x + int(area_w * min(self.SPAN, p.stop - self.t0)
                                  / self.SPAN)
                if x2 - x1 < 3:
                    continue
                live = p.start <= now < p.stop
                is_sel = selected_ch and (p is sel_prog)
                pygame.draw.rect(surf, BG_PANEL, (x1 + 1, y + 3,
                                                  x2 - x1 - 2, row_h - 8))
                if live:
                    frac = (now - p.start) / max(1, p.stop - p.start)
                    pw = int((x2 - x1 - 4) * frac)
                    if pw > 0:
                        pygame.draw.rect(surf, (50, 140, 80),
                                         (x1 + 2, y + row_h - 10, pw, 2))
                if is_sel:
                    pygame.draw.rect(surf, self.t.accent,
                                     (x1 + 1, y + 3, x2 - x1 - 2,
                                      row_h - 8), 2)
                    self.t.corner_brackets(
                        surf, (x1 - 1, y + 1, x2 - x1 + 2, row_h - 4),
                        self.t.accent, size=5, thick=1)
                elif live:
                    pygame.draw.rect(surf, (100, 200, 120),
                                     (x1 + 1, y + 3, x2 - x1 - 2,
                                      row_h - 8), 1)
                else:
                    pygame.draw.rect(surf, FG_FAINT,
                                     (x1 + 1, y + 3, x2 - x1 - 2,
                                      row_h - 8), 1)
                color = FG if (is_sel or live) else FG_DIM
                self.t.text(surf, p.title, (x1 + 5, y + 10),
                            self.t.f_tiny, color, maxw=x2 - x1 - 10)

        # now marker (pulsing)
        if self.t0 <= now <= self.t0 + self.SPAN:
            x = area_x + int(area_w * (now - self.t0) / self.SPAN)
            thick = 2 if int(now * 2) % 2 == 0 else 1
            pygame.draw.line(surf, self.t.accent, (x, 76),
                             (x, top + self.ROWS * row_h), thick)

        # ============ bottom detail panel ============
        y_base = top + self.ROWS * row_h + 4
        pygame.draw.rect(surf, BG_PANEL, (0, y_base, W, H - y_base - 34))
        pygame.draw.line(surf, self.t.accent, (0, y_base), (W, y_base), 1)
        self.t.corner_brackets(surf, (2, y_base, W - 4, H - y_base - 36),
                                self.t.accent, size=6, thick=1)

        cur, nxt = epg.now_next(self.channels[self.sel]) if epg else (None, None)
        from . import icons as _ic
        # --- NOW (green, play icon, both green) ---
        y0 = y_base + 5
        _ic.draw_icon(surf, "play", 10, y0 + 2, 13,
                       (100, 220, 120), time.time())
        self.t.text(surf, "NOW", (28, y0), self.t.f_small, (100, 220, 120))
        if cur:
            self.t.text(surf, cur.title, (72, y0 - 1), self.t.f_small,
                        (100, 220, 120), maxw=W - 90)
        else:
            self.t.text(surf, "—", (72, y0 - 1), self.t.f_small, FG_FAINT)

        # --- NEXT (dim, smaller, italic, » symbol) ---
        y1 = y0 + 20
        self.t.text(surf, "»", (10, y1), it_font, FG_DIM)
        self.t.text(surf, "NEXT", (28, y1), it_font, FG_DIM)
        if nxt:
            tm = time.strftime("%H:%M", time.localtime(nxt.start))
            self.t.text(surf, "%s (%s)" % (nxt.title, tm),
                        (72, y1), it_font, FG_DIM, maxw=W - 90)
        else:
            self.t.text(surf, "—", (72, y1), it_font, FG_FAINT)

        # --- SELECTED programme (only when user navigated) ---
        if sel_prog and (not cur or sel_prog is not cur) and \
                (not nxt or sel_prog is not nxt):
            y2 = y1 + 20
            pygame.draw.line(surf, self.t.accent, (8, y2 - 2),
                             (W - 8, y2 - 2), 1)
            tm1 = time.strftime("%H:%M", time.localtime(sel_prog.start))
            tm2 = time.strftime("%H:%M", time.localtime(sel_prog.stop))
            self.t.text(surf, "▸ " + sel_prog.title,
                        (8, y2), self.t.f_small, self.t.accent,
                        maxw=W - 130)
            self.t.text(surf, "%s-%s" % (tm1, tm2),
                        (W - 116, y2), self.t.f_tiny, FG_DIM)
            if sel_prog.desc:
                plot = sel_prog.desc.replace("\n", " ")
                self.t.text(surf, plot[:130], (14, y2 + 20),
                            self.t.f_tiny, FG_FAINT, maxw=W - 20)



# ---------------------------------------------------------------------
#  OnScreenKeyboard
# ---------------------------------------------------------------------
class OnScreenKeyboard(object):
    PAGES = [
        "abcdefghij" "klmnopqrst" "uvwxyz0123" "456789-_./",
        "ABCDEFGHIJ" "KLMNOPQRST" "UVWXYZ:/@?" "&=%#+~,;!*",
    ]
    COLS = 10

    def __init__(self, theme, title, initial=""):
        self.t = theme
        self.title = title
        self.value = initial
        self.page = 0
        self.sel = 0
        self.done = None

    def keys(self):
        return self.PAGES[self.page]

    def handle(self, btn):
        keys = self.keys()
        rows = (len(keys) + self.COLS - 1) // self.COLS
        r, c = divmod(self.sel, self.COLS)
        if btn == "UP":
            r = (r - 1) % rows
        elif btn == "DOWN":
            r = (r + 1) % rows
        elif btn == "LEFT":
            c = (c - 1) % self.COLS
        elif btn == "RIGHT":
            c = (c + 1) % self.COLS
        elif btn == "A":
            self.value += keys[min(self.sel, len(keys) - 1)]
        elif btn == "B":
            if self.value:
                self.value = self.value[:-1]
            else:
                self.done = False
        elif btn == "Y":
            self.value += " "
        elif btn in ("L1", "R1"):
            self.page = (self.page + 1) % len(self.PAGES)
        elif btn == "START":
            self.done = True
        elif btn == "X":
            self.done = False
        self.sel = min(r * self.COLS + c, len(keys) - 1)

    def draw(self, surf):
        surf.fill(BG)
        self.t.header(surf, self.title, "OSK")
        pygame.draw.rect(surf, BG_PANEL, (14, 64, W - 28, 36))
        pygame.draw.rect(surf, self.t.accent, (14, 64, W - 28, 36), 1)
        self.t.corner_brackets(surf, (14, 64, W - 28, 36),
                                self.t.accent, size=6, thick=2)
        shown = self.value[-52:]
        self.t.text(surf, shown + "_", (22, 72), self.t.f_med, FG)
        keys = self.keys()
        kx, ky, kw, kh = 40, 124, 56, 52
        for i, chak in enumerate(keys):
            r, c = divmod(i, self.COLS)
            x, y = kx + c * kw, ky + r * kh
            selected = (i == self.sel)
            pygame.draw.rect(surf, BG_SEL if selected else BG_PANEL,
                             (x, y, kw - 6, kh - 6))
            pygame.draw.rect(surf, self.t.accent if selected else FG_FAINT,
                             (x, y, kw - 6, kh - 6), 1)
            f = self.t.f_med
            cw, chh = f.size(chak)
            self.t.text(surf, chak, (x + (kw - 6 - cw) // 2,
                                     y + (kh - 6 - chh) // 2), f,
                        FG if selected else FG_DIM)
        self.t.footer(surf, [
            ("A", i18n.t("btn.insert")), ("B", i18n.t("btn.del")),
            ("Y", i18n.t("btn.space")), ("L/R", i18n.t("btn.symbols")),
            ("START", i18n.t("btn.ok")), ("X", i18n.t("btn.cancel")),
        ])


# ---------------------------------------------------------------------
#  Toast
# ---------------------------------------------------------------------
class Toast(object):
    def __init__(self, theme):
        self.t = theme
        self.msg = ""
        self.ok = True
        self.until = 0

    def show(self, msg, ok=True, secs=2.4):
        self.msg, self.ok, self.until = msg, ok, time.time() + secs

    def draw(self, surf):
        if time.time() > self.until or not self.msg:
            return
        f = self.t.f_small
        tw = f.size(self.msg)[0]
        w = min(W - 40, tw + 34)
        x, y = (W - w) // 2, H - 78
        s = pygame.Surface((w, 34), pygame.SRCALPHA)
        s.fill((BG_PANEL[0], BG_PANEL[1], BG_PANEL[2], 230))
        surf.blit(s, (x, y))
        pygame.draw.rect(surf, OK if self.ok else ERR, (x, y, w, 34), 1)
        self.t.corner_brackets(surf, (x, y, w, 34),
                                self.t.accent, size=5, thick=1)
        self.t.text(surf, self.msg, (x + 17, y + 9), f,
                    OK if self.ok else ERR, maxw=w - 34)


# backward-compat: main.py busy() chiama .scanlines()
if hasattr(Theme, 'scanline_overlay') and not hasattr(Theme, 'scanlines'):
    Theme.scanlines = Theme.scanline_overlay
