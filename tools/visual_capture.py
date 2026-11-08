#!/usr/bin/env python3
"""Inventory VoidDesk graphics and F12 screenshots.

Examples:
    python3 tools/visual_capture.py
    python3 tools/visual_capture.py --check
    python3 tools/visual_capture.py --export-public

Only the Python standard library is required. Captures stay local until reviewed.
"""
from __future__ import annotations
import argparse
import html
import os
import hashlib
import json
import re
import shutil
import struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ASSET_DIRS = ("assets", "resources", "love/assets", "glyph")
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
              ".svg", ".ttf", ".otf", ".woff", ".woff2"}
REQUIRED = {
    "pygame": ["home", "session", "forge", "uplink", "mediahub",
               "workshop", "toolbox", "mapps", "settings", "info"],
    "love": ["bootanim", "intro", "nexus", "hub_session", "hub_forge",
             "hub_uplink", "hub_media", "hub_workshop", "hub_toolbox",
             "hub_mapps", "hub_external", "hub_settings", "hub_display_fx",
             "hub_info", "hub_iptv", "hub_calendar", "hub_shell",
             "tool_calc", "tool_clock", "tool_editor"],
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dimensions(path: Path) -> tuple[int | None, int | None]:
    """Read common image dimensions from headers; Pillow is not required."""
    try:
        data = path.read_bytes()[:65536]
    except OSError:
        return None, None
    try:
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            return struct.unpack(">II", data[16:24])
        if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
            return struct.unpack("<HH", data[6:10])
        if data.startswith(b"BM") and len(data) >= 26:
            w, h = struct.unpack("<ii", data[18:26])
            return abs(w), abs(h)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and data[12:16] == b"VP8X" and len(data) >= 30:
            return (1 + int.from_bytes(data[24:27], "little"),
                    1 + int.from_bytes(data[27:30], "little"))
        if data[:2] == b"\xff\xd8":
            i = 2
            while i + 4 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
                    continue
                size = int.from_bytes(data[i:i + 2], "big")
                if size < 2 or i + size > len(data):
                    break
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    return int.from_bytes(data[i + 5:i + 7], "big"), int.from_bytes(data[i + 3:i + 5], "big")
                i += size
        if path.suffix.lower() == ".svg":
            root = ET.fromstring(data.decode("utf-8", "ignore"))
            vb = root.attrib.get("viewBox", "").replace(",", " ").split()
            if len(vb) == 4:
                return int(float(vb[2])), int(float(vb[3]))
    except (ValueError, IndexError, ET.ParseError, OverflowError):
        return None, None
    return None, None


def scan_assets(root: Path) -> list[dict]:
    out = []
    for folder_name in ASSET_DIRS:
        folder = root / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in ASSET_EXTS:
                continue
            is_image = path.suffix.lower() in {
                ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"
            }
            w, h = dimensions(path) if is_image else (None, None)
            out.append({
                "path": path.relative_to(root).as_posix(),
                "kind": "image" if is_image else "font",
                "bytes": path.stat().st_size,
                "width": w, "height": h,
                "sha256": digest(path),
            })
    return out


def active_planet_images(root: Path) -> tuple[list[str], list[str]]:
    file = root / "love/core/nodes.lua"
    if not file.exists():
        return [], []
    text = file.read_text(encoding="utf-8", errors="replace")
    mapping = re.search(r"nodes\.PLANET_FILE\s*=\s*\{(.*?)\n\}", text, re.S)
    listing = re.search(
        r"nodes\.LIST\s*=\s*\{(.*?)\n\}\s*\n\s*function nodes\.color_for",
        text, re.S)
    if not mapping or not listing:
        return [], ["Could not parse LÖVE node asset declarations"]
    icons = dict(re.findall(r'([A-Za-z0-9_]+)\s*=\s*"([^"]+)"', mapping.group(1)))
    blocks = re.split(r"(?=^\s*\{\s*idx\s*=)", listing.group(1), flags=re.M)
    active, missing = [], []
    for block in blocks:
        icon = re.search(r'\bicon\s*=\s*"([^"]+)"', block)
        if not icon or re.search(r"\bhidden\s*=\s*true", block):
            continue
        name = icons.get(icon.group(1))
        if not name:
            missing.append("No PLANET_FILE entry for " + icon.group(1))
            continue
        path = "love/assets/nexus_planets/" + name
        active.append(path)
        if not (root / path).is_file():
            missing.append(path)
    return active, missing


def scan_screenshots(root: Path) -> list[dict]:
    folder = root / "data/visual-captures"
    if not folder.exists():
        return []
    out = []
    for image in sorted(folder.rglob("*.png")):
        sidecar = image.with_suffix(".json")
        meta = {}
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {"metadata_error": "invalid JSON sidecar"}
        w, h = dimensions(image)
        out.append({
            "path": image.relative_to(root).as_posix(),
            "engine": meta.get("engine", image.name.split("__", 1)[0]),
            "screen": meta.get("screen", ""),
            "timestamp_utc": meta.get("timestamp_utc", ""),
            "width": meta.get("width", w), "height": meta.get("height", h),
            "bytes": image.stat().st_size,
            "metadata": sidecar.relative_to(root).as_posix() if sidecar.exists() else None,
        })
    return out


def write_galleries(root: Path, outdir: Path,
                   assets: list[dict], screenshots: list[dict],
                   public_captures: bool = False) -> None:
    """Create local HTML galleries without external libraries or network access."""
    image_items = [item for item in assets if item["kind"] == "image"]
    asset_cards = []
    for item in image_items:
        src = os.path.relpath(root / item["path"], outdir).replace(os.sep, "/")
        label = html.escape(item["path"])
        dimensions_text = (
            f"{item['width']} × {item['height']}"
            if item["width"] and item["height"] else "dimensions unavailable"
        )
        asset_cards.append(
            '<article class="asset">'
            f'<a href="{html.escape(src, quote=True)}" target="_blank" rel="noreferrer">'
            f'<img loading="lazy" src="{html.escape(src, quote=True)}" alt="{label}"></a>'
            f'<h2>{label}</h2>'
            f'<p>{dimensions_text} · {item["bytes"]:,} bytes</p>'
            f'<code>SHA-256 {item["sha256"][:16]}…</code>'
            '</article>'
        )

    font_cards = []
    for item in (item for item in assets if item["kind"] == "font"):
        label = html.escape(item["path"])
        font_cards.append(
            '<article class="font">'
            f'<h2>{label}</h2><p>{item["bytes"]:,} bytes</p>'
            '<p class="sample">VoidDesk NEXUS · 0123456789</p>'
            '</article>'
        )

    asset_html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VoidDesk — Visual Asset Gallery</title>
<style>
:root{color-scheme:dark}body{margin:0;padding:28px;background:#090c12;color:#e7edf4;
font:15px/1.5 system-ui,sans-serif}h1{margin:0 0 8px;font-size:28px}
p.lead{color:#aab7c6;margin:0 0 24px}.grid{display:grid;
grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
article{min-width:0;background:#141c28;border:1px solid #29364a;border-radius:10px;
padding:12px;overflow:hidden}.asset img{display:block;width:100%;height:150px;
object-fit:contain;background:#080b10;border-radius:6px}.asset h2,.font h2{
font:600 12px/1.4 ui-monospace,monospace;overflow-wrap:anywhere;margin:10px 0 4px}
article p,code{font-size:11px;color:#aebac8}.font .sample{font-size:22px;padding:18px 0}
</style></head><body>
<h1>VoidDesk — Visual Asset Gallery</h1>
<p class="lead">Local review gallery generated from the tracked project assets. Images are linked to their original files.</p>
<h2>Images and graphics</h2><div class="grid">""" + "\n".join(asset_cards) + """</div>
<h2>Fonts</h2><div class="grid">""" + "\n".join(font_cards) + """</div>
</body></html>
"""
    (outdir / "ASSET_GALLERY.html").write_text(asset_html, encoding="utf-8")

    screenshot_cards = []
    for item in screenshots:
        if public_captures:
            src = "captures/" + Path(item["path"]).name
        else:
            src = os.path.relpath(root / item["path"], outdir).replace(os.sep, "/")
        label = html.escape(f"{item['engine']} / {item['screen'] or 'unknown screen'}")
        dims = (
            f"{item['width']} × {item['height']}"
            if item["width"] and item["height"] else "dimensions unavailable"
        )
        screenshot_cards.append(
            '<article class="shot">'
            f'<a href="{html.escape(src, quote=True)}" target="_blank" rel="noreferrer">'
            f'<img loading="lazy" src="{html.escape(src, quote=True)}" alt="{label}"></a>'
            f'<h2>{label}</h2><p>{dims} · {item["bytes"]:,} bytes</p>'
            f'<code>{html.escape(item["path"])}</code></article>'
        )
    screenshot_html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VoidDesk — Screenshot Gallery</title>
<style>
:root{color-scheme:dark}body{margin:0;padding:28px;background:#090c12;color:#e7edf4;
font:15px/1.5 system-ui,sans-serif}h1{font-size:28px;margin:0 0 8px}
p.lead{color:#aab7c6;margin:0 0 24px}.grid{display:grid;
grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
article{background:#141c28;border:1px solid #29364a;border-radius:10px;padding:12px}
img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#080b10;border-radius:6px}
h2{font:600 13px ui-monospace,monospace;overflow-wrap:anywhere;margin:10px 0 4px}
p,code{font-size:11px;color:#aebac8;overflow-wrap:anywhere}
</style></head><body>
<h1>VoidDesk — Screenshot Gallery</h1>
<p class="lead">Local PNG captures from the Pygame and LÖVE frontends. Review these for private information before sharing.</p>
<div class="grid">""" + "\n".join(screenshot_cards) + """</div>
</body></html>
"""
    (outdir / "SCREENSHOT_GALLERY.html").write_text(screenshot_html, encoding="utf-8")


def generate(root: Path, export_public: bool = False) -> dict:
    assets = scan_assets(root)
    screenshots = scan_screenshots(root)
    active, missing = active_planet_images(root)
    outdir = root / "docs/visual"
    outdir.mkdir(parents=True, exist_ok=True)

    groups = defaultdict(list)
    for item in assets:
        groups[item["path"].split("/", 1)[0]].append(item)
    lines = ["# Visual asset catalogue", "",
             "Generated by tools/visual_capture.py; do not edit by hand.", "",
             f"**{len(assets)} image and font assets** tracked.", "",
             "| Directory | Files | Size |", "|---|---:|---:|"]
    for name in sorted(groups):
        lines.append(f"| {name}/ | {len(groups[name])} | {sum(x['bytes'] for x in groups[name]) / 1024:.1f} KiB |")
    lines += ["", "## Active LÖVE NEXUS textures", ""] + [f"- {p}" for p in active]
    if missing:
        lines += ["", "## Missing references", ""] + [f"- {p}" for p in missing]
    else:
        lines += ["", "All active visible LÖVE node textures are present."]
    lines += ["", "## Full inventory", "",
              "| File | Kind | Dimensions | Size | SHA-256 prefix |",
              "|---|---|---:|---:|---|"]
    for x in assets:
        dims = f"{x['width']}x{x['height']}" if x["width"] and x["height"] else "—"
        lines.append(f"| {x['path']} | {x['kind']} | {dims} | {x['bytes']:,} B | {x['sha256'][:12]} |")
    (outdir / "ASSET_CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    seen = {name: set() for name in REQUIRED}
    for x in screenshots:
        if x["engine"] in seen and x["screen"]:
            seen[x["engine"]].add(x["screen"])
    lines = ["# Screenshot coverage", "",
             "Press F12 in either frontend to capture a PNG and JSON sidecar.",
             "Captures remain local until reviewed for private information.", "",
             f"Found {len(screenshots)} screenshot(s)."]
    for engine, required in REQUIRED.items():
        lines += ["", f"## {engine.title()}", "", "| Screen | Status |", "|---|---|"]
        for screen in required:
            lines.append(f"| {screen} | {'captured' if screen in seen[engine] else 'not captured'} |")
    lines += ["", "## Captured files", ""]
    if screenshots:
        lines += ["| Path | Engine | Screen | Resolution |", "|---|---|---|---:|"]
        for x in screenshots:
            dims = f"{x['width']}x{x['height']}" if x["width"] and x["height"] else "—"
            lines.append(f"| {x['path']} | {x['engine']} | {x['screen']} | {dims} |")
    else:
        lines.append("No local screenshots found yet.")
    lines += ["", "## Workflow", "",
              "1. Start a frontend and navigate to a stable screen.",
              "2. Press F12 and wait for the PNG and JSON sidecar to save.",
              "3. Copy data/visual-captures/ from the device to this checkout.",
              "4. Run python3 tools/visual_capture.py to refresh this report.",
              "5. Inspect every image for SSIDs, IPs, hostnames and personal filenames.",
              "6. Use --export-public only for images approved for publication."]
    (outdir / "SCREENSHOT_CHECKLIST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if export_public and screenshots:
        target = outdir / "captures"
        target.mkdir(parents=True, exist_ok=True)
        for x in screenshots:
            src = root / x["path"]
            shutil.copy2(src, target / src.name)
            if x["metadata"]:
                meta = root / x["metadata"]
                shutil.copy2(meta, target / meta.name)

    write_galleries(root, outdir, assets, screenshots, export_public)
    payload = {
        "asset_count": len(assets), "assets": assets,
        "active_love_textures": active, "missing_love_textures": missing,
        "screenshots": screenshots, "required_screens": REQUIRED,
    }
    (outdir / "visual-inventory.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true",
                        help="return non-zero if an active LÖVE texture is missing")
    parser.add_argument("--export-public", action="store_true",
                        help="copy reviewed screenshots into docs/visual/captures/ and link the gallery there")
    args = parser.parse_args()
    result = generate(args.root.resolve(), args.export_public)
    print("Visual inventory: %d assets, %d screenshots" %
          (result["asset_count"], len(result["screenshots"])))
    for missing in result["missing_love_textures"]:
        print("MISSING:", missing)
    return 1 if args.check and result["missing_love_textures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
