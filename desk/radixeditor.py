# -*- coding: utf-8 -*-
# ============================================================================
#  RADIX VERITAS – Nexus Editor (Enhanced)
#  Advanced tool per modificare il planetario Nexus: orbite, nodi, colori, 
#  satelliti e decorazioni. Le modifiche si riflettono in tempo reale.
#  Eseguito come overlay quando selezionato dal menu CURSEDEV.
# ============================================================================

import math
import random
import time
import pygame

from desk.const import (
    W, H, NEXUS_RING_MID, NEXUS_RING_OUT, NEXUS_RING_FAR,
    NEXUS_RING_RADIUS, NEXUS_SQUASH, NEXUS_NODE_COLOR,
    NEXUS_NODE_R, NEXUS_ZOOM, NEXUS_NODE_DECO, NEXUS_SATELLITES,
    NEXUS_ORBIT_SPEED, NEXUS_OUTER_TILT, NEXUS_FAR_TILT, BG, FAINT,
)
from desk import icons


class RadixEditor:
    """Editor avanzato del Nexus con preview in tempo reale."""

    def __init__(self, app):
        self.app = app
        self.surface = app.surface
        self.fonts = {
            "big": app.f_big,
            "big_b": app.f_big_b,
            "med": app.f_med,
            "small": app.f_small,
            "tiny": app.f_tiny,
            "mono": app.f_mono,
        }

        # Copia dei dati originali (modificabili)
        self.data = {
            "ring_radii": dict(NEXUS_RING_RADIUS),
            "node_radii": dict(NEXUS_NODE_R),
            "node_colors": dict(NEXUS_NODE_COLOR),
            "node_zoom": dict(NEXUS_ZOOM),
            "node_deco": dict(NEXUS_NODE_DECO),
            "satellites": {k: list(v) for k, v in NEXUS_SATELLITES.items()},
            "ring_speeds": dict(NEXUS_ORBIT_SPEED),
            "squash": NEXUS_SQUASH,
            "outer_tilt": NEXUS_OUTER_TILT,
            "far_tilt": NEXUS_FAR_TILT,
        }
        self.original_data = {
            k: v.copy() if isinstance(v, dict) else v
            for k, v in self.data.items()
        }

        # Stato dell'editor
        self.selected_node = 0
        self.edit_mode = "select"     # select, orbit, node, color, satellite
        self.show_help = False
        self.anim_time = 0.0
        self.ripples = []
        self.roots = []
        self.glow_timer = 0.0
        self.running = True
        self.scroll_offset = 0

        # Animazioni decorative
        self._generate_roots()
        self._init_particles()

    def _generate_roots(self):
        """Crea le radici decorative ai bordi dello schermo."""
        self.roots = []
        for _ in range(6):
            start_angle = random.uniform(0, 2 * math.pi)
            length = random.uniform(40, 100)
            thickness = random.uniform(1.5, 3)
            segments = random.randint(5, 10)
            points = []
            for i in range(segments + 1):
                t = i / segments
                angle = start_angle + t * random.uniform(0.3, 0.8)
                r = 5 + length * (t ** 0.8)
                x = W // 2 + r * math.cos(angle)
                y = H // 2 + r * math.sin(angle)
                points.append((int(x), int(y)))
            self.roots.append({
                "points": points,
                "thickness": thickness,
                "phase": random.uniform(0, 2 * math.pi),
                "grow": 0.0
            })

    def _init_particles(self):
        """Inizializza le particelle fluttuanti."""
        self.particles = []
        for _ in range(12):
            self.particles.append({
                "x": random.uniform(0, W),
                "y": random.uniform(0, H),
                "vx": random.uniform(-0.1, 0.1),
                "vy": random.uniform(-0.2, 0.1),
                "life": random.uniform(0.5, 3.0),
                "size": random.randint(1, 2)
            })

    def update(self, dt):
        """Aggiorna animazioni e stato."""
        self.anim_time += dt
        
        # Aggiorna crescita radici
        for root in self.roots:
            root["grow"] = min(1.0, root["grow"] + dt * 0.08)
        
        # Aggiorna particelle
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= dt * 0.2
            p["vy"] += dt * 0.05  # gravità leggera
            if p["life"] <= 0:
                p["x"] = random.uniform(0, W)
                p["y"] = -10
                p["life"] = random.uniform(2.0, 4.0)
        
        # Anelli d'acqua
        self.ripples = [r for r in self.ripples if r["life"] > 0]
        if random.random() < 0.02:
            self.ripples.append({
                "x": W // 2,
                "y": H // 2,
                "radius": 30,
                "life": 1.0,
                "speed": random.uniform(50, 100)
            })
        for r in self.ripples:
            r["radius"] += r["speed"] * dt
            r["life"] -= dt * 0.4
        
        # Glitch occasionale
        if random.random() < 0.01:
            self.glow_timer = 0.3

    def handle_button(self, btn):
        """Gestisce i pulsanti dell'editor."""
        if btn == "B":
            self.running = False
            self.app.play("back")
            return
        
        if btn == "A":
            if self.edit_mode == "select":
                self.edit_mode = "orbit"
                self.app.play("click")
            elif self.edit_mode == "orbit":
                self.edit_mode = "select"
                self.app.play("click")
            return
        
        if btn == "X":
            self.edit_mode = "satellite"
            self.app.play("click")
            return
        
        if btn == "Y":
            self._reset_all()
            return
        
        if btn == "SELECT":
            self.show_help = not self.show_help
            return
        
        # Navigazione nodi
        if btn == "UP":
            self.selected_node = (self.selected_node - 1) % 10
            self.app.play("move")
        elif btn == "DOWN":
            self.selected_node = (self.selected_node + 1) % 10
            self.app.play("move")
        
        # Modifica valori
        elif btn == "LEFT":
            if self.edit_mode == "orbit":
                self._adjust_ring_radius(-5)
                self.app.play("snap")
            elif self.edit_mode == "node":
                self._adjust_node_size(-1)
                self.app.play("snap")
        elif btn == "RIGHT":
            if self.edit_mode == "orbit":
                self._adjust_ring_radius(5)
                self.app.play("snap")
            elif self.edit_mode == "node":
                self._adjust_node_size(1)
                self.app.play("snap")
        
        # Cambia mode
        elif btn == "L1":
            self.edit_mode = "node"
            self.app.play("click")
        elif btn == "R1":
            self.edit_mode = "color"
            self.app.play("click")

    def _adjust_ring_radius(self, delta):
        """Modifica il raggio dell'orbita del nodo selezionato."""
        node_idx = self.selected_node
        ring = None
        for r, nodes in [(1, NEXUS_RING_MID), (2, NEXUS_RING_OUT), (3, NEXUS_RING_FAR)]:
            if node_idx in nodes:
                ring = r
                break
        
        if ring is None:
            return
        
        new_radius = self.data["ring_radii"][ring] + delta
        new_radius = max(80, min(450, new_radius))
        self.data["ring_radii"][ring] = new_radius
        NEXUS_RING_RADIUS[ring] = new_radius

    def _adjust_node_size(self, delta):
        """Modifica la dimensione del nodo."""
        node_idx = self.selected_node
        current = self.data["node_radii"].get(node_idx, 15)
        new_size = max(4, min(50, current + delta))
        self.data["node_radii"][node_idx] = new_size
        NEXUS_NODE_R[node_idx] = new_size

    def _reset_all(self):
        """Ripristina i valori originali."""
        self.data = {
            k: v.copy() if isinstance(v, dict) else v
            for k, v in self.original_data.items()
        }
        
        for ring, radius in self.data["ring_radii"].items():
            NEXUS_RING_RADIUS[ring] = radius
        for idx, r in self.data["node_radii"].items():
            NEXUS_NODE_R[idx] = r
        for idx, col in self.data["node_colors"].items():
            NEXUS_NODE_COLOR[idx] = col
        
        self.app.play("success")
        self.app.notify("NEXUS ripristinato", ok=False)

    def draw(self):
        """Disegna l'editor."""
        surf = self.surface
        now = time.time()
        self.update(1 / 30.0)

        # Sfondo
        surf.fill(BG)
        
        # Griglia animata
        self._draw_grid(surf, now)
        
        # Particelle fluttuanti
        for p in self.particles:
            if p["life"] > 0:
                col = (50 + int(40 * p["life"]), 100, 150)
                pygame.draw.circle(surf, col, (int(p["x"]), int(p["y"])), p["size"])
        
        # Glitch visivo
        if self.glow_timer > 0:
            for _ in range(3):
                y = random.randint(40, H - 40)
                h = random.randint(1, 2)
                off = random.randint(-4, 4)
                if y + h <= H:
                    band = surf.subsurface((0, y, W, h)).copy()
                    surf.blit(band, (off, y))
            self.glow_timer -= 1 / 30.0
        
        # Titolo
        self._draw_title(surf)
        
        # Area principale (mappa)
        self._draw_editor_panel(surf, now)
        
        # Info laterale
        self._draw_info_panel(surf)
        
        # Footer
        self._draw_footer(surf)

    def _draw_grid(self, surf, t):
        """Disegna una griglia animata sullo sfondo."""
        for i in range(0, W + 40, 40):
            offset = int(2 * math.sin(t * 0.3 + i * 0.01))
            pygame.draw.line(surf, (15, 20, 30), (i + offset, 0), (i + offset, H), 1)
        for j in range(0, H + 40, 40):
            offset = int(2 * math.sin(t * 0.25 + j * 0.015))
            pygame.draw.line(surf, (15, 20, 30), (0, j + offset), (W, j + offset), 1)

    def _draw_title(self, surf):
        """Disegna il titolo dell'editor."""
        title = "RADIX VERITAS"
        f = self.fonts["big_b"]
        img = f.render(title, True, (200, 150, 100))
        tw = img.get_width()
        
        # Glow attorno al titolo
        glow = pygame.Surface((tw + 20, img.get_height() + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow, (180, 100, 80, 80), (0, 0, glow.get_width(), glow.get_height()), border_radius=8)
        surf.blit(glow, (W // 2 - tw // 2 - 10, 16))
        surf.blit(img, (W // 2 - tw // 2, 20))

    def _draw_editor_panel(self, surf, t):
        """Disegna il pannello principale con l'anteprima della mappa."""
        panel_x, panel_y = 60, 70
        panel_w, panel_h = W - 120, 280
        
        # Bordo del pannello
        pygame.draw.rect(surf, (40, 60, 100, 100), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surf, (100, 150, 200, 150), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        # Area interna per la mappa
        map_x, map_y = panel_x + 12, panel_y + 12
        map_w, map_h = panel_w - 24, panel_h - 24
        
        # Clip region
        clip_rect = pygame.Rect(map_x, map_y, map_w, map_h)
        surf.set_clip(clip_rect)
        
        # Disegna la mappa del Nexus
        center_x = map_x + map_w // 2
        center_y = map_y + map_h // 2
        radius = min(map_w, map_h) // 2.5
        
        self._draw_nexus_map(surf, center_x, center_y, radius)
        
        surf.set_clip(None)

    def _draw_nexus_map(self, surf, cx, cy, radius):
        """Disegna la miniatura del Nexus."""
        ring_radii = self.data["ring_radii"]
        squash = self.data["squash"]
        
        # Orbite
        for ring in [1, 2, 3]:
            r = ring_radii.get(ring, 200) * (radius / 350)
            pts = []
            for i in range(36):
                a = i / 36 * 2 * math.pi
                x = cx + r * math.cos(a)
                y = cy + r * squash * math.sin(a)
                pts.append((int(x), int(y)))
            alpha = 60 if ring == 1 else 40
            pygame.draw.lines(surf, (120, 160, 200, alpha), pts + [pts[0]], 1)
        
        # Nodi
        node_list = []
        for ring, nodes in [(1, NEXUS_RING_MID), (2, NEXUS_RING_OUT), (3, NEXUS_RING_FAR)]:
            r = ring_radii.get(ring, 200) * (radius / 350)
            for i, idx in enumerate(nodes):
                angle = (i / len(nodes)) * 2 * math.pi
                x = cx + r * math.cos(angle)
                y = cy + r * squash * math.sin(angle)
                node_list.append((idx, int(x), int(y)))
        
        # Nodo centrale
        node_list.append((0, cx, cy))
        
        # Disegna i nodi
        for idx, x, y in node_list:
            is_sel = (idx == self.selected_node)
            col = self.data["node_colors"].get(idx, (180, 180, 180))
            r = self.data["node_radii"].get(idx, 15) * (radius / 350)
            r = max(3, int(r))
            
            if is_sel:
                pygame.draw.circle(surf, (255, 200, 100), (x, y), r + 4, 2)
            pygame.draw.circle(surf, col, (x, y), r)

    def _draw_info_panel(self, surf):
        """Disegna il pannello informazioni laterale."""
        info_x, info_y = 20, 370
        info_w, info_h = W - 40, H - 410
        
        pygame.draw.rect(surf, (20, 25, 35), (info_x, info_y, info_w, info_h), border_radius=6)
        pygame.draw.rect(surf, (80, 120, 160), (info_x, info_y, info_w, info_h), 1, border_radius=6)
        
        # Titolo informazioni
        self.app.text("SELEZIONE", (info_x + 12, info_y + 8),
                     self.fonts["small"], (200, 180, 140))
        
        # Nodo selezionato
        if self.selected_node < len(self.app.menu):
            node_name = self.app.menu[self.selected_node][0]
        else:
            node_name = f"Nodo {self.selected_node}"
        
        self.app.text(f"Nodo: {node_name}", (info_x + 12, info_y + 30),
                     self.fonts["tiny"], (180, 200, 220))
        
        # Modalità
        mode_str = self.edit_mode.upper()
        self.app.text(f"Modalità: {mode_str}", (info_x + 12, info_y + 46),
                     self.fonts["tiny"], (150, 200, 100))
        
        # Comandi disponibili
        y_cmd = info_y + 70
        commands = [
            ("UP/DN", "Seleziona nodo"),
            ("L/R", "Modifica valore"),
            ("A", "Orbita"),
            ("L1/R1", "Nodo/Colore"),
            ("X", "Satellite"),
            ("Y", "Reset"),
        ]
        
        for cmd, desc in commands:
            self.app.text(f"{cmd}: {desc}", (info_x + 12, y_cmd),
                         self.fonts["tiny"], (140, 150, 160))
            y_cmd += 14

    def _draw_footer(self, surf):
        """Disegna il footer."""
        pygame.draw.line(surf, (60, 80, 120), (0, H - 32), (W, H - 32), 1)
        pygame.draw.rect(surf, (5, 8, 15), (0, H - 32, W, 32))
        
        hints = [
            ("UP/DN", "select"),
            ("L/R", "modify"),
            ("A", "mode"),
            ("B", "back"),
        ]
        
        x = 12
        for key, label in hints:
            self.app.npanel(x, H - 28, 70, 24,
                           border=self.app.accent, fill=(10, 12, 20), cut=3)
            self.app.text(key, (x + 8, H - 24),
                         self.fonts["small"], self.app.accent)
            self.app.text(label, (x + 50, H - 24),
                         self.fonts["tiny"], (140, 150, 160))
            x += 85
