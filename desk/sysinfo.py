# -*- coding: utf-8 -*-
# VOIDDESK // sysinfo — stato reale delle periferiche dell'host muOS.
# Niente dipendenze esterne: se un comando manca si prova la via successiva.

import os
import subprocess


def _read(p, d=""):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return d


def _run(cmd, t=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=t).stdout
    except Exception:
        return ""


def _have(b):
    return any(os.access(os.path.join(d, b), os.X_OK)
               for d in os.environ.get("PATH", "").split(":"))


# ---------------------------------------------------------------- rete -----
def wireless_ifaces():
    out = []
    base = "/sys/class/net"
    try:
        for n in os.listdir(base):
            if (os.path.exists(os.path.join(base, n, "wireless")) or
                    os.path.exists(os.path.join(base, n, "phy80211"))):
                out.append(n)
    except OSError:
        pass
    return out


def iface_ip(name):
    for ln in _run(["ip", "-4", "-o", "addr", "show", "dev", name]).split(
            "\n"):
        p = ln.split()
        if len(p) > 3 and p[2] == "inet":
            return p[3].split("/")[0]
    return None


def any_ip():
    for ln in _run(["ip", "-4", "-o", "addr", "show"]).splitlines():
        p = ln.split()
        if len(p) > 3 and p[1] != "lo" and p[2] == "inet":
            return p[3].split("/")[0], p[1]
    # ripiego senza il comando ip: /proc/net/route + ifconfig
    out = _run(["ifconfig"])
    cur = None
    for ln in out.splitlines():
        if ln and not ln.startswith((" ", "\t")):
            cur = ln.split()[0].rstrip(":")
        if "inet " in ln and cur and cur != "lo":
            for tok in ln.replace("addr:", "addr: ").split():
                if tok.count(".") == 3 and tok[0].isdigit():
                    return tok, cur
    return None, None


def wifi_status():
    """(connesso, ssid, tacche 0..3, iface, ip) — robusto su muOS.
    connesso=None se non c'e' proprio hardware wifi."""
    ifs = wireless_ifaces()
    if not ifs:
        ip, ifc = any_ip()
        return (None, None, None, ifc, ip)

    ssid = None
    lvl = None
    iface = None
    ip = None

    for n in ifs:
        state = _read("/sys/class/net/%s/operstate" % n, "")
        this_ip = iface_ip(n)
        carrier = _read("/sys/class/net/%s/carrier" % n, "0") == "1"
        if state == "up" or this_ip or carrier:
            iface = n
            ip = this_ip
            break
    if iface is None:
        iface = ifs[0]
        ip = iface_ip(iface)

    # SSID: iwgetid -> iw dev link -> wpa_cli status -> iwconfig
    if _have("iwgetid"):
        ssid = _run(["iwgetid", "-r"]).strip() or None
    if not ssid and _have("iw"):
        out = _run(["iw", "dev", iface, "link"])
        for ln in out.splitlines():
            ln = ln.strip()
            if ln.startswith("SSID:"):
                ssid = ln.split(":", 1)[1].strip()
            elif ln.startswith("signal:"):
                try:
                    dbm = float(ln.split()[1])
                    lvl = (0 if dbm < -80 else 1 if dbm < -70 else
                           2 if dbm < -60 else 3)
                except (ValueError, IndexError):
                    pass
    if not ssid and _have("wpa_cli"):
        for sock in ("/var/run/wpa_supplicant", "/run/wpa_supplicant"):
            if not os.path.isdir(sock):
                continue
            out = _run(["wpa_cli", "-p", sock, "-i", iface, "status"])
            for ln in out.splitlines():
                if ln.startswith("ssid="):
                    ssid = ln.split("=", 1)[1].strip()
                elif ln.startswith("ip_address=") and not ip:
                    ip = ln.split("=", 1)[1].strip()
            if ssid:
                break
    if not ssid and _have("iwconfig"):
        out = _run(["iwconfig", iface])
        if 'ESSID:"' in out:
            ssid = out.split('ESSID:"', 1)[1].split('"')[0] or None

    # qualita' del segnale da /proc/net/wireless
    if lvl is None:
        try:
            for ln in open("/proc/net/wireless"):
                p = ln.split()
                if len(p) > 3 and p[0].rstrip(":") == iface:
                    q = float(p[2].rstrip("."))
                    if q > 0:
                        # alcune schede riportano 0..70, altre 0..100
                        pct = q if q <= 100 else 100.0
                        lvl = (0 if pct < 25 else 1 if pct < 45 else
                               2 if pct < 65 else 3)
                    else:
                        dbm = float(p[3].rstrip("."))
                        if dbm < 0:
                            lvl = (0 if dbm < -80 else 1 if dbm < -70 else
                                   2 if dbm < -60 else 3)
                    break
        except (OSError, ValueError, IndexError):
            pass

    connected = bool(ssid or ip)
    if connected and lvl is None:
        lvl = 2          # connesso ma senza dati di segnale
    if not ip:
        ip2, _i = any_ip()
        ip = ip or ip2
    return (connected, ssid, lvl, iface, ip)


