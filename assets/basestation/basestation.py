#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  VOID BaseStation — Unified Console Command Center                           ║
║  Single-file edition (GUI + Embedded Daemon)                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

INDEX / TABLE OF CONTENTS
─────────────────────────
§1  BOOT SEQUENCE ............... Splash screen, dependency check, auto-installer
§2  CONSTANTS & PALETTE .......... UI colors, fonts, geometry defaults
§3  CONFIG MANAGER ............... JSON profile persistence, device registry
§4  NETWORK UTILS ................. Subnet scanner, port probe, IP discovery
§5  SSH MANAGER ................... Paramiko wrapper (exec, sftp, push)
§6  EMBEDDED DAEMON ............... ThreadingHTTPServer for console telemetry link
§7  TERMINAL PANEL ................ Interactive PTY-over-SSH widget (xterm-256color)
§8  UI COMPONENTS .................. HUD buttons, service cards, stat bars, tooltips
§9  MEDIA & SYNC PANEL ............. Framebuffer screenshot + two-way SFTP sync
§10 MAIN APPLICATION ............... VOID BaseStation root window & orchestration
§11 ENTRY POINT .................... main() launcher

DEPENDENCIES
────────────
  Required : paramiko, tkinter (usually bundled with Python)
  Optional : Pillow (for PNG screenshot export)

LOCALISATION
────────────
  All user-facing strings and code comments are in English.
