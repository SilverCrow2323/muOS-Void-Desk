# outdesk/VoidCast/voidcast/ui/anim.py
# -*- coding: utf-8 -*-
# VOIDCAST // ui.anim — animations intensity governor.
import math
import time

class Anim:
    intensity = 2  # 0..3

    @classmethod
    def set_intensity(cls, v):
        try:
            cls.intensity = max(0, min(3, int(v)))
        except Exception:
            cls.intensity = 2

    @classmethod
    def enabled(cls):
        return cls.intensity > 0

    @classmethod
    def pulse(cls, period=1.5, lo=0.0, hi=1.0):
        if not cls.enabled():
            return (lo + hi) / 2
        s = (math.sin(time.time() * 2 * math.pi / period) + 1) / 2
        return lo + (hi - lo) * s

    @classmethod
    def scan(cls, length, speed=90.0):
        if not cls.enabled():
            return -1
        return (time.time() * speed) % (length + 120) - 60

    @classmethod
    def now(cls):
        return time.time()
