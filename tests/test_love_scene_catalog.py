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



def test_iptv_epg_fallback_ignores_empty_configured_list():
    core = (LOVE / "core" / "iptv.lua").read_text(encoding="utf-8")
    scene = (LOVE / "scenes" / "hub_iptv.lua").read_text(encoding="utf-8")

    assert "function iptv.select_epg_urls(cfg_urls, playlist_urls)" in core
    assert 'type(cfg_urls) == "table" and #cfg_urls > 0' in core
    assert 'type(playlist_urls) == "table" and #playlist_urls > 0' in core
    assert "cfg and cfg.epg_urls, resp and resp.epg_urls" in scene
    assert "local urls = cfg.epg_urls or resp.epg_urls" not in scene


def test_external_tools_status_widget_uses_the_same_status_publisher():
    source = (LOVE / "scenes" / "hub_external.lua").read_text(encoding="utf-8")
    assert "local function publish_status(scene, message)" in source
    assert 'widgets.info_row(20, 148, W-40, "Status", status_msg, nc, alpha)' in source
    assert 'publish_status(scene, "Loading external tools...")' in source
    assert 'publish_status(scene, "Launched: " .. t.name)' in source
    assert 'publish_status(scene, "Failed: " .. (resp.error or "unknown"))' in source
    assert 'scene.set_status("Loading external tools...")' not in source


def test_love_visual_capture_covers_all_declared_user_scenes():
    capture = (LOVE / "core" / "visual_capture.lua").read_text(
        encoding="utf-8"
    )
    scenes = re.findall(r'\{ name = "([^"]+)"', capture)
    assert len(scenes) == 25
    assert len(scenes) == len(set(scenes)), "duplicate LÖVE capture scene"

    for scene in scenes:
        assert (LOVE / "scenes" / f"{scene}.lua").is_file(), scene

    assert "hub_diagnostics" in scenes
    assert "hub_monitor" in scenes
    # The generic error/stub page is a fallback, not a user-facing feature.
    assert "hub_stub" not in scenes
