# -*- coding: utf-8 -*-
# VOIDDESK // jsmap — corrispondenza evdev  <->  numero pulsante QJoyPad.
#
# QJoyPad legge /dev/input/js0, e il driver joydev del kernel numera i
# pulsanti cosi' (drivers/input/joydev.c):
#   prima i codici da BTN_JOYSTICK (0x120=288) a 0x13F (319), in ordine,
#   poi quelli da BTN_MISC (0x100=256) a 0x11F (287).
# Il numero "Button N" di QJoyPad e' indice_js + 1.
#
# Non tiriamo a indovinare: leggiamo la mappa dei tasti del device con
# ioctl EVIOCGBIT e replichiamo l'algoritmo. Se possibile confermiamo
# leggendo js0 mentre l'utente preme (verita' assoluta).

import fcntl
import os
import struct

EV_KEY = 0x01
EV_ABS = 0x03
KEY_MAX = 0x2FF
JS_EVENT_BUTTON = 0x01
JS_EVENT_INIT = 0x80
_JSEV = struct.calcsize("IhBB")


def _EVIOCGBIT(ev, length):
    # _IOC(_IOC_READ, 'E', 0x20 + ev, length)
    return (2 << 30) | (length << 16) | (0x45 << 8) | (0x20 + ev)


def _bits(fd, ev, maxbit):
    n = (maxbit + 7) // 8
    buf = bytearray(n)
    try:
        fcntl.ioctl(fd, _EVIOCGBIT(ev, n), buf)
    except OSError:
        return set()
    out = set()
    for i in range(maxbit):
        if buf[i >> 3] & (1 << (i & 7)):
            out.add(i)
    return out


def device_keys(path):
    """Codici tasto esposti da un event device (set), o set vuoto."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return set(), set()
    try:
        keys = _bits(fd, EV_KEY, KEY_MAX)
        axes = _bits(fd, EV_ABS, 0x40)
        return keys, axes
    finally:
        os.close(fd)


def find_pad():
    """Event device che fa da gamepad: quello con piu' pulsanti >= 288."""
    base = os.environ.get("VOIDCAST_INPUT_DIR",
                          os.environ.get("VOIDPAD_INPUT_DIR", "/dev/input"))
    best, best_n, best_keys = None, 0, set()
    try:
        names = sorted(n for n in os.listdir(base) if n.startswith("event"))
    except OSError:
        return None, set()
    for n in names:
        p = os.path.join(base, n)
        keys, _axes = device_keys(p)
        pad_keys = {k for k in keys if 256 <= k <= 319}
        if len(pad_keys) > best_n:
            best, best_n, best_keys = p, len(pad_keys), keys
    return best, best_keys


def js_order(keys=None):
    """dict: codice evdev -> indice js (come lo calcola joydev)."""
    if keys is None:
        _p, keys = find_pad()
    hi = sorted(k for k in keys if 288 <= k <= 319)
    lo = sorted(k for k in keys if 256 <= k <= 287)
    order = hi + lo
    return {code: i for i, code in enumerate(order)}


def ev_to_qj(keys=None):
    """dict: codice evdev -> numero 'Button N' di QJoyPad (1-based)."""
    return {c: i + 1 for c, i in js_order(keys).items()}


# ------------------------------------------------------- lettura da js0 ----
def js_open():
    for n in ("js0", "js1"):
        p = os.path.join(os.environ.get("VOIDCAST_JS_DIR", "/dev/input"), n)
        try:
            return os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
    return None


def js_poll(fd):
    """Numeri dei pulsanti js premuti adesso (verita' dal kernel)."""
    out = []
    if fd is None:
        return out
    while True:
        try:
            data = os.read(fd, _JSEV * 32)
        except (BlockingIOError, InterruptedError, OSError):
            break
        if not data:
            break
        for off in range(0, len(data) - _JSEV + 1, _JSEV):
            _t, value, etype, number = struct.unpack_from("IhBB", data, off)
            if etype & JS_EVENT_INIT:
                continue
            if (etype & JS_EVENT_BUTTON) and value == 1:
                out.append(number)
    return out


def js_close(fd):
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass
