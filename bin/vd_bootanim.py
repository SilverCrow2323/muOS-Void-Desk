#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // vd_bootanim — sigla di avvio dedicata all'ambiente desktop.
#
#  Parte quando la barra di caricamento arriva in fondo, un attimo prima di
#  startx: ~2.6 secondi di puro framebuffer, marchio SPDW FACTORY ma ognuna
#  con l'anima del desktop che sta per aprirsi:
#
#    xfce   la megastruttura: nervature che convergono, il "muso" che si
#           materializza riga per riga tra ghost cromatici. Acciaio e ciano.
#    icewm  la velocita': speedline manga orizzontali, una scheggia di
#           ghiaccio che piomba in scena e vibra all'impatto. Ghiaccio.
#    lxde   la leggerezza: griglia di punti che sale, uno swoosh che
#           plana verso il centro lasciando la scia. Ambra calda.
#
#  uso: vd_bootanim.py <xfce|icewm|lxde>
# ============================================================================
import math
import os
import random
import subprocess
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP, "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbtext                                   # noqa: E402
from vd_loader import Painter, open_fb          # noqa: E402

BG = (5, 6, 9)
INK = (2, 2, 4)
LINE = (30, 34, 42)
FG = (233, 233, 226)

FPS_DT = 0.085
FRAMES = 30
HOLD = 0.55

# --- VOID DESK / PY-ENGINE -----------------------------------------------
# PY and LÖVE share one visual grammar, but are deliberately mirrored.
# PY: optical nucleus on the right, spiral expands left, cyan / glacier.
BG = (2, 5, 10)
INK = (0, 0, 0)
LINE = (13, 27, 38)
PY_ACCENT = (33, 211, 235)
PY_HOT = (139, 248, 255)
PY_MID = (18, 112, 137)
PY_DIM = (9, 49, 65)

FPS_DT = 0.075
FRAMES = 36
HOLD = 0.40


def segment(pt, x0, y0, x1, y1, col, width=2):
    """Linea DDA economica, con campioni ravvicinati e clipping del Painter."""
    dx, dy = x1 - x0, y1 - y0
    steps = max(1, int(max(abs(dx), abs(dy)) / 3.5))
    for i in range(steps + 1):
        q = i / float(steps)
        pt.fill(int(x0 + dx * q), int(y0 + dy * q), width, width, col)


def ring(pt, cx, cy, radius, col, width=2, squash=1.0):
    """Anello ellittico a segmenti: evita dipendenze grafiche esterne."""
    prev = None
    for i in range(97):
        a = (i / 96.0) * math.pi * 2.0
        p = (cx + math.cos(a) * radius,
             cy + math.sin(a) * radius * squash)
        if prev is not None:
            segment(pt, prev[0], prev[1], p[0], p[1], col, width)
        prev = p


def disc(pt, cx, cy, radius, col):
    """Disco pieno per il nucleo ottico nero."""
    for dy in range(-radius, radius + 1):
        half = int(math.sqrt(max(0, radius * radius - dy * dy)))
        pt.fill(cx - half, cy + dy, half * 2 + 1, 1, col)