"""

from __future__ import print_function

import base64
import getpass
import json
import os
import platform
import queue
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, font as tkfont
except ImportError:
    print("[FATAL] tkinter is required but not installed.")
    sys.exit(1)

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import webbrowser


# ══════════════════════════════════════════════════════════════════════════════
# §2  CONSTANTS & PALETTE
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME = "VOID BaseStation"
APP_VERSION = "3.0.0"
APP_TAG = "VOID-BS"

CONFIG_DIR = Path.home() / ".config" / "void_basestation"
CONFIG_FILE = CONFIG_DIR / "profiles.json"
DAEMON_CFG = CONFIG_DIR / "daemon.json"
INBOX_FILE = CONFIG_DIR / "inbox.jsonl"
OUTBOX_FILE = CONFIG_DIR / "outbox.json"

CONSOLE_APP_DIR = Path(__file__).resolve().parent / "console_app"
CONSOLE_APP_REMOTE = "/mnt/mmc/MUOS/application/VOID_Uplink"

BG0 = "#0d0d1a"
BG1 = "#1a1a2e"
PANEL_BG = "#111128"
CYAN = "#00ffcc"
MAGENTA = "#ff00ff"
ORANGE = "#ff6600"
RED = "#ff2244"
YELLOW = "#f0e130"
TEXT = "#e0e0e0"
TEXT_DIM = "#555577"
GRID = "#1e3a5f"
LOG_BG = "#08080f"
LOG_FG = "#00cc99"
TERM_BG = "#000000"
TERM_FG = "#d0d0d0"

FONT_FAMILY = "Courier New"
FONT = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_TITLE = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_TERM = (FONT_FAMILY, 10)

DEFAULT_SERVICES = {
    "ssh": {
        "label": "Secure Shell", "kind": "ssh", "auth": True,
        "port": 22, "user": "root", "pass": "root",
    },
    "sftp": {
        "label": "SFTP", "kind": "sftp", "auth": True,
        "port": 2022, "user": "muos", "pass": "muos",
    },
    "filebrowser": {
        "label": "FileBrowser (Web)", "kind": "web", "auth": True,
        "port": 9090, "user": "muos", "pass": "muos",
    },
    "vterm": {
        "label": "Virtual Terminal (Web)", "kind": "web", "auth": False,
        "port": 8080, "user": "", "pass": "",
    },
    "syncthing": {
        "label": "Syncthing (Web)", "kind": "web", "auth": False,
        "port": 7070, "user": "", "pass": "",
    },
}

SCAN_PORT_LABELS = {
    8080: "vterm", 9090: "filebrowser", 22: "ssh",
    2022: "sftp", 7070: "syncthing"
}

ANSI_COLORS = {
    30: "#1a1a1a", 31: "#e05561", 32: "#8cc265", 33: "#d2b967",
    34: "#4aa5f0", 35: "#c162de", 36: "#42c7da", 37: "#c7c7c7",
    90: "#5c5c5c", 91: "#ff6b7a", 92: "#a8e076", 93: "#f0d878",
    94: "#75b8f5", 95: "#d68af0", 96: "#67e0f2", 97: "#ffffff",
}

ANSI_CSI_RE = re.compile(r'\x1b\[([0-9;?]*)([A-Za-z])')
ANSI_OSC_RE = re.compile(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)')
ANSI_OTHER_RE = re.compile(r'\x1b[()][A-Za-z0-9]|\x1b[=>]')

DEFAULT_UPLINK = {
    "daemon_port": 31337,
    "daemon_autostart": True,
    "sync_pairs": [
        {"name": "Saves", "local": "", "remote": "/mnt/mmc/MUOS/save/file", "enabled": True},
        {"name": "States", "local": "", "remote": "/mnt/mmc/MUOS/save/state", "enabled": True},
    ],
    "rec_path": str(Path.home() / "Videos" / "VOID_Recordings"),
}


def make_banner(text, width=50):
    top = "╔" + "═" * width + "╗"
    mid = "║" + text.center(width) + "║"
    bot = "╚" + "═" * width + "╝"
    return "\n".join([top, mid, bot])


def status_color(state):
    return {
        "online": CYAN, "offline": RED, "checking": ORANGE, "unknown": TEXT_DIM,
    }.get(state, TEXT_DIM)


def open_ssh_terminal(ip, port, user):
    ssh_argv = ["ssh", "-p", str(port), "{}@{}".format(user, ip)]
    system = platform.system()
    if system == "Linux":
        candidates = [
            ["xfce4-terminal", "-x"] + ssh_argv,
            ["gnome-terminal", "--"] + ssh_argv,
            ["konsole", "-e"] + ssh_argv,
            ["x-terminal-emulator", "-e"] + ssh_argv,
            ["xterm", "-e"] + ssh_argv,
        ]
        for c in candidates:
            if shutil.which(c[0]):
                subprocess.Popen(c)
                return
        raise RuntimeError("no supported graphical terminal found")
    elif system == "Windows":
        subprocess.Popen(["cmd", "/K"] + ssh_argv)
        return
    elif system == "Darwin":
        cmd_str = " ".join(ssh_argv)
        script = 'tell application "Terminal" to do script "{}"'.format(cmd_str)
        subprocess.Popen(["osascript", "-e", script])
        return
    else:
        raise RuntimeError("unsupported operating system: {}".format(system))


# ══════════════════════════════════════════════════════════════════════════════
# §1  BOOT SEQUENCE — Dependency check & auto-install splash
# ══════════════════════════════════════════════════════════════════════════════

class BootSequence:
    """
    Displays a borderless splash window while checking for required and optional
    Python packages. If 'paramiko' is missing, prompts the user for the sudo
    password and attempts installation via pip.
    """

    REQUIRED = ["paramiko"]
    OPTIONAL = ["Pillow"]

    def __init__(self, root):
        self.root = root
        self.splash = tk.Toplevel(root)
        self.splash.overrideredirect(True)
        self.splash.configure(bg=BG0)
        self._center_window(520, 340)

        tk.Label(self.splash, text=make_banner("  V O I D   B A S E S T A T I O N  ", 54),
                 fg=CYAN, bg=BG0, font=FONT_BOLD, justify="center").pack(pady=(20, 8))

        self.status_lbl = tk.Label(self.splash, text="Initializing core systems...",
                                   fg=TEXT, bg=BG0, font=FONT)
        self.status_lbl.pack(pady=6)

        self.progress = tk.Label(self.splash, text="", fg=MAGENTA, bg=BG0, font=FONT_BOLD)
        self.progress.pack(pady=4)

        self.detail_lbl = tk.Label(self.splash, text="", fg=TEXT_DIM, bg=BG0,
                                   font=FONT_SMALL, wraplength=480, justify="center")
        self.detail_lbl.pack(pady=4)

        self._missing = []

    def _center_window(self, w, h):
        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() // 2) - (w // 2)
        y = (self.splash.winfo_screenheight() // 2) - (h // 2)
        self.splash.geometry("{}x{}+{}+{}".format(w, h, x, y))

    def run(self, on_complete):
        self._on_complete = on_complete
        self._animate_dot()
        self._stage0_check()

    def _animate_dot(self, count=0):
        if not self.splash.winfo_exists():
            return
        dots = "." * (count % 4)
        self.progress.config(text=dots)
        self.splash.after(300, lambda: self._animate_dot(count + 1))

    def _stage0_check(self):
        self.status_lbl.config(text="Checking dependencies...")
        self._missing = []
        details = []

        try:
            import paramiko
            details.append("[OK] paramiko found")
        except ImportError:
            self._missing.append("paramiko")
            details.append("[MISSING] paramiko not found")

        try:
            from PIL import Image
            details.append("[OK] Pillow found")
        except ImportError:
            details.append("[INFO] Pillow not found (PNG export disabled)")

        self.detail_lbl.config(text="\n".join(details))

        if "paramiko" in self._missing:
            self.splash.after(600, self._stage1_ask_install)
        else:
            self.splash.after(600, self._stage2_done)

    def _stage1_ask_install(self):
        self.status_lbl.config(text="Missing critical dependency: paramiko")
        self.detail_lbl.config(text="paramiko is required for SSH/SFTP connectivity.\n"
                                   "Enter your sudo password below to auto-install.")

        entry_frame = tk.Frame(self.splash, bg=BG0)
        entry_frame.pack(pady=8)
        self.pw_var = tk.StringVar()
        pw_entry = tk.Entry(entry_frame, textvariable=self.pw_var, show="*",
                            bg=BG1, fg=TEXT, insertbackground=CYAN, font=FONT,
                            width=30, relief="flat")
        pw_entry.pack(side="left", padx=4)
        pw_entry.bind("<Return>", lambda _e: self._stage1_install())
        pw_entry.focus_set()

        btn = tk.Button(entry_frame, text="Install", command=self._stage1_install,
                        bg=CYAN, fg=BG0, font=FONT_BOLD, relief="flat", cursor="hand2")
        btn.pack(side="left", padx=4)

        skip = tk.Button(entry_frame, text="Skip (limited mode)", command=self._stage2_done,
                         bg=BG1, fg=TEXT_DIM, font=FONT_SMALL, relief="flat", cursor="hand2")
        skip.pack(side="left", padx=4)

    def _stage1_install(self):
        password = self.pw_var.get()
        if not password:
            return
        self.status_lbl.config(text="Installing paramiko via pip...")
        self.detail_lbl.config(text="This may take a moment. Please wait...")

        def worker():
            try:
                proc = subprocess.Popen(
                    ["sudo", "-S", sys.executable, "-m", "pip", "install", "paramiko"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                out, err = proc.communicate((password + "\n").encode())
                try:
                    import paramiko
                    global HAS_PARAMIKO
                    HAS_PARAMIKO = True
                    self.splash.after(0, lambda: self._stage2_done())
                except ImportError:
                    msg = (err.decode() if err else out.decode())[:200]
                    self.splash.after(0, lambda m=msg: self._install_failed(m))
            except Exception as e:
                self.splash.after(0, lambda: self._install_failed(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _install_failed(self, msg):
        self.status_lbl.config(text="Installation failed", fg=RED)
        self.detail_lbl.config(text="Error:\n{}\n\nContinuing in limited mode.".format(msg))
        self.splash.after(2000, self._stage2_done)

    def _stage2_done(self):
        self.status_lbl.config(text="Boot sequence complete")
        self.detail_lbl.config(text="Launching VOID BaseStation...")
        self.splash.after(400, self._close_and_continue)

    def _close_and_continue(self):
        self.splash.destroy()
        self._on_complete()


# ══════════════════════════════════════════════════════════════════════════════
# §3  CONFIG MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = {
            "devices": {},
            "last_used": None,
            "auto_connect": None,
            "window_geometry": None,
            "uplink": json.loads(json.dumps(DEFAULT_UPLINK))
        }
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.data.update(loaded)
            except Exception:
                pass
        up = self.data.setdefault("uplink", {})
        for k, v in DEFAULT_UPLINK.items():
            up.setdefault(k, json.loads(json.dumps(v)))

    def uplink(self):
        return self.data["uplink"]

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add_device(self, name, ip, services=None):
        self.data["devices"][name] = {
            "ip": ip,
            "services": services if services is not None else json.loads(json.dumps(DEFAULT_SERVICES)),
            "added": datetime.now().isoformat(timespec="seconds"),
        }
        self.data["last_used"] = name
        self.save()

    def remove_device(self, name):
        self.data["devices"].pop(name, None)
        if self.data.get("last_used") == name:
            self.data["last_used"] = next(iter(self.data["devices"]), None)
        if self.data.get("auto_connect") == name:
            self.data["auto_connect"] = None
        self.save()

    def update_device(self, name, **kwargs):
        if name in self.data["devices"]:
            self.data["devices"][name].update(kwargs)
            self.save()

    def list_devices(self):
        return self.data["devices"]

    def get_device(self, name):
        return self.data["devices"].get(name)


# ══════════════════════════════════════════════════════════════════════════════
# §4  NETWORK UTILS
# ══════════════════════════════════════════════════════════════════════════════

class NetworkUtils:
    @staticmethod
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    @staticmethod
    def check_port(ip, port, timeout=0.6):
        if not port:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex((ip, int(port))) == 0
        except Exception:
            return False

    @staticmethod
    def get_hostname(ip):
        try:
            return socket.gethostbyaddr(ip)[0].split(".")[0]
        except Exception:
            return None

    @staticmethod
    def scan_subnet(progress_cb=None, ports=(8080, 9090, 22, 2022, 7070),
                     timeout=0.35, max_workers=60):
        local_ip = NetworkUtils.get_local_ip()
        prefix = ".".join(local_ip.split(".")[:3])
        found = []
        found_lock = threading.Lock()
        progress_lock = threading.Lock()
        q = queue.Queue()
        for i in range(1, 255):
            q.put("{}.{}".format(prefix, i))

        def worker():
            while True:
                try:
                    ip = q.get_nowait()
                except queue.Empty:
                    return
                hits = [p for p in ports if NetworkUtils.check_port(ip, p, timeout)]
                if hits:
                    hostname = NetworkUtils.get_hostname(ip)
                    with found_lock:
                        found.append((ip, hits, hostname))
                if progress_cb:
                    with progress_lock:
                        progress_cb()
                q.task_done()

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(max_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return sorted(found)


# ══════════════════════════════════════════════════════════════════════════════
# §5  SSH MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class SSHManager:
    @staticmethod
    def _require_paramiko():
        if not HAS_PARAMIKO:
            raise RuntimeError("paramiko is not installed")

    @staticmethod
    def exec_command(ip, port, user, password, command, timeout=8):
        SSHManager._require_paramiko()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, port=int(port), username=user, password=password,
                           timeout=timeout, banner_timeout=timeout, auth_timeout=timeout)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            return out, err
        finally:
            client.close()

    @staticmethod
    def push_file(ip, port, user, password, local_path, remote_path, timeout=10):
        SSHManager._require_paramiko()
        transport = paramiko.Transport((ip, int(port)))
        try:
            transport.connect(username=user, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                sftp.put(local_path, remote_path)
            finally:
                sftp.close()
        finally:
            transport.close()


# ══════════════════════════════════════════════════════════════════════════════
# §6  EMBEDDED DAEMON — HTTP telemetry & message hub
# ══════════════════════════════════════════════════════════════════════════════

class DaemonStore:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.cfg = {"port": 31337, "pc_name": "", "token": ""}
        self._lock = threading.Lock()
        if DAEMON_CFG.exists():
            try:
                self.cfg.update(json.loads(DAEMON_CFG.read_text(encoding="utf-8")))
            except Exception:
                pass

    def outbox_read(self, drain=False):
        with self._lock:
            if not OUTBOX_FILE.exists():
                return []
            try:
                items = json.loads(OUTBOX_FILE.read_text(encoding="utf-8"))
            except Exception:
                items = []
            if drain:
                OUTBOX_FILE.write_text("[]", encoding="utf-8")
            return items

    def outbox_push(self, title, body=""):
        with self._lock:
            items = []
            if OUTBOX_FILE.exists():
                try:
                    items = json.loads(OUTBOX_FILE.read_text(encoding="utf-8"))
                except Exception:
                    items = []
            items.append({"title": str(title)[:80], "body": str(body)[:300],
                          "ts": datetime.now().isoformat(timespec="seconds")})
            items = items[-50:]
            OUTBOX_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    def inbox_push(self, title, body=""):
        rec = {"title": str(title)[:80], "body": str(body)[:300],
               "ts": datetime.now().isoformat(timespec="seconds"), "read": False}
        with self._lock:
            with open(INBOX_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def make_daemon_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "{}/{}".format(APP_TAG, APP_VERSION)

        def log_message(self, fmt, *args):
            pass

        def _auth_ok(self):
            token = store.cfg.get("token", "")
            if not token:
                return True
            return self.headers.get("X-SPDW-Token", "") == token

        def _json(self, obj, code=200):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                n = 0
            if n <= 0 or n > 65536:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8", errors="replace"))
            except Exception:
                return {}

        def do_GET(self):
            if not self._auth_ok():
                return self._json({"error": "unauthorized"}, 401)
            path = urllib.parse.urlparse(self.path).path
            if path == "/ping":
                self._json({"ok": True,
                            "name": store.cfg.get("pc_name") or socket.gethostname(),
                            "version": APP_VERSION,
                            "ts": datetime.now().isoformat(timespec="seconds")})
            elif path == "/outbox":
                self._json({"messages": store.outbox_read(drain=True)})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            if not self._auth_ok():
                return self._json({"error": "unauthorized"}, 401)
            path = urllib.parse.urlparse(self.path).path
            data = self._body()
            if path == "/notify":
                title = data.get("title", "Console")
                body = data.get("body", "")
                store.inbox_push(title, body)
                print("[{}] NOTIFICATION from console -> {}: {}".format(
                    datetime.now().isoformat(timespec="seconds"), title, body), flush=True)
                self._json({"ok": True})
            elif path == "/outbox":
                title = data.get("title", "")
                body = data.get("body", "")
                if not title:
                    return self._json({"error": "title required"}, 400)
                store.outbox_push(title, body)
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)

    return Handler


class EmbeddedDaemon:
    """Runs the HTTP daemon inside the same process (background thread)."""

    def __init__(self, cfg_manager):
        self.cfg_mgr = cfg_manager
        self.port = int(self.cfg_mgr.uplink().get("daemon_port", 31337))
        self.store = DaemonStore()
        self.httpd = None
        self._thread = None

    def is_running(self):
        return self.httpd is not None

    def start(self):
        if self.is_running():
            return True
        try:
            self.store.cfg["port"] = self.port
            handler = make_daemon_handler(self.store)
            ThreadingHTTPServer.allow_reuse_address = True
            self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
            self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print("[DAEMON] Failed to start:", e, flush=True)
            return False

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    def api_get(self, path, timeout=4):
        url = "http://127.0.0.1:{}{}".format(self.port, path)
        req = urllib.request.Request(url, headers={"User-Agent": "{}/{}".format(APP_TAG, APP_VERSION)})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def api_post(self, path, payload, timeout=4):
        url = "http://127.0.0.1:{}{}".format(self.port, path)
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "{}/{}".format(APP_TAG, APP_VERSION)})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def read_inbox_tail(self, offset):
        if not INBOX_FILE.exists():
            return [], 0
        size = INBOX_FILE.stat().st_size
        if offset > size:
            offset = 0
        with open(INBOX_FILE, "r", encoding="utf-8") as f:
            f.seek(offset)
            lines = f.readlines()
            new_offset = f.tell()
        out = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out, new_offset


# ══════════════════════════════════════════════════════════════════════════════
# §7  TERMINAL PANEL — Interactive PTY-over-SSH
# ══════════════════════════════════════════════════════════════════════════════

class TerminalPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG0)
        self.app = app
        self.client = None
        self.channel = None
        self.connected = False
        self.current_device_name = None
        self.term_queue = queue.Queue()
        self._current_tags = ["default_fg"]
        self._resize_after_id = None
        self._device_names = []

        bar = tk.Frame(self, bg=BG0)
        bar.pack(fill="x", pady=(0, 6))

        tk.Label(bar, text="Device:", fg=TEXT, bg=BG0, font=FONT_SMALL).pack(side="left")
        self.device_var = tk.StringVar()
        self.device_menu = tk.OptionMenu(bar, self.device_var, "")
        self.device_menu.config(bg=BG1, fg=CYAN, font=FONT_SMALL, relief="flat", bd=0,
                                highlightthickness=0, activebackground=CYAN, activeforeground=BG0,
                                padx=8, cursor="hand2")
        self.device_menu["menu"].config(bg=BG1, fg=TEXT, font=FONT_SMALL,
                                          activebackground=CYAN, activeforeground=BG0)
        self.device_menu.pack(side="left", padx=6)

        self.connect_btn = tk.Button(bar, text="Connect", command=self.toggle_connect,
                                     bg=CYAN, fg=BG0, font=FONT_BOLD, relief="flat", padx=10, cursor="hand2")
        self.connect_btn.pack(side="left", padx=4)

        self.status_dot = tk.Label(bar, text="●", fg=RED, bg=BG0, font=FONT_BOLD)
        self.status_dot.pack(side="left", padx=(10, 2))
        self.status_lbl = tk.Label(bar, text="Disconnected", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL)
        self.status_lbl.pack(side="left")

        tk.Button(bar, text="Power Off", command=lambda: self.quick_cmd("poweroff", confirm=True),
                  bg=RED, fg=BG0, font=FONT_SMALL, relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)
        tk.Button(bar, text="Reboot", command=lambda: self.quick_cmd("reboot", confirm=True),
                  bg=ORANGE, fg=BG0, font=FONT_SMALL, relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)
        tk.Button(bar, text="SysInfo", command=lambda: self.quick_cmd("uname -a && uptime && df -h", confirm=False),
                  bg=MAGENTA, fg=BG0, font=FONT_SMALL, relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)
        tk.Button(bar, text="Clear", command=self.clear_screen,
                  bg=TEXT_DIM, fg=BG0, font=FONT_SMALL, relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)

        term_frame = tk.Frame(self, bg=GRID, highlightbackground=GRID, highlightthickness=1)
        term_frame.pack(fill="both", expand=True)

        self.text = tk.Text(term_frame, bg=TERM_BG, fg=TERM_FG, insertbackground=CYAN,
                            font=FONT_TERM, wrap="char", undo=False,
                            padx=8, pady=6, bd=0, highlightthickness=0)
        vs = tk.Scrollbar(term_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=vs.set)
        self.text.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

        hint = tk.Label(self, text="Click terminal to type · Ctrl+C copies selection or sends SIGINT · Ctrl+V pastes",
                        fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, anchor="w")
        hint.pack(fill="x", pady=(4, 0))

        self._setup_tags()
        self._bind_keys()
        self.text.bind("<Configure>", self._on_resize_debounced)
        self.after(100, self._poll_term_queue)

    def _setup_tags(self):
        for code, color in ANSI_COLORS.items():
            self.text.tag_configure("fg{}".format(code), foreground=color)
        self.text.tag_configure("bold", font=(FONT_FAMILY, FONT_TERM[1], "bold"))
        self.text.tag_configure("default_fg", foreground=TERM_FG)

    def _bind_keys(self):
        t = self.text
        t.bind("<Control-c>", self._on_ctrl_c)
        t.bind("<Control-v>", self._on_ctrl_v)
        t.bind("<Key>", self._on_key)
        t.bind("<BackSpace>", lambda e: self._send_bytes(b"\x7f"))
        t.bind("<Return>", lambda e: self._send_bytes(b"\r"))
        t.bind("<Tab>", lambda e: self._send_bytes(b"\t"))
        t.bind("<Up>", lambda e: self._send_bytes(b"\x1b[A"))
        t.bind("<Down>", lambda e: self._send_bytes(b"\x1b[B"))
        t.bind("<Right>", lambda e: self._send_bytes(b"\x1b[C"))
        t.bind("<Left>", lambda e: self._send_bytes(b"\x1b[D"))
        t.bind("<Escape>", lambda e: self._send_bytes(b"\x1b"))
        t.bind("<Delete>", lambda e: self._send_bytes(b"\x1b[3~"))
        t.bind("<Home>", lambda e: self._send_bytes(b"\x1bOH"))
        t.bind("<End>", lambda e: self._send_bytes(b"\x1bOF"))

    def refresh_devices(self, select=None):
        names = list(self.app.cfg.list_devices().keys())
        self._device_names = names
        menu = self.device_menu["menu"]
        menu.delete(0, "end")
        for n in names:
            menu.add_command(label=n, command=lambda v=n: self.device_var.set(v))
        current = self.device_var.get()
        if self.connected and self.current_device_name in names:
            self.device_var.set(self.current_device_name)
        elif select and select in names:
            self.device_var.set(select)
        elif current in names:
            pass
        elif names:
            self.device_var.set(names[0])
        else:
            self.device_var.set("")

    def toggle_connect(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        if not HAS_PARAMIKO:
            messagebox.showwarning("Terminal", "paramiko is required. Install it to use the terminal.")
            return
        name = self.device_var.get()
        d = self.app.cfg.get_device(name)
        if not d:
            messagebox.showinfo("Terminal", "Select a device from the menu first.")
            return
        ssh_svc = d["services"].get("ssh")
        if not ssh_svc:
            messagebox.showwarning("Terminal", "'{}' does not have the SSH service enabled.".format(name))
            return

        self.status_lbl.config(text="Connecting...", fg=ORANGE)
        self.status_dot.config(fg=ORANGE)
        self.connect_btn.config(state="disabled")

        def worker():
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(d["ip"], port=int(ssh_svc["port"]), username=ssh_svc["user"],
                               password=ssh_svc["pass"], timeout=10, banner_timeout=10, auth_timeout=10)
                cols, rows = self._term_size()
                channel = client.invoke_shell(term="xterm-256color", width=cols, height=rows)
                channel.settimeout(0.5)

                self.client = client
                self.channel = channel
                self.current_device_name = name
                self.connected = True
                self.term_queue.put(("connected", None))
                self._reader_loop(channel)
            except Exception as e:
                self.connected = False
                self.term_queue.put(("connect_error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _reader_loop(self, channel):
        try:
            while self.connected:
                try:
                    data = channel.recv(4096)
                except socket.timeout:
                    continue
                except Exception:
                    break
                if not data:
                    break
                self.term_queue.put(("data", data))
        except Exception:
            pass
        finally:
            self.connected = False
            self.term_queue.put(("disconnected", None))

    def disconnect(self):
        self.connected = False
        try:
            if self.channel:
                self.channel.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.channel = None
        self.client = None
        self.status_lbl.config(text="Disconnected", fg=TEXT_DIM)
        self.status_dot.config(fg=RED)
        self.connect_btn.config(text="Connect", state="normal")
        if self.current_device_name:
            self.app.log("Terminal disconnected from {}".format(self.current_device_name), "warn")

    def _poll_term_queue(self):
        try:
            while True:
                kind, payload = self.term_queue.get_nowait()
                if kind == "data":
                    self._feed(payload)
                elif kind == "connected":
                    self.status_lbl.config(text="Connected — {}".format(self.current_device_name), fg=CYAN)
                    self.status_dot.config(fg=CYAN)
                    self.connect_btn.config(text="Disconnect", state="normal")
                    self.app.log("Terminal connected to {}".format(self.current_device_name), "ok")
                    self.text.focus_set()
                elif kind == "connect_error":
                    self.status_lbl.config(text="Connection error", fg=RED)
                    self.status_dot.config(fg=RED)
                    self.connect_btn.config(text="Connect", state="normal")
                    self.app.log("Terminal error: {}".format(payload), "err")
                    messagebox.showerror("Terminal", "Connection failed:\n{}".format(payload))
                elif kind == "disconnected":
                    if self.connect_btn["text"] != "Connect":
                        self.status_lbl.config(text="Disconnected (session ended)", fg=TEXT_DIM)
                        self.status_dot.config(fg=RED)
                        self.connect_btn.config(text="Connect", state="normal")
        except queue.Empty:
            pass
        self.after(80, self._poll_term_queue)

    def _send_bytes(self, data):
        if self.connected and self.channel:
            try:
                self.channel.send(data)
            except Exception:
                pass
        return "break"

    def _on_key(self, event):
        if self.connected:
            ch = event.char
            if ch and (ord(ch) >= 32 or ch == "\t"):
                self._send_bytes(ch.encode("utf-8", errors="ignore"))
        return "break"

    def _on_ctrl_c(self, event):
        try:
            if self.text.tag_ranges("sel"):
                selected = self.text.get("sel.first", "sel.last")
                self.text.clipboard_clear()
                self.text.clipboard_append(selected)
                return "break"
        except tk.TclError:
            pass
        self._send_bytes(b"\x03")
        return "break"

    def _on_ctrl_v(self, event):
        try:
            data = self.text.clipboard_get()
            self._send_bytes(data.encode("utf-8", errors="ignore"))
        except tk.TclError:
            pass
        return "break"

    def quick_cmd(self, cmd, confirm=False):
        if not self.connected:
            messagebox.showinfo("Terminal", "Connect to a device first.")
            return
        if confirm and not messagebox.askyesno("Confirm", "Execute '{}' on {}?".format(cmd, self.current_device_name)):
            return
        self._send_bytes((cmd + "\n").encode("utf-8"))

    def clear_screen(self):
        self.text.delete("1.0", "end")

    def _feed(self, data):
        text = data.decode("utf-8", errors="replace")
        self._feed_str(text)

    def _feed_str(self, s):
        s = ANSI_OSC_RE.sub("", s)
        s = ANSI_OTHER_RE.sub("", s)
        pos = 0
        for m in ANSI_CSI_RE.finditer(s):
            literal = s[pos:m.start()]
            if literal:
                self._write_literal(literal)
            params, final = m.group(1), m.group(2)
            if final == "m":
                self._current_tags = self._sgr_tags(params, self._current_tags)
            elif final == "J" and params in ("2", "3", ""):
                self.text.delete("1.0", "end")
            elif final == "K":
                p = params or "0"
                if p == "0":
                    self.text.delete("insert", "insert lineend")
                elif p == "1":
                    self.text.delete("insert linestart", "insert")
                elif p == "2":
                    self.text.delete("insert linestart", "insert lineend")
            pos = m.end()
        literal = s[pos:]
        if literal:
            self._write_literal(literal)
        self._trim_scrollback()
        self.text.see("end")

    def _write_literal(self, text):
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\r":
                if not (i + 1 < n and text[i + 1] == "\n"):
                    self.text.mark_set("insert", "insert linestart")
                i += 1
            elif ch == "\n":
                self.text.insert("insert", "\n")
                i += 1
            elif ch in ("\x08", "\x7f"):
                self.text.delete("insert -1c", "insert")
                i += 1
            elif ch == "\x07":
                i += 1
            else:
                j = i
                while j < n and text[j] not in ("\r", "\n", "\x08", "\x7f", "\x07"):
                    j += 1
                chunk = text[i:j]
                self.text.insert("insert", chunk, tuple(self._current_tags))
                i = j

    def _sgr_tags(self, params, current):
        codes = [int(p) for p in params.split(";") if p != ""] if params else [0]
        tags = list(current)
        for code in codes:
            if code == 0:
                tags = ["default_fg"]
            elif code == 1:
                if "bold" not in tags:
                    tags.append("bold")
            elif code == 22:
                tags = [t for t in tags if t != "bold"]
            elif code in ANSI_COLORS:
                tags = [t for t in tags if not t.startswith("fg")] + ["fg{}".format(code)]
            elif code == 39:
                tags = [t for t in tags if not t.startswith("fg")] + ["default_fg"]
        return tags

    def _trim_scrollback(self, max_lines=4000):
        try:
            total = int(self.text.index("end-1c").split(".")[0])
            if total > max_lines:
                self.text.delete("1.0", "{}".format(total - max_lines))
        except Exception:
            pass

    def _on_resize_debounced(self, _event=None):
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(300, self._apply_resize)

    def _apply_resize(self):
        self._resize_after_id = None
        if self.connected and self.channel:
            cols, rows = self._term_size()
            try:
                self.channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def _term_size(self):
        try:
            font = tkfont.Font(font=self.text.cget("font"))
            char_w = max(font.measure("M"), 1)
            char_h = max(font.metrics("linespace"), 1)
            w = max(self.text.winfo_width(), 200)
            h = max(self.text.winfo_height(), 100)
            cols = max(w // char_w, 20)
            rows = max(h // char_h, 5)
            return cols, rows
        except Exception:
            return 80, 24


# ══════════════════════════════════════════════════════════════════════════════
# §8  UI COMPONENTS — HUD buttons, cards, tooltips, stat bars
# ══════════════════════════════════════════════════════════════════════════════

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+{}+{}".format(x, y))
        label = tk.Label(tw, text=self.text, bg="#2a2a4e", fg=TEXT,
                         font=FONT_SMALL, padx=6, pady=3, relief="solid", bd=1)
        label.pack()

    def _on_leave(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class HudButton(tk.Button):
    def __init__(self, parent, text, command, accent=None, tooltip=None, **kw):
        accent = accent or CYAN
        super().__init__(
            parent, text=text, command=command,
            bg=BG1, fg=accent, activebackground=accent, activeforeground=BG0,
            disabledforeground=TEXT_DIM,
            font=FONT_SMALL, relief="flat", bd=0, padx=10, pady=5,
            cursor="hand2", **kw
        )
        self._accent = accent
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        if tooltip:
            ToolTip(self, tooltip)

    def _on_enter(self, _e):
        if str(self["state"]) != "disabled":
            self.config(bg=self._accent, fg=BG0)

    def _on_leave(self, _e):
        if str(self["state"]) != "disabled":
            self.config(bg=BG1, fg=self._accent)


class ServiceCard(tk.Frame):
    def __init__(self, parent, key, svc, app):
        super().__init__(parent, bg=PANEL_BG, highlightbackground=GRID,
                         highlightcolor=GRID, highlightthickness=1, padx=10, pady=8)
        self.key = key
        self.svc = svc
        self.app = app
        self.state = "unknown"

        top = tk.Frame(self, bg=PANEL_BG)
        top.pack(fill="x")
        self.dot = tk.Label(top, text="●", fg=TEXT_DIM, bg=PANEL_BG, font=FONT_BOLD)
        self.dot.pack(side="left")
        tk.Label(top, text=" {}".format(svc["label"]), fg=CYAN, bg=PANEL_BG, font=FONT_BOLD).pack(side="left")

        ip = app.current_ip()
        info = "{}:{}".format(ip, svc["port"]) if svc.get("port") else "managed via SSH"
        tk.Label(self, text=info, fg=TEXT_DIM, bg=PANEL_BG, font=FONT_SMALL, anchor="w").pack(fill="x")

        box = tk.Frame(self, bg=PANEL_BG)
        box.pack(fill="x", pady=(6, 0))
        self._build_buttons(box)

    def _build_buttons(self, parent):
        kind = self.svc["kind"]
        if kind == "ssh":
            r1 = tk.Frame(parent, bg=PANEL_BG)
            r1.pack(fill="x")
            HudButton(r1, "External Terminal", lambda: self.app.action_open_ssh(self.svc)).pack(side="left", padx=2, pady=1)
            HudButton(r1, "Embedded Terminal", lambda: self.app.action_open_embedded_terminal(), accent=MAGENTA).pack(side="left", padx=2, pady=1)
            r2 = tk.Frame(parent, bg=PANEL_BG)
            r2.pack(fill="x")
            HudButton(r2, "Quick Command", lambda: self.app.action_quick_command(self.svc)).pack(side="left", padx=2, pady=1)
            HudButton(r2, "Copy SSH", lambda: self.app.action_copy_ssh(self.svc)).pack(side="left", padx=2, pady=1)
        elif kind == "sftp":
            HudButton(parent, "Open Client", lambda: self.app.action_open_sftp(self.svc)).pack(side="left", padx=2, pady=1)
            HudButton(parent, "Send File...", lambda: self.app.action_push_file(self.svc)).pack(side="left", padx=2, pady=1)
        elif kind == "web":
            HudButton(parent, "Open Browser", lambda: self.app.action_open_web(self.svc)).pack(side="left", padx=2, pady=1)
            if self.svc.get("user"):
                HudButton(parent, "Copy Credentials", lambda: self.app.action_copy_creds(self.svc)).pack(side="left", padx=2, pady=1)

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.dot.config(fg=status_color(state))


class StatBar(tk.Canvas):
    def __init__(self, parent, label, unit="%", width=300, height=52, **kw):
        super().__init__(parent, width=width, height=height, bg=PANEL_BG,
                         highlightbackground=GRID, highlightthickness=1, **kw)
        self.label = label
        self.unit = unit
        self.pct = 0.0
        self.value_text = "—"
        self._last_drawn = None
        self._resize_after_id = None
        self.bind("<Configure>", self._on_resize)
        self._draw()

    def _on_resize(self, _event=None):
        if self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(200, self._draw)

    def set(self, pct, value_text=None, sub_text=None):
        new_pct = max(0.0, min(100.0, float(pct or 0)))
        new_value = value_text if value_text is not None else "{:.1f}{}".format(new_pct, self.unit)
        new_sub = sub_text or ""
        if (abs(new_pct - self.pct) > 0.5 or
                self.value_text != new_value or
                getattr(self, "sub_text", "") != new_sub):
            self.pct = new_pct
            self.value_text = new_value
            self.sub_text = new_sub
            self._draw()

    def _draw(self):
        w = max(self.winfo_width(), 120)
        h = max(self.winfo_height(), 48)
        pct = self.pct
        color = CYAN if pct < 60 else (ORANGE if pct < 85 else RED)
        sub = getattr(self, "sub_text", "")
        current = (w, h, pct, color, self.value_text, sub)
        if self._last_drawn == current:
            return
        self._last_drawn = current
        self.delete("all")
        bar_y = h - 10
        bar_w = int((w - 8) * pct / 100.0)
        self.create_rectangle(4, bar_y, w - 4, bar_y + 6, fill=BG1, outline="")
        if bar_w > 0:
            self.create_rectangle(4, bar_y, 4 + bar_w, bar_y + 6, fill=color, outline="")
        self.create_text(8, 6, text=self.label, anchor="nw", fill=TEXT, font=FONT_SMALL)
        self.create_text(w - 8, 6, text=self.value_text, anchor="ne", fill=color, font=FONT_BOLD)
        if sub:
            self.create_text(8, 22, text=sub, anchor="nw", fill=TEXT_DIM, font=(FONT_FAMILY, 8))


# ══════════════════════════════════════════════════════════════════════════════
# §9  MEDIA & SYNC PANEL — Framebuffer screenshot + two-way SFTP sync
# ══════════════════════════════════════════════════════════════════════════════

PROBE_SCRIPT = r"""
echo "PROBE_BEGIN"
read c1 < /proc/stat; sleep 0.4; read c2 < /proc/stat
echo "CPU_STAT1=$(echo $c1 | cut -d' ' -f2-)"
echo "CPU_STAT2=$(echo $c2 | cut -d' ' -f2-)"
echo "LOAD=$(cut -d' ' -f1-3 /proc/loadavg)"
echo "UPTIME=$(cut -d' ' -f1 /proc/uptime)"
echo "MEMTOTAL=$(awk '/MemTotal/{print $2}' /proc/meminfo)"
echo "MEMAVAIL=$(awk '/MemAvailable/{print $2}' /proc/meminfo)"
for p in /sys/class/power_supply/*; do
  [ -f "$p/capacity" ] || continue
  echo "BAT_NAME=$(basename $p)"
  echo "BAT_CAP=$(cat $p/capacity 2>/dev/null)"
  echo "BAT_STATUS=$(cat $p/status 2>/dev/null)"
  [ -f "$p/current_now" ] && echo "BAT_CUR=$(cat $p/current_now)"
  break
done
for z in /sys/class/thermal/thermal_zone*; do
  [ -f "$z/temp" ] || continue
  echo "TEMP=$(cat $z/type 2>/dev/null):$(cat $z/temp)"
done
for m in /mnt/mmc /mnt/sdcard /; do
  df -k "$m" 2>/dev/null | awk -v M="$m" 'NR==2{printf "DISK=%s:%s:%s:%s\n", M, $2, $3, $5}'
done
for i in wlan0 eth0 usb0; do
  [ -d "/sys/class/net/$i" ] || continue
  ip=$(ip -4 -o addr show $i 2>/dev/null | awk '{split($4,a,"/"); print a[1]}')
  rx=$(cat /sys/class/net/$i/statistics/rx_bytes 2>/dev/null)
  tx=$(cat /sys/class/net/$i/statistics/tx_bytes 2>/dev/null)
  [ -n "$ip$rx" ] && echo "NET=$i:$ip:$rx:$tx"
done
awk '/wlan/{printf "WIFI_SIG=%s\n", $4}' /proc/net/wireless 2>/dev/null
for b in /sys/class/backlight/*; do
  [ -f "$b/brightness" ] || continue
  echo "BRIGHT=$(cat $b/brightness):$(cat $b/max_brightness 2>/dev/null)"
  break
done
vol=$(amixer sget Master 2>/dev/null | awk -F'[][]' '/\\[/{print $2; exit}' | tr -d '%')
[ -n "$vol" ] && echo "VOL=$vol"
app=""; appcmd=""
for d in /proc/[0-9]*; do
  [ -r "$d/cmdline" ] || continue
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null)
  case "$cmd" in
    *retroarch*) app="RETROARCH"; appcmd="$cmd"; break;;
    */drastic*|*DraStic*) app="DRASTIC"; appcmd="$cmd"; break;;
    *PPSSPP*|*ppsspp*) app="PPSSPP"; appcmd="$cmd"; break;;
    *mupen64plus*) app="MUPEN64"; appcmd="$cmd"; break;;
    *flycast*) app="FLYCAST"; appcmd="$cmd"; break;;
    *scummvm*) app="SCUMMVM"; appcmd="$cmd"; break;;
    *pico8*) app="PICO8"; appcmd="$cmd"; break;;
    *PortMaster*) app="PORTMASTER"; appcmd="$cmd"; break;;
  esac
