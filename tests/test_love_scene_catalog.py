import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOVE = ROOT / "love"


def _labels(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    return re.findall(r'label\s*=\s*"([^"]+)"', source)


def test_forge_menu_has_no_duplicate_labels():
    labels = _labels(LOVE / "scenes" / "hub_forge.lua")
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    assert not duplicates, "duplicate Forge menu entries: " + ", ".join(duplicates)


def test_toolbox_calculator_and_clock_open_existing_scenes():
    source = (LOVE / "scenes" / "hub_toolbox.lua").read_text(encoding="utf-8")
    for scene in ("tool_calc", "tool_clock"):
        assert f'sm.push("{scene}", {{}})' in source
        assert (LOVE / "scenes" / f"{scene}.lua").is_file()

    assert "Coming soon: scientific + RPN" not in source
    assert "Coming soon: digital + analog" not in source


def test_forge_shell_opens_existing_shell_scene():
    source = (LOVE / "scenes" / "hub_forge.lua").read_text(encoding="utf-8")
    assert 'sm.push("hub_shell", {})' in source
    assert (LOVE / "scenes" / "hub_shell.lua").is_file()
