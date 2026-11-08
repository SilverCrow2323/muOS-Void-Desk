import importlib.util
import json
from pathlib import Path


def load_tool():
    script = Path(__file__).resolve().parents[1] / "tools" / "visual_capture.py"
    spec = importlib.util.spec_from_file_location("visual_capture_tool", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_visual_inventory_tracks_assets_active_planets_and_screenshots(tmp_path):
    tool = load_tool()
    (tmp_path / "assets/nexus_planets").mkdir(parents=True)
    (tmp_path / "resources").mkdir()
    (tmp_path / "love/core").mkdir(parents=True)
    (tmp_path / "love/assets/nexus_planets").mkdir(parents=True)
    (tmp_path / "data/visual-captures").mkdir(parents=True)

    png = (
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
        + b"\x00\x00\x00\x01\x00\x00\x00\x01" + b"\x08\x06\x00\x00\x00"
    )
    (tmp_path / "assets/nexus_planets/start.png").write_bytes(png)
    (tmp_path / "love/assets/nexus_planets/start.png").write_bytes(png)
    (tmp_path / "resources/brand.otf").write_bytes(b"font")
    (tmp_path / "love/core/nodes.lua").write_text(
        'nodes.PLANET_FILE = { start="start.png" }\n'
        'nodes.LIST = {\n'
        ' { idx=0, name="START", icon="start", ring=1, type="sun" },\n'
        '}\nfunction nodes.color_for(idx) return nodes.COLOR[idx] end\n',
        encoding="utf-8",
    )
    image = (
        tmp_path / "data/visual-captures/"
        "love__nexus__20261108T120000_001.png"
    )
    image.write_bytes(png)
    image.with_suffix(".json").write_text(json.dumps({
        "engine": "love",
        "screen": "nexus",
        "timestamp_utc": "2026-11-08T12:00:00Z",
        "width": 1,
        "height": 1,
        "image": image.name,
    }), encoding="utf-8")

    report = tool.generate(tmp_path)
    assert report["asset_count"] == 3
    assert report["missing_love_textures"] == []
    assert len(report["screenshots"]) == 1
    assert report["screenshots"][0]["screen"] == "nexus"
    assert (tmp_path / "docs/visual/ASSET_CATALOG.md").is_file()
    assert (tmp_path / "docs/visual/SCREENSHOT_CHECKLIST.md").is_file()
    payload = json.loads(
        (tmp_path / "docs/visual/visual-inventory.json").read_text()
    )
    assert payload["asset_count"] == 3


def test_png_dimensions_header_parser(tmp_path):
    tool = load_tool()
    data = (
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
        + b"\x00\x00\x02\x80\x00\x00\x01\xe0" + b"\x08\x06\x00\x00\x00"
    )
    path = tmp_path / "screen.png"
    path.write_bytes(data)
    assert tool.dimensions(path) == (640, 480)
