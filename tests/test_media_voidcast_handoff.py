from desk.hubs import media


class FakeApp:
    def __init__(self):
        self.messages = []
        self.handoff_label = None
        self.running = True
        self.exit_code = 99

    def notify(self, *args):
        self.messages.append(args)

    def handoff(self, label):
        self.handoff_label = label


def test_media_voidcast_writes_mux_handoff_and_exits_cleanly(tmp_path, monkeypatch):
    app_root = tmp_path / "Void-Desk"
    script = app_root / "outdesk" / "VoidCast" / "voidcast" / "main.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('VoidCast')")
    data_dir = app_root / "data"
    muos_bootstrap = tmp_path / "muos" / "script" / "var" / "func.sh"
    muos_bootstrap.parent.mkdir(parents=True)
    muos_bootstrap.write_text("# muOS")
    monkeypatch.setattr(media, "APP_DIR", app_root)
    monkeypatch.setattr(media, "DATA_DIR", data_dir)
    monkeypatch.setattr(media, "MUOS_BOOTSTRAP", muos_bootstrap)
    app = FakeApp()

    media.MediaHub(app).voidcast()

    assert (data_dir / ".pending_session").read_text() == "voidcast\n"
    assert app.handoff_label == "AVVIO VOIDCAST IPTV..."
    assert app.exit_code == 0
    assert app.running is False
    assert app.messages == []


def test_media_voidcast_reports_missing_muos_launcher(tmp_path, monkeypatch):
    app_root = tmp_path / "Void-Desk"
    script = app_root / "outdesk" / "VoidCast" / "voidcast" / "main.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('VoidCast')")
    data_dir = app_root / "data"
    monkeypatch.setattr(media, "APP_DIR", app_root)
    monkeypatch.setattr(media, "DATA_DIR", data_dir)
    monkeypatch.setattr(media, "MUOS_BOOTSTRAP", tmp_path / "missing-func.sh")
    app = FakeApp()

    media.MediaHub(app).voidcast()

    assert app.running is True
    assert app.exit_code == 99
    assert not data_dir.exists()
    assert app.messages and app.messages[0][0] == "VoidCast IPTV"

def test_mux_launcher_bootstraps_pygame_runtime_for_voidcast_even_with_love_engine():
    from pathlib import Path

    launcher = Path(__file__).resolve().parents[1] / "mux_launch.sh"
    source = launcher.read_text(encoding="utf-8")
    branch = source.split("            voidcast)", 1)[1].split("            *)", 1)[0]

    assert 'MARKER="$DATA/.pygame_ready"' in branch
    assert 'python3 "$APP_DIR/bin/bootstrap_lite.py"' in branch
    assert '[ ! -f "$MARKER" ]' in branch
    assert '[ ! -d "$APP_DIR/runtime" ]' in branch
    assert branch.index("bootstrap_lite.py") < branch.index('python3 "$APP_DIR/outdesk/VoidCast/voidcast/main.py"')

