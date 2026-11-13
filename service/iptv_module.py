# -*- coding: utf-8 -*-
"""Bounded M3U/XMLTV parsing and optional mpv control for Void Desk.

Feed downloads use the system TLS trust store, public HTTP(S) hosts only,
bounded response sizes, and redirect validation. Stream URLs are passed to
mpv as a single argument and are restricted to network schemes.
"""
from __future__ import annotations

import gzip
import io
import json
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP_DIR: Path | None = None

MAX_PLAYLIST_BYTES = 8 * 1024 * 1024
MAX_EPG_BYTES = 24 * 1024 * 1024
MAX_CHANNELS = 2000
MAX_EPG_PROGRAMMES = 50000
MAX_FEED_URL_LENGTH = 2048
MAX_STREAM_URL_LENGTH = 4096
DEFAULT_USER_AGENT = "VoidDesk/10.5"


def _validate_public_host(host: str, *, resolve: bool = True) -> None:
    """Reject localhost, private, reserved and link-local feed destinations."""
    if not host or host.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("local feed hosts are not allowed")

    if host.lower().endswith((".localhost", ".local", ".internal", ".home")):
        raise ValueError("local feed host suffix is not allowed")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if not literal.is_global:
            raise ValueError("private or reserved feed IP is not allowed")
        return

    if not resolve:
        return

    try:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("feed host could not be resolved") from exc

    addresses = set()
    for result in results:
        try:
            addresses.add(ipaddress.ip_address(result[4][0]))
        except (ValueError, IndexError):
            continue

    if not addresses:
        raise ValueError("feed host has no usable address")
    if any(not address.is_global for address in addresses):
        raise ValueError("feed host resolves to a private or reserved address")


