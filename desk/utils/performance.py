# -*- coding: utf-8 -*-
"""
Strumenti per performance: dirty rect rendering, monitoraggio RAM.
"""

import os
import time
import pygame


class DirtyRectRenderer:
    def __init__(self):
        self.dirty_rects = []
        self._last_full_refresh = 0.0
        self._full_refresh_interval = 5.0
        self.enabled = True

    def mark_dirty(self, rect):
        if not self.enabled:
            return
        self.dirty_rects.append(rect)

    def mark_all_dirty(self):
        self.dirty_rects = [pygame.Rect(0, 0, W, H)]

    def render(self, surface, draw_func, force_full=False):
        if not self.enabled or force_full:
            draw_func(surface, None)
            pygame.display.flip()
            self._last_full_refresh = time.time()
            self.dirty_rects = []
            return

        now = time.time()
        if now - self._last_full_refresh > self._full_refresh_interval:
            self.mark_all_dirty()
            self._last_full_refresh = now

        if self.dirty_rects:
            for rect in self.dirty_rects:
                draw_func(surface, rect)
            pygame.display.update(self.dirty_rects)
            self.dirty_rects = []
        else:
            pass


def get_free_memory_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return -1


def is_low_memory(threshold_mb=150):
    free = get_free_memory_mb()
    return free != -1 and free < threshold_mb


def memory_guard(func):
    def wrapper(*args, **kwargs):
        if is_low_memory(100):
            return None
        return func(*args, **kwargs)
    return wrapper
