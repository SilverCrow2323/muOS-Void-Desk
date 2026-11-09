# outdesk/VoidCast/voidcast/core/evinput.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.evinput — input diretto da /dev/input/event* (evdev).
#
# Su muOS/RG35XX-H i tasti arrivano da un device "muOS-Keys" che il SDL
# del wheel pygame non vede come joystick: si legge l'evdev grezzo.
# Codici (verificati su RG35XX-H, stessi usati da PyLauncher):
#   EV_KEY: 304 A, 305 B, 306 Y, 307 X, 308 L1, 309 R1, 310 SELECT,
#           311 START, 312 MENU, 314 L2, 315 R2
#   EV_ABS: 16 = dpad X (-1/0/+1), 17 = dpad Y (-1/0/+1)

import os
import struct

_EV_KEY = 1
_EV_ABS = 3
_EVSZ = struct.calcsize("llHHi")  # 24 byte su 64 bit

KEYMAP = {
    304: "A", 305: "B", 306: "Y", 307: "X",
    308: "L1", 309: "R1", 314: "L2", 315: "R2",
    310: "SELECT", 311: "START", 312: "MENU",
    114: "VOL-", 115: "VOL+",
}

_state = {"fds": [], "hx": 0, "hy": 0, "active": False}


def start():
    """Apre tutti gli event device in non-blocking. True se almeno uno."""
    stop()
    fds = []
    base = os.environ.get("VOIDCAST_INPUT_DIR", "/dev/input")
    try:
        names = sorted(n for n in os.listdir(base)
                       if n.startswith("event"))
    except OSError:
        names = []
    for n in names:
        try:
            fd = os.open(os.path.join(base, n), os.O_RDONLY | os.O_NONBLOCK)
            fds.append(fd)
        except OSError:
            pass
    _state["fds"] = fds
    _state["active"] = bool(fds)
    _state["hx"] = _state["hy"] = 0
    return _state["active"]


def stop():
    for fd in _state["fds"]:
        try:
            os.close(fd)
        except OSError:
            pass
    _state["fds"] = []
    _state["active"] = False


def active():
    return _state["active"]


def hat():
    """Stato corrente del dpad come (hx, hy) in convenzione SDL
    (hy = +1 verso l'alto)."""
    return _state["hx"], -_state["hy"]


def poll():
    """Ritorna la lista dei bottoni logici PREMUTI dall'ultima chiamata.
    Aggiorna anche lo stato del dpad."""
    out = []
    for fd in _state["fds"]:
        while True:
            try:
                data = os.read(fd, _EVSZ * 32)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            if not data:
                break
            for off in range(0, len(data) - _EVSZ + 1, _EVSZ):
                _sec, _usec, etype, code, value = struct.unpack_from(
                    "llHHi", data, off)
                if etype == _EV_KEY:
                    if value == 1 and code in KEYMAP:
                        out.append(KEYMAP[code])
                elif etype == _EV_ABS:
                    if code == 16:
                        _state["hx"] = value
                    elif code == 17:
                        _state["hy"] = value
    return out

def sync_with_joystick(joystick_available):
    """Use raw muOS evdev only on framebuffer devices without SDL joystick."""
    if joystick_available or os.environ.get("VOIDCAST_FB") != "1":
        stop()
        return False
    return start()

