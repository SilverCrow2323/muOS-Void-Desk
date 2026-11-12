from desk.muos_video import init_muos_surface, poll_muos_events


class _FakeSurface:
    def __init__(self, size):
        self.size = size


class _ForbiddenDisplay:
    def init(self):
        raise AssertionError("SDL display must not be initialized on muOS")

    def set_mode(self, size):
        raise AssertionError("SDL set_mode must not be used on muOS")


class _FakeEvents:
    def __init__(self, error=None):
        self.error = error
        self.called = False

    def get(self):
        self.called = True
        if self.error:
            raise self.error
        return ("event",)


class _FakePygame:
    error = RuntimeError

    def __init__(self, event_error=None):
        self.created = None
        self.display = _ForbiddenDisplay()
        self.event = _FakeEvents(event_error)

    def Surface(self, size):
        self.created = _FakeSurface(size)
        return self.created


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


def test_direct_framebuffer_does_not_poll_sdl_event_queue():
    pygame = _FakePygame()
    assert poll_muos_events(pygame, direct_fb=True) == ()
    assert pygame.event.called is False


def test_legacy_event_poll_handles_uninitialized_video_queue():
    pygame = _FakePygame(event_error=RuntimeError("video system not initialized"))
    assert poll_muos_events(pygame, direct_fb=False) == ()
    assert pygame.event.called is True


def test_legacy_event_poll_returns_events_when_available():
    pygame = _FakePygame()
    assert poll_muos_events(pygame, direct_fb=False) == ("event",)
    assert pygame.event.called is True
