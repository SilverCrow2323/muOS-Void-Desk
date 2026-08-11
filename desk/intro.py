# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // intro — sigla d'avvio (Minoru Uzumaki Constant Flow Build)
# ============================================================================
import math
import os
import random
import time
import pygame

FONT = None
_SYMBOL_CACHE = {}
_OVERLAY_CACHE = {}

def _symbol(h):
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

def _get_overlay(w, h, alpha, strength):
    key = (w, h, alpha, strength)
    if key in _OVERLAY_CACHE:
        return _OVERLAY_CACHE[key]
    
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    step = 3
    for y in range(0, h, step):
        pygame.draw.line(ov, (0, 0, 0, alpha), (0, y), (w, y))
    steps = 9
    th = max(2, min(w, h) // (2 * steps))
    for i in range(steps):
        a = int(strength * ((steps - i) / float(steps)) ** 2.2)
        if a > 0:
            r = pygame.Rect(i * th, i * th, w - 2 * i * th, h - 2 * i * th)
            pygame.draw.rect(ov, (0, 0, 0, a), r, th)
            
    _OVERLAY_CACHE[key] = ov
    return ov

def _draw_ssj3_purple_aurora(surface, center_x, center_y, box_w, box_h, t):
    for _ in range(3):
        angle = random.uniform(0, 2 * math.pi)
        ox = center_x + math.cos(angle) * (box_w * 0.45 + random.randint(0, 10))
        oy = center_y + math.sin(angle) * (box_h * 0.45 + random.randint(0, 8))
        
        curr_x, curr_y = ox, oy
        points = [(int(ox), int(oy))]
        for _seg in range(3):
            curr_x += random.randint(-14, 14)
            curr_y += random.randint(-14, 14)
            points.append((int(curr_x), int(curr_y)))
            
        if len(points) > 1:
            pygame.draw.lines(surface, (220, 130, 255), False, points, 1)

class UnstableTunnel(object):
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cx, self.cy = w // 2, h // 2
        self.num_rings = 16
        self.sides = 6
        self.z_vals = [i * (14.0 / self.num_rings) for i in range(self.num_rings)]
        self.last_active_points = []

    def draw(self, surface, t, speed=0.0, accent=(255, 176, 46), spiral_progress=0.0):
        # Velocità perfettamente costante basata sul tempo lineare t, senza sbalzi o accelerazioni improvvise
        step = speed * 0.04
        
        if spiral_progress <= 0:
            for i in range(self.num_rings):
                self.z_vals[i] -= step
                if self.z_vals[i] <= 0.1:
                    self.z_vals[i] += 14.0
                    
        sorted_z = sorted(self.z_vals, reverse=True)
        rot = t * 0.3 
        
        shift_x = self.cx + math.sin(t * 1.2) * 30 + math.cos(t * 0.5) * 15
        shift_y = self.cy + math.cos(t * 1.0) * 20 + math.sin(t * 0.4) * 10

        current_frame_points = []

        for z in sorted_z:
            if z < 0.1: continue
            scale = (self.w * 0.8) / z
            
            pts = []
            deform_sides = self.sides + int(math.sin(z + t * 1.5) * 2)
            deform_sides = max(4, min(8, deform_sides))
            
            for s in range(deform_sides):
                angle = rot + (s * (2 * math.pi / deform_sides)) + (z * 0.15)
                px = shift_x + math.cos(angle) * scale
                py = shift_y + math.sin(angle) * scale
                pts.append((px, py))
            
            current_frame_points.append((pts, z))
                
            intensity = max(0.0, 1.0 - (z / 14.0))
            if intensity > 0.05:
                mix_factor = (math.sin(t * 1.8 + z) + 1) * 0.5
                c = (
                    int(accent[0] * (1 - mix_factor) + 160 * mix_factor * intensity),
                    int(accent[1] * (1 - mix_factor) + 50 * mix_factor * intensity),
                    int(accent[2] * (1 - mix_factor) + 240 * mix_factor * intensity)
                )
                thickness = max(1, int(2.5 / z))
                
                if spiral_progress > 0:
                    uzumaki_pts = []
                    for px, py in pts:
                        dx = px - self.cx
                        dy = py - self.cy
                        dist = math.hypot(dx, dy)
                        base_angle = math.atan2(dy, dx)
                        
                        twist = base_angle + (spiral_progress * (6.0 + (12.0 / (dist + 1.0))))
                        target_dist = dist * (1.0 - spiral_progress)
                        
                        ux = self.cx + math.cos(twist) * target_dist
                        uy = self.cy + math.sin(twist) * target_dist
                        uzumaki_pts.append((int(ux), int(uy)))
                    pygame.draw.lines(surface, c, True, uzumaki_pts, max(1, int(thickness * (1.0 - spiral_progress * 0.5))))
                else:
                    int_pts = [(int(px), int(py)) for px, py in pts]
                    pygame.draw.lines(surface, c, True, int_pts, thickness)

        if spiral_progress <= 0:
            self.last_active_points = current_frame_points

        if random.random() < 0.3 and spiral_progress <= 0:
            sx_pt = random.randint(0, self.w)
            sy_pt = random.randint(0, self.h)
            ex_pt = sx_pt + random.randint(-30, 30)
            ey_pt = sy_pt + random.randint(-30, 30)
            pygame.draw.line(surface, (210, 90, 255), (sx_pt, sy_pt), (ex_pt, ey_pt), 1)

class Sparks(object):
    def __init__(self):
        self.list = []

    def burst(self, x, y, n, col):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            s = random.uniform(1.5, 5.0)
            self.list.append([x, y, math.cos(a) * s, math.sin(a) * s,
                              random.uniform(0.4, 0.8), col])

    def step(self, surface):
        alive = []
        for p in self.list:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] -= 0.04
            if p[4] > 0:
                c = tuple(int(v * p[4]) for v in p[5])
                pygame.draw.circle(surface, c, (int(p[0]), int(p[1])), 1)
                alive.append(p)
        self.list = alive

