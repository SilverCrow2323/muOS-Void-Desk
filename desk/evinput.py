# -*- coding: utf-8 -*-
# VOIDDESK/VOIDCAST // evinput — input diretto da /dev/input/event* (evdev).
#
# Un solo punto di lettura: poll() consuma gli eventi e aggiorna sia i nomi
# logici sia i codici grezzi (per la rimappatura) sia lo stato del dpad.
# poll_raw() NON legge per conto suo: si appoggia a poll(), cosi' non puo'
# rubare gli eventi agli altri (era il bug dei tasti morti nel menu).

import os
import struct

_EV_KEY = 1
_EV_ABS = 3
_EVSZ = struct.calcsize("llHHi")

KEYMAP_ANDROMEDA = {
    304: "A", 305: "B", 306: "Y", 307: "X",
    310: "L1", 311: "R1", 312: "L2", 313: "R2",
    314: "SELECT", 315: "START", 316: "MENU",
    114: "VOL-", 115: "VOL+",
}
KEYMAP_NON_ANDROMEDA = {
    304: "A", 305: "B", 307: "X", 308: "Y",
    310: "L1", 311: "R1", 312: "SELECT", 313: "L3",
    314: "R3", 315: "MENU", 316: "START",
    317: "L2", 318: "R2", 114: "VOL-", 115: "VOL+",
}

def detect_muos_release():
    value = os.environ.get("MUOS_VERSION", "")
    if not value:
        try:
            import subprocess
            value = subprocess.run(
                ["sh", "-c", '. /opt/muos/script/var/func.sh 2>/dev/null; GET_VAR system version 2>/dev/null'],
                capture_output=True, text=True, timeout=2).stdout.strip()
        except Exception:
            value = ""
    if not value:
        try:
            with open("/opt/muos/config/system/version") as stream:
                value = stream.readline().strip()
        except OSError:
            value = ""
    return "andromeda" if "andromeda" in value.lower() else "not_andromeda"

def resolve_profile(selection="auto"):
    selection = str(selection or "auto").lower()
    if selection == "auto":
        return detect_muos_release()
    return "andromeda" if selection == "andromeda" else "not_andromeda"

def set_profile(selection="auto"):
    global KEYMAP
    KEYMAP = dict(KEYMAP_ANDROMEDA if resolve_profile(selection) == "andromeda"
                  else KEYMAP_NON_ANDROMEDA)
    return resolve_profile(selection)



_state = {"fds": [], "hx": 0, "hy": 0, "active": False, "raw": []}
set_profile(os.environ.get("VOID_MUOS_PROFILE", "auto"))


def start():
    stop()
    fds = []
    base = os.environ.get("VOIDCAST_INPUT_DIR",
                          os.environ.get("VOIDPAD_INPUT_DIR", "/dev/input"))
    try:
        names = sorted(n for n in os.listdir(base) if n.startswith("event"))
    except OSError:
        names = []
    for n in names:
        try:
            fds.append(os.open(os.path.join(base, n),
                               os.O_RDONLY | os.O_NONBLOCK))
        except OSError:
            pass
    _state["fds"] = fds
    _state["active"] = bool(fds)
    _state["hx"] = _state["hy"] = 0
    _state["raw"] = []
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
    """Dpad come (hx, hy), convenzione SDL (hy positivo = su)."""
    return _state["hx"], -_state["hy"]


def poll():
    """Legge gli eventi: ritorna i tasti logici premuti e aggiorna lo
    stato del dpad e la lista dei codici grezzi."""
    out = []
    raw = []
    for fd in _state["fds"]:
        while True:
            try:
                data = os.read(fd, _EVSZ * 32)
            except (BlockingIOError, InterruptedError, OSError):
                break
            if not data:
                break
            for off in range(0, len(data) - _EVSZ + 1, _EVSZ):
                _s, _u, etype, code, value = struct.unpack_from(
                    "llHHi", data, off)
                if etype == _EV_KEY:
                    if value == 1:
                        raw.append(code)
                        if code in KEYMAP:
                            out.append(KEYMAP[code])
                elif etype == _EV_ABS:
                    if code == 16:
                        _state["hx"] = value
                    elif code == 17:
                        _state["hy"] = value
    _state["raw"] = raw
    return out


def poll_raw():
    """Codici grezzi premuti in questo giro (per la rimappatura).
    Si appoggia a poll(): non consuma eventi di nascosto."""
    poll()
    return _state["raw"]
