# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // mpvctl -- controllo mpv via socket IPC JSON.
#  Condiviso da Void Radio e Void Podcaster: un solo posto per lanciare mpv,
#  parlargli, e leggere lo stato (posizione, metadati ICY, errori).
# ============================================================================
import json
import os
import socket
import subprocess
import threading
import time


class MpvController:
    def __init__(self, sock_path=None):
        self.sock_path = sock_path or "/tmp/voiddesk_mpv.sock"
        self.proc = None
        self._sock = None
        self._lock = threading.Lock()
        self._req_id = 0
        self.last_error = ""
        self.log_path = self.sock_path + ".log"

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, url, extra_args=None):
        """Avvia mpv su un URL/percorso, in pausa iniziale disattivata.
        Ritorna (ok, errore)."""
        self.stop()
        try:
            if os.path.exists(self.sock_path):
                os.remove(self.sock_path)
            if os.path.exists(self.log_path):
                os.remove(self.log_path)
        except OSError:
            pass
        args = ["mpv", "--no-video", "--idle=no", "--no-terminal",
               "--input-ipc-server=" + self.sock_path,
               "--volume=100", "--audio-client-name=VoidRadio",
               "--stream-buffer-size=2MiB",
               "--log-file=" + self.log_path, "--really-quiet"]
        if extra_args:
            args += extra_args
        args.append(url)
        try:
            self.proc = subprocess.Popen(
                args, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except (OSError, FileNotFoundError) as e:
            self.last_error = str(e)[:80]
            return False, self.last_error
        for _ in range(30):
            if os.path.exists(self.sock_path):
                break
            time.sleep(0.1)
        else:
            self.last_error = "socket IPC non comparso"
            return False, self.last_error
        for _ in range(10):
            try:
                self._connect()
                # Il socket viene creato prima della connessione HTTP: senza
                # questo controllo una radio morta risultava "avviata".
                time.sleep(0.25)
                if not self.is_running():
                    self.last_error = self._read_last_error()
                    return False, self.last_error
                return True, ""
            except (OSError, ConnectionError):
                time.sleep(0.1)
        self.last_error = "connessione al socket fallita"
        return False, self.last_error

    def _read_last_error(self):
        """Restituisce l'ultima causa utile di mpv senza esporre un log
        enorme nell'interfaccia a 640px."""
        try:
            with open(self.log_path, "r", errors="replace") as f:
                lines = f.readlines()[-30:]
            for line in reversed(lines):
                low = line.lower()
                if any(word in low for word in ("error", "failed", "cannot",
                                                "unable", "network", "http")):
                    return line.strip()[-110:]
        except OSError:
            pass
        return "mpv ha chiuso lo stream"

    def _connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(self.sock_path)
        self._sock = s

    def _send(self, command):
        """Manda un comando IPC vero, ritorna la risposta parsata o
        None se qualcosa va storto (mpv chiuso, socket morto...)."""
        if self._sock is None:
            return None
        with self._lock:
            self._req_id += 1
            payload = json.dumps({"command": command,
                                  "request_id": self._req_id}) + "\n"
            try:
                self._sock.sendall(payload.encode("utf-8"))
                buf = b""
                t0 = time.time()
                while time.time() - t0 < 2.0:
                    chunk = self._sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    for line in buf.split(b"\n"):
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                        except ValueError:
                            continue
                        if obj.get("request_id") == self._req_id:
                            return obj
                return None
            except (OSError, socket.timeout):
                return None

    def get_property(self, name):
        r = self._send(["get_property", name])
        if r and r.get("error") == "success":
            return r.get("data")
        return None

    def set_property(self, name, value):
        self._send(["set_property", name, value])

    def toggle_pause(self):
        cur = self.get_property("pause")
        self.set_property("pause", not cur if cur is not None
                          else True)
        return self.get_property("pause")

    def set_volume(self, vol):
        self.set_property("volume", max(0, min(100, vol)))

    def status(self):
        """Istantanea vera dello stato: posizione, durata, metadati
        ICY se lo stream li espone, se sta ancora bufferizzando."""
        if not self.is_running():
            return {"running": False}
        out = {"running": True,
              "pause": self.get_property("pause"),
              "time_pos": self.get_property("time-pos"),
              "duration": self.get_property("duration"),
              "volume": self.get_property("volume"),
              "core_idle": self.get_property("core-idle"),
              "paused_for_cache": self.get_property(
                  "paused-for-cache")}
        meta = self.get_property("metadata")
        if isinstance(meta, dict):
            out["icy_title"] = (meta.get("icy-title") or
                               meta.get("title") or "")
            out["icy_name"] = meta.get("icy-name") or ""
        return out

    def stop(self):
        if self._sock is not None:
            try:
                self._send(["quit"])
            except Exception:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except OSError:
                    pass
            self.proc = None
        try:
            if os.path.exists(self.sock_path):
                os.remove(self.sock_path)
        except OSError:
            pass
