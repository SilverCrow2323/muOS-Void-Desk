# ============================================================================
#  VOID DESK — Audio Engine & SFX
#  Extracted from main.py section [G]
# ============================================================================
import pygame
import random
import math


class AudioEngine:
    """Sintetizzatore audio per Void-Desk: jingle d'avvio, SFX UI,
    suoni di ingresso hub. Zero asset esterni; se l'audio manca,
    silenzio e pace."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.sfx = None
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 256)
        except pygame.error:
            self.sfx = None
            return
        self._build_sfx()

    def _tone(self, f0, f1, ms, vol=0.30, noise=0.0, fm=None, fm_index=0.0, inharmonic=None):
        n = int(22050 * ms / 1000)
        buf = bytearray()
        ph = 0.0
        fm_ph = 0.0
        rnd = random.Random(3)
        inharmonic = inharmonic or []
        for i in range(n):
            t = i / float(n)
            freq = f0 + (f1 - f0) * t
            if fm is not None and fm_index > 0:
                fm_ph += 2 * math.pi * fm / 22050
                freq += fm_index * math.sin(fm_ph)
            ph += 2 * math.pi * freq / 22050
            v = math.sin(ph)
            for mul, amp in inharmonic:
                v += amp * math.sin(ph * mul)
            v = v / (1.0 + sum(amp for _, amp in inharmonic))
            if noise:
                v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
            env = min(1.0, i / 40.0) * (1 - t) ** 1.6
            smp = int(vol * env * 32767 * v)
            buf += smp.to_bytes(2, "little", signed=True)
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except pygame.error:
            return None

    def _build_sfx(self):
        try:
            self.sfx = {
                "open": self._tone(420, 980, 70),
                "back": self._tone(760, 320, 60),
                "move": self._tone(1240, 1240, 16, 0.16),
                "snap": self._tone(190, 130, 45, 0.34, 0.55),
                "click": self._tone(900, 500, 30, 0.20, 0.60),
                "off": self._tone(320, 38, 480, 0.42, 0.35),
                "nexus": self._tone(560, 1520, 110, 0.24, 0.10),
                "charge": self._tone(140, 640, 340, 0.22, 0.30),
                "charge2": self._tone(100, 420, 320, 0.22, 0.24),
                "charge3": self._tone(220, 820, 310, 0.22, 0.34),
                "charge4": self._tone(170, 540, 360, 0.20, 0.20),
                "lid_click": self._tone(200, 85, 90, 0.25, 0.45),
                "page_flip": self._tone(420, 950, 70, 0.16, 0.55),
                "media_vault_sword": self._tone(400, 1200, 80, vol=0.25, noise=0.2, fm=300, fm_index=5.0),
                "media_vault_flash": self._tone(800, 2000, 60, vol=0.4, noise=0.1, fm=500, fm_index=8.0),
                "media_vault_open": self._tone(200, 800, 120, vol=0.22, noise=0.20, inharmonic=[(2.1, 0.3), (3.5, 0.15)]),
            }
        except pygame.error:
            self.sfx = None

    def build_intro_jingle(self):
        """Il colpo sonoro sincronizzato con l'impatto del logo nella
        sigla d'avvio: una rincorsa che sale, poi un accordo pieno
        (due toni impilati + un pizzico di rumore per il punch) esatto
        nell'istante in cui compaiono anelli e scintille."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 256)
        except pygame.error:
            return None
        sr = 22050

        def synth(events):
            dur = max(t0 + d for t0, f0, f1, d, vol, noise in events)
            n = int(sr * dur)
            buf = [0.0] * n
            rnd = random.Random(11)
            for t0, f0, f1, d, vol, noise in events:
                i0, nn = int(t0 * sr), int(d * sr)
                ph = 0.0
                for i in range(nn):
                    if i0 + i >= n:
                        break
                    tt = i / float(nn)
                    ph += 2 * math.pi * (f0 + (f1 - f0) * tt) / sr
                    v = math.sin(ph)
                    if noise:
                        v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
                    env = min(1.0, i / 30.0) * (1 - tt) ** 1.8
                    buf[i0 + i] += vol * env * v
            raw = bytearray()
            for v in buf:
                s = max(-1.0, min(1.0, v))
                raw += int(s * 32767).to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(raw))
        try:
            return synth([
                (0.00, 500, 1400, 0.16, 0.22, 0.05),   # rincorsa che sale
                (0.16, 220, 210, 0.35, 0.34, 0.10),     # impatto: fondamentale
                (0.16, 440, 415, 0.30, 0.22, 0.10),     # impatto: ottava
                (0.16, 60, 55, 0.40, 0.30, 0.35),       # punch grave
            ])
        except pygame.error:
            return None

    def play(self, name):
        if self.sfx and self.cfg.get("sfx", True):
            try:
                self.sfx[name].play()
            except (KeyError, pygame.error):
                pass
