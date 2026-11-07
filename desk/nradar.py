# ============================================================================
#  VOID DESK — N-RADAR Renderer
#  Vista 2D "radar" del planetario condiviso con NEXUS: stessa sorgente
#  dati (anelli, nodi, colori, satelliti, velocita'), ma proiezione
#  piatta dall'alto -- niente schiacciamento 3/4, niente inclinazione
#  delle orbite, niente profondita'. Eredita le MODIFICHE 2D fatte da
#  RADIX VERITAS (che muta i globali NEXUS_* letti da entrambe le viste);
#  le modifiche 3D (squash / tilt) non hanno effetto qui per natura 2D.
# ============================================================================
import math
import os
import re
import time
import pygame

from desk.const import (
    APP_DIR, NEXUS_NODE_DECO, NEXUS_RING_RADIUS, NEXUS_ORBIT_SPEED,
    NEXUS_RING_MID, NEXUS_RING_OUT, NEXUS_RING_FAR, NEXUS_RING_INNER,
    NEXUS_ZOOM, NEXUS_NODE_R, NEXUS_NODE_COLOR, NEXUS_SELECT_ZONE,
    NEXUS_NODE_BADGE, NEXUS_NODE_CODE, NEXUS_SATELLITES,
    NEXUS_SAT_ANCHOR, NEXUS_SAT_ZOOM_MULT, HUB_DESCRIPTIONS,
    FONT_MONO_PATH, FONT_PATH, INK, LINE, W, H, FAINT, FG, DIM, STEEL,
)


