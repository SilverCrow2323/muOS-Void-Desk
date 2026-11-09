import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_service():
    script = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_tailscale_service_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tailscale_handlers_delegate_to_native_adapter(monkeypatch, tmp_path):
    service = load_service()
    calls = []
    fake = SimpleNamespace(
        status=lambda app_dir: {"ok": True, "installed": True, "backend": "Running"},
        action=lambda app_dir, action, value: (
            calls.append((app_dir, action, value)) or {"ok": True, "output": "Done"}
        ),
    )
    monkeypatch.setattr(service, "APP_DIR", tmp_path)
    monkeypatch.setattr(service, "tailscale_manager", fake)

    status = service.HANDLERS["tailscale_status"]({})
    result = service.HANDLERS["tailscale_action"]({
        "action": "exit_node", "value": "100.64.0.2"
    })

    assert status["installed"] is True
    assert status["backend"] == "Running"
    assert result["ok"] is True
    assert calls == [(tmp_path, "exit_node", "100.64.0.2")]


def test_tailscale_action_handler_rejects_missing_adapter(monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "tailscale_manager", None)
    assert service.h_tailscale_status({})["ok"] is False
    assert service.h_tailscale_action({"action": "start"})["ok"] is False


def test_tailscale_first_start_is_dispatched_to_background_job(monkeypatch):
    service = load_service()
    captured = {}
    monkeypatch.setattr(
        service, "tailscale_manager",
        SimpleNamespace(status=lambda app_dir: {"ok": True}),
    )

    def fake_job(args):
        captured.update(args)
        return {"ok": True, "job": {"id": "7"}}

    monkeypatch.setattr(service, "h_job_start", fake_job)
    result = service.h_tailscale_action({"action": "start"})

    assert result["ok"] is True
    assert captured["service_task"] == "tailscale_start"
    assert captured["hub"] == "uplink"
