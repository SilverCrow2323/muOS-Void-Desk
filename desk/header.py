# -*- coding: utf-8 -*-
"""
Header avanzato per VoidDesk.
Indicatori LED, barra WiFi, batteria con effetto carica, orologio digitale.
"""

import time
import math
import pygame

from desk.const import W, FG, DIM, FAINT, OK_G, NO_R, INK, LINE
from desk import icons


def draw_header(surface, app, title, right="", icon=None, accent=None, badge=None):
    """Disegna l'header completo con tutti gli indicatori cyberpunk."""
    acc = accent if accent is not None else app.accent
    acc2 = app.accent2 if accent is None else theme_secondary(acc)

    pygame.draw.rect(surface, INK, (0, 0, W, 42))
    pygame.draw.line(surface, LINE, (0, 0), (W, 0), 1)
    pygame.draw.line(surface, acc, (0, 42), (W, 42), 2)
    pygame.draw.line(surface, INK, (0, 44), (W, 44), 2)
    pygame.draw.line(surface, acc2, (10, 36), (W - 10, 36), 1)

    for hx in range(0, 46, 9):
        pygame.draw.line(surface, acc, (hx, 42), (hx + 5, 46), 2)

    if title == "__brand__":
        _draw_brand(surface, app, acc)
    else:
        _draw_title(surface, app, title, icon, badge, acc)

    _draw_indicators(surface, app, acc, acc2, right)


def _draw_brand(surface, app, acc):
    sym = app.brand_symbol(26) if hasattr(app, "brand_symbol") else None
    tx0 = 13
    if sym is not None:
        surface.blit(sym, (10, 8))
        tx0 = 10 + sym.get_width() + 6
    surface.blit(app.f_big.render("Void-DESK", True, (150, 30, 30)), (tx0, 9))
    surface.blit(app.f_big.render("Void-DESK", True, (25, 90, 100)), (tx0 + 2, 7))
    surface.blit(app.f_big.render("Void-", True, FG), (tx0 + 1, 8))
    bw = app.f_big.size("Void-")[0]
    surface.blit(app.f_big.render("DESK", True, acc), (tx0 + 1 + bw, 8))


def _draw_title(surface, app, title, icon, badge, acc):
    if badge:
        bimg = app.badge_img(badge, 56) if hasattr(app, "badge_img") else None
        if bimg is not None:
            shadow = pygame.Surface(bimg.get_size(), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 100))
            surface.blit(shadow, (13, 4))
            surface.blit(bimg, (9, 1))
            return
    tx0 = 14
    if icon:
        icons.draw(surface, icon, 12, 8, 28, acc)
        tx0 = 48
    else:
        surface.blit(app.f_big.render("\u25a0 ", True, (140, 30, 30)), (13, 9))
        surface.blit(app.f_big.render("\u25a0 ", True, acc), (14, 8))
        tx0 = 14 + app.f_big.size("\u25a0 ")[0]
    surface.blit(app.f_big.render(title, True, (140, 30, 30)), (tx0 - 1, 9))
    surface.blit(app.f_big.render(title, True, acc), (tx0, 8))


