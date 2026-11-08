import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_syncthing_service_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_syncthing_status_returns_native_folder_and_device_data_without_api_key(
        monkeypatch, tmp_path):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)
    monkeypatch.setattr(
        service, "syncthing_discovery",
        SimpleNamespace(discover_connection=lambda data_dir: {
            "url": "http://127.0.0.1:7070", "key": "private-api-key",
        }),
    )
    calls = []

    def rest(url, key, path, method="GET", payload=None):
        calls.append((url, key, path, method))
        if path == "/rest/system/status":
            return {"myID": "VOIDDESK-LOCAL-DEVICE"}
        if path == "/rest/config":
            return {
                "folders": [{
                    "id": "roms", "label": "ROMs",
                    "path": "/mnt/mmc/ROMS", "paused": False,
                }],
                "devices": [{
                    "deviceID": "REMOTE-PC", "name": "Desktop PC",
                }],
            }
        if path == "/rest/system/connections":
            return {"connections": {
                "REMOTE-PC": {"connected": True, "paused": False,
                              "address": "192.168.1.20:22000"},
            }}
        if path.startswith("/rest/db/completion"):
            return {"completion": 75}
        raise AssertionError(path)

    monkeypatch.setattr(service, "_syncthing_rest", rest)
    result = service.h_syncthing_status({})

    assert result["ok"] and result["available"]
    assert result["id"] == "VOIDDESK-LOCAL-DE"
    assert result["folders"][0]["pct"] == 75
    assert result["devices"][0]["connected"] is True
    assert result["connected"] == 1
    assert "key" not in result and "private-api-key" not in repr(result)
    assert all(call[1] == "private-api-key" for call in calls)


def test_syncthing_actions_validate_ids_and_delegate_allowlisted_action(
        monkeypatch, tmp_path):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", False)
    monkeypatch.setattr(
        service, "syncthing_discovery",
        SimpleNamespace(discover_connection=lambda data_dir: {
            "url": "http://127.0.0.1:7070", "key": "secret",
        }),
    )
    monkeypatch.setattr(
        service, "_syncthing_rest",
        lambda url, key, path, method="GET", payload=None: {
            "folders": [{"id": "roms"}],
            "devices": [{"deviceID": "REMOTE-PC"}],
        } if path == "/rest/config" else {},
    )
    captured = {}

    def perform(rest, url, key, action, **kwargs):
        captured.update({"url": url, "key": key, "action": action, **kwargs})
        return {"ok": True, "action": action}

    monkeypatch.setattr(
        service, "syncthing_api",
        SimpleNamespace(perform_action=perform),
    )
    result = service.h_syncthing_action({"action": "scan", "folder": "roms"})
    assert result["ok"] is True
    assert captured == {
        "url": "http://127.0.0.1:7070", "key": "secret",
        "action": "scan", "folder": "roms", "device": "",
    }

    bad = service.h_syncthing_action({
        "action": "scan", "folder": "not-configured",
    })
    assert bad["ok"] is False
    assert "unknown" in bad["error"]


def test_syncthing_status_visual_capture_uses_safe_fixture(monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", True)
    monkeypatch.setattr(
        service, "syncthing_discovery",
        SimpleNamespace(discover_connection=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("visual capture must not probe the real service")
        )),
    )
    result = service.h_syncthing_status({})
    assert result["available"] is True
    assert result["folders"][0]["id"] == "roms"
    assert result["devices"][0]["name"] == "Desktop PC"