done
if [ -z "$app" ]; then
  for d in /proc/[0-9]*; do
    [ -r "$d/comm" ] || continue
    c=$(cat "$d/comm" 2>/dev/null)
    case "$c" in
      mux*) app="MUOS:$c"; break;;
    esac
  done
fi
echo "APP=${app:-IDLE}"
if [ "$app" = "RETROARCH" ]; then
  rom=$(echo "$appcmd" | grep -o '"[^"]*"' | tail -n1 | tr -d '"')
  [ -n "$rom" ] && echo "ROM=$(basename "$rom")"
fi
echo "PROBE_END"
"""


def parse_probe(text):
    s = {"temps": [], "disks": [], "nets": [], "raw": text}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key in ("CPU_STAT1", "CPU_STAT2"):
            try:
                vals = [int(x) for x in val.split()]
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                s[key] = (idle, sum(vals))
            except Exception:
                pass
        elif key == "LOAD":
            try:
                s["load"] = [float(x) for x in val.split()[:3]]
            except Exception:
                s["load"] = []
        elif key == "UPTIME":
            try:
                s["uptime_s"] = float(val)
            except Exception:
                pass
        elif key in ("MEMTOTAL", "MEMAVAIL", "BAT_CAP", "VOL"):
            try:
                s[key.lower()] = int(val)
            except Exception:
                s[key.lower()] = val
        elif key in ("BAT_NAME", "BAT_STATUS", "BAT_CUR", "APP", "ROM", "WIFI_SIG"):
            s[key.lower()] = val
        elif key == "TEMP":
            try:
                zone, t = val.split(":", 1)
                tc = int(t) / 1000.0
                if 0 < tc < 150:
                    s["temps"].append({"zone": zone, "temp_c": round(tc, 1)})
            except Exception:
                pass
        elif key == "DISK":
            try:
                mount, total, used, pct = val.split(":")
                s["disks"].append({"mount": mount,
                                   "total_mb": round(int(total) / 1024, 0),
                                   "used_mb": round(int(used) / 1024, 0),
                                   "pct": int(pct.rstrip("%"))})
            except Exception:
                pass
        elif key == "NET":
            try:
                iface, ip, rx, tx = val.split(":")
                s["nets"].append({"iface": iface, "ip": ip,
                                  "rx": int(rx or 0), "tx": int(tx or 0)})
            except Exception:
                pass
        elif key == "BRIGHT":
            try:
                cur, mx = val.split(":")
                s["brightness"] = int(cur)
                s["brightness_max"] = int(mx or 255)
            except Exception:
                pass
    if "CPU_STAT1" in s and "CPU_STAT2" in s:
        didle = s["CPU_STAT2"][0] - s["CPU_STAT1"][0]
        dtot = s["CPU_STAT2"][1] - s["CPU_STAT1"][1]
        s["cpu_pct"] = round(100.0 * (1.0 - didle / dtot), 1) if dtot > 0 else 0.0
    if "memtotal" in s:
        total = s["memtotal"]
        used = total - s.get("memavail", 0)
        s["ram"] = {"total_mb": round(total / 1024, 0), "used_mb": round(used / 1024, 0),
                    "pct": round(100.0 * used / total, 1) if total else 0.0}
    s["ts"] = time.time()
    return s


class ConsoleMonitor:
    """Lightweight background monitor that probes a console via SSH."""

    def __init__(self, status_queue, interval=2.5):
        self.q = status_queue
        self.interval = interval
        self.client = None
        self.device = None
        self.svc = None
        self.running = False
        self.connected = False
        self._thread = None
        self._net_prev = {}
        self.last_stats = None

    def set_device(self, device, ssh_svc):
        self.disconnect()
        self.device = device
        self.svc = ssh_svc

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.disconnect()

    def disconnect(self):
        self.connected = False
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.client = None

    def _connect(self):
        if not HAS_PARAMIKO or not self.device or not self.svc:
            return False
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(self.device["ip"], port=int(self.svc["port"]),
                      username=self.svc["user"], password=self.svc["pass"],
                      timeout=6, banner_timeout=6, auth_timeout=6)
            self.client = c
            self.connected = True
            self.q.put(("monitor_state", True))
            return True
        except Exception as e:
            self.connected = False
            self.q.put(("monitor_error", str(e)[:120]))
            return False

    def _loop(self):
        backoff = 0
        while self.running:
            if not self.client:
                if not self.device:
                    time.sleep(1.0)
                    continue
                if self._connect():
                    backoff = 0
                else:
                    backoff = min(backoff + 2, 10)
                    time.sleep(backoff)
                    continue
            try:
                _stdin, stdout, _stderr = self.client.exec_command(PROBE_SCRIPT, timeout=8)
                out = stdout.read().decode(errors="replace")
                if "PROBE_END" not in out:
                    raise RuntimeError("incomplete probe")
                stats = parse_probe(out)
                now = time.time()
                for n in stats.get("nets", []):
                    prev = self._net_prev.get(n["iface"])
                    if prev:
                        dt = max(now - prev[2], 0.001)
                        n["rx_kbs"] = round((n["rx"] - prev[0]) / dt / 1024, 1)
                        n["tx_kbs"] = round((n["tx"] - prev[1]) / dt / 1024, 1)
                    self._net_prev[n["iface"]] = (n["rx"], n["tx"], now)
                self.last_stats = stats
                self.q.put(("monitor_stats", stats))
            except Exception as e:
                self.q.put(("monitor_error", str(e)[:120]))
                self.disconnect()
            time.sleep(self.interval)

    def exec_quick(self, command, timeout=8):
        if self.client and self.connected:
            try:
                _i, o, e = self.client.exec_command(command, timeout=timeout)
                return o.read().decode(errors="replace") + e.read().decode(errors="replace")
            except Exception:
                self.disconnect()
        if not (self.device and self.svc and HAS_PARAMIKO):
            raise RuntimeError("no device/paramiko available")
        return SSHManager.exec_command(self.device["ip"], self.svc["port"],
                                       self.svc["user"], self.svc["pass"],
                                       command, timeout=timeout)[0]


def grab_framebuffer(monitor):
    """Capture framebuffer via SSH. Uses real display dimensions, not virtual_size."""
    meta = monitor.exec_quick(
        "cat /sys/class/graphics/fb0/virtual_size; "
        "cat /sys/class/graphics/fb0/bits_per_pixel; "
        "cat /sys/class/graphics/fb0/stride; "
        "cat /sys/class/graphics/fb0/red /sys/class/graphics/fb0/green "
        "/sys/class/graphics/fb0/blue 2>/dev/null; "
        "fbset 2>/dev/null | grep -E 'geometry|mode' | head -3; "
        "cat /sys/class/graphics/fb0/modes 2>/dev/null | head -1",
        timeout=6)
    lines = [x.strip() for x in meta.splitlines() if x.strip()]
    if len(lines) < 2:
        raise RuntimeError("unable to read framebuffer parameters")

    vw, vh = (int(x) for x in lines[0].replace(",", " ").split()[:2])
    bpp = int(lines[1])
    stride = int(lines[2]) if len(lines) > 2 and lines[2].isdigit() else None

    real_w, real_h = vw, vh
    for ln in lines[3:]:
        if ln.startswith("geometry"):
            parts = ln.split()
            if len(parts) >= 3:
                try:
                    real_w = int(parts[1])
                    real_h = int(parts[2])
                except ValueError:
                    pass
        elif "x" in ln and "p" in ln:
            m = re.search(r'(\d+)x(\d+)', ln)
            if m:
                real_w = int(m.group(1))
                real_h = int(m.group(2))

    if vh > real_h * 1.5:
        h = real_h
    else:
        h = vh
    w = vw if vw == real_w else real_w

    fmt = {"r": (11, 5), "g": (5, 6), "b": (0, 5)}
    if bpp == 32:
        fmt = {"r": (16, 8), "g": (8, 8), "b": (0, 8)}
    try:
        if len(lines) >= 6:
            fmt = {"r": tuple(int(v) for v in lines[3].split(",")),
                   "g": tuple(int(v) for v in lines[4].split(",")),
                   "b": tuple(int(v) for v in lines[5].split(","))}
    except Exception:
        pass

    b64 = monitor.exec_quick("base64 /dev/fb0 2>/dev/null || "
                             "dd if=/dev/fb0 bs=65536 2>/dev/null | base64",
                             timeout=25)
    try:
        raw = base64.b64decode(b64)
    except Exception:
        raise RuntimeError("invalid framebuffer dump (base64)")

    if stride is None:
        stride = vw * (bpp // 8)
    need = stride * h
    if len(raw) < need:
        raise RuntimeError("incomplete dump: {} bytes vs {} expected".format(len(raw), need))

    rgb = bytearray(w * h * 3)
    ro, rl = fmt["r"]
    go, gl = fmt["g"]
    bo, bl = fmt["b"]
    rmax = (1 << rl) - 1
    gmax = (1 << gl) - 1
    bmax = (1 << bl) - 1
    shift = bpp // 8
    di = 0
    for y in range(h):
        row = y * stride
        if shift == 2:
            vals = struct.unpack_from("<{}H".format(w), raw, row)
            for v in vals:
                rgb[di] = (((v >> ro) & rmax) * 255 // rmax)
                rgb[di + 1] = (((v >> go) & gmax) * 255 // gmax)
                rgb[di + 2] = (((v >> bo) & bmax) * 255 // bmax)
                di += 3
        else:
            vals = struct.unpack_from("<{}I".format(w), raw, row)
            for v in vals:
                rgb[di] = (((v >> ro) & rmax) * 255 // rmax)
                rgb[di + 1] = (((v >> go) & gmax) * 255 // gmax)
                rgb[di + 2] = (((v >> bo) & bmax) * 255 // bmax)
                di += 3
    return w, h, bytes(rgb)


def rgb_to_ppm(w, h, rgb):
    return b"P6\n%d %d\n255\n" % (w, h) + rgb


class SFTPSync:
    def __init__(self, ip, port, user, password):
        self.ip, self.port, self.user, self.password = ip, int(port), user, password
        self.transport = None
        self.sftp = None

    def __enter__(self):
        self.transport = paramiko.Transport((self.ip, self.port))
        self.transport.connect(username=self.user, password=self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self

    def __exit__(self, *a):
        try:
            if self.sftp:
                self.sftp.close()
        finally:
            if self.transport:
                self.transport.close()

    def remote_walk(self, root):
        out = {}
        def _walk(path, rel):
            try:
                entries = self.sftp.listdir_attr(path)
            except Exception:
                return
            for e in entries:
                rp = "{}/{}".format(rel, e.filename) if rel else e.filename
                full = "{}/{}".format(path, e.filename)
                if stat.S_ISDIR(e.st_mode or 0):
                    _walk(full, rp)
                else:
                    out[rp] = (e.st_size or 0, e.st_mtime or 0)
        _walk(root, "")
        return out

    @staticmethod
    def local_walk(root):
        out = {}
        root = str(root)
        if not os.path.isdir(root):
            return out
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                out[rel] = (st.st_size, st.st_mtime)
        return out

    def remote_makedirs(self, path):
        parts = path.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                self.sftp.stat(cur)
            except FileNotFoundError:
                try:
                    self.sftp.mkdir(cur)
                except Exception:
                    pass

    def plan(self, local_root, remote_root):
        local = self.local_walk(local_root)
        remote = self.remote_walk(remote_root)
        push, pull = [], []
        for rel, (size, mtime) in local.items():
            if rel not in remote:
                push.append(rel)
            else:
                rsize, rmtime = remote[rel]
                if size != rsize and mtime > rmtime + 2:
                    push.append(rel)
        for rel, (size, mtime) in remote.items():
            if rel not in local:
                pull.append(rel)
            else:
                lsize, lmtime = local[rel]
                if size != lsize and mtime > lmtime + 2:
                    pull.append(rel)
        return push, pull, len(local), len(remote)

    def execute(self, local_root, remote_root, push, pull, progress_cb=None):
        done = 0
        total = len(push) + len(pull)
        for rel in push:
            src = os.path.join(local_root, *rel.split("/"))
            dst_dir = remote_root.rstrip("/") + ("/" + "/".join(rel.split("/")[:-1]) if "/" in rel else "")
            self.remote_makedirs(dst_dir)
            self.sftp.put(src, remote_root.rstrip("/") + "/" + rel)
            try:
                self.sftp.utime(remote_root.rstrip("/") + "/" + rel,
                                (int(os.path.getmtime(src)), int(os.path.getmtime(src))))
            except Exception:
                pass
            done += 1
            if progress_cb:
                progress_cb("↑ {}".format(rel), done, total)
        for rel in pull:
            dst = os.path.join(local_root, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            self.sftp.get(remote_root.rstrip("/") + "/" + rel, dst)
            try:
                _s, mt = self.remote_walk_entry(remote_root.rstrip("/") + "/" + rel)
                os.utime(dst, (mt, mt))
            except Exception:
                pass
            done += 1
            if progress_cb:
                progress_cb("↓ {}".format(rel), done, total)

    def remote_walk_entry(self, path):
        st = self.sftp.stat(path)
        return st.st_size, st.st_mtime


class MediaPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG0)
        self.app = app
        self._photo = None
        self._ppm = None
        self._grabbing = False
        self._auto = False

        # ── top bar: screenshot controls ──
        bar = tk.Frame(self, bg=BG0)
        bar.pack(fill="x", pady=(0, 8))

        ss_frame = tk.Frame(bar, bg=PANEL_BG, highlightbackground=GRID, highlightthickness=1)
        ss_frame.pack(side="left", fill="y", padx=(0, 6))
        tk.Label(ss_frame, text="[ SCREENSHOT ]", fg=CYAN, bg=PANEL_BG, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(6, 2))
        ss_row = tk.Frame(ss_frame, bg=PANEL_BG)
        ss_row.pack(fill="x", padx=8, pady=(2, 6))
        self.grab_btn = HudButton(ss_row, "Capture", self.grab)
        self.grab_btn.pack(side="left", padx=2)
        HudButton(ss_row, "Save PNG...", self.save, accent=MAGENTA).pack(side="left", padx=2)
        self.auto_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ss_row, text="Auto (5s)", variable=self.auto_var,
                       command=self._auto_toggle, fg=YELLOW, bg=PANEL_BG, selectcolor=BG1,
                       activebackground=PANEL_BG, activeforeground=YELLOW, font=FONT_SMALL,
                       bd=0, highlightthickness=0).pack(side="left", padx=8)

        self.info_lbl = tk.Label(bar, text="Framebuffer via SSH — zero console-side installs",
                                 fg=TEXT_DIM, bg=BG0, font=FONT_SMALL)
        self.info_lbl.pack(side="right", padx=4)
        self.media_device_lbl = tk.Label(bar, text="", fg=CYAN, bg=BG0, font=FONT_BOLD)
        self.media_device_lbl.pack(side="right", padx=10)

        # ── preview area ──
        preview_frame = tk.Frame(self, bg=GRID, highlightbackground=GRID, highlightthickness=1)
        preview_frame.pack(fill="x", pady=6)
        self.canvas = tk.Label(preview_frame, bg="#000000", text="No capture", fg=TEXT_DIM, font=FONT)
        self.canvas.pack()

        # ── sync section ──
        sep = tk.Frame(self, bg=GRID, height=2)
        sep.pack(fill="x", pady=8)

        sync_frame = tk.Frame(self, bg=BG0)
        sync_frame.pack(fill="both", expand=True, pady=(0, 0))

        tk.Label(sync_frame, text="[ SYNC FOLDERS PC ↔ CONSOLE ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        tk.Label(sync_frame, text="Two-way 'newest wins' via SFTP — no files are ever deleted. "
                                   "Ideal for muOS saves and states.",
                 fg=TEXT_DIM, bg=BG0, font=FONT_SMALL).pack(anchor="w", pady=(0, 8))

        hdr = tk.Frame(sync_frame, bg=BG0)
        hdr.pack(fill="x")
        for txt, w in (("Active", 6), ("Name", 20), ("Local folder (PC)", 44), ("Remote folder (console)", 40)):
            tk.Label(hdr, text=txt, fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, width=w, anchor="w").pack(side="left", padx=2)

        self.list_frame = tk.Frame(sync_frame, bg=BG0)
        self.list_frame.pack(fill="x", pady=4)
        self._rows = []
        self._render_rows()

        self.sync_progress = tk.Frame(sync_frame, bg=BG0)
        self.sync_progress.pack(fill="x", pady=(0, 4))
        self.sync_progress_lbl = tk.Label(self.sync_progress, text="", fg=CYAN, bg=BG0, font=FONT_SMALL)
        self.sync_progress_lbl.pack(side="left")
        btns = tk.Frame(sync_frame, bg=BG0)
        btns.pack(fill="x", pady=6)
        HudButton(btns, "+ Add Pair", self._add_pair).pack(side="left", padx=2)
        HudButton(btns, "Analyse Differences", self._analyze, accent=MAGENTA).pack(side="left", padx=2)
        HudButton(btns, "SYNC NOW", self._sync, accent=CYAN).pack(side="left", padx=2)
        self.status_lbl = tk.Label(btns, text="", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL)
        self.status_lbl.pack(side="right")

        self.log_text = tk.Text(sync_frame, height=6, bg=LOG_BG, fg=LOG_FG, font=FONT_SMALL,
                                state="disabled", wrap="word",
                                highlightbackground=GRID, highlightthickness=1)
        self.log_text.pack(fill="x", expand=True)

    def _auto_toggle(self):
        self._auto = self.auto_var.get()
        if self._auto:
            self._auto_loop()

    def _auto_loop(self):
        if not self._auto:
            return
        if not self._grabbing:
            self.grab(silent=True)
        self.after(5000, self._auto_loop)

    def _update_device_label(self):
        d = self.app.current_device()
        new_text = "📱 {}".format(self.app.selected_device) if d else ""
        if self.media_device_lbl.cget("text") != new_text:
            self.media_device_lbl.config(text=new_text)

    def grab(self, silent=False):
        self._update_device_label()
        if self._grabbing:
            return
        if not self.app._monitor_target_ready():
            if not silent:
                messagebox.showinfo("Screenshot", "Select a device with SSH active.")
            return
        self._grabbing = True
        self.grab_btn.config(state="disabled")
        self.info_lbl.config(text="Capturing...", fg=ORANGE)

        def worker():
            try:
                w, h, rgb = grab_framebuffer(self.app.monitor)
                ppm = rgb_to_ppm(w, h, rgb)
                self.app.status_queue.put(("screenshot", (w, h, ppm)))
            except Exception as e:
                self.app.status_queue.put(("screenshot_error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def show(self, w, h, ppm):
        self._ppm = (w, h, ppm)
        try:
            self._photo = tk.PhotoImage(data=ppm)
            self.canvas.config(image=self._photo, text="")
            self._photo_ref = self._photo
            self._photo_ref2 = self._photo
        except tk.TclError as e:
            self.info_lbl.config(text="Render error: {}".format(e), fg=RED)
            self._grabbing = False
            self.grab_btn.config(state="normal")
            return
        self.info_lbl.config(text="{}x{} — captured {}".format(w, h, datetime.now().strftime("%H:%M:%S")), fg=CYAN)
        self._grabbing = False
        self.grab_btn.config(state="normal")

    def on_error(self, msg):
        self.info_lbl.config(text="Error: {}".format(msg), fg=RED)
        self._grabbing = False
        self.grab_btn.config(state="normal")

    def save(self):
        if not self._ppm:
            messagebox.showinfo("Save", "Nothing to save yet.")
            return
        w, h, ppm = self._ppm
        path = filedialog.asksaveasfilename(
            title="Save screenshot", defaultextension=".png",
            initialfile="muos_{}.png".format(datetime.now().strftime("%Y%m%d_%H%M%S")),
            filetypes=[("PNG", "*.png"), ("PPM", "*.ppm")])
        self.canvas.update_idletasks()
        if not path:
            return
        try:
            if path.lower().endswith(".ppm"):
                Path(path).write_bytes(ppm)
            else:
                if HAS_PIL:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(ppm))
                    img.save(path, "PNG")
                else:
                    img = tk.PhotoImage(data=ppm)
                    img.write(path, format="png")
            self.app.log("Screenshot saved: {}".format(path), "ok")
        except Exception as e:
            messagebox.showerror("Save", "Error: {}".format(e))
        finally:
            self.canvas.update_idletasks()
            if self._photo:
                self.canvas.config(image=self._photo)

    def _render_rows(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._rows = []
        for pair in self.app.cfg.uplink().get("sync_pairs", []):
            row = tk.Frame(self.list_frame, bg=BG0)
            row.pack(fill="x", pady=1)
            en = tk.BooleanVar(value=pair.get("enabled", True))
            tk.Checkbutton(row, variable=en, bg=BG0, activebackground=BG0,
                           selectcolor=BG1, bd=0, highlightthickness=0, width=6).pack(side="left", padx=2)
            name = tk.StringVar(value=pair.get("name", ""))
            tk.Entry(row, textvariable=name, bg=BG1, fg=TEXT, insertbackground=CYAN,
                     font=FONT_SMALL, width=20, relief="flat").pack(side="left", padx=2)
            local = tk.StringVar(value=pair.get("local", ""))
            le = tk.Entry(row, textvariable=local, bg=BG1, fg=TEXT, insertbackground=CYAN,
                          font=FONT_SMALL, width=40, relief="flat")
            le.pack(side="left", padx=2)
            HudButton(row, "…", lambda v=local: self._pick_dir(v), accent=TEXT_DIM).pack(side="left")
            remote = tk.StringVar(value=pair.get("remote", ""))
            tk.Entry(row, textvariable=remote, bg=BG1, fg=TEXT, insertbackground=CYAN,
                     font=FONT_SMALL, width=40, relief="flat").pack(side="left", padx=2)
            HudButton(row, "✕", lambda r=row, p=pair: self._del_pair(r, p), accent=RED).pack(side="left", padx=4)
            self._rows.append({"frame": row, "pair": pair, "enabled": en,
                               "name": name, "local": local, "remote": remote})

    def _pick_dir(self, var):
        d = filedialog.askdirectory(title="Local folder")
        if d:
            var.set(d)

    def _add_pair(self):
        self.app.cfg.uplink()["sync_pairs"].append(
            {"name": "New pair", "local": "", "remote": "/mnt/mmc/", "enabled": True})
        self._save_rows()
        self._render_rows()

    def _del_pair(self, row, pair):
        self.app.cfg.uplink()["sync_pairs"] = [
            p for p in self.app.cfg.uplink()["sync_pairs"] if p is not pair]
        self._save_rows()
        self._render_rows()

    def _save_rows(self):
        pairs = []
        for r in self._rows:
            pairs.append({"name": r["name"].get().strip() or "sync",
                          "local": r["local"].get().strip(),
                          "remote": r["remote"].get().strip(),
                          "enabled": r["enabled"].get()})
        self.app.cfg.uplink()["sync_pairs"] = pairs
        self.app.cfg.save()

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _ssh_creds(self):
        d = self.app.current_device()
        if not d:
            return None
        svc = d["services"].get("sftp") or d["services"].get("ssh")
        if not svc:
            return None
        return d["ip"], svc["port"], svc["user"], svc["pass"]

    def _analyze(self):
        self._save_rows()
        creds = self._ssh_creds()
        if not creds:
            messagebox.showinfo("Sync", "A device with SFTP/SSH service is required.")
            return
        pairs = [p for p in self.app.cfg.uplink()["sync_pairs"]
                 if p.get("enabled") and p.get("local") and p.get("remote")]
        if not pairs:
            messagebox.showinfo("Sync", "Configure at least one active pair with both paths set.")
            return
        self.status_lbl.config(text="Analysing...", fg=ORANGE)
        self._log("[{}] Analysing differences...".format(datetime.now().strftime("%H:%M:%S")))

        def worker():
            try:
                with SFTPSync(*creds) as sync:
                    for p in pairs:
                        if not os.path.isdir(p["local"]):
                            os.makedirs(p["local"], exist_ok=True)
                        push, pull, nl, nr = sync.plan(p["local"], p["remote"])
                        self.app.status_queue.put(("sync_log",
                            "  {}: {} local / {} remote → ↑{} ↓{}".format(p["name"], nl, nr, len(push), len(pull))))
                self.app.status_queue.put(("sync_status", ("Analysis complete", CYAN)))
            except Exception as e:
                self.app.status_queue.put(("sync_log", "  ERROR: {}".format(e)))
                self.app.status_queue.put(("sync_status", ("Analysis error", RED)))

        threading.Thread(target=worker, daemon=True).start()

    def _sync(self):
        self._save_rows()
        creds = self._ssh_creds()
        if not creds:
            messagebox.showinfo("Sync", "A device with SFTP/SSH service is required.")
            return
        pairs = [p for p in self.app.cfg.uplink()["sync_pairs"]
                 if p.get("enabled") and p.get("local") and p.get("remote")]
        if not pairs:
            messagebox.showinfo("Sync", "Configure at least one active pair with both paths set.")
            return
        self.status_lbl.config(text="Syncing...", fg=ORANGE)
        self._log("[{}] Sync started".format(datetime.now().strftime("%H:%M:%S")))

        def worker():
            try:
                with SFTPSync(*creds) as sync:
                    for p in pairs:
                        os.makedirs(p["local"], exist_ok=True)
                        push, pull, _nl, _nr = sync.plan(p["local"], p["remote"])
                        self.app.status_queue.put(("sync_log",
                            "▸ {}: ↑{} ↓{}".format(p["name"], len(push), len(pull))))
                        sync.execute(p["local"], p["remote"], push, pull,
                                     progress_cb=lambda f, d, t: self.app.status_queue.put(
                                         ("sync_log", "    [{}/{}] {}".format(d, t, f))))
                self.app.status_queue.put(("sync_status", ("Sync complete ✓", CYAN)))
                self.app.status_queue.put(("log", ("Synchronisation complete", "ok")))
            except Exception as e:
                self.app.status_queue.put(("sync_log", "  ERROR: {}".format(e)))
                self.app.status_queue.put(("sync_status", ("Sync error", RED)))

        threading.Thread(target=worker, daemon=True).start()

    def on_log(self, msg):
        self._log(msg)

    def on_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.sync_progress_lbl.config(text=text, fg=color)


# ══════════════════════════════════════════════════════════════════════════════
# §10  MAIN APPLICATION — VOID BaseStation root window
# ══════════════════════════════════════════════════════════════════════════════

class ScanDialog(tk.Toplevel):
    def __init__(self, app, on_select=None):
        super().__init__(app)
        self.app = app
        self.on_select = on_select
        self.configure(bg=BG0)
        self.title("Network Scan")
        self.geometry("440x440")
        self.transient(app)
        self.grab_set()

        tk.Label(self, text="[ LOCAL SUBNET SCAN ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(pady=(14, 4))
        tk.Label(self, text="Searching for hosts with typical muOS ports (8080/9090/22/2022/7070)",
                 fg=TEXT_DIM, bg=BG0, font=FONT_SMALL).pack()
        self.progress_label = tk.Label(self, text="Preparing...", fg=ORANGE, bg=BG0, font=FONT_SMALL)
        self.progress_label.pack(pady=6)

        self.listbox = tk.Listbox(self, bg=BG1, fg=TEXT, selectbackground=CYAN,
                                  selectforeground=BG0, font=FONT, height=12,
                                  highlightthickness=1, highlightbackground=GRID, bd=0)
        self.listbox.pack(fill="both", expand=True, padx=14, pady=6)

        if self.on_select:
            self.listbox.bind("<Double-Button-1>", self._pick)
            tk.Label(self, text="Double-click a result to use it",
                     fg=TEXT_DIM, bg=BG0, font=FONT_SMALL).pack(pady=(0, 10))
        else:
            tk.Label(self, text="", bg=BG0).pack(pady=(0, 4))

        self._counter = {"n": 0}
        self.after(100, self._run_scan)

    def _run_scan(self):
        self.progress_label.config(text="Scanning in progress... (0/254)")

        def progress_cb():
            self._counter["n"] += 1

        def worker():
            results = NetworkUtils.scan_subnet(progress_cb=progress_cb)
            self.after(0, lambda: self._show_results(results))

        threading.Thread(target=worker, daemon=True).start()
        self._tick()

    def _tick(self):
        if not self.winfo_exists():
            return
        n = self._counter["n"]
        self.progress_label.config(text="Scanning in progress... ({}/254)".format(n))
        if n < 254:
            self.after(200, self._tick)

    def _show_results(self, results):
        if not self.winfo_exists():
            return
        self.progress_label.config(text="Completed — {} hosts found".format(len(results)), fg=CYAN)
        self.listbox.delete(0, "end")
        for ip, ports, hostname in results:
            names = ",".join(SCAN_PORT_LABELS.get(p, str(p)) for p in ports)
            label = "{}   [{}]".format(ip, names)
            if hostname:
                label += "  ({})".format(hostname)
            self.listbox.insert("end", label)
        if not results:
            self.listbox.insert("end", "No hosts found — ensure console and PC are on the same network")

    def _pick(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        text = self.listbox.get(sel[0])
        ip = text.split()[0]
        if ip.count(".") == 3 and self.on_select:
            self.on_select(ip)
            self.destroy()


class DeviceWizard(tk.Toplevel):
    def __init__(self, app, mode="new", device_name=None, preset_ip=None, preset_ports=None):
        super().__init__(app)
        self.app = app
        self.mode = mode
        self.device_name = device_name
        self.configure(bg=BG0)
        self.title("New Device" if mode == "new" else "Edit: {}".format(device_name))
        self.geometry("600x680")
        self.minsize(560, 580)
        self.transient(app)
        self.grab_set()

        existing = app.cfg.get_device(device_name) if device_name else None
        services_src = existing["services"] if existing else DEFAULT_SERVICES

        pad = {"padx": 16, "pady": 4}

        tk.Label(self, text="[ IDENTIFICATION ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(anchor="w", padx=16, pady=(14, 4))

        form = tk.Frame(self, bg=BG0)
        form.pack(fill="x", **pad)
        tk.Label(form, text="Device name:", fg=TEXT, bg=BG0, font=FONT, width=16, anchor="w").grid(row=0, column=0, sticky="w", pady=3)
        self.name_var = tk.StringVar(value=device_name or "")
        tk.Entry(form, textvariable=self.name_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                 font=FONT, width=26, relief="flat").grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(form, text="IP address:", fg=TEXT, bg=BG0, font=FONT, width=16, anchor="w").grid(row=1, column=0, sticky="w", pady=3)
        self.ip_var = tk.StringVar(value=existing["ip"] if existing else (preset_ip or ""))
        tk.Entry(form, textvariable=self.ip_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                 font=FONT, width=26, relief="flat").grid(row=1, column=1, sticky="w", padx=6)
        HudButton(form, "Scan Network", self._scan, accent=MAGENTA).grid(row=1, column=2, padx=6)

        current_auto = app.cfg.data.get("auto_connect")
        self.autoconn_var = tk.BooleanVar(value=(device_name is not None and current_auto == device_name))
        tk.Checkbutton(form, text="★ Auto-connect Terminal at app startup", variable=self.autoconn_var,
                       fg=YELLOW, bg=BG0, selectcolor=BG1, activebackground=BG0, activeforeground=YELLOW,
                       font=FONT_SMALL, bd=0, highlightthickness=0).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        tk.Label(self, text="[ SERVICES ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self, text="Default ports/credentials are official muOS defaults — change only if necessary.",
                 fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, wraplength=560, justify="left", anchor="w").pack(fill="x", padx=16)

        svc_frame = tk.Frame(self, bg=BG0)
        svc_frame.pack(fill="both", expand=True, padx=16, pady=8)

        headers = ["Service", "Active", "Port", "User", "Password"]
        widths = [24, 6, 6, 10, 10]
        for c, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(svc_frame, text=h, fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, width=w, anchor="w").grid(row=0, column=c, sticky="w")

        self.svc_vars = {}
        r = 1
        for key, svc in services_src.items():
            enabled = tk.BooleanVar(value=True)
            port_val = svc.get("port")
            port_var = tk.StringVar(value=str(port_val) if port_val else "")
            user_var = tk.StringVar(value=svc.get("user", ""))
            pass_var = tk.StringVar(value=svc.get("pass", ""))
            self.svc_vars[key] = {
                "enabled": enabled, "port": port_var, "user": user_var, "pass": pass_var,
                "label": svc["label"], "kind": svc["kind"], "auth": svc.get("auth", False),
            }

            tk.Label(svc_frame, text=svc["label"], fg=TEXT, bg=BG0, font=FONT_SMALL, width=24, anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            tk.Checkbutton(svc_frame, variable=enabled, bg=BG0, activebackground=BG0,
                           selectcolor=BG1, bd=0, highlightthickness=0).grid(row=r, column=1)

            if svc["kind"] != "tailscale":
                tk.Entry(svc_frame, textvariable=port_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                         font=FONT_SMALL, width=6, relief="flat").grid(row=r, column=2, padx=3)
            if svc.get("auth"):
                tk.Entry(svc_frame, textvariable=user_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                         font=FONT_SMALL, width=10, relief="flat").grid(row=r, column=3, padx=3)
                tk.Entry(svc_frame, textvariable=pass_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                         font=FONT_SMALL, width=10, relief="flat", show="•").grid(row=r, column=4, padx=3)
            r += 1

        # If preset_ports provided, auto-enable services based on detected ports
        if preset_ports:
            for p in preset_ports:
                label = SCAN_PORT_LABELS.get(p)
                if label and label in self.svc_vars:
                    self.svc_vars[label]["enabled"].set(True)

        btns = tk.Frame(self, bg=BG0)
        btns.pack(fill="x", padx=16, pady=(6, 4))
        HudButton(btns, "Test Connection", self._test).pack(side="left")
        HudButton(btns, "Save", self._save, accent=MAGENTA).pack(side="right")
        HudButton(btns, "Cancel", self.destroy, accent=TEXT_DIM).pack(side="right", padx=6)

        self.result_label = tk.Label(self, text="", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL,
                                      anchor="w", justify="left", wraplength=560)
        self.result_label.pack(fill="x", padx=16, pady=(4, 12))

    def _scan(self):
        ScanDialog(self.app, on_select=lambda ip: self.ip_var.set(ip))

    def _test(self):
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Test Connection", "Enter an IP address first.")
            return
        self.result_label.config(text="Testing...", fg=ORANGE)

        def worker():
            lines = []
            for _key, v in self.svc_vars.items():
                if not v["enabled"].get():
                    continue
                port_txt = v["port"].get().strip()
                if not port_txt:
                    continue
                if not port_txt.isdigit():
                    lines.append("{}: invalid port".format(v["label"]))
                    continue
                ok = NetworkUtils.check_port(ip, int(port_txt), timeout=1.2)
                lines.append("{}: {}".format(v["label"], "REACHABLE" if ok else "no response"))
            text = "\n".join(lines) if lines else "No service with a port to test"

            def apply():
                if self.winfo_exists():
                    self.result_label.config(text=text, fg=TEXT)
            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _save(self):
        name = self.name_var.get().strip()
        ip = self.ip_var.get().strip()
        if not name or not ip:
            messagebox.showwarning("Save", "Name and IP address are required.")
            return

        existing_names = self.app.cfg.list_devices()
        if self.mode == "new" and name in existing_names:
            messagebox.showerror("Save", "A device with this name already exists.")
            return
        if self.mode == "edit" and name != self.device_name and name in existing_names:
            messagebox.showerror("Save", "A device with this name already exists.")
            return

        services = {}
        for key, v in self.svc_vars.items():
            if not v["enabled"].get():
                continue
            port_txt = v["port"].get().strip()
            port = int(port_txt) if port_txt.isdigit() else None
            services[key] = {
                "label": v["label"], "kind": v["kind"], "auth": v["auth"],
                "port": port, "user": v["user"].get(), "pass": v["pass"].get(),
            }

        if not services:
            messagebox.showwarning("Save", "Enable at least one service.")
            return

        old_name_for_autoconn = self.device_name if self.mode == "edit" else None

        if self.mode == "new":
            self.app.cfg.add_device(name, ip, services)
        else:
            if name != self.device_name:
                self.app.cfg.remove_device(self.device_name)
                self.app.cfg.add_device(name, ip, services)
            else:
                self.app.cfg.update_device(name, ip=ip, services=services)
            self.app.cfg.data["last_used"] = name

        if self.autoconn_var.get():
            self.app.cfg.data["auto_connect"] = name
        elif self.app.cfg.data.get("auto_connect") == old_name_for_autoconn and old_name_for_autoconn:
            self.app.cfg.data["auto_connect"] = None
        self.app.cfg.save()

        self.app.selected_device = name
        self.app._refresh_sidebar()
        self.app._render_dashboard()
        self.app.terminal_panel.refresh_devices()
        self.app.log("Device '{}' saved ({})".format(name, ip), "ok")
        self.destroy()


class QuickCommandDialog(tk.Toplevel):
    def __init__(self, app, device, svc):
        super().__init__(app)
        self.app = app
        self.device = device
        self.svc = svc
        self.configure(bg=BG0)
        self.title("Quick Command — {}".format(device["ip"]))
        self.geometry("600x440")
        self.transient(app)

        tk.Label(self, text="[ SINGLE COMMAND (non-interactive) ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(anchor="w", padx=16, pady=(14, 6))

        entry_frame = tk.Frame(self, bg=BG0)
        entry_frame.pack(fill="x", padx=16)
        self.cmd_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self.cmd_var, bg=BG1, fg=TEXT,
                         insertbackground=CYAN, font=FONT, relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=3)
        entry.bind("<Return>", lambda _e: self._run())
        HudButton(entry_frame, "Run", self._run, accent=MAGENTA).pack(side="left", padx=6)

        self.output = tk.Text(self, bg=LOG_BG, fg=LOG_FG, insertbackground=CYAN,
                              font=FONT_SMALL, state="disabled", wrap="word",
                              highlightbackground=GRID, highlightthickness=1)
        self.output.pack(fill="both", expand=True, padx=16, pady=12)
        entry.focus_set()

        if not HAS_PARAMIKO:
            self._append("[!] paramiko not installed — run: pip install paramiko\n")
            entry.config(state="disabled")

    def _append(self, text):
        self.output.config(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.config(state="disabled")

    def _run(self):
        cmd = self.cmd_var.get().strip()
        if not cmd or not HAS_PARAMIKO:
            return
        self._append("\n$ {}\n".format(cmd))

        def worker():
            try:
                out, err = SSHManager.exec_command(
                    self.device["ip"], self.svc["port"], self.svc["user"], self.svc["pass"], cmd
                )
                text = out + (err or "")

                def apply():
                    if self.winfo_exists():
                        self._append(text if text else "(no output)\n")
                self.after(0, apply)
            except Exception as e:
                def apply_err():
                    if self.winfo_exists():
                        self._append("[error] {}\n".format(e))
                self.after(0, apply_err)

        threading.Thread(target=worker, daemon=True).start()


class PushFileDialog(tk.Toplevel):
    def __init__(self, app, device, svc, local_path):
        super().__init__(app)
        self.app = app
        self.device = device
        self.svc = svc
        self.local_path = local_path
        self.configure(bg=BG0)
        self.title("Send File via SFTP")
        self.geometry("480x260")
        self.transient(app)
        self.grab_set()

        tk.Label(self, text="[ FILE TRANSFER ]", fg=CYAN, bg=BG0, font=FONT_BOLD).pack(anchor="w", padx=16, pady=(14, 6))
        tk.Label(self, text="Local file: {}".format(os.path.basename(local_path)),
                 fg=TEXT, bg=BG0, font=FONT_SMALL, anchor="w").pack(fill="x", padx=16)

        tk.Label(self, text="Remote destination path:", fg=TEXT, bg=BG0,
                 font=FONT_SMALL, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        self.remote_var = tk.StringVar(value="/{}".format(os.path.basename(local_path)))
        tk.Entry(self, textvariable=self.remote_var, bg=BG1, fg=TEXT, insertbackground=CYAN,
                 font=FONT, relief="flat").pack(fill="x", padx=16, ipady=3)
        tk.Label(self, text="Tip: open FileBrowser first to verify the exact path (MMC/SDCARD/USB).",
                 fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, wraplength=440, justify="left", anchor="w").pack(fill="x", padx=16, pady=(6, 0))

        self.status_lbl = tk.Label(self, text="", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, anchor="w")
        self.status_lbl.pack(fill="x", padx=16, pady=(10, 0))

        btns = tk.Frame(self, bg=BG0)
        btns.pack(fill="x", padx=16, pady=14)
        self.send_btn = HudButton(btns, "Send", self._send, accent=MAGENTA)
        self.send_btn.pack(side="right")
        HudButton(btns, "Cancel", self.destroy, accent=TEXT_DIM).pack(side="right", padx=6)

        if not HAS_PARAMIKO:
            self.status_lbl.config(text="paramiko not installed — run: pip install paramiko", fg=RED)
            self.send_btn.config(state="disabled")

    def _send(self):
        if not HAS_PARAMIKO:
            return
        remote = self.remote_var.get().strip()
        if not remote:
            return
        self.status_lbl.config(text="Sending...", fg=ORANGE)
        self.send_btn.config(state="disabled")

        def worker():
            try:
                SSHManager.push_file(self.device["ip"], self.svc["port"], self.svc["user"],
                                     self.svc["pass"], self.local_path, remote)

                def done():
                    if self.winfo_exists():
                        self.status_lbl.config(text="Completed ✓", fg=CYAN)
                        self.send_btn.config(state="normal")
                    self.app.log("File sent: {} → {}".format(os.path.basename(self.local_path), remote), "ok")
                self.after(0, done)
            except Exception as e:
                def fail():
                    if self.winfo_exists():
                        self.status_lbl.config(text="Error: {}".format(e), fg=RED)
                        self.send_btn.config(state="normal")
                self.after(0, fail)

        threading.Thread(target=worker, daemon=True).start()


# ── mousewheel scroll helper ─────────────────────────────────────────────────

def _bind_mousewheel(widget, canvas):
    def _on_mousewheel(event):
        if platform.system() == "Linux":
            if event.num == 4:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                canvas.yview_scroll(3, "units")
        elif platform.system() == "Darwin":
            canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    if platform.system() == "Linux":
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)
    else:
        widget.bind("<MouseWheel>", _on_mousewheel)


class VOIDBaseStation(tk.Tk):
    def __init__(self):
        super().__init__()
        self._detect_font()
        try:
            self.iconphoto(False, tk.PhotoImage(data=b"P1 1 1 0 1 "))
        except Exception:
            pass

        self.title("{} v{}".format(APP_NAME, APP_VERSION))
        self.minsize(1200, 800)
        self.configure(bg=BG0)

        self.cfg = ConfigManager()
        saved_geom = self.cfg.data.get("window_geometry")
        self.geometry(saved_geom if saved_geom else "1200x800")

        self.selected_device = self.cfg.data.get("last_used")
        if self.selected_device not in self.cfg.data["devices"]:
            self.selected_device = next(iter(self.cfg.data["devices"]), None)

        self.status_queue = queue.Queue()
        self.cards = {}
        self._saved_order = []
        self.discovered_devices = []   # list of (ip, ports, hostname)
        self._scanning = False

        self.monitor = ConsoleMonitor(self.status_queue, interval=2.5)
        self.daemon = EmbeddedDaemon(self.cfg)
        self._inbox_offset = INBOX_FILE.stat().st_size if INBOX_FILE.exists() else 0
        self._daemon_started_by_us = False

        self._build_layout()

        # Status bar
        self.status_bar = tk.Label(self, text="{} v{} — Ready".format(APP_NAME, APP_VERSION),
                                   fg=TEXT_DIM, bg=BG1, font=FONT_SMALL, anchor="w", padx=10, pady=3)
        self.status_bar.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self._refresh_sidebar()
        self._render_dashboard()
        self.terminal_panel.refresh_devices(select=self.selected_device)

        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Menu bar
        menubar = tk.Menu(self, bg=BG1, fg=TEXT, activebackground=CYAN, activeforeground=BG0)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg=BG1, fg=TEXT, activebackground=CYAN, activeforeground=BG0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Device    Ctrl+N", command=self.action_new_device)
        file_menu.add_command(label="Export Profiles", command=self.action_export_profiles)
        file_menu.add_command(label="Import Profiles", command=self.action_import_profiles)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        view_menu = tk.Menu(menubar, tearoff=0, bg=BG1, fg=TEXT, activebackground=CYAN, activeforeground=BG0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Dashboard    Ctrl+D", command=lambda: self._select_tab("dashboard"))
        view_menu.add_command(label="Media        Ctrl+M", command=lambda: self._select_tab("media"))
        view_menu.add_command(label="Terminal    Ctrl+T", command=lambda: self._select_tab("terminal"))
        view_menu.add_separator()
        view_menu.add_command(label="Fullscreen   F11", command=lambda: self.attributes("-fullscreen", True))

        help_menu = tk.Menu(menubar, tearoff=0, bg=BG1, fg=TEXT, activebackground=CYAN, activeforeground=BG0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)

        # Polling loops
        self.after(500, self._poll_queue)
        self.after(2000, self._poll_inbox)
        self._start_status_loop()

        # Default tab
        self.after(500, lambda: self._select_tab("dashboard"))

        # Auto-connect saved device
        auto_name = self.cfg.data.get("auto_connect")
        if auto_name and auto_name in self.cfg.data["devices"]:
            self.after(900, lambda: self._do_auto_connect(auto_name))

        self.log("{} v{} initialised.".format(APP_NAME, APP_VERSION), "ok")
        if not HAS_PARAMIKO:
            self.log("paramiko not found — Terminal, Screenshot and Sync are disabled until installed.", "warn")

        # Auto-start daemon
        if self.cfg.uplink().get("daemon_autostart"):
            if self.daemon.start():
                self._daemon_started_by_us = True
                self.log("Daemon auto-started on port {}".format(self.daemon.port), "ok")

        # Auto-scan network at startup
        self.after(1200, self._start_auto_scan)

    # ── font detection ────────────────────────────────────────────────────────

    def _detect_font(self):
        global FONT_FAMILY, FONT, FONT_BOLD, FONT_TITLE, FONT_SMALL, FONT_TERM
        try:
            families = set(tkfont.families())
        except Exception:
            families = set()
        for candidate in ["JetBrains Mono", "Consolas", "DejaVu Sans Mono",
                           "Liberation Mono", "Courier New", "Courier"]:
            if candidate in families:
                FONT_FAMILY = candidate
                break
        else:
            FONT_FAMILY = "TkFixedFont"
        FONT = (FONT_FAMILY, 10)
        FONT_BOLD = (FONT_FAMILY, 10, "bold")
        FONT_TITLE = (FONT_FAMILY, 13, "bold")
        FONT_SMALL = (FONT_FAMILY, 9)
        FONT_TERM = (FONT_FAMILY, 10)

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.action_new_device())
        self.bind("<Control-d>", lambda e: self._select_tab("dashboard"))
        self.bind("<Control-m>", lambda e: self._select_tab("media"))
        self.bind("<Control-t>", lambda e: self._select_tab("terminal"))
        self.bind("<F5>", lambda e: self._trigger_immediate_check())
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False) if self.attributes("-fullscreen") else None)

    def _on_close(self):
        if self.monitor.running:
            if not messagebox.askyesno("Confirm", "The console monitor is active. Close anyway?"):
                return
        try:
            self.cfg.data["window_geometry"] = self.geometry()
            self.cfg.save()
        except Exception:
            pass
        try:
            if self.terminal_panel.connected:
                self.terminal_panel.disconnect()
        except Exception:
            pass
        try:
            self.monitor.stop()
        except Exception:
            pass
        try:
            if self._daemon_started_by_us:
                self.daemon.stop()
        except Exception:
            pass
        self.destroy()

    # ── layout builder ────────────────────────────────────────────────────────

    def _build_layout(self):
        header = tk.Frame(self, bg=BG0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        banner_text = make_banner("  V O I D   B A S E S T A T I O N  ", 54)
        tk.Label(header, text=banner_text, fg=CYAN, bg=BG0, font=FONT_BOLD, justify="center").pack()
        tk.Label(header, text="PC ↔ Console Interconnected System",
                 fg=MAGENTA, bg=BG0, font=FONT_SMALL).pack(pady=(2, 0))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # ── sidebar ──
        sidebar = tk.Frame(self, bg=BG1, width=280)
        sidebar.grid(row=1, column=0, sticky="ns", padx=(10, 4), pady=6)
        sidebar.grid_propagate(False)

        # PC info block
        pc_frame = tk.Frame(sidebar, bg=PANEL_BG, highlightbackground=GRID, highlightthickness=1)
        pc_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.pc_user_lbl = tk.Label(pc_frame, text="", fg=CYAN, bg=PANEL_BG, font=FONT_BOLD, anchor="w")
        self.pc_user_lbl.pack(fill="x", padx=8, pady=(6, 0))
        self.pc_host_lbl = tk.Label(pc_frame, text="", fg=TEXT_DIM, bg=PANEL_BG, font=FONT_SMALL, anchor="w")
        self.pc_host_lbl.pack(fill="x", padx=8, pady=(0, 6))
        self._refresh_pc_info()

        # Connection status
        self.conn_indicator = tk.Label(sidebar, text="● No device selected", fg=TEXT_DIM, bg=BG1, font=FONT_SMALL)
        self.conn_indicator.pack(anchor="w", padx=10, pady=(0, 4))

        # Saved devices
        tk.Label(sidebar, text="[ SAVED DEVICES ]", fg=CYAN, bg=BG1, font=FONT_BOLD).pack(anchor="w", padx=10, pady=(8, 2))
        self.saved_listbox = tk.Listbox(
            sidebar, bg="#0f0f22", fg=TEXT, selectbackground=CYAN, selectforeground=BG0,
            font=FONT, height=8, highlightthickness=0, bd=0, activestyle="none"
        )
        self.saved_listbox.pack(fill="x", padx=10, pady=4)
        self.saved_listbox.bind("<<ListboxSelect>>", self._on_saved_select)
        self.saved_listbox.bind("<Double-Button-1>", self._on_saved_double_click)

        # Discovered devices
        disc_header = tk.Frame(sidebar, bg=BG1)
        disc_header.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(disc_header, text="[ DISCOVERED ]", fg=MAGENTA, bg=BG1, font=FONT_BOLD).pack(side="left")
        self.scan_btn = HudButton(disc_header, "↻", self._start_auto_scan, accent=CYAN, tooltip="Rescan network")
        self.scan_btn.pack(side="right")
        self.discovered_listbox = tk.Listbox(
            sidebar, bg="#0f0f22", fg=TEXT_DIM, selectbackground=MAGENTA, selectforeground=BG0,
            font=FONT_SMALL, height=6, highlightthickness=0, bd=0, activestyle="none"
        )
        self.discovered_listbox.pack(fill="x", padx=10, pady=4)
        self.discovered_listbox.bind("<Double-Button-1>", self._on_discovered_double_click)

        # Sidebar buttons
        sbtns = tk.Frame(sidebar, bg=BG1)
        sbtns.pack(fill="x", padx=10, pady=(4, 6))
        HudButton(sbtns, "+ New Device", self.action_new_device).pack(fill="x", pady=2)
        HudButton(sbtns, "Edit", self.action_edit_device).pack(fill="x", pady=2)
        HudButton(sbtns, "Remove", self.action_remove_device, accent=RED).pack(fill="x", pady=2)
        HudButton(sbtns, "Connect Terminal", self.action_open_embedded_terminal, accent=CYAN).pack(fill="x", pady=2)

        tk.Frame(sidebar, bg=GRID, height=1).pack(fill="x", padx=10, pady=(2, 6))
        io_row = tk.Frame(sidebar, bg=BG1)
        io_row.pack(fill="x", padx=10, pady=(0, 10))
        HudButton(io_row, "Export", self.action_export_profiles, accent=TEXT_DIM).pack(side="left", expand=True, fill="x", padx=(0, 2))
        HudButton(io_row, "Import", self.action_import_profiles, accent=TEXT_DIM).pack(side="left", expand=True, fill="x", padx=(2, 0))

        # ── main area ──
        main = tk.Frame(self, bg=BG0)
        main.grid(row=1, column=1, sticky="nsew", padx=(4, 10), pady=6)
        main.grid_rowconfigure(3, weight=1)
        main.grid_columnconfigure(0, weight=1)

        dev_info = tk.Frame(main, bg=BG0)
        dev_info.grid(row=0, column=0, sticky="ew")
        self.device_title = tk.Label(dev_info, text="—", fg=CYAN, bg=BG0, font=FONT_TITLE, anchor="w")
        self.device_title.pack(side="left")
        self.device_sub = tk.Label(dev_info, text="", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, anchor="w")
        self.device_sub.pack(side="left", padx=10)

        HudButton(dev_info, "Refresh", self._trigger_immediate_check, accent=TEXT_DIM, tooltip="Refresh service status").pack(side="right", padx=2)
        HudButton(dev_info, "Connect All", self.action_connect_all, accent=CYAN, tooltip="Start all connections").pack(side="right")

        tk.Frame(main, bg=GRID, height=1).grid(row=1, column=0, sticky="ew", pady=6)

        tabbar = tk.Frame(main, bg=BG0)
        tabbar.grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.tab_buttons = {}
        for key, label in (("dashboard", "◈ DASHBOARD"), ("media", "◐ MEDIA"), ("terminal", "▶ TERMINAL")):
            b = tk.Label(tabbar, text="  {}  ".format(label), fg=TEXT_DIM, bg=BG0, font=FONT_BOLD, cursor="hand2")
            b.pack(side="left", padx=(0, 4))
            b.bind("<Button-1>", lambda _e, k=key: self._select_tab(k))
            self.tab_buttons[key] = b

        content = tk.Frame(main, bg=BG0)
        content.grid(row=3, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # Dashboard tab
        self.dashboard_frame = tk.Frame(content, bg=BG0)
        self.dashboard_frame.grid(row=0, column=0, sticky="nsew")
        self.dashboard_frame.grid_rowconfigure(0, weight=1)
        self.dashboard_frame.grid_columnconfigure(0, weight=1)

        self.dash_canvas = tk.Canvas(self.dashboard_frame, bg=BG0, highlightthickness=0, bd=0)
        self.dash_scrollbar = tk.Scrollbar(self.dashboard_frame, orient="vertical", command=self.dash_canvas.yview)
        self.dash_scrollable = tk.Frame(self.dash_canvas, bg=BG0)
        self.dash_scrollable.bind(
            "<Configure>",
            lambda e: self.dash_canvas.configure(scrollregion=self.dash_canvas.bbox("all"))
        )
        self.dash_canvas.create_window((0, 0), window=self.dash_scrollable, anchor="nw")
        self.dash_canvas.configure(yscrollcommand=self.dash_scrollbar.set)
        self.dash_canvas.grid(row=0, column=0, sticky="nsew")
        self.dash_scrollbar.grid(row=0, column=1, sticky="ns")
        _bind_mousewheel(self.dash_canvas, self.dash_canvas)
        _bind_mousewheel(self.dash_scrollable, self.dash_canvas)
        self.dash_canvas.bind("<Configure>", lambda e: self.dash_canvas.itemconfig(1, width=e.width))

        self.service_grid = tk.Frame(self.dash_scrollable, bg=BG0)
        self.service_grid.pack(fill="x", expand=True)

        log_frame = tk.Frame(self.dash_scrollable, bg=BG0)
        log_frame.pack(fill="x", expand=True, pady=(10, 0))
        tk.Label(log_frame, text="[ LOG ]", fg=TEXT_DIM, bg=BG0, font=FONT_SMALL, anchor="w").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=7, bg=LOG_BG, fg=LOG_FG, font=FONT_SMALL,
                                 state="disabled", wrap="word", highlightbackground=GRID, highlightthickness=1)
        self.log_text.tag_configure("timestamp", foreground=TEXT_DIM)
        self.log_text.tag_configure("ok", foreground=CYAN)
        self.log_text.tag_configure("err", foreground=RED)
        self.log_text.tag_configure("warn", foreground=ORANGE)
        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="x", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Terminal tab
        self.terminal_frame = tk.Frame(content, bg=BG0)
        self.terminal_frame.grid(row=0, column=0, sticky="nsew")
        self.terminal_panel = TerminalPanel(self.terminal_frame, self)
        self.terminal_panel.pack(fill="both", expand=True)

        # Media tab (scrollable)
        self.media_frame = tk.Frame(content, bg=BG0)
        self.media_frame.grid(row=0, column=0, sticky="nsew")
        self.media_frame.grid_rowconfigure(0, weight=1)
        self.media_frame.grid_columnconfigure(0, weight=1)

        self.media_canvas = tk.Canvas(self.media_frame, bg=BG0, highlightthickness=0, bd=0)
        self.media_scrollbar = tk.Scrollbar(self.media_frame, orient="vertical", command=self.media_canvas.yview)
        self.media_scrollable = tk.Frame(self.media_canvas, bg=BG0)
        self.media_scrollable.bind(
            "<Configure>",
            lambda e: self.media_canvas.configure(scrollregion=self.media_canvas.bbox("all"))
        )
        self.media_canvas.create_window((0, 0), window=self.media_scrollable, anchor="nw")
        self.media_canvas.configure(yscrollcommand=self.media_scrollbar.set)
        self.media_canvas.grid(row=0, column=0, sticky="nsew")
        self.media_scrollbar.grid(row=0, column=1, sticky="ns")
        _bind_mousewheel(self.media_canvas, self.media_canvas)
        _bind_mousewheel(self.media_scrollable, self.media_canvas)
        self.media_canvas.bind("<Configure>", lambda e: self.media_canvas.itemconfig(1, width=e.width))

        self.media_panel = MediaPanel(self.media_scrollable, self)
        self.media_panel.pack(fill="both", expand=True)

        self._current_tab = "dashboard"
        self._tab_frames = {
            "dashboard": self.dashboard_frame,
            "media": self.media_frame,
            "terminal": self.terminal_frame,
        }
        self._select_tab("dashboard")

    def _select_tab(self, key):
        self._current_tab = key
        for k, b in self.tab_buttons.items():
            if k == key:
                b.config(fg=BG0, bg=CYAN)
            else:
                b.config(fg=TEXT_DIM, bg=BG0)
        self._tab_frames[key].tkraise()
        if key == "terminal":
            self.terminal_panel.refresh_devices(select=self.selected_device)

    # ── sidebar refresh & interaction ─────────────────────────────────────────

    def _refresh_pc_info(self):
        user = getpass.getuser()
        hostname = platform.node() or "PC"
        ip = NetworkUtils.get_local_ip()
        self.pc_user_lbl.config(text="👤 {}@{}".format(user, hostname))
        self.pc_host_lbl.config(text="🌐 {}".format(ip))
        self.after(30000, self._refresh_pc_info)

    def _refresh_sidebar(self):
        # Saved
        self.saved_listbox.delete(0, "end")
        self._saved_order = list(self.cfg.list_devices().keys())
        auto = self.cfg.data.get("auto_connect")
        for n in self._saved_order:
            label = "★ {}".format(n) if n == auto else "  {}".format(n)
            self.saved_listbox.insert("end", label)
        if self.selected_device in self._saved_order:
            idx = self._saved_order.index(self.selected_device)
            self.saved_listbox.selection_set(idx)

        # Discovered
        self.discovered_listbox.delete(0, "end")
        if self._scanning:
            self.discovered_listbox.insert("end", "  Scanning...")
        elif not self.discovered_devices:
            self.discovered_listbox.insert("end", "  No devices found yet")
        else:
            for ip, ports, hostname in self.discovered_devices:
                names = ",".join(SCAN_PORT_LABELS.get(p, str(p)) for p in ports)
                label = "  {} [{}]".format(ip, names)
                if hostname:
                    label += " ({})".format(hostname)
                self.discovered_listbox.insert("end", label)

        self._update_conn_indicator()

    def _on_saved_select(self, _event=None):
        sel = self.saved_listbox.curselection()
        if not sel or sel[0] >= len(self._saved_order):
            return
        name = self._saved_order[sel[0]]
        if name != self.selected_device:
            self.selected_device = name
            self.cfg.data["last_used"] = name
            self.cfg.save()
            self._render_dashboard()
            self._update_conn_indicator()

    def _on_saved_double_click(self, _event=None):
        self._on_saved_select()
        self.after(200, self.action_open_embedded_terminal)

    def _on_discovered_double_click(self, _event=None):
        sel = self.discovered_listbox.curselection()
        if not sel:
            return
        if self._scanning or not self.discovered_devices:
            return
        idx = sel[0]
        if idx >= len(self.discovered_devices):
            return
        ip, ports, hostname = self.discovered_devices[idx]
        # Open wizard pre-filled
        DeviceWizard(self, mode="new", preset_ip=ip, preset_ports=ports)

    def _update_conn_indicator(self):
        d = self.current_device()
        if not d:
            self.conn_indicator.config(text="● No device selected", fg=TEXT_DIM)
            return
        # Quick async check
        def check():
            ssh_svc = d["services"].get("ssh")
            if ssh_svc and ssh_svc.get("port"):
                ok = NetworkUtils.check_port(d["ip"], ssh_svc["port"], timeout=1.0)
                if ok:
                    self.conn_indicator.config(text="● {} Online".format(self.selected_device), fg=CYAN)
                else:
                    self.conn_indicator.config(text="● {} Offline".format(self.selected_device), fg=RED)
            else:
                self.conn_indicator.config(text="● {} (no SSH)".format(self.selected_device), fg=ORANGE)
        threading.Thread(target=check, daemon=True).start()

    def _start_auto_scan(self):
        if self._scanning:
            return
        self._scanning = True
        self.discovered_devices = []
        self._refresh_sidebar()
        self.log("Network scan started...", "info")

        def worker():
            results = NetworkUtils.scan_subnet(timeout=0.4, max_workers=60)
            self.discovered_devices = results
            self._scanning = False
            self.status_queue.put(("scan_complete", len(results)))

        threading.Thread(target=worker, daemon=True).start()

    # ── device state helpers ──────────────────────────────────────────────────

    def current_device(self):
        return self.cfg.get_device(self.selected_device) if self.selected_device else None

    def current_ip(self):
        d = self.current_device()
        return d["ip"] if d else "—"

    def set_status(self, text, color=TEXT_DIM):
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.config(text=text, fg=color)

    def log(self, msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "·", "ok": "✓", "err": "✗", "warn": "!"}.get(tag, "·")
        colors = {"info": LOG_FG, "ok": CYAN, "err": RED, "warn": ORANGE}
        self.log_text.config(state="normal")
        self.log_text.insert("end", "[{}] ".format(ts), "timestamp")
        self.log_text.insert("end", "{} ".format(prefix), tag)
        self.log_text.insert("end", "{}\n".format(msg))
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.set_status("[{}] {} {}".format(ts, prefix, msg[:60]), colors.get(tag, TEXT_DIM))

    def _render_dashboard(self):
        for w in self.service_grid.winfo_children():
            w.destroy()
        self.cards = {}

        d = self.current_device()
        if not d:
            self.device_title.config(text="No device configured")
            self.device_sub.config(text="Use '+ New Device' or wait for network scan results")
            return

        self.device_title.config(text=self.selected_device)
        ssh_svc = d["services"].get("ssh", {})
        ssh_port = ssh_svc.get("port", 22)
        self.device_sub.config(text="🌐 {}:{}".format(d["ip"], ssh_port), fg=CYAN, font=FONT_BOLD)

        row = col = 0
        for key, svc in d["services"].items():
            card = ServiceCard(self.service_grid, key, svc, self)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            self.cards[key] = card
            col += 1
            if col >= 2:
                col = 0
                row += 1

        for c in range(2):
            self.service_grid.grid_columnconfigure(c, weight=1)
        for r in range(4):
            self.service_grid.grid_rowconfigure(r, weight=1)

        self._trigger_immediate_check()

    # ── polling & status loops ────────────────────────────────────────────────

    def _poll_queue(self):
        processed = 0
        try:
            while processed < 20:
                kind, payload = self.status_queue.get_nowait()
                if kind == "log":
                    msg, tag = payload
                    self.log(msg, tag)
                elif kind == "port_status":
                    dev_name, key, state = payload
                    if dev_name == self.selected_device and key in self.cards:
                        self.cards[key].set_state(state)
                elif kind == "screenshot":
                    w, h, ppm = payload
                    self.media_panel.show(w, h, ppm)
                elif kind == "screenshot_error":
                    self.media_panel.on_error(payload)
                elif kind == "sync_log":
                    self.media_panel.on_log(payload)
                elif kind == "sync_status":
                    text, color = payload
                    self.media_panel.on_status(text, color)
                elif kind == "scan_complete":
                    self._refresh_sidebar()
                    self.log("Network scan complete — {} host(s) found".format(payload), "ok")
                processed += 1
        except queue.Empty:
            pass
        self.after(500, self._poll_queue)

    def _poll_inbox(self):
        try:
            if self.daemon.is_running():
                items, new_offset = self.daemon.read_inbox_tail(self._inbox_offset)
                self._inbox_offset = new_offset
                for it in items:
                    self.log("NOTIFICATION FROM CONSOLE — {}: {}".format(it.get("title",""), it.get("body","")), "ok")
                    try:
                        self.bell()
                    except Exception:
                        pass
        except Exception:
            pass
        self.after(2000, self._poll_inbox)

    def _monitor_target_ready(self):
        d = self.current_device()
        if not d:
            return False
        svc = d["services"].get("ssh")
        if not svc:
            return False
        if self.monitor.device is not d or self.monitor.svc is not svc:
            self.monitor.set_device(d, svc)
        return HAS_PARAMIKO

    def _trigger_immediate_check(self):
        dev_name = self.selected_device
        d = self.cfg.get_device(dev_name) if dev_name else None
        if not d:
            return

        def worker():
            for key, svc in d["services"].items():
                port = svc.get("port")
                state = "online" if port and NetworkUtils.check_port(d["ip"], port, timeout=1.0) else ("offline" if port else "unknown")
                self.status_queue.put(("port_status", (dev_name, key, state)))

        threading.Thread(target=worker, daemon=True).start()
        self._update_conn_indicator()

    def _start_status_loop(self):
        def loop():
            while True:
                dev_name = self.selected_device
                d = self.cfg.get_device(dev_name) if dev_name else None
                if d:
                    for key, svc in d["services"].items():
                        port = svc.get("port")
                        if port:
                            state = "online" if NetworkUtils.check_port(d["ip"], port, timeout=1.0) else "offline"
                        else:
                            state = "unknown"
                        self.status_queue.put(("port_status", (dev_name, key, state)))
                time.sleep(10)

        threading.Thread(target=loop, daemon=True).start()

    # ── auto-connect ──────────────────────────────────────────────────────────

    def _do_auto_connect(self, name):
        self.selected_device = name
        self.cfg.data["last_used"] = name
        self.cfg.save()
        self._refresh_sidebar()
        self._render_dashboard()
        self._select_tab("terminal")
        self.log("Auto-connecting to '{}'...".format(name), "info")
        self.terminal_panel.refresh_devices(select=name)
        self.terminal_panel.connect()

    # ── actions ───────────────────────────────────────────────────────────────

    def _show_shortcuts(self):
        msg = """Keyboard shortcuts:

