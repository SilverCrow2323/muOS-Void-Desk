import importlib.util
from pathlib import Path
import zipfile


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
                 "THIRD-PARTY.md"):
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


def test_builder_emits_only_void_desk_root_and_bundles_rt_service(tmp_path):
    builder = load_builder()
    project = tmp_path / "project"
    project.mkdir()
    make_project(project)
    (project / ".env").write_text("API_KEY=must-not-ship\n")
    (project / "data").mkdir()
    (project / "data" / "user-config.json").write_text("{\"private\": true}")
    output = tmp_path / "dist" / "Void-Desk.muxapp"

    result = builder.build_archive(project, output)

    assert result == output
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    assert names
    assert all(name.startswith("Void-Desk/") for name in names)
    assert "Void-Desk/mux_launch.sh" in names
    assert "Void-Desk/love/main.lua" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf" in names
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
