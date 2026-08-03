# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // pcuplink — client verso il demone SPDW sul PC.
#  Adattato da net.py (app di riferimento SPDW Uplink, PySDL2): stessa
#  architettura, stesso protocollo. Polling in thread separato con lock:
#  la UI non si blocca mai, nemmeno a PC spento o irraggiungibile.
# ============================================================================
import json
import threading
import time
import urllib.request
import urllib.error


def local_subnet_hosts(own_ip):
    """Indirizzi candidati della sottorete /24 propria, esclusi
    l'indirizzo di rete, broadcast, e se' stessi."""
    try:
        parts = own_ip.split(".")
        if len(parts) != 4:
            return []
        base = ".".join(parts[:3])
        return ["%s.%d" % (base, i) for i in range(1, 255)
               if "%s.%d" % (base, i) != own_ip]
    except (ValueError, AttributeError):
        return []


def scan_for_servers(own_ip, port=8420, timeout=0.25, max_workers=48):
    """Scansione in parallelo della sottorete propria: prova /ping su
    ogni indirizzo candidato con molti thread contemporanei (non uno
    alla volta -- 254 tentativi in sequenza sarebbero troppo lenti).
    Ritorna la lista dei server che hanno risposto per davvero."""
    hosts = local_subnet_hosts(own_ip)
    if not hosts:
        return []
    found = []
    found_lock = threading.Lock()

    def probe(ip):
        url = "http://%s:%d/ping" % (ip, port)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "VoidDesk-Uplink/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8",
                                                   errors="replace"))
            with found_lock:
                found.append({"host": ip, "port": port,
                             "name": data.get("name", ip),
                             "version": data.get("version", "")})
        except Exception:
            pass

    threads = []
    for ip in hosts:
        t = threading.Thread(target=probe, args=(ip,), daemon=True)
        threads.append(t)
    # avvio a ondate per non aprire 254 socket in un colpo solo
    i = 0
    while i < len(threads):
        wave = threads[i:i + max_workers]
        for t in wave:
            t.start()
        for t in wave:
            t.join(timeout=timeout + 0.3)
        i += max_workers
    return found


class PcClient:
    def __init__(self, host, port, token="", poll_s=3.0,
                device_id=None, device_name="", stats_fn=None,
                screenshot_fn=None):
        self.host = host
        self.port = int(port) if port else 8420
        self.token = token
        self.poll_s = poll_s
        self.device_id = device_id or "unknown"
        self.device_name = device_name
        self.stats_fn = stats_fn
        self.screenshot_fn = screenshot_fn

        self.stats = None
        self.inbox = []
        self.new_messages = []
        self.online = False
        self.ping_ms = None
        self.pc_name = ""
        self.daemon_version = ""
        self.last_ok = 0.0
        self.last_error = ""

        self._lock = threading.Lock()
        self._stop = False
        self._force = threading.Event()
        self._cycle = 0
        self._thread = None

    def _get(self, path, timeout=2.5):
        url = "http://{}:{}{}".format(self.host, self.port, path)
        headers = {"User-Agent": "VoidDesk-Uplink/1.0"}
        if self.token:
            headers["X-VOID-Token"] = self.token
        req = urllib.request.Request(url, headers=headers)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        return data, (time.time() - t0) * 1000.0

    def _post(self, path, payload, timeout=2.5):
        url = "http://{}:{}{}".format(self.host, self.port, path)
        headers = {"Content-Type": "application/json",
                   "User-Agent": "VoidDesk-Uplink/1.0"}
        if self.token:
            headers["X-VOID-Token"] = self.token
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self._force.set()

    def force_refresh(self):
        self._force.set()

    def _loop(self):
        while not self._stop:
            self._cycle += 1
            try:
                data, ms = self._get("/stats")
                with self._lock:
                    self.stats = data
                    self.ping_ms = round(ms, 1)
                    self.online = True
                    self.last_ok = time.time()
                    self.last_error = ""
                if self._cycle % 10 == 1:
                    try:
                        ping, _ = self._get("/ping")
                        with self._lock:
                            self.pc_name = ping.get("name", "")
                            self.daemon_version = ping.get(
                                "version", "")
                    except Exception:
                        pass
                if self.stats_fn:
                    try:
                        dev_stats = self.stats_fn()
                        self._post(
                            "/device/%s/stats" % self.device_id,
                            {"name": self.device_name,
                             "stats": dev_stats})
                    except Exception:
                        pass
                try:
                    cmds_resp, _ = self._get(
                        "/device/%s/command" % self.device_id)
                    for cmd in cmds_resp.get("commands", []):
                        if cmd.get("cmd") == "screenshot" and \
                                self.screenshot_fn:
                            try:
                                png_b64 = self.screenshot_fn()
                                self._post(
                                    "/device/%s/screenshot" %
                                    self.device_id,
                                    {"png_base64": png_b64})
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    box, _ = self._get("/outbox")
                    msgs = box.get("messages", [])
                    if msgs:
                        with self._lock:
                            for m in msgs:
                                self.inbox.insert(0, m)
                                self.new_messages.append(m)
                            self.inbox = self.inbox[:30]
                except Exception:
                    pass
            except Exception as e:
                with self._lock:
                    self.online = False
                    self.last_error = str(e)[:60]
            self._force.clear()
            self._force.wait(self.poll_s)

    def send_notify(self, title, body=""):
        try:
            self._post("/notify", {"title": title, "body": body,
                                   "device_name": self.device_name})
            return True, ""
        except Exception as e:
            return False, str(e)[:60]

    def send_file(self, device_id, local_path):
        import base64
        import os
        try:
            with open(local_path, "rb") as f:
                content = f.read()
            b64 = base64.b64encode(content).decode("ascii")
            fn = os.path.basename(local_path)
            self._post("/device/%s/file" % device_id,
                      {"filename": fn, "data_base64": b64})
            return True, ""
        except Exception as e:
            return False, str(e)[:60]

    def snapshot(self):
        with self._lock:
            return {
                "stats": self.stats,
                "inbox": list(self.inbox),
                "online": self.online,
                "ping_ms": self.ping_ms,
                "pc_name": self.pc_name,
                "daemon_version": self.daemon_version,
                "last_ok": self.last_ok,
                "last_error": self.last_error,
            }

    def pop_new_messages(self):
        with self._lock:
            out = list(self.new_messages)
            self.new_messages.clear()
            return out
