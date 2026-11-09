import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "outdesk" / "VoidCast" / "voidcast" / "core" / "evinput.py"


def load_evinput():
    spec = importlib.util.spec_from_file_location("voidcast_evinput_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evinput_is_used_when_sdl_has_no_joystick(monkeypatch):
    monkeypatch.setenv("VOIDCAST_FB", "1")
    evinput = load_evinput()
    calls = []
    monkeypatch.setattr(evinput, "start", lambda: calls.append("start") or True)
    monkeypatch.setattr(evinput, "stop", lambda: calls.append("stop"))

    assert evinput.sync_with_joystick(False) is True
    assert calls == ["start"]


def test_evinput_is_disabled_when_sdl_joystick_is_available(monkeypatch):
    monkeypatch.setenv("VOIDCAST_FB", "1")
    evinput = load_evinput()
    calls = []
    monkeypatch.setattr(evinput, "start", lambda: calls.append("start") or True)
    monkeypatch.setattr(evinput, "stop", lambda: calls.append("stop"))

    assert evinput.sync_with_joystick(True) is False
    assert calls == ["stop"]

def test_evinput_is_not_used_on_desktop_without_framebuffer(monkeypatch):
    monkeypatch.delenv("VOIDCAST_FB", raising=False)
    evinput = load_evinput()
    calls = []
    monkeypatch.setattr(evinput, "start", lambda: calls.append("start") or True)
    monkeypatch.setattr(evinput, "stop", lambda: calls.append("stop"))

    assert evinput.sync_with_joystick(False) is False
    assert calls == ["stop"]
