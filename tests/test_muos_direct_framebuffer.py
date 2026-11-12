from desk.muos_video import init_muos_surface


class _FakeSurface:
    def __init__(self, size):
        self.size = size


class _FakePygame:
    def __init__(self):
        self.created = None
        self.display = _ForbiddenDisplay()

    def Surface(self, size):
        self.created = _FakeSurface(size)
        return self.created


class _ForbiddenDisplay:
    def init(self):
        raise AssertionError("SDL display must not be initialized on muOS")

    def set_mode(self, size):
        raise AssertionError("SDL set_mode must not be used on muOS")


class _FakeFramebuffer:
    def __init__(self, available=True):
        self.available = available
        self.attached = None

    def attach(self, surface):
        self.attached = surface
        return self.available

    def info(self):
        return "fb: test"


def test_muos_surface_uses_direct_framebuffer_without_sdl_display():
    pygame = _FakePygame()
    fb = _FakeFramebuffer()

    surface = init_muos_surface(pygame, fb, (640, 480))

    assert surface is pygame.created
    assert surface.size == (640, 480)
    assert fb.attached is surface


def test_muos_surface_fails_loudly_when_framebuffer_is_unavailable():
    pygame = _FakePygame()
    fb = _FakeFramebuffer(available=False)

    try:
        init_muos_surface(pygame, fb, (640, 480))
    except RuntimeError as exc:
        assert "muOS framebuffer initialization failed" in str(exc)
        assert "fb: test" in str(exc)
    else:
        raise AssertionError("expected framebuffer initialization failure")
