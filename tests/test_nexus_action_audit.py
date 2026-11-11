from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AUDITED_SCENES = (
    "hub_session.lua",
    "hub_forge.lua",
    "hub_workshop.lua",
    "hub_toolbox.lua",
    "hub_mapps.lua",
)


def test_visible_hub_actions_have_no_dead_coming_soon_placeholders():
    for name in AUDITED_SCENES:
        source = (ROOT / "love" / "scenes" / name).read_text(encoding="utf-8")
        assert not re.search(
            r"coming soon|not implemented|TODO", source, re.IGNORECASE
        ), f"unfinished placeholder remains in {name}"


def test_hub_scene_routes_resolve_to_real_scene_files():
    for name in AUDITED_SCENES:
        source = (ROOT / "love" / "scenes" / name).read_text(encoding="utf-8")
        for target in re.findall(r'sm\.push\(["\']([^"\']+)["\']', source):
            target_path = ROOT / "love" / "scenes" / f"{target}.lua"
            assert target_path.is_file(), (
                f"{name} routes to missing scene {target}"
            )


def test_workshop_actions_are_connected_to_real_tools():
    workshop = (ROOT / "love" / "scenes" / "hub_workshop.lua").read_text(
        encoding="utf-8"
    )
    assert 'sm.push("hub_diagnostics"' in workshop
    assert 'sm.push("hub_monitor"' in workshop
    assert 'sm.push("hub_apt", {tab = "SYSTEM"})' in workshop
    assert 'sm.push("hub_apt", {tab = "JOBS"})' in workshop


def test_forge_bridge_calls_are_registered_and_legacy_dead_rows_are_gone():
    forge = (ROOT / "love" / "scenes" / "hub_forge.lua").read_text(
        encoding="utf-8"
    )
    service = (ROOT / "service" / "voiddesk_service.py").read_text(
        encoding="utf-8"
    )
    registered = {
        line.strip().split('"')[1]
        for line in service.splitlines()
        if line.strip().startswith('"') and '": h_' in line
    }
    called = set()
    for line in forge.splitlines():
        if 'bridge.call("' in line:
            called.add(line.split('bridge.call("', 1)[1].split('"', 1)[0])
    assert called <= registered, (
        "Forge calls missing service handlers: "
        + ", ".join(sorted(called - registered))
    )
    for stale in ("comp_install", "comp_autostart", "clihub_list"):
        assert stale not in forge
    assert 'bridge.call("session_launch", {id = "xfce"}' in forge
    assert 'apt_action = "install"' in forge


def test_muos_apps_scene_builds_a_dynamic_selectable_application_list():
    scene = (ROOT / "love" / "scenes" / "hub_mapps.lua").read_text(
        encoding="utf-8"
    )
    assert 'bridge.call("list_muos_apps"' in scene
    assert 'bridge.call("launch_muos_app", { path = app.path }' in scene
    assert "scene._get_items = items_for" in scene
    assert "Launch selected app" not in scene


def test_muos_app_handoff_is_validated_by_the_shell_launcher():
    launcher = (ROOT / "mux_launch.sh").read_text(encoding="utf-8")
    assert 'MUOS_APP="$DATA/.muos_app"' in launcher
    assert 'run_muos_app "$MUOS_APP_SCRIPT"' in launcher
    assert "/mnt/mmc/MUOS/application/*/mux_launch.sh" in launcher
    assert "/mnt/sdcard/MUOS/application/*/mux_launch.sh" in launcher
    assert 'APP_REAL" != "$ROOT_REAL/$APP_NAME"' in launcher
    assert 'APP_REAL" = "$APP_DIR"' in launcher

