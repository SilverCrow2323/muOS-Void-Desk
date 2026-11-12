from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from desk.qwasar.profile_resolver import (
    ProfileResolutionError,
    QwasarProfileResolver,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    for folder in ("schemas", "data/profiles"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for name in ("qwasar-ui.schema.json", "qwasar-profile.schema.json"):
        shutil.copy2(ROOT / "schemas" / name, tmp_path / "schemas" / name)
    shutil.copy2(
        ROOT / "data/qwasar_ui_manifest.json",
        tmp_path / "data/qwasar_ui_manifest.json",
    )
    profile_path = tmp_path / DEFAULT_PROFILE
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / DEFAULT_PROFILE, profile_path)
    shutil.copy2(
        ROOT / "data/profiles/voiddesk-desktop-default.qprofile.json",
        tmp_path / "data/profiles/voiddesk-desktop-default.qprofile.json",
    )
    return tmp_path, profile_path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _resolver(tmp_path: Path) -> tuple[QwasarProfileResolver, Path]:
    root, profile = _fixture(tmp_path)
    return QwasarProfileResolver(root), profile


def test_bundled_h700_profile_resolves_without_mutating_source_files(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    manifest_before = (tmp_path / "data/qwasar_ui_manifest.json").read_bytes()
    profile_before = profile_path.read_bytes()

    composition = resolver.resolve()

    assert composition["profile"]["id"] == "qwasar.profile.voiddesk.handheld-default"
    assert len(composition["workspaces"]) == 8
    assert [item["id"] for item in composition["workspaces"]] == [
        "start-session", "the-forge", "uplink", "media-vault",
        "rt-toolbox", "settings", "info-community", "end-node",
    ]
    toolbox = next(item for item in composition["workspaces"] if item["id"] == "rt-toolbox")
    assert [item["id"] for item in toolbox["sections"]] == [
        "toolbox.everyday", "toolbox.files-storage",
        "toolbox.system-health", "toolbox.developer-terminal",
    ]
    assert composition["globalPanels"]["mediaPlayer"]["enabled"] is True
    assert composition["theme"]["visualStyle"] == "megastructure"
    assert composition["theme"]["palette"] == "cyberpunk"
    assert (tmp_path / "data/qwasar_ui_manifest.json").read_bytes() == manifest_before
    assert profile_path.read_bytes() == profile_before


def test_resolver_applies_workspace_section_menu_and_panel_overrides(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["workspaceOrder"] = [
        "rt-toolbox", "start-session", "the-forge", "uplink",
        "media-vault", "settings", "info-community", "end-node",
    ]
    profile["workspaceOverrides"][0]["sections"][0]["visible"] = False
    profile["workspaceOverrides"][0]["menuOrder"] = [
        "toolbox.switchboard", "toolbox.inspector",
        "toolbox.installed-modules",
    ]
    profile["workspaceOverrides"][0]["hiddenMenuEntries"] = ["toolbox.inspector"]
    profile["shell"]["globalPanels"]["mediaPlayer"]["enabled"] = False
    _write(profile_path, profile)

    composition = resolver.resolve()
    assert composition["workspaces"][0]["id"] == "rt-toolbox"
    toolbox = composition["workspaces"][0]
    assert toolbox["sections"][0]["visible"] is False
    assert [item["id"] for item in toolbox["menu"]] == [
        "toolbox.switchboard", "toolbox.inspector", "toolbox.installed-modules",
    ]
    inspector = next(item for item in toolbox["menu"] if item["id"] == "toolbox.inspector")
    assert inspector["visible"] is False
    assert composition["globalPanels"]["mediaPlayer"]["enabled"] is False


def test_resolver_preserves_manifest_menu_metadata(tmp_path: Path):
    resolver, _ = _resolver(tmp_path)

    composition = resolver.resolve()
    session = next(
        item for item in composition["workspaces"]
        if item["id"] == "start-session"
    )
    install_desktop = next(
        item for item in session["menu"]
        if item["id"] == "session.install-xfce"
    )
    assert install_desktop["icon"] == "download"
    assert install_desktop["confirmation"] == "host-required"

    toolbox = next(
        item for item in composition["workspaces"]
        if item["id"] == "rt-toolbox"
    )
    developer = next(
        item for item in toolbox["sections"]
        if item["id"] == "toolbox.developer-terminal"
    )
    shell = next(
        item for item in developer["menu"]
        if item["id"] == "toolbox.shell-open"
    )
    assert shell["capabilities"] == ["device.shell.pty"]


def test_disabled_and_hidden_workspace_states_are_not_collapsed(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["workspaceOverrides"].append({
        "id": "uplink", "enabled": False, "visible": True,
    })
    profile["workspaceOverrides"].append({
        "id": "media-vault", "enabled": True, "visible": False,
    })
    _write(profile_path, profile)

    composition = resolver.resolve()
    uplink = next(item for item in composition["workspaces"] if item["id"] == "uplink")
    media = next(item for item in composition["workspaces"] if item["id"] == "media-vault")
    assert uplink["enabled"] is False and uplink["visible"] is True
    assert media["enabled"] is True and media["visible"] is False


def test_resolver_merges_module_contribution_and_keymap_states(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["moduleStates"] = [{
        "moduleId": "community.network.wifi-overview",
        "enabled": False,
    }]
    profile["contributionStates"] = [{
        "contributionId": "wifi-overview.tile",
        "state": "hidden",
    }]
    profile["bindings"][0]["value"] = "p"
    _write(profile_path, profile)

    composition = resolver.resolve()
    assert composition["modules"]["community.network.wifi-overview"] is False
    assert composition["contributions"]["wifi-overview.tile"]["state"] == "hidden"
    media_binding = next(
        item for item in composition["keymap"]
        if item["actionId"] == "panel.media.toggle"
        and item["input"] == "keyboard"
    )
    assert media_binding["value"] == "p"


def test_unknown_workspace_section_menu_action_and_panel_references_are_rejected(
    tmp_path: Path,
):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["workspaceOrder"][0] = "workspace.not-registered"
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="unknown workspaces"):
        resolver.resolve(fallback_to_default=False)

    profile = _read(ROOT / DEFAULT_PROFILE)
    profile["workspaceOverrides"][0]["sections"][0]["id"] = "section.unknown"
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="unknown section"):
        resolver.resolve(fallback_to_default=False)

    profile = _read(ROOT / DEFAULT_PROFILE)
    profile["workspaceOverrides"][0]["hiddenMenuEntries"] = ["menu.not-registered"]
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="unknown entries"):
        resolver.resolve(fallback_to_default=False)

    profile = _read(ROOT / DEFAULT_PROFILE)
    profile["shell"]["globalPanels"]["panel.unknown"] = {"enabled": True}
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="unknown global panels"):
        resolver.resolve(fallback_to_default=False)


def test_imported_profile_cannot_hide_end_node_or_disable_shell(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["workspaceOverrides"].append({
        "id": "end-node", "enabled": True, "visible": False,
    })
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="protected workspace"):
        resolver.resolve(fallback_to_default=False)

    profile = _read(ROOT / DEFAULT_PROFILE)
    profile["shell"]["header"]["enabled"] = False
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="protected shell"):
        resolver.resolve(fallback_to_default=False)


