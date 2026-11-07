#!/usr/bin/env python3
# ============================================================================
#  VOID DESK — NEXUS SFX Generator
#  Generates weird, void-themed UI sounds as .wav files
#  for the NEXUS planetarium navigator.
# ============================================================================
import os
import math
import random
import struct
import wave

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(APP_DIR, "assets", "sfx")
SR = 22050


def _tone(f0, f1, ms, vol=0.30, noise=0.0, fm=0.0, fm_index=0.0,
          inharmonic=None, env_pow=1.6, attack=40):
    n = int(SR * ms / 1000)
    buf = bytearray()
    ph = 0.0
    ph_mod = 0.0
    rnd = random.Random(42)
    for i in range(n):
        t = i / float(n)
        freq = f0 + (f1 - f0) * t
        ph += 2 * math.pi * freq / SR
        v = math.sin(ph)
        if fm:
            ph_mod += 2 * math.pi * (fm + (fm * 0.5) * t) / SR
            v = math.sin(ph + fm_index * math.sin(ph_mod))
        if inharmonic:
            for ratio, amp in inharmonic:
                v += amp * math.sin(ph * ratio + t * 3.0)
            v /= 1.0 + sum(amp for _, amp in inharmonic)
        if noise:
            v = v * (1 - noise) + noise * (rnd.random() * 2 - 1)
        env = min(1.0, i / max(1, attack)) * (1 - t) ** env_pow
        smp = int(vol * env * 32767 * max(-1.0, min(1.0, v)))
        buf += struct.pack("<h", smp)
    return bytes(buf)


def _save(name, raw):
    path = os.path.join(OUT_DIR, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(raw)
    print(f"generated {path}")


def gen_nexus_dpad():
    raw = bytearray()
    raw += _tone(880, 440, 35, vol=0.22, noise=0.35,
                 fm=180, fm_index=3.5, env_pow=2.2, attack=8)
    raw += _tone(1200, 600, 25, vol=0.12, noise=0.20,
                 inharmonic=[(2.41, 0.3), (3.73, 0.15)], env_pow=3.0, attack=4)
    _save("dpad_nexus", bytes(raw))


def gen_nexus_switch():
    raw = bytearray()
    raw += _tone(220, 880, 70, vol=0.18, noise=0.08,
                 inharmonic=[(2.41, 0.4), (3.73, 0.3), (5.13, 0.15)],
                 env_pow=1.4, attack=6)
    raw += _tone(660, 440, 50, vol=0.10, noise=0.05,
                 fm=120, fm_index=2.0, env_pow=2.8, attack=10)
    _save("nexus_switch", bytes(raw))


def gen_nexus_select():
    raw = bytearray()
    raw += _tone(80, 120, 60, vol=0.20, noise=0.25, env_pow=1.2, attack=30)
    raw += _tone(120, 680, 100, vol=0.22, noise=0.12,
                 fm=55, fm_index=5.0, env_pow=1.8, attack=15)
    raw += _tone(680, 1200, 50, vol=0.10, noise=0.40, env_pow=4.0, attack=5)
    _save("nexus_select", bytes(raw))


def gen_nexus_exit():
    raw = _tone(900, 300, 45, vol=0.18, noise=0.30,
                fm=200, fm_index=2.5, env_pow=2.2, attack=5)
    _save("nexus_exit", bytes(raw))


def gen_nexus_hover():
    raw = _tone(1800, 2400, 18, vol=0.08, noise=0.15,
                fm=600, fm_index=1.5, env_pow=3.5, attack=2)
    _save("nexus_hover", bytes(raw))


def gen_dpad_menu():
    raw = bytearray()
    raw += _tone(1000, 700, 20, vol=0.14, noise=0.25,
                 fm=250, fm_index=2.0, env_pow=2.5, attack=3)
    raw += _tone(700, 500, 15, vol=0.08, noise=0.15, env_pow=3.0, attack=2)
    _save("dpad_menu", bytes(raw))


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_nexus_dpad()
    gen_nexus_switch()
    gen_nexus_select()
    gen_nexus_exit()
    gen_nexus_hover()
    gen_dpad_menu()
    print("done")
