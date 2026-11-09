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


def test_media_voidcast_entry_hands_off_to_bundled_outdesk_app():
    source = (LOVE / "scenes" / "hub_media.lua").read_text(encoding="utf-8")
    assert 'label = "VoidCast IPTV"' in source
    assert 'bridge.call("voidcast_launch", {}' in source
    assert "love.event.quit()" in source
    assert "LÖVE prototype" not in source
    assert "M3U, multi-source EPG, PVR and add-ons" in source

def test_uplink_exposes_shared_spdw_device_agent_status_and_pairing():
    source = (LOVE / "scenes" / "hub_uplink.lua").read_text(encoding="utf-8")
    assert 'bridge.call("hub_gateway_status", {}' in source
    assert 'label = "SPDW Hub Device Agent"' in source
    assert "state.hub.pairing_pin" in source
    assert "state.hub.port" in source


def test_external_tools_status_widget_uses_the_same_status_publisher():
    source = (LOVE / "scenes" / "hub_external.lua").read_text(encoding="utf-8")
    assert "local function publish_status(scene, message)" in source
    assert 'widgets.info_row(20, 148, W-40, "Status", status_msg, nc, alpha)' in source
    assert "publish_status(scene, \"Loading external tools...\")" in source
    assert "publish_status(scene, \"Launched: \" .. t.name)" in source
    assert "publish_status(scene, \"Failed: \" .. (resp.error or \"unknown\"))" in source
    assert "scene.set_status(\"Loading external tools...\")" not in source
