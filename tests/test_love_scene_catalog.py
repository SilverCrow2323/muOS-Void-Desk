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


def test_love_visual_capture_includes_diagnostics_and_monitor():
    capture = (LOVE / "core" / "visual_capture.lua").read_text(
        encoding="utf-8"
    )
    for scene in ("hub_diagnostics", "hub_monitor"):
        assert f'name = "{scene}"' in capture
        assert (LOVE / "scenes" / f"{scene}.lua").is_file()

    # The generic error/stub page is a fallback, not a user-facing feature.
    assert 'name = "hub_stub"' not in capture


def test_all_love_bridge_commands_are_registered_by_the_service():
    service = (ROOT / "service" / "voiddesk_service.py").read_text(
        encoding="utf-8"
    )
    registered = set(re.findall(
        r'^\s*"([a-z0-9_]+)"\s*:\s*h_[a-z0-9_]+,',
        service,
        re.MULTILINE,
    ))
    called = set()
    for source_path in LOVE.rglob("*.lua"):
        source = source_path.read_text(encoding="utf-8")
        called.update(re.findall(
            r'bridge\.call\(\s*["\']([a-z0-9_]+)["\']',
            source,
        ))
    missing = sorted(called - registered)
    assert not missing, "LÖVE bridge commands without service handlers: " + ", ".join(missing)



def test_start_session_is_a_real_desktop_environment_selector():
    source = (LOVE / "scenes" / "hub_session.lua").read_text(encoding="utf-8")
    for env_id in ("xfce", "icewm", "lxde"):
        assert f'id = "{env_id}"' in source
        assert f'"{env_id}"' in source
    assert "VoidCast" not in source
    assert "detail_open" in source
    assert "confirm_uninstall" in source
    assert 'bridge.call("session_launch"' in source
    assert 'bridge.call("xfce_install"' in source
    assert 'bridge.call("env_install"' in source
    assert 'bridge.call("env_uninstall"' in source
    assert 'bridge.call("env_update_check"' in source


def test_love_global_onboarding_tablet_and_operation_overlay_are_wired():
    main = (LOVE / "main.lua").read_text(encoding="utf-8")
    for module in ("core.onboarding", "core.tablet", "core.operation_overlay"):
        assert f'require("{module}")' in main
    assert "onboarding.init(config)" in main
    assert "onboarding.draw(current_theme)" in main
    assert "tablet.draw()" in main
    assert "operation_overlay.draw()" in main
    assert 'if key == "m" then' in main
    assert "tablet.toggle()" in main
    assert (LOVE / "core" / "onboarding.lua").is_file()
    assert (LOVE / "core" / "tablet.lua").is_file()
    assert (LOVE / "core" / "operation_overlay.lua").is_file()


def test_xfce_bootstrap_publishes_english_structured_progress_not_framebuffer_text():
    source = (ROOT / "bin" / "xfce_bootstrap.py").read_text(encoding="utf-8")
    assert ".xfce_bootstrap_state.json" in source
    assert "def report(" in source
    assert "Not enough free storage. Need at least" in source
    assert "import fbtext" not in source
    assert "FATAL: servono almeno" not in source
    assert "0/5 controlli preliminari" not in source


def test_desktop_maintenance_is_allowlisted_and_does_not_auto_upgrade():
    helper = (ROOT / "bin" / "desktop_env_maintenance.py").read_text(encoding="utf-8")
    service = (ROOT / "service" / "voiddesk_service.py").read_text(encoding="utf-8")
    assert 'action not in ("uninstall", "updates")' in helper
    assert 'env_id not in ENVIRONMENTS' in helper
    assert '"env_uninstall": h_env_uninstall' in service
    assert '"env_update_check": h_env_update_check' in service
    assert "apt-get -s upgrade" in helper
    assert "apt-get upgrade" not in helper


def test_love_dashboard_widget_budgets_leave_room_for_menu_rows():
    compact = (
        "hub_info.lua", "hub_media.lua", "hub_forge.lua", "hub_uplink.lua",
        "hub_external.lua", "hub_settings.lua", "hub_workshop.lua",
        "hub_diagnostics.lua", "hub_tailscale.lua", "hub_syncthing.lua",
        "hub_display_fx.lua",
    )
    for name in compact:
        source = (LOVE / "scenes" / name).read_text(encoding="utf-8")
        match = re.search(r"widget_height\s*=\s*(\d+)", source)
        assert match, f"{name} has no explicit widget budget"
        assert int(match.group(1)) <= 125, f"{name} still wastes vertical menu space"


def test_nexus_orbits_have_wider_spacing_and_planets_are_not_pixel_grid_shaded():
    source = (LOVE / "scenes" / "nexus.lua").read_text(encoding="utf-8")
    planet = (LOVE / "core" / "planet.lua").read_text(encoding="utf-8")
    assert "[2]=164, [3]=232, [4]=296" in source
    assert "local SQUASH = 0.42" in source
    assert "for i = 0, N-1" not in planet
    assert "three-tone cel-shaded sphere" in planet.lower()
    assert 'love.graphics.arc("pie"' in planet



def test_notes_has_a_real_toolbox_route_and_visual_capture():
    toolbox = (LOVE / "scenes" / "hub_toolbox.lua").read_text(encoding="utf-8")
    capture = (LOVE / "core" / "visual_capture.lua").read_text(encoding="utf-8")
    service = (ROOT / "service" / "voiddesk_service.py").read_text(encoding="utf-8")
    assert 'sm.push("hub_notes", {})' in toolbox
    assert (LOVE / "scenes" / "hub_notes.lua").is_file()
    assert 'name = "hub_notes"' in capture
    for command in ("notes_list", "notes_read", "notes_save", "notes_delete"):
        assert f'"{command}": h_' in service
