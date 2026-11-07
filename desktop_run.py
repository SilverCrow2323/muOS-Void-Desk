#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VoidDesk on desktop (640x480 window, keyboard input).

On the device the app draws to /dev/fb0 and reads buttons from /dev/input
(evdev). Here we open a real SDL window and translate the keyboard into the
same buttons. No app file is modified: only evinput and fbdisplay are
patched in memory, and device-only actions (XFCE install/launch, apt, etc.)
are intercepted with a friendly message.

Keys:  arrows = D-pad      Z / Enter = A      X / Backspace = B
       A = Y               S = X              Q / W = L1 / R1
       E = L2              R = R2
       Tab = SELECT        Space = START      Esc / M = MENU
       - / = = VOL- / VOL+
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
    K.K_z: "A", K.K_RETURN: "A",
    K.K_x: "B", K.K_BACKSPACE: "B",
    K.K_a: "Y",
    K.K_s: "X",
    K.K_q: "L1", K.K_w: "R1",
    K.K_e: "L2", K.K_r: "R2",
    K.K_TAB: "SELECT",
    K.K_SPACE: "START",
    K.K_ESCAPE: "MENU", K.K_m: "MENU",
    K.K_MINUS: "VOL-", K.K_EQUALS: "VOL+",
}
RAW = {"A": 304, "B": 305, "Y": 306, "X": 307, "L1": 308, "R1": 309,
       "L2": 314, "R2": 315, "SELECT": 310, "START": 311, "MENU": 312,
       "VOL-": 114, "VOL+": 115}

_q = []
_held = set()


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

    def hat():
        hx = (pygame.K_RIGHT in _held) - (pygame.K_LEFT in _held)
        hy = (pygame.K_UP in _held) - (pygame.K_DOWN in _held)
        return hx, hy

    targets = [evinput]
    if "desk.evinput" in sys.modules:
        targets.append(sys.modules["desk.evinput"])
    try:
        import desk.evinput as _d
        if _d not in targets:
            targets.append(_d)
    except Exception:
        pass
    for m in targets:
        m.start = start
        m.stop = stop
        m.active = lambda: state["active"]
        m.poll = poll
        m.poll_raw = poll_raw
        m.hat = hat


def install_fbdisplay_bypass():
    """On desktop there is no /dev/fb0. desk/main.py calls fbdisplay.attach();
    if it returns False, the app prints 'fbdisplay not available'. We return
    True so the message is silenced and pygame's own flip() keeps working."""
    try:
        import fbdisplay as _fb
    except Exception:
        return

    _fb._orig_attach = getattr(_fb, "attach", None)
    _fb._orig_detach = getattr(_fb, "detach", None)

    def _noop_attach(surface=None):
        return True  # pretend success

    def _noop_detach():
        return None

    _fb.attach = _noop_attach
    _fb.detach = _noop_detach
    try:
        import desk.fbdisplay as _dfb
        if _dfb is not _fb:
            _dfb.attach = _noop_attach
            _dfb.detach = _noop_detach
    except Exception:
        pass


def install_render_flip_guard():
    import desk.main as m
    _orig_render = m.App.render

    def render_with_flip(self, *a, **k):
        result = _orig_render(self, *a, **k)
        try:
            pygame.display.flip()
        except Exception:
            pass
        return result

    m.App.render = render_with_flip


# Exit codes used by mux_launch.sh that mean "hand off to device-only script".
# On desktop there is no mux_launch.sh, so these would just exit the app.
DEVICE_ONLY = {
    11: "XFCE desktop launch requires the RG35XX-H handheld (arm64 + /dev/fb0).",
    12: "XFCE installation requires the RG35XX-H handheld (arm64 Ubuntu chroot).",
    13: "Package install requires the RG35XX-H handheld.",
    14: "Package removal requires the RG35XX-H handheld.",
    15: "System update requires the RG35XX-H handheld.",
    16: "muOS app launch requires the RG35XX-H handheld.",
    17: "Real terminal requires the RG35XX-H handheld.",
}


def install_device_only_guard():
    """Wrap App.run so exit codes 11-17 show a friendly notification and
    return to the menu instead of closing the app. Prevents the 'XFCE
    download crashes' behaviour on desktop."""
    import desk.main as m
    _orig_run = m.App.run

    def _guarded_run(self):
        while True:
            result = _orig_run(self)
            if result in DEVICE_ONLY:
                msg = DEVICE_ONLY[result]
                print(f"[desktop] blocked device-only action (rc={result}): {msg}",
                      flush=True)
                try:
                    self.notify("Desktop Mode", msg, "warning")
                except Exception as e:
                    print(f"[desktop] notify failed: {e}", flush=True)
                # Reset the app back to the main menu and keep running.
                try:
                    self.stack = ["menu"]
                except Exception:
                    pass
                self.running = True
                self.exit_code = 0
                continue
            return result

    m.App.run = _guarded_run


if __name__ == "__main__":
    install_keyboard_bridge()
    install_fbdisplay_bypass()
    import importlib
    main = importlib.import_module("desk.main")
    install_render_flip_guard()
    install_device_only_guard()
    sys.exit(main.App().run())
