#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  VOID BASESTATION
  Ground control for VoidDesk units -- Sector K telemetry relay
================================================================

Lightweight daemon (stdlib only) that runs on the PC and talks to
one or more VoidDesk (muOS) devices over plain HTTP/JSON. This is
the ground-side counterpart to VoidDesk's "PC Uplink" feature.

No SSH, no manual IP entry on either side: VoidDesk finds this
daemon by scanning its own subnet, and once it does, it starts
pushing its own telemetry here on every poll cycle.

Endpoints:

  GET  /ping            -> basestation identity (used by VoidDesk's
                            auto-discovery scan)
  GET  /stats           -> PC telemetry (cpu/ram/temp/net/...)
  POST /notify          -> notification FROM a device TO this PC
                            (desktop popup + spool)
  GET  /outbox          -> PC->device messages waiting for the
                            calling device (consumed on read)
  POST /outbox          -> queue a PC->device message (used by the
                            dashboard's "send notification" button)

  POST /device/<id>/stats   -> a device pushes its own telemetry
  GET  /device/<id>/stats   -> dashboard reads the latest pushed
                                telemetry for that device
  GET  /devices             -> list of all known devices (id, name,
                                last-seen, online/offline)

  GET  /device/<id>/command      -> a device polls for a pending
                                     basestation-initiated request
                                     (e.g. "send a screenshot")
  POST /device/<id>/command      -> dashboard queues a request for
                                     that device
  POST /device/<id>/screenshot   -> a device uploads a screenshot
                                     (base64 PNG) in response
  GET  /device/<id>/screenshot   -> dashboard fetches the latest
                                     screenshot for that device

Config:  ~/.config/void_basestation/daemon.json
Spool:   ~/.config/void_basestation/inbox.jsonl   (notifications received)
         ~/.config/void_basestation/outbox.json   (messages for devices)
         ~/.config/void_basestation/devices.json  (known devices, telemetry)

No external dependencies. Default port: 8420 (matches VoidDesk's
default scan port).
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.0"
APP_TAG = "VOID-BASESTATION"

CONFIG_DIR = Path.home() / ".config" / "void_basestation"
DAEMON_CFG = CONFIG_DIR / "daemon.json"
INBOX_FILE = CONFIG_DIR / "inbox.jsonl"
OUTBOX_FILE = CONFIG_DIR / "outbox.json"
DEVICES_FILE = CONFIG_DIR / "devices.json"

DEFAULT_CONFIG = {
    "port": 8420,
    "pc_name": "",                # empty = hostname
    "token": "",                  # if set, required as X-VOID-Token header
    "device_offline_after_s": 30,  # no push in this long -> offline
}


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


# ══════════════════════════════════════════════════════════════════
#  CONFIG + SPOOL
# ══════════════════════════════════════════════════════════════════

class Store:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.cfg = dict(DEFAULT_CONFIG)
        self._load()
        self._lock = threading.Lock()
        self._devices = {}
        self._load_devices()

    def _load(self):
        if DAEMON_CFG.exists():
            try:
                self.cfg.update(json.loads(
                    DAEMON_CFG.read_text(encoding="utf-8")))
            except Exception:
                pass

    def save(self):
        DAEMON_CFG.write_text(
            json.dumps(self.cfg, indent=2, ensure_ascii=False),
            encoding="utf-8")

    def _load_devices(self):
        if DEVICES_FILE.exists():
            try:
                self._devices = json.loads(
                    DEVICES_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._devices = {}

    def _save_devices(self):
        try:
            DEVICES_FILE.write_text(
                json.dumps(self._devices, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception:
            pass

    # ── devices (multi-device telemetry + commands) ───────────────
    def device_push_stats(self, dev_id, name, stats):
        with self._lock:
            d = self._devices.setdefault(dev_id, {})
            d["name"] = name or dev_id
            d["stats"] = stats
            d["last_seen"] = now_iso()
            d["last_seen_ts"] = time.time()
            d.setdefault("commands", [])
            d.setdefault("screenshot", None)
            self._save_devices()

    def device_list(self):
        with self._lock:
            offline_after = self.cfg.get("device_offline_after_s", 30)
            out = []
            for dev_id, d in self._devices.items():
                online = (time.time() - d.get("last_seen_ts", 0)) < \
                    offline_after
                out.append({"id": dev_id, "name": d.get("name", dev_id),
                           "last_seen": d.get("last_seen"),
                           "online": online})
            return out

    def device_get_stats(self, dev_id):
        with self._lock:
            d = self._devices.get(dev_id)
            return d.get("stats") if d else None

    def device_queue_command(self, dev_id, cmd):
        with self._lock:
            d = self._devices.setdefault(dev_id, {})
            d.setdefault("commands", []).append(cmd)
            self._save_devices()

    def device_pop_commands(self, dev_id):
        with self._lock:
            d = self._devices.get(dev_id)
            if not d:
                return []
            cmds = d.get("commands", [])
            d["commands"] = []
            self._save_devices()
            return cmds

    def device_add_file(self, dev_id, filename, b64data):
        import base64
        safe_dev = "".join(c for c in dev_id if c.isalnum() or
                          c in "-_") or "unknown"
        safe_fn = os.path.basename(filename) or "file.bin"
        out_dir = Path(__file__).resolve().parent / \
            "received_files" / safe_dev
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / safe_fn
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64data))
        with self._lock:
            d = self._devices.setdefault(dev_id, {})
            files = d.setdefault("received_files", [])
            files.insert(0, {"name": safe_fn,
                            "ts": now_iso(),
                            "size": out_path.stat().st_size})
            d["received_files"] = files[:50]
            self._save_devices()
        return str(out_path)

    def device_list_files(self, dev_id):
        with self._lock:
            d = self._devices.get(dev_id) or {}
            return d.get("received_files", [])

    def device_set_screenshot(self, dev_id, b64png):
        with self._lock:
            d = self._devices.setdefault(dev_id, {})
            d["screenshot"] = b64png
            d["screenshot_ts"] = now_iso()
            self._save_devices()

    def device_get_screenshot(self, dev_id):
        with self._lock:
            d = self._devices.get(dev_id)
            if not d:
                return None, None
            return d.get("screenshot"), d.get("screenshot_ts")

    # ── outbox (basestation -> device) ─────────────────────────────
    def outbox_read(self, drain=False):
        with self._lock:
            if not OUTBOX_FILE.exists():
                return []
            try:
                items = json.loads(OUTBOX_FILE.read_text(
                    encoding="utf-8"))
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
                    items = json.loads(OUTBOX_FILE.read_text(
                        encoding="utf-8"))
                except Exception:
                    items = []
            items.append({"title": str(title)[:80],
                          "body": str(body)[:300], "ts": now_iso()})
            items = items[-50:]
            OUTBOX_FILE.write_text(
                json.dumps(items, ensure_ascii=False, indent=1),
                encoding="utf-8")

    # ── inbox (device -> basestation) ──────────────────────────────
    def inbox_push(self, title, body=""):
        rec = {"title": str(title)[:80], "body": str(body)[:300],
              "ts": now_iso(), "read": False}
        with self._lock:
            with open(INBOX_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════════
#  PC TELEMETRY (unchanged from the earlier daemon -- this part
#  was already solid, no reason to redo it)
# ══════════════════════════════════════════════════════════════════

class PcStats:
    def __init__(self):
        self._cpu_prev = None
        self._net_prev = None
        self._net_prev_t = None
        self._has_xdotool = shutil.which("xdotool") is not None

    def _cpu_times(self):
        try:
            with open("/proc/stat") as f:
                parts = f.readline().split()[1:]
            vals = [int(x) for x in parts]
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            total = sum(vals)
            return idle, total
        except Exception:
            return None

    def cpu_percent(self):
        cur = self._cpu_times()
        if cur is None:
            return None
        if self._cpu_prev is None:
            self._cpu_prev = cur
            time.sleep(0.05)
            cur2 = self._cpu_times()
            if cur2 is None:
                return None
            prev, cur = cur, cur2
        else:
            prev, cur = self._cpu_prev, cur
        self._cpu_prev = cur
        didle = cur[0] - prev[0]
        dtot = cur[1] - prev[1]
        if dtot <= 0:
            return 0.0
        return round(100.0 * (1.0 - didle / dtot), 1)

    @staticmethod
    def mem_info():
        info = {}
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0])
        except Exception:
            return {}
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        used = total - avail
        return {"total_mb": round(total / 1024, 1),
               "used_mb": round(used / 1024, 1),
               "available_mb": round(avail / 1024, 1),
               "percent": round(100.0 * used / total, 1) if total
               else 0.0}

    @staticmethod
    def temperatures():
        out = []
        base = Path("/sys/class/thermal")
        try:
            for zone in sorted(base.glob("thermal_zone*")):
                try:
                    t = int((zone / "temp").read_text().strip()) \
                        / 1000.0
                    label = (zone / "type").read_text().strip()
                except Exception:
                    continue
                if 0 < t < 150:
                    out.append({"zone": label, "temp_c": round(t, 1)})
        except Exception:
            pass
        friendly = {"x86_pkg_temp": "CPU", "coretemp": "CPU",
                   "cpu-thermal": "CPU", "acpitz": "ACPI",
                   "soc-thermal": "SoC", "gpu-thermal": "GPU",
                   "nvme": "NVMe", "iwlwifi_1": "WiFi"}
        for z in out:
            z["label"] = friendly.get(z["zone"], z["zone"])
        return out

    def net_rates(self):
        now = time.time()
        cur = {}
        base = Path("/sys/class/net")
        try:
            for iface in base.iterdir():
                name = iface.name
                if name == "lo":
                    continue
                try:
                    rx = int((iface / "statistics/rx_bytes")
                            .read_text())
                    tx = int((iface / "statistics/tx_bytes")
                            .read_text())
                except Exception:
                    continue
                cur[name] = (rx, tx)
        except Exception:
            pass
        rates = {}
        if self._net_prev is not None and self._net_prev_t:
            dt = max(now - self._net_prev_t, 0.001)
            for name, (rx, tx) in cur.items():
                if name in self._net_prev:
                    prx, ptx = self._net_prev[name]
                    rates[name] = {
                        "rx_kbs": round((rx - prx) / dt / 1024, 1),
                        "tx_kbs": round((tx - ptx) / dt / 1024, 1),
                        "rx_total_mb": round(rx / 1048576, 1),
                        "tx_total_mb": round(tx / 1048576, 1)}
        self._net_prev = cur
        self._net_prev_t = now
        return rates

    @staticmethod
    def net_addrs():
        out = {}
        try:
            txt = subprocess.run(
                ["ip", "-o", "-4", "addr", "show", "scope", "global"],
                capture_output=True, text=True, timeout=3).stdout
            for line in txt.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    out[parts[1]] = parts[3].split("/")[0]
        except Exception:
            pass
        return out

    @staticmethod
    def storage():
        out = []
        try:
            st = shutil.disk_usage("/")
            out.append({"mount": "/",
                       "total_gb": round(st.total / 2**30, 1),
                       "used_gb": round(st.used / 2**30, 1),
                       "percent": round(100.0 * st.used / st.total, 1)})
        except Exception:
            pass
        return out

    @staticmethod
    def load_uptime():
        load = []
        try:
            with open("/proc/loadavg") as f:
                load = [float(x) for x in f.read().split()[:3]]
        except Exception:
            pass
        up = 0.0
        try:
            with open("/proc/uptime") as f:
                up = float(f.read().split()[0])
        except Exception:
            pass
        return load, up

    @staticmethod
    def top_processes(n=5):
        procs = []
        try:
            with open("/proc/stat") as f:
                total = sum(int(x) for x in
                           f.readline().split()[1:])
            for p in Path("/proc").iterdir():
                if not p.name.isdigit():
                    continue
                try:
                    stat = (p / "stat").read_text()
                    rparen = stat.rfind(")")
                    name = stat[stat.find("(") + 1:rparen]
                    fields = stat[rparen + 2:].split()
                    ticks = int(fields[11]) + int(fields[12])
                    procs.append((ticks, name))
                except Exception:
                    continue
        except Exception:
            return []
        procs.sort(reverse=True)
        out = []
        for ticks, name in procs[:n]:
            pct = round(100.0 * ticks / max(total, 1), 2)
            out.append({"name": name, "cpu_cum_pct": pct})
        return out

    def focused_window(self):
        if not self._has_xdotool:
            return ""
        try:
            wid = subprocess.run(
                ["xdotool", "getwindowfocus"], capture_output=True,
                text=True, timeout=2).stdout.strip()
            title = subprocess.run(
                ["xdotool", "getwindowname", wid], capture_output=True,
                text=True, timeout=2).stdout.strip()
            return title[:80]
        except Exception:
            return ""

    def snapshot(self):
        load, up = self.load_uptime()
        return {"ts": now_iso(), "hostname": socket.gethostname(),
               "os": "%s %s" % (platform.system(), platform.release()),
               "cpu_percent": self.cpu_percent(),
               "cpu_count": os.cpu_count() or 1, "load": load,
               "memory": self.mem_info(),
               "temperatures": self.temperatures(),
               "net_rates": self.net_rates(),
               "net_addrs": self.net_addrs(), "storage": self.storage(),
               "uptime_s": up, "top_processes": self.top_processes(),
               "active_window": self.focused_window()}


def desktop_notify(title, body):
    system = platform.system()
    try:
        if system == "Linux" and shutil.which("notify-send"):
            subprocess.Popen(["notify-send", "-a", "Void Basestation",
                             title, body])
        elif system == "Darwin":
            script = 'display notification "%s" with title "%s"' % (
                body.replace('"', "'"), title.replace('"', "'"))
            subprocess.Popen(["osascript", "-e", script])
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  PORT FALLBACK
# ══════════════════════════════════════════════════════════════════

def find_free_port(start_port, max_attempts=10):
    for attempt in range(max_attempts):
        port = start_port + attempt
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            s.close()
            return port, attempt
        except OSError:
            s.close()
            continue
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 0))
    assigned = s.getsockname()[1]
    s.close()
    return assigned, max_attempts


