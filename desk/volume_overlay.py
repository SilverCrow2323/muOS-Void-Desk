# -*- coding: utf-8 -*-
"""
Overlay volume per VoidDesk.
Riquadro semitrasparente con icona, barra orizzontale e percentuale.
"""

import time
import pygame

from desk.const import W, H
from desk import icons


class VolumeOverlay:
    def __init__(self, app):
        self.app = app
        self.visible = False
        self.alpha = 0
        self.timer = 0.0
        self.last_volume = 50

    def show(self, volume):
        self.last_volume = max(0, min(100, volume))
        self.visible = True
        self.timer = time.time()
        self.alpha = min(255, self.alpha + 40)

    def hide(self):
        self.visible = False
        self.alpha = 0

    def update(self):
        if not self.visible:
            return
        elapsed = time.time() - self.timer
        if elapsed > 1.5:
            self.alpha = max(0, self.alpha - 12)
            if self.alpha <= 0:
                self.hide()
        else:
            self.alpha = min(255, self.alpha + 20)

    def draw(self, surf):
        if not self.visible or self.alpha <= 0:
            return

        alpha = self.alpha
        vol = self.last_volume

        panel_w, panel_h = 220, 90
        panel_x = (W - panel_w) // 2
        panel_y = (H - panel_h) // 2 - 30

        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, int(200 * alpha / 255)))

        cut = 10
        pts = [(cut, 0), (panel_w - cut, 0), (panel_w, cut),
               (panel_w, panel_h - cut), (panel_w - cut, panel_h),
               (cut, panel_h), (0, panel_h - cut), (0, cut)]
        pygame.draw.polygon(s, (255, 255, 255, int(120 * alpha / 255)), pts, 2)
        pygame.draw.polygon(s, (self.app.accent[0], self.app.accent[1], self.app.accent[2], int(80 * alpha / 255)), pts, 1)

        icons.volume_icon(s, 20, 25, 40, vol, (255, 255, 255), (100, 100, 100))

        bar_x, bar_y = 80, 35
        bar_w, bar_h = 110, 14
        pygame.draw.rect(s, (30, 35, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        fill_w = int(bar_w * vol / 100)
        if fill_w > 0:
            if vol < 20:
                col = (255, 80, 80)
            elif vol < 60:
                col = (255, 200, 60)
            else:
                col = (60, 255, 110)
            pygame.draw.rect(s, (*col, alpha), (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        pygame.draw.rect(s, (200, 200, 200, int(120 * alpha / 255)), (bar_x, bar_y, bar_w, bar_h), 1)

        txt = "%d%%" % vol
        tw = self.app.f_med.size(txt)[0] if hasattr(self.app, "f_med") else 20
        self.app.text(txt, (bar_x + bar_w - tw - 4, bar_y - 2), s, self.app.f_med, (255, 255, 255))

        surf.blit(s, (panel_x, panel_y))