Ctrl+N  → New Device
Ctrl+D  → Dashboard
Ctrl+M  → Media (Screenshot + Sync)
Ctrl+T  → Terminal
F5      → Refresh status
F11     → Fullscreen
Esc     → Exit fullscreen

Tabs are selectable via click or shortcut."""
        messagebox.showinfo("Keyboard Shortcuts", msg)

    def _show_about(self):
        messagebox.showinfo("About",
            "{} v{}\n"
            "PC ↔ Console Interconnected System\n\n"
            "Built for muOS (RG35XX H and derivatives)\n"
            "SPDW Factory — RSPDW Lab".format(APP_NAME, APP_VERSION))

    def action_new_device(self):
        DeviceWizard(self, mode="new")

    def action_edit_device(self):
        if not self.selected_device:
            messagebox.showinfo("Edit", "Select a device from the saved list first.")
            return
        DeviceWizard(self, mode="edit", device_name=self.selected_device)

    def action_remove_device(self):
        if not self.selected_device:
            return
        if messagebox.askyesno(
            "Confirm removal",
            "Remove '{}' from BaseStation?\n"
            "(The physical device is untouched; only the local profile is deleted.)"
        ):
            removed = self.selected_device
            self.cfg.remove_device(self.selected_device)
            self.selected_device = self.cfg.data.get("last_used")
            self._refresh_sidebar()
            self._render_dashboard()
            self.terminal_panel.refresh_devices()
            self.log("Device '{}' removed".format(removed), "warn")

    def action_connect_all(self):
        d = self.current_device()
        if not d:
            return
        opened = 0

        for _key, svc in d["services"].items():
            try:
                if svc["kind"] == "ssh":
                    open_ssh_terminal(d["ip"], svc["port"], svc["user"])
                    opened += 1
                elif svc["kind"] == "web":
                    import webbrowser
                    webbrowser.open("http://{}:{}".format(d["ip"], svc["port"]))
                    opened += 1
            except Exception as e:
                self.log("Error starting {}: {}".format(svc["label"], e), "err")

        if HAS_PARAMIKO:
            ssh_svc = d["services"].get("ssh")
            if ssh_svc:
                self.monitor.stop()
                self.monitor.set_device(d, ssh_svc)
                self.monitor.start()
                self.log("Console monitor started automatically", "ok")
                opened += 1
            else:
                self.log("Console monitor unavailable: SSH not configured", "warn")
        else:
            self.log("Console monitor unavailable: paramiko not installed", "warn")

        if self.daemon.start():
            self._daemon_started_by_us = True
            self.log("Daemon started on port {}".format(self.daemon.port), "ok")
            opened += 1

        self.log("Quick connect launched on {} service(s)/system(s)".format(opened), "ok")

    def action_open_embedded_terminal(self):
        self._select_tab("terminal")
        self.terminal_panel.refresh_devices(select=self.selected_device)
        if not self.terminal_panel.connected:
            self.terminal_panel.connect()

    def action_export_profiles(self):
        path = filedialog.asksaveasfilename(
            title="Export VOID profiles", defaultextension=".json",
            initialfile="void_profiles_backup.json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.cfg.data, indent=2, ensure_ascii=False), encoding="utf-8")
            self.log("Profiles exported to {}".format(path), "ok")
        except Exception as e:
            messagebox.showerror("Export", "Error during export:\n{}".format(e))

    def action_import_profiles(self):
        path = filedialog.askopenfilename(title="Import VOID profiles", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            incoming = json.loads(Path(path).read_text(encoding="utf-8"))
            if "devices" not in incoming:
                raise ValueError("invalid file: missing 'devices' key")
            mode = messagebox.askyesnocancel(
                "Import Profiles",
                "Yes = merge with existing profiles (overwrites duplicates)\n"
                "No = replace current profiles completely\n"
                "Cancel = do nothing"
            )
            if mode is None:
                return
            if mode:
                self.cfg.data["devices"].update(incoming.get("devices", {}))
            else:
                self.cfg.data["devices"] = incoming.get("devices", {})
                self.cfg.data["auto_connect"] = incoming.get("auto_connect")
            self.cfg.data["last_used"] = next(iter(self.cfg.data["devices"]), None)
            self.selected_device = self.cfg.data["last_used"]
            self.cfg.save()
            self._refresh_sidebar()
            self._render_dashboard()
            self.terminal_panel.refresh_devices()
            self.log("Profiles imported from {}".format(path), "ok")
        except Exception as e:
            messagebox.showerror("Import", "Error during import:\n{}".format(e))

    def action_open_ssh(self, svc):
        d = self.current_device()
        try:
            open_ssh_terminal(d["ip"], svc["port"], svc["user"])
            self.log("External terminal opened to {}:{}".format(d["ip"], svc["port"]), "ok")
        except Exception as e:
            cmd = "ssh -p {} {}@{}".format(svc["port"], svc["user"], d["ip"])
            self.clipboard_clear()
            self.clipboard_append(cmd)
            self.log("No terminal auto-detected ({}). Command copied: {}".format(e, cmd), "warn")
            messagebox.showinfo("SSH", "No graphical terminal auto-detected.\nCommand copied to clipboard:\n\n{}".format(cmd))

    def action_copy_ssh(self, svc):
        d = self.current_device()
        cmd = "ssh -p {} {}@{}".format(svc["port"], svc["user"], d["ip"])
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.log("SSH command copied to clipboard: {}".format(cmd), "info")

    def action_open_web(self, svc):
        d = self.current_device()
        url = "http://{}:{}".format(d["ip"], svc["port"])
        import webbrowser
        webbrowser.open(url)
        self.log("Opened {} in default browser".format(url), "ok")

    def action_copy_creds(self, svc):
        creds = "{}:{}".format(svc.get("user", ""), svc.get("pass", ""))
        self.clipboard_clear()
        self.clipboard_append(creds)
        self.log("Credentials copied to clipboard (user: {})".format(svc.get("user", "")), "info")

    def action_open_sftp(self, svc):
        d = self.current_device()
        uri = "sftp://{}:{}/".format(d["ip"], svc["port"])
        system = platform.system()
        try:
            if system == "Linux" and shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", uri])
            elif system == "Darwin":
                subprocess.Popen(["open", uri])
            else:
                raise RuntimeError("direct opening not supported on this system")
            self.log("SFTP client requested: {}".format(uri), "ok")
        except Exception as e:
            cmd = "sftp -P {} {}@{}".format(svc["port"], svc["user"], d["ip"])
            self.clipboard_clear()
            self.clipboard_append(cmd)
            self.log("Auto-open failed ({}). Command copied: {}".format(e, cmd), "warn")

    def action_push_file(self, svc):
        d = self.current_device()
        path = filedialog.askopenfilename(title="Select file to send")
        if not path:
            return
        PushFileDialog(self, d, svc, path)

    def action_quick_command(self, svc):
        d = self.current_device()
        QuickCommandDialog(self, d, svc)

    def action_install_console_app(self):
        d = self.current_device()
        if not d:
            messagebox.showinfo("Install App", "Select a device first.")
            return
        svc = d["services"].get("sftp") or d["services"].get("ssh")
        if not svc:
            messagebox.showinfo("Install App", "Enable SFTP or SSH on the profile.")
            return
        if not HAS_PARAMIKO:
            messagebox.showwarning("Install App", "paramiko is required: pip install paramiko")
            return
        if not CONSOLE_APP_DIR.exists():
            messagebox.showerror("Install App",
                                 "Console app folder not found:\n{}\n"
                                 "It must be next to this script.".format(CONSOLE_APP_DIR))
            return
        port = self.cfg.uplink().get("daemon_port", 31337)
        pc_ip = NetworkUtils.get_local_ip()
        if not messagebox.askyesno(
            "Install Console App",
            "The 'VOID_Uplink' app will be installed/updated on:\n"
            "  {} → {}\n\n"
            "It will be configured to point to this PC:\n"
            "  {}:{}\n\n"
            "If the PC IP is incorrect, change it later in the app's config.ini\n"
            "(via FileBrowser/SFTP).\n\nProceed?".format(d["ip"], CONSOLE_APP_REMOTE, pc_ip, port)):
            return

        self.log("Installing console app on {}...".format(d["ip"]), "info")

        def worker():
            try:
                transport = paramiko.Transport((d["ip"], int(svc["port"])))
                transport.connect(username=svc["user"], password=svc["pass"])
                sftp = paramiko.SFTPClient.from_transport(transport)
                try:
                    remote_root = CONSOLE_APP_REMOTE

                    def rmkdir(path):
                        parts = path.strip("/").split("/")
                        cur = ""
                        for p in parts:
                            cur += "/" + p
                            try:
                                sftp.stat(cur)
                            except FileNotFoundError:
                                try:
                                    sftp.mkdir(cur)
                                except Exception:
                                    pass

                    def send_tree(local_dir, remote_dir):
                        rmkdir(remote_dir)
                        for item in sorted(os.listdir(local_dir)):
                            lp = os.path.join(local_dir, item)
                            rp = remote_dir.rstrip("/") + "/" + item
                            if os.path.isdir(lp):
                                send_tree(lp, rp)
                            else:
                                sftp.put(lp, rp)
                                self.status_queue.put(("log", ("  → {}".format(rp), "info")))

                    send_tree(str(CONSOLE_APP_DIR), remote_root)
                    cfg_txt = ("[link]\npc_ip = {}\npc_port = {}\n"
                               "token =\npoll_seconds = 3\n".format(pc_ip, port))
                    with sftp.open(remote_root + "/config.ini", "w") as f:
                        f.write(cfg_txt)
                    try:
                        sftp.chmod(remote_root + "/mux_launch.sh", 0o755)
                    except Exception:
                        pass
                finally:
                    sftp.close()
                    transport.close()
                self.status_queue.put(("log", (
                    "Console app installed ✓ — find it in Applications on muOS "
                    "(refresh content if it does not appear immediately)", "ok")))
            except Exception as e:
                self.status_queue.put(("log", ("Console app installation failed: {}".format(e), "err")))

        threading.Thread(target=worker, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# §11  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    try:
        root = tk.Tk()
        root.withdraw()

        def launch_app():
            root.deiconify()
            app = VOIDBaseStation()
            app.mainloop()

        boot = BootSequence(root)
        boot.run(on_complete=launch_app)
        root.mainloop()
    except tk.TclError as e:
        print("[VOID] GUI initialisation error: {}".format(e))
        print("Ensure a graphical environment is active (X11/Wayland) and python3-tk is installed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
