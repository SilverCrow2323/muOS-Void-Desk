from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "qwasar_ui_manifest.json"
SCHEMA_PATH = ROOT / "schemas" / "qwasar-ui.schema.json"
INSTALLATIONS_PATH = ROOT / "data" / "qwasar_installations.example.json"
INSTALLATIONS_SCHEMA_PATH = ROOT / "schemas" / "qwasar-installations.schema.json"


def _walk_component(node):
    yield node
    for child in node.get("children", []):
        yield from _walk_component(child)
    for children in node.get("slots", {}).values():
        for child in children:
            yield from _walk_component(child)


def _load_ui():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_component_nodes(manifest):
    nodes = []
    nodes.extend(_walk_component(manifest["shell"]["header"]))
    nodes.extend(_walk_component(manifest["shell"]["footer"]))
    for region in manifest["shell"]["homePanels"].values():
        nodes.extend(_walk_component(region["content"]))
    for panel in manifest["shell"]["globalPanels"].values():
        nodes.extend(_walk_component(panel["content"]))
    nodes.extend(_walk_component(manifest["runtimeLaunch"]["selector"]["component"]))
    for workspace in manifest["workspaces"]:
        nodes.extend(_walk_component(workspace["layout"]))
        for widget in workspace.get("widgets", []):
            nodes.extend(_walk_component(widget))
        for section in workspace.get("sections", []):
            if section.get("layout"):
                nodes.extend(_walk_component(section["layout"]))
            for widget in section.get("widgets", []):
                nodes.extend(_walk_component(widget))
    return nodes


def _all_menu_entries(manifest):
    def visit(entries):
        for entry in entries or []:
            yield entry
            yield from visit(entry.get("children", []))

    for workspace in manifest["workspaces"]:
        yield from visit(workspace.get("menu", []))
        for section in workspace.get("sections", []):
            yield from visit(section.get("menu", []))


def test_qwasar_ui_schema_and_reference_manifest_validate():
    manifest = _load_ui()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(manifest)
    assert manifest["schemaVersion"] == "1.0"
    assert manifest["apiVersion"] == "1.0"


