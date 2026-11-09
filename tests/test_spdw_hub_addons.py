import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "service" / "spdw_hub" / "addons.py"


def load_addons_module():
    spec = importlib.util.spec_from_file_location("spdw_addons_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_manifest():
    return {
        "schema": "spdw-addon",
        "manifest_version": 1,
        "id": "diagnostics.sample",
        "name": "Sample Diagnostics",
        "version": "1.0.0",
        "description": "Read-only sample module.",
        "author": "SPDW",
        "host": "both",
        "entrypoint": "addon.py",
        "ui": {"label": "Diagnostics", "route": "/addons/diagnostics.sample/"},
        "capabilities": ["device.status.read"],
        "confirmation_actions": [],
        "listeners": [],
        "dependencies": {
            "binaries": [], "python_modules": [],
            "services": [], "addons": [],
        },
    }


def test_valid_addon_manifest_is_accepted(tmp_path):
    module = load_addons_module()
    (tmp_path / "addon.py").write_text("# inert test entrypoint\n", encoding="utf-8")

    assert module.validate_addon_manifest(valid_manifest(), tmp_path) == []


def test_addon_entrypoint_cannot_escape_its_directory():
    module = load_addons_module()
    manifest = valid_manifest()
    manifest["entrypoint"] = "../../outside.py"

    errors = module.validate_addon_manifest(manifest)

    assert any("safe relative path" in error for error in errors)


def test_external_listener_requires_auth_and_a_reason():
    module = load_addons_module()
    manifest = valid_manifest()
    manifest["listeners"] = [{
        "host": "pc", "protocol": "tcp", "port": 9133,
        "bind": "lan", "auth": "none",
    }]

    errors = module.validate_addon_manifest(manifest)

    assert any("requires auth" in error for error in errors)
    assert any("requires a reason" in error for error in errors)


def test_destructive_capability_requires_confirmation():
    module = load_addons_module()
    manifest = valid_manifest()
    manifest["capabilities"] = ["files.delete"]

    errors = module.validate_addon_manifest(manifest)

    assert any("confirmation_actions" in error for error in errors)


def test_unknown_capability_is_rejected():
    module = load_addons_module()
    manifest = valid_manifest()
    manifest["capabilities"] = ["root.shell.anything"]

    errors = module.validate_addon_manifest(manifest)

    assert any("unknown capabilities" in error for error in errors)


def test_discovery_never_enables_or_executes_addon(tmp_path):
    module = load_addons_module()
    root = tmp_path / "addons"
    addon_dir = root / "sample"
    addon_dir.mkdir(parents=True)
    (addon_dir / "addon.py").write_text(
        "raise RuntimeError('must not execute during discovery')\n",
        encoding="utf-8")
    (addon_dir / "addon.json").write_text(
        json.dumps(valid_manifest()), encoding="utf-8")

    discovered = module.discover_addons([root])

    assert len(discovered) == 1
    assert discovered[0]["valid"] is True
    assert discovered[0]["enabled"] is False

def test_addon_entrypoint_symlink_cannot_escape_addon_directory(tmp_path):
    module = load_addons_module()
    addon_dir = tmp_path / "addons" / "sample"
    addon_dir.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("# outside\n", encoding="utf-8")
    (addon_dir / "entry.py").symlink_to(outside)
    manifest = valid_manifest()
    manifest["entrypoint"] = "entry.py"

    errors = module.validate_addon_manifest(manifest, addon_dir)

    assert any("resolves outside" in error for error in errors)



def test_malformed_manifest_types_are_reported_without_crashing():
    module = load_addons_module()
    manifest = valid_manifest()
    manifest["host"] = {"unexpected": "object"}
    manifest["capabilities"] = [{}]
    manifest["confirmation_actions"] = [{}]
    manifest["listeners"] = [{
        "host": {},
        "protocol": [],
        "port": True,
        "bind": {},
        "auth": "none",
    }]

    errors = module.validate_addon_manifest(manifest)

    assert any("host must be pc" in error for error in errors)
    assert any("capabilities must contain only strings" in error for error in errors)
    assert any("confirmation_actions must contain only strings" in error for error in errors)
    assert any("listeners[0] has invalid host" in error for error in errors)
    assert any("listeners[0] has invalid protocol" in error for error in errors)
    assert any("listeners[0] has invalid port" in error for error in errors)
    assert any("listeners[0] bind must be" in error for error in errors)


def test_discovery_handles_unhashable_manifest_ids(tmp_path):
    module = load_addons_module()
    addon_dir = tmp_path / "addons" / "bad-id"
    addon_dir.mkdir(parents=True)
    manifest = valid_manifest()
    manifest["id"] = {"not": "hashable"}
    (addon_dir / "addon.py").write_text("# inert\n", encoding="utf-8")
    (addon_dir / "addon.json").write_text(json.dumps(manifest), encoding="utf-8")

    discovered = module.discover_addons([tmp_path / "addons"])

    assert len(discovered) == 1
    assert discovered[0]["valid"] is False
    assert discovered[0]["id"] == {"not": "hashable"}


def test_discovery_rejects_symlinked_manifest(tmp_path):
    module = load_addons_module()
    root = tmp_path / "addons"
    addon_dir = root / "sample"
    addon_dir.mkdir(parents=True)
    external = tmp_path / "external.json"
    external.write_text(json.dumps(valid_manifest()), encoding="utf-8")
    (addon_dir / "addon.py").write_text("# inert\n", encoding="utf-8")
    (addon_dir / "addon.json").symlink_to(external)

    discovered = module.discover_addons([root])

    assert len(discovered) == 1
    assert discovered[0]["valid"] is False
    assert any("must not be a symlink" in error for error in discovered[0]["errors"])