def draw_reflection(pt, fb, now):
    """Quarto destro: riflesso verticale deformato, non un semplice pannello."""
    edge = int(fb.w * 0.75)
    pt.fill(edge, 0, fb.w - edge, fb.h, (3, 9, 16))
    for i in range(19):
        base = edge + i * max(1, (fb.w - edge) // 18)
        phase = i * 0.47
        for y in range(0, fb.h, 13):
            wave = math.sin(y * 0.031 + now * 2.1 + phase) * 7
            wave += math.sin(y * 0.012 - now * 1.3 + phase) * 4
            x = int(base + wave)
            col = PY_MID if i % 4 == 0 else (10, 42, 57)
            pt.fill(x, y, 1 if i % 3 else 2, 8, col)
    for y in range(20, fb.h, 31):
        shift = int(math.sin(y * 0.04 + now * 2.5) * 12)
        pt.fill(edge + shift, y, max(0, fb.w - edge - shift), 1, (8, 32, 44))
    pt.fill(edge, 0, 2, fb.h, (15, 79, 96))
    pt.fill(edge + 3, 0, 1, fb.h, (5, 27, 38))


def draw_spiral(pt, fb, now, extent):
    """Tre filamenti deformati si aprono dal nucleo destro verso i 3/4 sinistri."""
    cx, cy = int(fb.w * 0.82), fb.h // 2
    max_r = fb.w * 0.91
    turns = math.pi * 8.6
    strands = ((0.00, PY_ACCENT, 2), (0.15, PY_MID, 2),
               (-0.15, PY_HOT, 1))
    for phase, col, width in strands:
        prev = None
        for i in range(181):
            u = (i / 180.0) * extent
            radius = 9.0 + max_r * u
            angle = turns * u + phase + math.sin(u * 17.0 + now * 2.0) * 0.13
            warp = math.sin(angle * 1.9 - now * 3.2 + phase) * (3.0 + 19.0 * u)
            x = cx - (radius * math.cos(angle) + warp * 0.62)
            y = cy + radius * 0.64 * math.sin(angle) + warp
            if prev is not None:
                segment(pt, prev[0], prev[1], x, y, col, width)
            prev = (x, y)


def draw_core(pt, fb, now):
    """Il punto di origine resta nero, incastonato in riflessi e orbite."""
    cx, cy = int(fb.w * 0.82), fb.h // 2
    pulse = 1.0 + 0.035 * math.sin(now * 5.0)
    ring(pt, cx, cy, int(49 * pulse), PY_DIM, 2, 0.74)
    ring(pt, cx, cy, 39, PY_MID, 2, 0.74)
    ring(pt, cx, cy, 31, (5, 22, 31), 2, 0.74)
    disc(pt, cx, cy, 25, INK)
    ring(pt, cx, cy, 25, (1, 5, 9), 1, 0.74)
    pt.fill(cx - 2, cy - 37, 4, 10, PY_HOT)
    pt.fill(cx - 2, cy + 27, 4, 10, PY_ACCENT)


def draw_logo(pt, fb, env, now):
    """Tavola di marca leggibile sopra la spirale, nella regione sinistra."""
    panel_x = int(fb.w * 0.055)
    panel_y = int((fb.h - 154) / 2)
    panel_w, panel_h = int(fb.w * 0.64), 154
    pt.fill(panel_x, panel_y, panel_w, panel_h, (3, 10, 17))
    pt.frame(panel_x, panel_y, panel_w, panel_h, PY_MID, 2, cut=16)
    pt.fill(panel_x + 13, panel_y + 15, 3, panel_h - 30, PY_ACCENT)
    pt.fill(panel_x + 20, panel_y + 15, 1, panel_h - 30, (8, 53, 68))

    brand_y = (panel_y + 17) // fbtext.CH
    fb.text((panel_x + 31) // fbtext.CW, brand_y,
            "SPDW FACTORY", (115, 185, 197))
    fb.text((panel_x + 180) // fbtext.CW, brand_y,
            "// QWASAR ENV", PY_ACCENT)

    title_y = panel_y + 53
    pt.big_text(panel_x + 29, title_y + 2, "VOID DESK", (5, 20, 28), 3)
    pt.big_text(panel_x + 27, title_y, "VOID DESK", (237, 249, 250), 3)

    tag_x, tag_y = panel_x + 27, panel_y + 120
    pt.fill(tag_x, tag_y, 116, 23, (7, 36, 47))
    pt.frame(tag_x, tag_y, 116, 23, PY_ACCENT, 1)
    fb.text((tag_x + 10) // fbtext.CW, (tag_y + 2) // fbtext.CH,
            "PY-ENGINE", PY_HOT)
    target = ("TARGET // " + (env or "DESKTOP").upper())[:18]
    target_x = panel_x + panel_w - 13 - len(target) * fbtext.CW
    fb.text(target_x // fbtext.CW, (tag_y + 2) // fbtext.CH,
            target, (106, 151, 162))


def anim_void_engine(pt, fb, env):
    """Sigla PY definitiva: specchio a destra, nucleo nero, spirale verso sinistra."""
    t0 = time.time()
    for frame in range(FRAMES):
        now = time.time() - t0
        p = frame / float(max(1, FRAMES - 1))
        extent = p * p * (3.0 - 2.0 * p)
        fb.clear(BG)
        for x in range(18, int(fb.w * 0.75), 42):
            offset = int(math.sin(x * 0.025 + now) * 5)
            pt.fill(x + offset, 0, 1, fb.h, LINE)
        for y in range(34, fb.h, 48):
            pt.fill(0, y, int(fb.w * 0.75), 1, (7, 16, 25))

        draw_reflection(pt, fb, now)
        draw_spiral(pt, fb, now, extent)
        draw_core(pt, fb, now)
        for y in range(0, fb.h, 5):
            pt.fill(0, y, fb.w, 1, (1, 3, 6))
        draw_logo(pt, fb, env, now)
        fb.flush()
        time.sleep(FPS_DT)


# ------------------------------------------------------------- BGM -----
def bgm_log(msg):
    """Il chiamante rediriges gia' stdout su xfce_session.log: un print
    qui e' gia' un log persistente, niente di piu' da fare."""
    print("[vd_bootanim/bgm] " + msg)


def alsa_volume_hint():
    """Diagnostica extra, a costo quasi zero: se il mixer ALSA di
    sistema e' a 0 o mutato, tutto il resto di questo file puo'
    funzionare alla perfezione e restare comunque muto -- e' una causa
    molto comune, e da qui non potevamo vederla finche' non la
    controlliamo esplicitamente."""
    try:
        out = subprocess.run(["amixer", "get", "Master"],
                             capture_output=True, text=True,
                             timeout=3).stdout
        if out:
            bgm_log("amixer Master: " + " | ".join(
                ln.strip() for ln in out.splitlines()
                if "%" in ln or "[on]" in ln or "[off]" in ln))
    except Exception as e:
        bgm_log("amixer not available per la diagnostica: %s" % e)


def load_bgm(env):
    """Preferisce il file WAV vero in assets/bgm/<env>.wav — cosi'
    l'utente puo' sostituirlo col proprio (stesso nome) senza toccare
    codice. Se manca o e' illeggibile, ripiega sulla sintesi al volo
    (nessuna sigla resta mai muta per un file missing)."""
    if os.environ.get("VD_BGM_OFF"):
        bgm_log("disattivato da VD_BGM_OFF")
        return None
    try:
        import pygame
    except Exception as e:
        bgm_log("pygame non importabile: %s" % e)
        return None
    drv = os.environ.get("VD_BGM_DRIVER")
    if drv:
        os.environ["SDL_AUDIODRIVER"] = drv
    wav = os.environ.get("VD_BGM_WAV",
                         os.path.join(APP, "assets", "bgm",
                                      env + ".wav"))
    combos = [(44100, -16, 2, 1024), (44100, -16, 1, 1024),
              (22050, -16, 1, 512), (48000, -16, 2, 1024)]
    for freq, size, ch, buf_sz in combos:
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        try:
            pygame.mixer.init(freq, size, ch, buf_sz)
            bgm_log("mixer OK per file: %r driver=%s" %
                    ((freq, size, ch),
                     os.environ.get("SDL_AUDIODRIVER", "(default)")))
            break
        except Exception as e:
            bgm_log("mixer.init%r failed: %s" % ((freq, size, ch), e))
    else:
        bgm_log("nessun formato audio disponibile: silenzio")
        return None
    if os.path.exists(wav):
        try:
            return pygame.mixer.Sound(wav)
        except Exception as e:
            bgm_log("loading %s failed: %s -- ripiego su sintesi"
                    % (wav, e))
    else:
        bgm_log("%s missing -- ripiego su sintesi" % wav)
    return synth_bgm_pcm(env)


def synth_bgm_pcm(env):
    """Sintesi di riserva (usata solo se il WAV su disco manca o e'
    corrotto): stesso spartito di sempre, generato al volo sul mixer
    che load_bgm() ha gia' opened."""
    import math as m
    import random as r
    import pygame
    got = pygame.mixer.get_init()
    SR = got[0] if got else 44100
    N = int(SR * 3.0)
    buf = [0.0] * N

    def note(f, t0, dur, vol=0.22, atk=0.012, shine=True):
        i0 = int(t0 * SR)
        nn = int(dur * SR)
        for i in range(nn):
            if i0 + i >= N:
                break
            t = i / float(nn)
            env_ = min(1.0, (i / SR) / atk) * (1 - t) ** 2.2
            ph = 2 * m.pi * f * i / SR
            v = m.sin(ph)
            if shine:                      # armonica da campana
                v += 0.35 * m.sin(ph * 2.01) + 0.12 * m.sin(ph * 3.0)
            buf[i0 + i] += vol * env_ * v

    def whoosh(t0, dur, vol=0.20):
        i0 = int(t0 * SR)
        nn = int(dur * SR)
        rd = r.Random(5)
        lp = 0.0
        for i in range(nn):
            if i0 + i >= N:
                break
            t = i / float(nn)
            lp += 0.25 * ((rd.random() * 2 - 1) - lp)
            buf[i0 + i] += vol * (t ** 1.4) * lp * 3.0

    if env == "icewm":                    # velocita': scala che sfreccia
        for k, f in enumerate((392, 494, 587, 784, 988, 1175)):
            note(f, 0.14 + k * 0.09, 0.5, 0.20)
        whoosh(0.55, 0.5, 0.24)
        note(58, 1.02, 0.35, 0.30, atk=0.002, shine=False)   # impatto
        note(784, 1.55, 1.2, 0.16)
        note(1175, 1.62, 1.2, 0.12)
    elif env == "lxde":                   # leggerezza: triade calda
        for k, f in enumerate((262, 330, 392)):
            note(f, 0.18 + k * 0.30, 1.5, 0.18, atk=0.10)
        note(784, 1.55, 1.1, 0.10, atk=0.05)
        note(1046, 1.75, 1.0, 0.08, atk=0.05)
    else:                                 # xfce: megastruttura che si accende
        note(110, 0.0, 2.6, 0.14, atk=0.25, shine=False)     # pad basso
        for k, f in enumerate((330, 415, 494, 660)):
            note(f, 0.42 + k * 0.16, 0.9, 0.20)
        note(988, 1.55, 1.2, 0.14)

    D = int(0.18 * SR)                    # eco da sala giochi
    for i in range(D, N):
        buf[i] += buf[i - D] * 0.32
    raw = bytearray()
    for v in buf:
        s = max(-1.0, min(1.0, v * 0.8))
        raw += int(s * 32767).to_bytes(2, "little", signed=True)
    got = pygame.mixer.get_init()
    if got and got[2] == 2:               # il device vuole stereo:
        stereo = bytearray()              # duplico il canale mono
        for i in range(0, len(raw), 2):
            stereo += raw[i:i + 2] * 2
        raw = stereo
    try:
        return pygame.mixer.Sound(buffer=bytes(raw))
    except Exception as e:
        bgm_log("Sound(buffer=...) failed: %s" % e)
        return None


def main():
    env = (sys.argv[1] if len(sys.argv) > 1 else "xfce").lower()
    fb = open_fb()
    if not fb.ok:
        return 0
    pt = Painter(fb)
    bgm = load_bgm(env)
    if bgm:
        try:
            import pygame
            bgm.play()
            busy = pygame.mixer.get_busy()
            bgm_log("play() chiamato, get_busy()=%r" % busy)
        except Exception as e:
            bgm_log("play() failed: %s" % e)
        alsa_volume_hint()
    anim_void_engine(pt, fb, env)
    time.sleep(HOLD)
    if bgm:
        try:
            bgm.fadeout(220)
            time.sleep(0.24)
        except Exception:
            pass
        try:
            import pygame
            pygame.mixer.quit()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
