#!/usr/bin/env python3
"""Transactional, profile-only controls for QWASAR workspace composition.

This is not a package manager. It never installs/uninstalls modules, stops
services, launches commands or changes the protected shell/recovery surfaces.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import jsonschema
except ImportError:  # pragma: no cover - covered by CLI error path
    jsonschema = None  # type: ignore[assignment]

from desk.utils.atomic_io import atomic_write_text


DEFAULT_MANIFEST = "data/qwasar_ui_manifest.json"
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"
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


class QwasarSwitchboard:
    """Edit a QWASAR .qprofile in memory and persist it atomically on request.

    A profile update is validated before it replaces the in-memory snapshot.
    save() then verifies that the source file has not changed since load and
    commits the complete profile using the repository's atomic I/O helper.
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
        self._validate_profile(self.profile)
        self.protected_areas = set(
            self.manifest["featureManagement"]["protectedAreas"]
        )
        self._loaded_digest = _digest(self.profile_path)

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
            seen_sections: set[str] = set()
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

        for binding in profile.get("bindings", []):
            if binding["actionId"] not in known_actions:
                raise SwitchboardError(
                    f"profile binding references unknown action: {binding['actionId']}"
                )

        for key, id_key in (
            ("moduleStates", "moduleId"),
            ("contributionStates", "contributionId"),
        ):
            values = [item[id_key] for item in profile.get(key, [])]
            if len(values) != len(set(values)):
                raise SwitchboardError(f"profile contains duplicate IDs in {key}")

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

    def _ensure_changeable(self, item_id: str, operation: str) -> None:
        if operation in {"disabled", "hidden"} and item_id in self.protected_areas:
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

    def set_global_panel_enabled(
        self, panel_id: str, enabled: bool
    ) -> dict[str, Any]:
        panels = self.manifest["shell"]["globalPanels"]
        if panel_id not in panels:
            raise SwitchboardError(f"unknown global panel: {panel_id}")
        if not isinstance(enabled, bool):
            raise SwitchboardError("global panel enabled state must be a boolean")

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

    def reset_profile(self, default_profile_path: str | Path = DEFAULT_PROFILE) -> dict[str, Any]:
        defaults = _read_json(self._resolve(default_profile_path), "default QWASAR profile")
        return self._edit(lambda profile: (profile.clear(), profile.update(copy.deepcopy(defaults))))

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
                })
            sections.sort(key=lambda item: (item["order"], item["id"]))
            workspaces.append({
                "id": workspace_id,
                "label": override.get("labelOverride", base["label"]),
                "enabled": override.get("enabled", True),
                "visible": override.get("visible", True),
                "order": index,
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
        current = _digest(self.profile_path)
        if current != self._loaded_digest:
            raise ConcurrentProfileUpdate(
                f"profile changed on disk since load; reload before saving: {self.profile_path}"
            )
        serialized = json.dumps(
            self.profile, ensure_ascii=False, indent=2, sort_keys=False
        ) + "\n"
        try:
            atomic_write_text(str(self.profile_path), serialized, backup=True)
        except OSError as exc:
            raise SwitchboardError(f"cannot save profile {self.profile_path}: {exc}") from exc
        self._loaded_digest = _digest(self.profile_path)
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
        elif args.command == "move-workspace":
            switchboard.move_workspace(args.workspace_id, args.index)
        elif args.command == "move-section":
            switchboard.move_section(args.workspace_id, args.section_id, args.index)
        elif args.command == "reset-profile":
            switchboard.reset_profile()
        saved = switchboard.save()
        print(f"[QWASAR Switchboard] OK — profile saved atomically: {saved}")
        return 0
    except (SwitchboardError, OSError, ValueError) as exc:
        print(f"[QWASAR Switchboard] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
