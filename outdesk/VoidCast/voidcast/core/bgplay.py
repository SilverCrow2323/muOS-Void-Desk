# outdesk/VoidCast/voidcast/core/bgplay.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.bgplay — audio-only background playback (mpv --no-video)
import json
import os
import socket
import subprocess

from . import config as C

class BgPlayer(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.proc = None
        self.sock = None
        self.channel = None
        self.paused = False
        self.sock_path = "/tmp/voidcast-bg.sock"

    @property
    def active(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, channel):
        if self.active:
            self.stop()
        try:
            os.remove(self.sock_path)
        except OSError:
            pass
        ua = self.cfg.get("user_agent", "")
        cmd = ["mpv", channel.url,
               "--no-config", "--no-video", "--ao=auto",
               "--cache=yes", "--cache-secs=5",
               "--user-agent=%s" % ua,
               "--network-timeout=12",
               "--input-ipc-server=%s" % self.sock_path]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.channel = channel
            self.paused = False
            return True
        except OSError:
            self.proc = None
            return False

    def _ipc(self, *args):
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(0.3)
                self.sock.connect(self.sock_path)
            except OSError:
                self.sock = None
                return False
        try:
            self.sock.sendall((json.dumps({"command": list(args)}) + "\n")
                              .encode("utf-8"))
            return True
        except OSError:
            self.sock = None
            return False

    def toggle_pause(self):
        self.paused = not self.paused
        return self._ipc("set", "pause", self.paused)

    def stop(self):
        if self.proc:
            self._ipc("quit")
            try:
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()
        self.proc = None
        self.sock = None
        self.channel = None
        self.paused = False