def play(surface, flip, app_name="Void-DESK", accent=(255, 176, 46),
         skip_check=None, font_path=None, duration=1.3, menu_surf=None,
         jingle=None):
    global FONT
    FONT = font_path
    W, H = surface.get_size()
    tunnel = UnstableTunnel(W, H)
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

    overlay = _get_overlay(W, H, 26, 105)

    def skipped():
        return bool(skip_check and skip_check())

    def bg(t, speed=1.0, shake=0, spiral_p=0.0):
        surface.fill((5, 5, 9))
        tunnel.draw(surface, t, speed, accent, spiral_p)
        if shake:
            return random.randint(-shake, shake), random.randint(-shake, shake)
        return 0, 0

    def wait(fr):
        return int(fr * duration)

    # Atto 1
    n = wait(45)
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 1.0)
        a = int(255 * min(1, k * 3))
        x = W // 2 - i_fact.get_width() // 2
        y = H // 2 - 40
        if k < 0.22:
            _glitch_bands(surface, i_fact, x, y, 4)
        else:
            _rgb_split(surface, i_fact, x, y, int(2 * max(0, 1 - (k - 0.2) * 5)), a)
        lw = int((W - 220) * min(1, k * 1.4))
        pygame.draw.line(surface, accent, (W // 2 - lw // 2, y + 46), (W // 2 + lw // 2, y + 46), 2)
        if k > 0.35:
            pa = int(255 * min(1, (k - 0.35) * 3))
            p = i_pres.copy()
            p.set_alpha(pa)
            surface.blit(p, (W // 2 - p.get_width() // 2, y + 56))
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    for _ in range(wait(28)):
        if skipped(): return
        t = time.time() - t0
        bg(t, 1.0)
        x = W // 2 - i_fact.get_width() // 2
        y = H // 2 - 40
        surface.blit(i_fact, (x, y))
        pygame.draw.line(surface, accent, (W // 2 - (W - 220) // 2, y + 46), (W // 2 + (W - 220) // 2, y + 46), 2)
        surface.blit(i_pres, (W // 2 - i_pres.get_width() // 2, y + 56))
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # Atto 2
    n = wait(20)
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 1.0)
        a = int(255 * (1 - k))
        f = i_fact.copy()
        f.set_alpha(a)
        surface.blit(f, (W // 2 - f.get_width() // 2, H // 2 - 40))
        p = i_pres.copy()
        p.set_alpha(a)
        surface.blit(p, (W // 2 - p.get_width() // 2, H // 2 + 16))
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.016)

    # Atto 3 (Montaggio Logo)
    ly = H // 2 - 46
    n = wait(42)
    jingle_fired = False
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        ease = 1 - (1 - min(1, k * 1.25)) ** 4
        sx, sy = bg(t, 1.0)
        x = W // 2 - logo_w // 2 + sx
        off = int(140 * (1 - ease))
        a = int(255 * min(1, k * 2))
        _rgb_split(surface, i_a, x - off, ly + sy, int(4 * (1 - ease)), a)
        _rgb_split(surface, i_b, x + i_a.get_width() + off, ly + sy, int(4 * (1 - ease)), a)
        
        if k > 0.62:
            if jingle is not None and not jingle_fired:
                try: jingle.play()
                except Exception: pass
                jingle_fired = True
        
        if 0.6 < k < 0.66: sparks.burst(W // 2, ly + 26, 4, accent)
        sparks.step(surface)
        
        gw = int(logo_w * ease)
        pygame.draw.line(surface, accent, (W // 2 - gw // 2, ly + 62), (W // 2 + gw // 2, ly + 62), 3)
        
        sym = _symbol(50)
        if sym is not None and k > 0.55:
            sa = int(255 * min(1, (k - 0.55) / 0.35))
            simg = sym.copy()
            simg.set_alpha(sa)
            sx2 = x - off - sym.get_width() - 16
            surface.blit(simg, (sx2, ly - 2 + sy))
            _draw_ssj3_purple_aurora(surface, W // 2, ly + 25, logo_w + 60, 70, t)

        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # Atto 4 (Durata del logo ulteriormente allungata)
    n = wait(100)
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 1.0)
        x = W // 2 - logo_w // 2
        surface.blit(i_a, (x, ly))
        surface.blit(i_b, (x + i_a.get_width(), ly))
        sym = _symbol(50)
        if sym is not None:
            surface.blit(sym, (x - sym.get_width() - 16, ly - 2))
        pygame.draw.line(surface, accent, (W // 2 - logo_w // 2, ly + 62), (W // 2 + logo_w // 2, ly + 62), 3)
        sparks.step(surface)
        
        _draw_ssj3_purple_aurora(surface, W // 2, ly + 25, logo_w + 60, 70, t)
        
        sub_a = int(255 * min(1, k * 1.6))
        if sub_a > 0:
            sub_surf = pygame.Surface((sub_w + 4, 30), pygame.SRCALPHA)
            sub_surf.blit(sub_pre, (0, 2))
            rint_w, dot_rel = _rainbow_text(sub_surf, "Rintromping", f_rint, sub_pre.get_width(), 0, t, tremor=1)
            sub_surf.blit(sub_post, (sub_pre.get_width() + rint_w, 2))
            sub_surf.set_alpha(sub_a)
            sub_x0 = W // 2 - sub_w // 2
            surface.blit(sub_surf, (sub_x0, ly + 72))
            
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # Atto 4.5: Spegnimento CRT pulito del solo Logo
    crt_n = wait(20)
    base_clean_surf = surface.copy()
    logo_block_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    lx0 = W // 2 - logo_w // 2
    logo_block_surf.blit(i_a, (lx0, ly))
    logo_block_surf.blit(i_b, (lx0 + i_a.get_width(), ly))
    if sym is not None:
        logo_block_surf.blit(sym, (lx0 - sym.get_width() - 16, ly - 2))
    pygame.draw.line(logo_block_surf, accent, (lx0, ly + 62), (lx0 + logo_w, ly + 62), 3)
    logo_block_surf.blit(sub_pre, (W // 2 - sub_w // 2, ly + 74))
    
    for i in range(crt_n):
        if skipped(): return
        k = i / float(crt_n)
        t = time.time() - t0
        surface.blit(base_clean_surf, (0, 0))
        bg(t, 1.0)
        
        box_y1 = ly - 15
        box_y2 = ly + 110
        box_h_local = box_y2 - box_y1
        target_cy = box_y1 + box_h_local // 2
        
        if k < 0.75:
            h_line = max(1, int(box_h_local * (1.0 - (k / 0.75))))
            rect_src = pygame.Rect(0, target_cy - box_h_local // 2, W, box_h_local)
            sub_logo = logo_block_surf.subsurface(rect_src)
            scaled_sub = pygame.transform.smoothscale(sub_logo, (W, max(2, h_line)))
            surface.blit(scaled_sub, (0, target_cy - h_line // 2))
            if h_line < 20:
                pygame.draw.line(surface, (230, 150, 255), (0, target_cy), (W, target_cy), 1)
        else:
            flash_w = max(1, int(W * (1.0 - ((k - 0.75) / 0.25))))
            pygame.draw.line(surface, (255, 255, 255), (W // 2 - flash_w // 2, target_cy), (W // 2 + flash_w // 2, target_cy), 1)

        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.016)

    # Atto 5: Spirale Finale "Uzumaki" con velocità costante
    if menu_surf is None:
        for _ in range(wait(10)):
            flip()
            time.sleep(0.02)
        return
        
    n = wait(50)
    for i in range(n):
        if skipped(): break
        k = i / float(n)
        t = time.time() - t0
        
        surface.fill((5, 5, 9))
        tunnel.draw(surface, t, speed=1.0, accent=accent, spiral_progress=k)
        
        if k > 0.35:
            scale_k = (k - 0.35) / 0.65
            alpha_menu = int(255 * scale_k)
            temp_menu = menu_surf.copy()
            temp_menu.set_alpha(alpha_menu)
            surface.blit(temp_menu, (0, 0))

        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.016)
        
    surface.blit(menu_surf, (0, 0))
    flip()
