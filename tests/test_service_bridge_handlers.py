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
