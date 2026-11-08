import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_external_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_registry_reports_only_real_launchers_as_installed(
    tmp_path, monkeypatch
):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "DATA", tmp_path / "data")
    sh_launcher = tmp_path / "external" / "ready" / "mux_launch.sh"
    sh_launcher.parent.mkdir(parents=True)
    sh_launcher.write_text("#!/bin/sh\n")
    love_dir = tmp_path / "external" / "incomplete"
    love_dir.mkdir(parents=True)
    ready_love = tmp_path / "external" / "ready-love"
    ready_love.mkdir()
    (ready_love / "main.lua").write_text("function love.load() end")
    registry = {
        "tools": [
            {"id": "ready", "name": "Ready", "hub": "toolbox",
             "native_engine": "py", "launcher_type": "sh",
             "launcher": "external/ready/mux_launch.sh"},
            {"id": "incomplete", "name": "Incomplete", "hub": "toolbox",
             "native_engine": "love", "launcher_type": "love",
             "launcher": "external/incomplete"},
            {"id": "ready-love", "name": "Ready Love", "hub": "toolbox",
             "native_engine": "love", "launcher_type": "love",
             "launcher": "external/ready-love"},
        ]
    }
    registry_path = tmp_path / "external" / "tools.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    result = service.h_list_external({})
    assert result["ok"] is True
    installed = {tool["id"]: tool["exists"] for tool in result["tools"]}
    assert installed == {
        "ready": True,
        "incomplete": False,
        "ready-love": True,
    }


def test_external_registry_rejects_path_escape(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    registry_path = tmp_path / "external" / "tools.json"
    registry_path.parent.mkdir()
    registry_path.write_text(json.dumps({"tools": [{
        "id": "escape", "name": "Escape", "hub": "toolbox",
        "launcher_type": "sh", "launcher": "../outside.sh",
    }]}), encoding="utf-8")
    result = service.h_list_external({})
    assert result["ok"] is True
    assert result["tools"][0]["exists"] is False
