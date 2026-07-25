#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // gen_layout — genera il .lyt di QJoyPad per il profilo scelto,
# usando la numerazione REALE dei pulsanti (letta dal kernel via jsmap).
# uso: gen_layout.py <profilo> <file_destinazione>

import json
import os
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
sys.path.insert(0, os.path.join(APP, "desk"))
import jsmap  # noqa: E402

# nomi confermati sul pad muOS / RG35XX-H
KNOWN = {304: "A", 305: "B", 306: "Y", 307: "X", 308: "L1", 309: "R1",
         310: "SELECT", 311: "START", 312: "MENU", 314: "L2", 315: "R2"}
EXTRA_ORDER = ["L3", "R3"]      # nomi per i codici extra, in ordine

# azioni QJoyPad
ACT = {
    "click_l": "mouse 1", "click_r": "mouse 3", "click_m": "mouse 2",
    "wheel_up": "mouse 4", "wheel_dn": "mouse 5",
    "back": "key 166", "enter": "key 36", "esc": "key 9",
    "kbd": None,                # gestita dal watcher VoidDesk, non da QJoyPad
}


def names_map(keys):
    """codice evdev -> nome leggibile (A, B, L3, ...)."""
    out = dict(KNOWN)
    extra = sorted(k for k in keys if 256 <= k <= 319 and k not in KNOWN)
    for i, code in enumerate(extra):
        out[code] = EXTRA_ORDER[i] if i < len(EXTRA_ORDER) else "B%d" % code
    return out


def default_map(keys):
    """funzione -> lista di codici evdev (con L3/R3 se il pad li ha)."""
    nm = names_map(keys)
    by_name = {v: k for k, v in nm.items()}
    m = {
        "click_l": [c for c in (by_name.get("A"), by_name.get("L3")) if c],
        "click_r": [c for c in (by_name.get("X"), by_name.get("R3")) if c],
        "click_m": [c for c in (by_name.get("Y"),) if c],
        "wheel_up": [c for c in (by_name.get("R1"),) if c],
        "wheel_dn": [c for c in (by_name.get("L1"),) if c],
        "back": [c for c in (by_name.get("B"),) if c],
        "enter": [c for c in (by_name.get("START"),) if c],
        "esc": [c for c in (by_name.get("SELECT"),) if c],
        "kbd": [c for c in (by_name.get("MENU"),) if c],
    }
    return m


def load_cfg():
    try:
        return json.load(open(os.path.join(DATA, "desk_config.json")))
    except Exception:
        return {}


def qj_of(ev, computed, learned):
    """Numero Button: prima quello imparato dal vero js0, poi il calcolo."""
    v = learned.get(str(ev))
    if isinstance(v, int) and v > 0:
        return v
    return computed.get(ev)


def build(profile, cfg, keys):
    computed = jsmap.ev_to_qj(keys)
    learned = cfg.get("qj_map", {})
    if profile == "custom" and cfg.get("map"):
        m = cfg["map"]
        stick = cfg.get("mouse_stick", "sinistro")
    else:
        m = default_map(keys)
        stick = "destro" if profile == "classico" else "sinistro"

    out = ["# QJoyPad 4.3 Layout File",
           "# VOIDDESK - profilo %s (numeri pulsante letti dal kernel)"
           % profile, "Joystick 1 {"]
    if profile == "terminale":
        # niente mouse: qui serve solo una tastiera seria. Sinistro e
        # dpad restano frecce (navigano la tastiera a schermo); il
        # destro scorre lo storico del terminale (Prior/Next), xterm
        # e' configurato per accettarli senza bisogno di Shift.
        out += ["\tAxis 1: gradient, +key 114, -key 113",
                "\tAxis 2: gradient, +key 116, -key 111",
                "\tAxis 3: gradient, +key 117, -key 112",
                "\tAxis 4: gradient, +key 117, -key 112"]
    elif stick == "sinistro":
        out += ["\tAxis 1: gradient, maxSpeed 3, mouse+h",
                "\tAxis 2: gradient, maxSpeed 3, mouse+v",
                "\tAxis 3: gradient, +key 114, -key 113",
                "\tAxis 4: gradient, +key 117, -key 112"]
    else:
        out += ["\tAxis 3: gradient, maxSpeed 3, mouse+h",
                "\tAxis 4: gradient, maxSpeed 3, mouse+v",
                "\tAxis 1: gradient, +key 114, -key 113",
                "\tAxis 2: gradient, +key 117, -key 112"]
    out += ["\tAxis 5: +key 114, -key 113",
            "\tAxis 6: +key 116, -key 111"]
    used = []
    if profile == "terminale":
        # mappatura scritta apposta per una tastiera a schermo: A
        # digita il carattere puntato, X cancella, Y spazio, START
        # come A (equivalente a invio anche a tastiera nascosta)
        nm = names_map(keys)
        by_name = {v: k for k, v in nm.items()}
        term_map = {"A": "key 36", "START": "key 36",
                   "X": "key 22", "Y": "key 65"}
        for bname, act in term_map.items():
            ev = by_name.get(bname)
            if ev is None:
                continue
            qj = qj_of(int(ev), computed, learned)
            if qj:
                out.append("\tButton %d: %s" % (qj, act))
                used.append((qj, bname))
        out.append("}")
        return "\n".join(out) + "\n", used
    skip_mouse = False
    for func, evs in m.items():
        if skip_mouse and func in ("click_l", "click_r", "click_m",
                                   "wheel_up", "wheel_dn"):
            continue
        act = ACT.get(func)
        if not act:
            continue
        for ev in evs:
            qj = qj_of(int(ev), computed, learned)
            if qj:
                out.append("\tButton %d: %s" % (qj, act))
                used.append((qj, func))
    out.append("}")
    return "\n".join(out) + "\n", used


def main():
    profile = sys.argv[1] if len(sys.argv) > 1 else "sinistro"
    dest = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        DATA, "qjoypad_generated.lyt")
    path, keys = jsmap.find_pad()
    if not keys:
        sys.stderr.write("gen_layout: nessun gamepad trovato\n")
        return 1
    cfg = load_cfg()
    text, used = build(profile, cfg, keys)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            f.write(text)
    except OSError as e:
        sys.stderr.write("gen_layout: %s\n" % e)
        return 1
    nm = names_map(keys)
    qj = jsmap.ev_to_qj(keys)
    sys.stderr.write("gen_layout: pad %s, %d pulsanti\n" % (path, len(qj)))
    for ev in sorted(qj):
        sys.stderr.write("   %-6s ev%-4d -> Button %d\n"
                         % (nm.get(ev, "?"), ev, qj[ev]))
    sys.stderr.write("gen_layout: profilo %s -> %s\n" % (profile, dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
