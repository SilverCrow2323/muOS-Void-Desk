# -*- coding: utf-8 -*-
"""IPTV module for VoidDesk service.
Parses M3U playlists and XMLTV EPG, controls mpv.
"""
import gzip, hashlib, io, json, os, re, socket, ssl, subprocess, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

APP_DIR = None  # set from main service

# ── HTTP ───────────────────────────────────────────────────────────────
def _opener(ua=None):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    h = urllib.request.HTTPSHandler(context=ctx)
    op = urllib.request.build_opener(h)
    op.addheaders = [("User-Agent", ua or "VoidDesk/1.0"),
                     ("Accept-Encoding", "gzip")]
    return op

def fetch_bytes(url, ua=None, timeout=25):
    op = _opener(ua)
    with op.open(url, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        try: raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError: pass
    return raw

def fetch_text(url, ua=None, timeout=25):
    raw = fetch_bytes(url, ua, timeout)
    for enc in ("utf-8", "latin-1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: continue
    return raw.decode("utf-8", "replace")

# ── M3U PARSER ─────────────────────────────────────────────────────────
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="(.*?)"')

def parse_m3u(text):
    channels = []
    epg_urls = []
    pending = None
    idx = 0
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    for line in text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line: continue
        if line.startswith("#EXTM3U"):
            attrs = dict(ATTR_RE.findall(line))
            for key in ("url-tvg", "x-tvg-url", "tvg-url"):
                v = attrs.get(key, "")
                for u in v.split(","):
                    u = u.strip()
                    if u and u not in epg_urls:
                        epg_urls.append(u)
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[1].strip() if "," in line else "?"
            pending = {
                "name": name, "tvg_id": attrs.get("tvg-id", ""),
                "tvg_name": attrs.get("tvg-name", ""),
                "logo": attrs.get("tvg-logo", ""),
                "group": attrs.get("group-title", "Uncategorized") or "Uncategorized",
            }
            continue
        if line.startswith("#"):
            continue
        if pending is not None:
            ch = dict(pending)
            ch["url"] = line
            ch["index"] = idx
            channels.append(ch)
            idx += 1
            pending = None
        elif line.startswith(("http://", "https://", "rtmp://", "rtsp://")):
            channels.append({
                "name": line.split("/")[-1][:40] or "?",
                "url": line, "tvg_id": "", "tvg_name": "",
                "logo": "", "group": "Uncategorized", "index": idx,
            })
            idx += 1
    groups = []
    seen = set()
    for ch in channels:
        g = ch.get("group", "Uncategorized")
        if g not in seen:
            seen.add(g); groups.append(g)
    return {"channels": channels, "groups": groups, "epg_urls": epg_urls}

# ── EPG PARSER ─────────────────────────────────────────────────────────
def _parse_time(s):
    if not s: return None
    s = s.strip()
    base, tz = (s.split(" ", 1) + [""])[:2] if " " in s else (s, "")
    base = base[:14].ljust(14, "0")
    try:
        dt = datetime.strptime(base, "%Y%m%d%H%M%S")
    except ValueError: return None
    offset = timedelta(0)
    tz = tz.strip()
    if len(tz) == 5 and tz[0] in "+-":
        try:
            offset = timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5]))
            if tz[0] == "-": offset = -offset
        except ValueError: pass
    return (dt - offset).replace(tzinfo=timezone.utc).timestamp()

def parse_xmltv(data):
    by_key = {}
    chan_names = {}
    try:
        for event, el in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = el.tag.split("}")[-1]
            if tag == "channel":
                cid = (el.get("id") or "").strip().lower()
                names = [(dn.text or "").strip().lower()
                         for dn in el.findall("display-name") if dn.text]
                if cid: chan_names[cid] = names
                el.clear()
            elif tag == "programme":
                cid = (el.get("channel") or "").strip().lower()
                start = _parse_time(el.get("start"))
                stop = _parse_time(el.get("stop"))
                t = el.find("title")
                d = el.find("desc")
                title = (t.text or "").strip() if t is not None and t.text else "?"
                desc = (d.text or "").strip() if d is not None and d.text else ""
                if cid and start:
                    prog = {"start": start, "stop": stop or start + 1800,
                            "title": title[:80], "desc": desc[:200]}
                    keys = [cid] + chan_names.get(cid, [])
                    for k in set(keys):
                        by_key.setdefault(k, []).append(prog)
                el.clear()
    except ET.ParseError:
        pass
    for progs in by_key.values():
        progs.sort(key=lambda p: p["start"])
    return by_key

