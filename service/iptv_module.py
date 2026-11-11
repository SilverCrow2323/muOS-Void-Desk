# -*- coding: utf-8 -*-
"""IPTV module for VoidDesk service.
Parses M3U playlists and XMLTV EPG, controls mpv.
"""
import gzip, io, json, os, re, shutil, socket, ssl, subprocess, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

APP_DIR = None  # set from main service

# ── HTTP / URL VALIDATION ──────────────────────────────────────────────
MAX_PLAYLIST_BYTES = 8 * 1024 * 1024
MAX_EPG_BYTES = 32 * 1024 * 1024
MAX_CHANNELS = 2000
FETCH_SCHEMES = {"http", "https"}
STREAM_SCHEMES = {"http", "https", "rtmp", "rtmps", "rtsp", "rtsps"}


def validate_url(url, *, stream=False):
    """Validate a user-configured playlist/stream URL without shell interpretation."""
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("URL is empty or too long")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in url):
        raise ValueError("URL contains control characters")
    parsed = urllib.parse.urlsplit(url.strip())
    allowed = STREAM_SCHEMES if stream else FETCH_SCHEMES
    if parsed.scheme.lower() not in allowed:
        raise ValueError("unsupported URL scheme")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must contain a host and no embedded credentials")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("URL has an invalid port") from exc
    return url.strip()


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        old_scheme = urllib.parse.urlsplit(request.full_url).scheme.lower()
        target = validate_url(newurl)
        target_scheme = urllib.parse.urlsplit(target).scheme.lower()
        if old_scheme == "https" and target_scheme != "https":
            raise ValueError("HTTPS media source attempted an insecure redirect")
        return super().redirect_request(
            request, fp, code, msg, headers, target)


def _opener(ua=None):
    # Use the platform trust store and hostname verification. Never disable
    # certificate validation for playlists or EPG sources.
    ctx = ssl.create_default_context()
    handler = urllib.request.HTTPSHandler(context=ctx)
    op = urllib.request.build_opener(handler, _SafeRedirectHandler())
    op.addheaders = [
        ("User-Agent", ua or "VoidDesk/1.0"),
        ("Accept-Encoding", "gzip"),
    ]
    return op


def fetch_bytes(url, ua=None, timeout=25, max_bytes=MAX_PLAYLIST_BYTES):
    url = validate_url(url)
    op = _opener(ua)
    request = urllib.request.Request(url, headers={"Accept": "*/*"})
    with op.open(request, timeout=timeout) as response:
        validate_url(response.geturl())
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                announced_size = int(content_length)
            except ValueError as exc:
                raise ValueError("remote media source sent an invalid Content-Length") from exc
            if announced_size < 0 or announced_size > max_bytes:
                raise ValueError("remote media document exceeds size limit")
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("remote media document exceeds size limit")
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(max_bytes + 1)
        except OSError as exc:
            raise ValueError("invalid gzip response") from exc
        if len(raw) > max_bytes:
            raise ValueError("decompressed media document exceeds size limit")
    return raw


def fetch_text(url, ua=None, timeout=25, max_bytes=MAX_PLAYLIST_BYTES):
    raw = fetch_bytes(url, ua, timeout, max_bytes)
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")

# ── M3U PARSER ─────────────────────────────────────────────────────────
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="(.*?)"')

