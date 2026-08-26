# ============================================================================
#  VOID DESK — NEXUS Renderer
#  Net-Sphere planetarium: orbits, nodes, planets, zoom, pan
# ============================================================================
import math
import random
import re
import time
import os
import pygame
from functools import lru_cache

from desk import icons
from desk.const import (
    NEXUS_NODE_DECO, NEXUS_SQUASH, NEXUS_OUTER_TILT, NEXUS_FAR_TILT,
    NEXUS_VOID_TILT, NEXUS_RING_RADIUS, NEXUS_ORBIT_SPEED, NEXUS_RING_MID, NEXUS_RING_OUT,
    NEXUS_RING_FAR, NEXUS_RING_INNER, NEXUS_RING_VOID, NEXUS_ZOOM, NEXUS_NODE_R,
    NEXUS_NODE_COLOR, NEXUS_SELECT_ZONE, NEXUS_NODE_BADGE, NEXUS_NODE_CODE,
    HUB_DESCRIPTIONS, FONT_MONO_PATH, FONT_OXANIUM_REGULAR_PATH, INK, LINE, W, H, FAINT, FG,
    NEXUS_PLANET_FILES, APP_DIR, NEXUS_BG_DEFAULTS
)


class NexusRenderer:
    """NEXUS planetarium renderer. All drawing methods operate on
    app.surface and read state from the app instance."""

    # Limiti per dispositivi con poca RAM (RG35XX-H ha 1GB)
    MAX_TRAIL_LENGTH = 4
    MAX_PARTICLES_PER_FRAME = 12
    PARTICLE_LIFETIME = 1.5
    CACHE_MAXSIZE = 12

    # Cache per seed: (cos_a, sin_a, jitter) precomputati
    _sphere_cache = {}
    # Posizioni stelle pregenerate una sola volta (seed 77 -> pos fisse,
    # solo il valore/twinkle varia col tempo): evita di riallokare e
    # randomizzare ogni 0.2s una superficie intera (W*H*4 byte) su RAM
    # stretta.
    _star_positions = None

    def __init__(self, app):
        self.app = app
        self._rtcore_residue = None
        self._rtcore_residue_alpha = 0.0
        self._rtcore_residue_timer = 0.0
        self._nexus_planet_lru = {}
        self._nexus_planet_lru_order = []

    @staticmethod
    def _sphere_jitter_data(seed):
        data = NexusRenderer._sphere_cache.get(seed)
        if data is not None:
            return data
        n_pts = 26
        cos_a = [0.0] * n_pts
        sin_a = [0.0] * n_pts
        jit = [0.0] * n_pts
        for k in range(n_pts):
            a = 2 * math.pi * k / n_pts
            cos_a[k] = math.cos(a)
            sin_a[k] = math.sin(a)
            jit[k] = (1.6 * math.sin(k * 2.7 + seed * 1.3) +
                      1.0 * math.sin(k * 5.1 + seed * 0.6))
        data = (cos_a, sin_a, jit)
        NexusRenderer._sphere_cache[seed] = data
        return data

    @staticmethod
    def _sun_jitter_data():
        n_pts = 26
        cos_a = [0.0] * n_pts
        sin_a = [0.0] * n_pts
        jit = [0.0] * n_pts
        for k in range(n_pts):
            a = 2 * math.pi * k / n_pts
            cos_a[k] = math.cos(a)
            sin_a[k] = math.sin(a)
            jit[k] = (1.6 * math.sin(k * 2.7) + 1.0 * math.sin(k * 5.1))
        return cos_a, sin_a, jit

    _SUN_JITTER = _sun_jitter_data.__func__()

    def _cached_planet_icon(self, icon_key, size):
        """Cache LRU boundata per texture planetarie, evita growth
        incontrollato su RAM stretta."""
        key = (icon_key, size)
        lru = self._nexus_planet_lru
        order = self._nexus_planet_lru_order
        if key in lru:
            order.remove(key)
            order.append(key)
            return lru[key]
        img = None
        fname = NEXUS_PLANET_FILES.get(icon_key)
        if fname:
            path = os.path.join(APP_DIR, "assets", "nexus_planets",
                                fname)
            try:
                src = pygame.image.load(path).convert_alpha()
                sw, sh = src.get_size()
                fit = min(size / float(sw), size / float(sh))
                nw = max(1, int(round(sw * fit)))
                nh = max(1, int(round(sh * fit)))
                scaled = pygame.transform.smoothscale(src, (nw, nh))
                img = pygame.Surface((size, size), pygame.SRCALPHA)
                img.blit(scaled, ((size - nw) // 2, (size - nh) // 2))
            except Exception:
                img = None
        lru[key] = img
        order.append(key)
        while len(order) > self.CACHE_MAXSIZE:
            old = order.pop(0)
            lru.pop(old, None)
        return img

    def clear_caches(self):
        """Svuota tutte le cache del renderer per liberare memoria."""
        self._nexus_planet_lru.clear()
        self._nexus_planet_lru_order.clear()
        self._cached_planet_icon.cache_clear()
        self._sphere_cache.clear()
        self._star_positions = None

    def _get_quality_level(self):
        """Restituisce (trail_len, particles) adattati all'FPS corrente
        per risparmiare memoria e CPU su dispositivi con poca RAM."""
        fps = getattr(self.app, "clock", None)
        fps_val = fps.get_fps() if fps else 30.0
        if fps_val < 20:
            return 2, 0
        elif fps_val < 28:
            return 3, 4
        else:
            return self.MAX_TRAIL_LENGTH, self.MAX_PARTICLES_PER_FRAME

    # --- helpers ---

    def _nexus_curve(self, i, j, cx0, cy0, cx1, cy1):
        rnd = random.Random(3100 + min(i, j) * 7 + max(i, j))
        mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
        dx, dy = cx1 - cx0, cy1 - cy0
        dist = max(1, math.hypot(dx, dy))
        nx, ny = -dy / dist, dx / dist
        perp = rnd.uniform(-54, 54)
        return mx + nx * perp, my + ny * perp

    def _nexus_sphere(self, cx, cy, r, col, icon_key, t_now, pulse_extra=0.0,
                      spin=False, seed=0, selected=False, idx=None):
        deco = NEXUS_NODE_DECO.get(idx) if idx is not None else None
        moon = None
        if deco is not None:
            if deco[0] == "moonlet":
                moon = self._nexus_moonlet_pos(cx, cy, r, t_now, seed)
                if moon[0]:
                    self._nexus_draw_moonlet(moon, col)
            else:
                ring_surf = self._nexus_ring_surf(deco, r, col)
                if ring_surf is not None:
                    rw, rh = ring_surf.get_size()
                    self.app.surface.blit(ring_surf,
                                          (int(cx - rw / 2), int(cy - rh / 2)))
        pulse = 0.75 + 0.25 * abs(math.sin(t_now * 2.2)) + pulse_extra
        glow = tuple(min(255, int(c * pulse)) for c in col)
        pygame.draw.circle(self.app.surface, tuple(min(255, int(c * 0.5))
                           for c in col), (int(cx) + 2, int(cy) + 3), r)
        pygame.draw.circle(self.app.surface, (8, 9, 16), (int(cx), int(cy)),
                           r + 4, 2)
        pygame.draw.circle(self.app.surface, glow, (int(cx), int(cy)), r)
        if spin and r > 14:
            prev_clip = self.app.surface.get_clip()
            self.app.surface.set_clip(pygame.Rect(int(cx - r), int(cy - r),
                                                  r * 2, r * 2))
            for k in range(3):
                phase = (t_now * 0.5 + k / 3.0) % 1.0
                ang = phase * 2 * math.pi
                mx = r * math.cos(ang)
                if abs(mx) >= r - 1:
                    continue
                mw = max(2, int(r * abs(math.sin(ang)) * 0.85))
                clip_h = int(2 * math.sqrt(max(0, r * r - mx * mx)))
                if clip_h < 2:
                    continue
                shade = 0.78 if math.cos(ang) > 0 else 1.16
                band = tuple(max(0, min(255, int(c * shade)))
                            for c in glow)
                pygame.draw.ellipse(self.app.surface, band,
                                   (int(cx + mx - mw / 2),
                                    int(cy - clip_h / 2), mw, clip_h))
            self.app.surface.set_clip(prev_clip)
        for k, (off, sz, add) in enumerate(((0.32, 0.42, 90),
                                            (0.15, 0.18, 140))):
            hi = tuple(min(255, c + add) for c in glow)
            pygame.draw.circle(self.app.surface, hi,
                               (int(cx - r * off), int(cy - r * off)),
                               max(2, int(r * sz) - k * 2))
        cos_a, sin_a, jit = self._sphere_jitter_data(seed)
        n_pts = 26
        pts = []
        for k in range(n_pts):
            rr = r + jit[k]
            pts.append((int(cx + rr * cos_a[k]),
                       int(cy + rr * sin_a[k])))
        pygame.draw.polygon(self.app.surface, INK, pts, 3)
        if selected:
            psize = max(64, int(r * 2.4))
        else:
            psize = max(28, int(r * 1.9))
        planet_img = self.app.nexus_planet_icon(icon_key, psize)
        if planet_img:
            self.app.surface.blit(planet_img,
                                  (int(cx - psize / 2), int(cy - psize / 2)))
        else:
            icons.draw(self.app.surface, icon_key, int(cx - r * 0.55),
                      int(cy - r * 0.55), max(10, int(r * 1.1)), INK)
        if moon is not None and not moon[0]:
            self._nexus_draw_moonlet(moon, col)

    def _nexus_dust_tone(self, col):
        sand = (150, 140, 122)
        return tuple(int(c * 0.5 + s * 0.5) for c, s in zip(col, sand))

    def _nexus_ring_surf(self, deco, r, col):
        kind, tilt, bands, dashed = deco
        cache = getattr(self.app, "_nexus_ring_cache", None)
        if cache is None:
            cache = {}
            self.app._nexus_ring_cache = cache
        r_key = max(4, (int(r) // 4) * 4)
        key = (kind, tilt, bands, dashed, r_key, col)
        surf = cache.get(key)
        if surf is not None:
            return surf
        squash = 0.34
        outer = max(6, int(r_key * 2.0))
        pad = 6
        size = outer * 2 + pad * 2
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        ccx = ccy = size // 2
        dust = self._nexus_dust_tone(col)
        widths = (outer, int(outer * 0.72)) if bands == 2 else (outer,)
        for rw in widths:
            rh = max(2, int(rw * squash))
            rect = pygame.Rect(ccx - rw, ccy - rh, rw * 2, rh * 2)
            if dashed:
                n = 20
                for k in range(0, n, 2):
                    a0 = math.radians(360.0 * k / n)
                    a1 = math.radians(360.0 * (k + 1) / n)
                    pygame.draw.arc(base, dust, rect, a0, a1, 3)
            else:
                pygame.draw.ellipse(base, (6, 7, 12), rect, 4)
                pygame.draw.ellipse(base, dust, rect.inflate(-3, -3), 2)
        rotated = pygame.transform.rotate(base, tilt)
        cache[key] = rotated
        return rotated

    def _nexus_moonlet_pos(self, cx, cy, r, t_now, seed):
        orb_r = r * 2.2
        ang = t_now * 0.6 + seed * 1.7
        mx = cx + orb_r * math.cos(ang)
        my = cy + orb_r * NEXUS_SQUASH * 1.4 * math.sin(ang)
        behind = math.sin(ang) < 0
        mr = max(2, int(r * 0.24))
        return behind, mx, my, mr

    def _nexus_draw_moonlet(self, moon, col):
        _behind, mx, my, mr = moon
        dust = self._nexus_dust_tone(col)
        glow = pygame.Surface((mr * 2 + 10, mr * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col, 60), (mr + 5, mr + 5), mr + 4)
        self.app.surface.blit(glow, (int(mx - mr - 5), int(my - mr - 5)))
        pygame.draw.circle(self.app.surface, (5, 6, 10), (int(mx), int(my)), mr + 1)
        pygame.draw.circle(self.app.surface, dust, (int(mx), int(my)), mr)
        pygame.draw.circle(self.app.surface, (255, 255, 255, 120), (int(mx - mr//3), int(my - mr//3)), max(1, mr//3))

    @staticmethod
    def _nexus_star_positions():
        # Con seed 77 le posizioni sono SEMPRE le stesse: le si generano
        # una sola volta (invece che a ogni rigenerazione della velatura)
        # perche' random.Random(77).randrange e' deterministico.
        pos = NexusRenderer._star_positions
        if pos is None:
            rnd = random.Random(77)
            pos = [(rnd.randrange(W), rnd.randrange(44, H))
                   for _ in range(140)]
            NexusRenderer._star_positions = pos
        return pos

    def _nexus_stars_surf(self):
        now = time.time()
        cached = getattr(self.app, "_nexus_star_cache", None)
        cached_t = getattr(self.app, "_nexus_star_cache_t", 0.0)
        # Rallentato a 0.5s: la fremitazione e' quasi percettibile a 0.2s
        # e cosi' si alloca 2x meno spesso una superficie W*H*4 byte.
        if cached is not None and now - cached_t < 0.5:
            return cached
        # Riutilizza la superficie esistente invece di ne allocarne una
        # nuova (evita churn di memoria su RAM stretta), svuotandola.
        if cached is None:
            surf = pygame.Surface((W, H), pygame.SRCALPHA)
        else:
            surf = cached
            surf.fill((0, 0, 0, 0))
        for i, (sx, sy) in enumerate(self._nexus_star_positions()):
            phase = (now * 0.5 + i * 0.37) % 4.0
            if phase > 2.6:
                continue
            tw = 0.3 + 0.7 * abs(math.sin(now * 1.3 + sx * 0.1))
            v = int(70 * tw)
            surf.set_at((sx, sy), (v, v, v + 22, 255))
        self.app._nexus_star_cache = surf
        self.app._nexus_star_cache_t = now
        return surf

    def _nexus_nebula_surf(self):
        col = NEXUS_NODE_COLOR.get(self.app.sel, self.app.accent)
        cache = getattr(self.app, "_nexus_neb_cache", None)
        cache_key = getattr(self.app, "_nexus_neb_cache_key", None)
        # La nebulosa e' statica per colore: non cambia col tempo, quindi
        # non va rigenerata ogni 0.5s. Si rigenera solo se il colore
        # cambia (sel/tema), evitando un'allocazione W*H*4 ogni mezzo
        # secondo in piu' per un handheld con 1GB di RAM.
        if cache is not None and cache_key == col:
            return cache
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, cy, maxr = NEXUS_SELECT_ZONE[0], NEXUS_SELECT_ZONE[1], 220
        for rr in range(maxr, 0, -6):
            a = int(14 * (1 - rr / float(maxr)) ** 1.6)
            if a > 0:
                pygame.draw.circle(surf, col + (a,), (cx, cy), rr)
        self.app._nexus_neb_cache = surf
        self.app._nexus_neb_cache_key = col
        return surf

    def _nexus_bg(self):
        surf = self.app.surface
        bg_cfg = self.app.cfg.get("nexus_bg", {})

        if bg_cfg.get("enabled", False) and bg_cfg.get("image_path"):
            try:
                img = pygame.image.load(bg_cfg["image_path"])
                scaled = pygame.transform.smoothscale(img, (W, H - 44))
                opacity = bg_cfg.get("opacity", 0.6)
                if opacity < 1.0:
                    scaled.set_alpha(int(opacity * 255))
                surf.blit(scaled, (0, 44))
            except Exception:
                pygame.draw.rect(surf, (4, 5, 10), (0, 44, W, H - 44))
        else:
            pygame.draw.rect(surf, (4, 5, 10), (0, 44, W, H - 44))

        t_now = time.time()
        stars_on = bg_cfg.get("stars", self.app.cfg.get("void_stars", True))
        if stars_on:
            surf.blit(self._nexus_stars_surf(), (0, 0))
        nebula_on = bg_cfg.get("nebula", self.app.cfg.get("void_nebula", True))
        if nebula_on:
            surf.blit(self._nexus_nebula_surf(), (0, 0))
        for gy in range(H - 90, H, 18):
            fade = (gy - (H - 90)) / 90.0
            col = (10, 12, 22 + int(20 * fade))
            pygame.draw.line(surf, col, (0, gy), (W, gy), 1)
        gseed = int(t_now * 3.7)
        grnd = random.Random(gseed)
        if grnd.random() < 0.10:
            gy2 = grnd.randrange(44, H - 6)
            gh = grnd.randrange(2, 6)
            shift = grnd.randrange(-14, 14)
            band = surf.subsurface((0, gy2, W, gh)).copy()
            surf.blit(band, (shift, gy2))
            gcol = self.app.accent if grnd.random() < 0.5 else (200, 60, 90)
            pygame.draw.line(surf, gcol, (0, gy2), (W, gy2), 1)
        glitch_on = bg_cfg.get("glitch", self.app.cfg.get("void_glitch", False))
        if glitch_on:
            self._apply_glitch(surf)
        comets_on = bg_cfg.get("comets", self.app.cfg.get("void_comets", True))
        if comets_on:
            self._draw_comets(surf)
        scanlines_on = bg_cfg.get("scanlines", False)
        if scanlines_on:
            line = pygame.Surface((W, 1), pygame.SRCALPHA)
            line.fill((0, 0, 0, 36))
            for y in range(0, H, 3):
                surf.blit(line, (0, y))
        vignette_on = bg_cfg.get("vignette", True)
        if vignette_on:
            fx = pygame.Surface((W, H), pygame.SRCALPHA)
            steps, th = 7, 9
            for i in range(steps):
                a = int(88 * ((steps - i) / float(steps)) ** 2.4)
                pygame.draw.rect(fx, (0, 0, 0, a),
                                 (i * th, i * th, W - 2 * i * th, H - 2 * i * th), th)
            surf.blit(fx, (0, 0))

    def _draw_comets(self, surf):
        if not hasattr(self.app, "_void_comets"):
            self.app._void_comets = []
            for _ in range(3):
                self.app._void_comets.append({
                    "x": random.randint(0, W),
                    "y": random.randint(44, H - 20),
                    "vx": random.uniform(1.5, 3.5),
                    "vy": random.uniform(-0.3, 0.3),
                    "life": random.uniform(0.3, 1.0),
                    "size": random.randint(1, 2),
                })
        for c in self.app._void_comets[:]:
            c["x"] += c["vx"]
            c["y"] += c["vy"]
            c["life"] -= 0.008
            if c["life"] <= 0 or c["x"] > W + 10 or c["y"] < 44 or c["y"] > H - 10:
                c["x"] = -10
                c["y"] = random.randint(44, H - 20)
                c["vx"] = random.uniform(1.5, 3.5)
                c["vy"] = random.uniform(-0.3, 0.3)
                c["life"] = random.uniform(0.3, 1.0)
            tail_len = 12
            for t in range(tail_len):
                a = int(180 * (1 - t / tail_len) * c["life"])
                tx = int(c["x"] - t * c["vx"] * 1.8)
                ty = int(c["y"] - t * c["vy"] * 1.8)
                if 0 <= tx < W and 0 <= ty < H:
                    s2 = pygame.Surface((6, 6), pygame.SRCALPHA)
                    pygame.draw.circle(s2, (180, 220, 255, a), (3, 3),
                                       max(1, c["size"] - t // 4))
                    surf.blit(s2, (tx - 3, ty - 3))

    def _apply_glitch(self, surf):
        if random.random() < 0.3:
            gy2 = random.randint(44, H - 6)
            gh = random.randint(2, 8)
            shift = random.randint(-18, 18)
            band = surf.subsurface((0, gy2, W, gh)).copy()
            surf.blit(band, (shift, gy2))
            gcol = random.choice([(200, 40, 60), (40, 200, 120), (160, 40, 200)])
            pygame.draw.line(surf, gcol, (0, gy2), (W, gy2), 2)

    def _draw_orbits(self, surf, color, width, style):
        rings = [NEXUS_RING_RADIUS[1], NEXUS_RING_RADIUS[2], NEXUS_RING_RADIUS[3]]
        cx, cy = NEXUS_SELECT_ZONE
        zoom = NEXUS_ZOOM.get(self.app.sel, 1.0)
        for rad in rings:
            rr = int(rad * zoom)
            if rr < 4:
                continue
            if style == "solid":
                pygame.draw.circle(surf, color, (cx, cy), rr, width)
            elif style == "dashed":
                for a in range(0, 360, 12):
                    a1 = math.radians(a)
                    a2 = math.radians(a + 6)
                    x1 = cx + rr * math.cos(a1)
                    y1 = cy + rr * math.sin(a1)
                    x2 = cx + rr * math.cos(a2)
                    y2 = cy + rr * math.sin(a2)
                    pygame.draw.line(surf, color, (int(x1), int(y1)), (int(x2), int(y2)), width)
            elif style == "glow":
                for w in range(width + 4, width - 1, -2):
                    alpha = 60 if w > width else 120
                    col = (*color, alpha)
                    pygame.draw.circle(surf, col, (cx, cy), rr + w - width, w)

    def _nexus_ring_list(self, ring):
        return (NEXUS_RING_INNER, NEXUS_RING_MID, NEXUS_RING_OUT,
                NEXUS_RING_FAR, NEXUS_RING_VOID)[ring]

    def _nexus_ring_step(self, ring):
        n = len(self._nexus_ring_list(ring))
        return 360.0 / n if n else 0.0

    def _nexus_ring_rot(self, ring):
        if ring == 1:
            return self.app.nexus_rot_mid
        if ring == 2:
            return self.app.nexus_rot_out
        if ring == 3:
            return self.app.nexus_rot_far
        if ring == 4:
            return self.app.nexus_rot_void
        return 0

    def _nexus_set_ring_rot(self, ring, rot):
        if ring == 1:
            self.app.nexus_rot_mid = rot
        elif ring == 2:
            self.app.nexus_rot_out = rot
        elif ring == 3:
            self.app.nexus_rot_far = rot
        elif ring == 4:
            self.app.nexus_rot_void = rot

    def _nexus_sync_sel(self):
        ring_list = self._nexus_ring_list(self.app.nexus_ring)
        if not ring_list:
            return
        rot = self._nexus_ring_rot(self.app.nexus_ring)
        self.app.sel = ring_list[rot % len(ring_list)]

    def _nexus_orbit_point(self, ring, angle_deg, radius):
        ang = math.radians(angle_deg)
        x = radius * math.cos(ang)
        y = radius * NEXUS_SQUASH * math.sin(ang)
        tilt = NEXUS_OUTER_TILT if ring == 2 else (
               NEXUS_FAR_TILT if ring == 3 else (
               NEXUS_VOID_TILT if ring == 4 else None))
        if tilt is not None:
            tr = math.radians(tilt)
            x, y = (x * math.cos(tr) - y * math.sin(tr),
                    x * math.sin(tr) + y * math.cos(tr))
        return x, y

    def _nexus_to_screen(self, wx, wy, sel_wx, sel_wy, zoom, anchor=None):
        ax, ay = anchor if anchor is not None else NEXUS_SELECT_ZONE
        sx = ax + (wx - sel_wx) * zoom
        sy = ay + (wy - sel_wy) * zoom
        return sx, sy

    def _nexus_select_zone_marker(self):
        x, y = NEXUS_SELECT_ZONE
        r = 8
        col = self.app.accent
        pygame.draw.circle(self.app.surface, col, (x, y), r, 1)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p0 = (x + dx * (r + 3), y + dy * (r + 3))
            p1 = (x + dx * (r + 8), y + dy * (r + 8))
            pygame.draw.line(self.app.surface, col, p0, p1, 1)

    def _nexus_dashed_ring(self, ring, r, active, sel_wx, sel_wy, zoom,
                           anchor=None, color=None, width=None, style=None):
        n_pts = 48
        pts = [self._nexus_to_screen(
                  *self._nexus_orbit_point(ring, 360.0 * k / n_pts, r),
                  sel_wx, sel_wy, zoom, anchor)
              for k in range(n_pts + 1)]
        minx = min(p[0] for p in pts)
        maxx = max(p[0] for p in pts)
        miny = min(p[1] for p in pts)
        maxy = max(p[1] for p in pts)
        pad = 4
        w = max(2, int(maxx - minx) + pad * 2)
        h = max(2, int(maxy - miny) + pad * 2)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        local = [(px - minx + pad, py - miny + pad) for px, py in pts]
        alpha = 110 if active else 55
        col = color if color is not None else (255, 255, 255)
        lw = width if width is not None else 1
        if style == "dashed":
            for i in range(0, len(local) - 1, 2):
                pygame.draw.line(surf, col + (alpha,), local[i], local[i + 1], lw)
        elif style == "glow":
            for gw in range(lw + 4, lw - 1, -2):
                a = 60 if gw > lw else 120
                pygame.draw.line(surf, col + (a,), local[0], local[-1], gw)
            pygame.draw.line(surf, col + (alpha,), local[0], local[-1], lw)
        else:
            pygame.draw.lines(surf, col + (alpha,), False, local, lw)
        self.app.surface.blit(surf, (minx - pad, miny - pad))

    def _nexus_world_angle(self, ring, i, t_now):
        step = self._nexus_ring_step(ring)
        drift = NEXUS_ORBIT_SPEED.get(ring, 0.0) * t_now
        return step * i + drift

    def _nexus_camera_target_pos(self, ring, i_frac, t_now):
        if ring == 0:
            return (0.0, 0.0)
        angle = self._nexus_world_angle(ring, i_frac, t_now)
        r = NEXUS_RING_RADIUS[ring]
        return self._nexus_orbit_point(ring, angle, r)

    def _nexus_draw_scene(self, sel_pos_override=None, zoom_override=None,
                          anchor_override=None):
        t_now = time.time()
        self._quality_trail, self._quality_particles = self._get_quality_level()
        low_quality = (self._quality_particles == 0)
        if sel_pos_override is not None:
            sel_wx, sel_wy = sel_pos_override
        else:
            sel_wx, sel_wy = self._nexus_camera_target_pos(
                self.app.nexus_ring, self._nexus_ring_rot(self.app.nexus_ring),
                t_now)
        zoom = (zoom_override if zoom_override is not None else
               NEXUS_ZOOM.get(self.app.sel, 1.0))
        bg_cfg = self.app.cfg.get("nexus_bg", {})
        o_color = bg_cfg.get("orbit_color")
        o_width = bg_cfg.get("orbit_width")
        o_style = bg_cfg.get("orbit_style")
        self._nexus_dashed_ring(1, NEXUS_RING_RADIUS[1],
                                self.app.nexus_ring == 1, sel_wx, sel_wy, zoom,
                                anchor_override, color=o_color, width=o_width, style=o_style)
        self._nexus_dashed_ring(2, NEXUS_RING_RADIUS[2],
                                self.app.nexus_ring == 2, sel_wx, sel_wy, zoom,
                                anchor_override, color=o_color, width=o_width, style=o_style)
        self._nexus_dashed_ring(3, NEXUS_RING_RADIUS[3],
                                self.app.nexus_ring == 3, sel_wx, sel_wy, zoom,
                                anchor_override, color=o_color, width=o_width, style=o_style)
        positions = {}
        for ring, ring_list in ((1, NEXUS_RING_MID), (2, NEXUS_RING_OUT),
                                (3, NEXUS_RING_FAR)):
            for i, idx in enumerate(ring_list):
                r_node = NEXUS_RING_RADIUS[ring]
                angle = self._nexus_world_angle(ring, i, t_now)
                wx, wy = self._nexus_orbit_point(ring, angle, r_node)
                sx, sy = self._nexus_to_screen(wx, wy, sel_wx, sel_wy,
                                               zoom, anchor_override)
                depth = (math.sin(math.radians(angle)) + 1) / 2
                positions[idx] = (sx, sy, depth)
        sun_sx, sun_sy = self._nexus_to_screen(0.0, 0.0, sel_wx, sel_wy,
                                                zoom, anchor_override)
        if self.app.cfg.get("void_gravity", True):
            gr = 28 + int(6 * math.sin(t_now * 1.4))
            for gy in range(3):
                a = int(22 * (1 - gy / 3.0))
                s = pygame.Surface((gr * 2 + gy * 16 + 4, gr * 2 + gy * 16 + 4),
                                   pygame.SRCALPHA)
                pygame.draw.circle(s, (40, 30, 60, a),
                                   (s.get_width() // 2, s.get_height() // 2),
                                   gr + gy * 8, 2)
                self.app.surface.blit(s, (int(sun_sx) - s.get_width() // 2,
                                          int(sun_sy) - s.get_height() // 2))
        order = sorted(positions.items(), key=lambda kv: kv[1][2])
        if self.app.cfg.get("void_trails", True):
            _ring_map = {}
            for _r, _rl in ((1, NEXUS_RING_MID), (2, NEXUS_RING_OUT), (3, NEXUS_RING_FAR)):
                for _i, _idx in enumerate(_rl):
                    _ring_map[_idx] = (_r, _i)
            trail_len = min(5, self._quality_trail)
            for idx, (sx, sy, depth) in order:
                if idx not in _ring_map:
                    continue
                ring, i_in_ring = _ring_map[idx]
                base_r = NEXUS_NODE_R.get(idx, 18)
                r = max(4, int(base_r * zoom * (0.75 + 0.32 * depth) *
                              (1.12 if idx == self.app.sel else 1.0)))
                raw_col = NEXUS_NODE_COLOR.get(idx, self.app.accent)
                shade = 0.60 + 0.40 * depth
                col = tuple(min(255, int(c * shade)) for c in raw_col)
                for t in range(trail_len):
                    ta = self._nexus_world_angle(ring, i_in_ring, t_now - t * 0.18)
                    r_node = NEXUS_RING_RADIUS[ring]
                    wx, wy = self._nexus_orbit_point(ring, ta, r_node)
                    tsx, tsy = self._nexus_to_screen(wx, wy, sel_wx, sel_wy,
                                                     zoom, anchor_override)
                    a = max(0, 80 - t * 18)
                    tr = max(1, r // 4)
                    s2 = pygame.Surface((tr * 2 + 2, tr * 2 + 2), pygame.SRCALPHA)
                    pygame.draw.circle(s2, col + (a,), (tr + 1, tr + 1), tr)
                    self.app.surface.blit(s2, (tsx - tr - 1, tsy - tr - 1))
        order = sorted(positions.items(), key=lambda kv: kv[1][2])
        for idx, (sx, sy, depth) in order:
            sel = (idx == self.app.sel)
            base_r = NEXUS_NODE_R.get(idx, 18)
            r = max(4, int(base_r * zoom * (0.75 + 0.32 * depth) *
                          (1.12 if sel else 1.0)))
            raw_col = NEXUS_NODE_COLOR.get(idx, self.app.accent)
            shade = 0.60 + 0.40 * depth
            col = tuple(min(255, int(c * shade)) for c in raw_col)
            if sel and not low_quality:
                halo_a = int(55 * (0.5 + 0.5 * math.sin(t_now * 3.0)))
                for gr in (r + 12, r + 5):
                    s = pygame.Surface((gr * 2 + 4, gr * 2 + 4),
                                       pygame.SRCALPHA)
                    pygame.draw.circle(s, col + (halo_a,),
                                       (gr + 2, gr + 2), gr)
                    self.app.surface.blit(s, (sx - gr - 2, sy - gr - 2))
            spin_speed = 0.28 + (idx * 37 % 97) / 97.0 * 0.8
            self._nexus_sphere(sx, sy, r, col, self.app.menu_icons[idx],
                               t_now * spin_speed, 0.15 if sel else 0.0,
                               spin=True, seed=idx, selected=sel, idx=idx)
            if sel:
                self.app.last_sel_rect = (sx - r, sy - r, r * 2, r * 2)
        self._nexus_sun(sun_sx, sun_sy, t_now, zoom)
        if anchor_override is None:
            self._nexus_select_zone_marker()
        return positions

    def _nexus_sun(self, cx, cy, t_now, zoom=1.0):
        col = NEXUS_NODE_COLOR.get(0, (255, 205, 120))
        sel = (self.app.sel == 0)
        r = max(6, int((46 if sel else 40) * zoom))
        pulse = 0.85 + 0.15 * math.sin(t_now * 1.3)
        glow = tuple(min(255, int(c * pulse)) for c in col)
        # glow costante estratto dal ciclo; 2 anelli invece di 3: l'anello
        # esterno piu' pallido (r+30, alpha 22) era quasi invisibile ma
        # costringeva l'allocazione di una superficie in piu a fotogrammo.
        # Su bassa qualita' (FPS < 20) si salta l'anello esterno per
        # risparmiare memoria su dispositivi con 1GB di RAM.
        low_quality = getattr(self, '_quality_particles', self.MAX_PARTICLES_PER_FRAME) == 0
        rings = ((r + 8, 58),) if low_quality else ((r + 18, 38), (r + 8, 58))
        for gr, a in rings:
            s = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, glow + (a,), (gr + 2, gr + 2), gr)
            self.app.surface.blit(s, (cx - gr - 2, cy - gr - 2))
        core = tuple(min(255, int(c * (pulse + 0.12))) for c in col)
        for k in range(10):
            fa = math.radians(k * 36 + t_now * 26)
            fl = r + 5 + int(6 * abs(math.sin(t_now * 2.2 + k)))
            pygame.draw.line(self.app.surface, core,
                            (cx + r * 0.82 * math.cos(fa),
                             cy + r * 0.82 * math.sin(fa)),
                            (cx + fl * math.cos(fa),
                             cy + fl * math.sin(fa)), 2)
        pygame.draw.circle(self.app.surface, core, (int(cx), int(cy)), r)
        hi = tuple(min(255, c + 60) for c in core)
        pygame.draw.circle(self.app.surface, hi,
                          (int(cx - r * 0.3), int(cy - r * 0.3)),
                          max(3, int(r * 0.3)))
        n_pts = 26
        pts = []
        cos_a, sin_a, jit = self._SUN_JITTER
        for k in range(n_pts):
            rr = r + jit[k]
            pts.append((int(cx + rr * cos_a[k]),
                       int(cy + rr * sin_a[k])))
        pygame.draw.polygon(self.app.surface, INK, pts, 3)
        sun_size = max(12, int(r * 1.3))
        sun_img = self.app.nexus_planet_icon(self.app.menu_icons[0], sun_size)
        if sun_img:
            self.app.surface.blit(sun_img, (int(cx - sun_size / 2),
                                            int(cy - sun_size / 2)))
        else:
            icons.draw(self.app.surface, self.app.menu_icons[0],
                      int(cx - r * 0.5), int(cy - r * 0.5),
                      max(10, int(r)), INK)
        if sel:
            self.app.last_sel_rect = (cx - r, cy - r, r * 2, r * 2)

    def _endnode_glitch_panel(self, x, y, w, h):
        rnd = random.Random(int(time.time() * 17) % 10000)
        intensity = 0.35
        n_slices = max(1, int(h * 0.2 * intensity))
        for _ in range(n_slices):
            sy = rnd.randrange(max(0, y), min(H, y + h))
            sh = rnd.randint(1, 3)
            if sy + sh > y + h:
                continue
            offset = rnd.randint(-5, 5)
            rect = (x, sy, w, sh)
            try:
                sub = self.app.surface.subsurface(rect).copy()
                self.app.surface.blit(sub, (x + offset, sy))
            except ValueError:
                continue
        if rnd.random() < 0.4 * intensity:
            for sy in range(max(0, y), min(H, y + h), 2):
                if rnd.random() < 0.08 * intensity:
                    rect = (x, sy, w, 1)
                    try:
                        sub = self.app.surface.subsurface(rect).copy()
                        self.app.surface.blit(sub, (x + rnd.randint(-2, 2), sy))
                    except ValueError:
                        continue

    def _glitch_text(self, text, font, color):
        surf = font.render(text, True, color)
        rnd = random.Random(int(time.time() * 31) % 10000)
        w, h = surf.get_size()
        n_slices = max(1, int(h * 0.25))
        for _ in range(n_slices):
            sy = rnd.randrange(0, h)
            sh = rnd.randint(1, 2)
            if sy + sh > h:
                continue
            offset = rnd.randint(-3, 3)
            rect = (0, sy, w, sh)
            try:
                sub = surf.subsurface(rect).copy()
                surf.blit(sub, (offset, sy))
            except ValueError:
                continue
        return surf

    def _nexus_format_code(self, raw_code):
        m = re.match(r'RAIL-(\d+)([α-ω]?)', raw_code)
        if not m:
            return raw_code
        num_str, greek = m.groups()
        num = int(num_str)
        if num == 999:
            num_str = "99"
        else:
            num_str = f"{num:02d}"
        if greek:
            return f"RAIL://{num_str}-{greek}"
        return f"RAIL://{num_str}"

    def _nexus_side_panels(self, bx0=360):
        idx = self.app.sel
        label, sub = self.app.menu[idx]
        col = NEXUS_NODE_COLOR.get(idx, self.app.accent)
        icon_key = self.app.menu_icons[idx]
        bx = bx0
        bw = max(140, W - bx - 14)
        by = 50
        box_h = 160
        is_endnode = (idx == 9)
        if is_endnode:
            box_h = 180
        self.app.npanel(bx, by, bw, box_h, border=col, fill=INK, cut=10)
        raw_code = NEXUS_NODE_CODE.get(idx, "RAIL-?α")
        code = self._nexus_format_code(raw_code)
        bkey = NEXUS_NODE_BADGE.get(idx)
        bimg = self.app.badge_img(bkey, 160) if bkey else None
        if bimg is not None:
            bw2, bh2 = bimg.get_size()
            maxw = bw - 20
            if bw2 > maxw:
                bh2 = max(8, int(bh2 * maxw / float(bw2)))
                bw2 = maxw
                bimg = pygame.transform.smoothscale(bimg, (bw2, bh2))
            self.app.surface.blit(bimg, (bx + (bw - bw2) // 2, by + 8))
            f_ox = getattr(self.app, "_f_ox_rail", None)
            if f_ox is None:
                f_ox = pygame.font.Font(FONT_MONO_PATH,
                                        self.app.f_small.get_height())
                self.app._f_ox_rail = f_ox
            cw = f_ox.size(code)[0]
            code_x = bx + bw - cw - 10
            code_y = by + box_h - 18
            if is_endnode:
                code_surf = self._glitch_text(code, f_ox, col)
                self.app.surface.blit(code_surf, (code_x, code_y))
            else:
                self.app.text(code, (code_x, code_y), f_ox, col)
        else:
            picon = self.app.nexus_planet_icon(icon_key, 44)
            text_x0 = bx + 12
            if picon:
                self.app.surface.blit(picon, (bx + 10, by + box_h // 2 - 22))
                text_x0 = bx + 10 + 44 + 10
            f_ox = getattr(self.app, "_f_ox_rail", None)
            if f_ox is None:
                f_ox = pygame.font.Font(FONT_MONO_PATH,
                                        self.app.f_small.get_height())
                self.app._f_ox_rail = f_ox
            code_x = text_x0
            code_y = by + 6
            if is_endnode:
                code_surf = self._glitch_text(code, f_ox, col)
                self.app.surface.blit(code_surf, (code_x, code_y))
            else:
                self.app.text(code, (code_x, code_y), f_ox, col)
            avail_w = max(20, bx + bw - 12 - text_x0)
            lw = self.app.f_med_b.size(label)[0]
            self.app.text(label, (text_x0 + max(0, (avail_w - lw) // 2),
                     by + box_h // 2 - 8), self.app.f_med_b, FG, maxw=avail_w)

        if is_endnode:
            self._endnode_glitch_panel(bx, by, bw, box_h)

        by2 = by + box_h + 28
        desc = HUB_DESCRIPTIONS.get(idx, {}).get(self.app.lang, "")
        if not desc:
            desc = sub
        desc = desc[:1].upper() + desc[1:] if desc else ""
        rows = self.app.note_wrap(desc, bw - 24, self.app.f_small, 4)
        line_h = 18
        ph = 30 + max(1, len(rows)) * line_h + 8
        self.app.npanel(bx, by2, bw, ph, border=col, fill=INK, cut=8)
        f_ox = getattr(self.app, "_f_ox_rail", None)
        if f_ox is None:
            f_ox = pygame.font.Font(FONT_MONO_PATH,
                                    self.app.f_small.get_height())
            self.app._f_ox_rail = f_ox
        title_text = "NODE REPORT"
        if is_endnode:
            title_surf = self._glitch_text(title_text, f_ox, col)
            self.app.surface.blit(title_surf, (bx + 12, by2 + 6))
        else:
            self.app.text(title_text, (bx + 12, by2 + 6), f_ox, col)
        ty = by2 + 30
        for row in rows:
            self.app.text(row, (bx + 12, ty), self.app.f_small,
                         (180, 185, 190), maxw=bw - 24)
            ty += line_h

    def _rtcarousel_glitch_transition(self):
        surf = self.app.surface
        W, H = surf.get_size()
        start = time.time()
        duration = 1.2
        base = surf.copy()
        self._rtcore_residue = base.copy()
        self._rtcore_residue_alpha = 1.0
        self._rtcore_residue_timer = time.time()
        while time.time() - start < duration:
            progress = (time.time() - start) / duration
            surf.blit(base, (0, 0))
            glitch_intensity = math.sin(progress * math.pi) * 1.2
            rnd = random.Random(int(time.time() * 1000))
            for _ in range(int(15 * glitch_intensity)):
                y = rnd.randint(0, H-1)
                h = rnd.randint(2, 8)
                dx = rnd.randint(-int(30*glitch_intensity), int(30*glitch_intensity))
                if y + h <= H:
                    band = base.subsurface((0, y, W, h)).copy()
                    surf.blit(band, (dx, y))
            for _ in range(int(8 * glitch_intensity)):
                x = rnd.randint(0, W-20)
                y = rnd.randint(0, H-20)
                w_block = rnd.randint(20, 60)
                h_block = rnd.randint(10, 30)
                if x + w_block <= W and y + h_block <= H:
                    block = base.subsurface((x, y, w_block, h_block)).copy()
                    for px in range(w_block):
                        for py in range(h_block):
                            c = block.get_at((px, py))
                            if c.a > 0:
                                block.set_at((px, py), (255-c[0], 255-c[1], 255-c[2], c.a))
                    surf.blit(block, (x + rnd.randint(-10, 10), y))
            if random.random() < 0.15 * glitch_intensity:
                flash = pygame.Surface((W, H), pygame.SRCALPHA)
                flash.fill((255, 255, 255, int(60 * glitch_intensity)))
                surf.blit(flash, (0, 0))
            pygame.display.flip()
            time.sleep(0.016)

    def _rtcarousel_draw_residue(self, surf):
        if self._rtcore_residue is None:
            return
        elapsed = time.time() - self._rtcore_residue_timer
        alpha = max(0, self._rtcore_residue_alpha * (1 - elapsed / 3.0))
        if alpha <= 0:
            self._rtcore_residue = None
            return
        residue = self._rtcore_residue.copy()
        residue.set_alpha(int(alpha * 150))
        dx = int(2 * math.sin(elapsed * 0.5))
        dy = int(2 * math.cos(elapsed * 0.3))
        surf.blit(residue, (dx, dy))
        if elapsed > 1.5:
            burn = pygame.Surface((W, H), pygame.SRCALPHA)
            burn.fill((0, 0, 0, int(200 * (elapsed - 1.5) / 1.5)))
            surf.blit(burn, (0, 0))
