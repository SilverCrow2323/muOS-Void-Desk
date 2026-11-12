from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.qwasar_switchboard import (
    ConcurrentProfileUpdate,
    QwasarSwitchboard,
    SwitchboardError,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    for folder in ("schemas", "data/profiles", "data/profiles/templates"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for name in ("qwasar-ui.schema.json", "qwasar-profile.schema.json"):
        shutil.copy2(ROOT / "schemas" / name, tmp_path / "schemas" / name)
    shutil.copy2(ROOT / "data/qwasar_ui_manifest.json", tmp_path / "data/qwasar_ui_manifest.json")
    profile_path = tmp_path / DEFAULT_PROFILE
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / DEFAULT_PROFILE, profile_path)
    shutil.copy2(
        ROOT / "data/profiles/templates/voiddesk-handheld-default.qprofile.json",
        tmp_path / "data/profiles/templates/voiddesk-handheld-default.qprofile.json",
    )
    return tmp_path, profile_path


def _switchboard(tmp_path: Path) -> tuple[QwasarSwitchboard, Path]:
    root, profile = _fixture(tmp_path)
    return QwasarSwitchboard(root, profile), profile


def _profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_preview_reads_effective_state_without_mutating_profile(tmp_path: Path):
    switchboard, profile_path = _switchboard(tmp_path)
    before = profile_path.read_bytes()
    preview = switchboard.preview()

    assert preview["profileId"] == "qwasar.profile.voiddesk.handheld-default"
    assert len(preview["workspaces"]) == 8
    assert preview["globalPanels"]["mediaPlayer"] is True
    assert profile_path.read_bytes() == before


def test_workspace_disabled_and_hidden_have_distinct_semantics(tmp_path: Path):
    switchboard, profile_path = _switchboard(tmp_path)

    switchboard.set_workspace_state("rt-toolbox", "disabled")
    state = next(item for item in switchboard.preview()["workspaces"] if item["id"] == "rt-toolbox")
    assert state["enabled"] is False
    assert state["visible"] is True

    switchboard.set_workspace_state("rt-toolbox", "hidden")
    state = next(item for item in switchboard.preview()["workspaces"] if item["id"] == "rt-toolbox")
    assert state["enabled"] is True
    assert state["visible"] is False
    assert _profile(profile_path)["workspaceOverrides"][0]["visible"] is True


def test_end_node_cannot_be_disabled_or_hidden(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    original = switchboard.profile.copy()

    with pytest.raises(SwitchboardError, match="protected"):
        switchboard.set_workspace_state("end-node", "disabled")
    with pytest.raises(SwitchboardError, match="protected"):
        switchboard.set_workspace_state("end-node", "hidden")

    assert switchboard.profile == original


def test_sections_modules_contributions_and_global_panels_are_profile_only(tmp_path: Path):
    switchboard, profile_path = _switchboard(tmp_path)
    switchboard.set_section_state("rt-toolbox", "toolbox.files-storage", "hidden")
    switchboard.set_module_enabled("community.network.example", False)
    switchboard.set_contribution_state("community.network.example.tile", "disabled")
    switchboard.set_global_panel_enabled("mediaPlayer", False)

    preview = switchboard.preview()
    toolbox = next(item for item in preview["workspaces"] if item["id"] == "rt-toolbox")
    files = next(item for item in toolbox["sections"] if item["id"] == "toolbox.files-storage")
    assert files["enabled"] is True and files["visible"] is False
    assert preview["modules"]["community.network.example"] is False
    assert preview["contributions"]["community.network.example.tile"] == "disabled"
    assert preview["globalPanels"]["mediaPlayer"] is False

    # Nothing reaches disk until the explicit save call.
    assert _profile(profile_path)["moduleStates"] == []


def test_reorder_workspace_and_sections_preserves_all_registered_entries(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    switchboard.move_workspace("rt-toolbox", 0)
    assert switchboard.profile["workspaceOrder"][0] == "rt-toolbox"
    assert len(switchboard.profile["workspaceOrder"]) == 8

    switchboard.move_section("rt-toolbox", "toolbox.developer-terminal", 0)
    toolbox = next(item for item in switchboard.preview()["workspaces"] if item["id"] == "rt-toolbox")
    assert toolbox["sections"][0]["id"] == "toolbox.developer-terminal"


def test_unknown_targets_are_rejected_without_partial_change(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    original = switchboard.profile.copy()

    with pytest.raises(SwitchboardError, match="unknown workspace"):
        switchboard.set_workspace_state("workspace.unknown", "hidden")
    with pytest.raises(SwitchboardError, match="unknown section"):
        switchboard.set_section_state("rt-toolbox", "section.unknown", "hidden")
    with pytest.raises(SwitchboardError, match="unknown global panel"):
        switchboard.set_global_panel_enabled("panel.unknown", False)

    assert switchboard.profile == original


def test_save_is_atomic_creates_backup_and_can_be_reloaded(tmp_path: Path):
    switchboard, profile_path = _switchboard(tmp_path)
    original = profile_path.read_bytes()
    switchboard.set_workspace_state("rt-toolbox", "disabled")
    saved = switchboard.save()

    assert saved == profile_path
    assert profile_path.exists()
    assert Path(str(profile_path) + ".bak").read_bytes() == original
    assert _profile(profile_path)["workspaceOverrides"][0]["enabled"] is False
    reloaded = QwasarSwitchboard(tmp_path, profile_path)
    assert next(
        item for item in reloaded.preview()["workspaces"] if item["id"] == "rt-toolbox"
    )["enabled"] is False


def test_save_refuses_to_overwrite_a_concurrent_profile_edit(tmp_path: Path):
    root, profile_path = _fixture(tmp_path)
    first = QwasarSwitchboard(root, profile_path)
    second = QwasarSwitchboard(root, profile_path)

    first.set_workspace_state("rt-toolbox", "disabled")
    first.save()
    second.set_workspace_state("uplink", "hidden")

    with pytest.raises(ConcurrentProfileUpdate, match="changed on disk"):
        second.save()


def test_reset_profile_restores_bundled_default_in_memory(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    switchboard.set_workspace_state("rt-toolbox", "hidden")
    switchboard.reset_profile()

    toolbox = next(item for item in switchboard.preview()["workspaces"] if item["id"] == "rt-toolbox")
    assert toolbox["enabled"] is True
    assert toolbox["visible"] is True

def test_imported_profile_cannot_disable_recovery_workspace(tmp_path: Path):
    root, profile_path = _fixture(tmp_path)
    profile = _profile(profile_path)
    profile["workspaceOverrides"].append({
        "id": "end-node",
        "enabled": False,
        "visible": False,
    })
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SwitchboardError, match="protected workspace"):
        QwasarSwitchboard(root, profile_path)


def test_imported_profile_cannot_disable_the_central_shell(tmp_path: Path):
    root, profile_path = _fixture(tmp_path)
    profile = _profile(profile_path)
    profile["shell"]["header"]["enabled"] = False
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SwitchboardError, match="protected shell region"):
        QwasarSwitchboard(root, profile_path)

def test_reset_command_can_recover_a_corrupt_profile_and_back_it_up(tmp_path: Path):
    root, profile_path = _fixture(tmp_path)
    profile_path.write_text("{ broken json", encoding="utf-8")

    restored = QwasarSwitchboard.restore_default(root, profile_path)

    assert restored == profile_path
    assert Path(str(profile_path) + ".bak").read_text(encoding="utf-8") == "{ broken json"
    recovered = QwasarSwitchboard(root, profile_path)
    assert recovered.preview()["profileId"] == "qwasar.profile.voiddesk.handheld-default"

def test_menu_entries_can_be_hidden_shown_and_reordered_in_workspace_or_section(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    switchboard.set_menu_entry_visibility("rt-toolbox", "toolbox.inspector", False)
    workspace_menu = next(
        item for item in switchboard.preview()["workspaces"]
        if item["id"] == "rt-toolbox"
    )["menu"]
    inspector = next(item for item in workspace_menu if item["id"] == "toolbox.inspector")
    assert inspector["visible"] is False

    switchboard.set_menu_entry_visibility("rt-toolbox", "toolbox.inspector", True)
    workspace_menu = next(
        item for item in switchboard.preview()["workspaces"]
        if item["id"] == "rt-toolbox"
    )["menu"]
    inspector = next(item for item in workspace_menu if item["id"] == "toolbox.inspector")
    assert inspector["visible"] is True

    switchboard.move_menu_entry(
        "rt-toolbox", "toolbox.backup", 0, section_id="toolbox.files-storage"
    )
    toolbox = next(
        item for item in switchboard.preview()["workspaces"]
        if item["id"] == "rt-toolbox"
    )
    files = next(
        item for item in toolbox["sections"]
        if item["id"] == "toolbox.files-storage"
    )
    assert files["menu"][0]["id"] == "toolbox.backup"


def test_menu_entries_inside_end_node_cannot_be_hidden(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    with pytest.raises(SwitchboardError, match="protected"):
        switchboard.set_menu_entry_visibility("end-node", "exit.poweroff", False)


def test_switchboard_rejects_unknown_menu_entry_ids(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    with pytest.raises(SwitchboardError, match="unknown menu entry"):
        switchboard.set_menu_entry_visibility("rt-toolbox", "menu.not-registered", False)

def test_imported_profile_cannot_hide_end_node_menu_actions(tmp_path: Path):
    root, profile_path = _fixture(tmp_path)
    profile = _profile(profile_path)
    profile["workspaceOverrides"].append({
        "id": "end-node",
        "hiddenMenuEntries": ["exit.poweroff"],
    })
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SwitchboardError, match="protected menu entry"):
        QwasarSwitchboard(root, profile_path)


def test_switchboard_cannot_disable_protected_module_identifiers(tmp_path: Path):
    switchboard, _ = _switchboard(tmp_path)
    with pytest.raises(SwitchboardError, match="protected"):
        switchboard.set_module_enabled("end-node.recovery", False)