class NRadarRenderer:
    """N-RADAR: renderer 2D radar del planetario. Tutto in coordinate
    mondo (origine = SOLE) proiettate piatte sullo schermo."""

    _star_positions = None

    def __init__(self, app):
        self.app = app

    # --- helper mondo/schermo (proiezione 2D pura, senza squash/tilt) ---
    def _nscreen(self, wx, wy, sel_wx, sel_wy, zoom, anchor):
        ax, ay = anchor if anchor is not None else NEXUS_SELECT_ZONE
        return (ax + (wx - sel_wx) * zoom,
                ay + (wy - sel_wy) * zoom)

    def _nradar_ring_list(self, ring):
        return (NEXUS_RING_INNER, NEXUS_RING_MID, NEXUS_RING_OUT,
                NEXUS_RING_FAR)[ring]

    def _nradar_ring_step(self, ring):
        n = len(self._nradar_ring_list(ring))
        return 360.0 / n if n else 0.0

    def _nradar_ring_rot(self, ring):
        if ring == 1:
            return self.app.nradar_rot_mid
        if ring == 2:
            return self.app.nradar_rot_out
        if ring == 3:
            return self.app.nradar_rot_far
        return 0

    def _nradar_set_ring_rot(self, ring, rot):
        if ring == 1:
            self.app.nradar_rot_mid = rot
        elif ring == 2:
            self.app.nradar_rot_out = rot
        elif ring == 3:
            self.app.nradar_rot_far = rot

    def _nradar_sync_sel(self):
        ring_list = self._nradar_ring_list(self.app.nradar_ring)
        rot = self._nradar_ring_rot(self.app.nradar_ring)
        self.app.sel = ring_list[rot % len(ring_list)]

    def _nradar_world_angle(self, ring, i, t_now):
        step = self._nradar_ring_step(ring)
        drift = NEXUS_ORBIT_SPEED.get(ring, 0.0) * t_now
        return step * i + drift

    def _nradar_camera_target_pos(self, ring, i_frac, t_now):
        if ring == 0:
            return (0.0, 0.0)
        angle = self._nradar_world_angle(ring, i_frac, t_now)
        r = NEXUS_RING_RADIUS[ring]
        return (r * math.cos(math.radians(angle)),
                r * math.sin(math.radians(angle)))

    # --- formattazione codice RAIL (stesso di NEXUS) ---
    def _nradar_format_code(self, raw_code):
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

    # --- sfondo radar ---
    def _nradar_bg(self):
        surf = self.app.surface
        # riempimento solo sotto l'header (y=44) per non cancellarlo,
        # come fa il renderer NEXUS.
        surf.fill((3, 6, 9), (0, 44, W, H - 44))
        # vignettatura blu radiale leggera
        cx, cy = W // 2, H // 2
        for rr in range(260, 0, -20):
            a = int(5 * (1 - rr / 260.0))
            if a > 0:
                s = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (20, 60, 90, a), (rr, rr), rr)
                surf.blit(s, (cx - rr, cy - rr))
        self._draw_stars(time.time())

    @staticmethod
    def _nradar_star_positions():
        if NRadarRenderer._star_positions is None:
            import random
            rnd = random.Random(7)
            NRadarRenderer._star_positions = [
                (rnd.randrange(W), rnd.randrange(44, H)) for _ in range(70)]
        return NRadarRenderer._star_positions

    def _draw_stars(self, t_now):
        surf = self.app.surface
        for i, (sx, sy) in enumerate(self._nradar_star_positions()):
            tw = 0.3 + 0.7 * abs(math.sin(t_now * 1.1 + sx * 0.07))
            v = int(60 * tw)
            surf.set_at((sx, sy), (v, v, v + 20))

    # --- griglia radar + sweep ---
    def _draw_radar_grid(self, sun_sx, sun_sy, zoom, t_now, sweep_col):
        surf = self.app.surface
        rings = [NEXUS_RING_RADIUS[1], NEXUS_RING_RADIUS[2],
                 NEXUS_RING_RADIUS[3]]
        for ri, rad in enumerate(rings):
            rr = max(2, int(rad * zoom))
            pygame.draw.circle(surf, (40, 80, 70), (int(sun_sx), int(sun_sy)),
                               rr, 1)
            # tacche ogni 30 gradi
            for k in range(12):
                a = math.radians(30 * k)
                x0 = sun_sx + (rr - 4) * math.cos(a)
                y0 = sun_sy + (rr - 4) * math.sin(a)
                x1 = sun_sx + rr * math.cos(a)
                y1 = sun_sy + rr * math.sin(a)
                pygame.draw.line(surf, (30, 70, 60), (int(x0), int(y0)),
                                 (int(x1), int(y1)), 1)
        # raggi radiali
        for k in range(0, 360, 30):
            a = math.radians(k)
            x1 = sun_sx + rings[-1] * zoom * math.cos(a)
            y1 = sun_sy + rings[-1] * zoom * math.sin(a)
            pygame.draw.line(surf, (18, 40, 40), (int(sun_sx), int(sun_sy)),
                             (int(x1), int(y1)), 1)
        # sweep rotante
        sweep = (t_now * 0.9) % (2 * math.pi)
        sw_len = rings[-1] * zoom + 30
        grad = 26
        for g in range(grad):
            ga = sweep - g * 0.025
            alpha = int(70 * (1 - g / float(grad)))
            if alpha <= 0:
                continue
            x = sun_sx + sw_len * math.cos(ga)
            y = sun_sy + sw_len * math.sin(ga)
            col = (min(255, sweep_col[0]), min(255, sweep_col[1]),
                   min(255, sweep_col[2]))
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, col + (alpha,), (2, 2), 2)
            surf.blit(s, (int(x) - 2, int(y) - 2))
        # lama principale dello sweep
        x = sun_sx + sw_len * math.cos(sweep)
        y = sun_sy + sw_len * math.sin(sweep)
        pygame.draw.line(surf, sweep_col, (int(sun_sx), int(sun_sy)),
                         (int(x), int(y)), 2)
        return sweep

    # --- singolo nodo "blip" ---
    def _draw_blip(self, sx, sy, r, col, icon_key, t_now, selected,
                   sweep, world_angle, idx):
        surf = self.app.surface
        # differenza angolare con lo sweep -> "ping"
        da = abs((world_angle - sweep + math.pi) % (2 * math.pi) - math.pi)
        ping = max(0.0, 1.0 - da / 0.5)
        if ping > 0.02:
            pr = int(r + 6 + 22 * (1 - ping))
            a_ = int(150 * ping)
            s = pygame.Surface((pr * 2 + 4, pr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, col + (a_,), (pr + 2, pr + 2), pr, 2)
            surf.blit(s, (int(sx - pr - 2), int(sy - pr - 2)))
        # corpo
        pygame.draw.circle(surf, (6, 10, 12), (int(sx), int(sy)), r + 2)
        ring_col = col if selected else tuple(int(c * 0.8) for c in col)
        pygame.draw.circle(surf, ring_col, (int(sx), int(sy)), r, 2)
        # icona
        psize = max(8, int(r * 1.1))
        pimg = self.app.nexus_planet_icon(icon_key, int(psize * 1.6))
        if pimg:
            surf.blit(pimg, (int(sx - psize / 2), int(sy - psize / 2)))
        else:
            import icons
            icons.draw(surf, icon_key, int(sx - psize / 2),
                       int(sy - psize / 2), psize, col)
        if selected:
            # riticle a croce (mirino)
            half = r + 8
            for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                x0 = sx + dx * (r + 3)
                y0 = sy + dy * (r + 3)
                x1 = sx + dx * half
                y1 = sy + dy * half
                pygame.draw.line(surf, col, (int(x0), int(y0)),
                                 (int(x1), int(y1)), 2)
            pulse = 0.5 + 0.5 * math.sin(t_now * 3.0)
            s = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
            pygame.draw.circle(s, col + (int(60 * pulse),),
                               (r + 8, r + 8), r + 6, 1)
            surf.blit(s, (int(sx - r - 8), int(sy - r - 8)))

    def _draw_sun_core(self, sx, sy, t_now, zoom):
        surf = self.app.surface
        col = NEXUS_NODE_COLOR.get(0, (255, 205, 120))
        base = max(14, int(26 * zoom))
        for i in range(3, 0, -1):
            rr = base + i * 7
            a_ = int(40 * (0.5 + 0.5 * math.sin(t_now * 2 + i)))
            s = pygame.Surface((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, col + (a_,), (rr + 2, rr + 2), rr, 1)
            surf.blit(s, (int(sx - rr - 2), int(sy - rr - 2)))
        pulse = 0.85 + 0.15 * math.sin(t_now * 2.5)
        pygame.draw.circle(surf, tuple(int(c * pulse) for c in col),
                           (int(sx), int(sy)), base)
        pygame.draw.circle(surf, (255, 240, 200), (int(sx), int(sy)),
                           max(2, base // 3))
        # croce centrale
        for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            pygame.draw.line(surf, col,
                             (int(sx + dx * (base + 4)),
                              int(sy + dy * (base + 4))),
                             (int(sx + dx * (base + 12)),
                              int(sy + dy * (base + 12))), 2)

    def _nradar_select_zone_marker(self):
        surf = self.app.surface
        x, y = NEXUS_SELECT_ZONE
        r = 9
        col = self.app.accent
        pygame.draw.circle(surf, col, (x, y), r, 1)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p0 = (x + dx * (r + 3), y + dy * (r + 3))
            p1 = (x + dx * (r + 9), y + dy * (r + 9))
            pygame.draw.line(surf, col, p0, p1, 1)

    def _nradar_draw_scene(self, sel_pos_override=None, zoom_override=None,
                           anchor_override=None):
        t_now = time.time()
        app = self.app
        if sel_pos_override is not None:
            sel_wx, sel_wy = sel_pos_override
        else:
            sel_wx, sel_wy = self._nradar_camera_target_pos(
                app.nradar_ring, self._nradar_ring_rot(app.nradar_ring), t_now)
        zoom = (zoom_override if zoom_override is not None else
                NEXUS_ZOOM.get(app.sel, 1.0))
        anchor = anchor_override if anchor_override is not None else NEXUS_SELECT_ZONE

        # sole (origine) -> schermo
        sun_sx, sun_sy = self._nscreen(0.0, 0.0, sel_wx, sel_wy, zoom, anchor)
        sweep_col = NEXUS_NODE_COLOR.get(app.sel, app.accent)
        sweep = self._draw_radar_grid(sun_sx, sun_sy, zoom, t_now, sweep_col)

        positions = {}
        for ring, ring_list in ((1, NEXUS_RING_MID), (2, NEXUS_RING_OUT),
                                 (3, NEXUS_RING_FAR)):
            n = len(ring_list)
            for i, idx in enumerate(ring_list):
                angle = self._nradar_world_angle(ring, i, t_now)
                arad = math.radians(angle)
                wx = NEXUS_RING_RADIUS[ring] * math.cos(arad)
                wy = NEXUS_RING_RADIUS[ring] * math.sin(arad)
                sx, sy = self._nscreen(wx, wy, sel_wx, sel_wy, zoom, anchor)
                positions[idx] = (sx, sy, 1.0)
        # decori orbitali (lune) in 2D
        for ring, ring_list in ((1, NEXUS_RING_MID), (2, NEXUS_RING_OUT),
                                 (3, NEXUS_RING_FAR)):
            for i, idx in enumerate(ring_list):
                if idx == 9:
                    continue
                deco = NEXUS_NODE_DECO.get(idx)
                if not deco or deco[0] != "moonlet":
                    continue
                angle = self._nradar_world_angle(ring, i, t_now)
                arad = math.radians(angle)
                wx = NEXUS_RING_RADIUS[ring] * math.cos(arad)
                wy = NEXUS_RING_RADIUS[ring] * math.sin(arad)
                sx, sy = self._nscreen(wx, wy, sel_wx, sel_wy, zoom, anchor)
                orb_r = (NEXUS_NODE_R.get(idx, 16)) * zoom * 1.8
                ma = t_now * 0.6 + idx * 1.7
                mx = sx + orb_r * math.cos(ma)
                my = sy + orb_r * math.sin(ma)
                moon_col = (150, 140, 122)
                pygame.draw.circle(self.app.surface, moon_col,
                                   (int(mx), int(my)), 3)

        order = sorted(positions.items(), key=lambda kv: kv[0])
        for idx, (sx, sy, _depth) in order:
            sel = (idx == app.sel)
            r = max(5, int(NEXUS_NODE_R.get(idx, 16) * zoom * 1.15))
            col = NEXUS_NODE_COLOR.get(idx, app.accent)
            if idx == 9:
                col = (215, 80, 35)
            icon_key = app.menu_icons[idx]
            world_angle = math.atan2(sy - sun_sy, sx - sun_sx)
            world_angle = (math.degrees(world_angle)) % 360.0
            self._draw_blip(sx, sy, r, col, icon_key, t_now, sel,
                            math.degrees(sweep), world_angle, idx)
            if sel:
                app.last_sel_rect = (int(sx - r), int(sy - r), r * 2, r * 2)

        self._draw_sun_core(sun_sx, sun_sy, t_now, zoom)
        if anchor_override is None:
            self._nradar_select_zone_marker()
        return positions

    # --- pannello laterale NODE REPORT (specchio di NEXUS) ---
    def _nradar_side_panels(self, bx0=360):
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

        now = time.time()
        if self.app.nradar_report_target == 1:
            self.app.nradar_report_phase = min(
                1.0, self.app.nradar_report_phase + 0.04)
        else:
            self.app.nradar_report_phase = max(
                0.0, self.app.nradar_report_phase - 0.04)

        phase = self.app.nradar_report_phase
        if phase <= 0.0:
            return

        ease = 1 - (1 - phase) ** 3
        scale = 0.6 + 0.4 * ease
        alpha = int(255 * ease)

        sw = int(bw * scale)
        sh = int(box_h * scale)
        sx = bx + (bw - sw) // 2
        sy = by + (box_h - sh) // 2

        cut = 12
        pts = [
            (sx, sy), (sx + sw - cut, sy), (sx + sw, sy + cut),
            (sx + sw, sy + sh), (sx, sy + sh),
        ]
        bg_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        bg_surf.fill((*INK, int(200 * ease)))
        self.app.surface.blit(bg_surf, (sx, sy))

        glow_col = (*col, int(180 * ease))
        pygame.draw.polygon(self.app.surface, glow_col, pts, 2)
        for i in range(2, 0, -1):
            glow = pygame.Surface((sw + i * 4, sh + i * 4), pygame.SRCALPHA)
            glow_pts = [(i * 2, i * 2), (sw + i * 2 - cut, i * 2),
                       (sw + i * 2, i * 2 + cut), (sw + i * 2, sh + i * 2),
                       (i * 2, sh + i * 2)]
            pygame.draw.polygon(glow, (*col, int(40 * ease / i)),
                                glow_pts, 1)
            self.app.surface.blit(glow, (sx - i * 2, sy - i * 2))

        f_ox = getattr(self.app, "_f_ox_rail", None)
        if f_ox is None:
            f_ox = pygame.font.Font(FONT_MONO_PATH,
                                    self.app.f_small.get_height())
            self.app._f_ox_rail = f_ox

        title_text = "NODE REPORT"
        tw = f_ox.size(title_text)[0]
        title_x = sx + sw - tw - 12
        title_y = sy + 8
        shadow_surf = f_ox.render(title_text, True, (0, 0, 0))
        shadow_surf.set_alpha(alpha)
        self.app.surface.blit(shadow_surf, (title_x + 1, title_y + 1))
        title_surf = f_ox.render(title_text, True, col)
        title_surf.set_alpha(alpha)
        self.app.surface.blit(title_surf, (title_x, title_y))

        f_italic = pygame.font.Font(FONT_PATH, self.app.f_small.get_height())
        f_italic.set_italic(True)
        desc = HUB_DESCRIPTIONS.get(idx, {}).get(self.app.lang, "")
        if not desc:
            desc = sub
        desc = desc[:1].upper() + desc[1:] if desc else ""
        desc_lines = self.app.note_wrap(desc, sw - 24, f_italic, 4)
        line_h = 18
        yy = title_y + 22
        for line in desc_lines:
            ls = f_italic.render(line, True, (180, 185, 190))
            ls.set_alpha(alpha)
            self.app.surface.blit(ls, (sx + 12, yy))
            yy += line_h

        bkey = NEXUS_NODE_BADGE.get(idx)
        if bkey:
            bimg = self.app.badge_img(bkey, 48) if bkey else None
            if bimg is not None:
                bw2, bh2 = bimg.get_size()
                maxw = sw // 2 - 12
                if bw2 > maxw:
                    bh2 = max(8, int(bh2 * maxw / float(bw2)))
                    bw2 = maxw
                    bimg = pygame.transform.smoothscale(bimg, (bw2, bh2))
                self.app.surface.blit(bimg, (sx + 10, sy + 10))
        else:
            picon = self.app.nexus_planet_icon(icon_key, 44)
            if picon:
                self.app.surface.blit(picon, (sx + 10, sy + 10))

        led_x = sx + sw - 14
        led_y = sy + sh - 14
        pulse = 0.5 + 0.5 * math.sin(now * 4)
        pygame.draw.circle(self.app.surface, (10, 12, 16), (led_x, led_y), 6)
        pygame.draw.circle(self.app.surface, col, (led_x, led_y), 4)
        if phase > 0.8:
            glow_led = pygame.Surface((12, 12), pygame.SRCALPHA)
            glow_led.fill((*col, int(60 * pulse)))
            self.app.surface.blit(glow_led, (led_x - 6, led_y - 6))

        if phase > 0.9:
            for yy2 in range(sy + 4, sy + sh - 4, 3):
                self.app.surface.fill((0, 0, 0, 20), (sx + 4, yy2, sw - 8, 1))

        for (cx, cy, dx, dy) in [(sx, sy, 1, 1), (sx + sw, sy, -1, 1),
                                 (sx, sy + sh, 1, -1), (sx + sw, sy + sh, -1, -1)]:
            for i in range(0, 16, 4):
                pygame.draw.line(self.app.surface, col,
                                 (cx + i * dx, cy), (cx + (i + 2) * dx, cy + 2 * dy), 2)
                pygame.draw.line(self.app.surface, col,
                                 (cx, cy + i * dy), (cx + 2 * dx, cy + (i + 2) * dy), 2)

        self.app.last_sel_rect = (sx, sy, sw, sh)
