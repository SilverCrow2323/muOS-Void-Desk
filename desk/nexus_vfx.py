import pygame
import math
import os

class PlanetVFX:
    def __init__(self, name, radius, quality="high"):
        self.name = name.upper().strip()
        self.radius = int(radius)
        self.angle = 0.0
        self.quality = quality
        
        # Loader dinamico PNG delle dimensioni esatte
        self.image = None
        clean_name = self.name.replace('THE ', '').lower()
        path = f"assets/nodes/{clean_name}.png"
        
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            self.image = pygame.transform.smoothscale(img, (self.radius * 2, self.radius * 2))
        else:
            # Fallback geometrico in caso di file mancante
            self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (60, 255, 110, 40), (self.radius, self.radius), self.radius)

        # Maschera sferica 3D (illusione volumetrica con gradiente alpha)
        self.shadow = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        for i in range(self.radius, 0, -1):
            alpha = int(255 * (i / self.radius) ** 2.2)
            pygame.draw.circle(self.shadow, (7, 8, 11, alpha), (self.radius - i // 5, self.radius + i // 5), i)

        # Particelle anello diagonale per THE FORGE
        # Limitate per dispositivi con poca RAM
        max_particles = 60 if quality == "high" else (20 if quality == "medium" else 0)
        self.particles = []
        if "FORGE" in self.name:
            for i in range(max_particles):
                self.particles.append({
                    "angle": i * (360 / max_particles) if max_particles else 0,
                    "speed": 1.5 + (i % 4) * 0.4,
                    "dist": self.radius + 18 + (i % 6)
                })

    def update(self):
        self.angle = (self.angle + 0.5) % 360
        for p in self.particles:
            p["angle"] = (p["angle"] + p["speed"]) % 360

    def draw(self, surface, x, y):
        ix, iy = int(x), int(y)
        
        # 1. Texture sferica in rotazione
        if self.image:
            rotated = pygame.transform.rotate(self.image, self.angle)
            rect = rotated.get_rect(center=(ix, iy))
            surface.blit(rotated, rect.topleft)
        
        # 2. Ombra sferica tridimensionale
        surface.blit(self.shadow, (ix - self.radius, iy - self.radius))

        # 3. Bordo sottilissimo (RIGOROSAMENTE 1px, zero sbavature)
        pygame.draw.circle(surface, (60, 255, 110), (ix, iy), self.radius, 1)

        # 4. Anello di polvere in diagonale (THE FORGE)
        if "FORGE" in self.name:
            tilt = 0.32  
            tilt_angle = math.radians(28)  
            for p in self.particles:
                rad = math.radians(p["angle"])
                px_b = math.cos(rad) * p["dist"]
                py_b = math.sin(rad) * p["dist"] * tilt
                
                px = px_b * math.cos(tilt_angle) - py_b * math.sin(tilt_angle)
                py = px_b * math.sin(tilt_angle) + py_b * math.cos(tilt_angle)
                
                pygame.draw.circle(surface, (160, 255, 160), (int(ix + px), int(iy + py)), 1)
