# -*- coding: utf-8 -*-
"""fbtext - testo direttamente su /dev/fb0, puro python3, zero dipendenze.
Gestisce 16bpp (RGB565) e 32bpp. Non solleva mai eccezioni verso il
chiamante: se il framebuffer non c'e', le chiamate sono no-op."""
import base64
import fcntl
import os
import struct
import zlib

_FBIOGET_VSCREENINFO = 0x4600
_FBIOGET_FSCREENINFO = 0x4602


def _probe(f):
    try:
        v = bytearray(160)
        fcntl.ioctl(f, _FBIOGET_VSCREENINFO, v)
        xres, yres, _xv, _yv, _xo, _yo, bpp, _g = struct.unpack_from("8I", v, 0)
        x = bytearray(80)
        fcntl.ioctl(f, _FBIOGET_FSCREENINFO, x)
        stride = struct.unpack_from("I", x, 48)[0]
        if xres and yres and bpp in (16, 32) and stride:
            return xres, yres, bpp, stride
    except Exception:
        pass
    return None

_ATLAS = "eNqlVr9r21AQvvMZ0cGEQJZAQ/AQOgsHQoYQMpf+AaFDMTRkyhAyaTDBBOPJhEydSugQOnXoVDp0MKkRGURmT8FkyOyhFA1C6d2TZEvvR5zQ+7AtS6e7e3ff3XsALxVfQ3FPl5sZFsl3vMALSGnMuu/gEQ/gAN5oOk1GDN9wAzZgh68m+AWb+BUT9aRZ0lyHFdjkzyW2YRVCbFKz1qQh6l4D9tVQWIOt2kf6TdcYYofc631K9qDNUYjWMnsVLKt/Tb6/V9Ir3y8wf09f8RUGHOcVVlfoijCllJ4Tq/7eqlNDvL+UGbp0sQtDlZ927m1VZd1jVH1F0MM+4wdDfnsYWfwHcFTKXYHEqG8HQjhD9o5Dfn4M28pvatXLtAKOs6veCPmuLhPGFISjEb8RcraHINAlgbpCB0a5tS5eW+zFMGAtD1K4VasVRBgbeqmKTVBkMMuhmZcoszG7stuTPJf8qfhGzjqXa/oUs0w9B69owpxeYgTcw0BuNgmby792qXG/xzDEIa90nf/ZODyCggVFlLZ1cD3Qo3vapBV6rbBCLXqgOs+HKZZXKl2xr3gQ8Tsp59EjMmJM8yyHmF15JN+p4XcKnzHrhgINvjM19E6Zc32sIuS7Bv+wnjNwflW39EeCjXz+za8E1rxgFlmY+x0wb3S9eVRpJUbTrw8mzPhiGBo4tPRRn0J84CdbsMs4lN5U2db1GlYkZNo7p1t6S+/phOvfoloOXe8cBZf4Sc2rB0aIoWW95X6b9Z2l3xKefj2sk3wnMK/cc+3x7HLwJZxde2TmRdVXVXeHuSidcsbrSAy/j2Srm9lHemzZnDHXS1RwSfrohjsq4CntW/RENrkSJ3SKH/BWYWDk2SOxNGYrPtsJVG/20exL8TtQGQueXEdKPDOwmLrZrrUE+iw65n3bheNqfKqzG8qS+Gurk4FUrYvl6radCLSJm+2YHsJ/yyt1KnmJxDBipsTcAdmM+6VFUcwy2d3Ocxacc91Sh70prPEUyhjPJzJj/hU7aYxRhVcxuuKT6ns8iySKgbEPTrCYO4v4nNsz/Mq5ZjR7XnTrH8W7XgnmPimyo3nVzyVS7+x0YmOCb0w1YfQRW+3wt0TQ0Hi6bmWoL3uwVe5wC1vYojnseovWa59akfO8wXyBKl8846TorAd2De9j3KZVKMMV30DlMVZnQNt5KHs7xbItv3IyKEuvkpMIfzr0vPycKxMwm0h2yaZgi7bwL96xvcihJ7ndV3O0mIAOv1RM3nE+d+0ntiSfgfJsTZ0V7H2UYa3C6XaJXf4CFFK1MME2VO3bZJdPiPdaXP8AZEyqnw=="
CW, CH = 10, 20
_FIRST, _LAST = 32, 126


