import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "service" / "spdw_hub" / "registry.py"
DATA = ROOT / "service" / "spdw_hub" / "services.json"


def load_registry_module():
    spec = importlib.util.spec_from_file_location("spdw_registry_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_registry_is_valid_and_loadable():
    registry = load_registry_module()

    data = registry.load_registry(DATA)

    assert data["schema"] == "spdw-service-registry"
    assert registry.validate_registry(data) == []


def test_one_externally_reachable_management_gateway_per_host():
    registry = load_registry_module()
    data = registry.load_registry(DATA)

    for host in ("handheld", "pc"):
        public_management = [
            item for item in registry.listeners_for_host(data, host)
            if item.get("management")
            and item.get("exposure") in ("lan", "tailnet", "lan-or-tailnet")
        ]
        assert len(public_management) == 1
    assert registry.listeners_for_host(data, "handheld")[0]["port"] == 22


def test_tailscale_legacy_panel_is_loopback_only():
    registry = load_registry_module()
    data = registry.load_registry(DATA)
    item = next(x for x in data["services"] if x["id"] == "rt-tailscale-panel-legacy")

    assert item["port"] == 8077
    assert item["bind"] == "loopback"
    assert item["exposure"] == "loopback"
    assert item["auth"] == "rt-pin-session+csrf"


def test_sftp_is_a_subsystem_of_ssh_not_a_second_listener():
    registry = load_registry_module()
    data = registry.load_registry(DATA)
    item = next(x for x in data["services"] if x["id"] == "sftp-subsystem")

    assert item["type"] == "subsystem"
    assert item["shares_listener_with"] == "ssh"
    assert item["port"] == 22
    assert item["fallback_port"] == 2022


def test_registry_rejects_second_management_listener_on_same_host():
    registry = load_registry_module()
    data = registry.load_registry(DATA)
    duplicate = dict(next(
        x for x in data["services"] if x["id"] == "spdw-device-gateway"))
    duplicate.update({
        "id": "duplicate-management",
        "port": 9001,
        "owner": "rogue-addon",
    })
    data["services"].append(duplicate)

    errors = registry.validate_registry(data)

    assert any("second externally reachable management listener" in e for e in errors)


def test_registry_rejects_unauthenticated_wildcard_listener():
    registry = load_registry_module()
    data = registry.load_registry(DATA)
    data["services"].append({
        "id": "unsafe-test-listener",
        "type": "listener",
        "host": "handheld",
        "protocol": "tcp",
        "port": 9011,
        "bind": "all",
        "exposure": "lan",
        "auth": "none",
        "owner": "unsafe-addon",
        "management": False,
    })

    errors = registry.validate_registry(data)

    assert any("externally exposed without authentication" in e for e in errors)


def test_port_audit_includes_listener_owner_and_auth_model():
    registry = load_registry_module()
    data = registry.load_registry(DATA)

    audit = registry.port_audit(data)

    pc_gateway = next(x for x in audit["pc"] if x["id"] == "spdw-pc-gateway")
    assert pc_gateway["port"] == 8420
    assert pc_gateway["owner"] == "spdw-hub-pc"
    assert pc_gateway["auth"] == "device-token"

def test_port_audit_distinguishes_sunshine_transport_from_management():
    registry = load_registry_module()
    data = registry.load_registry(DATA)

    entries = registry.port_audit(data)["pc"]
    video = next(x for x in entries
                 if x["id"] == "sunshine-stream-transport:video")
    web_ui = next(x for x in entries if x["id"] == "sunshine-web-ui")

    assert video["protocol"] == "udp"
    assert video["port"] == 47998
    assert video["kind"] == "protocol-transport"
    assert video["management"] is False
    assert web_ui["port"] == 47990
    assert web_ui["exposure"] == "loopback"


def test_port_audit_marks_sftp_as_shared_subsystem_not_new_socket():
    registry = load_registry_module()
    data = registry.load_registry(DATA)

    sftp = next(x for x in registry.port_audit(data)["handheld"]
                if x["id"] == "sftp-subsystem")

    assert sftp["kind"] == "subsystem"
    assert sftp["port"] == 22
    assert sftp["shares_listener_with"] == "ssh"
    assert sftp["fallback_port"] == 2022


def test_registry_rejects_duplicate_socket_ownership():
    registry = load_registry_module()
    data = registry.load_registry(DATA)
    duplicate = {
        "id": "second-ssh-owner",
        "type": "listener",
        "host": "handheld",
        "protocol": "tcp",
        "port": 22,
        "bind": "system",
        "exposure": "lan-or-tailnet",
        "auth": "ssh-host-auth",
        "owner": "another-daemon",
        "management": False,
    }
    data["services"].append(duplicate)

    errors = registry.validate_registry(data)

    assert any("listener collision" in error for error in errors)