# ══════════════════════════════════════════════════════════════════
#  HTTP SERVER
# ══════════════════════════════════════════════════════════════════

def make_handler(store, stats):
    class Handler(BaseHTTPRequestHandler):
        server_version = APP_TAG + "/" + VERSION

        def log_message(self, fmt, *args):
            pass

        def _auth_ok(self):
            token = store.cfg.get("token", "")
            if not token:
                return True
            return self.headers.get("X-VOID-Token", "") == token

        def _json(self, obj, code=200):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type",
                            "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                n = 0
            if n <= 0 or n > 6_000_000:
                return {}
            try:
                return json.loads(self.rfile.read(n)
                                  .decode("utf-8", errors="replace"))
            except Exception:
                return {}

        def _path_parts(self):
            import urllib.parse
            p = urllib.parse.urlparse(self.path).path
            return [x for x in p.split("/") if x]

        def do_GET(self):
            if not self._auth_ok():
                return self._json({"error": "unauthorized"}, 401)
            parts = self._path_parts()
            if parts == ["ping"]:
                self._json({"ok": True,
                           "name": store.cfg.get("pc_name") or
                           socket.gethostname(), "version": VERSION,
                           "ts": now_iso()})
            elif parts == ["stats"]:
                try:
                    self._json(stats.snapshot())
                except Exception as e:
                    self._json({"error": str(e)}, 500)
            elif parts == ["outbox"]:
                self._json({"messages": store.outbox_read(drain=True)})
            elif parts == ["devices"]:
                self._json({"devices": store.device_list()})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "stats":
                data = store.device_get_stats(parts[1])
                self._json({"stats": data})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "command":
                cmds = store.device_pop_commands(parts[1])
                self._json({"commands": cmds})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "screenshot":
                png, ts = store.device_get_screenshot(parts[1])
                self._json({"png_base64": png, "ts": ts})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "files":
                self._json({"files": store.device_list_files(
                    parts[1])})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            if not self._auth_ok():
                return self._json({"error": "unauthorized"}, 401)
            parts = self._path_parts()
            data = self._body()
            if parts == ["notify"]:
                title = data.get("title", "Device")
                body = data.get("body", "")
                store.inbox_push(title, body)
                desktop_notify("[%s] %s" % (
                    data.get("device_name", "Device"), title), body)
                print("[%s] NOTIFY FROM DEVICE -> %s: %s" %
                     (now_iso(), title, body), flush=True)
                self._json({"ok": True})
            elif parts == ["outbox"]:
                title = data.get("title", "")
                body = data.get("body", "")
                if not title:
                    return self._json({"error": "title required"},
                                      400)
                store.outbox_push(title, body)
                self._json({"ok": True})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "stats":
                store.device_push_stats(parts[1],
                                        data.get("name", parts[1]),
                                        data.get("stats", {}))
                self._json({"ok": True})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "command":
                store.device_queue_command(parts[1], data)
                self._json({"ok": True})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "screenshot":
                store.device_set_screenshot(
                    parts[1], data.get("png_base64", ""))
                self._json({"ok": True})
            elif len(parts) == 3 and parts[0] == "device" and \
                    parts[2] == "file":
                try:
                    saved_path = store.device_add_file(
                        parts[1], data.get("filename", "file.bin"),
                        data.get("data_base64", ""))
                    self._json({"ok": True, "path": saved_path})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 400)
            else:
                self._json({"error": "not found"}, 404)

    return Handler