class FB(object):
    def __init__(self, dev="/dev/fb0", sysfs="/sys/class/graphics/fb0",
                 width=None, height=None, bpp=None, stride=None):
        self.ok = False
        try:
            if width is None:
                geo = None
                try:
                    with open(dev, "rb") as fd:
                        geo = _probe(fd)
                except Exception:
                    geo = None
                if geo:
                    width, height, bpp, stride = geo
            if width is None:
                vs = open(os.path.join(sysfs, "virtual_size")).read().strip()
                width, height = [int(v) for v in vs.split(",")]
            if bpp is None:
                bpp = int(open(os.path.join(sysfs, "bits_per_pixel")).read())
            if stride is None:
                try:
                    stride = int(open(os.path.join(sysfs, "stride")).read())
                except Exception:
                    stride = width * bpp // 8
            self.w, self.h, self.bpp, self.stride = width, height, bpp, stride
            self.dev = dev
            self.font = zlib.decompress(base64.b64decode(_ATLAS))
            self.cols = max(1, self.w // CW)
            self.rows = max(1, self.h // CH)
            self.buf = bytearray(self.stride * self.h)
            self.ok = True
        except Exception:
            self.ok = False

    def _px(self, x, y, rgb):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        r, g, b = rgb
        if self.bpp == 16:
            v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            o = y * self.stride + x * 2
            self.buf[o] = v & 0xFF
            self.buf[o + 1] = (v >> 8) & 0xFF
        else:
            o = y * self.stride + x * 4
            self.buf[o] = b
            self.buf[o + 1] = g
            self.buf[o + 2] = r
            self.buf[o + 3] = 0

    def clear(self, rgb=(16, 16, 24)):
        if not self.ok:
            return
        row = bytearray(self.stride)
        for x in range(self.w):
            self._px(x, 0, rgb)
        row[:] = self.buf[:self.stride]
        for y in range(1, self.h):
            self.buf[y * self.stride:(y + 1) * self.stride] = row

    def char(self, col, row, ch, fg, bg=None):
        c = ord(ch)
        if c < _FIRST or c > _LAST:
            c = ord("?")
        base = (c - _FIRST) * CH * 2
        x0, y0 = col * CW, row * CH
        for dy in range(CH):
            rowbits = self.font[base + dy * 2] | (self.font[base + dy * 2 + 1] << 8)
            for dx in range(CW):
                if rowbits & (1 << dx):
                    self._px(x0 + dx, y0 + dy, fg)
                elif bg is not None:
                    self._px(x0 + dx, y0 + dy, bg)

    def text(self, col, row, s, fg=(230, 230, 230), bg=None):
        if not self.ok:
            return
        for i, ch in enumerate(s[: self.cols - col]):
            self.char(col + i, row, ch, fg, bg)

    def flush(self):
        if not self.ok:
            return
        try:
            with open(self.dev, "r+b") as f:
                f.write(self.buf)
        except Exception:
            pass


class Screen(object):
    """Console a scorrimento: ogni print() finisce anche sullo schermo."""

    def __init__(self, title="", **kw):
        self.fb = FB(**kw)
        self.title = title
        self.lines = []

    def log(self, msg):
        for chunk in str(msg).splitlines() or [""]:
            self.lines.append(chunk)
        self.render()

    def render(self):
        fb = self.fb
        if not fb.ok:
            return
        fb.clear()
        r = 0
        if self.title:
            fb.text(1, 0, self.title[: fb.cols - 2], (255, 200, 60))
            r = 2
        avail = fb.rows - r - 1
        for ln in self.lines[-avail:]:
            low = ln.lower()
            if "fatal" in low or "fail" in low or "errore" in low:
                col = (255, 90, 90)
            elif "ok" in low or "completato" in low or "fatto" in low:
                col = (120, 230, 120)
            else:
                col = (225, 225, 225)
            fb.text(1, r, ln[: fb.cols - 2], col)
            r += 1
        fb.flush()
