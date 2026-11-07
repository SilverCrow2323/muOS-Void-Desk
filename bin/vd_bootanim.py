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

# --- glifi 16x16 (bit piu' alto = colonna sinistra) -------------------------
MOUSE = [  # muso XFCE: corpo, muso a sinistra, orecchio, coda a destra
    0x0000, 0x0000, 0x0380, 0x0383,
    0x07E2, 0x1FF6, 0x3FFC, 0x7FFC,
    0x7FFC, 0x3FFC, 0x0FF8, 0x07F8,
    0x0780, 0x0000, 0x0000, 0x0000,
]
BOLT = [  # tre picchi montani IceWM, altezza decrescente
    0x0000, 0x0000, 0x0000, 0x0000,
    0x1800, 0x1840, 0x1840, 0x3CE0,
    0x3CE0, 0x3DFC, 0x7FFC, 0x7FFC,
    0x7FFE, 0xFFFE, 0xFFFF, 0x0000,
]
SWOOSH = [  # ala/swoosh LXDE, punta in alto, tre dita in basso
    0x0060, 0x00F0, 0x00F0, 0x00F8,
    0x01F8, 0x01F8, 0x01FC, 0x03FC,
    0x03FE, 0x07FE, 0x06FC, 0x04D8,
    0x0CB0, 0x09A0, 0x0100, 0x0000,
]


def glyph(pt, mask, x, y, sc, col, rows=16):
    """Disegna le prime `rows` righe del glifo, scalato a blocchi."""
    for ry in range(min(rows, 16)):
        bits = mask[ry]
        for rx in range(16):
            if bits & (1 << (15 - rx)):
                pt.fill(x + rx * sc, y + ry * sc, sc - 1, sc - 1, col)


def scanlines(pt, fb):
    for y in range(0, fb.h, 3):
        pt.fill(0, y, fb.w, 1, (0, 0, 0))


def frame_base(pt, fb):
    fb.clear(BG)
    pt.fill(0, 0, fb.w, 2, INK)
    pt.fill(0, fb.h - 2, fb.w, 2, INK)


SPDW_CORE = [   # ingranaggio: la firma SPDW per xfce/CORE (struttura)
    0x0000, 0x0000, 0x0180, 0x13C8,
    0x0FF0, 0x0FF0, 0x1C38, 0x3C3C,
    0x3C3C, 0x1C38, 0x0FF0, 0x0FF0,
    0x13C8, 0x0180, 0x0000, 0x0000,
]
SPDW_TURBO = [  # fulmine: la firma SPDW per icewm/TURBO (velocita')
    0x0070, 0x00E0, 0x00E0, 0x01E0,
    0x01C0, 0x03C0, 0x0780, 0x07F0,
    0x0FE0, 0x01C0, 0x0380, 0x0300,
    0x0600, 0x0C00, 0x0800, 0x1000,
]
SPDW_LIGHT = [  # foglia: la firma SPDW per lxde/LIGHT (leggerezza)
    0x0000, 0x0080, 0x01F0, 0x03FC,
    0x07F8, 0x0FF0, 0x1FE0, 0x1FE0,
    0x1FC0, 0x1F80, 0x3F00, 0x3C00,
    0x3000, 0x2000, 0x0000, 0x0000,
]
ENV_CODENAME = {"xfce": "CORE", "icewm": "TURBO", "lxde": "LIGHT"}


