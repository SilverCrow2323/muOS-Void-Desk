# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // intro — boot animation
#  Final revision: vd_logo.png reveal + animated menu voices.
#  All text in English. Backward-compatible signature with earlier versions.
# ============================================================================
import math
import os
import random
import time
import pygame

FONT = None
_LOGO_CACHE = {}
_OVERLAY_CACHE = {}

# Menu voices shown during the boot sequence (name, subtitle).
# These are the same hub names used by the main menu — kept in sync here
# so the boot animation previews exactly what the user is about to see.
MENU_VOICES = [
    ("START SESSION", "desktop environments"),
    ("THE FORGE",     "installer"),
    ("UPLINK",        "network"),
    ("MEDIA VAULT",   "media"),
    ("Rt:TOOLBOX",    "tools"),
    ("WORKSHOP",      "maintenance"),
    ("INFO & ABOUT",  "info"),
    ("SETTINGS",      "config"),
    ("END",           "power"),
]


# ---------------------------------------------------------------- fonts ----
def _f(sz, bold=False):
    try:
        f = pygame.font.Font(FONT or None, sz)
    except Exception:
        f = pygame.font.Font(None, sz)
    f.set_bold(bold)
    return f


# ----------------------------------------------------------------- logo ----
def _logo_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (
        os.path.join(here, "..", "resources", "vd_logo.png"),
        os.path.join(here, "resources", "vd_logo.png"),
        os.path.join(here, "..", "assets", "brand", "vd_logo.png"),
        os.path.join(here, "..", "assets", "logo.png"),
    ):
        if os.path.isfile(p):
            return p
    return None


def _logo(h, max_w=None):
    """Load and cache vd_logo.png scaled to height h.
    Returns a Surface, or None if the file is missing/corrupt."""
    key = (h, max_w)
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    img = None
    p = _logo_path()
    if p:
        try:
            raw = pygame.image.load(p).convert_alpha()
            w = max(1, int(raw.get_width() * h / raw.get_height()))
            if max_w and w > max_w:
                w = max_w
                h = max(1, int(raw.get_height() * w / raw.get_width()))
            img = pygame.transform.smoothscale(raw, (w, h))
        except Exception:
            img = None
    _LOGO_CACHE[key] = img
    return img


# ---------------------------------------------------------- fx helpers ----
def _rgb_split(surface, img, x, y, amount, alpha=255):
    """Chromatic aberration / RGB split effect."""
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
    """Horizontal tearing/banding glitch."""
    h = img.get_height()
    yy = 0
    while yy < h:
        band = random.randint(2, 7)
        dx = random.randint(-amount, amount) if random.random() < 0.45 else 0
        r = pygame.Rect(0, yy, img.get_width(), min(band, h - yy))
        surface.blit(img.subsurface(r), (x + dx, y + yy))
        yy += band


def _get_overlay(w, h, alpha, strength):
    """Cached scanline + vignette overlay."""
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


def _rainbow_text(surface, text, font, x, y, t, tremor=1):
    """Rainbow-outlined text with optional jitter. Returns (width, baseline_y)."""
    palette = [(255, 70, 70), (255, 170, 40), (255, 230, 60),
               (90, 230, 110), (70, 200, 255), (150, 110, 255),
               (255, 90, 200)]
    jx = random.randint(-tremor, tremor) if tremor else 0
    jy = random.randint(-tremor, tremor) if tremor else 0
    img = font.render(text, True, (255, 255, 255))
    n = len(palette)
    for i2, (ox, oy) in enumerate(((2, 0), (2, 2), (0, 2), (-2, 2),
                                   (-2, 0), (-2, -2), (0, -2), (2, -2))):
        col = palette[int(t * 3 + i2) % n]
        ring = font.render(text, True, col)
        surface.blit(ring, (x + ox + jx, y + oy + jy))
    surface.blit(img, (x + jx, y + jy))
    return img.get_width(), y + jy + img.get_height() // 2


def _draw_ssj3_purple_aurora(surface, center_x, center_y, box_w, box_h, t):
    """Subtle purple lightning arcs around the logo."""
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


