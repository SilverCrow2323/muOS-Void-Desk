# -*- coding: utf-8 -*-
# VOIDCAST // core.fbdisplay — uscita video su /dev/fb0 senza driver SDL.
#
# Per pannelli dove SDL non apre il video (niente /dev/dri, driver custom):
# la UI renderizza normalmente su una Surface (SDL_VIDEODRIVER=dummy) e ogni
# pygame.display.flip() copia il frame sul framebuffer. La conversione di
# formato (RGB565 o XRGB8888) la fa pygame in C con una blit: veloce.
#
# Attivazione: VOIDCAST_FB=1 nell'ambiente; main.init_display() chiama
# attach(surface) dopo set_mode.

import fcntl
import mmap
import os
import struct

import pygame

_FBIOGET_VSCREENINFO = 0x4600
_FBIOPUT_VSCREENINFO = 0x4601
_FBIOGET_FSCREENINFO = 0x4602
_FBIOBLANK = 0x4611


def _reset_pan(f):
    """Azzera xoffset/yoffset (doppio buffer) e sblanka il pannello,
    cosi' quello che scriviamo all'inizio del buffer e' cio' che si vede."""
    try:
        v = bytearray(160)
        fcntl.ioctl(f, _FBIOGET_VSCREENINFO, v)
        struct.pack_into("2I", v, 16, 0, 0)   # xoffset, yoffset = 0
        fcntl.ioctl(f, _FBIOPUT_VSCREENINFO, bytes(v))
    except Exception:
        pass
    try:
        fcntl.ioctl(f, _FBIOBLANK, 0)         # unblank
    except Exception:
        pass


def _probe(f):
    """Geometria reale via ioctl: (w, h, bpp, stride, masks) o None."""
    try:
        v = bytearray(160)
        fcntl.ioctl(f, _FBIOGET_VSCREENINFO, v)
        xres, yres, _xv, _yv, _xo, _yo, bpp, _g = struct.unpack_from("8I", v, 0)
        ro, rl, _m1, go, gl, _m2, bo, bl, _m3 = struct.unpack_from("9I", v, 32)
        x = bytearray(80)
        fcntl.ioctl(f, _FBIOGET_FSCREENINFO, x)
        stride = struct.unpack_from("I", x, 48)[0]
        masks = (((1 << rl) - 1) << ro, ((1 << gl) - 1) << go,
                 ((1 << bl) - 1) << bo, 0)
        if xres and yres and bpp in (16, 32) and stride:
            return xres, yres, bpp, stride, masks
    except Exception:
        pass
    return None

_state = {"fb": None}


class _FBOut(object):
    def __init__(self, dev=None, sysfs=None):
        dev = dev or os.environ.get("VOIDCAST_FB_DEV", "/dev/fb0")
        sysfs = sysfs or os.environ.get("VOIDCAST_FB_SYSFS",
                                        "/sys/class/graphics/fb0")
        self.ok = False
        try:
            self.f = open(dev, "r+b")
            _reset_pan(self.f)
            geo = _probe(self.f)
            if geo:
                self.w, self.h, self.bpp, self.stride, masks = geo
            else:  # fallback sysfs (attenzione: virtual_size puo' includere
                   # il doppio buffer, l'ioctl e' la fonte affidabile)
                vs = open(os.path.join(sysfs, "virtual_size")).read().strip()
                self.w, self.h = [int(v) for v in vs.split(",")]
                self.bpp = int(open(os.path.join(sysfs,
                                                 "bits_per_pixel")).read())
                try:
                    self.stride = int(open(os.path.join(sysfs,
                                                        "stride")).read())
                except Exception:
                    self.stride = self.w * self.bpp // 8
                masks = ((0xF800, 0x07E0, 0x001F, 0) if self.bpp == 16
                         else (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
            self.mm = mmap.mmap(self.f.fileno(), self.stride * self.h)
            self.frame = pygame.Surface((self.w, self.h), 0, self.bpp, masks)
            self.frame.fill((0, 0, 0))
            self.pitch = self.frame.get_pitch()
            self.masks = masks
            self._fit = None
            self.ok = True
        except Exception:
            self.close()

    def close(self):
        try:
            if getattr(self, "mm", None):
                self.mm.close()
            if getattr(self, "f", None):
                self.f.close()
        except Exception:
            pass
        self.ok = False

    def present(self, src):
        if not self.ok:
            return
        try:
            sw, sh = src.get_size()
            if (sw, sh) != (self.w, self.h):
                if self._fit is None:
                    k = min(self.w / float(sw), self.h / float(sh))
                    dw, dh = int(sw * k), int(sh * k)
                    self._fit = (dw, dh, (self.w - dw) // 2,
                                 (self.h - dh) // 2,
                                 pygame.Surface((dw, dh)))
                dw, dh, ox, oy, tmp = self._fit
                pygame.transform.scale(src, (dw, dh), tmp)
                self.frame.blit(tmp, (ox, oy))
            else:
                self.frame.blit(src, (0, 0))
            buf = self.frame.get_buffer().raw
            if self.pitch == self.stride:
                self.mm[: len(buf)] = buf
            else:
                bpr = self.w * (self.bpp // 8)
                for y in range(self.h):
                    o = y * self.stride
                    p = y * self.pitch
                    self.mm[o: o + bpr] = buf[p: p + bpr]
        except Exception:
            pass


def grab(dev=None, sysfs=None):
    """Legge il framebuffer COSI' COM'E' e lo restituisce come Surface.
    Usato dal pannello LIVE per mostrare lo sfondo XFCE congelato."""
    fb = _FBOut(dev, sysfs)
    if not fb.ok:
        return None
    try:
        raw = fb.mm[:fb.stride * fb.h]
        surf = pygame.Surface((fb.w, fb.h), 0, fb.bpp, fb.masks)
        pitch = surf.get_pitch()
        buf = surf.get_buffer()
        if pitch == fb.stride:
            buf.write(bytes(raw))
        else:
            n = min(pitch, fb.stride)
            for y in range(fb.h):
                buf.write(bytes(raw[y * fb.stride:y * fb.stride + n]),
                          y * pitch)
        del buf
        try:
            return surf.convert()
        except pygame.error:
            return surf
    except Exception:
        return None
    finally:
        fb.close()


def info():
    fb = _state.get("fb")
    if fb is None or not fb.ok:
        return "fb: non attivo"
    return ("fb: %dx%d %dbpp stride=%d masks=%s"
            % (fb.w, fb.h, fb.bpp, fb.stride,
               ",".join(hex(m) for m in fb.masks)))


def attach(surface):
    """Sostituisce pygame.display.flip con la copia su framebuffer.
    Ritorna True se il framebuffer e' utilizzabile."""
    old = _state.get("fb")
    if old is not None:
        old.close()
    fb = _FBOut()
    if not fb.ok:
        return False
    _state["fb"] = fb

    def _flip():
        fb.present(surface)

    pygame.display.flip = _flip
    pygame.display.update = lambda *a, **k: _flip()
    _flip()
    return True


def detach():
    fb = _state.get("fb")
    if fb is not None:
        fb.close()
        _state["fb"] = None