def _draw_indicators(surface, app, acc, acc2, right=""):
    st = app.status_snapshot() if hasattr(app, "status_snapshot") else {}
    x = W - 14
    now = time.time()

    if app.cfg.get("battery", True) and app.cfg.get("st_batt", True):
        batt = st.get("batt")
        if batt is not None:
            bar_w, bar_h = 4, 16
            bar_x = x - 18
            bar_y = 12
            pygame.draw.rect(surface, (8, 10, 14), (bar_x, bar_y, bar_w, bar_h))
            fill_h = int(bar_h * (batt / 100))
            col = NO_R if batt <= 20 else (OK_G if batt > 50 else (255, 200, 60))
            if fill_h > 0:
                pygame.draw.rect(surface, col, (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))
            pygame.draw.rect(surface, acc, (bar_x, bar_y, bar_w, bar_h), 1)
            if st.get("chg"):
                pulse = 0.5 + 0.5 * math.sin(now * 4)
                pygame.draw.circle(surface, (60, 255, 110, int(150 * pulse)), (bar_x + 2, bar_y - 3), 2)
            txt = "%d%%" % batt
            tw = app.f_tiny.size(txt)[0]
            x -= tw + 4
            surface.blit(app.f_tiny.render(txt, True, col if batt > 20 else NO_R), (x, 14))

    if app.cfg.get("st_vol", True):
        vol = st.get("vol")
        if vol is not None:
            x -= 22
            icons.volume_icon(surface, x, 10, 16, vol, acc, FAINT)
            bar_w, bar_h = 14, 3
            bar_x = x + 1
            bar_y = 33
            pygame.draw.rect(surface, (20, 22, 28), (bar_x, bar_y, bar_w, bar_h))
            fill_w = max(1, int(bar_w * (vol or 0) / 100))
            pygame.draw.rect(surface, acc, (bar_x, bar_y, fill_w, bar_h))

    if st.get("usb") and app.cfg.get("st_usb", True):
        x -= 20
        icons.draw(surface, "usb" if st["usb"] == "mtp" else "android", x, 10, 14, acc)

    if st.get("hot") and app.cfg.get("st_hotspot", True):
        x -= 20
        icons.draw(surface, "uplink", x, 10, 14, OK_G)
        if int(now * 2) % 2:
            pygame.draw.circle(surface, OK_G, (x + 7, 30), 2)

    if st.get("bt") is not None and app.cfg.get("st_bt", True):
        x -= 20
        icons.bt_icon(surface, x, 10, 16, st["bt"], acc, FAINT)
        col = OK_G if st["bt"] else (60, 60, 60)
        pulse = 0.5 + 0.5 * math.sin(now * 3) if st["bt"] else 1
        pygame.draw.circle(surface, (col[0], col[1], col[2], int(150 * pulse)), (x + 8, 30), 2)

    if app.cfg.get("st_wifi", True):
        x -= 22
        icons.wifi_icon(surface, x, 10, 16, st.get("wifi"), acc, FAINT)
        wifi_lvl = st.get("wifi")
        if wifi_lvl is not None:
            for i in range(4):
                h = 2 + i * 2
                col = acc if i < wifi_lvl else (40, 44, 52)
                pygame.draw.rect(surface, col, (x + 2 + i * 3, 34 - h, 2, h))

    if app.cfg.get("clock_badge", True):
        lt = time.localtime()
        blink = int(now * 2) % 2 == 0
        sep = ":" if blink else " "
        hm = "%02d%s%02d" % (lt.tm_hour, sep, lt.tm_min)
        tw = app.f_med_b.size(hm)[0]
        bx = x - tw - 10
        by = 8
        pygame.draw.rect(surface, (4, 6, 8), (bx, by, tw + 8, 26), border_radius=4)
        pygame.draw.rect(surface, acc, (bx, by, tw + 8, 26), 1, border_radius=4)
        surface.blit(app.f_med_b.render(hm, True, (120, 240, 170)), (bx + 4, by + 2))
        pulse = 0.5 + 0.5 * math.sin(now * 3)
        pygame.draw.circle(surface, (60, 255, 110, int(150 * pulse)), (bx - 6, by + 12), 3)

    if right:
        x -= app.f_small.size(right)[0] + 6
        surface.blit(app.f_small.render(right, True, DIM), (x, 14))


def theme_secondary(accent):
    r, g, b = accent
    gray = (r + g + b) / 3.0
    r2 = r * 0.5 + gray * 0.5
    g2 = g * 0.5 + gray * 0.5
    b2 = b * 0.5 + gray * 0.5
    return (int(r2 * 0.5), int(g2 * 0.5), int(b2 * 0.5))
