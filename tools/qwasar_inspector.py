#!/usr/bin/env python3
"""Read-only validator for QWASAR UI, profile and module manifests.

Run from the repository root with:
    python3 tools/qwasar_inspector.py

The inspector never installs, enables, disables, rewrites or executes modules.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import jsonschema
except ImportError:  # pragma: no cover - exercised by the CLI error path
    jsonschema = None  # type: ignore[assignment]


DEFAULT_MANIFEST = "data/qwasar_ui_manifest.json"
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"
DEFAULT_MODULE = "data/examples/qwasar-wifi-overview.module.json"


@dataclass
class InspectionReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_json(path: Path, label: str, report: InspectionReport) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.errors.append(f"{label}: file not found: {path}")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.errors.append(f"{label}: cannot read JSON ({exc}): {path}")
    else:
        if not isinstance(value, dict):
            report.errors.append(f"{label}: top-level JSON value must be an object: {path}")
        else:
            return value
    return None


def _validate_schema(
    document: dict[str, Any], schema_path: Path, label: str, report: InspectionReport
) -> bool:
    schema = _read_json(schema_path, f"{label} schema", report)
    if schema is None:
        return False
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
        failures = sorted(
            validator.iter_errors(document),
            key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
        )
    except (jsonschema.SchemaError, TypeError, ValueError) as exc:
        report.errors.append(f"{label}: invalid schema {schema_path}: {exc}")
        return False
    for failure in failures:
        location = "/".join(str(part) for part in failure.absolute_path) or "$"
        report.errors.append(f"{label} schema: {location}: {failure.message}")
    return not failures


def _walk_node(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield node
    for child in node.get("children", []):
        yield from _walk_node(child)
    for children in node.get("slots", {}).values():
        for child in children:
            yield from _walk_node(child)


def _component_nodes(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    shell = manifest["shell"]
    roots.extend((shell["header"], shell["footer"]))
    roots.extend(region["content"] for region in shell["homePanels"].values())
    roots.extend(panel["content"] for panel in shell["globalPanels"].values())
    roots.append(manifest["runtimeLaunch"]["selector"]["component"])
    for workspace in manifest["workspaces"]:
        roots.append(workspace["layout"])
        roots.extend(workspace.get("widgets", []))
        for section in workspace.get("sections", []):
            if "layout" in section:
                roots.append(section["layout"])
            roots.extend(section.get("widgets", []))
    return [node for root in roots for node in _walk_node(root)]


def _menu_entries(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    def walk(entries: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
        for entry in entries:
            yield entry
            yield from walk(entry.get("children", []))

    for workspace in manifest["workspaces"]:
        yield from walk(workspace.get("menu", []))
        for section in workspace.get("sections", []):
            yield from walk(section.get("menu", []))


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def _check_manifest(manifest: dict[str, Any], report: InspectionReport) -> None:
    registry_items = manifest["componentRegistry"]
    action_items = manifest["actions"]
    workspace_items = manifest["workspaces"]
    registry = {item["id"]: item for item in registry_items}
    action_ids = {item["id"] for item in action_items}

    for label, ids in (
        ("component type", [item["id"] for item in registry_items]),
        ("action", [item["id"] for item in action_items]),
        ("workspace", [item["id"] for item in workspace_items]),
    ):
        for duplicate in sorted(_duplicates(ids)):
            report.errors.append(f"manifest: duplicate {label} ID: {duplicate}")

    sections: set[str] = set()
    for workspace in workspace_items:
        section_ids = [item["id"] for item in workspace.get("sections", [])]
        for duplicate in sorted(_duplicates(section_ids)):
            report.errors.append(
                f"manifest: duplicate section ID {duplicate} in workspace {workspace['id']}"
            )
        sections.update(section_ids)

    invalid_props_schemas: set[str] = set()
    for definition in registry_items:
        props_schema = definition["propsSchema"]
        try:
            jsonschema.Draft202012Validator.check_schema(props_schema)
        except jsonschema.SchemaError as exc:
            invalid_props_schemas.add(definition["id"])
            report.errors.append(
                f"manifest: invalid propsSchema for {definition['id']}: {exc.message}"
            )
            continue
        if props_schema.get("additionalProperties") is not False:
            report.errors.append(
                f"manifest: propsSchema for {definition['id']} must set additionalProperties=false"
            )
        customizable = set(definition.get("customizable", []))
        declared = set(props_schema.get("properties", {}))
        if not customizable <= declared:
            report.errors.append(
                f"manifest: {definition['id']} customizes undeclared props: "
                + ", ".join(sorted(customizable - declared))
            )

    nodes = _component_nodes(manifest)
    node_ids = [node["id"] for node in nodes]
    for duplicate in sorted(_duplicates(node_ids)):
        report.errors.append(f"manifest: duplicate component node ID: {duplicate}")
    for node in nodes:
        definition = registry.get(node["type"])
        if definition is None:
            report.errors.append(
                f"manifest: component {node['id']} uses unregistered type {node['type']}"
            )
            continue
        if node["type"] in invalid_props_schemas:
            continue
        invalid_slots = set(node.get("slots", {})) - set(definition.get("slots", []))
        if invalid_slots:
            report.errors.append(
                f"manifest: component {node['id']} uses unsupported slots: "
                + ", ".join(sorted(invalid_slots))
            )
        try:
            jsonschema.Draft202012Validator(
                definition["propsSchema"], format_checker=jsonschema.FormatChecker()
            ).validate(node.get("props", {}))
        except jsonschema.ValidationError as exc:
            report.errors.append(
                f"manifest: invalid props on {node['id']} ({node['type']}): {exc.message}"
            )

    for entry in _menu_entries(manifest):
        action_id = entry.get("actionId")
        if action_id and action_id not in action_ids:
            report.errors.append(
                f"manifest: menu entry {entry['id']} references unknown action {action_id}"
            )
    for node in nodes:
        action_id = node.get("actionId")
        if action_id and action_id not in action_ids:
            report.errors.append(
                f"manifest: component {node['id']} references unknown action {action_id}"
            )
    for binding in manifest.get("keymap", []):
        if binding["actionId"] not in action_ids:
            report.errors.append(
                f"manifest: key binding {binding['id']} references unknown action "
                f"{binding['actionId']}"
            )

    report.stats.update({
        "component_types": len(registry_items),
        "component_nodes": len(nodes),
        "actions": len(action_items),
        "workspaces": len(workspace_items),
        "sections": len(sections),
    })


def _is_protected(item_id: str, protected_areas: set[str]) -> bool:
    return any(
        item_id == protected or item_id.startswith(protected + ".")
        for protected in protected_areas
    )


def _menu_index(
    entries: list[dict[str, Any]],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Return direct child IDs and all recursively registered menu entries."""
    direct = {entry["id"] for entry in entries}
    all_entries: dict[str, dict[str, Any]] = {}

    def walk(items: list[dict[str, Any]]) -> None:
        for item in items:
            all_entries[item["id"]] = item
            walk(item.get("children", []))

    walk(entries)
    return direct, all_entries


