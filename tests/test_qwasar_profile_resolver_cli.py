from __future__ import annotations

import json
from pathlib import Path

from tools.qwasar_profile_resolver import main

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "data/profiles/voiddesk-handheld-default.qprofile.json"


def _copy_inputs(tmp_path: Path) -> None:
    import shutil

    for folder in ("schemas", "data/profiles"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    for name in ("qwasar-ui.schema.json", "qwasar-profile.schema.json"):
        shutil.copy2(ROOT / "schemas" / name, tmp_path / "schemas" / name)
    shutil.copy2(
        ROOT / "data/qwasar_ui_manifest.json",
        tmp_path / "data/qwasar_ui_manifest.json",
    )
    shutil.copy2(
        ROOT / DEFAULT_PROFILE,
        tmp_path / DEFAULT_PROFILE,
    )
    shutil.copy2(
        ROOT / "data/profiles/voiddesk-desktop-default.qprofile.json",
        tmp_path / "data/profiles/voiddesk-desktop-default.qprofile.json",
    )


def test_runtime_cli_writes_shared_effective_composition_atomically(tmp_path: Path):
    _copy_inputs(tmp_path)
    output = tmp_path / "data/qwasar_effective_profile.json"

    rc = main([
        "--root", str(tmp_path),
        "--output", "data/qwasar_effective_profile.json",
    ])

    assert rc == 0
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["profile"]["id"] == "qwasar.profile.voiddesk.handheld-default"
    assert value["schemaVersion"] == "1.0"
    assert not list(output.parent.glob(".qwasar_effective_profile.json.*.tmp"))


def test_runtime_cli_refuses_output_paths_outside_application_root(tmp_path: Path):
    _copy_inputs(tmp_path)
    outside = tmp_path.parent / "qwasar-escape.json"

    try:
        rc = main(["--root", str(tmp_path), "--output", str(outside)])
    except SystemExit as exc:
        rc = exc.code

    assert rc == 2
    assert not outside.exists()


def test_runtime_cli_strict_mode_does_not_overwrite_on_invalid_profile(tmp_path: Path):
    _copy_inputs(tmp_path)
    invalid = tmp_path / "data/profiles/invalid.qprofile.json"
    invalid.write_text("{ bad", encoding="utf-8")
    output = tmp_path / "data/qwasar_effective_profile.json"

    rc = main([
        "--root", str(tmp_path),
        "--profile", str(invalid),
        "--output", str(output),
        "--strict",
    ])

    assert rc == 1
    assert not output.exists()



def test_runtime_cli_selects_desktop_fallback_profile(tmp_path: Path):
    _copy_inputs(tmp_path)
    output = tmp_path / "data/qwasar_effective_profile.json"

    rc = main([
        "--root", str(tmp_path),
        "--platform", "desktop",
        "--default-profile", "data/profiles/voiddesk-desktop-default.qprofile.json",
        "--output", "data/qwasar_effective_profile.json",
    ])

    assert rc == 0
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["profile"]["id"] == "qwasar.profile.voiddesk.desktop-default"
