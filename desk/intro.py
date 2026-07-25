# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // intro — sigla d'avvio disegnata a runtime.
#  Atti: 1) SPDW FACTORY presents  2) montaggio del logo  3) sottotitolo
#        4) atterraggio del logo nell'header e comparsa del menu.
#  Si salta con qualsiasi tasto. Un solo file esterno: il simbolo di
#  Void Desk (assets/brand/voiddesk_symbol.png), colori suoi propri,
#  mai ricolorato sul tema -- e' un marchio, non un elemento della UI.
# ============================================================================
import math
import os
import random
import time

import pygame

FONT = None
STAR_N = 90
_SYMBOL_CACHE = {}


def _symbol(h):
    """Simbolo Void Desk, ridimensionato e tenuto in cache per altezza
    richiesta -- caricato una volta sola dal disco, mai ricalcolato."""
    if h in _SYMBOL_CACHE:
        return _SYMBOL_CACHE[h]
    path = os.path.join(os.path.dirname(__file__), "..", "assets",
                        "brand", "voiddesk_symbol.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        w = int(img.get_width() * h / img.get_height())
        img = pygame.transform.smoothscale(img, (w, h))
    except Exception:
        img = None
    _SYMBOL_CACHE[h] = img
    return img


def _f(sz, bold=False):
    try:
        f = pygame.font.Font(FONT or None, sz)
    except Exception:
        f = pygame.font.Font(None, sz)
    f.set_bold(bold)
    return f


def _rainbow_text(surface, text, font, x, y, t, tremor=1):
    """Parola con bordo multicolore che ruota nel tempo e un lieve
    tremolio -- 'Rintromping' vive qui. Restituisce (larghezza totale,
    posizione stimata del puntino della prima 'i'), utile a chi deve
    far partire un effetto proprio da li'."""
    palette = [(255, 70, 70), (255, 170, 40), (255, 230, 60),
              (90, 230, 110), (70, 200, 255), (150, 110, 255),
              (255, 90, 200)]
    jx = random.randint(-tremor, tremor) if tremor else 0
    jy = random.randint(-tremor, tremor) if tremor else 0
    img = font.render(text, True, (255, 255, 255))
    n = len(palette)
    for i2, (ox, oy) in enumerate(((2, 0), (2, 2), (0, 2), (-2, 2),
                                   (-2, 0), (-2, -2), (0, -2),
                                   (2, -2))):
        col = palette[int(t * 3 + i2) % n]
        ring = font.render(text, True, col)
        surface.blit(ring, (x + ox + jx, y + oy + jy))
    surface.blit(img, (x + jx, y + jy))
    # stima del puntino della prima "i": subito prima del gambo,
    # vicino alla sommita' del carattere -- va bene un'approssimazione,
    # nessuno la misurera' al pixel
    idx = text.find("i")
    if idx >= 0:
        pre_w = font.size(text[:idx])[0]
        glyph_w = font.size("i")[0]
        dot_x = x + jx + pre_w + glyph_w // 2
        dot_y = y + jy + int(font.get_height() * 0.22)
    else:
        dot_x, dot_y = x + jx, y + jy
    return img.get_width(), (dot_x, dot_y)


def _rgb_split(surface, img, x, y, amount, alpha=255):
    """Aberrazione cromatica: rosso e ciano sfalsati. Sapore SPDW."""
    if amount <= 0:
        i = img.copy()
        i.set_alpha(alpha)
        surface.blit(i, (x, y))
        return
    for col, dx in (((255, 60, 60), -amount), ((60, 220, 255), amount)):
        ghost = img.copy()
        ghost.fill(col, special_flags=pygame.BLEND_RGB_MULT)
        ghost.set_alpha(int(alpha * 0.55))
        surface.blit(ghost, (x + dx, y), special_flags=pygame.BLEND_ADD)
    i = img.copy()
    i.set_alpha(alpha)
    surface.blit(i, (x, y))


def _glitch_bands(surface, img, x, y, amount):
    h = img.get_height()
    yy = 0
    while yy < h:
        band = random.randint(2, 7)
        dx = random.randint(-amount, amount) if random.random() < 0.45 else 0
        r = pygame.Rect(0, yy, img.get_width(), min(band, h - yy))
        surface.blit(img.subsurface(r), (x + dx, y + yy))
        yy += band


def _scanlines(surface, alpha=26, step=3):
    ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for y in range(0, surface.get_height(), step):
        pygame.draw.line(ov, (0, 0, 0, alpha), (0, y),
                         (surface.get_width(), y))
    surface.blit(ov, (0, 0))


def _vignette(surface, strength=105):
    """Bordi scuri, centro pulito (i rettangoli sono cornici, non pieni:
    prima si sommavano al contrario e spegnevano il logo)."""
    w, h = surface.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 9
    th = max(2, min(w, h) // (2 * steps))
    for i in range(steps):
        a = int(strength * ((steps - i) / float(steps)) ** 2.2)
        if a <= 0:
            continue
        r = pygame.Rect(i * th, i * th, w - 2 * i * th, h - 2 * i * th)
        pygame.draw.rect(ov, (0, 0, 0, a), r, th)
    surface.blit(ov, (0, 0))


class Stars(object):
    def __init__(self, w, h):
        self.pts = [[random.uniform(0, w), random.uniform(0, h),
                     random.uniform(0.2, 1.0)] for _ in range(STAR_N)]
        self.w, self.h = w, h

    def draw(self, surface, t, speed=0.0):
        for p in self.pts:
            p[0] -= speed * p[2] * 3
            if p[0] < 0:
                p[0] = self.w
                p[1] = random.uniform(0, self.h)
            v = 40 + 170 * p[2] * (0.45 + 0.55 * math.sin(t * 4 + p[2] * 9))
            v = max(0, min(255, int(v)))
            surface.set_at((int(p[0]) % self.w, int(p[1])),
                           (v // 3, v // 3, min(255, v // 2 + 20)))


class Sparks(object):
    def __init__(self):
        self.list = []

    def burst(self, x, y, n, col):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            s = random.uniform(1.5, 7.0)
            self.list.append([x, y, math.cos(a) * s, math.sin(a) * s,
                              random.uniform(0.4, 1.0), col])

    def step(self, surface):
        alive = []
        for p in self.list:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] -= 0.035
            if p[4] > 0:
                c = tuple(int(v * p[4]) for v in p[5])
                pygame.draw.circle(surface, c, (int(p[0]), int(p[1])),
                                   1 + int(p[4] * 2))
                alive.append(p)
        self.list = alive


def play(surface, flip, app_name="Void-DESK", accent=(255, 176, 46),
         skip_check=None, font_path=None, duration=1.0, menu_surf=None,
         jingle=None):
    global FONT
    FONT = font_path
    W, H = surface.get_size()
    stars = Stars(W, H)
    sparks = Sparks()
    t0 = time.time()

    f_pres = _f(15)
    f_fact = _f(30, True)
    f_logo = _f(46, True)
    f_sub = _f(16)
    f_rint = _f(16, True)

    i_fact = f_fact.render("SPDW FACTORY", True, (240, 240, 246))
    i_pres = f_pres.render("p r e s e n t s", True, (140, 140, 158))
    na, nb = (app_name.split("-", 1) + [""])[:2]
    i_a = f_logo.render(na, True, (244, 244, 250))
    i_b = f_logo.render("-" + nb if nb else "", True, accent)
    logo_w = i_a.get_width() + i_b.get_width()
    sub_pre = f_sub.render("A muOS ", True, (216, 216, 228))
    sub_post = f_sub.render(" Experience", True, (216, 216, 228))
    rint_w0 = f_rint.size("Rintromping")[0]
    sub_w = sub_pre.get_width() + rint_w0 + sub_post.get_width()

    def skipped():
        return bool(skip_check and skip_check())

    def bg(t, speed=0.0, shake=0):
        surface.fill((5, 5, 9))
        stars.draw(surface, t, speed)
        if shake:
            return random.randint(-shake, shake), random.randint(-shake,
                                                                 shake)
        return 0, 0

    def wait(fr):
        return int(fr * duration)

    # =================== ATTO 1: SPDW FACTORY ===================
    n = wait(46)
    for i in range(n):
        if skipped():
            return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 0.4)
        a = int(255 * min(1, k * 3))
        x = W // 2 - i_fact.get_width() // 2
        y = H // 2 - 40
        if k < 0.22:
            _glitch_bands(surface, i_fact, x, y, 5)
        else:
            _rgb_split(surface, i_fact, x, y,
                       int(3 * max(0, 1 - (k - 0.2) * 5)), a)
        lw = int((W - 220) * min(1, k * 1.4))
        pygame.draw.line(surface, accent, (W // 2 - lw // 2, y + 46),
                         (W // 2 + lw // 2, y + 46), 2)
        if k > 0.35:
            pa = int(255 * min(1, (k - 0.35) * 3))
            p = i_pres.copy()
            p.set_alpha(pa)
            surface.blit(p, (W // 2 - p.get_width() // 2, y + 56))
        _scanlines(surface)
        _vignette(surface)
        flip()
        time.sleep(0.018)

    # pausa di lettura
    for _ in range(wait(26)):
        if skipped():
            return
        t = time.time() - t0
        bg(t, 0.4)
        x = W // 2 - i_fact.get_width() // 2
        y = H // 2 - 40
        surface.blit(i_fact, (x, y))
        pygame.draw.line(surface, accent, (W // 2 - (W - 220) // 2, y + 46),
                         (W // 2 + (W - 220) // 2, y + 46), 2)
        surface.blit(i_pres, (W // 2 - i_pres.get_width() // 2, y + 56))
        _scanlines(surface)
        _vignette(surface)
        flip()
        time.sleep(0.018)

    # =================== ATTO 2: dissolvenza + accelerazione stelle ========
    n = wait(20)
    for i in range(n):
        if skipped():
            return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 0.4 + k * 7)
        a = int(255 * (1 - k))
        f = i_fact.copy()
        f.set_alpha(a)
        surface.blit(f, (W // 2 - f.get_width() // 2, H // 2 - 40))
        p = i_pres.copy()
        p.set_alpha(a)
        surface.blit(p, (W // 2 - p.get_width() // 2, H // 2 + 16))
        _scanlines(surface)
        _vignette(surface)
        flip()
        time.sleep(0.016)

    # =================== ATTO 3: montaggio del logo ===================
    ly = H // 2 - 46
    n = wait(40)
    jingle_fired = False
    for i in range(n):
        if skipped():
            return
        k = i / float(n)
        t = time.time() - t0
        ease = 1 - (1 - min(1, k * 1.25)) ** 4
        sx, sy = bg(t, 7 * (1 - ease) + 0.4, 3 if 0.62 < k < 0.72 else 0)
        x = W // 2 - logo_w // 2 + sx
        off = int(180 * (1 - ease))
        a = int(255 * min(1, k * 2))
        _rgb_split(surface, i_a, x - off, ly + sy, int(6 * (1 - ease)), a)
        _rgb_split(surface, i_b, x + i_a.get_width() + off, ly + sy,
                   int(6 * (1 - ease)), a)
        # anelli d'impatto
        if k > 0.62:
            if jingle is not None and not jingle_fired:
                try:
                    jingle.play()
                except Exception:
                    pass
                jingle_fired = True
            for r in (int((k - 0.62) * 700), int((k - 0.62) * 430)):
                if r > 0:
                    al = max(0, 150 - r)
                    if al > 0:
                        rs = pygame.Surface((W, H), pygame.SRCALPHA)
                        pygame.draw.circle(rs, accent + (al,),
                                           (W // 2, ly + 26), r, 2)
                        surface.blit(rs, (0, 0))
        if 0.6 < k < 0.66:
            sparks.burst(W // 2, ly + 26, 6, accent)
        sparks.step(surface)
        # riga luminosa sotto il logo
        gw = int(logo_w * ease)
        pygame.draw.line(surface, accent, (W // 2 - gw // 2, ly + 62),
                         (W // 2 + gw // 2, ly + 62), 3)
        # il simbolo arriva in dissolvenza, un filo dopo l'impatto del
        # logo -- stessa soglia k>0.62 di jingle e anelli, cosi' tutto
        # si sente come un unico evento
        sym = _symbol(50)
        if sym is not None and k > 0.55:
            sa = int(255 * min(1, (k - 0.55) / 0.35))
            simg = sym.copy()
            simg.set_alpha(sa)
            sx2 = x - off - sym.get_width() - 16
            surface.blit(simg, (sx2, ly - 2 + sy))
        # scia che attraversa il logo
        if 0.45 < k < 0.95:
            px = int((k - 0.45) / 0.5 * (logo_w + 90)) + W // 2 - logo_w // 2 \
                - 45
            sh = pygame.Surface((16, 66), pygame.SRCALPHA)
            for c in range(16):
                al = int(110 * (1 - abs(c - 8) / 8.0))
                pygame.draw.line(sh, accent + (al,), (c, 0), (c, 66))
            surface.blit(sh, (px, ly - 6), special_flags=pygame.BLEND_ADD)
        _scanlines(surface)
        _vignette(surface)
        flip()
        time.sleep(0.018)

    # =================== ATTO 4: sottotitolo che si scrive ===============
    rint_dot = [(W // 2, 260)]     # posizione di riserva, aggiornata a frame
    n = wait(52)
    for i in range(n):
        if skipped():
            return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 0.4)
        x = W // 2 - logo_w // 2
        surface.blit(i_a, (x, ly))
        surface.blit(i_b, (x + i_a.get_width(), ly))
        sym = _symbol(50)
        if sym is not None:
            surface.blit(sym, (x - sym.get_width() - 16, ly - 2))
        pygame.draw.line(surface, accent, (W // 2 - logo_w // 2, ly + 62),
                         (W // 2 + logo_w // 2, ly + 62), 3)
        sparks.step(surface)
        # sottotitolo unico, in dissolvenza: "Rintromping" ha il
        # trattamento speciale, il resto e' testo normale
        sub_a = int(255 * min(1, k * 1.6))
        if sub_a > 0:
            sub_surf = pygame.Surface((sub_w + 4, 30), pygame.SRCALPHA)
            sub_surf.blit(sub_pre, (0, 2))
            rint_w, dot_rel = _rainbow_text(
                sub_surf, "Rintromping", f_rint, sub_pre.get_width(), 0,
                t, tremor=1)
            sub_surf.blit(sub_post, (sub_pre.get_width() + rint_w, 2))
            sub_surf.set_alpha(sub_a)
            sub_x0 = W // 2 - sub_w // 2
            surface.blit(sub_surf, (sub_x0, ly + 72))
            rint_dot[0] = (sub_x0 + dot_rel[0], ly + 72 + dot_rel[1])
        _scanlines(surface)
        _vignette(surface)
        flip()
        time.sleep(0.018)

    # =================== ATTO 5: atterraggio nell'header ===============
    if menu_surf is None:
        for _ in range(wait(10)):
            flip()
            time.sleep(0.02)
        return
    logo_full = pygame.Surface((logo_w, i_a.get_height()), pygame.SRCALPHA)
    logo_full.blit(i_a, (0, 0))
    logo_full.blit(i_b, (i_a.get_width(), 0))
    # posizione/dimensione finali = quelle del logo nell'header del menu
    f_hdr = _f(26)
    tw = f_hdr.size("Void-DESK")[0]
    tx, ty = 14, 8
    ox, oy = rint_dot[0]
    diag = int(math.hypot(max(ox, W - ox), max(oy, H - oy))) + 20
    n = wait(26)
    frozen = surface.copy().convert_alpha()
    for i in range(n):
        if skipped():
            break
        k = i / float(n)
        e = 1 - (1 - k) ** 3
        sweep = e * 2 * math.pi
        surface.blit(menu_surf, (0, 0))
        # maschera a settore: quel che il fascio NON ha ancora
        # spazzato resta della vecchia sigla, il resto lascia vedere
        # il menu sotto -- moltiplico l'alpha del fotogramma congelato
        # per una maschera a spicchio che cresce nel tempo
        mask = pygame.Surface((W, H), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pts = [(ox, oy)]
        steps = 40
        for s in range(steps + 1):
            a = -math.pi / 2 + sweep + s * (2 * math.pi - sweep) / steps
            pts.append((ox + diag * math.cos(a), oy + diag * math.sin(a)))
        if len(pts) > 2:
            pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        fr = frozen.copy()
        fr.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(fr, (0, 0))
        # il fascio vero e proprio: una lama di luce all'angolo attuale
        bx = ox + diag * math.cos(-math.pi / 2 + sweep)
        by = oy + diag * math.sin(-math.pi / 2 + sweep)
        beam = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.line(beam, accent + (210,), (ox, oy), (bx, by), 5)
        pygame.draw.circle(beam, (255, 255, 255, 230), (int(ox), int(oy)),
                           5)
        surface.blit(beam, (0, 0), special_flags=pygame.BLEND_ADD)
        flip()
        time.sleep(0.016)
    surface.blit(menu_surf, (0, 0))
    flip()