def epg_now_next(by_key, channel, now=None):
    now = now or time.time()
    keys = []
    for k in ("tvg_id", "tvg_name"):
        if channel.get(k): keys.append(channel[k].strip().lower())
    keys.append(channel.get("name", "").strip().lower())
    cur = nxt = None
    for k in keys:
        progs = by_key.get(k)
        if not progs: continue
        for p in progs:
            if p["start"] <= now < p["stop"]:
                cur = p
            elif p["start"] > now:
                nxt = p
                break
        if cur or nxt: break
    return cur, nxt

# ── MPV PLAYER ─────────────────────────────────────────────────────────
_mpv_proc = None
_mpv_sock = None
_mpv_channel = None
_mpv_state = "idle"   # idle | playing | paused | error
_mpv_error = ""

def _write_mpv_input_conf(path):
    conf = """\
GAMEPAD_DPAD_UP quit 20
GAMEPAD_DPAD_DOWN quit 21
GAMEPAD_DPAD_LEFT seek -30
GAMEPAD_DPAD_RIGHT seek 30
GAMEPAD_ACTION_RIGHT cycle pause
GAMEPAD_ACTION_DOWN cycle pause
GAMEPAD_LEFT_SHOULDER add volume -5
GAMEPAD_RIGHT_SHOULDER add volume 5
GAMEPAD_START show-progress
GAMEPAD_BACK quit 0
q quit 0
"""
    try:
        with open(path, "w") as f: f.write(conf)
    except OSError: pass

def play(channel_url, channel_name, ua="VLC/3.0.20 LibVLC/3.0.20"):
    global _mpv_proc, _mpv_sock, _mpv_channel, _mpv_state, _mpv_error
    stop()
    if not channel_url:
        _mpv_state = "error"; _mpv_error = "no URL"; return False
    import shutil
    if not shutil.which("mpv"):
        _mpv_state = "error"; _mpv_error = "mpv not installed"; return False
    sock = "/tmp/voiddesk_mpv.sock"
    try: os.remove(sock)
    except OSError: pass
    input_conf = str((APP_DIR / "data" / "mpv_input.conf")) if APP_DIR else "/tmp/mpv_input.conf"
    _write_mpv_input_conf(input_conf)
    args = [
        "mpv", channel_url,
        "--no-config", "--fullscreen", "--keepaspect=yes",
        "--osd-level=1", f"--user-agent={ua}",
        "--network-timeout=12",
        "--cache=yes", "--cache-secs=5",
        f"--input-ipc-server={sock}",
        f"--input-conf={input_conf}",
    ]
    env = dict(os.environ)
    env.pop("SDL_VIDEODRIVER", None)
    try:
        _mpv_proc = subprocess.Popen(args,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     env=env, start_new_session=True)
        _mpv_sock = sock
        _mpv_channel = {"name": channel_name, "url": channel_url}
        _mpv_state = "playing"
        _mpv_error = ""
        return True
    except Exception as e:
        _mpv_state = "error"; _mpv_error = str(e)[:200]
        return False

def stop():
    global _mpv_proc, _mpv_state
    if _mpv_proc is not None:
        try:
            _mpv_proc.terminate(); _mpv_proc.wait(timeout=3)
        except Exception:
            try: _mpv_proc.kill()
            except Exception: pass
        _mpv_proc = None
    _mpv_state = "idle"

def status():
    global _mpv_state
    if _mpv_proc is not None and _mpv_proc.poll() is not None:
        _mpv_state = "idle"
        _mpv_proc = None
    return {
        "state": _mpv_state,
        "channel": _mpv_channel,
        "error": _mpv_error,
        "pid": _mpv_proc.pid if _mpv_proc else None,
    }
