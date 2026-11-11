"""Safety tests for optional XFCE environment installation."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env_installer():
    script = ROOT / "bin" / "env_install.py"
    spec = importlib.util.spec_from_file_location("voiddesk_env_install_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_install_refuses_to_modify_an_active_xfce_session(
        tmp_path, monkeypatch):
    module = load_env_installer()
    data = tmp_path / "data"
    data.mkdir()
    image = data / "xfce.img"
    image.write_bytes(b"test image")

    monkeypatch.setattr(module, "DATA", str(data))
    monkeypatch.setattr(module, "IMG", str(image))
    monkeypatch.setattr(module, "MNT", str(data / "xfce_mnt"))
    monkeypatch.setattr(module, "fbtext", None)
    monkeypatch.setattr(module.imgmount, "is_mounted", lambda _path: True)
    monkeypatch.setattr(
        module.imgmount, "mount_img",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("must not mount or mutate an active image")
        ),
    )
    monkeypatch.setattr(
        module.subprocess, "call",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not launch package commands")
        ),
    )
    monkeypatch.setattr("sys.argv", ["env_install.py", "icewm"])

    assert module.main() == 1
