#!/usr/bin/env python3
"""Assemble the self-contained QWASAR / Void Desk static site."""
from __future__ import annotations
import argparse
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIAGRAMS = ROOT / "docs" / "assets"
BRAND = ROOT / "assets" / "brand"
RESOURCES = ROOT / "resources"
DIAGRAM_FILES = ("voiddesk-docs-banner.svg", "qwasar-system-map.svg", "nexus-v12-navigation.svg", "muos-profile-resolution.svg")
ICON_FILES = ("workshop.png", "settings.png", "the_forge.png", "start.png", "rt_toolbox.png", "net_sphere.png", "muos.png", "media_vault.png", "info.png", "end.png")
REQUIRED_SITE_PAGES = ("index.html", "architecture.html", "field-manual.html", "asset-atlas.html", "studio.html", "blueprint.html", "404.html")

def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required site asset is missing: {path.relative_to(ROOT)}")

class ReferenceCollector(HTMLParser):
    """Collect local link and asset references from a generated HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.references.append(value)


def validate_site(output: Path) -> None:
    pages = list(output.rglob("*.html"))
    known_ids: dict[Path, set[str]] = {}
    collected: dict[Path, list[str]] = {}
    for page in pages:
        parser = ReferenceCollector()
        parser.feed(page.read_text(encoding="utf-8"))
        known_ids[page.resolve()] = parser.ids
        collected[page.resolve()] = parser.references

    for page, references in collected.items():
        for reference in references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or parsed.path.startswith(("data:", "mailto:")):
                continue
            target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                raise FileNotFoundError(
                    f"Broken local reference in {page.relative_to(output.resolve())}: {reference}"
                )
            if parsed.fragment and target.suffix.lower() == ".html":
                fragment_ids = known_ids.get(target.resolve(), set())
                if parsed.fragment not in fragment_ids:
                    raise ValueError(
                        f"Broken fragment in {page.relative_to(output.resolve())}: {reference}"
                    )

    # Guard the portal's core product surfaces against accidental omission.
    page_names = {page.name for page in pages}
    missing_pages = sorted(set(REQUIRED_SITE_PAGES) - page_names)
    if missing_pages:
        raise FileNotFoundError(f"Required portal pages are missing: {', '.join(missing_pages)}")

    page_text = {page.name: page.read_text(encoding="utf-8") for page in pages}
    atlas = page_text["asset-atlas.html"]
    if atlas.count("data-asset-card") != len(ICON_FILES):
        raise ValueError(
            f"Asset Atlas must expose {len(ICON_FILES)} navigation icons; "
            f"found {atlas.count('data-asset-card')}"
        )
    if "assets/screens/forge-menu.png" not in atlas or "assets/icons/the_forge.png" not in atlas:
        raise ValueError("Asset Atlas must keep the THE FORGE screen and hub icon distinct")

    studio = page_text["studio.html"]
    if studio.count("data-studio-tab=") != 4 or studio.count("data-studio-panel=") != 4:
        raise ValueError("QWASAR Studio must expose all four workbenches and panels")
    for required in (
        'data-node-route="session.launch.xfce"',
        'data-node-route="route.forge.apt"',
        'data-node-route="route.media.library"',
        "data-export-profile",
        "data-export-release",
    ):
        if required not in studio:
            raise ValueError(f"QWASAR Studio is missing a required prototype contract: {required}")

    script = output / "assets" / "site.js"
    if not script.is_file():
        raise FileNotFoundError("Shared portal JavaScript is missing")
    script_text = script.read_text(encoding="utf-8")
    for required in (
        "data-studio-tab",
        "voiddesk-studio-sample.qprofile",
        "qwasar.release-manifest/v1",
        'title:"QWASAR Studio"',
    ):
        if required not in script_text:
            raise ValueError(f"Shared portal interactions are missing: {required}")

    for page_name in REQUIRED_SITE_PAGES:
        if page_name == "404.html":
            continue
        if 'id="command-dialog"' not in page_text[page_name]:
            raise ValueError(f"{page_name} is missing the global command palette")


def build(output: Path) -> None:
    for page_name in REQUIRED_SITE_PAGES:
        require_file(SITE / page_name)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SITE, output)
    asset_root = output / "assets"
    icon_root = asset_root / "icons"
    screen_root = asset_root / "screens"
    icon_root.mkdir(parents=True, exist_ok=True)
    screen_root.mkdir(parents=True, exist_ok=True)
    for name in DIAGRAM_FILES:
        source = DIAGRAMS / name
        require_file(source)
        shutil.copy2(source, asset_root / name)
    symbol = BRAND / "voiddesk_symbol.png"
    require_file(symbol)
    shutil.copy2(symbol, asset_root / symbol.name)
    for name in ICON_FILES:
        source = RESOURCES / name
        require_file(source)
        shutil.copy2(source, icon_root / name)
    forge_screen = RESOURCES / "forge-menu.png"
    require_file(forge_screen)
    shutil.copy2(forge_screen, screen_root / forge_screen.name)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    validate_site(output.resolve())
    pages = sorted(path.name for path in output.glob("*.html"))
    print(f"Built {len(pages)} HTML pages into {output}")
    print(f"Copied {len(DIAGRAM_FILES)} diagrams, {len(ICON_FILES)} navigation icons,")
    print("the brand symbol and the distinct THE FORGE screen capture.")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    build(output.resolve())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
