import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_service_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_toolbox_stats_counts_notes_and_supported_text_files(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    (tmp_path / "notes").mkdir()
    (tmp_path / "Texts").mkdir()
    (tmp_path / "notes" / "one.txt").write_text("note")
    (tmp_path / "notes" / "two.txt").write_text("note")
    (tmp_path / "notes" / "ignore.md").write_text("not a note")
    (tmp_path / "Texts" / "readme.md").write_text("text")
    (tmp_path / "Texts" / "config.ini").write_text("text")
    (tmp_path / "Texts" / "cover.png").write_bytes(b"png")
    (tmp_path / "Texts" / "nested").mkdir()
    result = service.h_toolbox_stats({})
    assert result == {"ok": True, "notes_count": 2, "text_files": 2}


def test_calendar_events_returns_only_valid_events_for_requested_month(
    tmp_path, monkeypatch
):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    (tmp_path / "calendar.json").write_text(json.dumps([
        {"t": "Later", "y": 2026, "mo": 11, "d": 8, "h": 18, "mi": 30, "imp": 2},
        {"t": "Earlier", "y": 2026, "mo": 11, "d": 8, "h": 9, "mi": 15, "imp": 1},
        {"t": "Other month", "y": 2026, "mo": 12, "d": 1, "h": 9, "mi": 0},
        {"t": "Invalid date", "y": 2026, "mo": 11, "d": 31, "h": 9, "mi": 0},
        {"broken": True},
    ]), encoding="utf-8")
    result = service.h_calendar_events({"year": 2026, "month": 11})
    assert result["ok"] is True
    events = result["events"]["2026-11-08"]
    assert [event["title"] for event in events] == ["Earlier", "Later"]
    assert events[0]["category"] == "personal"
    assert events[1]["importance"] == 2
    assert "2026-12-01" not in result["events"]


def test_calendar_events_rejects_invalid_month(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    result = service.h_calendar_events({"year": 2026, "month": 13})
    assert result["ok"] is False


def test_github_release_handler_returns_bounded_public_metadata(monkeypatch):
    service = load_service()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps([
                {
                    "tag_name": "v10.5.4",
                    "name": "Void Desk 10.5.4",
                    "html_url": "https://github.com/example/release",
                    "published_at": "2026-11-11T12:00:00Z",
                    "draft": False,
                    "prerelease": True,
                    "body": "Release notes",
                },
                {"tag_name": "draft", "draft": True},
            ]).encode()

    requested = {}

    def fake_urlopen(request, timeout):
        requested["url"] = request.full_url
        requested["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(service.urllib.request, "urlopen", fake_urlopen)
    result = service.h_gh_fetch_releases({})
    assert result["ok"] is True
    assert result["tag"] == "v10.5.4"
    assert result["status"] == "available"
    assert len(result["releases"]) == 1
    assert result["releases"][0]["notes"] == "Release notes"
    assert requested["timeout"] == 8
    assert "api.github.com/repos/SilverCrow2323/Void-Desk-Project/releases" in requested["url"]


def test_github_release_handler_reports_empty_release_catalog(monkeypatch):
    service = load_service()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"[]"

    monkeypatch.setattr(
        service.urllib.request, "urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    result = service.h_gh_fetch_releases({})
    assert result == {
        "ok": True,
        "tag": None,
        "name": "No published releases",
        "url": None,
        "published_at": None,
        "releases": [],
        "status": "empty",
    }


def test_github_release_command_is_registered():
    service = load_service()
    assert service.HANDLERS["gh_fetch_releases"] is service.h_gh_fetch_releases


def _prepare_muos_app_roots(tmp_path, monkeypatch):
    service = load_service()
    sd1 = tmp_path / "sd1" / "MUOS" / "application"
    sd2 = tmp_path / "sd2" / "MUOS" / "application"
    sd1.mkdir(parents=True)
    sd2.mkdir(parents=True)
    monkeypatch.setattr(service, "IS_DEVICE", True)
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)
    monkeypatch.setattr(service, "APP_DIR", tmp_path / "VoidDesk")
    monkeypatch.setattr(service, "MUOS_APP_ROOTS", (sd1, sd2))
    monkeypatch.setattr(service, "DATA", tmp_path / "VoidDesk" / "data")
    return service, sd1, sd2


def _make_muos_app(root, name, *, executable=True):
    app_dir = root / name
    app_dir.mkdir()
    launcher = app_dir / "mux_launch.sh"
    launcher.write_text("#!/bin/sh\n# HELP: Test application\nexit 0\n")
    launcher.chmod(0o755 if executable else 0o644)
    return app_dir


def test_muos_app_discovery_only_returns_direct_launchable_apps(tmp_path, monkeypatch):
    service, sd1, sd2 = _prepare_muos_app_roots(tmp_path, monkeypatch)
    app1 = _make_muos_app(sd1, "Example App")
    app2 = _make_muos_app(sd2, "Another_Tool")
    _make_muos_app(sd1, "NotExecutable", executable=False)
    outside = _make_muos_app(tmp_path, "OutsideRoot")
    (sd1 / "LinkedApp").symlink_to(outside, target_is_directory=True)
    nested = sd1 / "Group"
    nested.mkdir()
    (nested / "NestedApp").mkdir()

    result = service.h_list_muos_apps({})
    assert result["ok"] is True
    assert [app["name"] for app in result["apps"]] == [
        "Example App", "Another_Tool"
    ]
    assert result["apps"][0]["path"] == str(app1.resolve())
    assert result["apps"][0]["sd"] == "SD1"
    assert result["apps"][0]["help"] == "Test application"
    assert result["apps"][1]["path"] == str(app2.resolve())
    assert result["apps"][1]["sd"] == "SD2"


def test_muos_app_launch_writes_shared_pygame_handoff_marker(tmp_path, monkeypatch):
    service, sd1, _sd2 = _prepare_muos_app_roots(tmp_path, monkeypatch)
    app_dir = _make_muos_app(sd1, "Example App")

    scanned = service.h_list_muos_apps({})
    assert scanned["ok"] is True
    app = scanned["apps"][0]
    result = service.h_launch_muos_app({"path": app["path"]})

    assert result["ok"] is True
    assert result["handoff"] is True
    marker = service.DATA / ".muos_app"
    assert marker.read_text(encoding="utf-8").splitlines() == [
        str(app_dir.resolve()), "Example App"
    ]


def test_muos_app_launch_rejects_paths_not_returned_by_the_scanner(
    tmp_path, monkeypatch
):
    service, _sd1, _sd2 = _prepare_muos_app_roots(tmp_path, monkeypatch)
    outside = _make_muos_app(tmp_path, "OutsideRoot")

    result = service.h_launch_muos_app({"path": str(outside.resolve())})
    assert result["ok"] is False
    assert not (service.DATA / ".muos_app").exists()


def test_muos_app_handlers_are_registered():
    service = load_service()
    assert service.HANDLERS["list_muos_apps"] is service.h_list_muos_apps
    assert service.HANDLERS["launch_muos_app"] is service.h_launch_muos_app


def test_media_library_lists_only_supported_files_and_skips_symlinks(tmp_path, monkeypatch):
    service = load_service()
    root = tmp_path / "sd"
    music = root / "Music"
    music.mkdir(parents=True)
    (music / "track.flac").write_bytes(b"audio")
    (music / "clip.mp4").write_bytes(b"video")
    (music / "cover.png").write_bytes(b"image")
    (music / "folder").mkdir()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"outside")
    (music / "linked.mp3").symlink_to(outside)
    monkeypatch.setattr(service, "MEDIA_ROOTS", (root,))
    result = service.h_media_list({"path": str(music)})
    assert result["ok"] is True
    assert [item["name"] for item in result["items"]] == [
        "folder", "clip.mp4", "track.flac"
    ]
    assert all("linked.mp3" != item["name"] for item in result["items"])


def test_media_library_rejects_path_traversal_and_external_paths(tmp_path, monkeypatch):
    service = load_service()
    root = tmp_path / "sd"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(service, "MEDIA_ROOTS", (root,))
    assert service.h_media_list({"path": str(outside)})["ok"] is False
    assert service.h_media_list({"path": str(root / ".." / "outside")})["ok"] is False
    assert service.h_media_play({"path": str(outside / "secret.mp3")})["ok"] is False


def test_media_library_handlers_are_registered():
    service = load_service()
    assert service.HANDLERS["media_list"] is service.h_media_list
    assert service.HANDLERS["media_play"] is service.h_media_play
    assert service.HANDLERS["media_stop"] is service.h_media_stop


def test_media_play_uses_argument_list_and_selects_audio_mode(tmp_path, monkeypatch):
    service = load_service()
    root = tmp_path / "sd"
    root.mkdir()
    track = root / "track.flac"
    track.write_bytes(b"audio")
    monkeypatch.setattr(service, "MEDIA_ROOTS", (root,))
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/mpv")
    spawned = {}

    class FakeProcess:
        pid = 123
        def poll(self):
            return None
        def terminate(self):
            pass
        def wait(self, timeout=None):
            return 0

    def fake_popen(args, **kwargs):
        spawned["args"] = args
        spawned["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(service.subprocess, "Popen", fake_popen)
    result = service.h_media_play({"path": str(track)})
    assert result["ok"] is True
    assert spawned["args"] == [
        "/usr/bin/mpv", "--no-terminal", "--no-video", str(track)
    ]
    assert "shell" not in spawned["kwargs"]


def test_media_play_uses_video_window_for_video_files(tmp_path, monkeypatch):
    service = load_service()
    root = tmp_path / "sd"
    root.mkdir()
    video = root / "clip.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(service, "MEDIA_ROOTS", (root,))
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/mpv")
    spawned = {}

    class FakeProcess:
        pid = 124
        def poll(self):
            return None
        def terminate(self):
            pass
        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(
        service.subprocess, "Popen",
        lambda args, **kwargs: (spawned.update(args=args, kwargs=kwargs) or FakeProcess()),
    )
    result = service.h_media_play({"path": str(video)})
    assert result["ok"] is True
    assert "--force-window=yes" in spawned["args"]
    assert "--no-video" not in spawned["args"]


def test_radio_search_sanitizes_catalogue_and_bounds_results(monkeypatch):
    service = load_service()
    station_id = "12345678-1234-1234-1234-123456789abc"

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            return json.dumps([
                {"stationuuid": station_id, "name": "Radio One",
                 "url_resolved": "https://stream.example/radio",
                 "country": "Italy", "codec": "MP3", "bitrate": "128"},
                {"stationuuid": "bad", "name": "Bad",
                 "url_resolved": "javascript:alert(1)"},
                {"stationuuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                 "name": "Local", "url_resolved": "http://localhost/stream"},
            ]).encode()

    requested = {}
    def fake_urlopen(request, timeout):
        requested["url"] = request.full_url
        requested["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(service.urllib.request, "urlopen", fake_urlopen)
    result = service.h_radio_search({"name": "Radio", "country": "Italy",
                                     "tag": "jazz", "limit": 999})
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["stations"][0]["stationuuid"] == station_id
    assert "name=Radio" in requested["url"]
    assert "country=Italy" in requested["url"]
    assert "tag=jazz" in requested["url"]
    assert "limit=50" in requested["url"]
    assert requested["timeout"] == 10


def test_radio_favorites_persist_and_toggle(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    monkeypatch.setattr(service, "_RADIO_FAVORITES_FILE",
                        tmp_path / "radio_favorites.json")
    station_id = "12345678-1234-1234-1234-123456789abc"
    service._RADIO_STATIONS[station_id] = {
        "stationuuid": station_id, "name": "Radio One",
        "url": "https://stream.example/radio", "country": "Italy",
        "language": "Italian", "tags": "jazz", "codec": "MP3",
        "bitrate": 128, "favicon": "",
    }
    added = service.h_radio_favorite_toggle({"stationuuid": station_id})
    assert added == {"ok": True, "favorite": True, "count": 1}
    assert service.h_radio_favorites({})["stations"][0]["name"] == "Radio One"
    removed = service.h_radio_favorite_toggle({"stationuuid": station_id})
    assert removed == {"ok": True, "favorite": False, "count": 0}


def test_radio_favorite_rejects_unknown_station_and_invalid_id():
    service = load_service()
    assert service.h_radio_favorite_toggle({"stationuuid": "bad"})["ok"] is False
    assert service.h_radio_favorite_toggle({
        "stationuuid": "12345678-1234-1234-1234-123456789abc"
    })["ok"] is False


def test_radio_play_uses_catalogue_id_not_client_url(monkeypatch):
    service = load_service()
    station_id = "12345678-1234-1234-1234-123456789abc"
    service._RADIO_STATIONS[station_id] = {
        "stationuuid": station_id, "name": "Radio One",
        "url": "https://stream.example/radio",
    }
    class FakePlayer:
        def __init__(self):
            self.url = None
        def start(self, url):
            self.url = url
            return True, ""
    player = FakePlayer()
    monkeypatch.setattr(service, "_radio_player", lambda: player)
    result = service.h_radio_play({
        "stationuuid": station_id,
        "url": "https://attacker.example/evil",
    })
    assert result["ok"] is True
    assert player.url == "https://stream.example/radio"


def test_radio_handlers_are_registered():
    service = load_service()
    assert service.HANDLERS["radio_search"] is service.h_radio_search
    assert service.HANDLERS["radio_favorites"] is service.h_radio_favorites
    assert service.HANDLERS["radio_favorite_toggle"] is service.h_radio_favorite_toggle
    assert service.HANDLERS["radio_play"] is service.h_radio_play
    assert service.HANDLERS["radio_action"] is service.h_radio_action
    assert service.HANDLERS["radio_status"] is service.h_radio_status


def test_radio_search_rejects_unsafe_stream_urls(monkeypatch):
    service = load_service()
    bad = [
        {"stationuuid": "11111111-1111-1111-1111-111111111111",
         "url_resolved": "javascript:alert(1)"},
        {"stationuuid": "22222222-2222-2222-2222-222222222222",
         "url_resolved": "file:///etc/passwd"},
        {"stationuuid": "33333333-3333-3333-3333-333333333333",
         "url_resolved": "http://user:pass@example.org/radio"},
        {"stationuuid": "44444444-4444-4444-4444-444444444444",
         "url_resolved": "http://localhost/radio"},
        {"stationuuid": "66666666-6666-6666-6666-666666666666",
         "url_resolved": "http://192.168.1.1/radio"},
    ]
    assert all(service._radio_clean_station(item) is None for item in bad)


def test_radio_favorite_file_ignores_invalid_entries(tmp_path, monkeypatch):
    service = load_service()
    favorite_file = tmp_path / "radio_favorites.json"
    favorite_file.write_text(json.dumps([
        {"stationuuid": "55555555-5555-5555-5555-555555555555",
         "name": "Valid", "url": "https://radio.example/stream"},
        {"stationuuid": "bad", "name": "Invalid",
         "url": "https://radio.example/stream"},
    ]), encoding="utf-8")
    monkeypatch.setattr(service, "_RADIO_FAVORITES_FILE", favorite_file)
    result = service.h_radio_favorites({})
    assert result["ok"] is True
    assert [item["name"] for item in result["stations"]] == ["Valid"]


def test_radio_actions_control_pause_volume_and_stop(monkeypatch):
    service = load_service()
    class FakePlayer:
        def __init__(self):
            self.running = True
            self.volume = None
            self.stopped = False
        def is_running(self):
            return self.running
        def toggle_pause(self):
            return True
        def set_volume(self, value):
            self.volume = value
        def stop(self):
            self.running = False
            self.stopped = True
    player = FakePlayer()
    monkeypatch.setattr(service, "_radio_player", lambda: player)
    assert service.h_radio_action({"action": "toggle_pause"}) == {
        "ok": True, "pause": True
    }
    assert service.h_radio_action({"action": "volume", "value": 150}) == {
        "ok": True, "volume": 100
    }
    assert player.volume == 100
    assert service.h_radio_action({"action": "stop"}) == {
        "ok": True, "running": False
    }
    assert player.stopped is True