def _check_profile(
    profile: dict[str, Any], label: str, manifest: dict[str, Any], report: InspectionReport
) -> None:
    workspaces = {item["id"]: item for item in manifest["workspaces"]}
    actions = {item["id"] for item in manifest["actions"]}
    protected = set(manifest.get("featureManagement", {}).get("protectedAreas", []))

    def protected_item(item_id: str) -> bool:
        return _is_protected(item_id, protected)

    for workspace_id in profile.get("workspaceOrder", []):
        if workspace_id not in workspaces:
            report.errors.append(
                f"{label}: workspaceOrder references unknown workspace {workspace_id}"
            )

    # The central shell and recovery surfaces cannot be removed by an imported
    # profile. Switchboard applies the same boundary before saving edits.
    for region_name in ("header", "footer"):
        if profile.get("shell", {}).get(region_name, {}).get("enabled") is False:
            report.errors.append(
                f"{label}: protected shell region cannot be disabled: {region_name}"
            )

    known_global_panels = set(manifest.get("shell", {}).get("globalPanels", {}))
    global_panel_overrides = profile.get("shell", {}).get("globalPanels", {})
    for panel_id, override in global_panel_overrides.items():
        if panel_id not in known_global_panels:
            report.errors.append(
                f"{label}: shell references unknown global panel {panel_id}"
            )
        if protected_item(panel_id) and override.get("enabled") is False:
            report.errors.append(
                f"{label}: protected global panel cannot be disabled: {panel_id}"
            )

    seen_overrides: set[str] = set()
    for override in profile.get("workspaceOverrides", []):
        workspace_id = override["id"]
        if workspace_id not in workspaces:
            report.errors.append(
                f"{label}: override references unknown workspace {workspace_id}"
            )
            continue
        if workspace_id in seen_overrides:
            report.errors.append(f"{label}: duplicate workspace override {workspace_id}")
            continue
        seen_overrides.add(workspace_id)

        base_workspace = workspaces[workspace_id]
        direct_ids, all_entries = _menu_index(base_workspace.get("menu", []))
        for entry_id in override.get("menuOrder", []):
            if entry_id not in direct_ids:
                report.errors.append(
                    f"{label}: menuOrder references unknown top-level entry "
                    f"{entry_id} in {workspace_id}"
                )
        for entry_id in override.get("hiddenMenuEntries", []):
            entry = all_entries.get(entry_id)
            if entry is None:
                report.errors.append(
                    f"{label}: hiddenMenuEntries references unknown entry "
                    f"{entry_id} in {workspace_id}"
                )
            elif (
                protected_item(workspace_id)
                or protected_item(entry_id)
                or protected_item(entry.get("actionId", ""))
            ):
                report.errors.append(
                    f"{label}: protected menu entry cannot be hidden: "
                    f"{entry_id} in {workspace_id}"
                )

        if protected_item(workspace_id) and (
            override.get("enabled") is False or override.get("visible") is False
        ):
            report.errors.append(
                f"{label}: protected workspace cannot be disabled or hidden: {workspace_id}"
            )

        known_sections = {
            item["id"]: item for item in base_workspace.get("sections", [])
        }
        seen_sections: set[str] = set()
        for section in override.get("sections", []):
            section_id = section["id"]
            if section_id not in known_sections:
                report.errors.append(
                    f"{label}: section {section_id} is not registered in {workspace_id}"
                )
                continue
            if section_id in seen_sections:
                report.errors.append(
                    f"{label}: duplicate section override {section_id} in {workspace_id}"
                )
                continue
            seen_sections.add(section_id)

            section_menu = known_sections[section_id].get("menu", [])
            section_direct, section_all = _menu_index(section_menu)
            for entry_id in section.get("menuOrder", []):
                if entry_id not in section_direct:
                    report.errors.append(
                        f"{label}: menuOrder references unknown top-level entry "
                        f"{entry_id} in section {section_id}"
                    )
            for entry_id in section.get("hiddenMenuEntries", []):
                entry = section_all.get(entry_id)
                if entry is None:
                    report.errors.append(
                        f"{label}: hiddenMenuEntries references unknown entry "
                        f"{entry_id} in section {section_id}"
                    )
                elif (
                    protected_item(workspace_id)
                    or protected_item(section_id)
                    or protected_item(entry_id)
                    or protected_item(entry.get("actionId", ""))
                ):
                    report.errors.append(
                        f"{label}: protected menu entry cannot be hidden: "
                        f"{entry_id} in section {section_id}"
                    )

            if protected_item(section_id) and (
                section.get("enabled") is False or section.get("visible") is False
            ):
                report.errors.append(
                    f"{label}: protected section cannot be disabled or hidden: {section_id}"
                )
            _check_protected_contributions(
                section.get("contributions", []), label, protected, report
            )

        _check_protected_contributions(
            override.get("contributions", []), label, protected, report
        )

    for binding in profile.get("bindings", []):
        if binding["actionId"] not in actions:
            report.errors.append(
                f"{label}: binding references unknown action {binding['actionId']}"
            )

    seen_modules: set[str] = set()
    for module in profile.get("moduleStates", []):
        module_id = module["moduleId"]
        if module_id in seen_modules:
            report.errors.append(f"{label}: duplicate module state {module_id}")
        seen_modules.add(module_id)
        if protected_item(module_id) and module["enabled"] is False:
            report.errors.append(
                f"{label}: protected module cannot be disabled: {module_id}"
            )

    _check_protected_contributions(
        profile.get("contributionStates", []), label, protected, report
    )


