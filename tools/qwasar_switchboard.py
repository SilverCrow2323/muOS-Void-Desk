#!/usr/bin/env python3
"""Transactional, profile-only controls for QWASAR workspace composition.

This is not a package manager. It never installs/uninstalls modules, stops
services, launches commands or changes the protected shell/recovery surfaces.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

try:
    import jsonschema
except ImportError:  # pragma: no cover - covered by CLI error path
    jsonschema = None  # type: ignore[assignment]



DEFAULT_MANIFEST = "data/qwasar_ui_manifest.json"
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"
DEFAULT_PROFILE_TEMPLATE = "data/profiles/templates/voiddesk-handheld-default.qprofile.json"
DEFAULT_PROFILE_SCHEMA = "schemas/qwasar-profile.schema.json"
DEFAULT_UI_SCHEMA = "schemas/qwasar-ui.schema.json"
PROFILE_STATES = {"enabled", "disabled", "hidden"}
PROFILE_STATE_KEYS = {
    "enabled": (True, True),
    "disabled": (False, True),
    "hidden": (True, False),
}


class SwitchboardError(RuntimeError):
    """A requested profile operation is invalid or unsafe."""


class ConcurrentProfileUpdate(SwitchboardError):
    """The profile changed on disk after this Switchboard instance loaded it."""


def _menu_ids(entries: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for entry in entries:
        found.add(entry["id"])
        found.update(_menu_ids(entry.get("children", [])))
    return found


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SwitchboardError(f"{label} not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SwitchboardError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SwitchboardError(f"{label} must be a JSON object: {path}")
    return data


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SwitchboardError(f"cannot fingerprint profile {path}: {exc}") from exc


def _atomic_write_profile(path: Path, text: str) -> None:
    """Write in the target directory, fsync, retain a backup and replace atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            shutil.copy2(path, str(path) + ".bak")
        os.replace(temporary, path)
        try:
            directory_fd = os.open(
                path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Some removable/FAT-like filesystems do not support directory fsync.
            # The file itself has already been flushed before the atomic rename.
            pass
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


class QwasarSwitchboard:
    """Edit a QWASAR .qprofile in memory and persist it atomically on request.

    A profile update is validated before it replaces the in-memory snapshot.
    save() then verifies that the source file has not changed since load and
    commits the complete profile with a same-directory atomic replacement.
    """

    def __init__(
        self,
        root: Path,
        profile_path: str | Path,
        manifest_path: str = DEFAULT_MANIFEST,
    ) -> None:
        if jsonschema is None:
            raise SwitchboardError(
                "QWASAR Switchboard requires jsonschema "
                "(install: python3 -m pip install 'jsonschema>=4.23,<5')"
            )
        self.root = Path(root).resolve()
        self.manifest_path = self._resolve(manifest_path)
        self.profile_path = self._resolve(profile_path)
        self.manifest = _read_json(self.manifest_path, "QWASAR UI manifest")
        self.profile = _read_json(self.profile_path, "QWASAR profile")
        self._validate_ui_manifest()
        self.protected_areas = set(
            self.manifest["featureManagement"]["protectedAreas"]
        )
        self._validate_profile(self.profile)
        self._loaded_digest = _digest(self.profile_path)

    @classmethod
    def restore_default(
        cls,
        root: Path,
        target_profile_path: str | Path,
        manifest_path: str = DEFAULT_MANIFEST,
        default_profile_path: str = DEFAULT_PROFILE,
    ) -> Path:
        """Restore from the trusted bundled default, even if the target is corrupt."""
        switchboard = cls(root, default_profile_path, manifest_path)
        target = switchboard._resolve(target_profile_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        switchboard.profile_path = target
        switchboard._loaded_digest = _digest(target) if target.exists() else None
        return switchboard.save()

    def _resolve(self, path: str | Path) -> Path:
        value = Path(path).expanduser()
        return value.resolve() if value.is_absolute() else (self.root / value).resolve()

    def _validate_ui_manifest(self) -> None:
        schema_path = self._resolve(DEFAULT_UI_SCHEMA)
        schema = _read_json(schema_path, "QWASAR UI schema")
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker()
            ).validate(self.manifest)
        except jsonschema.SchemaError as exc:
            raise SwitchboardError(f"invalid QWASAR UI schema: {exc.message}") from exc
        except jsonschema.ValidationError as exc:
            where = "/".join(str(item) for item in exc.absolute_path) or "$"
            raise SwitchboardError(
                f"invalid QWASAR UI manifest at {where}: {exc.message}"
            ) from exc

    def _validate_profile(self, profile: dict[str, Any]) -> None:
        schema = _read_json(self._resolve(DEFAULT_PROFILE_SCHEMA), "profile schema")
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker()
            ).validate(profile)
        except jsonschema.SchemaError as exc:
            raise SwitchboardError(f"invalid QWASAR profile schema: {exc.message}") from exc
        except jsonschema.ValidationError as exc:
            where = "/".join(str(item) for item in exc.absolute_path) or "$"
            raise SwitchboardError(
                f"profile schema validation failed at {where}: {exc.message}"
            ) from exc

        workspace_map = {
            item["id"]: item for item in self.manifest["workspaces"]
        }
        known_actions = {item["id"] for item in self.manifest["actions"]}
        for workspace_id in profile.get("workspaceOrder", []):
            if workspace_id not in workspace_map:
                raise SwitchboardError(
                    f"profile references unknown workspace in workspaceOrder: {workspace_id}"
                )

        seen_workspaces: set[str] = set()
        for override in profile.get("workspaceOverrides", []):
            workspace_id = override["id"]
            if workspace_id not in workspace_map:
                raise SwitchboardError(
                    f"profile references unknown workspace override: {workspace_id}"
                )
            if workspace_id in seen_workspaces:
                raise SwitchboardError(
                    f"profile has duplicate workspace override: {workspace_id}"
                )
            seen_workspaces.add(workspace_id)
            known_sections = {
                item["id"]
                for item in workspace_map[workspace_id].get("sections", [])
            }
            base_workspace = workspace_map[workspace_id]
            workspace_menu = base_workspace.get("menu", [])
            workspace_menu_ids = {item["id"] for item in workspace_menu}
            workspace_menu_all_ids = _menu_ids(workspace_menu)
            if not set(override.get("menuOrder", [])) <= workspace_menu_ids:
                raise SwitchboardError(f"profile menuOrder references unknown workspace menu entry in {workspace_id}")
            if not set(override.get("hiddenMenuEntries", [])) <= workspace_menu_all_ids:
                raise SwitchboardError(f"profile hiddenMenuEntries references unknown workspace menu entry in {workspace_id}")

            seen_sections: set[str] = set()
            base_sections = {item["id"]: item for item in base_workspace.get("sections", [])}
            for section in override.get("sections", []):
                section_id = section["id"]
                if section_id not in known_sections:
                    raise SwitchboardError(
                        f"profile references unknown section {section_id} in {workspace_id}"
                    )
                if section_id in seen_sections:
                    raise SwitchboardError(
                        f"profile has duplicate section override {section_id} in {workspace_id}"
                    )
                seen_sections.add(section_id)
                base_menu = base_sections[section_id].get("menu", [])
                direct_ids = {item["id"] for item in base_menu}
                all_ids = _menu_ids(base_menu)
                if not set(section.get("menuOrder", [])) <= direct_ids:
                    raise SwitchboardError(f"profile menuOrder references unknown entry in section {section_id}")
                if not set(section.get("hiddenMenuEntries", [])) <= all_ids:
                    raise SwitchboardError(f"profile hiddenMenuEntries references unknown entry in section {section_id}")

        for binding in profile.get("bindings", []):
            if binding["actionId"] not in known_actions:
                raise SwitchboardError(
                    f"profile binding references unknown action: {binding['actionId']}"
                )

        known_global_panels = set(self.manifest["shell"]["globalPanels"])
        unknown_global_panels = set(profile["shell"].get("globalPanels", {})) - known_global_panels
        if unknown_global_panels:
            raise SwitchboardError(
                "profile references unknown global panels: "
                + ", ".join(sorted(unknown_global_panels))
            )

        # Imported profiles are held to the same safety floor as UI edits.
        # A crafted .qprofile must not be able to hide recovery or disable
        # the central shell before the user opens Switchboard.
        for region_name in ("header", "footer"):
            if profile["shell"][region_name].get("enabled") is False:
                raise SwitchboardError(
                    f"protected shell region cannot be disabled: {region_name}"
                )
        for override in profile.get("workspaceOverrides", []):
            workspace_id = override["id"]
            if self._is_protected(workspace_id) and (
                override.get("enabled") is False or override.get("visible") is False
            ):
                raise SwitchboardError(
                    f"protected workspace cannot be disabled or hidden: {workspace_id}"
                )
            base_workspace = workspace_map[workspace_id]
            base_sections = {
                item["id"]: item for item in base_workspace.get("sections", [])
            }
            for entry_id in override.get("hiddenMenuEntries", []):
                entry = self._find_menu_entry(base_workspace.get("menu", []), entry_id)
                if (
                    self._is_protected(workspace_id)
                    or self._is_protected(entry_id)
                    or (entry and self._is_protected(entry.get("actionId", "")))
                ):
                    raise SwitchboardError(
                        f"profile cannot hide protected menu entry {entry_id} in {workspace_id}"
                    )
            for section in override.get("sections", []):
                section_id = section["id"]
                if self._is_protected(section_id) and (
                    section.get("enabled") is False or section.get("visible") is False
                ):
                    raise SwitchboardError(
                        f"protected section cannot be disabled or hidden: {section_id}"
                    )
                base_menu = base_sections[section_id].get("menu", [])
                for entry_id in section.get("hiddenMenuEntries", []):
                    entry = self._find_menu_entry(base_menu, entry_id)
                    if (
                        self._is_protected(workspace_id)
                        or self._is_protected(section_id)
                        or self._is_protected(entry_id)
                        or (entry and self._is_protected(entry.get("actionId", "")))
                    ):
                        raise SwitchboardError(
                            f"profile cannot hide protected menu entry {entry_id} in section {section_id}"
                        )
                for contribution in section.get("contributions", []):
                    contribution_id = contribution["contributionId"]
                    if self._is_protected(contribution_id) and contribution["state"] != "enabled":
                        raise SwitchboardError(
                            f"protected contribution cannot be disabled or hidden: {contribution_id}"
                        )
            for contribution in override.get("contributions", []):
                contribution_id = contribution["contributionId"]
                if self._is_protected(contribution_id) and contribution["state"] != "enabled":
                    raise SwitchboardError(
                        f"protected contribution cannot be disabled or hidden: {contribution_id}"
                    )
        for module in profile.get("moduleStates", []):
            if self._is_protected(module["moduleId"]) and module["enabled"] is False:
                raise SwitchboardError(
                    f"profile cannot disable protected module {module['moduleId']}"
                )
        for contribution in profile.get("contributionStates", []):
            contribution_id = contribution["contributionId"]
            if self._is_protected(contribution_id) and contribution["state"] != "enabled":
                raise SwitchboardError(
                    f"protected contribution cannot be disabled or hidden: {contribution_id}"
                )
        for panel_id, panel_override in profile["shell"].get("globalPanels", {}).items():
            if self._is_protected(panel_id) and panel_override.get("enabled") is False:
                raise SwitchboardError(
                    f"profile cannot disable protected global panel {panel_id}"
                )

    def _edit(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        candidate = copy.deepcopy(self.profile)
        mutator(candidate)
        self._validate_profile(candidate)
        self.profile = candidate
        return copy.deepcopy(self.profile)

    def _workspace(self, workspace_id: str) -> dict[str, Any]:
        for item in self.manifest["workspaces"]:
            if item["id"] == workspace_id:
                return item
        raise SwitchboardError(f"unknown workspace: {workspace_id}")

    def _is_protected(self, item_id: str) -> bool:
        return any(
            item_id == protected or item_id.startswith(protected + ".")
            for protected in self.protected_areas
        )

    def _ensure_changeable(self, item_id: str, operation: str) -> None:
        if operation in {"disabled", "hidden"} and self._is_protected(item_id):
            raise SwitchboardError(
                f"{item_id} is protected and cannot be {operation}"
            )

    @staticmethod
    def _workspace_override(profile: dict[str, Any], workspace_id: str) -> dict[str, Any]:
        overrides = profile.setdefault("workspaceOverrides", [])
        for override in overrides:
            if override["id"] == workspace_id:
                return override
        override = {"id": workspace_id}
        overrides.append(override)
        return override

    def _section_override(
        self, profile: dict[str, Any], workspace_id: str, section_id: str
    ) -> dict[str, Any]:
        workspace_override = self._workspace_override(profile, workspace_id)
        sections = workspace_override.setdefault("sections", [])
        for section in sections:
            if section["id"] == section_id:
                return section
        section = {"id": section_id}
        sections.append(section)
        return section

    def set_workspace_state(self, workspace_id: str, state: str) -> dict[str, Any]:
        self._workspace(workspace_id)
        if state not in PROFILE_STATES:
            raise SwitchboardError(f"unsupported workspace state: {state}")
        self._ensure_changeable(workspace_id, state)

        def mutate(profile: dict[str, Any]) -> None:
            override = self._workspace_override(profile, workspace_id)
            override["enabled"], override["visible"] = PROFILE_STATE_KEYS[state]

        return self._edit(mutate)

    def set_section_state(
        self, workspace_id: str, section_id: str, state: str
    ) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        known = {item["id"] for item in workspace.get("sections", [])}
        if section_id not in known:
            raise SwitchboardError(
                f"unknown section {section_id} in workspace {workspace_id}"
            )
        if state not in PROFILE_STATES:
            raise SwitchboardError(f"unsupported section state: {state}")
        self._ensure_changeable(section_id, state)

        def mutate(profile: dict[str, Any]) -> None:
            override = self._section_override(profile, workspace_id, section_id)
            override["enabled"], override["visible"] = PROFILE_STATE_KEYS[state]

        return self._edit(mutate)

    def set_module_enabled(self, module_id: str, enabled: bool) -> dict[str, Any]:
        if not isinstance(enabled, bool):
            raise SwitchboardError("module enabled state must be a boolean")
        if not module_id or len(module_id) > 96:
            raise SwitchboardError("module ID must contain 1..96 characters")
        if not enabled:
            self._ensure_changeable(module_id, "disabled")

        def mutate(profile: dict[str, Any]) -> None:
            states = profile.setdefault("moduleStates", [])
            entry = next((item for item in states if item["moduleId"] == module_id), None)
            if entry is None:
                states.append({"moduleId": module_id, "enabled": enabled})
            else:
                entry["enabled"] = enabled

        return self._edit(mutate)

    def set_contribution_state(
        self, contribution_id: str, state: str
    ) -> dict[str, Any]:
        if state not in PROFILE_STATES:
            raise SwitchboardError(f"unsupported contribution state: {state}")
        self._ensure_changeable(contribution_id, state)

        def mutate(profile: dict[str, Any]) -> None:
            states = profile.setdefault("contributionStates", [])
            entry = next(
                (item for item in states if item["contributionId"] == contribution_id),
                None,
            )
            if entry is None:
                states.append({"contributionId": contribution_id, "state": state})
            else:
                entry["state"] = state

        return self._edit(mutate)

    def _menu_scope(
        self, workspace_id: str, section_id: str | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        workspace = self._workspace(workspace_id)
        if section_id is None:
            return workspace.get("menu", []), None
        section = next(
            (item for item in workspace.get("sections", []) if item["id"] == section_id),
            None,
        )
        if section is None:
            raise SwitchboardError(
                f"unknown section {section_id} in workspace {workspace_id}"
            )
        return section.get("menu", []), {"sectionId": section_id}

    @staticmethod
    def _find_menu_entry(
        entries: list[dict[str, Any]], entry_id: str
    ) -> dict[str, Any] | None:
        for entry in entries:
            if entry["id"] == entry_id:
                return entry
            found = QwasarSwitchboard._find_menu_entry(
                entry.get("children", []), entry_id
            )
            if found is not None:
                return found
        return None

    def set_menu_entry_visibility(
        self,
        workspace_id: str,
        entry_id: str,
        visible: bool,
        section_id: str | None = None,
    ) -> dict[str, Any]:
        entries, _ = self._menu_scope(workspace_id, section_id)
        entry = self._find_menu_entry(entries, entry_id)
        if entry is None:
            raise SwitchboardError(f"unknown menu entry {entry_id} in {workspace_id}")
        if not isinstance(visible, bool):
            raise SwitchboardError("menu visibility must be a boolean")
        if not visible:
            self._ensure_changeable(workspace_id, "hidden")
            self._ensure_changeable(entry_id, "hidden")
            if entry.get("actionId"):
                self._ensure_changeable(entry["actionId"], "hidden")

        def mutate(profile: dict[str, Any]) -> None:
            if section_id is None:
                override = self._workspace_override(profile, workspace_id)
            else:
                override = self._section_override(profile, workspace_id, section_id)
            hidden = override.setdefault("hiddenMenuEntries", [])
            if visible and entry_id in hidden:
                hidden.remove(entry_id)
            elif not visible and entry_id not in hidden:
                hidden.append(entry_id)

        return self._edit(mutate)

    def move_menu_entry(
        self,
        workspace_id: str,
        entry_id: str,
        new_index: int,
        section_id: str | None = None,
    ) -> dict[str, Any]:
        entries, _ = self._menu_scope(workspace_id, section_id)
        entry_ids = [item["id"] for item in entries]
        if entry_id not in entry_ids:
            raise SwitchboardError(
                f"only registered top-level menu entries can be reordered: {entry_id}"
            )
        if not isinstance(new_index, int) or isinstance(new_index, bool):
            raise SwitchboardError("menu order index must be an integer")
        if not 0 <= new_index < len(entry_ids):
            raise SwitchboardError(f"menu order index must be 0..{len(entry_ids) - 1}")
        entry_ids.remove(entry_id)
        entry_ids.insert(new_index, entry_id)

        def mutate(profile: dict[str, Any]) -> None:
            if section_id is None:
                override = self._workspace_override(profile, workspace_id)
            else:
                override = self._section_override(profile, workspace_id, section_id)
            override["menuOrder"] = entry_ids

        return self._edit(mutate)

    def set_global_panel_enabled(
        self, panel_id: str, enabled: bool
    ) -> dict[str, Any]:
        panels = self.manifest["shell"]["globalPanels"]
        if panel_id not in panels:
            raise SwitchboardError(f"unknown global panel: {panel_id}")
        if not isinstance(enabled, bool):
            raise SwitchboardError("global panel enabled state must be a boolean")
        if not enabled:
            self._ensure_changeable(panel_id, "disabled")

        def mutate(profile: dict[str, Any]) -> None:
            overrides = profile["shell"].setdefault("globalPanels", {})
            overrides.setdefault(panel_id, {})["enabled"] = enabled

        return self._edit(mutate)

    def move_workspace(self, workspace_id: str, new_index: int) -> dict[str, Any]:
        self._workspace(workspace_id)
        order = self._complete_workspace_order()
        if not isinstance(new_index, int) or isinstance(new_index, bool):
            raise SwitchboardError("workspace order index must be an integer")
        if not 0 <= new_index < len(order):
            raise SwitchboardError(f"workspace order index must be 0..{len(order) - 1}")
        order.remove(workspace_id)
        order.insert(new_index, workspace_id)
        return self._edit(lambda profile: profile.__setitem__("workspaceOrder", order))

    def move_section(
        self, workspace_id: str, section_id: str, new_index: int
    ) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        sections = workspace.get("sections", [])
        section_ids = [item["id"] for item in sections]
        if section_id not in section_ids:
            raise SwitchboardError(
                f"unknown section {section_id} in workspace {workspace_id}"
            )
        if not isinstance(new_index, int) or isinstance(new_index, bool):
            raise SwitchboardError("section order index must be an integer")
        if not 0 <= new_index < len(section_ids):
            raise SwitchboardError(f"section order index must be 0..{len(section_ids) - 1}")
        section_ids.remove(section_id)
        section_ids.insert(new_index, section_id)

        def mutate(profile: dict[str, Any]) -> None:
            for order, item_id in enumerate(section_ids):
                self._section_override(profile, workspace_id, item_id)["order"] = order

        return self._edit(mutate)

    def _complete_workspace_order(self) -> list[str]:
        known = [item["id"] for item in self.manifest["workspaces"]]
        current = [item for item in self.profile.get("workspaceOrder", []) if item in known]
        current.extend(item for item in known if item not in current)
        return current

    def reset_profile(self, default_profile_path: str | Path = DEFAULT_PROFILE_TEMPLATE) -> dict[str, Any]:
        defaults = _read_json(self._resolve(default_profile_path), "default QWASAR profile")
        return self._edit(lambda profile: (profile.clear(), profile.update(copy.deepcopy(defaults))))

    @staticmethod
    def _preview_menu(
        entries: list[dict[str, Any]], override: dict[str, Any]
    ) -> list[dict[str, Any]]:
        order = override.get("menuOrder", [])
        rank = {entry_id: index for index, entry_id in enumerate(order)}
        hidden = set(override.get("hiddenMenuEntries", []))
        indexed = list(enumerate(entries))
        indexed.sort(
            key=lambda pair: (
                rank.get(pair[1]["id"], len(rank) + pair[0]),
                pair[0],
            )
        )
        result = []
        for _, entry in indexed:
            effective = copy.deepcopy(entry)
            effective["enabled"] = entry.get("enabled", True)
            effective["visible"] = (
                entry.get("visible", True) and entry["id"] not in hidden
            )
            effective["children"] = QwasarSwitchboard._preview_menu(
                entry.get("children", []), override
            )
            result.append(effective)
        return result

    def preview(self) -> dict[str, Any]:
        profile = self.profile
        workspace_order = self._complete_workspace_order()
        overrides = {
            item["id"]: item for item in profile.get("workspaceOverrides", [])
        }
        workspaces = []
        for index, workspace_id in enumerate(workspace_order):
            base = self._workspace(workspace_id)
            override = overrides.get(workspace_id, {})
            sections_override = {
                item["id"]: item for item in override.get("sections", [])
            }
            sections = []
            for section_index, section in enumerate(base.get("sections", [])):
                change = sections_override.get(section["id"], {})
                sections.append({
                    "id": section["id"],
                    "label": change.get("labelOverride", section["label"]),
                    "enabled": change.get("enabled", True),
                    "visible": change.get("visible", True),
                    "order": change.get("order", section_index),
                    "menu": self._preview_menu(section.get("menu", []), change),
                })
            sections.sort(key=lambda item: (item["order"], item["id"]))
            workspaces.append({
                "id": workspace_id,
                "label": override.get("labelOverride", base["label"]),
                "enabled": override.get("enabled", True),
                "visible": override.get("visible", True),
                "order": index,
                "menu": self._preview_menu(base.get("menu", []), override),
                "sections": sections,
            })
        global_panels = {}
        for panel_id, panel in self.manifest["shell"]["globalPanels"].items():
            value = profile["shell"].get("globalPanels", {}).get(panel_id, {})
            global_panels[panel_id] = value.get("enabled", panel["enabled"])
        return {
            "profileId": profile["id"],
            "workspaces": workspaces,
            "modules": {
                item["moduleId"]: item["enabled"]
                for item in profile.get("moduleStates", [])
            },
            "contributions": {
                item["contributionId"]: item["state"]
                for item in profile.get("contributionStates", [])
            },
            "globalPanels": global_panels,
        }

    def save(self) -> Path:
        """Validate and atomically persist; reject lost updates from another editor."""
        self._validate_profile(self.profile)
        serialized = json.dumps(
            self.profile, ensure_ascii=False, indent=2, sort_keys=False
        ) + "\n"
        lock_path = Path(str(self.profile_path) + ".lock")
        try:
            # A stable sibling lock survives the atomic replacement of the
            # profile inode, so concurrent Switchboard processes serialize.
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                current = _digest(self.profile_path) if self.profile_path.exists() else None
                if current != self._loaded_digest:
                    raise ConcurrentProfileUpdate(
                        "profile changed on disk since load; reload before saving: "
                        f"{self.profile_path}"
                    )
                _atomic_write_profile(self.profile_path, serialized)
                self._loaded_digest = _digest(self.profile_path)
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except ConcurrentProfileUpdate:
            raise
        except OSError as exc:
            raise SwitchboardError(f"cannot save profile {self.profile_path}: {exc}") from exc
        return self.profile_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--profile", help="profile file to edit; mutations require this explicit path")
    parser.add_argument("--save", action="store_true", help="persist changes atomically with a .bak backup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preview", help="show the effective profile without changing files")
    workspace = commands.add_parser("workspace-state")
    workspace.add_argument("workspace_id")
    workspace.add_argument("state", choices=sorted(PROFILE_STATES))
    section = commands.add_parser("section-state")
    section.add_argument("workspace_id")
    section.add_argument("section_id")
    section.add_argument("state", choices=sorted(PROFILE_STATES))
    module = commands.add_parser("module-state")
    module.add_argument("module_id")
    module.add_argument("state", choices=("enabled", "disabled"))
    contribution = commands.add_parser("contribution-state")
    contribution.add_argument("contribution_id")
    contribution.add_argument("state", choices=sorted(PROFILE_STATES))
    panel = commands.add_parser("panel")
    panel.add_argument("panel_id")
    panel.add_argument("state", choices=("enabled", "disabled"))
    menu = commands.add_parser("menu-visibility")
    menu.add_argument("workspace_id")
    menu.add_argument("entry_id")
    menu.add_argument("state", choices=("show", "hide"))
    menu.add_argument("--section", dest="section_id")
    move_menu = commands.add_parser("move-menu")
    move_menu.add_argument("workspace_id")
    move_menu.add_argument("entry_id")
    move_menu.add_argument("index", type=int)
    move_menu.add_argument("--section", dest="section_id")
    move_workspace = commands.add_parser("move-workspace")
    move_workspace.add_argument("workspace_id")
    move_workspace.add_argument("index", type=int)
    move_section = commands.add_parser("move-section")
    move_section.add_argument("workspace_id")
    move_section.add_argument("section_id")
    move_section.add_argument("index", type=int)
    commands.add_parser("reset-profile", help="restore the bundled default profile")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "preview" and not args.save:
        print("[QWASAR Switchboard] ERROR: mutating commands require --save", file=sys.stderr)
        return 2
    if args.save and not args.profile:
        print("[QWASAR Switchboard] ERROR: --save requires an explicit --profile path", file=sys.stderr)
        return 2
    profile_path = args.profile or DEFAULT_PROFILE
    try:
        if args.command == "reset-profile":
            saved = QwasarSwitchboard.restore_default(
                args.root, profile_path, args.manifest
            )
            print(f"[QWASAR Switchboard] OK — default profile restored atomically: {saved}")
            return 0
        switchboard = QwasarSwitchboard(args.root, profile_path, args.manifest)
        if args.command == "preview":
            print(json.dumps(switchboard.preview(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "workspace-state":
            switchboard.set_workspace_state(args.workspace_id, args.state)
        elif args.command == "section-state":
            switchboard.set_section_state(args.workspace_id, args.section_id, args.state)
        elif args.command == "module-state":
            switchboard.set_module_enabled(args.module_id, args.state == "enabled")
        elif args.command == "contribution-state":
            switchboard.set_contribution_state(args.contribution_id, args.state)
        elif args.command == "panel":
            switchboard.set_global_panel_enabled(args.panel_id, args.state == "enabled")
        elif args.command == "menu-visibility":
            switchboard.set_menu_entry_visibility(
                args.workspace_id, args.entry_id, args.state == "show",
                section_id=args.section_id,
            )
        elif args.command == "move-menu":
            switchboard.move_menu_entry(
                args.workspace_id, args.entry_id, args.index,
                section_id=args.section_id,
            )
        elif args.command == "move-workspace":
            switchboard.move_workspace(args.workspace_id, args.index)
        elif args.command == "move-section":
            switchboard.move_section(args.workspace_id, args.section_id, args.index)
        saved = switchboard.save()
        print(f"[QWASAR Switchboard] OK — profile saved atomically: {saved}")
        return 0
    except (SwitchboardError, OSError, ValueError) as exc:
        print(f"[QWASAR Switchboard] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
