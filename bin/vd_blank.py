#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vd_blank.py — Schermata vuota (nera) da mostrare mentre un'app
outer-desk si sta avviando. Non blocca: gira in un processo
separato e viene ucciso dal chiamante quando l'app termina.
"""
import sys
import os
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_DIR = os.path.join(APP_DIR, "runtime")
DESK_DIR = os.path.join(APP_DIR, "desk")

sys.path.insert(0, RUNTIME_DIR)
sys.path.insert(0, DESK_DIR)

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import pygame
except ImportError:
    sys.exit(0)


def main():
    try:
        pygame.display.init()
        try:
            fbdisplay = __import__("fbdisplay")
            screen = pygame.display.set_mode((640, 480))
            fbdisplay.attach(screen)
        except Exception:
            screen = pygame.display.set_mode((640, 480), pygame.FULLSCREEN)
        screen.fill((0, 0, 0))
        pygame.display.flip()
        if len(sys.argv) > 1 and sys.argv[1]:
            logo_path = sys.argv[1]
            if os.path.exists(logo_path):
                try:
                    logo = pygame.image.load(logo_path).convert_alpha()
                    lw = min(120, logo.get_width())
                    lh = int(lw * logo.get_height() / logo.get_width())
                    logo = pygame.transform.smoothscale(logo, (lw, lh))
                    screen.blit(logo, ((640 - lw) // 2, (480 - lh) // 2))
                    pygame.display.flip()
                except Exception:
                    pass
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            time.sleep(0.5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