# ------------------------------------------------------- tunnel + sparks ----
class UnstableTunnel(object):
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cx, self.cy = w // 2, h // 2
        self.num_rings = 16
        self.sides = 6
        self.z_vals = [i * (14.0 / self.num_rings) for i in range(self.num_rings)]
        self.last_active_points = []

    def draw(self, surface, t, speed=0.0, accent=(255, 176, 46), spiral_progress=0.0):
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
            if z < 0.1:
                continue
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
                    int(accent[2] * (1 - mix_factor) + 240 * mix_factor * intensity),
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
                    pygame.draw.lines(surface, c, True, uzumaki_pts,
                                      max(1, int(thickness * (1.0 - spiral_progress * 0.5))))
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


# ------------------------------------------------------------------ play ----
def play(surface, flip, app_name="Void-DESK", accent=(255, 176, 46),
         skip_check=None, font_path=None, duration=1.3, menu_surf=None,
         jingle=None):
    """VoidDesk boot animation.

    Acts:
      1. Tunnel fade-in + vd_logo.png glitch reveal + sparks
      2. Title slides in, subtitle with rainbow 'Rintromping' accent
      3. Menu voices cascade in (glitch-slide, one by one)
      4. Hold frame with purple aurora around the logo
      5. CRT collapse of the whole block
      6. Uzumaki spiral transition to the actual menu (menu_surf)

    Signature is intentionally identical to the previous intro.play()
    so callers do not need to change.
    """
    global FONT
    FONT = font_path
    W, H = surface.get_size()
    tunnel = UnstableTunnel(W, H)
    sparks = Sparks()
    t0 = time.time()

    f_pres    = _f(12)
    f_title   = _f(26, True)
    f_sub     = _f(13)
    f_menu    = _f(15, True)
    f_menu_sub = _f(11)

    overlay = _get_overlay(W, H, 24, 95)

    # ---- logo geometry -------------------------------------------------
    logo_h = max(70, min(110, int(H * 0.22)))
    logo = _logo(logo_h, max_w=max(120, W - 60))
    if logo:
        logo_w, logo_h = logo.get_size()
    else:
        logo_w, logo_h = 0, 0
    logo_x = (W - logo_w) // 2
    logo_y = int(H * 0.10)

    # ---- title geometry ------------------------------------------------
    parts = app_name.split("-", 1)
    na = parts[0] + "-" if len(parts) > 1 else parts[0]
    nb = parts[1] if len(parts) > 1 else ""
    i_a = f_title.render(na, True, (244, 244, 250))
    i_b = f_title.render(nb, True, accent)
    title_w = i_a.get_width() + i_b.get_width()
    title_x = (W - title_w) // 2
    title_y = logo_y + logo_h + 10
    i_pres = f_pres.render("S P D W   F A C T O R Y", True, (140, 140, 158))

    # ---- subtitle geometry (rainbow accent on 'Rintromping') -----------
    sub_pre = f_sub.render("A muOS ", True, (216, 216, 228))
    sub_post = f_sub.render(" Experience", True, (216, 216, 228))
    rint_w, _ = f_sub.size("Rintromping")
    sub_w = sub_pre.get_width() + rint_w + sub_post.get_width()
    sub_x = (W - sub_w) // 2
    sub_y = title_y + i_a.get_height() + 8

    # ---- menu voices geometry ------------------------------------------
    line_h = max(20, f_menu.get_height() + 8)
    menu_top = sub_y + f_sub.get_height() + 22
    avail = H - menu_top - 20
    if len(MENU_VOICES) * line_h > avail:
        line_h = max(14, avail // len(MENU_VOICES))
    menu_left = W // 2 - 130

    menu_rows = []
    for name, sub in MENU_VOICES:
        menu_rows.append({
            "name": f_menu.render(name, True, (235, 235, 245)),
            "sub":  f_menu_sub.render(sub, True, (120, 122, 138)),
        })

    def skipped():
        return bool(skip_check and skip_check())

    def bg(t, speed=1.0, shake=0, spiral_p=0.0):
        surface.fill((5, 5, 9))
        tunnel.draw(surface, t, speed, accent, spiral_p)
        if shake:
            return random.randint(-shake, shake), random.randint(-shake, shake)
        return 0, 0

    def wait(fr):
        return max(1, int(fr * duration))

    def draw_logo(x, y, alpha=255, glitch=0):
        if not logo:
            return
        if glitch > 0:
            _glitch_bands(surface, logo, x, y, glitch)
        else:
            _rgb_split(surface, logo, x, y, 0, alpha)

    def draw_title(y_off=0, glitch=0, alpha=255):
        x = title_x
        y = title_y + y_off
        if glitch > 0:
            _glitch_bands(surface, i_a, x, y, glitch)
            b = i_b.copy(); b.set_alpha(alpha)
            surface.blit(b, (x + i_a.get_width(), y))
        else:
            a = i_a.copy(); a.set_alpha(alpha)
            b = i_b.copy(); b.set_alpha(alpha)
            surface.blit(a, (x, y))
            surface.blit(b, (x + i_a.get_width(), y))

    def draw_subtitle(t, alpha=255):
        if alpha <= 0:
            return
        sub_surf = pygame.Surface((sub_w + 4, f_sub.get_height() + 4), pygame.SRCALPHA)
        sub_surf.blit(sub_pre, (0, 0))
        _rainbow_text(sub_surf, "Rintromping", f_sub, sub_pre.get_width(), 0, t, tremor=1)
        sub_surf.blit(sub_post, (sub_pre.get_width() + rint_w, 0))
        sub_surf.set_alpha(alpha)
        surface.blit(sub_surf, (sub_x, sub_y))

    def draw_menu(reveal_idx, current_local_k):
        for j, row in enumerate(menu_rows):
            if j > reveal_idx:
                break
            y = menu_top + j * line_h
            if j == reveal_idx and current_local_k < 1.0:
                lk = current_local_k
                a = int(255 * min(1, lk * 2.2))
                off_x = int((1 - lk) * 30)
                if lk < 0.35:
                    _glitch_bands(surface, row["name"], menu_left + off_x, y, 4)
                else:
                    nm = row["name"].copy(); nm.set_alpha(a)
                    sm = row["sub"].copy();  sm.set_alpha(a)
                    surface.blit(nm, (menu_left + off_x, y))
                    surface.blit(sm, (menu_left + nm.get_width() + 12, y + 2))
            else:
                surface.blit(row["name"], (menu_left, y))
                surface.blit(row["sub"],
                             (menu_left + row["name"].get_width() + 12, y + 2))
            # accent tick on the left
            pygame.draw.rect(surface, accent,
                             (menu_left - 8, y + 4, 3, line_h - 8))

    jingle_fired = False

    # ===================================================================
    # ACT 1 — tunnel + logo glitch reveal + sparks  (~0.75 s)
    # ===================================================================
    n = wait(40)
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 1.0)
        a = int(255 * min(1, k * 2.5))
        gl = int(8 * (1 - k)) if k < 0.7 else 0
        draw_logo(logo_x, logo_y, a, glitch=gl)
        # spark burst when the logo is ~60% in
        if 0.55 < k < 0.62 and logo_w:
            sparks.burst(W // 2, logo_y + logo_h // 2, 6, accent)
        sparks.step(surface)
        # SPDW presenter line fades in near the end
        if k > 0.65:
            pa = int(255 * min(1, (k - 0.65) * 4))
            p = i_pres.copy(); p.set_alpha(pa)
            surface.blit(p, (W // 2 - p.get_width() // 2, logo_y + logo_h + 4))
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # ===================================================================
    # ACT 2 — title slides in + subtitle with rainbow accent  (~0.65 s)
    # ===================================================================
    n = wait(35)
    for i in range(n):
        if skipped(): return
        k = i / float(n)
        t = time.time() - t0
        bg(t, 1.0)
        draw_logo(logo_x, logo_y)
        p = i_pres.copy(); p.set_alpha(255)
        surface.blit(p, (W // 2 - p.get_width() // 2, logo_y + logo_h + 4))
        ease = 1 - (1 - min(1, k * 1.4)) ** 3
        off_y = int(-40 * (1 - ease))
        gl = int(6 * (1 - ease))
        draw_title(off_y, glitch=gl)
        # accent underline grows
        lw = int(title_w * ease)
        pygame.draw.line(surface, accent,
                         (W // 2 - lw // 2, title_y + i_a.get_height() + 2),
                         (W // 2 + lw // 2, title_y + i_a.get_height() + 2), 2)
        # subtitle appears after the title settles
        if k > 0.35:
            sa = int(255 * min(1, (k - 0.35) * 3))
            draw_subtitle(t, sa)
            if not jingle_fired and jingle is not None:
                try: jingle.play()
                except Exception: pass
                jingle_fired = True
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # ===================================================================
    # ACT 3 — menu voices cascade in  (~9 frames × 9 items ≈ 1.6 s)
    # ===================================================================
    per_item = 9
    total_menu = per_item * len(menu_rows)
    for i in range(total_menu):
        if skipped(): return
        t = time.time() - t0
        bg(t, 1.0)
        draw_logo(logo_x, logo_y)
        surface.blit(i_pres, (W // 2 - i_pres.get_width() // 2, logo_y + logo_h + 4))
        draw_title()
        pygame.draw.line(surface, accent,
                         (W // 2 - title_w // 2, title_y + i_a.get_height() + 2),
                         (W // 2 + title_w // 2, title_y + i_a.get_height() + 2), 2)
        draw_subtitle(t)
        idx = min(len(menu_rows) - 1, i // per_item)
        local_k = 1.0 if i // per_item < idx else (i % per_item) / float(per_item)
        draw_menu(idx, local_k)
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # ===================================================================
    # ACT 4 — hold frame + purple aurora around logo  (~0.9 s)
    # ===================================================================
    n = wait(50)
    for i in range(n):
        if skipped(): return
        t = time.time() - t0
        bg(t, 1.0)
        draw_logo(logo_x, logo_y)
        surface.blit(i_pres, (W // 2 - i_pres.get_width() // 2, logo_y + logo_h + 4))
        draw_title()
        pygame.draw.line(surface, accent,
                         (W // 2 - title_w // 2, title_y + i_a.get_height() + 2),
                         (W // 2 + title_w // 2, title_y + i_a.get_height() + 2), 2)
        draw_subtitle(t)
        draw_menu(len(menu_rows) - 1, 1.0)
        if logo_w:
            _draw_ssj3_purple_aurora(surface, W // 2, logo_y + logo_h // 2,
                                     logo_w + 40, logo_h + 20, t)
        sparks.step(surface)
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.018)

    # ===================================================================
    # ACT 5 — CRT collapse of the whole block  (~0.35 s)
    # ===================================================================
    crt_n = wait(20)
    base = surface.copy()
    block = pygame.Surface((W, H), pygame.SRCALPHA)
    if logo:
        block.blit(logo, (logo_x, logo_y))
    block.blit(i_a, (title_x, title_y))
    block.blit(i_b, (title_x + i_a.get_width(), title_y))
    for j, row in enumerate(menu_rows):
        block.blit(row["name"], (menu_left, menu_top + j * line_h))
        block.blit(row["sub"],
                   (menu_left + row["name"].get_width() + 12, menu_top + j * line_h + 2))
    y1 = max(0, logo_y - 4)
    y2 = min(H, menu_top + len(menu_rows) * line_h + 6)
    bh = max(20, y2 - y1)
    cy = y1 + bh // 2
    for i in range(crt_n):
        if skipped(): return
        k = i / float(crt_n)
        t = time.time() - t0
        surface.blit(base, (0, 0))
        bg(t, 1.0)
        if k < 0.75:
            h_line = max(1, int(bh * (1.0 - (k / 0.75))))
            src = pygame.Rect(0, cy - bh // 2, W, bh)
            sub = block.subsurface(src)
            scaled = pygame.transform.smoothscale(sub, (W, max(2, h_line)))
            surface.blit(scaled, (0, cy - h_line // 2))
            if h_line < 20:
                pygame.draw.line(surface, (230, 150, 255), (0, cy), (W, cy), 1)
        else:
            fw = max(1, int(W * (1.0 - ((k - 0.75) / 0.25))))
            pygame.draw.line(surface, (255, 255, 255),
                             (W // 2 - fw // 2, cy), (W // 2 + fw // 2, cy), 1)
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.016)

    # ===================================================================
    # ACT 6 — Uzumaki spiral transition to the real menu  (~0.9 s)
    # ===================================================================
    if menu_surf is None:
        for _ in range(wait(8)):
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
            a = int(255 * scale_k)
            tmp = menu_surf.copy(); tmp.set_alpha(a)
            surface.blit(tmp, (0, 0))
        surface.blit(overlay, (0, 0))
        flip()
        time.sleep(0.016)
    surface.blit(menu_surf, (0, 0))
    flip()


# ---------------------------------------------------------------- compat ----
def _symbol(h):
    """Deprecated: use _logo() for the main logo. Returns None."""
    return None