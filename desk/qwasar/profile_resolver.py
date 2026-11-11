#!/usr/bin/env python3
"""Resolve portable QWASAR profiles into an engine-neutral UI composition.

This module is intentionally independent from Pygame and LÖVE. It reads the
canonical UI manifest and a data-only .qprofile; it never executes module
code, installs packages, or mutates either input file.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # The runtime keeps a structural fallback for lean muOS images.
    jsonschema = None  # type: ignore[assignment]


DEFAULT_MANIFEST = "data/qwasar_ui_manifest.json"
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"
UI_SCHEMA = "schemas/qwasar-ui.schema.json"
PROFILE_SCHEMA = "schemas/qwasar-profile.schema.json"


class ProfileResolutionError(RuntimeError):
    """The canonical manifest or the trusted default profile is unusable."""


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileResolutionError(f"{label} not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileResolutionError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProfileResolutionError(f"{label} must be a JSON object: {path}")
    return value


def _validate_schema(
    document: dict[str, Any], schema_path: Path, label: str, warnings: list[str]
) -> None:
    if jsonschema is None:
        warnings.append(
            "jsonschema is not installed; runtime structural and cross-reference "
            f"checks are active, but the complete {label} JSON Schema check was skipped"
        )
        return
    schema = _read_object(schema_path, f"{label} schema")
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
        validator.validate(document)
    except jsonschema.SchemaError as exc:
        raise ProfileResolutionError(
            f"invalid {label} schema {schema_path}: {exc.message}"
        ) from exc
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "$"
        raise ProfileResolutionError(
            f"{label} schema validation failed at {location}: {exc.message}"
        ) from exc


def _menu_ids(entries: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for entry in entries:
        result.add(entry["id"])
        result.update(_menu_ids(entry.get("children", [])))
    return result


def _find_menu(entries: list[dict[str, Any]], entry_id: str) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("id") == entry_id:
            return entry
        nested = _find_menu(entry.get("children", []), entry_id)
        if nested is not None:
            return nested
    return None


class QwasarProfileResolver:
    """Read, validate and resolve a selected profile without changing disk state."""

    def __init__(
        self,
        root: str | Path,
        manifest_path: str = DEFAULT_MANIFEST,
        default_profile_path: str = DEFAULT_PROFILE,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.manifest_path = self._resolve(manifest_path)
        self.default_profile_path = self._resolve(default_profile_path)
        self.manifest = _read_object(self.manifest_path, "QWASAR UI manifest")
        manifest_warnings: list[str] = []
        _validate_schema(
            self.manifest,
            self._resolve(UI_SCHEMA),
            "QWASAR UI manifest",
            manifest_warnings,
        )
        self._validate_manifest_structure()
        self._manifest_warnings = manifest_warnings
        self._workspaces = {
            item["id"]: item for item in self.manifest["workspaces"]
        }
        self._actions = {item["id"] for item in self.manifest["actions"]}
        self._protected = set(
            self.manifest["featureManagement"]["protectedAreas"]
        )

    def _resolve(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.root / candidate).resolve()

    def _validate_manifest_structure(self) -> None:
        required = {
            "schemaVersion", "id", "apiVersion", "componentRegistry", "shell",
            "workspaces", "actions", "keymap", "featureManagement",
        }
        missing = required - set(self.manifest)
        if missing:
            raise ProfileResolutionError(
                "QWASAR UI manifest is missing required fields: "
                + ", ".join(sorted(missing))
            )
        if not isinstance(self.manifest["workspaces"], list):
            raise ProfileResolutionError("manifest workspaces must be an array")
        workspace_ids = [item.get("id") for item in self.manifest["workspaces"]]
        if None in workspace_ids or len(workspace_ids) != len(set(workspace_ids)):
            raise ProfileResolutionError("manifest workspace IDs must be present and unique")
        if not isinstance(self.manifest["actions"], list):
            raise ProfileResolutionError("manifest actions must be an array")
        action_ids = [item.get("id") for item in self.manifest["actions"]]
        if None in action_ids or len(action_ids) != len(set(action_ids)):
            raise ProfileResolutionError("manifest action IDs must be present and unique")
        shell = self.manifest["shell"]
        if not isinstance(shell, dict) or not isinstance(shell.get("globalPanels"), dict):
            raise ProfileResolutionError("manifest shell/globalPanels structure is invalid")
        management = self.manifest["featureManagement"]
        if not isinstance(management, dict) or not isinstance(
            management.get("protectedAreas"), list
        ):
            raise ProfileResolutionError("manifest protected-area registry is invalid")

    def _is_protected(self, item_id: str) -> bool:
        return any(
            item_id == protected or item_id.startswith(protected + ".")
            for protected in self._protected
        )

    def _validate_profile(self, profile: dict[str, Any], warnings: list[str]) -> None:
        _validate_schema(
            profile,
            self._resolve(PROFILE_SCHEMA),
            "QWASAR profile",
            warnings,
        )
        required = {
            "schemaVersion", "id", "name", "compatibility", "workspaceOrder",
            "shell", "workspaceOverrides", "theme",
        }
        missing = required - set(profile)
        if missing:
            raise ProfileResolutionError(
                "profile is missing required fields: " + ", ".join(sorted(missing))
            )

        workspace_order = profile.get("workspaceOrder")
        if (
            not isinstance(workspace_order, list)
            or any(not isinstance(item, str) for item in workspace_order)
            or len(workspace_order) != len(set(workspace_order))
        ):
            raise ProfileResolutionError("profile workspaceOrder must contain unique string IDs")
        if not isinstance(profile.get("workspaceOverrides"), list):
            raise ProfileResolutionError("profile workspaceOverrides must be an array")
        if not isinstance(profile.get("shell"), dict):
            raise ProfileResolutionError("profile shell overrides must be an object")
        unknown = set(workspace_order) - set(self._workspaces)
        if unknown:
            raise ProfileResolutionError(
                "profile references unknown workspaces: " + ", ".join(sorted(unknown))
            )

        overrides = profile.get("workspaceOverrides", [])
        if any(not isinstance(item, dict) for item in overrides):
            raise ProfileResolutionError("workspace overrides must be objects")
        override_ids = [item.get("id") for item in overrides]
        if None in override_ids or len(override_ids) != len(set(override_ids)):
            raise ProfileResolutionError("workspace override IDs must be present and unique")
        for override in overrides:
            workspace_id = override["id"]
            workspace = self._workspaces.get(workspace_id)
            if workspace is None:
                raise ProfileResolutionError(
                    f"profile references unknown workspace override: {workspace_id}"
                )
            if self._is_protected(workspace_id) and (
                override.get("enabled") is False or override.get("visible") is False
            ):
                raise ProfileResolutionError(
                    f"profile cannot disable or hide protected workspace {workspace_id}"
                )

            workspace_menu = workspace.get("menu", [])
            direct_menu_ids = {item["id"] for item in workspace_menu}
            all_menu_ids = _menu_ids(workspace_menu)
            if not set(override.get("menuOrder", [])) <= direct_menu_ids:
                raise ProfileResolutionError(
                    f"workspace {workspace_id} menuOrder contains unknown entries"
                )
            hidden_menu = set(override.get("hiddenMenuEntries", []))
            if not hidden_menu <= all_menu_ids:
                raise ProfileResolutionError(
                    f"workspace {workspace_id} hiddenMenuEntries contains unknown entries"
                )
            for entry_id in hidden_menu:
                entry = _find_menu(workspace_menu, entry_id)
                if (
                    self._is_protected(workspace_id)
                    or self._is_protected(entry_id)
                    or (entry and self._is_protected(entry.get("actionId", "")))
                ):
                    raise ProfileResolutionError(
                        f"profile cannot hide protected menu entry {entry_id}"
                    )

            sections = {
                section["id"]: section for section in workspace.get("sections", [])
            }
            section_overrides = override.get("sections", [])
            if not isinstance(section_overrides, list) or any(
                not isinstance(item, dict) for item in section_overrides
            ):
                raise ProfileResolutionError(
                    f"workspace {workspace_id} section overrides must be objects"
                )
            section_ids = [item.get("id") for item in section_overrides]
            if None in section_ids or len(section_ids) != len(set(section_ids)):
                raise ProfileResolutionError(
                    f"workspace {workspace_id} section override IDs must be unique"
                )
            for section_override in section_overrides:
                section_id = section_override["id"]
                base_section = sections.get(section_id)
                if base_section is None:
                    raise ProfileResolutionError(
                        f"profile references unknown section {section_id} in {workspace_id}"
                    )
                if self._is_protected(section_id) and (
                    section_override.get("enabled") is False
                    or section_override.get("visible") is False
                ):
                    raise ProfileResolutionError(
                        f"profile cannot disable or hide protected section {section_id}"
                    )
                base_menu = base_section.get("menu", [])
                if not set(section_override.get("menuOrder", [])) <= {
                    item["id"] for item in base_menu
                }:
                    raise ProfileResolutionError(
                        f"section {section_id} menuOrder contains unknown entries"
                    )
                hidden = set(section_override.get("hiddenMenuEntries", []))
                if not hidden <= _menu_ids(base_menu):
                    raise ProfileResolutionError(
                        f"section {section_id} hiddenMenuEntries contains unknown entries"
                    )
                for entry_id in hidden:
                    entry = _find_menu(base_menu, entry_id)
                    if (
                        self._is_protected(workspace_id)
                        or self._is_protected(section_id)
                        or self._is_protected(entry_id)
                        or (entry and self._is_protected(entry.get("actionId", "")))
                    ):
                        raise ProfileResolutionError(
                            f"profile cannot hide protected menu entry {entry_id}"
                        )

        panel_ids = set(self.manifest["shell"]["globalPanels"])
        profile_panels = set(profile["shell"].get("globalPanels", {}))
        if not profile_panels <= panel_ids:
            raise ProfileResolutionError(
                "profile references unknown global panels: "
                + ", ".join(sorted(profile_panels - panel_ids))
            )
        for panel_id, override in profile["shell"].get("globalPanels", {}).items():
            if self._is_protected(panel_id) and override.get("enabled") is False:
                raise ProfileResolutionError(
                    f"profile cannot disable protected global panel {panel_id}"
                )

        for region in ("header", "footer"):
            if profile["shell"].get(region, {}).get("enabled") is False:
                raise ProfileResolutionError(
                    f"profile cannot disable protected shell region {region}"
                )

        for binding in profile.get("bindings", []):
            if binding.get("actionId") not in self._actions:
                raise ProfileResolutionError(
                    f"profile binding references unknown action {binding.get('actionId')}"
                )
        for module in profile.get("moduleStates", []):
            if self._is_protected(module["moduleId"]) and module.get("enabled") is False:
                raise ProfileResolutionError(
                    f"profile cannot disable protected module {module['moduleId']}"
                )
        for contribution in profile.get("contributionStates", []):
            contribution_id = contribution["contributionId"]
            if self._is_protected(contribution_id) and contribution.get("state") != "enabled":
                raise ProfileResolutionError(
                    f"profile cannot disable or hide protected contribution {contribution_id}"
                )

    @staticmethod
    def _menu_composition(
        entries: list[dict[str, Any]], override: dict[str, Any]
    ) -> list[dict[str, Any]]:
        order = override.get("menuOrder", [])
        ranks = {item_id: index for index, item_id in enumerate(order)}
        hidden = set(override.get("hiddenMenuEntries", []))
        ordered = list(enumerate(entries))
        ordered.sort(
            key=lambda item: (
                ranks.get(item[1]["id"], len(ranks) + item[0]),
                item[0],
            )
        )
        result = []
        for index, entry in ordered:
            result.append({
                "id": entry["id"],
                "label": entry["label"],
                "kind": entry["kind"],
                "actionId": entry.get("actionId"),
                "providerId": entry.get("providerId"),
                "enabled": entry.get("enabled", True),
                "visible": entry["id"] not in hidden,
                "description": entry.get("description", ""),
                "children": QwasarProfileResolver._menu_composition(
                    entry.get("children", []), override
                ),
            })
        return result

    @staticmethod
    def _merge_keymap(
        defaults: list[dict[str, Any]], overrides: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        result = copy.deepcopy(defaults)
        for binding in overrides:
            match = next(
                (
                    item for item in result
                    if item.get("actionId") == binding["actionId"]
                    and item.get("input") == binding["input"]
                ),
                None,
            )
            if match is None:
                result.append(copy.deepcopy(binding))
            else:
                match["value"] = binding["value"]
                match["enabled"] = binding.get("enabled", True)
        return result

    def _compose(self, profile: dict[str, Any], source: Path, warnings: list[str]) -> dict[str, Any]:
        workspace_overrides = {
            item["id"]: item for item in profile.get("workspaceOverrides", [])
        }
        order = list(profile.get("workspaceOrder", []))
        order.extend(
            item["id"] for item in self.manifest["workspaces"]
            if item["id"] not in order
        )
        workspaces = []
        for workspace_position, workspace_id in enumerate(order):
            definition = self._workspaces[workspace_id]
            override = workspace_overrides.get(workspace_id, {})
            section_overrides = {
                item["id"]: item for item in override.get("sections", [])
            }
            sections = []
            for source_position, section in enumerate(definition.get("sections", [])):
                section_override = section_overrides.get(section["id"], {})
                sections.append({
                    "id": section["id"],
                    "label": section_override.get("labelOverride", section["label"]),
                    "enabled": section_override.get("enabled", True),
                    "visible": section_override.get("visible", True),
                    "order": section_override.get("order", source_position),
                    "menu": self._menu_composition(
                        section.get("menu", []), section_override
                    ),
                    "definition": copy.deepcopy(section),
                })
            sections.sort(key=lambda item: (item["order"], item["id"]))
            workspaces.append({
                "id": workspace_id,
                "label": override.get("labelOverride", definition["label"]),
                "template": definition["template"],
                "status": definition.get("status", "current"),
                "enabled": override.get("enabled", True),
                "visible": override.get("visible", True),
                "order": workspace_position,
                "menu": self._menu_composition(definition.get("menu", []), override),
                "sections": sections,
                "definition": copy.deepcopy(definition),
            })

        panel_states = {}
        for panel_id, definition in self.manifest["shell"]["globalPanels"].items():
            profile_override = profile["shell"].get("globalPanels", {}).get(panel_id, {})
            panel_states[panel_id] = {
                "enabled": profile_override.get("enabled", definition["enabled"]),
                "placement": profile_override.get("placement", definition["placement"]),
            }

        shell_overrides = {
            "header": copy.deepcopy(profile["shell"].get("header", {})),
            "footer": copy.deepcopy(profile["shell"].get("footer", {})),
            "homePanels": copy.deepcopy(profile["shell"].get("homePanels", {})),
        }
        return {
            "schemaVersion": "1.0",
            "manifestId": self.manifest["id"],
            "uiApiVersion": self.manifest["apiVersion"],
            "profile": {
                "id": profile["id"],
                "name": profile["name"],
                "source": "default" if source == self.default_profile_path else "custom",
            },
            "workspaces": workspaces,
            "globalPanels": panel_states,
            "shell": shell_overrides,
            "theme": copy.deepcopy(profile.get("theme", {})),
            "keymap": self._merge_keymap(
                self.manifest.get("keymap", []), profile.get("bindings", [])
            ),
            "modules": {
                item["moduleId"]: item["enabled"]
                for item in profile.get("moduleStates", [])
            },
            "contributions": {
                item["contributionId"]: item["state"]
                for item in profile.get("contributionStates", [])
            },
            "warnings": list(dict.fromkeys(warnings)),
        }

    def resolve(
        self,
        profile_path: str | Path | None = None,
        *,
        fallback_to_default: bool = True,
    ) -> dict[str, Any]:
        requested = self._resolve(
            profile_path
            or os.environ.get("QWASAR_PROFILE")
            or self.default_profile_path
        )
        warnings = list(self._manifest_warnings)
        try:
            profile = _read_object(requested, "QWASAR profile")
            local_warnings: list[str] = []
            self._validate_profile(profile, local_warnings)
            return self._compose(profile, requested, warnings + local_warnings)
        except (ProfileResolutionError, KeyError, TypeError, ValueError) as exc:
            if not fallback_to_default or requested == self.default_profile_path:
                if isinstance(exc, ProfileResolutionError):
                    raise
                raise ProfileResolutionError(
                    f"selected QWASAR profile is structurally invalid: {exc}"
                ) from exc
            warnings.append(
                f"Selected profile was rejected; using the bundled H700 default: {exc}"
            )

        try:
            profile = _read_object(self.default_profile_path, "bundled default profile")
            local_warnings = []
            self._validate_profile(profile, local_warnings)
        except (ProfileResolutionError, KeyError, TypeError, ValueError) as exc:
            raise ProfileResolutionError(
                f"selected and default profiles are invalid; safe startup is blocked: {exc}"
            ) from exc
        return self._compose(
            profile, self.default_profile_path, warnings + local_warnings
        )

