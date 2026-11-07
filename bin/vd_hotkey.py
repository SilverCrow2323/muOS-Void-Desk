#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // vd_hotkey v3 — sorveglia START+SELECT e apre il pannello
# rapido (pygame su framebuffer) congelando Xorg. Fuori da X: funziona
# anche se il desktop e' bloccato.

import json
import os
import signal
import struct
import subprocess
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP, "desk"))
sys.path.insert(0, os.path.join(APP, "bin"))
import evinput         # noqa: E402

EVSZ = struct.calcsize("llHHi")
HOLD_S = 0.6
MNT = sys.argv[1] if len(sys.argv) > 1 else ""
DATA = os.path.join(APP, "data")
_hold = {310: False, 311: False}
_taps = []          # tasti premuti (codici grezzi) da smaltire


def kbd_buttons():
    """Tasti che mostrano/nascondono la tastiera (da OPZIONI > mappatura)."""
    try:
        cfg = json.load(open(os.path.join(DATA, "desk_config.json")))
        evs = (cfg.get("map") or {}).get("kbd")
        if evs:
            return list(evs)
    except Exception:
        pass
    return [312]        # MENU


def log(m):
    sys.stderr.write("vd_hotkey: %s\n" % m)
    sys.stderr.flush()


def poll_hold():
    del _taps[:]
    for fd in evinput._state["fds"]:
        while True:
            try:
                data = os.read(fd, EVSZ * 32)
            except (BlockingIOError, InterruptedError, OSError):
                break
            if not data:
                break
            for off in range(0, len(data) - EVSZ + 1, EVSZ):
                _s, _u, t, c, v = struct.unpack_from("llHHi", data, off)
                if t == 1:
                    if c in _hold:
                        _hold[c] = (v != 0)
                    if v == 1:
                        _taps.append(c)
    return _hold[310] and _hold[311]


def kbd_pids():
    return pids_of("matchbox-keybo", "matchbox-keyboard")


def onboard_toggle():
    """Mostra/nasconde la tastiera. Protocollo semplice e indistruttibile:
    se gira -> SIGTERM (sparisce); se non gira -> parte (appare).
    Il vecchio giro demone+SIGUSR1 moriva se il segnale arrivava prima
    dell'handler, ed era il freeze del pannello LIVE."""
    pids = kbd_pids()
    if pids:
        log("nascondo matchbox (SIGTERM)")
        sig_all(pids, signal.SIGTERM)
        time.sleep(0.3)
        still = kbd_pids()
        if still:
            log("SIGTERM ignorato o in ritardo, scalo a SIGKILL: %r"
                % still)
            sig_all(still, signal.SIGKILL)
    else:
        lay = "default"
        kbh = 230
        try:
            import json
            cfgd = json.load(open(os.path.join(
                os.path.dirname(MNT), "desk_config.json")))
            lay = cfgd.get("kbd_mb", "default")
            kbh = int(cfgd.get("kbd_h", 230))
        except Exception:
            pass
        # nel terminale (niente Thunar/Xfpanel a fare da riferimento
        # visivo) la tastiera di default risultava minuscola: qui la
        # ancoro in basso, piena larghezza, con caratteri leggibili
        extra = []
        if os.environ.get("VD_TERM_KBD") == "1":
            kby = max(0, 480 - kbh)
            extra = ["-g", "%dx640.%d.0" % (kbh, kby),
                    "--fontptsize", "16"]
        log("avvio matchbox-keyboard (%s)%s" %
            (lay, " terminale" if extra else ""))
        if lay and lay != "default":
            session_cmd(["matchbox-keyboard"] + extra + [lay])
            time.sleep(0.6)
            if kbd_pids():
                return
            log("layout %s assente: fallback default" % lay)
        session_cmd(["matchbox-keyboard"] + extra)


def pids_of(*names):
    """Processi VIVI con quel nome. Gli zombie (figli non raccolti) hanno
    ancora il comm leggibile: contarli faceva credere che la tastiera
    girasse, e il toggle mandava SIGTERM a un cadavere -> "non ricompare"."""
    out = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            comm = open("/proc/%s/comm" % pid).read().strip()
            st = open("/proc/%s/stat" % pid).read()
            if st.rsplit(") ", 1)[1][0] == "Z":
                continue
        except (OSError, IndexError):
            continue
        if any(comm == n or comm.startswith(n) for n in names):
            out.append(int(pid))
    return out


def sig_all(pids, sig):
    for p in pids:
        try:
            os.kill(p, sig)
        except OSError:
            pass