def signature(pt, fb):
    """SPDW Factory Lab, vicino al bordo superiore, centrata: la firma
    apre la scena invece di chiuderla in fondo."""
    sig = "SPDW Factory Lab"
    fb.text((fb.w // fbtext.CW - len(sig)) // 2, 2, sig, (100, 103, 110))


def title_row(pt, fb, env, name, col, f, reveal_start, reveal_frames):
    """Nome ambiente grande, centrato in basso. A sinistra non un
    doppione rimpicciolito del logo ufficiale (che sta gia' al centro
    scena) ma il marchio SPDW proprio di quell'ambiente -- ingranaggio,
    fulmine o foglia -- con sotto il nome in codice (CORE/TURBO/LIGHT).
    Ognuno prende forma in modo suo: CORE a blocchi che convergono dai
    bordi, TURBO con uno sweep fulmineo, LIGHT con una dissolvenza
    morbida (interpolazione colore, qui non c'e' alpha vero)."""
    p = max(0.0, min(1.0, (f - reveal_start) / float(reveal_frames)))
    if p <= 0:
        return
    mask = {"xfce": SPDW_CORE, "icewm": SPDW_TURBO,
            "lxde": SPDW_LIGHT}[env]
    sym_sc = 3
    sym_w = 16 * sym_sc + 16
    tw = len(name) * fbtext.CW * 3
    ty = fb.h - 132
    x0 = (fb.w - sym_w - tw) // 2
    sym_x, sym_y = x0, ty + 4
    if env == "xfce":
        rows = int(8 * min(1.0, p * 1.5))
        for ry in list(range(0, rows)) + list(range(16 - rows, 16)):
            bits = mask[ry]
            for rx in range(16):
                if bits & (1 << (15 - rx)):
                    pt.fill(sym_x + rx * sym_sc, sym_y + ry * sym_sc,
                           sym_sc - 1, sym_sc - 1, col)
    elif env == "icewm":
        # sweep orizzontale fulmineo: resta il piu' veloce dei tre (la
        # velocita' e' il punto), ma con vera progressione a colonne,
        # non un semplice on/off
        if p > 0.1:
            wp = min(1.0, (p - 0.1) / 0.3)
            cols = max(1, int(round(16 * wp)))
            for ry in range(16):
                bits = mask[ry]
                for rx in range(cols):
                    if bits & (1 << (15 - rx)):
                        pt.fill(sym_x + rx * sym_sc, sym_y + ry * sym_sc,
                               sym_sc - 1, sym_sc - 1, col)
    else:
        fade = min(1.0, p * 1.3)
        fc = tuple(int(c0 + (c1 - c0) * fade)
                  for c0, c1 in zip((10, 10, 12), col))
        glyph(pt, mask, sym_x, sym_y, sym_sc, fc)
    if p > 0.55:
        cp = min(1.0, (p - 0.55) / 0.45)
        code = ENV_CODENAME[env]
        chars = max(1, int(round(len(code) * cp)))
        fb.text((sym_x) // fbtext.CW,
                (sym_y + 16 * sym_sc + 3) // fbtext.CH,
                code[:chars], col)
    if p > 0.35:
        tp = min(1.0, (p - 0.35) / 0.65)
        chars = max(1, int(round(len(name) * tp)))
        shown = name[:chars]
        tx = x0 + sym_w
        pt.big_text(tx + 2, ty + 2, shown, INK, 3)
        pt.big_text(tx, ty, shown, col, 3)
    if p >= 0.99:
        signature(pt, fb)


# ---------------------------------------------------------------- XFCE -----
def anim_xfce(pt, fb):
    STEEL = (208, 214, 210)
    CYAN = (74, 206, 224)
    GR = (120, 30, 30)
    GC = (34, 120, 140)
    sc = 9
    gx = (fb.w - 16 * sc) // 2
    gy = 88
    rnd = random.Random(7)
    for f in range(FRAMES):
        frame_base(pt, fb)
        # nervature che convergono verso il centro
        k = 1.0 - f / float(FRAMES)
        for i in range(-5, 6):
            x = fb.w // 2 + int(i * (40 + 220 * k))
            pt.fill(x, 0, 1, fb.h, LINE)
        pt.fill(0, gy + 8 * sc, fb.w, 1, LINE)
        # il muso si materializza riga per riga, tra ghost cromatici
        rows = min(16, 2 + f)
        if f < FRAMES - 4:
            j = rnd.choice((-2, -1, 1, 2))
            glyph(pt, MOUSE, gx + j, gy, sc, GR, rows)
            glyph(pt, MOUSE, gx - j, gy + 1, sc, GC, rows)
        glyph(pt, MOUSE, gx, gy, sc, STEEL if f % 7 else CYAN, rows)
        # riga di scansione che "stampa" il glifo
        if rows < 16:
            pt.fill(gx - 26, gy + rows * sc, 16 * sc + 52, 2, CYAN)
        title_row(pt, fb, "xfce", "XFCE", STEEL, f, FRAMES - 14, 14)
        scanlines(pt, fb)
        fb.flush()
        time.sleep(FPS_DT)


# --------------------------------------------------------------- ICEWM -----
def anim_icewm(pt, fb):
    ICE = (190, 230, 245)
    BLU = (110, 195, 250)
    DEEP = (26, 52, 78)
    sc = 9
    gy = 96
    tx = (fb.w - 16 * sc) // 2
    rnd = random.Random(11)
    arrive = 12
    for f in range(FRAMES):
        frame_base(pt, fb)
        # speedline manga: trattini orizzontali che sfrecciano
        for _ in range(14):
            y = rnd.randrange(20, fb.h - 20)
            ln = rnd.randrange(60, 260)
            x = (rnd.randrange(fb.w) + f * 90) % (fb.w + ln) - ln
            pt.fill(x, y, ln, 2 if y % 3 else 1,
                    DEEP if y % 4 else (60, 110, 150))
        # la scheggia piomba da sinistra, overshoot e vibrazione
        if f < arrive:
            gx = int(-160 + (tx + 170) * (f / float(arrive)) ** 1.6)
        else:
            gx = tx + ((-3, 3, -2, 2, -1, 1)[f - arrive]
                       if f - arrive < 6 else 0)
        glyph(pt, BOLT, gx + 3, gy + 3, sc, DEEP)
        glyph(pt, BOLT, gx, gy, sc, ICE if f % 5 else BLU)
        if f == arrive:                      # flash d'impatto
            pt.fill(0, gy - 8, fb.w, 3, ICE)
            pt.fill(0, gy + 16 * sc, fb.w, 3, ICE)
        title_row(pt, fb, "icewm", "ICEWM", ICE, f, arrive + 2, 8)
        if f > arrive + 3:
            tag = "// TURBO"
            fb.text((fb.w // fbtext.CW - len(tag)) // 2,
                    (fb.h - 36) // fbtext.CH, tag, BLU)
        scanlines(pt, fb)
        fb.flush()
        time.sleep(FPS_DT)


# ---------------------------------------------------------------- LXDE -----
def anim_lxde(pt, fb):
    AMBER = (255, 176, 46)
    WARM = (255, 214, 130)
    DIMW = (120, 90, 40)
    sc = 8
    ex, ey = (fb.w - 16 * sc) // 2, 92
    for f in range(FRAMES):
        frame_base(pt, fb)
        # griglia di punti che sale, sempre piu' fitta: leggerezza
        off = (f * 5) % 26
        for gy in range(fb.h + 26, 40, -26):
            for gx in range(16, fb.w, 32):
                y = gy - off
                if 0 < y < fb.h:
                    pt.fill(gx, y, 2, 2,
                            LINE if (gx // 32 + gy // 26) % 3 else DIMW)
        # lo swoosh plana in diagonale verso il centro, con la scia
        t = min(1.0, f / float(FRAMES - 8))
        px = int(-140 + (ex + 140) * t)
        py = int(fb.h - 60 - (fb.h - 60 - ey) * t)
        for k, col in ((2, (60, 45, 22)), (1, DIMW)):
            glyph(pt, SWOOSH, px - k * 34, py + k * 22, sc, col)
        glyph(pt, SWOOSH, px, py, sc, AMBER if f % 6 else WARM)
        title_row(pt, fb, "lxde", "LXDE", AMBER, f, FRAMES - 12, 12)
        scanlines(pt, fb)
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
        bgm_log("amixer non disponibile per la diagnostica: %s" % e)


def load_bgm(env):
    """Preferisce il file WAV vero in assets/bgm/<env>.wav — cosi'
    l'utente puo' sostituirlo col proprio (stesso nome) senza toccare
    codice. Se manca o e' illeggibile, ripiega sulla sintesi al volo
    (nessuna sigla resta mai muta per un file assente)."""
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
            bgm_log("mixer.init%r fallito: %s" % ((freq, size, ch), e))
    else:
        bgm_log("nessun formato audio disponibile: silenzio")
        return None
    if os.path.exists(wav):
        try:
            return pygame.mixer.Sound(wav)
        except Exception as e:
            bgm_log("caricamento %s fallito: %s -- ripiego su sintesi"
                    % (wav, e))
    else:
        bgm_log("%s assente -- ripiego su sintesi" % wav)
    return synth_bgm_pcm(env)


def synth_bgm_pcm(env):
    """Sintesi di riserva (usata solo se il WAV su disco manca o e'
    corrotto): stesso spartito di sempre, generato al volo sul mixer
    che load_bgm() ha gia' aperto."""
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
        bgm_log("Sound(buffer=...) fallito: %s" % e)
        return None


ANIMS = {"xfce": anim_xfce, "icewm": anim_icewm, "lxde": anim_lxde}


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
            bgm_log("play() fallito: %s" % e)
        alsa_volume_hint()
    ANIMS.get(env, anim_xfce)(pt, fb)
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
