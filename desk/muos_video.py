"""Direct software-surface output for muOS framebuffer-only devices."""


def init_muos_surface(pygame, fbdisplay, size):
    """Create an off-screen surface and attach it to the Linux framebuffer.

    This path intentionally avoids pygame.display.init() and set_mode(): the
    SDL video driver compiled into some muOS H700 builds does not expose a
    usable dummy/fbcon backend, while fbdisplay writes the resulting pixels
    directly to /dev/fb0.
    """
    surface = pygame.Surface(size)
    if not fbdisplay.attach(surface):
        detail = fbdisplay.info() if hasattr(fbdisplay, "info") else "unknown"
        raise RuntimeError(
            "muOS framebuffer initialization failed (%s); "
            "check /dev/fb0 access and framebuffer geometry" % detail
        )
    return surface