def test_invalid_selected_profile_falls_back_to_bundled_default(tmp_path: Path):
    resolver, _ = _resolver(tmp_path)
    custom = tmp_path / "data/profiles/custom.qprofile.json"
    custom.write_text("{ invalid", encoding="utf-8")

    composition = resolver.resolve(custom)

    assert composition["profile"]["id"] == "qwasar.profile.voiddesk.handheld-default"
    assert any("Selected profile was rejected" in warning for warning in composition["warnings"])
    assert composition["warnings"]


def test_missing_custom_profile_falls_back_but_default_corruption_is_fatal(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    missing = tmp_path / "data/profiles/missing.qprofile.json"
    composition = resolver.resolve(missing)
    assert composition["profile"]["id"] == "qwasar.profile.voiddesk.handheld-default"

    profile_path.write_text("{ broken default", encoding="utf-8")
    with pytest.raises(ProfileResolutionError, match="cannot read"):
        resolver.resolve()


def test_portable_settings_are_preserved_and_sensitive_keys_are_rejected(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["settings"] = {"panel": {"density": "compact"}, "toolbox": {"columns": 2}}
    _write(profile_path, profile)

    composition = resolver.resolve()
    assert composition["settings"] == profile["settings"]

    profile["settings"]["cloud"] = {"apiToken": "must-not-be-exported"}
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError):
        resolver.resolve(fallback_to_default=False)


def test_platform_compatibility_selects_the_matching_safe_default(tmp_path: Path):
    resolver, h700_profile = _resolver(tmp_path)
    with pytest.raises(ProfileResolutionError, match="not compatible"):
        resolver.resolve(
            h700_profile,
            fallback_to_default=False,
            target_platform="desktop",
        )

    desktop_default = tmp_path / "data/profiles/voiddesk-desktop-default.qprofile.json"
    desktop_resolver = QwasarProfileResolver(
        tmp_path,
        default_profile_path="data/profiles/voiddesk-desktop-default.qprofile.json",
    )
    composition = desktop_resolver.resolve(
        h700_profile,
        target_platform="desktop",
    )
    assert composition["profile"]["id"] == "qwasar.profile.voiddesk.desktop-default"
    assert any("Selected profile was rejected" in warning for warning in composition["warnings"])


def test_profile_minimum_ui_api_is_enforced(tmp_path: Path):
    resolver, profile_path = _resolver(tmp_path)
    profile = _read(profile_path)
    profile["compatibility"]["minimumUiApi"] = "99.0"
    _write(profile_path, profile)
    with pytest.raises(ProfileResolutionError, match="requires UI API"):
        resolver.resolve(fallback_to_default=False)