def test_installed_instance_registry_uses_its_separate_local_schema():
    schema = json.loads(INSTALLATIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
    example = json.loads(INSTALLATIONS_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(example)
    assert example["instances"] == []


def test_future_engine_adapters_are_reserved_not_claimed_as_supported():
    manifest = _load_ui()
    adapters = {item["id"]: item["status"] for item in manifest["engineAdapters"]}
    assert adapters["pygame"] == "current"
    assert adapters["love"] == "current"
    for engine in ("qt6", "lvgl", "web"):
        assert adapters[engine] == "planned"


def test_shell_has_buildable_header_footer_side_panels_and_media_overlay():
    shell = _load_ui()["shell"]
    assert shell["header"]["type"] == "shell.header"
    assert shell["footer"]["type"] == "shell.footer"
    assert set(shell["homePanels"]) == {"left", "right"}
    assert shell["globalPanels"]["mediaPlayer"]["triggerAction"] == "panel.media.toggle"
    assert shell["globalPanels"]["mediaPlayer"]["enabled"] is True


def test_m_shortcut_is_a_semantic_action_not_a_hardcoded_engine_callback():
    manifest = _load_ui()
    matches = [
        item for item in manifest["keymap"]
        if item["input"] == "keyboard" and item["value"].lower() == "m"
    ]
    assert len(matches) == 1
    assert matches[0]["actionId"] == "panel.media.toggle"
    assert any(action["id"] == "panel.media.toggle" for action in manifest["actions"])


def test_bootloader_and_frontend_engine_selection_are_separate():
    runtime = _load_ui()["runtimeLaunch"]
    selector = runtime["selector"]
    assert selector["stage"] == "before-frontend"
    assert set(selector["selectionAxes"]) >= {
        "installed-instance", "build-flavour", "frontend-engine"
    }
    assert set(selector["engines"]) == {"pygame", "love"}
    assert selector["allowMultipleInstances"] is True
    adapters = {item["id"]: item for item in runtime["bootloaderAdapters"]}
    assert adapters["grub2"]["scope"] == "os-installation-selection"
    assert adapters["grub2"]["platform"] == "desktop-linux-x86_64"
    assert adapters["muos-launcher"]["scope"] == "app-launch"


def test_build_flavours_are_independent_of_frontend_engines_and_can_coexist():
    runtime = _load_ui()["runtimeLaunch"]
    flavours = {item["id"] for item in runtime["buildFlavours"]}
    assert flavours == {"full", "essential", "slim", "custom"}
    assert runtime["installPolicy"]["sideBySideInstances"] is True
    assert runtime["installPolicy"]["uniqueInstanceIds"] is True
    assert runtime["installPolicy"]["isolatedApplicationRoots"] is True


def test_start_session_targets_distinguish_desktop_terminal_pc_and_vm():
    targets = {item["id"]: item for item in _load_ui()["runtimeLaunch"]["sessionTargets"]}
    assert targets["session.xfce"]["kind"] == "desktop"
    assert targets["session.shell"]["kind"] == "terminal"
    assert targets["session.qwasar-link"]["kind"] == "remote-workstation"
    assert targets["session.virtualbox"]["kind"] == "virtual-machine"
    assert targets["session.virtualbox"]["platforms"] == ["desktop-linux-x86_64"]


def test_apt_package_adapters_never_target_the_muos_buildroot_host():
    adapters = {item["id"]: item for item in _load_ui()["runtimeLaunch"]["packageAdapters"]}
    assert adapters["apt.desktop-image"]["target"] == "optional-debian-ubuntu-image"
    assert adapters["apt.desktop-image"]["hostMutation"] is False
    assert adapters["apt.desktop-host"]["requiresExplicitApproval"] is True
    assert adapters["muos-buildroot"]["status"] == "forbidden"
    assert adapters["muos-buildroot"]["target"] == "muos-buildroot-host"


def test_input_leap_is_keyboard_mouse_only_and_not_remote_display():
    integrations = {item["id"]: item for item in _load_ui()["runtimeLaunch"]["integrations"]}
    assert integrations["input-leap"]["requiresInstallOnBothEnds"] is True
    assert "keyboard-mouse" in integrations["input-leap"]["transports"]
    assert "remote-display" not in integrations["input-leap"]["transports"]
    assert "remote-display" in integrations["qwasar-link"]["transports"]


def test_workspace_templates_and_four_part_toolbox_are_declared():
    manifest = _load_ui()
    workspaces = {item["id"]: item for item in manifest["workspaces"]}
    assert set(workspaces) == {
        "start-session", "the-forge", "uplink", "media-vault",
        "rt-toolbox", "settings", "info-community", "end-node",
    }
    assert workspaces["rt-toolbox"]["template"] == "tool-workbench"
    assert workspaces["rt-toolbox"]["status"] == "migration-target"
    sections = {section["id"] for section in workspaces["rt-toolbox"]["sections"]}
    assert sections == {
        "toolbox.everyday", "toolbox.files-storage",
        "toolbox.system-health", "toolbox.developer-terminal",
    }
    aliases = {item["oldId"]: item["newId"] for item in manifest["legacyAliases"]}
    assert aliases["hub_workshop"] == "rt-toolbox"
    assert aliases["hub_toolbox"] == "rt-toolbox"


def test_component_types_slots_and_ids_are_registered_and_unique():
    manifest = _load_ui()
    registry = {item["id"]: item for item in manifest["componentRegistry"]}
    assert len(registry) == len(manifest["componentRegistry"])
    for definition in registry.values():
        jsonschema.Draft202012Validator.check_schema(definition["propsSchema"])
    nodes = _load_component_nodes(manifest)
    for node in nodes:
        assert node["type"] in registry, (
            f"unregistered component type {node['type']} in {node['id']}"
        )
        definition = registry[node["type"]]
        allowed = set(definition["slots"])
        assert set(node.get("slots", {})) <= allowed, (
            f"unsupported slots on {node['type']} component {node['id']}"
        )
        jsonschema.Draft202012Validator(definition["propsSchema"]).validate(
            node.get("props", {})
        )
    ids = [node["id"] for node in nodes]
    assert len(ids) == len(set(ids)), "duplicate component node IDs"


def test_every_menu_and_component_action_reference_resolves():
    manifest = _load_ui()
    known = {action["id"] for action in manifest["actions"]}
    for entry in _all_menu_entries(manifest):
        if entry.get("actionId"):
            assert entry["actionId"] in known, entry["id"]
    for node in _load_component_nodes(manifest):
        if node.get("actionId"):
            assert node["actionId"] in known, node["id"]


def test_inspector_and_switchboard_have_separate_safe_responsibilities():
    management = _load_ui()["featureManagement"]
    tools = {item["id"]: item for item in management["tools"]}
    assert tools["qwasar.inspector"]["defaultMode"] == "read-only"
    assert "scan" in tools["qwasar.inspector"]["actions"]
    assert tools["qwasar.switchboard"]["defaultMode"] == "profile-edit"
    assert "enable" in tools["qwasar.switchboard"]["actions"]
    assert "disable" in tools["qwasar.switchboard"]["actions"]
    assert "shell.core" in management["protectedAreas"]

def test_portable_profile_schema_validates_data_only_layout_and_feature_overrides():
    schema_path = ROOT / "schemas" / "qwasar-profile.schema.json"
    sample_path = ROOT / "data" / "profiles" / "voiddesk-handheld-default.qprofile.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    profile = json.loads(sample_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(profile)
    assert "workspaceOrder" in profile
    assert "shell" in profile
    assert "workspaceOverrides" in profile
    assert "bindings" in profile
    assert "enginePreference" not in profile
    assert "installPath" not in profile


def test_profile_separates_disabled_from_hidden_contributions():
    schema = json.loads(
        (ROOT / "schemas" / "qwasar-profile.schema.json").read_text(encoding="utf-8")
    )
    states = schema["$defs"]["contributionState"]["properties"]["state"]["enum"]
    assert states == ["enabled", "disabled", "hidden"]