def session_cmd(cmd, wait=False):
    dbus = ""
    try:
        dbus = open(os.path.join(MNT, "tmp/.vd_dbus")).read().strip()
    except OSError:
        pass
    full = ["chroot", MNT, "/usr/bin/env", "DISPLAY=:0", "HOME=/root",
            "PATH=/usr/sbin:/usr/bin:/sbin:/bin"]
    if dbus:
        full.append("DBUS_SESSION_BUS_ADDRESS=" + dbus)
    try:
        if wait:
            return subprocess.call(full + cmd, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=8)
        subprocess.Popen(full + cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        return 1
    return 0


def do_action(act):
    if act in ("resume", "kbd"):
        if act == "kbd":
            time.sleep(0.25)        # X e' appena ripartito: gli do respiro
            onboard_toggle()
        session_cmd(["xrefresh", "-display", ":0"])
        return
    if act == "refresh":
        time.sleep(0.25)
        session_cmd(["xrefresh", "-display", ":0"])
        return
    if act and act.startswith("start:"):
        time.sleep(0.25)
        name = act[len("start:"):]
        cmds = {"matchbox-window-manager":
                ["matchbox-window-manager", "-use_titlebar", "no"],
                "qjoypad": ["qjoypad", "--notray", "Default"]}
        cmd = cmds.get(name)
        if cmd:
            log("Core Tasks: riavvio %s" % name)
            session_cmd(cmd)
        session_cmd(["xrefresh", "-display", ":0"])
        return
    if act == "ctrlc":
        time.sleep(0.25)
        session_cmd(["sh", "-c",
                    "WID=$(xdotool search --name 'VoidDesk :: CLI' "
                    "2>/dev/null | head -1); "
                    "[ -n \"$WID\" ] && xdotool key --window \"$WID\" "
                    "--clearmodifiers ctrl+c || "
                    "xdotool key --clearmodifiers ctrl+c"])
        session_cmd(["xrefresh", "-display", ":0"])
        return
    env = "xfce"
    try:
        env = (open(os.path.join(MNT, "tmp/.vd_env")).read().strip()
               or "xfce")
    except OSError:
        pass
    if env == "cli":
        # niente XFCE/IceWM/LXDE da salutare con le buone: qui c'e'
        # solo xterm, si passa dritti a terminare X. "close" e
        # "launch_clitools" atterrano entrambi su CLI Arsenal --
        # e' li' che si sceglie il prossimo tool, non ha senso avere
        # due meccanismi diversi per la stessa destinazione.
        if act in ("close", "launch_clitools"):
            try:
                open(os.path.join(os.path.dirname(MNT),
                                  ".land_clitools"), "w").close()
            except OSError:
                pass
        elif act == "restart":
            try:
                open(os.path.join(MNT, "tmp/.vd_restart"), "w").close()
            except OSError:
                pass
        xp = pids_of("Xorg", "X")
        if xp:
            log("chiusura CLI Terminal: termino X")
            sig_all(xp, signal.SIGTERM)
        return
    if act == "restart":
        try:
            open(os.path.join(MNT, "tmp/.vd_restart"), "w").close()
        except OSError:
            pass
    if env == "icewm":
        session_cmd(["sh", "-c", "kill $(pidof icewm-session) 2>/dev/null"])
    elif env == "lxde":
        session_cmd(["sh", "-c", "kill $(pidof lxsession) 2>/dev/null"])
    else:
        session_cmd(["xfce4-session-logout", "--logout", "--fast"])
    time.sleep(4)
    xp = pids_of("Xorg", "X")
    if xp:
        log("logout ignorato: termino X")
        sig_all(xp, signal.SIGTERM)


def main():
    if not MNT:
        log("uso: vd_hotkey.py <mountpoint>")
        return 2
    # i figli (matchbox, xrefresh...) si auto-raccolgono: mai piu' zombie
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    if not evinput.start():
        log("evdev non disponibile")
        return 1
    kbd_keys = kbd_buttons()
    log("attivo (START+SELECT = pannello, %s = tastiera)"
        % kbd_keys)
    both_since = 0.0
    fired = 0.0
    kbd_t = 0.0
    while True:
        both = poll_hold()
        now = time.time()
        # tasto tastiera virtuale (non passa da QJoyPad: lo gestiamo qui)
        if not both and now - kbd_t > 0.6:
            for c in _taps:
                if c in kbd_keys:
                    kbd_t = now
                    log("toggle tastiera")
                    onboard_toggle()
                    break
        if both:
            if not both_since:
                both_since = now
            elif now - both_since >= HOLD_S and now - fired > 2.0:
                fired = now
                both_since = 0.0
                _hold[310] = _hold[311] = False
                xp = pids_of("Xorg", "X")
                qp = pids_of("qjoypad")
                sig_all(xp + qp, signal.SIGSTOP)
                log("X congelato: %s" % xp)
                act = "resume"
                try:
                    import vd_panel
                    act = vd_panel.Panel(MNT).run_panel()
                except Exception as e:
                    log("errore pannello: %s" % e)
                finally:
                    sig_all(xp + qp, signal.SIGCONT)
                log("azione: %s" % act)
                do_action(act)
        else:
            both_since = 0.0
        time.sleep(0.03)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
