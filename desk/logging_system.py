# -*- coding: utf-8 -*-
"""
VoidDesk Logging System
Modular, async-capable logging with per-module files and central registry.
"""
import os
import time
import json
import threading
import zipfile
import socket
import urllib.request
from enum import IntEnum
from collections import deque
from datetime import datetime

from desk.const import LOGS_DIR, DATA


ARCHIVES_DIR = os.path.join(LOGS_DIR, "archives")
LOGGER_CONFIG_FILE = os.path.join(LOGS_DIR, "logger_config.json")

for _d in (ARCHIVES_DIR,):
    try:
        os.makedirs(_d, exist_ok=True)
    except OSError:
        pass


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class Logger:
    def __init__(self, name, filename, level=LogLevel.INFO, max_size_mb=5, enabled=True):
        self.name = name
        self.filename = filename
        self.level = level
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.enabled = enabled
        self._queue = deque()
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._flush_interval = 0.5

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self._flush()

    def _worker(self):
        while self._running:
            time.sleep(self._flush_interval)
            self._flush()

    def _flush(self):
        with self._lock:
            lines = list(self._queue)
            self._queue.clear()
        if not lines:
            return
        full_path = os.path.join(LOGS_DIR, self.filename)
        try:
            if os.path.exists(full_path) and os.path.getsize(full_path) > self.max_size_bytes:
                old = full_path + ".old"
                if os.path.exists(old):
                    os.remove(old)
                os.rename(full_path, old)
            with open(full_path, "a", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError:
            pass

    def log(self, level, msg):
        if not self.enabled or level < self.level:
            return
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[%s] [%s] %s\n" % (timestamp, level.name, msg)
        with self._lock:
            self._queue.append(line)
        LogRegistry.get_instance().add_entry(level, msg, self.name, timestamp)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def set_level(self, level):
        self.level = level


class LogRegistry:
    _instance = None
    MAX_ENTRIES = 1000

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._entries = deque(maxlen=self.MAX_ENTRIES)
        self._lock = threading.Lock()
        self._callbacks = []

    def add_entry(self, level, msg, source, timestamp=None):
        if timestamp is None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {"timestamp": timestamp, "level": level.name, "source": source, "message": msg}
        with self._lock:
            self._entries.append(entry)
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception:
                pass

    def get_entries(self, source_filter=None, level_filter=None, limit=None):
        with self._lock:
            entries = list(self._entries)
        if source_filter:
            entries = [e for e in entries if e["source"] == source_filter]
        if level_filter:
            entries = [e for e in entries if e["level"] == level_filter]
        if limit:
            entries = entries[-limit:]
        return entries

    def analyze(self, limit=200):
        """Analizza gli ultimi 'limit' log. Restituisce conteggi per livello."""
        entries = self.get_entries(limit=limit)
        counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        for e in entries:
            lvl = e["level"]
            if lvl in counts:
                counts[lvl] += 1
        return counts

    def clear(self):
        with self._lock:
            self._entries.clear()

    def register_callback(self, callback):
        self._callbacks.append(callback)

    def unregister_callback(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)


class LoggerManager:
    _instance = None

    MODULE_LOGS = {
        "voiddesk": {"file": "voiddesk.log", "desc": "Log principale di VoidDesk", "fundamental": True},
        "lastsession": {"file": "voiddesk_lastsession.log", "desc": "Log dell'ultima sessione", "fundamental": True},
        "debug": {"file": "voiddesk_debug.log", "desc": "Log di debug", "fundamental": False},
        "forge": {"file": "forge.log", "desc": "ForgeHub (installer, update)"},
        "uplink": {"file": "uplink.log", "desc": "UplinkHub (rete, WiFi, BT)"},
        "media": {"file": "media.log", "desc": "MediaHub (radio, IPTV, BGM)"},
        "workshop": {"file": "workshop.log", "desc": "WorkshopHub (stats, diag)"},
        "toolbox": {"file": "toolbox.log", "desc": "ToolboxHub (utilities)"},
        "controller": {"file": "controller.log", "desc": "ControllerHub (mapping)"},
        "info": {"file": "info.log", "desc": "InfoHub (about, manuale)"},
        "shutdown": {"file": "shutdown.log", "desc": "ShutdownHub (spegnimento)"},
        "games": {"file": "games.log", "desc": "GamesHub"},
        "develop": {"file": "develop.log", "desc": "DevelopHub"},
        "community": {"file": "community.log", "desc": "CommunityHub"},
        "outerdesk": {"file": "outerdesk.log", "desc": "OuterdeskHub"},
        "legacy": {"file": "legacy.log", "desc": "LegacyHub"},
        "radio": {"file": "radio.log", "desc": "Void Radio"},
        "voidcast": {"file": "voidcast.log", "desc": "VoidCast IPTV"},
        "bgm": {"file": "bgm.log", "desc": "BGM Normalizer"},
        "chd": {"file": "chd.log", "desc": "Disc Crusher (CHD)"},
        "doppel": {"file": "doppel.log", "desc": "Doppel-Defender"},
        "rss": {"file": "rss.log", "desc": "RSS Reader"},
        "weather": {"file": "weather.log", "desc": "Meteo"},
        "filemanager": {"file": "filemanager.log", "desc": "File Manager"},
        "ftp": {"file": "ftp.log", "desc": "FTP Client"},
        "sync": {"file": "sync.log", "desc": "Syncthing"},
        "tailscale": {"file": "tailscale.log", "desc": "Tailscale"},
        "rtshell": {"file": "rtshell.log", "desc": "Rt:Shell"},
        "python": {"file": "python.log", "desc": "Python REPL"},
        "editor": {"file": "editor.log", "desc": "Text Editor"},
        "options": {"file": "options.log", "desc": "Opzioni"},
        "settings": {"file": "settings.log", "desc": "Impostazioni"},
        "map": {"file": "map.log", "desc": "Button Mapping"},
        "netprobe": {"file": "netprobe.log", "desc": "Network Probe"},
        "pcup": {"file": "pcup.log", "desc": "PC Uplink"},
        "basestation": {"file": "basestation.log", "desc": "BaseStation"},
        "devicecheck": {"file": "devicecheck.log", "desc": "Device Check"},
        "backup": {"file": "backup.log", "desc": "Backup"},
        "evinput": {"file": "evinput.log", "desc": "Eventi input"},
    }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._loggers = {}
        self._register_all()
        self._load_config()

    def _register_all(self):
        for name, info in self.MODULE_LOGS.items():
            logger = Logger(
                name=name,
                filename=info["file"],
                level=LogLevel.INFO,
                max_size_mb=5,
                enabled=True,
            )
            self._loggers[name] = logger
            logger.start()

    def get_logger(self, name):
        if name not in self._loggers:
            self._loggers[name] = Logger(name=name, filename="%s.log" % name, enabled=True)
            self._loggers[name].start()
        return self._loggers[name]

    def get_all_loggers(self):
        return dict(self._loggers)

    def set_enabled(self, name, enabled):
        if name in self._loggers and not self.is_fundamental(name):
            self._loggers[name].set_enabled(enabled)
            self._save_config()

    def set_level(self, name, level):
        if name in self._loggers:
            self._loggers[name].set_level(level)

    def set_max_size(self, name, mb):
        if name in self._loggers:
            self._loggers[name].max_size_bytes = mb * 1024 * 1024
            self._save_config()

    def get_max_size(self, name):
        if name in self._loggers:
            return self._loggers[name].max_size_bytes // (1024 * 1024)
        return 5

    def is_fundamental(self, name):
        info = self.MODULE_LOGS.get(name, {})
        return info.get("fundamental", False)

    def get_description(self, name):
        info = self.MODULE_LOGS.get(name, {})
        return info.get("desc", "")

    def _load_config(self):
        if not os.path.exists(LOGGER_CONFIG_FILE):
            self._save_config()
            return
        try:
            with open(LOGGER_CONFIG_FILE, "r") as f:
                config = json.load(f)
            for name, enabled in config.get("enabled", {}).items():
                if name in self._loggers and not self.is_fundamental(name):
                    self._loggers[name].enabled = enabled
        except Exception:
            pass

    def _save_config(self):
        config = {"enabled": {}}
        for name, logger in self._loggers.items():
            if not self.is_fundamental(name):
                config["enabled"][name] = logger.enabled
        try:
            with open(LOGGER_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except OSError:
            pass

    def log(self, name, level, msg):
        logger = self.get_logger(name)
        logger.log(level, msg)

    def shutdown(self):
        for logger in self._loggers.values():
            logger.stop()


class LogArchiver:
    @staticmethod
    def create_archive(logger_names=None, include_config=True):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(ARCHIVES_DIR, exist_ok=True)
        zip_path = os.path.join(ARCHIVES_DIR, "logs_%s.zip" % timestamp)
        manager = LoggerManager.get_instance()
        all_loggers = manager.get_all_loggers()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, logger in all_loggers.items():
                if logger_names is not None and name not in logger_names:
                    continue
                if not logger.enabled:
                    continue
                log_file = os.path.join(LOGS_DIR, logger.filename)
                if os.path.exists(log_file):
                    zf.write(log_file, arcname=logger.filename)
            registry = LogRegistry.get_instance()
            entries = registry.get_entries(limit=500)
            if entries:
                zf.writestr("registry.json", json.dumps(entries, indent=2))
            if include_config:
                if os.path.exists(LOGGER_CONFIG_FILE):
                    zf.write(LOGGER_CONFIG_FILE, arcname="logger_config.json")
        return zip_path


class LogSender:
    """Invia log a destinazioni remote (Syslog, Webhook, Basestation)."""

    @staticmethod
    def syslog(message, host='127.0.0.1', port=514, facility=1, severity=6):
        """Invia via UDP a un server Syslog."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            pri = (facility << 3) | severity
            msg = "<%d>VoidDesk: %s" % (pri, message)
            sock.sendto(msg.encode('utf-8'), (host, port))
            sock.close()
            return True
        except Exception:
            return False

    @staticmethod
    def webhook(message, url, headers=None, timeout=5):
        """Invia via HTTP POST (JSON) a un webhook."""
        try:
            data = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "source": "voiddesk",
                "message": message
            }).encode('utf-8')
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            req = urllib.request.Request(url, data=data, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode() in (200, 201, 202)
        except Exception:
            return False

    @staticmethod
    def basestation(message, port=8765):
        """Invia alla Basestation interna su /api/log."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            url = "http://%s:%d/api/log" % (ip, port)
            data = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "source": "voiddesk",
                "message": message
            }).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.getcode() in (200, 201, 202)
        except Exception:
            return False
