#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  OUTERDESK INTRO — sigla per app standalone (stile console)
#  Effetto: macchinario principale che si separa da un modulo, rivelando
#  il logo dell'app con un portale energetico.
#
#  FIX: rilascio pulito del framebuffer prima del lancio del tool.
#       Usa fbdisplay.detach() e pygame.display.quit() per evitare
#       conflitti e flickering.
# =============================================================================
import os
import sys
import math
import random
import time
import subprocess
import argparse
import signal

# ---- PATH ----
VOIDDESK_BASE = None
for base in ("/mnt/mmc/MUOS/application/VoidDesk",
             "/mnt/sdcard/MUOS/application/VoidDesk"):
    if os.path.isdir(base):
        VOIDDESK_BASE = base
        break

if VOIDDESK_BASE is None:
    VOIDDESK_BASE = "/mnt/mmc/MUOS/application/VoidDesk"
    os.makedirs(VOIDDESK_BASE, exist_ok=True)

RUNTIME_DIR = os.path.join(VOIDDESK_BASE, "runtime")
ASSETS_DIR = os.path.join(VOIDDESK_BASE, "assets")
LOG_DIR = os.path.join(VOIDDESK_BASE, "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "outerdesk_launcher.log")

# ---- LOGGING ----
def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except:
        pass

log("=== OuterDesk Intro started ===")

# Aggiungi runtime al path
if os.path.isdir(RUNTIME_DIR):
    sys.path.insert(0, RUNTIME_DIR)
    for item in os.listdir(RUNTIME_DIR):
        sub = os.path.join(RUNTIME_DIR, item)
        if os.path.isdir(sub) and sub not in sys.path:
            sys.path.insert(0, sub)

# ---- IMPORTS ----
try:
    import pygame
except ImportError:
    log("ERRORE: pygame non trovato. Runtime mancante?")
    sys.exit(1)

try:
    import fbdisplay
    import evinput
except ImportError:
    log("fbdisplay o evinput non trovati, continuo senza.")
    fbdisplay = None
    evinput = None

# ---- COSTANTI ----
W, H = 640, 480
BG = (5, 5, 9)
ACCENT = (210, 165, 70)  # oro SPDW

# ---- FUNZIONI DI DISEGNO ----
def draw_portal(surface, cx, cy, radius, t, color=(180, 130, 255)):
    """Disegna un portale energetico con anelli che ruotano e pulsano."""
    for i in range(3):
        r = radius * (0.6 + 0.4 * math.sin(t * 2 + i * 1.2))
        alpha = int(80 + 120 * abs(math.sin(t * 1.5 + i)))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r, r), r, max(1, int(r*0.12)))
        pygame.draw.circle(s, (255,255,255, alpha//2), (r, r), r*0.3, 2)
        surface.blit(s, (cx - r, cy - r))
    # Raggi di luce
    for j in range(8):
        angle = t * 1.2 + j * math.pi/4
        length = radius * (0.5 + 0.5 * abs(math.sin(t * 2 + j)))
        x2 = cx + math.cos(angle) * length
        y2 = cy + math.sin(angle) * length
        alpha_ray = int(80 + 120 * abs(math.sin(t * 1.5 + j*0.5)))
        pygame.draw.line(surface, (*color, alpha_ray), (cx, cy), (x2, y2), 2)

def draw_separation_effect(surface, t):
    """Macchinario che si divide: due metà che si allontanano."""
    progress = min(1.0, t / 0.8)
    if progress >= 1.0:
        return 1.0
    offset = int(progress * 120)
    surface.fill(BG)
    pygame.draw.line(surface, ACCENT, (W//2, 0), (W//2, H), 3)
    for side in (-1, 1):
        cx = W//2 + side * offset
        r = 80
        if side == -1:
            rect = pygame.Rect(cx - r, H//2 - r, r, r*2)
        else:
            rect = pygame.Rect(cx, H//2 - r, r, r*2)
        pygame.draw.ellipse(surface, (180, 180, 200), rect, 3)
        for i in range(6):
            ang = math.radians(i * 60 + t * 30)
            x1 = cx + side * r * 0.8 * math.cos(ang)
            y1 = H//2 + r * 0.8 * math.sin(ang)
            x2 = cx + side * r * 1.1 * math.cos(ang)
            y2 = H//2 + r * 1.1 * math.sin(ang)
            pygame.draw.line(surface, (200, 200, 220), (x1, y1), (x2, y2), 2)
    return progress

# ---- RILASCIO PULITO DEL DISPLAY ----
def release_display():
    """Rilascia il framebuffer e pygame in modo pulito."""
    try:
        if fbdisplay is not None:
            fbdisplay.detach()
            log("fbdisplay.detach() chiamato")
    except Exception as e:
        log(f"fbdisplay.detach() fallito: {e}")
    try:
        pygame.display.quit()
        log("pygame.display.quit() chiamato")
    except Exception as e:
        log(f"pygame.display.quit() fallito: {e}")
    try:
        pygame.quit()
        log("pygame.quit() chiamato")
    except Exception as e:
        log(f"pygame.quit() fallito: {e}")

# ---- MAIN ----
def main():
    parser = argparse.ArgumentParser(description="OuterDesk Intro")
    parser.add_argument("--logo", required=True, help="Percorso del logo dell'app (PNG)")
    parser.add_argument("--name", required=True, help="Nome dell'app")
    parser.add_argument("--cmd", required=True, help="Comando da eseguire dopo l'intro")
    args = parser.parse_args()

    log(f"Lancio per: {args.name}")
    log(f"Comando: {args.cmd}")

    # ---- INIZIALIZZAZIONE DISPLAY ----
    # Usa il driver reale (framebuffer/SDL) se disponibile; dummy solo come
    # fallback assoluto. NON passare SDL_VIDEODRIVER=dummy al figlio.
    os.environ.pop("SDL_VIDEODRIVER", None)
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    
    try:
        pygame.display.init()
        pygame.font.init()
        # Fullscreen per prendere il framebuffer
        screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
        # Svuota subito lo schermo per evitare flickering
        screen.fill((0, 0, 0))
        pygame.display.flip()
        log("Display inizializzato")
    except Exception as e:
        log(f"ERRORE init display: {e}")
        # Fallback
        screen = pygame.display.set_mode((W, H))
        screen.fill((0, 0, 0))
        pygame.display.flip()

    # Attacca fbdisplay se disponibile
    if fbdisplay is not None:
        try:
            fbdisplay.attach(screen)
            log("fbdisplay attach OK")
        except Exception as e:
            log(f"fbdisplay attach fallito: {e}")

    # ---- SCHERMATA VUOTA (senza animazione che blocca) ----
    # Mostriamo subito uno schermo nero (con eventuale logo) e lanciamo
    # il tool figlio senza aspettare animazioni lunghe.
    try:
        font_path = os.path.join(VOIDDESK_BASE, "assets/fonts/DejaVuSans-Bold.ttf")
        try:
            font = pygame.font.Font(font_path, 38)
        except:
            font = pygame.font.Font(None, 38)

        logo_img = None
        try:
            logo_img = pygame.image.load(args.logo).convert_alpha()
            scale = min(1.0, 200 / max(logo_img.get_width(), logo_img.get_height()))
            new_w = int(logo_img.get_width() * scale)
            new_h = int(logo_img.get_height() * scale)
            logo_img = pygame.transform.smoothscale(logo_img, (new_w, new_h))
        except Exception as e:
            log(f"Logo non caricato: {e}")

        sfx_path = os.path.join(VOIDDESK_BASE, "assets/sfx/nexus_satellite.mp3")
        if os.path.exists(sfx_path):
            try:
                sound = pygame.mixer.Sound(sfx_path)
                sound.play()
            except:
                pass

        screen.fill(BG)
        if logo_img:
            lx = W // 2 - logo_img.get_width() // 2
            ly = H // 2 - logo_img.get_height() // 2 - 20
            screen.blit(logo_img, (lx, ly))
        name_surf = font.render(args.name, True, (255, 255, 255))
        screen.blit(name_surf, (W // 2 - name_surf.get_width() // 2, H // 2 + 60))
        sub_font = pygame.font.Font(None, 18)
        sub = sub_font.render("OuterDesk Module", True, (180, 180, 200))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 90))
        pygame.display.flip()
        log("Blank screen mostrato, lancio immediato del tool")
    except Exception as e:
        log(f"ERRORE blank screen: {e}")

    # ---- RILASCIO PULITO DEL DISPLAY ----
    release_display()
    log("Display rilasciato")

    # Piccola pausa per permettere al framebuffer di stabilizzarsi
    time.sleep(0.15)

    # ---- LANCIO DEL TOOL FIGLIO ----
    log(f"Lancio comando: {args.cmd}")
    try:
        cmd_parts = args.cmd.split()
        if cmd_parts:
            if cmd_parts[0] in ("python3", "python"):
                cmd_parts[0] = sys.executable
            # Environment pulito per il figlio: niente SDL_VIDEODRIVER=dummy,
            # aggiungi runtime a PYTHONPATH e LD_LIBRARY_PATH
            child_env = os.environ.copy()
            child_env.pop("SDL_VIDEODRIVER", None)
            runtime_dir = os.path.join(VOIDDESK_BASE, "runtime")
            child_env["PYTHONPATH"] = runtime_dir + os.pathsep + child_env.get("PYTHONPATH", "")
            child_env["LD_LIBRARY_PATH"] = runtime_dir + os.pathsep + child_env.get("LD_LIBRARY_PATH", "")
            proc = subprocess.Popen(cmd_parts, env=child_env)
            rc = proc.wait()
            log(f"Comando terminato con rc={rc}")
        else:
            log("ERRORE: comando vuoto")
    except Exception as e:
        log(f"ERRORE esecuzione comando: {e}")
        try:
            pygame.display.init()
            screen = pygame.display.set_mode((W, H))
            screen.fill((20, 0, 0))
            f_err = pygame.font.Font(None, 30)
            txt = f_err.render(f"ERRORE: {str(e)[:40]}", True, (255, 100, 100))
            screen.blit(txt, (20, 200))
            pygame.display.flip()
            time.sleep(4)
            pygame.quit()
        except:
            pass
        sys.exit(1)

    log("=== OuterDesk Intro terminato ===")
    sys.exit(0)

if __name__ == "__main__":
    main()