import hashlib
import importlib.util
from pathlib import Path
import zipfile
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    script = ROOT / "tools" / "build_muxapp.py"
    spec = importlib.util.spec_from_file_location("voiddesk_muxapp_builder_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_project(root: Path):
    for path in ("mux_launch.sh", "voiddesk.py", "love/main.lua",
                 "bin/launcher.sh", "service/voiddesk_service.py",
                 "external/tools.json", "LICENSE", "README.md",
                 "THIRD-PARTY.md",
                 "outdesk/VoidCast/voidcast/main.py",
                 "outdesk/VoidCast/presets/config.default.json",
                 "service/spdw_hub/__init__.py",
                 "service/spdw_hub/device_agent.py",
                 "service/spdw_hub/registry.py",
                 "service/spdw_hub/services.json",
                 "service/spdw_hub/addons.py",
                 "service/spdw_hub/manifest.schema.json"):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test fixture\n")

    upstream = root / "external" / "rt-tailscale-m"
    app = upstream / "app" / "RtTailscale"
    (app / "panel").mkdir(parents=True)
    for name in ("rt", "ts", "watchdog", "VERSION"):
        (app / name).write_text("fixture\n")
    (app / "panel" / "server.py").write_text("fixture\n")
    (app / "panel" / "index.html").write_text("fixture\n")
    (upstream / "LICENSE").write_text("MIT\n")
    (upstream / "THIRD-PARTY.md").write_text("notices\n")


def test_builder_emits_only_void_desk_root_and_bundles_rt_service(tmp_path, monkeypatch):
    builder = load_builder()
    monkeypatch.setattr(
        builder.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=builder.TAILSCALE_COMMIT, stderr=""
        ),
    )
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / ".env").write_text("API_KEY=must-not-ship\n")
    (project / "data").mkdir()
    (project / "data" / "user-config.json").write_text("{\"private\": true}")
    output = tmp_path / "dist" / "Void-Desk.muxapp"

    result = builder.build_archive(project, output)

    assert result == output
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    sidecar = output.with_suffix(output.suffix + ".sha256")
    assert sidecar.read_text(encoding="ascii").startswith(expected_hash + "  ")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        tailscale_config = archive.read(
            "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf"
        ).decode("utf-8")
    assert names
    assert all(name.startswith("Void-Desk/") for name in names)
    assert "Void-Desk/mux_launch.sh" in names
    assert "Void-Desk/love/main.lua" in names
    assert "Void-Desk/outdesk/VoidCast/voidcast/main.py" in names
    assert "Void-Desk/outdesk/VoidCast/presets/config.default.json" in names
    assert "Void-Desk/service/spdw_hub/device_agent.py" in names
    assert "Void-Desk/service/spdw_hub/services.json" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf" in names
    assert "PANEL=0" in tailscale_config
    assert "PANEL_BIND=127.0.0.1" in tailscale_config
    assert not any(name.startswith("Void-Desk/tests/") for name in names)
    assert "Void-Desk/.env" not in names
    assert "Void-Desk/data/user-config.json" not in names


def test_builder_fails_if_pinned_submodule_is_not_initialized(tmp_path):
    builder = load_builder()
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / "external" / "rt-tailscale-m" / "app" / "RtTailscale" / "rt").unlink()

    try:
        builder.build_archive(project, tmp_path / "bad.muxapp")
    except RuntimeError as exc:
        assert "git submodule update --init --recursive" in str(exc)
    else:
        raise AssertionError("builder must refuse a package without Rt:Tailscale-M")

def test_builder_refuses_package_without_voidcast_entrypoint(tmp_path, monkeypatch):
    builder = load_builder()
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / "outdesk" / "VoidCast" / "voidcast" / "main.py").unlink()

    try:
        builder.build_archive(project, tmp_path / "missing-voidcast.muxapp")
    except RuntimeError as exc:
        assert "outdesk/VoidCast/voidcast/main.py" in str(exc)
    else:
        raise AssertionError("builder must refuse a package without VoidCast")

def test_builder_refuses_package_without_device_agent(tmp_path, monkeypatch):
    builder = load_builder()
    monkeypatch.setattr(
        builder.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=builder.TAILSCALE_COMMIT, stderr=""
        ),
    )
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / "service" / "spdw_hub" / "device_agent.py").unlink()

    try:
        builder.build_archive(project, tmp_path / "missing-agent.muxapp")
    except RuntimeError as exc:
        assert "service/spdw_hub/device_agent.py" in str(exc)
    else:
        raise AssertionError("builder must refuse a package without the Device Agent")

