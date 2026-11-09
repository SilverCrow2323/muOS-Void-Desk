# -*- coding: utf-8 -*-
"""Authenticated SPDW Device Agent gateway for muOS handhelds.

The agent is hosted by the existing Void Desk background service process. It
replaces the older frontend-owned BaseStation HTTP server instead of creating
a second management daemon. Discovery and health are public; file APIs require
a local pairing PIN, an HttpOnly session cookie and CSRF protection.
"""
from __future__ import print_function

import hashlib
import hmac
import http.cookies
import json
import mimetypes
import os
import re
import secrets
import tempfile
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
SESSION_TTL = 8 * 60 * 60
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_SECONDS = 60
MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".cfg", ".ini", ".sh", ".csv",
    ".log", ".yaml", ".yml", ".conf", ".xml", ".js", ".css", ".html",
}


class AgentError(ValueError):
    """Expected request or filesystem validation error."""


def _atomic_write(path, payload, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".partial", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(temporary, mode)
        except OSError:
            pass
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _clean_name(value):
    value = os.path.basename(str(value or "").replace("\\", "/").strip())
    value = "".join(char if char.isalnum() or char in "._-" else "_"
                    for char in value)
    value = value.strip(" ._")
    if not value or value in (".", ".."):
        raise AgentError("a safe file or folder name is required")
    return value[:120]


def _inside(root, target):
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


class DeviceAgent:
    def __init__(self, data_dir, assets_dir, host=DEFAULT_HOST,
                 port=DEFAULT_PORT, server_factory=None):
        self.data_dir = Path(data_dir)
        self.assets_dir = Path(assets_dir)
        self.host = str(host or DEFAULT_HOST)
        self.port = int(port)
        self.state_dir = self.data_dir / "spdw_hub"
        self.security_file = self.state_dir / "device_agent.json"
        self.areas = {
            "in": self.data_dir / "incoming",
            "out": self.data_dir / "outgoing",
        }
        self._lock = threading.RLock()
        self._sessions = {}
        self._login_failures = {}
        self.httpd = None
        self.thread = None
        self.server_factory = server_factory or ThreadingHTTPServer
        self._state = self._load_or_create_state()

    def _load_or_create_state(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for directory in self.areas.values():
            directory.mkdir(parents=True, exist_ok=True)
        state = {}
        try:
            loaded = json.loads(self.security_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state.update(loaded)
        except (OSError, ValueError):
            pass
        pin = str(state.get("pairing_pin", ""))
        secret = str(state.get("secret", ""))
        if not re.fullmatch(r"\d{8}", pin):
            pin = "{:08d}".format(secrets.randbelow(100000000))
        if not re.fullmatch(r"[0-9a-f]{64}", secret):
            secret = secrets.token_hex(32)
        state = {
            "schema": "spdw-device-agent",
            "version": 1,
            "pairing_pin": pin,
            "secret": secret,
            "created_at": state.get(
                "created_at", datetime.now().astimezone().isoformat(timespec="seconds")),
        }
        _atomic_write(self.security_file,
                      json.dumps(state, indent=2).encode("utf-8"), mode=0o600)
        return state

    @property
    def pairing_pin(self):
        return self._state["pairing_pin"]

    @property
    def is_running(self):
        return self.httpd is not None

    def rotate_pairing_pin(self):
        with self._lock:
            self._state["pairing_pin"] = "{:08d}".format(
                secrets.randbelow(100000000))
            self._state["secret"] = secrets.token_hex(32)
            _atomic_write(self.security_file,
                          json.dumps(self._state, indent=2).encode("utf-8"),
                          mode=0o600)
            self._sessions.clear()
            self._login_failures.clear()
            return self.pairing_pin

    def status(self):
        return {
            "ok": True,
            "running": self.is_running,
            "host": self.host,
            "port": self.port,
            "url": "http://{}:{}/".format(self.host, self.port),
            "pairing_pin": self.pairing_pin,
        }

    def start(self):
        if self.is_running:
            return True
        try:
            handler = self.make_handler()
            self.httpd = self.server_factory((self.host, self.port), handler)
            self.httpd.daemon_threads = True
            self.thread = threading.Thread(
                target=self.httpd.serve_forever,
                name="spdw-device-agent",
                daemon=True,
            )
            self.thread.start()
            return True
        except OSError:
            self.httpd = None
            self.thread = None
            raise

    def stop(self):
        server = self.httpd
        self.httpd = None
        if server is not None:
            server.shutdown()
            server.server_close()
        thread = self.thread
        self.thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)

    def _request_ip(self, handler):
        return str(handler.client_address[0])

    def _login_locked(self, ip):
        now = time.monotonic()
        attempts, retry_at = self._login_failures.get(ip, (0, 0.0))
        if retry_at > now:
            return True, max(1, int(retry_at - now))
        if retry_at:
            self._login_failures.pop(ip, None)
        return False, 0

    def _login_failed(self, ip):
        now = time.monotonic()
        attempts, _retry_at = self._login_failures.get(ip, (0, 0.0))
        attempts += 1
        retry_at = now + LOGIN_LOCK_SECONDS if attempts >= LOGIN_MAX_FAILURES else 0.0
        self._login_failures[ip] = (attempts, retry_at)

    def _login_succeeded(self, ip):
        self._login_failures.pop(ip, None)

    def _new_session(self):
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(24)
        expires_at = time.time() + SESSION_TTL
        with self._lock:
            self._sessions[session_id] = {
                "csrf": csrf_token,
                "expires_at": expires_at,
            }
        return session_id, csrf_token

    def _get_session(self, session_id):
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if float(session.get("expires_at", 0)) <= time.time():
                self._sessions.pop(session_id, None)
                return None
            return dict(session)

    def _revoke_session(self, session_id):
        with self._lock:
            self._sessions.pop(session_id, None)

    def _resolve(self, area, relative="", must_exist=True):
        root = self.areas.get(str(area or ""))
        if root is None:
            raise AgentError("unknown file area")
        root.mkdir(parents=True, exist_ok=True)
        canonical_root = root.resolve(strict=True)
        rel = str(relative or "").replace("\\", "/")
        if rel.startswith("/"):
            raise AgentError("absolute paths are not allowed")
        parts = rel.split("/") if rel else []
        if any(part == ".." for part in parts):
            raise AgentError("parent traversal is not allowed")
        parts = [part for part in parts if part not in ("", ".")]
        candidate = canonical_root.joinpath(*parts)
        try:
            resolved = candidate.resolve(strict=must_exist)
        except FileNotFoundError:
            raise AgentError("path not found")
        if not _inside(canonical_root, resolved):
            raise AgentError("path escapes the selected file area")
        if must_exist and not resolved.exists():
            raise AgentError("path not found")
        return canonical_root, resolved

    @staticmethod
    def _atomic_file_write(target, payload, overwrite):
        target = Path(target)
        if target.exists() and not overwrite:
            raise FileExistsError(str(target))
        if target.is_dir():
            raise AgentError("target is a directory")
        _atomic_write(target, payload, mode=0o600)

    def make_handler(self):
        agent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "SPDW-Device-Agent/1.0"

            def log_message(self, fmt, *args):
                return

            def _send(self, status, content_type, payload, headers=None):
                self.send_response(int(status))
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)

            def _json(self, obj, status=200, headers=None):
                body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self._send(status, "application/json; charset=utf-8", body, headers)

            def _query(self):
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
                return parsed.path, {key: values[0] for key, values in query.items()}

            def _body(self):
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                except (TypeError, ValueError):
                    return None
                if size <= 0 or size > MAX_BODY_BYTES:
                    return None
                return self.rfile.read(size)

            def _form(self, payload):
                if payload is None:
                    return None
                content_type = self.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        data = json.loads(payload.decode("utf-8"))
                        return data if isinstance(data, dict) else None
                    except (UnicodeError, ValueError):
                        return None
                try:
                    parsed = urllib.parse.parse_qs(
                        payload.decode("utf-8", errors="replace"),
                        keep_blank_values=True)
                    return {key: values[0] for key, values in parsed.items()}
                except Exception:
                    return None

            def _session(self):
                cookie = http.cookies.SimpleCookie()
                try:
                    cookie.load(self.headers.get("Cookie", ""))
                    morsel = cookie.get("spdw_session")
                except Exception:
                    morsel = None
                if morsel is None:
                    return None, None
                session_id = morsel.value
                return session_id, agent._get_session(session_id)

            def _auth(self):
                session_id, session = self._session()
                if session is None:
                    self._json({"error": "authentication required"}, 401)
                    return None, None
                return session_id, session

            def _csrf(self, session):
                supplied = self.headers.get("X-CSRF-Token", "")
                expected = str(session.get("csrf", ""))
                try:
                    valid = bool(supplied and expected and hmac.compare_digest(
                        supplied.encode("utf-8"), expected.encode("utf-8")))
                except (UnicodeError, TypeError):
                    valid = False
                if not valid:
                    self._json({"error": "CSRF validation failed"}, 403)
                    return False
                return True

            def _file_list(self, area, relative):
                _root, directory = agent._resolve(area, relative, must_exist=True)
                if not directory.is_dir():
                    return self._json({"error": "not a directory"}, 400)
                entries = []
                for entry in sorted(directory.iterdir(),
                                    key=lambda item: (not item.is_dir(), item.name.lower())):
                    try:
                        if entry.is_symlink():
                            continue
                        info = entry.stat(follow_symlinks=False)
                        is_dir = entry.is_dir()
                        extension = entry.suffix.lower()
                        entries.append({
                            "name": entry.name,
                            "type": "dir" if is_dir else "file",
                            "size": 0 if is_dir else int(info.st_size),
                            "mtime": int(info.st_mtime),
                            "editable": (not is_dir) and extension in TEXT_EXTENSIONS,
                        })
                    except OSError:
                        continue
                self._json({"entries": entries[:1000]})

            def _file_read(self, area, relative):
                _root, target = agent._resolve(area, relative, must_exist=True)
                if not target.is_file():
                    return self._json({"error": "file not found"}, 404)
                if target.stat().st_size > MAX_TEXT_BYTES:
                    return self._json({"error": "file too large for editor"}, 413)
                try:
                    text = target.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    return self._json({"error": str(exc)}, 500)
                self._json({"content": text})

            def _file_download(self, area, relative):
                _root, target = agent._resolve(area, relative, must_exist=True)
                if not target.is_file():
                    return self._json({"error": "file not found"}, 404)
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                try:
                    size = target.stat().st_size
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(size))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("X-Frame-Options", "DENY")
                    self.send_header("Content-Disposition",
                                     'attachment; filename="{}"'.format(
                                         target.name.replace('"', "_")))
                    self.end_headers()
                    with target.open("rb") as stream:
                        while True:
                            chunk = stream.read(64 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (OSError, BrokenPipeError):
                    return

            def _file_upload(self, query, payload):
                area = query.get("area", "in")
                relative = query.get("path", "")
                _root, directory = agent._resolve(area, relative, must_exist=True)
                if not directory.is_dir():
                    return self._json({"error": "not a directory"}, 400)
                content_type = self.headers.get("Content-Type", "")
                boundary_match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))',
                                           content_type)
                if not boundary_match:
                    return self._json({"error": "multipart boundary required"}, 400)
                boundary = (boundary_match.group(1) or boundary_match.group(2)).encode("utf-8")
                filename, file_data = self._parse_multipart(payload, boundary)
                if not filename or file_data is None:
                    return self._json({"error": "no file supplied"}, 400)
                safe_name = _clean_name(filename)
                target = directory / safe_name
                try:
                    agent._resolve(area, (relative + "/" if relative else "") + safe_name,
                                   must_exist=False)
                    agent._atomic_file_write(target, file_data, overwrite=False)
                except FileExistsError:
                    return self._json({"error": "file already exists"}, 409)
                except AgentError as exc:
                    return self._json({"error": str(exc)}, 400)
                except OSError as exc:
                    return self._json({"error": str(exc)}, 500)
                self._json({"ok": True, "name": safe_name})

            @staticmethod
            def _parse_multipart(payload, boundary):
                marker = b"--" + boundary
                for part in payload.split(marker):
                    part = part.strip(b"\r\n")
                    if not part or part == b"--":
                        continue
                    if b"\r\n\r\n" not in part:
                        continue
                    headers, data = part.split(b"\r\n\r\n", 1)
                    match = re.search(
                        rb'Content-Disposition:[^\r\n]*filename="([^"]*)"',
                        headers, re.IGNORECASE)
                    if not match:
                        continue
                    data = data.rstrip(b"\r\n")
                    try:
                        name = match.group(1).decode("utf-8", errors="replace")
                    except Exception:
                        name = "upload.bin"
                    return name, data
                return None, None

            def _handle_write_action(self, path, data):
                area = data.get("area", "in")
                relative = data.get("path", "")
                _root, current = agent._resolve(area, relative, must_exist=True)
                if path == "/api/mkdir":
                    name = _clean_name(data.get("name", ""))
                    target_relative = (relative.rstrip("/") + "/" if relative else "") + name
                    _root, target = agent._resolve(area, target_relative, must_exist=False)
                    if target.exists():
                        return self._json({"error": "already exists"}, 409)
                    try:
                        target.mkdir()
                    except OSError as exc:
                        return self._json({"error": str(exc)}, 500)
                    return self._json({"ok": True, "name": name})
                if path == "/api/newfile":
                    name = _clean_name(data.get("name", ""))
                    target_relative = (relative.rstrip("/") + "/" if relative else "") + name
                    _root, target = agent._resolve(area, target_relative, must_exist=False)
                    if target.exists():
                        return self._json({"error": "already exists"}, 409)
                    content = data.get("content", "")
                    if not isinstance(content, str):
                        return self._json({"error": "content must be text"}, 400)
                    if len(content.encode("utf-8")) > MAX_TEXT_BYTES:
                        return self._json({"error": "text file too large"}, 413)
                    agent._atomic_file_write(target, content.encode("utf-8"), overwrite=False)
                    return self._json({"ok": True, "name": name})
                if path == "/api/write":
                    _root, target = agent._resolve(area, relative, must_exist=True)
                    if not target.is_file():
                        return self._json({"error": "file not found"}, 404)
                    content = data.get("content", "")
                    if not isinstance(content, str):
                        return self._json({"error": "content must be text"}, 400)
                    if len(content.encode("utf-8")) > MAX_TEXT_BYTES:
                        return self._json({"error": "text file too large"}, 413)
                    agent._atomic_file_write(target, content.encode("utf-8"), overwrite=True)
                    return self._json({"ok": True})
                if path == "/api/delete":
                    if not relative:
                        return self._json({"error": "refusing to delete area root"}, 400)
                    _root, target = agent._resolve(area, relative, must_exist=True)
                    if target.is_symlink() or target == _root:
                        return self._json({"error": "unsafe delete target"}, 400)
                    try:
                        if target.is_dir():
                            if any(target.iterdir()):
                                return self._json({"error": "folder is not empty"}, 400)
                            target.rmdir()
                        else:
                            target.unlink()
                    except OSError as exc:
                        return self._json({"error": str(exc)}, 500)
                    return self._json({"ok": True})
                return self._json({"error": "not found"}, 404)

            def do_GET(self):
                path, query = self._query()
                if path == "/":
                    page = agent.assets_dir / "index.html"
                    try:
                        payload = page.read_bytes()
                    except OSError:
                        return self._json({"error": "Hub web UI is missing"}, 500)
                    return self._send(200, "text/html; charset=utf-8", payload,
                                      {"Content-Security-Policy":
                                       "default-src 'self'; img-src 'self' https://i.ibb.co data:; "
                                       "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                                       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"})
                if path == "/api/health":
                    return self._json({
                        "ok": True, "name": "SPDW Device Agent",
                        "version": 1, "pairing_required": True,
                    })
                session_id, session = self._auth()
                if session is None:
                    return
                if path == "/api/list":
                    return self._file_list(query.get("area", "in"), query.get("path", ""))
                if path == "/api/read":
                    return self._file_read(query.get("area", "in"), query.get("path", ""))
                if path == "/api/download":
                    return self._file_download(query.get("area", "in"), query.get("path", ""))
                return self._json({"error": "not found"}, 404)

            def do_POST(self):
                path, query = self._query()
                payload = self._body()
                if payload is None:
                    return self._json({"error": "invalid or oversized request body"}, 413)
                if path == "/api/login":
                    form = self._form(payload)
                    pin = str((form or {}).get("pin", ""))
                    ip = agent._request_ip(self)
                    locked, retry_after = agent._login_locked(ip)
                    if locked:
                        return self._json({"error": "too many attempts; retry in {} seconds".format(
                            retry_after)}, 429, {"Retry-After": str(retry_after)})
                    expected = agent.pairing_pin
                    try:
                        valid = hmac.compare_digest(pin.encode("utf-8"),
                                                    expected.encode("utf-8"))
                    except (UnicodeError, TypeError):
                        valid = False
                    if not valid:
                        agent._login_failed(ip)
                        time.sleep(0.25)
                        return self._json({"error": "incorrect pairing PIN"}, 403)
                    agent._login_succeeded(ip)
                    session_id, csrf_token = agent._new_session()
                    cookie = ("spdw_session={}; HttpOnly; SameSite=Strict; "
                              "Path=/; Max-Age={}".format(session_id, SESSION_TTL))
                    return self._json({"ok": True, "csrf_token": csrf_token},
                                      200, {"Set-Cookie": cookie})
                session_id, session = self._auth()
                if session is None:
                    return
                if not self._csrf(session):
                    return
                if path == "/api/logout":
                    agent._revoke_session(session_id)
                    cookie = ("spdw_session=; HttpOnly; SameSite=Strict; "
                              "Path=/; Max-Age=0")
                    return self._json({"ok": True}, 200, {"Set-Cookie": cookie})
                if path == "/api/upload":
                    return self._file_upload(query, payload)
                data = self._form(payload)
                if data is None:
                    return self._json({"error": "invalid form body"}, 400)
                if path in ("/api/mkdir", "/api/newfile", "/api/write", "/api/delete"):
                    try:
                        return self._handle_write_action(path, data)
                    except AgentError as exc:
                        return self._json({"error": str(exc)}, 400)
                    except FileNotFoundError:
                        return self._json({"error": "path not found"}, 404)
                    except OSError as exc:
                        return self._json({"error": str(exc)}, 500)
                return self._json({"error": "not found"}, 404)

        return Handler
