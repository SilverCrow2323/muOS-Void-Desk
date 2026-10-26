#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VoidDesk on desktop (640x480 window, keyboard input).

    pip install pygame
    python3 desktop_run.py

On the device the app draws to /dev/fb0 and reads buttons from /dev/input (evdev).
Here we open a real SDL window and translate the keyboard into the same buttons.
No app file is modified: only the evinput module is patched in memory.

Keys:  arrows = D-pad      Z / Enter = A      X / Backspace = B
       A = Y               S = X              Q / W = L1 / R1     E / R = L2 / R2
       Tab = SELECT        Space = START      Esc / M = MENU      - / = = VOL- / VOL+
Env:   VD_VIDEO=x11|wayland|windows|cocoa  (SDL driver, per-platform default)
Notes: data (config, logs) goes to ./data like on the device. Features that rely on
muOS/embedded-Linux tools (amixer, nmcli, WiFi, Bluetooth...) will fail or do
nothing on a desktop: that is expected.
"""
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
os.environ["SDL_VIDEODRIVER"] = os.environ.get("VD_VIDEO") or {
    "win32": "windows", "darwin": "cocoa"}.get(sys.platform, "x11")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path[:0] = [os.path.join(APP, "desk"), APP]

import pygame  # noqa: E402

K = pygame
KEYS = {
    K.K_z: "A", K.K_RETURN: "A", K.K_x: "B", K.K_BACKSPACE: "B",
    K.K_a: "Y", K.K_s: "X", K.K_q: "L1", K.K_w: "R1", K.K_e: "L2", K.K_r: "R2",
    K.K_TAB: "SELECT", K.K_SPACE: "START", K.K_ESCAPE: "MENU", K.K_m: "MENU",
    K.K_MINUS: "VOL-", K.K_EQUALS: "VOL+",
}
RAW = {"A": 304, "B": 305, "Y": 306, "X": 307, "L1": 308, "R1": 309, "L2": 314,
       "R2": 315, "SELECT": 310, "START": 311, "MENU": 312, "VOL-": 114, "VOL+": 115}

_q, _held = [], set()


def install_keyboard_bridge():
    import evinput
    real_get = pygame.event.get

    def get(*a, **k):
        evs = real_get(*a, **k)
        for e in evs:
            if e.type == pygame.KEYDOWN:
                _held.add(e.key)
                if e.key in KEYS:
                    _q.append(KEYS[e.key])
            elif e.type == pygame.KEYUP:
                _held.discard(e.key)
        return evs

    pygame.event.get = get
    state = {"active": False, "raw": []}

    def start():
        state["active"] = True
        return True

    def stop():
        state["active"] = False

    def poll():
        out = _q[:]
        del _q[:]
        state["raw"] = [RAW[n] for n in out if n in RAW]
        return out

    def poll_raw():
        poll_names = poll()
        return [RAW[n] for n in poll_names if n in RAW]

    def hat():  # SDL convention: positive hy = up
        hx = (pygame.K_RIGHT in _held) - (pygame.K_LEFT in _held)
        hy = (pygame.K_UP in _held) - (pygame.K_DOWN in _held)
        return hx, hy

    evinput.start, evinput.stop, evinput.active = start, stop, lambda: state["active"]
    evinput.poll, evinput.poll_raw, evinput.hat = poll, poll_raw, hat


if __name__ == "__main__":
    install_keyboard_bridge()
    import importlib
    main = importlib.import_module("desk.main")
    sys.exit(main.App().run())
