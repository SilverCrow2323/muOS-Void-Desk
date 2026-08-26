# -*- coding: utf-8 -*-
"""
UI componenti riutilizzabili per VoidDesk.
Contiene funzioni per disegnare pannelli, quadranti cyberpunk, badge, ecc.
"""

import random
import pygame

from desk.const import INK, FG, DIM, FAINT, W, H


def draw_cyber_quadrant(surf, rect, color, alpha=255, badge_img=None,
                        icon_key=None, title="", desc="", selected=False,
                        font_small=None, font_tiny=None, font_med=None):
    """
    Disegna un riquadro cyberpunk con bordo doppio (sottile colorato + spesso nero irregolare).
    """
    seed = hash((rect.x, rect.y, rect.w, rect.h)) % 10000
    rnd = random.Random(seed)

    irr_rect = rect.inflate(4, 4)
    pygame.draw.rect(surf, (0, 0, 0, int(200 * alpha / 255)), irr_rect,
                     max(2, int(4 * alpha / 255)), border_radius=2)

    fill = (8, 10, 16)
    surf.fill((*fill, int(220 * alpha / 255)), rect)

    if selected:
        glow = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
        glow.fill((*color, int(40 * alpha / 255)))
        surf.blit(glow, (rect.x - 4, rect.y - 4))
        pygame.draw.rect(surf, color, rect, 2)
        for cx, cy in [(rect.x, rect.y), (rect.right, rect.y),
                       (rect.x, rect.bottom), (rect.right, rect.bottom)]:
            pygame.draw.circle(surf, color, (cx, cy), 4)
    else:
        pygame.draw.rect(surf, (*color, int(180 * alpha / 255)), rect, 1)

    inner = rect.inflate(-6, -6)
    pygame.draw.rect(surf, (*color, int(60 * alpha / 255)), inner, 1)

    logo_size = min(rect.w, rect.h) // 2 - 10
    logo_y_offset = -10 if desc else 0

    if badge_img:
        angle = (rect.x // rect.w) * 5 - 2
        rotated = pygame.transform.rotate(badge_img, angle)
        rotated.set_alpha(alpha)
        surf.blit(rotated, rotated.get_rect(center=(rect.centerx, rect.centery + logo_y_offset)))
    elif icon_key and font_small:
        import icons
        icon_size = min(logo_size, 40)
        icons.draw(surf, icon_key, rect.centerx - icon_size // 2,
                   rect.centery - icon_size // 2 + logo_y_offset, icon_size,
                   color if selected else (150, 150, 160))
        if font_small:
            title_surf = font_small.render(title, True, (200, 200, 210) if selected else (150, 150, 160))
            tw = title_surf.get_width()
            surf.blit(title_surf, (rect.centerx - tw // 2, rect.centery + logo_size // 2 + 4 + logo_y_offset))

    if desc and font_tiny:
        tw = font_tiny.size(desc)[0]
        if tw > rect.w - 20:
            desc = desc[:int((rect.w - 30) / (font_tiny.size("A")[0]))] + "..."
        surf.blit(font_tiny.render(desc, True, (120, 130, 150)),
                  (rect.centerx - tw // 2, rect.bottom - 18))
