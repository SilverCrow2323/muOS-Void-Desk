import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manager():
    script = ROOT / "service" / "tailscale_manager.py"
    spec = importlib.util.spec_from_file_location("voiddesk_tailscale_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_install(tmp_path):
    root = tmp_path / "RtTailscale"
    root.mkdir()
    (root / "rt").write_text("#!/bin/sh\n")
    (root / "ts").write_text("#!/bin/sh\n")
    (root / "config").mkdir()
    (root / "config" / "rt.conf").write_text("TAILDROP_DIR=\n")
    (root / "taildrop").mkdir()
    return root


class Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_status_reads_rt_summary_and_parses_tailnet_peers(tmp_path):
    manager = load_manager()
    root = make_install(tmp_path)
    (root / "taildrop" / "received.zip").write_bytes(b"abc")
    status_json = {
        "BackendState": "Running",
        "Version": "1.80.0",
        "AuthURL": "",
        "CurrentTailnet": {"Name": "example.ts.net"},
        "Self": {"HostName": "handheld", "TailscaleIPs": ["100.64.0.1"], "Online": True, "UserID": 1},
        "User": {"1": {"LoginName": "user@example.com"}},
        "Peer": {
            "peer-1": {"HostName": "desktop", "TailscaleIPs": ["100.64.0.2"], "Online": True, "ExitNodeOption": True}
        },
    }
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[0].endswith("/rt"):
            if command[1] == "summary":
                return Result("backend=Running\ndaemon=1\npanel=1\nwatchdog=1\ntaildrop=1\nautostart=on\nversion=3.0.6\n")
            return Result("LAN http://192.168.1.2:8077\n")
        if command[1:3] == ["status", "--json"]:
            return Result(json.dumps(status_json))
        raise AssertionError(command)

    result = manager.status(tmp_path, extra_roots=[root], runner=runner)
    assert result["ok"] and result["installed"] and result["available"]
    assert result["backend"] == "Running"
    assert result["self"]["ips"] == ["100.64.0.1"]
    assert result["self"]["user"] == "user@example.com"
    assert result["peers"][0]["name"] == "desktop"
    assert result["taildrop"][0]["name"] == "received.zip"
    assert result["autostart"] is True
    assert len(calls) == 3


def test_status_reports_missing_install_without_running_commands(tmp_path):
    manager = load_manager()
    result = manager.status(tmp_path, extra_roots=[])
    assert result["ok"] is True
    assert result["installed"] is False
    assert result["peers"] == []


def test_exit_node_action_validates_before_execution(tmp_path):
    manager = load_manager()
    root = make_install(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return Result("")

    bad = manager.action(tmp_path, "exit_node", "bad value; reboot",
                         extra_roots=[root], runner=runner)
    assert bad["ok"] is False
    assert calls == []

    good = manager.action(tmp_path, "exit_node", "100.64.0.9",
                          extra_roots=[root], runner=runner)
    assert good["ok"] is True
    assert calls[0][1:] == ["set", "--exit-node=100.64.0.9"]


def test_actions_use_rt_manager_not_a_second_tailscaled(tmp_path):
    manager = load_manager()
    root = make_install(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return Result("")

    result = manager.action(tmp_path, "start", extra_roots=[root], runner=runner)
    assert result["ok"] is True
    assert calls == [[str(root / "rt"), "start"]]
    assert not any("tailscaled" in part for command in calls for part in command)


def test_unknown_action_is_rejected(tmp_path):
    manager = load_manager()
    root = make_install(tmp_path)
    result = manager.action(tmp_path, "arbitrary_shell", extra_roots=[root])
    assert result["ok"] is False
    assert "unsupported" in result["error"]
