from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.qwasar_inspector import inspect_repository

ROOT = Path(__file__).resolve().parents[1]


def _fixture(tmp_path: Path) -> Path:
    for folder in ("schemas", "data/profiles", "data/examples"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for name in (
        "qwasar-ui.schema.json",
        "qwasar-profile.schema.json",
        "qwasar-module.schema.json",
    ):
        shutil.copy2(ROOT / "schemas" / name, tmp_path / "schemas" / name)
    for source, target in (
        (ROOT / "data/qwasar_ui_manifest.json", tmp_path / "data/qwasar_ui_manifest.json"),
        (
            ROOT / "data/profiles/voiddesk-handheld-default.qprofile.json",
            tmp_path / "data/profiles/voiddesk-handheld-default.qprofile.json",
        ),
        (
            ROOT / "data/examples/qwasar-wifi-overview.module.json",
            tmp_path / "data/examples/qwasar-wifi-overview.module.json",
        ),
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def test_bundled_qwasar_contract_passes_read_only_inspection():
    report = inspect_repository(
        ROOT,
        profile_paths=["data/profiles/voiddesk-handheld-default.qprofile.json"],
        module_paths=["data/examples/qwasar-wifi-overview.module.json"],
    )
    assert report.ok, "\n".join(report.errors)
    assert report.stats["component_nodes"] > 0
    assert report.stats["workspaces"] == 8
    assert report.stats["profiles"] == 1
    assert report.stats["modules"] == 1


def test_inspector_rejects_unregistered_component_types(tmp_path: Path):
    root = _fixture(tmp_path)
    path = root / "data/qwasar_ui_manifest.json"
    manifest = _read(path)
    manifest["shell"]["header"]["type"] = "widget.not-registered"
    _write(path, manifest)

    report = inspect_repository(root, profile_paths=[], module_paths=[])
    assert not report.ok
    assert any("uses unregistered type widget.not-registered" in error for error in report.errors)


def test_inspector_rejects_profile_references_to_unknown_actions(tmp_path: Path):
    root = _fixture(tmp_path)
    path = root / "data/profiles/voiddesk-handheld-default.qprofile.json"
    profile = _read(path)
    profile["bindings"][0]["actionId"] = "action.not-registered"
    _write(path, profile)

    report = inspect_repository(
        root,
        profile_paths=["data/profiles/voiddesk-handheld-default.qprofile.json"],
        module_paths=[],
    )
    assert not report.ok
    assert any(
        "binding references unknown action action.not-registered" in error
        for error in report.errors
    )


def test_inspector_rejects_module_component_and_action_cross_reference_errors(tmp_path: Path):
    root = _fixture(tmp_path)
    path = root / "data/examples/qwasar-wifi-overview.module.json"
    module = _read(path)
    module["contributions"][0]["componentType"] = "widget.not-registered"
    module["contributions"][0]["actionIds"] = ["module.missing-action"]
    _write(path, module)

    report = inspect_repository(
        root,
        profile_paths=[],
        module_paths=["data/examples/qwasar-wifi-overview.module.json"],
    )
    assert not report.ok
    assert any(
        "uses unregistered component widget.not-registered" in error
        for error in report.errors
    )
    assert any("undeclared module actions" in error for error in report.errors)