def _check_protected_contributions(
    entries: list[dict[str, Any]],
    label: str,
    protected_areas: set[str],
    report: InspectionReport,
) -> None:
    seen: set[str] = set()
    for entry in entries:
        contribution_id = entry["contributionId"]
        if contribution_id in seen:
            report.errors.append(
                f"{label}: duplicate contribution state {contribution_id}"
            )
        seen.add(contribution_id)
        if (
            _is_protected(contribution_id, protected_areas)
            and entry["state"] != "enabled"
        ):
            report.errors.append(
                f"{label}: protected contribution cannot be disabled or hidden: "
                f"{contribution_id}"
            )

def _check_module(
    module: dict[str, Any], label: str, manifest: dict[str, Any], report: InspectionReport
) -> None:
    components = {item["id"]: item for item in manifest["componentRegistry"]}
    workspaces = {item["id"]: item for item in manifest["workspaces"]}
    module_actions = [item["id"] for item in module.get("actions", [])]
    for duplicate in sorted(_duplicates(module_actions)):
        report.errors.append(f"{label}: duplicate action ID {duplicate}")
    contribution_ids = [
        item["id"] for item in module.get("contributions", [])
    ]
    for duplicate in sorted(_duplicates(contribution_ids)):
        report.errors.append(f"{label}: duplicate contribution ID {duplicate}")
    known_module_actions = set(module_actions)
    for contribution in module.get("contributions", []):
        component_type = contribution["componentType"]
        definition = components.get(component_type)
        if definition is None:
            report.errors.append(
                f"{label}: contribution {contribution['id']} uses unregistered component "
                f"{component_type}"
            )
        else:
            try:
                jsonschema.Draft202012Validator(
                    definition["propsSchema"], format_checker=jsonschema.FormatChecker()
                ).validate(contribution.get("props", {}))
            except jsonschema.ValidationError as exc:
                report.errors.append(
                    f"{label}: invalid props on contribution {contribution['id']}: {exc.message}"
                )
        workspace_id = contribution.get("workspaceId")
        if workspace_id and workspace_id not in workspaces:
            report.errors.append(
                f"{label}: contribution {contribution['id']} references unknown workspace "
                f"{workspace_id}"
            )
        section_id = contribution.get("sectionId")
        if section_id:
            if workspace_id and workspace_id in workspaces:
                known_sections = {
                    section["id"]
                    for section in workspaces[workspace_id].get("sections", [])
                }
            else:
                known_sections = {
                    section["id"]
                    for workspace in workspaces.values()
                    for section in workspace.get("sections", [])
                }
            if section_id not in known_sections:
                relationship = (
                    f" in workspace {workspace_id}" if workspace_id else ""
                )
                report.errors.append(
                    f"{label}: contribution {contribution['id']} references unknown "
                    f"section {section_id}{relationship}"
                )
        missing_actions = set(contribution.get("actionIds", [])) - known_module_actions
        if missing_actions:
            report.errors.append(
                f"{label}: contribution {contribution['id']} references undeclared module "
                "actions: " + ", ".join(sorted(missing_actions))
            )