def parse_m3u(text):
    channels = []
    epg_urls = []
    pending = None
    if not isinstance(text, str):
        raise ValueError("playlist must be text")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    for line in text.splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            attrs = dict(ATTR_RE.findall(line))
            for key in ("url-tvg", "x-tvg-url", "tvg-url"):
                for candidate in attrs.get(key, "").split(","):
                    candidate = candidate.strip()
                    try:
                        candidate = validate_url(candidate)
                    except ValueError:
                        continue
                    if candidate not in epg_urls and len(epg_urls) < 5:
                        epg_urls.append(candidate)
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[1].strip() if "," in line else "?"
            pending = {
                "name": name[:120] or "?",
                "tvg_id": attrs.get("tvg-id", "")[:120],
                "tvg_name": attrs.get("tvg-name", "")[:120],
                "logo": attrs.get("tvg-logo", "")[:500],
                "group": (attrs.get("group-title", "Uncategorized") or "Uncategorized")[:80],
            }
            continue
        if line.startswith("#"):
            continue
        try:
            stream_url = validate_url(line, stream=True)
        except ValueError:
            pending = None
            continue
        if pending is not None:
            channel = dict(pending)
        else:
            channel = {
                "name": urllib.parse.urlsplit(stream_url).path.rsplit("/", 1)[-1][:40] or "Stream",
                "tvg_id": "", "tvg_name": "", "logo": "",
                "group": "Uncategorized",
            }
        channel["url"] = stream_url
        channel["index"] = len(channels)
        channels.append(channel)
        pending = None
        if len(channels) >= MAX_CHANNELS:
            break

    groups = []
    seen = set()
    for channel in channels:
        group = channel.get("group", "Uncategorized")
        if group not in seen:
            seen.add(group)
            groups.append(group)
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
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("XMLTV input must be bytes")
    upper = bytes(data).upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("XMLTV document type/entity declarations are not supported")
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

def play(channel_url, channel_name, ua="VoidDesk/10.5"):
    global _mpv_proc, _mpv_sock, _mpv_channel, _mpv_state, _mpv_error
    try:
        channel_url = validate_url(channel_url, stream=True)
    except ValueError as exc:
        _mpv_state = "error"
        _mpv_error = str(exc)
        return False
    if not shutil.which("mpv"):
        _mpv_state = "error"
        _mpv_error = "mpv not installed"
        return False
    stop()
    sock = "/tmp/voiddesk_mpv.sock"
    try:
        os.remove(sock)
    except OSError:
        pass
    input_conf = str((APP_DIR / "data" / "mpv_input.conf")) if APP_DIR else "/tmp/mpv_input.conf"
    _write_mpv_input_conf(input_conf)
    args = [
        "mpv", "--no-config", "--fullscreen", "--keepaspect=yes",
        "--osd-level=1", "--user-agent=" + str(ua)[:120],
        "--network-timeout=12", "--cache=yes", "--cache-secs=5",
        "--input-ipc-server=" + sock, "--input-conf=" + input_conf,
        "--", channel_url,
    ]
    env = dict(os.environ)
    env.pop("SDL_VIDEODRIVER", None)
    try:
        _mpv_proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env, start_new_session=True,
        )
        _mpv_sock = sock
        _mpv_channel = {"name": str(channel_name or "Stream")[:120],
                        "url": channel_url}
        _mpv_state = "playing"
        _mpv_error = ""
        return True
    except Exception as exc:
        _mpv_state = "error"
        _mpv_error = str(exc)[:200]
        return False


def stop():
    global _mpv_proc, _mpv_sock, _mpv_channel, _mpv_state, _mpv_error
    if _mpv_proc is not None:
        try:
            _mpv_proc.terminate()
            _mpv_proc.wait(timeout=3)
        except Exception:
            try:
                _mpv_proc.kill()
            except Exception:
                pass
        _mpv_proc = None
    if _mpv_sock:
        try:
            os.remove(_mpv_sock)
        except OSError:
            pass
        _mpv_sock = None
    _mpv_state = "idle"
    _mpv_channel = None
    _mpv_error = ""


def status():
    global _mpv_proc, _mpv_state, _mpv_sock
    if _mpv_proc is not None and _mpv_proc.poll() is not None:
        _mpv_state = "idle"
        _mpv_proc = None
        if _mpv_sock:
            try:
                os.remove(_mpv_sock)
            except OSError:
                pass
            _mpv_sock = None
    return {
        "state": _mpv_state,
        "channel": _mpv_channel,
        "error": _mpv_error,
        "pid": _mpv_proc.pid if _mpv_proc else None,
    }
