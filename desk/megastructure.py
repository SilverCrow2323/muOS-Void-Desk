import pygame
import math
import random

class Megastructure2:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.grid_offset = 0
        self.particles = []
        self._frame_count = 0
        self._cache = {}
        self._init_particles()

    def _init_particles(self):
        for _ in range(60):
            self.particles.append({
                "x": random.randint(0, self.w),
                "y": random.randint(0, self.h),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.2, 0.2),
                "size": random.randint(1, 3),
                "alpha": random.randint(30, 80),
                "phase": random.uniform(0, 6.28),
            })

    def draw(self, surf, accent, t, speed=1.0):
        self._frame_count += 1
        if self._frame_count % 2 != 0:
            for p in self.particles:
                p["x"] += p["vx"] * speed + math.sin(t + p["phase"]) * 0.2
                p["y"] += p["vy"] * speed + math.cos(t * 0.7 + p["phase"]) * 0.2
                if p["x"] < 0 or p["x"] > self.w:
                    p["vx"] = -p["vx"]
                if p["y"] < 0 or p["y"] > self.h:
                    p["vy"] = -p["vy"]

        self.grid_offset = (self.grid_offset + speed * 0.5) % 40
        offset = int(self.grid_offset)
        for gx in range(-offset, self.w + 40, 40):
            alpha = 40 + 20 * math.sin(t * 0.5 + gx * 0.01)
            c = (*accent, int(alpha))
            pygame.draw.line(surf, c, (gx, 0), (gx, self.h), 1)
        for gy in range(-offset, self.h + 40, 40):
            alpha = 40 + 20 * math.sin(t * 0.4 + gy * 0.01)
            c = (*accent, int(alpha))
            pygame.draw.line(surf, c, (0, gy), (self.w, gy), 1)

        aura = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        cx, cy = self.w // 2, self.h // 2
        for r in range(0, 220, 8):
            a = int(12 * (1 - r / 220) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (*accent, a), (cx, cy), r)
        surf.blit(aura, (0, 0))

        for p in self.particles:
            a = int(p["alpha"] * (0.6 + 0.4 * math.sin(t * 2 + p["phase"])))
            pygame.draw.circle(surf, (*accent, a), (int(p["x"]), int(p["y"])), p["size"])