def inspect_repository(
    root: Path,
    manifest_path: str = DEFAULT_MANIFEST,
    profile_paths: list[str] | None = None,
    module_paths: list[str] | None = None,
) -> InspectionReport:
    """Validate the UI manifest and optional profiles/modules without modifying files."""
    report = InspectionReport()
    if jsonschema is None:
        report.errors.append(
            "QWASAR Inspector requires the 'jsonschema' Python package "
            "(install with: python3 -m pip install 'jsonschema>=4.23,<5')"
        )
        return report

    root = root.resolve()
    manifest = _read_json(root / manifest_path, "manifest", report)
    if manifest is None:
        return report
    if not _validate_schema(manifest, root / "schemas/qwasar-ui.schema.json", "manifest", report):
        return report
    _check_manifest(manifest, report)

    for index, relative_path in enumerate(profile_paths or []):
        label = f"profile[{index + 1}] {relative_path}"
        profile = _read_json(root / relative_path, label, report)
        if profile is None:
            continue
        if _validate_schema(
            profile, root / "schemas/qwasar-profile.schema.json", label, report
        ):
            _check_profile(profile, label, manifest, report)
        report.stats["profiles"] = report.stats.get("profiles", 0) + 1

    for index, relative_path in enumerate(module_paths or []):
        label = f"module[{index + 1}] {relative_path}"
        module = _read_json(root / relative_path, label, report)
        if module is None:
            continue
        if _validate_schema(module, root / "schemas/qwasar-module.schema.json", label, report):
            _check_module(module, label, manifest, report)
        report.stats["modules"] = report.stats.get("modules", 0) + 1
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="UI manifest path, relative to --root")
    parser.add_argument("--profile", action="append", help="profile path; repeat to inspect multiple profiles")
    parser.add_argument("--module", action="append", help="module path; repeat to inspect multiple modules")
    parser.add_argument("--manifest-only", action="store_true", help="skip bundled sample profile and module")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    profiles = args.profile if args.profile is not None else ([] if args.manifest_only else [DEFAULT_PROFILE])
    modules = args.module if args.module is not None else ([] if args.manifest_only else [DEFAULT_MODULE])
    report = inspect_repository(args.root, args.manifest, profiles, modules)

    if args.json_output:
        print(json.dumps({"ok": report.ok, **asdict(report)}, indent=2, sort_keys=True))
    else:
        prefix = "[QWASAR Inspector]"
        for warning in report.warnings:
            print(f"{prefix} WARNING: {warning}")
        for error in report.errors:
            print(f"{prefix} ERROR: {error}", file=sys.stderr)
        if report.ok:
            stats = ", ".join(f"{key}={value}" for key, value in sorted(report.stats.items()))
            print(f"{prefix} OK — read-only validation passed ({stats})")
        else:
            print(f"{prefix} FAILED — {len(report.errors)} error(s)", file=sys.stderr)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