def bt_status():
    """True/False/None (None = nessun adattatore)."""
    out = _run(["hciconfig"])
    if out.strip():
        return "UP RUNNING" in out
    out = _run(["bluetoothctl", "show"], t=4)
    if out.strip():
        return "Powered: yes" in out
    try:
        if os.path.isdir("/sys/class/bluetooth") and \
                os.listdir("/sys/class/bluetooth"):
            return None if not out else False
    except OSError:
        pass
    return None


# -------------------------------------------------------------- energia ----
def battery():
    base = "/sys/class/power_supply"
    try:
        names = os.listdir(base)
    except OSError:
        return None, False
    pct = None
    chg = False
    for n in names:
        cap = os.path.join(base, n, "capacity")
        if os.path.exists(cap) and pct is None:
            try:
                pct = int(_read(cap, "0"))
            except ValueError:
                pct = None
        st = _read(os.path.join(base, n, "status"), "").strip().lower()
        if st and "discharg" not in st and "not charg" not in st and \
                "charg" in st:
            chg = True
        on = _read(os.path.join(base, n, "online"), "").strip()
        if on == "1":
            chg = True
    return pct, chg


def usb_mode():
    """MTP o ADB attivi sulla porta USB, se il gadget li espone.
    None se non determinabile (nessun crash, solo nessuna icona).
    Nota d'onesta': i percorsi esatti usati da muOS per esporre questo
    stato non sono documentati pubblicamente, quindi controlliamo piu'
    candidati invece di fidarci di uno solo."""
    for p in (os.environ.get("VD_USB_FUNCTIONS"),
              "/sys/kernel/config/usb_gadget/g1/configs/c.1/strings/0x409/configuration",
              "/config/usb_gadget/g1/configs/c.1/strings/0x409/configuration",
              "/sys/kernel/config/usb_gadget/g1/os_desc/use",
              "/sys/class/android_usb/android0/functions",
              "/sys/class/android_usb/android0/state"):
        if not p:
            continue
        v = _read(p, "").strip().lower()
        if not v:
            continue
        if "adb" in v:
            return "adb"
        if "mtp" in v:
            return "mtp"
    # rete di sicurezza: interfaccia kernel piu' generica (UDC), dice
    # solo "connesso" senza sapere quale funzione, ma meglio di niente
    try:
        base = "/sys/class/udc"
        for n in os.listdir(base):
            st = _read(os.path.join(base, n, "state"), "").strip().lower()
            if st == "configured":
                return "mtp"
    except OSError:
        pass
    return None


def backlight_dev():
    base = "/sys/class/backlight"
    try:
        for n in sorted(os.listdir(base)):
            if os.path.exists(os.path.join(base, n, "brightness")):
                return os.path.join(base, n)
    except OSError:
        pass
    return None


def brightness():
    d = backlight_dev()
    if not d:
        return None
    try:
        mx = int(_read(os.path.join(d, "max_brightness"), "0")) or 1
        return max(0, min(100,
                          int(_read(os.path.join(d, "brightness"),
                                    "0")) * 100 // mx))
    except ValueError:
        return None


def set_brightness(pct):
    d = backlight_dev()
    if not d:
        return
    try:
        mx = int(_read(os.path.join(d, "max_brightness"), "0")) or 1
        with open(os.path.join(d, "brightness"), "w") as f:
            f.write(str(max(1, min(mx, mx * pct // 100))))
    except (OSError, ValueError):
        pass


# ---------------------------------------------------------------- audio ----
def volume():
    if not _have("amixer"):
        return None
    for ctl in ("Master", "PCM", "Speaker"):
        out = _run(["amixer", "sget", ctl])
        if not out:
            continue
        muted = "[off]" in out
        for tok in out.split():
            if tok.startswith("[") and tok.endswith("%]"):
                try:
                    v = int(tok[1:-2])
                    return 0 if muted else v
                except ValueError:
                    pass
    return None


def set_volume(pct):
    if not _have("amixer"):
        return
    for ctl in ("Master", "PCM", "Speaker"):
        subprocess.call(["amixer", "-q", "sset", ctl, "%d%%" % pct, "unmute"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sound_cards():
    c = _read("/proc/asound/cards", "")
    return [l for l in c.splitlines() if l.strip()]
