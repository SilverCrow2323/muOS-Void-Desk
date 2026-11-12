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
        launcher_info = archive.getinfo("Void-Desk/mux_launch.sh")
        launcher_mode = (launcher_info.external_attr >> 16) & 0o777
        service_modes = {
            name: (archive.getinfo(
                "Void-Desk/external/rt-tailscale-m/app/RtTailscale/" + name
            ).external_attr >> 16) & 0o777
            for name in ("rt", "ts", "watchdog")
        }
        tailscale_config = archive.read(
            "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf"
        ).decode("utf-8")
    assert names
    assert all(name.startswith("Void-Desk/") for name in names)
    assert "Void-Desk/mux_launch.sh" in names
    assert "Void-Desk/love/main.lua" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/rt" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/panel/server.py" in names
    assert "Void-Desk/external/rt-tailscale-m/app/RtTailscale/config/rt.conf" in names
    assert "PANEL=0" in tailscale_config
    assert "PANEL_BIND=127.0.0.1" in tailscale_config
    assert tailscale_config.splitlines()[0] == "PANEL=0"
    assert r"\n" not in tailscale_config
    assert launcher_mode & 0o111 == 0o111
    assert all(mode & 0o111 == 0o111 for mode in service_modes.values())
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
