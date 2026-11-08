# outdesk/VoidCast/voidcast/core/logos.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.logos — loghi canale (tvg-logo) con download in background.
#
# get(url, h) non blocca mai: ritorna subito la Surface se in cache,
# altrimenti accoda il download e ritorna None (il frame dopo ci sara').
# Cache su disco in data/cache/logos, fallimenti marcati per non ritentare.

import hashlib
import os
import queue
import threading

import pygame

from . import config as C
from . import net

LOGO_DIR = os.path.join(C.CACHE_DIR, "logos")


class Logos(object):
    def __init__(self, user_agent=""):
        self.ua = user_agent
        self.mem = {}          # (url, h) -> Surface | None
        self.pend = set()
        self.q = queue.Queue()
        self.thread = None
        try:
            os.makedirs(LOGO_DIR, exist_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    def _path(self, url):
        hid = hashlib.sha1(url.encode("utf-8", "replace")).hexdigest()[:20]
        return os.path.join(LOGO_DIR, hid + ".img")

    def _worker(self):
        while True:
            url = self.q.get()
            path = self._path(url)
            try:
                data = net.fetch_bytes(url, self.ua, timeout=10)
                if not data:
                    raise OSError("vuoto")
                tmp = path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, path)
            except Exception:
                try:
                    open(path + ".fail", "w").close()
                except OSError:
                    pass
            finally:
                self.pend.discard(url)

    # ------------------------------------------------------------------
    def get(self, url, h):
        """Surface del logo scalata ad altezza h, oppure None (per ora)."""
        if not url or h <= 0:
            return None
        key = (url, h)
        if key in self.mem:
            return self.mem[key]
        path = self._path(url)
        if os.path.exists(path):
            surf = None
            try:
                img = pygame.image.load(path).convert_alpha()
                w0, h0 = img.get_size()
                if w0 > 0 and h0 > 0:
                    w = max(1, int(w0 * h / float(h0)))
                    w = min(w, int(h * 1.9))
                    surf = pygame.transform.smoothscale(img, (w, h))
            except Exception:
                surf = None
            self.mem[key] = surf
            return surf
        if os.path.exists(path + ".fail"):
            self.mem[key] = None
            return None
        if url not in self.pend:
            self.pend.add(url)
            self.q.put(url)
            if self.thread is None:
                self.thread = threading.Thread(target=self._worker,
                                               daemon=True)
                self.thread.start()
        return None