def main():
    store = Store()
    stats = PcStats()

    cfg_port = int(store.cfg.get("port", 8420))
    port, attempts = find_free_port(cfg_port)
    if attempts > 0:
        print("[%s] port %d busy, using %d instead" %
             (APP_TAG, cfg_port, port), flush=True)

    handler = make_handler(store, stats)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print("[%s] v%s listening on 0.0.0.0:%d (%s)" %
         (APP_TAG, VERSION, port,
          store.cfg.get("pc_name") or socket.gethostname()),
         flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


import base64
import io
import tkinter as tk
from tkinter import font as tkfont


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD -- tema VOID: sfondo scuro, accento ciano
# ══════════════════════════════════════════════════════════════════

BG0 = "#0b0d10"
BG1 = "#12161a"
PANEL = "#161b20"
CYAN = "#3fd6c4"
DIM = "#5a6570"
TEXT = "#d8dde2"
RED = "#e2504a"
GREEN = "#4fc97a"
FONT_F = "Courier New"


class DevicesPanel(tk.Frame):
    """Elenco dispositivi noti, con pallino online/offline vero."""

    def __init__(self, master, on_select):
        super().__init__(master, bg=BG1)
        self.on_select = on_select
        self.selected = None
        tk.Label(self, text="DEVICES", bg=BG1, fg=CYAN,
                font=(FONT_F, 11, "bold")).pack(anchor="w", padx=10,
                                                pady=(10, 4))
        self.list_frame = tk.Frame(self, bg=BG1)
        self.list_frame.pack(fill="both", expand=True, padx=6)
        self.rows = {}

    def update_devices(self, devices):
        seen = set()
        for d in devices:
            seen.add(d["id"])
            if d["id"] not in self.rows:
                row = tk.Frame(self.list_frame, bg=BG1, cursor="hand2")
                row.pack(fill="x", pady=1)
                dot = tk.Canvas(row, width=10, height=10, bg=BG1,
                                highlightthickness=0)
                dot.pack(side="left", padx=(4, 6), pady=6)
                lbl = tk.Label(row, text="", bg=BG1, fg=TEXT,
                              font=(FONT_F, 10), anchor="w")
                lbl.pack(side="left", fill="x", expand=True)
                for w in (row, dot, lbl):
                    w.bind("<Button-1>",
                          lambda e, did=d["id"]: self.on_select(did))
                self.rows[d["id"]] = (row, dot, lbl)
            row, dot, lbl = self.rows[d["id"]]
            dot.delete("all")
            dot.create_oval(1, 1, 9, 9,
                            fill=GREEN if d["online"] else DIM,
                            outline="")
            lbl.config(text=d["name"],
                      fg=TEXT if d["online"] else DIM)
        for did in list(self.rows):
            if did not in seen:
                self.rows[did][0].destroy()
                del self.rows[did]


class DeviceDetailPanel(tk.Frame):
    """Statistiche del dispositivo selezionato, richiesta
    screenshot, invio notifica."""

    def __init__(self, master, store, request_screenshot_fn):
        super().__init__(master, bg=BG0)
        self.store = store
        self.request_screenshot_fn = request_screenshot_fn
        self.device_id = None
        self._shot_img = None

        self.title_lbl = tk.Label(self, text="Select a device", bg=BG0,
                                  fg=CYAN, font=(FONT_F, 13, "bold"))
        self.title_lbl.pack(anchor="w", padx=14, pady=(14, 6))

        stats_frame = tk.Frame(self, bg=PANEL)
        stats_frame.pack(fill="x", padx=14, pady=6)
        self.stats_text = tk.Label(stats_frame, text="", bg=PANEL,
                                   fg=TEXT, font=(FONT_F, 10),
                                   justify="left", anchor="w")
        self.stats_text.pack(fill="x", padx=10, pady=10)

        btn_row = tk.Frame(self, bg=BG0)
        btn_row.pack(fill="x", padx=14, pady=6)
        self.shot_btn = tk.Button(
            btn_row, text="Request screenshot", bg=PANEL, fg=CYAN,
            activebackground=PANEL, relief="flat",
            font=(FONT_F, 10), command=self._on_screenshot)
        self.shot_btn.pack(side="left")

        self.shot_canvas = tk.Canvas(self, bg=BG1, height=260,
                                     highlightthickness=1,
                                     highlightbackground=DIM)
        self.shot_canvas.pack(fill="x", padx=14, pady=8)
        self.shot_canvas.create_text(
            10, 10, anchor="nw", fill=DIM, font=(FONT_F, 9),
            text="No screenshot yet", tags="placeholder")

        notify_frame = tk.Frame(self, bg=BG0)
        notify_frame.pack(fill="x", padx=14, pady=(6, 14))
        self.notify_entry = tk.Entry(notify_frame, bg=PANEL, fg=TEXT,
                                     insertbackground=TEXT,
                                     font=(FONT_F, 10))
        self.notify_entry.pack(side="left", fill="x", expand=True,
                               ipady=4)
        tk.Button(notify_frame, text="Notify", bg=PANEL, fg=CYAN,
                 activebackground=PANEL, relief="flat",
                 font=(FONT_F, 10),
                 command=self._on_notify).pack(side="left", padx=(6, 0))

    def set_device(self, device_id, name):
        self.device_id = device_id
        self.title_lbl.config(text=name)

    def _on_screenshot(self):
        if self.device_id:
            self.request_screenshot_fn(self.device_id)

    def _on_notify(self):
        if not self.device_id:
            return
        msg = self.notify_entry.get().strip()
        if not msg:
            return
        self.store.outbox_push(msg, "")
        self.notify_entry.delete(0, "end")

    def refresh(self):
        if not self.device_id:
            return
        stats = self.store.device_get_stats(self.device_id)
        if stats:
            lines = []
            for k, v in stats.items():
                lines.append("%-20s %s" % (k, v))
            self.stats_text.config(text="\n".join(lines))
        else:
            self.stats_text.config(text="(no telemetry yet)")
        png_b64, ts = self.store.device_get_screenshot(self.device_id)
        if png_b64:
            self._show_screenshot(png_b64)

    def _show_screenshot(self, png_b64):
        try:
            raw = base64.b64decode(png_b64)
            img = tk.PhotoImage(data=base64.b64encode(raw))
        except Exception:
            return
        self._shot_img = img
        self.shot_canvas.delete("all")
        cw = self.shot_canvas.winfo_width() or 400
        iw = img.width() or 1
        scale = max(1, iw // max(1, cw))
        if scale > 1:
            img = img.subsample(scale, scale)
            self._shot_img = img
        self.shot_canvas.create_image(4, 4, anchor="nw", image=img)


class PcStatsBar(tk.Frame):
    """Riepilogo statistiche del PC stesso, sempre visibile in alto."""

    def __init__(self, master, pcstats):
        super().__init__(master, bg=PANEL)
        self.pcstats = pcstats
        self.lbl = tk.Label(self, text="", bg=PANEL, fg=DIM,
                            font=(FONT_F, 9), anchor="w")
        self.lbl.pack(fill="x", padx=10, pady=6)

    def refresh(self):
        try:
            snap = self.pcstats.snapshot()
            mem = snap.get("memory", {})
            txt = "PC  ·  CPU %s%%  ·  RAM %s%%  ·  %s" % (
                snap.get("cpu_percent"), mem.get("percent"),
                snap.get("hostname"))
        except Exception:
            txt = "PC  ·  (stats unavailable)"
        self.lbl.config(text=txt)


class BasestationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VOID BASESTATION")
        self.configure(bg=BG0)
        self.geometry("760x520")

        self.store = Store()
        self.pcstats = PcStats()
        self._start_server()

        top = PcStatsBar(self, self.pcstats)
        top.pack(fill="x")
        self.pc_bar = top

        body = tk.Frame(self, bg=BG0)
        body.pack(fill="both", expand=True)

        self.devices_panel = DevicesPanel(body, self._on_select_device)
        self.devices_panel.pack(side="left", fill="y")

        self.detail_panel = DeviceDetailPanel(
            body, self.store, self._request_screenshot)
        self.detail_panel.pack(side="left", fill="both", expand=True)

        self._device_names = {}
        self._tick()

    def _start_server(self):
        handler = make_handler(self.store, self.pcstats)
        cfg_port = int(self.store.cfg.get("port", 8420))
        port, _ = find_free_port(cfg_port)
        ThreadingHTTPServer.allow_reuse_address = True
        self.httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
        t = threading.Thread(target=self.httpd.serve_forever,
                             daemon=True)
        t.start()
        self.title("VOID BASESTATION  ::  port %d" % port)

    def _on_select_device(self, device_id):
        self.devices_panel.selected = device_id
        name = self._device_names.get(device_id, device_id)
        self.detail_panel.set_device(device_id, name)
        self.detail_panel.refresh()

    def _request_screenshot(self, device_id):
        self.store.device_queue_command(device_id, {"cmd": "screenshot"})

    def _tick(self):
        devices = self.store.device_list()
        for d in devices:
            self._device_names[d["id"]] = d["name"]
        self.devices_panel.update_devices(devices)
        self.pc_bar.refresh()
        if self.devices_panel.selected:
            self.detail_panel.refresh()
        self.after(1500, self._tick)


def run_gui():
    app = BasestationApp()
    app.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        main()
    else:
        run_gui()

