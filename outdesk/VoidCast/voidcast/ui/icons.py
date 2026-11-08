# outdesk/VoidCast/voidcast/ui/icons.py
# -*- coding: utf-8 -*-
# VOIDCAST // ui.icons — vector icons + real controller buttons.
import math
import pygame

BUTTON_COLORS = {
    "A": (90, 210, 100), "B": (220, 70, 70), "X": (70, 140, 220),
    "Y": (240, 200, 60),
    "L1": (95, 95, 110), "R1": (95, 95, 110),
    "L2": (75, 75, 90), "R2": (75, 75, 90),
    "L/R": (95, 95, 110), "L1/R1": (95, 95, 110),
    "START": (60, 60, 75), "SELECT": (60, 60, 75),
    "SEL": (60, 60, 75), "M": (60, 60, 75),
    "MENU": (60, 60, 75),
    "◄►": (60, 60, 75), "▲▼": (60, 60, 75),
    "<<>>": (60, 60, 75),
}
_FONT = None
def _font(size):
    global _FONT
    if _FONT is None or _FONT[0] != size:
        try:
            _FONT = (size, pygame.font.Font(None, size))
        except Exception:
            _FONT = (size, None)
    return _FONT[1]

def button_width(label, size=22):
    if label in ("A", "B", "X", "Y"):
        return size
    if label in ("UP", "DOWN", "LEFT", "RIGHT"):
        return size
    if label in ("L1", "R1", "L2", "R2", "◄►", "▲▼", "<<>>"):
        return max(size, 4 * 8 + 12)
    return max(size, len(label) * 8 + 12)

