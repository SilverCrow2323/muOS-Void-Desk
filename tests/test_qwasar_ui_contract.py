from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "qwasar_ui_manifest.json"
SCHEMA_PATH = ROOT / "schemas" / "qwasar-ui.schema.json"


def _walk_component(node):
    yield node
    for child in node.get("children", []):
        yield from _walk_component(child)
    for children in node.get("slots", {}).values():
        for child in children:
            yield from _walk_component(child)


def test_qwasar_ui_manifest_and_schema_are_valid_json_documents():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["type"] == "object"
    assert manifest["schemaVersion"] == "1.0"
    assert manifest["apiVersion"] == "1.0"


def test_future_engine_adapters_are_reserved_not_claimed_as_supported():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    adapters = {item["id"]: item["status"] for item in manifest["engineAdapters"]}
    assert adapters["pygame"] == "current"
    assert adapters["love"] == "current"
    for engine in ("qt6", "lvgl", "web"):
        assert adapters[engine] == "planned"


def test_shell_has_buildable_header_footer_side_panels_and_media_overlay():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shell = manifest["shell"]
    assert shell["header"]["type"] == "layout.row"
    assert shell["footer"]["type"] == "layout.row"
    assert set(shell["homePanels"]) == {"left", "right"}
    assert shell["globalPanels"]["mediaPlayer"]["triggerAction"] == "panel.media.toggle"
    assert shell["globalPanels"]["mediaPlayer"]["enabled"] is True


def test_m_shortcut_is_a_semantic_action_not_a_hardcoded_engine_callback():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    matches = [item for item in manifest["keymap"]
               if item["input"] == "keyboard" and item["value"].lower() == "m"]
    assert len(matches) == 1
    assert matches[0]["actionId"] == "panel.media.toggle"
    assert any(action["id"] == "panel.media.toggle" for action in manifest["actions"])


def test_workspace_templates_and_toolbox_merge_are_declared():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    workspaces = {item["id"]: item for item in manifest["workspaces"]}
    assert set(workspaces) == {
        "start-session", "the-forge", "uplink", "media-vault",
        "rt-toolbox", "settings", "info-community", "end-node",
    }
    assert workspaces["rt-toolbox"]["template"] == "tool-workbench"
    assert workspaces["rt-toolbox"]["status"] == "migration-target"
    assert "hub_workshop" in workspaces["rt-toolbox"]["legacyRoutes"] or any(
        alias["oldId"] == "hub_workshop" and alias["newId"] == "rt-toolbox"
        for alias in manifest["legacyAliases"]
    )


def test_component_types_are_registered_and_component_ids_are_unique():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    registered = {item["id"] for item in manifest["componentRegistry"]}
    assert len(registered) == len(manifest["componentRegistry"])
    component_nodes = []
    component_nodes.extend(_walk_component(manifest["shell"]["header"]))
    component_nodes.extend(_walk_component(manifest["shell"]["footer"]))
    for region in manifest["shell"]["homePanels"].values():
        component_nodes.extend(_walk_component(region["content"]))
    for panel in manifest["shell"]["globalPanels"].values():
        component_nodes.extend(_walk_component(panel["content"]))
    for workspace in manifest["workspaces"]:
        component_nodes.extend(_walk_component(workspace["layout"]))
        for widget in workspace.get("widgets", []):
            component_nodes.extend(_walk_component(widget))
    for component in component_nodes:
        assert component["type"] in registered, (
            f"unregistered component type {component['type']} in {component['id']}"
        )
    ids = [component["id"] for component in component_nodes]
    assert len(ids) == len(set(ids)), "duplicate component node IDs"


def test_every_menu_action_reference_resolves_to_a_registered_action():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    known = {action["id"] for action in manifest["actions"]}

    def visit(entries):
        for entry in entries:
            if entry.get("actionId"):
                assert entry["actionId"] in known, entry["id"]
            visit(entry.get("children", []))

    for workspace in manifest["workspaces"]:
        visit(workspace.get("menu", []))


def test_rt_toolbox_is_the_only_diagnostics_destination_in_target_nexus_map():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    workspaces = {item["id"] for item in manifest["workspaces"]}
    assert "rt-toolbox" in workspaces
    assert "workshop" not in workspaces
    assert "diagnostics" not in workspaces
    aliases = {item["oldId"]: item["newId"] for item in manifest["legacyAliases"]}
    assert aliases["hub_workshop"] == "rt-toolbox"
    assert aliases["hub_toolbox"] == "rt-toolbox"