def validate_feed_url(url: str, *, resolve: bool = True) -> str:
    """Validate an HTTP(S) feed URL before any privileged service fetch."""
    if not isinstance(url, str) or not url or len(url) > MAX_FEED_URL_LENGTH:
        raise ValueError("feed URL is empty or too long")

    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("feed URL must use HTTP or HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("feed URL must have a host and no embedded credentials")
    if parsed.fragment:
        raise ValueError("feed URL fragments are not supported")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("feed URL has an invalid port") from exc
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("feed URL has an invalid port")

    _validate_public_host(parsed.hostname, resolve=resolve)
    return urllib.parse.urlunsplit(parsed)


def validate_stream_url(url: str) -> str:
    """Validate a media stream URL; private LAN streams are allowed by design."""
    if not isinstance(url, str) or not url or len(url) > MAX_STREAM_URL_LENGTH:
        raise ValueError("stream URL is empty or too long")

    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https", "rtsp", "rtmp"}:
        raise ValueError("stream URL must use HTTP, HTTPS, RTSP or RTMP")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("stream URL must have a host and no embedded credentials")
    if parsed.fragment:
        raise ValueError("stream URL fragments are not supported")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("stream URL has an invalid port") from exc
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("stream URL has an invalid port")
    return urllib.parse.urlunsplit(parsed)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_feed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(user_agent: str | None = None):
    """Build an opener with normal certificate verification and safe redirects."""
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    opener.addheaders = [
        ("User-Agent", (user_agent or DEFAULT_USER_AGENT)[:160]),
        ("Accept", "application/vnd.apple.mpegurl, application/x-mpegURL, application/xml, text/xml, */*"),
        ("Accept-Encoding", "gzip"),
    ]
    return opener


def _read_bounded(response, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise ValueError("remote feed exceeds the size limit")
        except ValueError as exc:
            if str(exc) == "remote feed exceeds the size limit":
                raise
    chunks = []
    total = 0
    while True:
        chunk = response.read(min(65536, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("remote feed exceeds the size limit")
    return b"".join(chunks)


def fetch_bytes(
    url: str,
    ua: str | None = None,
    timeout: int = 15,
    max_bytes: int = MAX_PLAYLIST_BYTES,
) -> bytes:
    """Fetch a public HTTP(S) resource with TLS and compressed-size limits."""
    safe_url = validate_feed_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={
            "User-Agent": (ua or DEFAULT_USER_AGENT)[:160],
            "Accept": "application/xml, text/xml, application/x-mpegURL, */*",
            "Accept-Encoding": "gzip",
        },
    )
    with _opener(ua).open(request, timeout=max(1, min(int(timeout), 25))) as response:
        validate_feed_url(response.geturl())
        raw = _read_bounded(response, max_bytes)

    if raw[:2] == b"\x1f\x8b":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
                raw = zipped.read(max_bytes + 1)
        except OSError as exc:
            raise ValueError("invalid compressed feed") from exc
        if len(raw) > max_bytes:
            raise ValueError("decompressed feed exceeds the size limit")
    return raw


def fetch_text(url: str, ua: str | None = None, timeout: int = 15) -> str:
    raw = fetch_bytes(url, ua=ua, timeout=timeout, max_bytes=MAX_PLAYLIST_BYTES)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


# ── M3U parser ──────────────────────────────────────────────────────────
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="(.*?)"')


def parse_m3u(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("playlist must be text")
    if len(text.encode("utf-8", "replace")) > MAX_PLAYLIST_BYTES:
        raise ValueError("playlist exceeds the size limit")

    channels = []
    epg_urls = []
    pending = None

    for line in text.lstrip("\ufeff").splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            attrs = dict(ATTR_RE.findall(line))
            for key in ("url-tvg", "x-tvg-url", "tvg-url"):
                for candidate in attrs.get(key, "").split(","):
                    candidate = candidate.strip()
                    if not candidate or candidate in epg_urls:
                        continue
                    try:
                        validate_feed_url(candidate, resolve=False)
                    except ValueError:
                        continue
                    epg_urls.append(candidate)
                    if len(epg_urls) >= 8:
                        break
            continue

        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[1].strip() if "," in line else "?"
            pending = {
                "name": name[:120] or "?",
                "tvg_id": attrs.get("tvg-id", "")[:160],
                "tvg_name": attrs.get("tvg-name", "")[:120],
                "logo": attrs.get("tvg-logo", "")[:512],
                "group": (attrs.get("group-title", "Uncategorized") or "Uncategorized")[:80],
            }
            continue

        if line.startswith("#"):
            continue

        try:
            stream_url = validate_stream_url(line)
        except ValueError:
            pending = None
            continue

        if pending is None:
            channel = {
                "name": urllib.parse.urlsplit(stream_url).hostname or "Stream",
                "tvg_id": "",
                "tvg_name": "",
                "logo": "",
                "group": "Uncategorized",
            }
        else:
            channel = dict(pending)
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


# ── XMLTV EPG parser ────────────────────────────────────────────────────
def _parse_time(value: str | None):
    if not value:
        return None
    parts = value.strip().split(None, 1)
    base = parts[0][:14].ljust(14, "0")
    timezone_text = parts[1].strip() if len(parts) > 1 else ""
    try:
        moment = datetime.strptime(base, "%Y%m%d%H%M%S")
    except ValueError:
        return None

    offset = timedelta(0)
    if len(timezone_text) == 5 and timezone_text[0] in "+-":
        try:
            offset = timedelta(
                hours=int(timezone_text[1:3]),
                minutes=int(timezone_text[3:5]),
            )
            if timezone_text[0] == "-":
                offset = -offset
        except ValueError:
            pass
    return (moment - offset).replace(tzinfo=timezone.utc).timestamp()


def parse_xmltv(data: bytes) -> dict:
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("XMLTV payload must be bytes")
    if len(data) > MAX_EPG_BYTES:
        raise ValueError("XMLTV feed exceeds the size limit")
    upper = bytes(data).upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("XMLTV DTD and entity declarations are not supported")

    by_key = {}
    channel_names = {}
    programme_count = 0
    try:
        for _event, element in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = element.tag.split("}")[-1]
            if tag == "channel":
                channel_id = (element.get("id") or "").strip().lower()[:160]
                names = [
                    (entry.text or "").strip().lower()[:120]
                    for entry in element.findall("display-name")
                    if entry.text
                ]
                if channel_id:
                    channel_names[channel_id] = names
                element.clear()
            elif tag == "programme":
                programme_count += 1
                if programme_count > MAX_EPG_PROGRAMMES:
                    raise ValueError("XMLTV programme count exceeds the limit")
                channel_id = (element.get("channel") or "").strip().lower()[:160]
                start = _parse_time(element.get("start"))
                stop = _parse_time(element.get("stop"))
                title_element = element.find("title")
                desc_element = element.find("desc")
                title = (
                    (title_element.text or "").strip()
                    if title_element is not None and title_element.text
                    else "?"
                )
                description = (
                    (desc_element.text or "").strip()
                    if desc_element is not None and desc_element.text
                    else ""
                )
                if channel_id and start:
                    programme = {
                        "start": start,
                        "stop": stop or start + 1800,
                        "title": title[:80],
                        "desc": description[:200],
                    }
                    keys = [channel_id] + channel_names.get(channel_id, [])
                    for key in set(keys):
                        by_key.setdefault(key, []).append(programme)
                element.clear()
    except ET.ParseError as exc:
        raise ValueError("invalid XMLTV document") from exc

    for programmes in by_key.values():
        programmes.sort(key=lambda programme: programme["start"])
    return by_key


def epg_now_next(by_key: dict, channel: dict, now: float | None = None):
    now = time.time() if now is None else now
    keys = []
    for key in ("tvg_id", "tvg_name"):
        if channel.get(key):
            keys.append(channel[key].strip().lower())
    if channel.get("name"):
        keys.append(channel["name"].strip().lower())

    current = following = None
    for key in keys:
        programmes = by_key.get(key)
        if not programmes:
            continue
        for programme in programmes:
            if programme["start"] <= now < programme["stop"]:
                current = programme
            elif programme["start"] > now:
                following = programme
                break
        if current or following:
            break
    return current, following


# ── mpv player ──────────────────────────────────────────────────────────
_mpv_proc = None
_mpv_sock = None
_mpv_channel = None
_mpv_state = "idle"
_mpv_error = ""


def _write_mpv_input_conf(path: Path) -> None:
    configuration = """\
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
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(configuration)


def play(
    channel_url: str,
    channel_name: str,
    user_agent: str = "VLC/3.0.20 LibVLC/3.0.20",
) -> bool:
    global _mpv_proc, _mpv_sock, _mpv_channel, _mpv_state, _mpv_error

    stop()
    try:
        safe_url = validate_stream_url(channel_url)
    except ValueError as exc:
        _mpv_state = "error"
        _mpv_error = str(exc)
        return False

    if not shutil.which("mpv"):
        _mpv_state = "error"
        _mpv_error = "mpv not installed"
        return False

    socket_path = "/tmp/voiddesk-mpv-%d.sock" % os.getpid()
    try:
        os.remove(socket_path)
    except OSError:
        pass

    input_path = (
        APP_DIR / "data" / "mpv_input.conf"
        if APP_DIR is not None
        else Path("/tmp/voiddesk-mpv-input.conf")
    )
    try:
        _write_mpv_input_conf(input_path)
        args = [
            "mpv",
            "--no-config",
            "--fullscreen",
            "--keepaspect=yes",
            "--osd-level=1",
            "--network-timeout=12",
            "--cache=yes",
            "--cache-secs=5",
            "--input-ipc-server=" + socket_path,
            "--input-conf=" + str(input_path),
            "--",
            safe_url,
        ]
        clean_agent = (user_agent or DEFAULT_USER_AGENT).replace("\r", " ").replace("\n", " ")
        args.insert(-2, "--user-agent=" + clean_agent[:160])
        environment = dict(os.environ)
        environment.pop("SDL_VIDEODRIVER", None)
        _mpv_proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            start_new_session=True,
        )
        _mpv_sock = socket_path
        _mpv_channel = {"name": str(channel_name or "Live stream")[:120]}
        _mpv_state = "playing"
        _mpv_error = ""
        return True
    except Exception as exc:
        _mpv_state = "error"
        _mpv_error = str(exc)[:200]
        _mpv_proc = None
        _mpv_sock = None
        _mpv_channel = None
        return False


def stop() -> None:
    global _mpv_proc, _mpv_sock, _mpv_channel, _mpv_state
    process = _mpv_proc
    _mpv_proc = None
    if process is not None:
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                pass
    if _mpv_sock:
        try:
            os.remove(_mpv_sock)
        except OSError:
            pass
    _mpv_sock = None
    _mpv_channel = None
    _mpv_state = "idle"


def status() -> dict:
    global _mpv_proc, _mpv_state
    if _mpv_proc is not None and _mpv_proc.poll() is not None:
        _mpv_proc = None
        _mpv_state = "idle"
    return {
        "state": _mpv_state,
        "channel": _mpv_channel,
        "error": _mpv_error,
        "pid": _mpv_proc.pid if _mpv_proc else None,
    }


def action(action_name: str, value: int | None = None) -> dict:
    """Bounded local control for the active IPTV MPV process."""
    global _mpv_proc, _mpv_state
    if _mpv_proc is None or _mpv_proc.poll() is not None or not _mpv_sock:
        return {"ok": False, "error": "IPTV player is not running"}
    if action_name == "toggle_pause":
        command = ["cycle", "pause"]
    elif action_name == "volume":
        try:
            volume = max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return {"ok": False, "error": "volume must be between 0 and 100"}
        command = ["set_property", "volume", volume]
    elif action_name == "stop":
        stop()
        return {"ok": True, "state": "idle"}
    else:
        return {"ok": False, "error": "unsupported IPTV action"}

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.8)
            client.connect(_mpv_sock)
            client.sendall((json.dumps({
                "command": command, "request_id": 1,
            }) + "\\n").encode("utf-8"))
            buffer = b""
            deadline = time.monotonic() + 0.8
            while time.monotonic() < deadline and len(buffer) < 4096:
                chunk = client.recv(2048)
                if not chunk:
                    break
                buffer += chunk
                for line in buffer.splitlines():
                    try:
                        response = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if response.get("request_id") == 1:
                        if response.get("error") != "success":
                            return {"ok": False, "error": "MPV rejected IPTV control"}
                        return {"ok": True, "data": response.get("data"),
                                "volume": value if action_name == "volume" else None}
    except (OSError, ValueError, TimeoutError):
        return {"ok": False, "error": "IPTV player control socket is unavailable"}
    return {"ok": False, "error": "no IPTV control response"}
