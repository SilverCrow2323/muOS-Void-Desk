from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_muos_launcher_defaults_to_pygame_and_recovers_to_pygame():
    launcher = (ROOT / "mux_launch.sh").read_text(encoding="utf-8")
    assert ".get('engine','py')" in launcher
    assert "print('py')" in launcher
    assert '[ -z "$ENGINE" ] && ENGINE="py"' in launcher
    assert "revert_engine_to_py()" in launcher
    assert "revert_engine_to_love" not in launcher
    assert "falling back to LOVE engine" not in launcher
    assert "Pygame frontend failed" in launcher


def test_muos_launcher_refuses_incomplete_love_runtime():
    launcher = (ROOT / "mux_launch.sh").read_text(encoding="utf-8")
    assert '[ ! -f "$APP_DIR/lib/liblove-11.5.so" ]' in launcher
    assert "LÖVE runtime incomplete; using supported Pygame frontend" in launcher


def test_pygame_is_default_and_offline_archives_are_required():
    builder = (ROOT / "tools" / "build_muxapp.py").read_text(encoding="utf-8")
    settings = (ROOT / "desk" / "hubs" / "settings.py").read_text(encoding="utf-8")
    assert '"engine": "py"' in (ROOT / "voiddesk.py").read_text(encoding="utf-8")
    assert 'app.cfg.get("engine", "py")' in settings
    for archive in (
        "pygame.tar.gz",
        "pygame.libs.tar.gz",
        "pygame-2.6.1.data.tar.gz",
        "pygame-2.6.1.dist-info.tar.gz",
    ):
        assert archive in builder
