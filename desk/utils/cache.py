# -*- coding: utf-8 -*-
"""
Sistema di cache LRU per texture e font.
Ottimizzato per 1GB RAM: massimo 50 elementi, dimensione max 64x64.
"""

import collections
import pygame


class TextureCache:
    def __init__(self, max_size=50, max_texture_size=64):
        self.cache = collections.OrderedDict()
        self.max_size = max_size
        self.max_texture_size = max_texture_size
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, key, texture):
        if isinstance(texture, pygame.Surface):
            w, h = texture.get_size()
            if w > self.max_texture_size or h > self.max_texture_size:
                scale = min(self.max_texture_size / w, self.max_texture_size / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                texture = pygame.transform.smoothscale(texture, (new_w, new_h))
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[key] = texture

    def clear(self):
        for tex in self.cache.values():
            if isinstance(tex, pygame.Surface):
                tex.fill((0, 0, 0, 0))
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_or_create(self, key, creator_func):
        tex = self.get(key)
        if tex is not None:
            return tex
        tex = creator_func()
        if tex is not None:
            self.set(key, tex)
        return tex

    def stats(self):
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


_texture_cache = None


def get_texture_cache():
    global _texture_cache
    if _texture_cache is None:
        _texture_cache = TextureCache()
    return _texture_cache