def draw_button(surf, label, x, y, size=22):
    """Draw a controller-style button; returns width used."""
    if label in ("A", "B", "X", "Y"):
        col = BUTTON_COLORS[label]
        r = size // 2
        cx, cy = x + r, y + r
        # shadow
        s = pygame.Surface((size + 6, size + 6), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 0, 0, 110), (r + 3, r + 4), r)
        surf.blit(s, (x - 3, y - 3))
        # base
        pygame.draw.circle(surf, col, (cx, cy), r)
        # gradient top
        lighter = tuple(min(255, c + 55) for c in col)
        pygame.draw.circle(surf, lighter, (cx - 2, cy - 2), max(2, r - 4))
        pygame.draw.circle(surf, col, (cx, cy), r, 2)
        pygame.draw.circle(surf, (15, 15, 20), (cx, cy), r, 1)
        # letter
        f = _font(int(size * 0.9))
        if f:
            letter = f.render(label, True, (15, 15, 20))
            surf.blit(letter, (cx - letter.get_width() // 2,
                               cy - letter.get_height() // 2))
        return size
    elif label in ("UP", "DOWN", "LEFT", "RIGHT"):
        # small arrow in a dark square
        r = 4
        pygame.draw.rect(surf, (60, 60, 75), (x, y, size, size),
                         border_radius=r)
        pygame.draw.rect(surf, (15, 15, 20), (x, y, size, size),
                         1, border_radius=r)
        cx, cy = x + size // 2, y + size // 2
        a = 6
        if label == "UP":
            pts = [(cx, cy - a), (cx - a, cy + a // 2), (cx + a, cy + a // 2)]
        elif label == "DOWN":
            pts = [(cx, cy + a), (cx - a, cy - a // 2), (cx + a, cy - a // 2)]
        elif label == "LEFT":
            pts = [(cx - a, cy), (cx + a // 2, cy - a), (cx + a // 2, cy + a)]
        else:
            pts = [(cx + a, cy), (cx - a // 2, cy - a), (cx - a // 2, cy + a)]
        pygame.draw.polygon(surf, (220, 220, 230), pts)
        return size
    else:
        col = BUTTON_COLORS.get(label, (60, 60, 75))
        r = size // 2
        w = button_width(label, size)
        s = pygame.Surface((w + 6, size + 6), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 110), (3, 4, w, size), border_radius=r)
        surf.blit(s, (x - 3, y - 3))
        pygame.draw.rect(surf, col, (x, y, w, size), border_radius=r)
        lighter = tuple(min(255, c + 40) for c in col)
        pygame.draw.rect(surf, lighter,
                         (x + 2, y + 2, w - 4, size // 2), border_radius=r)
        pygame.draw.rect(surf, (15, 15, 20), (x, y, w, size), 1,
                         border_radius=r)
        f = _font(int(size * 0.65))
        if f:
            txt = f.render(label, True, (225, 225, 232))
            surf.blit(txt, (x + (w - txt.get_width()) // 2,
                            y + (size - txt.get_height()) // 2))
        return w

# ------------------------------------------------------------------
# Vector icons (animated where the "t" param matters)
# ------------------------------------------------------------------
def icon_playlist(surf, x, y, size, accent, t=0.0):
    pulse = int(2 * math.sin(t * 3))
    for i in range(3):
        c = accent if i < 2 else (accent[0] // 2, accent[1] // 2, accent[2] // 2)
        pygame.draw.rect(surf, c,
                         (x + 4 + i * 2, y + 6 + i * 6 + pulse // 3,
                          size - 10 - i * 2, 3), border_radius=1)

def icon_epg(surf, x, y, size, accent, t=0.0):
    for i in range(3):
        for j in range(3):
            ph = 0.5 + 0.5 * math.sin(t * 2 + i * 0.7 + j * 0.9)
            a = max(60, int(255 * ph))
            c = (accent[0] * a // 255, accent[1] * a // 255, accent[2] * a // 255)
            pygame.draw.rect(surf, c, (x + 4 + i * 6, y + 4 + j * 6, 4, 4))

def icon_settings(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2, y + size // 2
    ro = size // 2 - 2
    ri = ro - 4
    for i in range(8):
        a = t * 0.4 + i * math.pi / 4
        px = int(cx + math.cos(a) * ro)
        py = int(cy + math.sin(a) * ro)
        pygame.draw.circle(surf, accent, (px, py), 2)
    pygame.draw.circle(surf, accent, (cx, cy), ri, 2)
    pygame.draw.circle(surf, (15, 15, 20), (cx, cy), ri - 2)

def icon_exit(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2, y + size // 2
    r = size // 2 - 3
    pygame.draw.arc(surf, accent, (cx - r, cy - r, r * 2, r * 2),
                    math.radians(45), math.radians(315), 2)
    pygame.draw.rect(surf, accent, (cx - 1, cy - r - 1, 2, r + 2))

def icon_play(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2, y + size // 2
    a = 1.0 + 0.15 * math.sin(t * 4)
    pts = [(cx - (size // 3) * a, cy - size // 3),
           (cx - (size // 3) * a, cy + size // 3),
           (cx + size // 3, cy)]
    pygame.draw.polygon(surf, accent, pts)

def icon_star(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2, y + size // 2
    ro = size // 2 - 2
    ri = ro // 2
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = ro if i % 2 == 0 else ri
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    pygame.draw.polygon(surf, accent, pts)

def icon_search(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2 - 2, y + size // 2 - 2
    r = size // 3
    pygame.draw.circle(surf, accent, (cx, cy), r, 2)
    pygame.draw.line(surf, accent, (cx + r, cy + r),
                     (cx + r + 4, cy + r + 4), 2)

def icon_record(surf, x, y, size, accent, t=0.0):
    cx, cy = x + size // 2, y + size // 2
    r = size // 3
    if int(t * 3) % 2 == 0:
        pygame.draw.circle(surf, (230, 60, 60), (cx, cy), r)
    else:
        pygame.draw.circle(surf, accent, (cx, cy), r, 1)

ICONS = {
    "playlist": icon_playlist, "epg": icon_epg, "settings": icon_settings,
    "exit": icon_exit, "play": icon_play, "star": icon_star,
    "search": icon_search, "record": icon_record,
}

def draw_icon(surf, name, x, y, size, accent, t=0.0):
    fn = ICONS.get(name)
    if fn:
        fn(surf, x, y, size, accent, t)
