from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MEDIA_PATH = ROOT / "service" / "media_module.py"
SERVICE_PATH = ROOT / "service" / "voiddesk_service.py"


def load_media_module():
    spec = importlib.util.spec_from_file_location("voiddesk_media_module_test", MEDIA_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_service_module():
    spec = importlib.util.spec_from_file_location("voiddesk_media_service_test", SERVICE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_radio_catalog_reuses_curated_pygame_stations_and_categories(tmp_path):
    module = load_media_module()
    module.configure(tmp_path)

    all_stations = module.list_stations("all")
    italian = module.list_stations("italia")
    tekno = module.list_stations("tekno")

    assert all_stations["ok"] is True
    assert all_stations["count"] >= 10
    assert italian["count"] >= 3
    assert tekno["count"] >= 2
    assert all(item["id"] and item["name"] for item in all_stations["stations"])
    assert all("url" not in item for item in all_stations["stations"])


def test_radio_favourites_persist_in_the_shared_void_desk_config(tmp_path):
    module = load_media_module()
    module.configure(tmp_path)
    stations = module.list_stations("all")["stations"]
    station_id = stations[0]["id"]

    added = module.toggle_favorite(station_id)
    assert added == {"ok": True, "favorite": True, "station_id": station_id}
    assert module.list_stations("preferiti")["count"] == 1

    saved = json.loads((tmp_path / "data" / "desk_config.json").read_text())
    assert saved["radio_favorites"][0]["name"] == stations[0]["name"]

    removed = module.toggle_favorite(station_id)
    assert removed["favorite"] is False
    assert module.list_stations("preferiti")["count"] == 0


def test_radio_player_validates_station_and_reports_no_fake_success(tmp_path, monkeypatch):
    module = load_media_module()
    module.configure(tmp_path)
    stations = module.list_stations("all")["stations"]
    module._PLAYER = None

    result = module.play_radio(stations[0]["id"])
    assert result["ok"] is False
    assert "mpv controller" in result["error"]

    class FakePlayer:
        def __init__(self):
            self.started = None
        def start(self, url, extra_args=None):
            self.started = (url, extra_args)
            return True, ""
        def is_running(self):
            return True
        def status(self):
            return {"running": True, "icy_title": "Test stream", "volume": 70}
        def stop(self):
            self.started = None

    fake = FakePlayer()
    module._PLAYER = fake
    import iptv_module
    monkeypatch.setattr(iptv_module, "validate_feed_url", lambda url: url)
    result = module.play_radio(stations[0]["id"])
    assert result["ok"] is True
    assert fake.started and fake.started[0].startswith(("http://", "https://"))
    assert module.status()["playing"] is True
    assert "url" not in module.status()


def test_media_browser_confines_paths_and_skips_symlinks(tmp_path, monkeypatch):
    service = load_service_module()
    root = tmp_path / "sd1"
    music = root / "MUSIC"
    music.mkdir(parents=True)
    (music / "track.ogg").write_bytes(b"audio")
    (music / "notes.txt").write_text("not media")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.mp3").write_bytes(b"no")
    try:
        (music / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pass

    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)
    monkeypatch.setattr(service, "MEDIA_ROOT_CANDIDATES", ((root, "SD1"),))
    response = service.HANDLERS["media_list"]({"path": str(music)})
    names = {entry["name"] for entry in response["entries"]}
    assert response["ok"] is True
    assert "track.ogg" in names
    assert "notes.txt" not in names
    assert "escape" not in names

    with pytest.raises(ValueError, match="outside"):
        service._media_resolve_path(str(outside / "secret.mp3"))
    with pytest.raises(ValueError, match="traverse"):
        service._media_resolve_path(str(root / ".." / "outside" / "secret.mp3"))


def test_visual_capture_media_handlers_return_offline_fixtures(monkeypatch):
    service = load_service_module()
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", True)
    roots = service.HANDLERS["media_roots"]({})
    assert roots["ok"] is True
    assert {item["id"] for item in roots["roots"]} == {"sd1", "sd2", "data"}
    entries = service.HANDLERS["media_list"]({"path": "fixture://sd1"})
    assert entries["ok"] is True
    assert {item["type"] for item in entries["entries"]} == {"dir"}
    assert service.HANDLERS["media_play_file"]({"path": "fixture://track/audio"})["ok"] is False


def test_media_service_registers_typed_commands_and_serializes_player_ownership(monkeypatch):
    service = load_service_module()
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)

    calls = []

    class FakeIPTV:
        def stop(self):
            calls.append("iptv-stop")
        def play(self, url, name):
            calls.append(("iptv-play", url, name))
            return True
        def status(self):
            return {"state": "playing", "channel": {"name": "Fixture channel"}}

    class FakeMedia:
        def stop(self):
            calls.append("media-stop")
            return {"ok": True, "state": "idle"}
        def play_radio(self, station_id):
            calls.append(("radio-play", station_id))
            return {"ok": True, "state": "playing", "name": "Fixture radio"}
        def play_file(self, path, name, video=False):
            calls.append(("file-play", path, name, video))
            return {"ok": True, "state": "playing", "kind": "video" if video else "audio"}
        def status(self):
            return {"ok": True, "playing": False, "current": None}

    fake_iptv = FakeIPTV()
    fake_media = FakeMedia()
    monkeypatch.setattr(service, "iptv_module", fake_iptv)
    monkeypatch.setattr(service, "media_module", fake_media)
    monkeypatch.setattr(service, "_IPTV_CHANNELS", [
        {"url": "https://stream.example.test/channel.m3u8", "name": "Fixture channel"}
    ])

    expected = {
        "media_roots", "media_list", "media_play_file", "media_stop",
        "media_playback_status", "radio_list", "radio_toggle_favorite",
        "radio_play", "radio_stop", "radio_status",
    }
    assert expected <= set(service.HANDLERS)

    radio = service.HANDLERS["radio_play"]({"station_id": "fixture-id"})
    assert radio["ok"] is True
    assert calls[:2] == ["iptv-stop", ("radio-play", "fixture-id")]

    calls.clear()
    service.HANDLERS["iptv_play"]({"url": "https://stream.example.test/channel.m3u8"})
    assert calls[:2] == ["media-stop", (
        "iptv-play", "https://stream.example.test/channel.m3u8", "Fixture channel"
    )]


def test_media_browser_hides_playlist_files_until_local_import_is_supported(tmp_path, monkeypatch):
    service = load_service_module()
    root = tmp_path / "sd1"
    root.mkdir()
    (root / "radio.m3u").write_text("#EXTM3U\n")
    (root / "video.m3u8").write_text("#EXTM3U\n")
    (root / "song.mp3").write_bytes(b"audio")
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)
    monkeypatch.setattr(service, "MEDIA_ROOT_CANDIDATES", ((root, "SD1"),))

    response = service.HANDLERS["media_list"]({"path": str(root)})
    names = {entry["name"] for entry in response["entries"]}
    assert response["ok"] is True
    assert names == {"song.mp3"}
